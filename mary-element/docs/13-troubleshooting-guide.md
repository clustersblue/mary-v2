# Mary Care Management System — Troubleshooting Guide (Docker & Production)

**Document File:** `docs/13-troubleshooting-guide.md`  
**Target Audience:** L1/L2 Support Engineers, Developers, Operations Personnel  
**Environment:** Docker Compose & Containerized Deployments (DigitalOcean / Local Workstations)  
**Version:** 2.0.0 Production  
**Date:** October 2026  

---

## 1. Quick Diagnostic Flowchart

```mermaid
flowchart TD
    Issue["System Issue Reported"] --> Type{"What is the error symptom?"}
    
    Type -->|Browser Shows 502 Bad Gateway| Nginx["Nginx reverse proxy cannot reach backend (:8000).<br/>See Section 2.1"]
    Type -->|Browser Shows 401 on Every Request| Auth["Token expired or in-memory session cleared.<br/>See Section 2.2"]
    Type -->|Browser Shows 403 Access Denied| RBAC["User role lacks required permissions.<br/>See Section 2.3"]
    Type -->|PDF Generation Fails (500 Error)| PDF["Missing WeasyPrint Cairo/Pango system libraries.<br/>See Section 2.4"]
    Type -->|Database Query Hangs / Connection Refused| DB["MySQL connection pool exhausted or credentials invalid.<br/>See Section 2.5"]
```

---

## 2. Common Issues & Root Cause Resolutions

### 2.1 HTTP 502 Bad Gateway
- **Symptom:** Browser displays standard Nginx 502 error; frontend or API completely unresponsive.
- **Root Cause:** Backend FastAPI service (`mary_backend` container) is stopped, restarting, or unresponsive.
- **Diagnostic Commands (Docker):**
  ```bash
  # Check if backend container is running
  docker compose ps backend
  
  # Inspect container crash traceback
  docker compose logs --tail=50 backend
  ```
- **Resolution:**
  1. Restart the backend container:
     ```bash
     docker compose restart backend
     ```
  2. If the container failed to bind port 8000 on the host due to a zombie process:
     ```bash
     sudo lsof -i :8000
     sudo kill -9 <PID>
     docker compose restart backend
     ```

---

### 2.2 Infinite Redirect Loop to `/login?reason=expired`
- **Symptom:** User logs in successfully, but immediate redirection to `/login?reason=expired` occurs.
- **Root Cause:**
  - Token in browser storage is invalid or expired.
  - Or, in-memory backend session registry was cleared due to container restart while client still retained an old token.
- **Resolution:**
  1. Instruct the user to clear browser application storage (Developer Tools &rarr; Application &rarr; Clear site data).
  2. In production, ensure Redis is configured (`REDIS_URL`) so sessions persist across backend container restarts.

---

### 2.3 HTTP 403 Forbidden ("Account is currently suspended")
- **Symptom:** User credentials are valid, but login fails with `403 Forbidden` and message: `"Account is currently suspended. Please contact your coordinator."`
- **Root Cause:** In the database, the user's `carer_status_id` is set to `5` (Suspended/Inactive).
- **Resolution:**
  1. Verify status in database:
     ```sql
     SELECT id, username, carer_status_id FROM users WHERE username = 'target_user';
     ```
  2. If suspension has been lifted by management, update status back to active (`1`):
     ```sql
     UPDATE users SET carer_status_id = 1 WHERE username = 'target_user';
     ```

---

### 2.4 WeasyPrint PDF Generation Failure (`OSError: cannot load library 'pango-1.0-0'`)
- **Symptom:** Care Notes PDF generation or SAR export returns `500 Internal Server Error`; traceback references missing C shared libraries.
- **Root Cause:**
  - When running inside **Docker**, this issue is prevented because the `mary-api-fastapi/Dockerfile` pre-installs `libpango-1.0-0`, `pango1.0-tools`, `libpangocairo-1.0-0`, `libgdk-pixbuf-2.0-0`, `libffi-dev`, and `shared-mime-info`.
  - If developing natively without Docker, the host OS lacks these C libraries.
- **Resolution:**
  - **Docker Environments:** Rebuild image to ensure base packages are present:
    ```bash
    docker compose build backend
    docker compose up -d backend
    ```
  - **Native Linux Host:**
    ```bash
    sudo apt-get update && sudo apt-get install -y \
        libpango-1.0-0 pango1.0-tools libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 shared-mime-info
    ```
  - **Native Windows Host:** Install GTK3 runtime from [tschoonj/GTK-for-Windows-Runtime-Environment-Installer](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer) and add `C:\Program Files\GTK3-Runtime Win64\bin` to system `PATH`.

---

### 2.5 `aiomysql.OperationalError: (2006, 'MySQL server has gone away')`
- **Symptom:** First request after hours of inactivity fails with database timeout; subsequent requests succeed.
- **Root Cause:** MySQL connection timed out while sitting idle in SQLAlchemy's connection pool.
- **Resolution:**
  Ensure [`app/db/session.py`](file:///c:/Projects/Mary/mary-api-fastapi/app/db/session.py) includes `pool_pre_ping=True` and `pool_recycle=3600`:
  ```python
  engine = create_async_engine(
      settings.DATABASE_URL,
      pool_pre_ping=True,
      pool_recycle=3600
  )
  ```

---

### 2.6 Frontend 404 Not Found on Page Refresh
- **Symptom:** Navigating within the application works smoothly, but refreshing the page on any sub-route (e.g. `https://app.stmarysteamcare.co.uk/planner`) triggers Nginx 404 Not Found.
- **Root Cause:** Nginx is attempting to resolve the URI as a physical file on disk rather than falling back to Vue's `index.html`.
- **Resolution:**
  Inside the containerized frontend, [`mary-view-element/nginx.conf`](file:///c:/Projects/Mary/mary-view-element/nginx.conf) includes the fallback:
  ```nginx
  location / {
      root /usr/share/nginx/html;
      index index.html index.htm;
      try_files $uri $uri/ /index.html;
  }
  ```
  On the host Nginx proxy, ensure the reverse proxy forwards all routes to the frontend container:
  ```nginx
  location / {
      proxy_pass http://127.0.0.1:8080;
  }
  ```

---

### 2.7 Droplet Out of Memory (OOM Killer)
- **Symptom:** Backend container terminates silently during heavy PDF generation or large Excel SAR exports; `docker compose ps` shows `Exited (137)`.
- **Root Cause:** Linux kernel OOM Killer terminated the container when memory usage exceeded the Droplet limit.
- **Resolution:**
  1. Add swap memory on the Ubuntu host:
     ```bash
     sudo fallocate -l 2G /swapfile
     sudo chmod 600 /swapfile
     sudo mkswap /swapfile
     sudo swapon /swapfile
     echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
     ```
  2. Set container memory limits in `docker-compose.prod.yml`:
     ```yaml
     backend:
       deploy:
         resources:
           limits:
             memory: 1536M
     ```
  3. Clean Docker dangling layers: `docker system prune -af`.
