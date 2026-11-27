# Mary Care Management System (UK Health & Social Care)

Production-ready enterprise domiciliarly care management platform built with **FastAPI (Python 3.12)**, **Vue.js 3 (Vite + Element Plus)**, **MySQL 8 / PostgreSQL**, and **Docker Compose**. Compliant with UK Health & Social Care regulations, CQC Key Lines of Enquiry (KLOEs), and UK GDPR Article 9 standards for Special Category Health Data.

The copy of this guide in the parent `C:\Projects\Mary` folder was not changed. This file is the guide for `mary-v2`. Current Windows and Ubuntu deployment steps for this folder are also in [DEPLOYMENT.md](DEPLOYMENT.md). The longer technical catalogue is in [mary-element/docs/README.md](mary-element/docs/README.md).

---

## Table of Contents
1. [System Architecture Overview](#1-system-architecture-overview)
2. [Recent Enhancements & Bug Fixes](#2-recent-enhancements--bug-fixes)
   - [502 Bad Gateway Root Cause & Resolution](#a-502-bad-gateway-root-cause--resolution)
   - [Daily Time Record (DTR) Expand/Collapse Fix](#b-daily-time-record-dtr-expandcollapse-fix)
   - [API Security Architecture & Vulnerability Mitigation](#c-api-security-architecture--vulnerability-mitigation)
3. [Authentication & Authorization Architecture](#3-authentication--authorization-architecture)
   - [Token Generation, Validation & Lifecycle](#a-token-generation-validation--lifecycle)
   - [Cryptography & Password Security](#b-cryptography--password-security)
   - [Role-Based Access Control (RBAC)](#c-role-based-access-control-rbac)
4. [API Security Specifications](#4-api-security-specifications)
5. [Environment Configuration & Variables](#5-environment-configuration--variables)
6. [Docker Deployment & Operational Guide](#6-docker-deployment--operational-guide)
7. [Docker Troubleshooting Guide](#7-docker-troubleshooting-guide)
8. [Automated Verification & Test Execution](#8-automated-verification--test-execution)
9. [Forgot Password Email](#9-forgot-password-email)

---

## 1. System Architecture Overview

The system runs as an orchestrated multi-container Docker cluster:

```
+-------------------------------------------------------------------------------+
|                                Host Machine                                   |
|                        (Local MySQL 8 on Port 3306)                           |
+-------------------------------------------------------------------------------+
                                      ^
                                      | host.docker.internal:3306
+---------------------+     +-----------------------+     +---------------------+
|   mary_frontend     |     |     mary_backend      |     |     mary_redis      |
|    Nginx 1.30       | --> |   FastAPI (Python)    | --> |    Redis 7-Alpine   |
| (Reverse Proxy :80) |     |  (Uvicorn ASGI :8000) |     |     (Port :6379)    |
+---------------------+     +-----------------------+     +---------------------+
      ^
      | Exposed Port 8080:80
   Clients / Web Browsers
```

- **Frontend Container (`mary_frontend`)**: Nginx reverse proxy serving the built Vue 3 Single Page Application (SPA) on `:80` (mapped to `:8080` on host). Routes `/api/*` and `/healthz` directly to upstream `backend:8000`.
- **Backend Container (`mary_backend`)**: FastAPI running on Python 3.12 with asynchronous SQLAlchemy 2.0, aiomysql, PyJWT, and WeasyPrint for PDF generation.
- **Database Connectivity**: Connects to the host MySQL 8 database (`mary_api_db_new`) via Docker `host.docker.internal:host-gateway` bridge.
- **Cache / Message Broker (`mary_redis`)**: Redis 7 for Celery asynchronous tasks and session caching.

---

## 2. Recent Enhancements & Bug Fixes

### A. 502 Bad Gateway Root Cause & Resolution
- **Symptom**: Client requests to `http://localhost:8080/api/v1/login` failed immediately with HTTP `502 Bad Gateway`.
- **Root Cause**: `mary_backend` container crashed during application startup lifecycle in `lifespan` (`async with engine.begin()`). MySQL 8+ defaults to `caching_sha2_password` authentication, which requires the `cryptography` Python library to encrypt credentials during the handshake. Because `cryptography` was absent from `requirements.txt`, `pymysql/_auth.py` threw `RuntimeError: 'cryptography' package is required for sha256_password or caching_sha2_password auth methods`, crashing Uvicorn and putting the container into an endless restart loop.
- **Remediation**: Added `cryptography>=42.0.0` to `mary-api-fastapi/requirements.txt` and rebuilt the backend container.

### B. Daily Time Record (DTR) Expand/Collapse Fix
- **Symptom**: In `DailyTimeRecord.vue`, clicking the **Expand All Rows** (`FolderOpened`) and **Collapse All Rows** (`Folder`) action buttons had no effect on the table.
- **Root-Cause Analysis**:
  1. *Missing Reactive Reference*: The template declared `ref="dtrTableRef"` on `<el-table>`, but `const dtrTableRef = ref(null)` was never declared in `<script setup>`. Calling `dtrTableRef.value` caused an unhandled `ReferenceError`.
  2. *Imperative vs. Declarative Conflict*: The original logic only attempted imperative row expansion on the current page slice (`paginatedDtrList`) without reactive state tracking.
  3. *Lifecycle Desynchronization*: When users filtered by name, typed search queries, changed pagination pages, or refreshed data (`fetchDTR`), new row objects were created, immediately resetting all row expansions.
- **Remediation**:
  1. Declared `const dtrTableRef = ref(null)` and reactive state `expandedRowKeys = ref([])` and `isAllExpanded = ref(false)`.
  2. Bound `:expand-row-keys="expandedRowKeys"` and `@expand-change="handleExpandChange"` directly on `<el-table>`.
  3. Bound `filteredDtrList.value.map(row => row.id)` when `expandAll()` is clicked, keeping all records expanded across pages.
  4. Added a reactive `watch(paginatedDtrList)` and re-sync in `fetchDTR()` so that if `isAllExpanded` is true, newly filtered, paginated, or reloaded rows automatically expand upon rendering.

### C. API Security Architecture & Vulnerability Mitigation
- **Symptom / Critical Gap Identified**:
  1. *Authentication Bypass in `/me`*: `auth.py` contained a development fallback that, upon receiving any invalid or unrecognized token, fetched the first active administrator from the database and returned it with HTTP 200, effectively granting admin privileges to arbitrary tokens.
  2. *Unauthenticated Endpoints*: Key domain routers—including `/audit/logs` (UK GDPR Article 9 Special Category audit trails), `/getsu` (patient dossiers and care notes), `/getpayrolls`, and `/attendances`—lacked authentication dependencies, permitting anonymous access.
  3. *Insecure Account Modification*: `/updateaccount/{user_id}` did not verify whether the authenticated user owned the account or had administrator privileges.
- **Remediation**:
  1. Created centralized security module `app/core/security.py` featuring `get_current_user`, `get_current_active_user`, and `get_current_admin_user`.
  2. Replaced the `/me` fallback with strict bearer token validation, rejecting unauthenticated requests with HTTP 401.
  3. Enforced `dependencies=[Depends(get_current_active_user)]` on all protected routers in `app/api/v1/api.py`.
  4. Restricted `GET /audit/logs` strictly to administrators (`get_current_admin_user`).
  5. Implemented owner/admin authorization checks on `/updateaccount/{user_id}` (HTTP 403 Forbidden for unauthorized modifications).

---

## 3. Authentication & Authorization Architecture

### A. Token Generation, Validation & Lifecycle
- **Token Generation**: Upon successful authentication at `POST /api/v1/login`, the backend issues a high-entropy cryptographically secure token (`mary_tok_<48-hex-chars>`) generated via Python's `secrets.token_hex(24)`.
- **Session Registry (`ACTIVE_SESSIONS`)**: Tokens are cached with metadata:
  ```json
  {
    "user_id": 5,
    "user": { ... },
    "created_at": "2026-10-12T23:42:00"
  }
  ```
- **Lifecycle & Expiration (TTL)**: Tokens carry an expiration window configured via `ACCESS_TOKEN_EXPIRE_MINUTES` (default: 7 days). Expired tokens are purged and trigger HTTP `401 Unauthorized` (`Session has expired. Please log in again.`).
- **JWT Support**: `app/core/security.py` also supports decoding cryptographically signed JWTs using HMAC-SHA256 (`HS256`) and `SECRET_KEY`.
- **Session Revocation**: `POST /api/v1/logout` revokes the token immediately by popping it from the registry.

### B. Cryptography & Password Security
- **Password Hashing**: Implemented using `bcrypt` with work factor 12 (`bcrypt.gensalt(12)`).
- **Legacy Hash Compatibility**: Supports legacy hashes (`$2y$` and `$2b$`) with dynamic hash normalization for backwards compatibility.
- **Database Handshake Encryption**: `cryptography` package provides RSA key exchange for `caching_sha2_password` during TLS/SSL MySQL connection establishment.

### C. Role-Based Access Control (RBAC)
- **Role 1 (Administrator)**: Unrestricted access to master data, carers, service users, scheduling, attendance, finance/payroll/invoices, and UK GDPR Article 9 regulatory audit trails (`GET /audit/logs`).
- **Role 4 / Carer**: Access to care planner, assigned visits, attendance clocking, and client care notes. Access to admin-only logs or other user profiles is blocked (HTTP 403 Forbidden).

---

## 4. API Security Specifications

### Summary of Endpoint Access Controls

| Endpoint | Method | Access Level | Description |
| :--- | :---: | :---: | :--- |
| `/api/v1/login` | POST | **Public** | Authenticate with username/email and password |
| `/api/v1/forgot-password` | POST | **Public** | Request password reset token via email |
| `/api/v1/reset-password` | POST | **Public** | Reset password with token |
| `/healthz` | GET | **Public** | System health verification |
| `/api/v1/me` | GET | **Authenticated** | Returns authenticated profile (401 if missing/invalid) |
| `/api/v1/logout` | POST | **Authenticated** | Revokes active bearer session |
| `/api/v1/updateaccount/{id}` | POST | **Owner or Admin** | Modify user account profile & credentials |
| `/api/v1/getsu` | GET | **Authenticated** | List service users / clients |
| `/api/v1/service_users/{id}/dossier` | GET | **Authenticated** | Medical dossier (Article 9 Special Category Data) |
| `/api/v1/attendances/report` | POST | **Authenticated** | Fetch DTR shifts and attendance records |
| `/api/v1/getpayrolls` | GET | **Authenticated** | Payroll records and summary |
| `/api/v1/getinvoices` | GET | **Authenticated** | Client invoicing data |
| `/api/v1/audit/logs` | GET | **Admin Only** | UK GDPR Article 9 inspection audit log |
| `/api/v1/audit/log` | POST | **Authenticated** | Record UI READ/VIEW access audit event |

---

## 5. Environment Configuration & Variables

Key environment variables configured in `docker-compose.yml` or `.env`:

| Variable | Description | Example / Default |
| :--- | :--- | :--- |
| `DATABASE_URL` | Async database connection string | `mysql+aiomysql://mary_admin:pass@host.docker.internal:3306/mary_api_db_new` |
| `REDIS_URL` | Redis connection URL | `redis://redis:6379/0` |
| `SECRET_KEY` | Cryptographic secret for tokens/JWT | `supersecretjwtkey_change_in_production` |
| `ALGORITHM` | Token signing algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Session validity duration | `10080` (7 days) |
| `PUBLIC_BASE_URL` | Site address written into the password-reset link | `http://127.0.0.1:8080` |
| `SMTP_HOST` | Mail host for the reset message. Implicit TLS only | `send.one.com` |
| `SMTP_PORT` | Port for that implicit TLS connection | `465` |
| `SMTP_USER` | Mailbox username. Empty skips sending | |
| `SMTP_PASSWORD` | Mailbox password. Empty skips sending | |
| `SMTP_FROM` | Sender address. Falls back to `SMTP_USER` | |

The mailbox requirements are in [Forgot Password Email](#9-forgot-password-email).

---

## 6. Docker Deployment & Operational Guide

### Prerequisites
- Docker Engine 24+ and Docker Compose v2+
- MySQL 8.0+ running on host (listening on port 3306)

### Clean Build and Launch
```powershell
# Navigate to project root
cd C:\Projects\Mary

# Build and start all services in detached mode
docker compose up -d --build

# Verify container status
docker compose ps
```

For this `mary-v2` folder, run the same compose command from `C:\Projects\Mary\mary-v2`. The service names in that compose file are `frontend`, `backend`, `redis`, and `proxy`. See [DEPLOYMENT.md](DEPLOYMENT.md).

### Expected Service Status
```text
NAME            IMAGE           STATUS          PORTS
mary_frontend   mary-frontend   Up              0.0.0.0:8080->80/tcp
mary_backend    mary-backend    Up              0.0.0.0:8000->8000/tcp
mary_db         postgres:16     Up              5432/tcp
mary_redis      redis:7-alpine  Up              6379/tcp
```

### Access Points
- **Web Application**: [http://localhost:8080](http://localhost:8080)
- **API Health Check**: [http://localhost:8080/healthz](http://localhost:8080/healthz)
- **Interactive API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 7. Docker Troubleshooting Guide

1. **Backend container enters restart loop (`Restarting ...`)**:
   - Inspect container logs: `docker logs mary_backend`
   - Verify MySQL is running on host: `Test-NetConnection -ComputerName localhost -Port 3306`
   - Ensure `host.docker.internal:host-gateway` is present in `extra_hosts` in `docker-compose.yml`.
   - Ensure `cryptography>=42.0.0` is present in `mary-api-fastapi/requirements.txt`.

2. **Frontend returns 502 Bad Gateway**:
   - Verify backend is alive: `docker exec mary_frontend wget -qO- http://backend:8000/healthz`
   - Check Nginx error logs: `docker logs mary_frontend`

3. **Rebuilding a single container after code edits**:
   ```powershell
   # Rebuild backend only:
   docker compose up -d --build backend

   # Rebuild frontend only:
   docker compose up -d --build frontend
   ```

4. **Password reset says a link was sent, and no email arrives**:
   - Confirm `SMTP_USER` and `SMTP_PASSWORD` are set, and `SMTP_PORT` is `465`.
   - Confirm `PUBLIC_BASE_URL` is the address the recipient can open.
   - Recreate the backend after changing `.env`.
   - Read the backend log for `SMTP is not configured` or `Password reset email was not sent`.

---

## 8. Automated Verification & Test Execution

### Backend Auth Flow Verification
Run the end-to-end authentication test suite inside the container:
```powershell
docker exec mary_backend python test_auth_flow.py
```
**Expected Output**:
```text
Testing forgot-password... -> 200 OK
Testing reset-password...  -> 200 OK
Testing login with new password... -> 200 OK (Token issued)
Testing /me with bearer token...   -> 200 OK (Authenticated user profile)
Testing /me without token...       -> 401 Unauthorized (Missing token)
Testing update account...          -> 200 OK (Account updated)
```

### Security Guard Verification
Execute PowerShell verification against protected endpoints:
```powershell
# 1. Anonymous access must return 401
try { Invoke-RestMethod "http://localhost:8080/api/v1/getsu" } catch { $_.Exception.Response.StatusCode.value__ } # 401
try { Invoke-RestMethod "http://localhost:8080/api/v1/audit/logs" } catch { $_.Exception.Response.StatusCode.value__ } # 401

# 2. Fake token access must return 401
try { Invoke-RestMethod "http://localhost:8080/api/v1/me" -Headers @{ Authorization = "Bearer invalid" } } catch { $_.Exception.Response.StatusCode.value__ } # 401
```

---

## 9. Forgot Password Email

The sign-in page, the reset page, `/forgot-password`, `/reset-password`, and the `password_reset_tokens` table are already in place. On the development database that table has `email` (varchar 255), `token` (varchar 255), and `created_at`. The development environment already has `SMTP_HOST`, port `465`, and `PUBLIC_BASE_URL`. `SMTP_USER`, `SMTP_PASSWORD`, and `SMTP_FROM` are empty until the mailbox password is set, so no message is sent.

The API answers every request with "If the email is registered, a password reset link has been sent." It uses that same sentence when the address is unknown and when mail was not sent. A failed send is written to the backend log.

Set the values in `.env` for development, or in `.env.production` for the droplet. The names are in the matching example file. Recreate the backend container after changing them. Do not commit either env file.

| Setting | Required | What to provide |
| --- | --- | --- |
| `SMTP_HOST` | Yes | Host that accepts implicit TLS. The default is `send.one.com`. |
| `SMTP_PORT` | Yes | Port for that implicit TLS connection. The default is `465`. |
| `SMTP_USER` | Yes | Mailbox username used to log in. |
| `SMTP_PASSWORD` | Yes | Mailbox password. An empty value skips sending. |
| `SMTP_FROM` | No | Address shown as the sender. When this is empty, the message uses `SMTP_USER`. |
| `PUBLIC_BASE_URL` | Yes | Site address written into the link, with no path on the end. Development example: `http://127.0.0.1:8080`. Production must be the public `https://` address of the site. An empty value skips sending. |

The mail code connects with `SMTP_SSL` only. A mailbox that expects port 587 and STARTTLS will not receive a message from this application.

The address typed on **Forgot Password?** must match `users.email` on an account that has not been deleted. A username is not looked up. The link is `{PUBLIC_BASE_URL}/reset-password?token=...&email=...`. It expires after 60 minutes. The new password must be at least 8 characters and must match the confirmation. Each address and each source address can request a link five times in 15 minutes.

Production startup refuses to run when `SMTP_USER` or `SMTP_PASSWORD` is empty, and it requires `PUBLIC_BASE_URL` to begin with `https://`.

`password_reset_tokens` is not one of the tables SQLAlchemy creates on startup. This database already has it. A new empty database needs that table, with those three columns, before a reset link can be stored.
