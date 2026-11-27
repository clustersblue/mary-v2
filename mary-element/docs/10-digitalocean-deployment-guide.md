> **Superseded.** Use [DEPLOYMENT.md](../../../DEPLOYMENT.md) at the `mary-v2` root. This guide names repositories, Alembic commands, and folder paths that are not in this tree.

# Mary Care Management System — DigitalOcean Production Deployment Guide (Docker & Docker Compose)

**Document File:** `docs/10-digitalocean-deployment-guide.md`  
**Target Infrastructure:** DigitalOcean Cloud (Droplets, Managed MySQL, Spaces Object Storage)  
**Deployment Model:** Containerized Architecture via **Docker & Docker Compose** (Full Dev-Prod Parity)  
**Operating System:** Ubuntu 24.04 LTS (Noble Numbat)  
**Target Audience:** DevOps Engineers, System Administrators, Cloud Architects  
**Version:** 2.0.0 Containerized Production  
**Date:** October 2026  

---

## 1. Architectural Overview & Container Topology

The production environment on DigitalOcean mirrors the local development setup, deploying both the frontend and backend as containerized services orchestrated by **Docker Compose**. This guarantees strict development-to-production parity and eliminates environmental drift (such as library version mismatches or missing system C dependencies like WeasyPrint libraries).

```mermaid
graph TD
    DNS["DNS Registrar (*.stmarysteamcare.co.uk)"] --> LB["DigitalOcean Droplet Firewall (Ports 80 & 443)"]
    
    subgraph Droplet Infrastructure ["Ubuntu 24.04 LTS Droplet (4 GB RAM / 2 vCPUs)"]
        UFW["UFW Firewall (Allow 22, 80, 443)"]
        EdgeNginx["Host Nginx Reverse Proxy (:80 / :443 TLS)<br/>Let's Encrypt Certbot SSL Termination"]
        
        subgraph DockerBridge ["Docker Virtual Network (mary_default)"]
            FrontCont["mary_frontend (Nginx + Vue 3 SPA Container)<br/>Port 8080:80"]
            BackCont["mary_backend (Python 3.12 / FastAPI + WeasyPrint)<br/>Port 8000:8000"]
            RedisCont["mary_redis (Redis 7 Alpine Cache)<br/>Port 6379:6379"]
        end
        
        HostStorage["Host Persistent Storage<br/>/var/mary/storage"] -->|Mounted Volume| BackCont
    end
    
    EdgeNginx -->|Proxy Pass http://127.0.0.1:8080| FrontCont
    EdgeNginx -->|Proxy Pass http://127.0.0.1:8000| BackCont
    BackCont -->|Async Pool TLS :25060| DOMySQL[("DigitalOcean Managed MySQL 8.0<br/>High Availability & Daily Backups")]
    BackCont -->|Session Cache| RedisCont
    BackCont -.->|s3cmd / S3 API| DOSpaces[("DO Spaces (S3 Object Storage)<br/>Offsite Backups & Care Plan Archives")]
```

### 1.1 Droplet Sizing & Resource Allocation

| Deployment Scale | Monthly Care Visits | Recommended Droplet Spec | Managed Database Spec | Estimated Cost |
| :--- | :--- | :--- | :--- | :--- |
| **Standard Agency** | Up to 15,000 | Basic Droplet: 4 GB RAM, 2 AMD vCPUs, 80 GB NVMe | Managed MySQL: 1 GB RAM, 1 vCPU, 15 GB Disk | ~$40 / mo |
| **Mid-Size Agency** | 15,000 – 60,000 | General Purpose: 8 GB RAM, 2 Dedicated vCPUs, 160 GB NVMe | Managed MySQL: 2 GB RAM, 1 vCPU, 30 GB Disk + Standby | ~$95 / mo |
| **Enterprise / Multi-Branch** | 60,000+ | 2x Droplets (4 GB) behind DO Load Balancer | Managed MySQL: 4 GB RAM, 2 vCPUs, 50 GB NVMe | ~$180 / mo |

> [!IMPORTANT]
> **Data Sovereignty Compliance:** When provisioning DigitalOcean resources for UK health and domiciliary care, always select region **London (`LON1`)** to comply strictly with the UK Data Protection Act 2018 and UK GDPR Article 9.

---

## 2. Server Provisioning & Docker Host Preparation

### Step 2.1: Provision Ubuntu 24.04 LTS Droplet
In the DigitalOcean Control Panel:
1. Select **Ubuntu 24.04 LTS x64**.
2. Select **London (LON1)** datacenter region.
3. Choose Droplet Size: Minimum **4 GB RAM / 2 vCPUs**.
4. Configure SSH Key authentication (e.g., `id_ed25519.pub`).

### Step 2.2: Initial SSH Connection & User Hardening
Connect to the Droplet:
```bash
ssh root@<DROPLET_PUBLIC_IP>
```

Create a non-root administrative deploy user (`maryadmin`):
```bash
adduser maryadmin
usermod -aG sudo maryadmin

# Copy authorized SSH keys
rsync --archive --chown=maryadmin:maryadmin ~/.ssh /home/maryadmin
```

Harden SSH configuration by editing `/etc/ssh/sshd_config.d/99-hardening.conf`:
```text
PermitRootLogin no
PasswordAuthentication no
X11Forwarding no
MaxAuthTries 3
```
Restart SSH service:
```bash
systemctl restart ssh
```

### Step 2.3: Configure Host UFW Firewall
Allow only SSH, HTTP, and HTTPS on the Droplet host:
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp comment 'SSH'
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'
sudo ufw enable
```

### Step 2.4: Install Official Docker Engine & Docker Compose Plugin
Install Docker using the official Docker repository for Ubuntu 24.04:
```bash
# Update package index and install prerequisites
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release

# Add Docker's official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add Docker repository to Apt sources
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine, CLI, Containerd, and Docker Compose Plugin
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add maryadmin to docker group to run docker without sudo
sudo usermod -aG docker maryadmin
```

Verify Docker installation:
```bash
docker --version
docker compose version
```

---

## 3. Production Docker Compose Configuration

The codebase structure in production contains:
- `docker-compose.prod.yml`: Production container definitions.
- `.env.production`: Production environment variables and secrets.
- `mary-api-fastapi/Dockerfile`: Multi-stage Python 3.12-slim backend with WeasyPrint C libraries.
- `mary-view-element/Dockerfile`: Multi-stage Node 20 build -> Nginx Alpine SPA server.

### 3.1 Production `docker-compose.prod.yml`
Create or configure `/var/mary/docker-compose.prod.yml`:

```yaml
services:
  # ==========================================
  # Frontend Service (Vue 3 + Element Plus SPA)
  # ==========================================
  frontend:
    build:
      context: ./mary-view-element
      dockerfile: Dockerfile
    container_name: mary_frontend
    ports:
      - "127.0.0.1:8080:80"
    restart: always
    environment:
      - NODE_ENV=production
    depends_on:
      backend:
        condition: service_healthy
    networks:
      - mary_internal_network
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M

  # ==========================================
  # Backend Service (FastAPI + Async SQLAlchemy)
  # ==========================================
  backend:
    build:
      context: ./mary-api-fastapi
      dockerfile: Dockerfile
    container_name: mary_backend
    restart: always
    env_file:
      - .env.production
    ports:
      - "127.0.0.1:8000:8000"
    volumes:
      - /var/mary/storage:/app/storage
      - /var/mary/certs/ca-certificate.crt:/etc/ssl/certs/do-mysql-ca.crt:ro
    networks:
      - mary_internal_network
    depends_on:
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 20s
    deploy:
      resources:
        limits:
          cpus: '1.5'
          memory: 1536M

  # ==========================================
  # Cache & Session Store (Redis 7 Alpine)
  # ==========================================
  redis:
    image: redis:7-alpine
    container_name: mary_redis
    restart: always
    command: ["redis-server", "--appendonly", "yes", "--requirepass", "${REDIS_PASSWORD}"]
    volumes:
      - redis_data:/data
    networks:
      - mary_internal_network
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 256M

networks:
  mary_internal_network:
    driver: bridge

volumes:
  redis_data:
    driver: local
```

### 3.2 Production `.env.production` Environment File
Create `/var/mary/.env.production` (permissions `600`):

```env
# Application Metadata
PROJECT_NAME="Mary Care Management System"
VERSION="1.0.0"
API_V1_STR="/api/v1"
ENVIRONMENT="production"

# Cryptographic Security (Generate with: openssl rand -hex 32)
SECRET_KEY="replace-with-openssl-rand-hex-32"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# DigitalOcean Managed MySQL Database URL (with SSL Certificate)
DATABASE_URL="mysql+aiomysql://doadmin:REPLACE_WITH_DATABASE_PASSWORD@db-mysql-lon1-do-user-1234.b.db.ondigitalocean.com:25060/mary_api_db_new?ssl_ca=/etc/ssl/certs/do-mysql-ca.crt"

# Internal Redis Container URL
REDIS_PASSWORD="STRONG_REDIS_PASSWORD_HERE"
REDIS_URL="redis://:STRONG_REDIS_PASSWORD_HERE@redis:6379/0"

# Persistent Storage Path
STORAGE_PATH="/app/storage"

# CORS Origin Allowed Domains
CORS_ORIGINS=["https://app.stmarysteamcare.co.uk","https://api.stmarysteamcare.co.uk"]
```

Secure the environment file:
```bash
sudo chmod 600 /var/mary/.env.production
sudo chown maryadmin:maryadmin /var/mary/.env.production
```

---

## 4. Deploying the Application via Docker Compose

### Step 4.1: Clone Repositories onto the Droplet
```bash
sudo mkdir -p /var/mary/storage /var/mary/certs
sudo chown -R maryadmin:maryadmin /var/mary

cd /var/mary
git clone https://github.com/stmarys/mary-api-fastapi.git
git clone https://github.com/stmarys/mary-view-element.git
```

Copy your DigitalOcean Managed MySQL CA Certificate (`ca-certificate.crt`) into `/var/mary/certs/ca-certificate.crt`.

### Step 4.2: Build and Launch Containers
Execute the Docker Compose build and start command:
```bash
cd /var/mary
docker compose -f docker-compose.prod.yml up -d --build
```

### Step 4.3: Verify Running Containers & Health
```bash
docker compose -f docker-compose.prod.yml ps
```
Output should show all containers running and healthy:
```text
NAME            IMAGE                        COMMAND                  SERVICE    STATUS
mary_backend    mary-backend:latest          "uvicorn main:app..."    backend    running (healthy)
mary_frontend   mary-frontend:latest         "nginx -g 'daemon..."    frontend   running
mary_redis      redis:7-alpine               "docker-entrypoint..."   redis      running
```

### Step 4.4: Run Database Migrations Inside Container
Execute Alembic migrations directly inside the running backend container:
```bash
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

---

## 5. Host Nginx Reverse Proxy & Let's Encrypt SSL

While the frontend container has internal Nginx for static SPA files, the Droplet host's Nginx terminates SSL (port 443), handles domain routing, injects HTTP security headers, and enforces rate-limiting.

### Step 5.1: Install Host Nginx & Certbot
```bash
sudo apt-get install -y nginx certbot python3-certbot-nginx
```

### Step 5.2: Configure Host Nginx
Create `/etc/nginx/sites-available/mary`:

```nginx
# Rate Limiting Zone: 5 requests per minute on login attempts
limit_req_zone $binary_remote_addr zone=login_limit:10m rate=5r/m;

# 1. HTTP -> HTTPS Redirect
server {
    listen 80;
    listen [::]:80;
    server_name app.stmarysteamcare.co.uk api.stmarysteamcare.co.uk;

    location / {
        return 301 https://$host$request_uri;
    }
}

# 2. Main Production HTTPS Server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name app.stmarysteamcare.co.uk;

    # SSL Certificates (provisioned by Certbot)
    ssl_certificate /etc/letsencrypt/live/app.stmarysteamcare.co.uk/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/app.stmarysteamcare.co.uk/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self' https: data: blob: 'unsafe-inline' 'unsafe-eval';" always;

    client_max_body_size 25M;

    # 1. Route Frontend SPA requests to Docker frontend container (:8080)
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 2. Route API calls directly to Docker backend container (:8000)
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }

    # 3. Anti-Brute-Force Rate Limiting on Login Endpoint
    location /api/v1/login {
        limit_req zone=login_limit burst=5 nodelay;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 4. Health Check Endpoint
    location /healthz {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }
}
```

Enable site configuration:
```bash
sudo ln -s /etc/nginx/sites-available/mary /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

### Step 5.3: Obtain Free SSL Certificates via Certbot
```bash
sudo certbot --nginx -d app.stmarysteamcare.co.uk -d api.stmarysteamcare.co.uk
```
Verify automatic renewal timer:
```bash
sudo systemctl status certbot.timer
sudo certbot renew --dry-run
```

---

## 6. DigitalOcean Spaces Backup Strategy

### Step 6.1: Configure S3 Object Storage (`s3cmd`)
Install and configure `s3cmd` to connect to London DO Spaces (`lon1.digitaloceanspaces.com`):
```bash
sudo apt-get install -y s3cmd
s3cmd --configure
```

### Step 6.2: Automated Nightly Backup Script
Create `/usr/local/bin/mary-backup.sh`:

```bash
#!/bin/bash
set -e

DATE=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="/tmp/mary_backups"
DB_FILE="mary_db_${DATE}.sql.gz"
STORAGE_FILE="mary_storage_${DATE}.tar.gz"

mkdir -p $BACKUP_DIR

echo "[$(date)] Starting Mary backup to DigitalOcean Spaces..."

# 1. Dump database via Managed MySQL host
mysqldump -u doadmin -p'REPLACE_WITH_DATABASE_PASSWORD' \
    -h db-mysql-lon1-do-user-1234.b.db.ondigitalocean.com \
    -P 25060 \
    --ssl-ca=/var/mary/certs/ca-certificate.crt \
    --single-transaction \
    --quick \
    mary_api_db_new | gzip -9 > ${BACKUP_DIR}/${DB_FILE}

# 2. Archive persistent storage files (Care Plans, SAR Exports, Logs)
tar -czf ${BACKUP_DIR}/${STORAGE_FILE} -C /var/mary/storage .

# 3. Upload to DO Spaces bucket
s3cmd put ${BACKUP_DIR}/${DB_FILE} s3://mary-care-backups/database/${DB_FILE}
s3cmd put ${BACKUP_DIR}/${STORAGE_FILE} s3://mary-care-backups/storage/${STORAGE_FILE}

# 4. Clean local temporary files
rm -f ${BACKUP_DIR}/${DB_FILE} ${BACKUP_DIR}/${STORAGE_FILE}

echo "[$(date)] Backup completed successfully."
```

Make executable and register in crontab:
```bash
sudo chmod +x /usr/local/bin/mary-backup.sh

# Add to crontab: runs every morning at 02:00 UTC
(sudo crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/mary-backup.sh >> /var/log/mary_backup.log 2>&1") | sudo crontab -
```

---

## 7. Zero-Downtime Deployment & Container Rollout

Deploying new versions of the application is executed using Docker Compose rolling image builds:

### Step 7.1: Automated Deployment Script (`/var/mary/deploy.sh`)
Create `/var/mary/deploy.sh`:

```bash
#!/bin/bash
set -e

echo "=== 1. Pulling Latest Codebase ==="
cd /var/mary/mary-api-fastapi && git pull origin main
cd /var/mary/mary-view-element && git pull origin main
cd /var/mary

echo "=== 2. Building Updated Container Images ==="
docker compose -f docker-compose.prod.yml build

echo "=== 3. Applying Database Migrations ==="
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head

echo "=== 4. Recreating Containers With Zero-Downtime ==="
docker compose -f docker-compose.prod.yml up -d --no-deps backend
docker compose -f docker-compose.prod.yml up -d --no-deps frontend

echo "=== 5. Cleaning Dangling Images ==="
docker image prune -f

echo "=== 6. Validating Deployment Health ==="
sleep 5
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://app.stmarysteamcare.co.uk/healthz)

if [ "$HTTP_STATUS" -eq 200 ]; then
    echo "Deployment SUCCESSFUL: Application is healthy (HTTP 200)."
else
    echo "Deployment ERROR: Health check returned HTTP $HTTP_STATUS!"
    exit 1
fi
```

Make executable:
```bash
chmod +x /var/mary/deploy.sh
```

Execute a deployment simply with:
```bash
cd /var/mary && ./deploy.sh
```

---

## 8. Container Operations & Monitoring Reference

### 8.1 Essential Docker Commands for Operations

| Administrative Task | Command |
| :--- | :--- |
| **Inspect Container Status** | `docker compose -f docker-compose.prod.yml ps` |
| **Follow Live Backend Logs** | `docker compose -f docker-compose.prod.yml logs -f backend` |
| **Follow Live Frontend Logs** | `docker compose -f docker-compose.prod.yml logs -f frontend` |
| **Inspect Container CPU & RAM** | `docker stats` |
| **Restart Backend Container** | `docker compose -f docker-compose.prod.yml restart backend` |
| **Restart Frontend Container** | `docker compose -f docker-compose.prod.yml restart frontend` |
| **Open Interactive Shell in Backend** | `docker compose -f docker-compose.prod.yml exec backend bash` |
| **Check MySQL Connection in Container** | `docker compose -f docker-compose.prod.yml exec backend python -c "import asyncio, app.core.database as d; asyncio.run(d.check_db_health())"` |

---

## 9. Rollback Protocol

If a release causes critical errors or fails health checks:

```bash
#!/bin/bash
# Revert git commit tags
cd /var/mary/mary-api-fastapi && git checkout tags/v1.0.0
cd /var/mary/mary-view-element && git checkout tags/v1.0.0
cd /var/mary

# Downgrade database schema if needed
docker compose -f docker-compose.prod.yml run --rm backend alembic downgrade -1

# Rebuild and relaunch previous stable containers
docker compose -f docker-compose.prod.yml up -d --build

echo "Rollback to v1.0.0 complete."
```
