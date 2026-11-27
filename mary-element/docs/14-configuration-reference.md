# Mary Care Management System — Configuration Reference

**Document File:** `docs/14-configuration-reference.md`  
**Target Audience:** DevOps Engineers, System Administrators, Security Officers  
**Version:** 1.0.0 Production  
**Date:** October 2026  

---

## 1. Backend Configuration Reference (`mary-api-fastapi`)

Backend settings are managed using Pydantic's `BaseSettings` in [`app/core/config.py`](file:///c:/Projects/Mary/mary-api-fastapi/app/core/config.py). Variables are loaded from `/etc/mary/backend.env` (production) or `.env` (local).

| Variable Name | Type | Default Value (Dev) | Production Recommendation | Security Sensitive | Description |
| :--- | :---: | :--- | :--- | :---: | :--- |
| **`PROJECT_NAME`** | `str` | `"Mary Care Management System API"` | `"Mary Care Management System"` | No | Display title in OpenAPI documentation. |
| **`VERSION`** | `str` | `"1.0.0"` | `"1.0.0"` | No | API version tag. |
| **`API_V1_STR`** | `str` | `"/api/v1"` | `"/api/v1"` | No | Global URL prefix for versioned endpoints. |
| **`SECRET_KEY`** | `str` | `"supersecretjwtkey_change..."` | High-entropy 64+ char random string | **YES** | Cryptographic secret used for signing JWTs. |
| **`ALGORITHM`** | `str` | `"HS256"` | `"HS256"` | No | JWT signing algorithm. |
| **`ACCESS_TOKEN_EXPIRE_MINUTES`** | `int` | `10080` (7 days) | `10080` (7 days) | No | Duration before bearer sessions expire. |
| **`DATABASE_URL`** | `str` | `mysql+aiomysql://root:root@localhost:3306/mary_api_db_new` | `mysql+aiomysql://user:pass@host:25060/db?ssl_ca=...` | **YES** | Async connection string for primary database. |
| **`REDIS_URL`** | `str` | `"redis://localhost:6379/0"` | `"rediss://default:pass@host:25061/0"` | **YES** | Redis connection URI for caching and sessions. |
| **`STORAGE_PATH`** | `str` | `"storage"` | `"/var/mary/storage"` | No | Base directory on disk for PDF/SAR exports. |
| **`SMTP_HOST`** | `str` | `"send.one.com"` | `"send.one.com"` | No | Outbound mail host for password resets. |
| **`SMTP_PORT`** | `int` | `465` | `465` | No | SMTP port (465 for SSL, 587 for TLS). |
| **`SMTP_USER`** | `str` | `"service@stmarysteamcare.co.uk"` | Verified dispatch email address | **YES** | Mail service account credentials. |
| **`SMTP_PASSWORD`** | `str` | Set in `.env` only. Do not commit the value. | Set in the server env file only. | **YES** | Mail service account password. |

---

## 2. Frontend Configuration Reference (`mary-view-element`)

Frontend settings are evaluated at build time via Vite (`.env.production`):

| Variable Name | Type | Default Value (Dev) | Production Value | Description |
| :--- | :---: | :--- | :--- | :--- |
| **`VITE_API_BASE_URL`** | `str` | `"/api/v1"` | `"/api/v1"` | Base URL used by Axios client for API calls. |
| **`VITE_APP_TITLE`** | `str` | `"Mary Care Management System"` | `"Mary Care Management System"` | Page title in browser tabs. |
| **`VITE_SESSION_TIMEOUT_MINS`**| `int` | `60` | `60` | Inactivity timer for automated logout prompt. |

---

## 3. Environment Environments Comparison Matrix

```mermaid
graph LR
    Local["Local Workstation (.env)"] --> Staging["Staging Droplet (/etc/mary/backend.env)"]
    Staging --> Prod["Production Droplet (/etc/mary/backend.env)"]
```

| Configuration Property | Local Development | Staging (Pre-Prod) | Production |
| :--- | :--- | :--- | :--- |
| **Database Host** | `localhost:3306` or `host.docker.internal` | DO Managed MySQL (Staging DB) | DO Managed MySQL (Primary + Standby) |
| **SSL Enforcement** | Disabled (`http://`) | Enabled (`https://staging...`) | Enforced (`https://app...` with HSTS) |
| **CORS Origins** | `allow_origins=["*"]` | Whitelist: `https://staging...` | Whitelist: `https://app.stmarysteamcare.co.uk` |
| **Uvicorn Workers** | `1 worker (--reload)` | `2 workers` | `4 workers (Gunicorn managed)` |
| **Log Verbosity** | `DEBUG` | `INFO` | `WARNING` & `ERROR` |
| **Nightly Backups** | Disabled | Retained for 7 days | Retained for 30 days + Annual Archives |
