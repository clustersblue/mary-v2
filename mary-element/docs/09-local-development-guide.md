> **Superseded.** Use [DEPLOYMENT.md](../../../DEPLOYMENT.md) at the `mary-v2` root. The commands below refer to folders and secrets that are not the current stack.

# Mary Care Management System — Installation & Local Development Guide

**Document File:** `docs/09-local-development-guide.md`  
**Target Audience:** New Developers, QA Engineers, DevOps Onboarding  
**Goal:** Zero-friction local development environment setup under 20 minutes  
**Version:** 1.0.0 Production  
**Date:** October 2026  

---

## 1. Prerequisites & System Requirements

Ensure the following tools are installed on your host workstation (Windows, macOS, or Linux):

| Tool / Runtime | Minimum Version | Installation Link / Command |
| :--- | :---: | :--- |
| **Git** | `2.40+` | `https://git-scm.com/` |
| **Node.js & npm** | `20.x LTS` | `https://nodejs.org/` |
| **Python** | `3.12.x` | `https://www.python.org/` |
| **Docker & Docker Compose** | `25.x+` / `v2+` | `https://www.docker.com/products/docker-desktop/` |
| **MySQL Server** *(Optional if using Docker)* | `8.0.x` | `https://dev.mysql.com/downloads/mysql/` |

---

## 2. Quickstart Option A: Docker Compose (Recommended)

The easiest method to spin up the entire application stack (Frontend, Backend, Redis, MySQL):

### Step 1: Clone & Navigate to Repository
```bash
git clone https://github.com/stmarys/mary-care-management.git
cd mary-care-management
```

### Step 2: Configure Environment Variables
Create a root `.env` or verify `docker-compose.yml`:
```env
DATABASE_URL=mysql+aiomysql://root:root@host.docker.internal:3306/mary_api_db_new
REDIS_URL=redis://redis:6379/0
SECRET_KEY=local_development_secret_key_change_in_production_123!
```

### Step 3: Launch Containers
```bash
docker compose up -d --build
```

### Step 4: Verify Running Services
```bash
docker compose ps
```
Your local environment is now running:
- **Frontend Web UI:** [http://localhost:8080](http://localhost:8080)
- **FastAPI API Root:** [http://localhost:8000/api/v1](http://localhost:8000/api/v1)
- **Interactive Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Interactive ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 3. Quickstart Option B: Native Bare-Metal Development

If you are developing backend or frontend features natively outside containers:

### 3.1 Backend Setup (`mary-api-fastapi`)

#### 1. Navigate to Backend Directory
```bash
cd C:\Projects\Mary\mary-api-fastapi
```

#### 2. Create and Activate Virtual Environment
- **Windows (PowerShell):**
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
- **Linux / macOS:**
  ```bash
  python3.12 -m venv venv
  source venv/bin/activate
  ```

#### 3. Install System Dependencies (for WeasyPrint PDF Engine)
- **Linux (Ubuntu/Debian):**
  ```bash
  sudo apt-get install -y build-essential libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 shared-mime-info
  ```
- **macOS (Homebrew):**
  ```bash
  brew install pango gdk-pixbuf libffi
  ```
- **Windows:** WeasyPrint works directly or using GTK3 runtime installer for Windows.

#### 4. Install Python Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### 5. Configure Local Backend `.env`
Create `.env` inside `mary-api-fastapi`:
```env
PROJECT_NAME="Mary Care Management System API"
VERSION="1.0.0"
API_V1_STR="/api/v1"
SECRET_KEY="set-a-long-random-string"
DATABASE_URL="mysql+aiomysql://root:root@localhost:3306/mary_api_db_new"
REDIS_URL="redis://localhost:6379/0"
```

#### 6. Start the Backend Development Server
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
The server will start with hot-reload enabled.

---

### 3.2 Frontend Setup (`mary-view-element`)

#### 1. Navigate to Frontend Directory
```bash
cd C:\Projects\Mary\mary-view-element
```

#### 2. Install Node Dependencies
```bash
npm install
```

#### 3. Start Vite Development Server
```bash
npm run dev
```
The Vite development server will start at:
- Local: [http://localhost:3000](http://localhost:3000)

*(Note: In Vite development mode, requests to `/api/v1` are proxied to `http://localhost:8000`).*

---

## 4. Default Seed Accounts for Testing

The local database contains pre-configured test accounts across all roles. Use the password stored for those accounts outside this repository:

| Role | Username | Email | ID | Permissions |
| :--- | :--- | :--- | :---: | :--- |
| **Super Administrator** | `robertor` | `clustersblue@gmail.com` | `5` | Unrestricted full access to all features |
| **Finance Staff** | `bserdena` | `brix.serdena@stmarysteamcare.co.uk` | `46` | Finance, Invoices, Payroll, Rotas |
| **Operations Staff** | `mariam` | `mariasalvacionmorata@gmail.com` | `6` | Rotas, DTR, Clients, Staff (No finance) |
| **Field Carer** | `GemmaAgustin` | `gemmaagustin1978@gmail.com` | `8` | Mobile Carer Attendance Portal only |

---

## 5. Running the Automated Test Suite

To verify system functionality and RBAC enforcement:
```bash
# If running inside Docker:
docker exec mary_backend python /app/test_rbac_parity.py

# If running natively:
python test_rbac_parity.py
```
Expected output:
```text
ALL RBAC PARITY VERIFICATION CHECKS PASSED PERFECTLY!
```

---

## 6. Common Troubleshooting Steps

### 1. `ModuleNotFoundError: No module named 'aiomysql'`
- Ensure your Python virtual environment is activated (`.\venv\Scripts\Activate.ps1`).
- Re-run `pip install -r requirements.txt`.

### 2. `Access Denied for user 'root'@'localhost'` (MySQL connection failure)
- Verify MySQL service is running.
- Check `DATABASE_URL` credentials in `.env`.
- If running backend in Docker and MySQL on Windows host, use `host.docker.internal` instead of `localhost`.

### 3. Vite Frontend Blank Screen / Failed to fetch
- Ensure the backend server is running on `http://localhost:8000`.
- Verify browser console (F12) for CORS or network connection errors.
- Clear `localStorage` in browser dev tools (`localStorage.clear()`) and refresh.

### 4. WeasyPrint `OSError: cannot load library 'pango-1.0-0'`
- On Windows/Mac workstations, ensure Pango/Cairo system libraries are installed or run the backend inside Docker where Debian C libraries are pre-installed.
