> **Superseded.** Use [DEPLOYMENT.md](../../../DEPLOYMENT.md) at the `mary-v2` root. Do not apply the passwords or Compose layout in this file.

# Mary Care Management System — Container Deployment Guide

**Document File:** `docs/16-container-deployment-guide.md`
**Target Audience:** Developers deploying a Windows workstation, and operators deploying a DigitalOcean Droplet plus Managed MySQL
**Covers:** `mary_frontend`, `mary_backend`, `mary_redis`, `mary_db`, and the MySQL database the API uses
**Version:** 1.0.0
**Date:** November 2026

This guide starts from an empty machine. Part A is a Windows development PC. Part B is a DigitalOcean Droplet for the application containers and a DigitalOcean Managed MySQL database for care data.

The source layout on disk is:

```text
C:\Projects\Mary\
  docker-compose.yml
  mary-fastapi\          API image for mary_backend
  mary-element\          UI image for mary_frontend
```

`docker-compose.yml` is the Windows development stack. Production uses a separate file, `/var/mary/docker-compose.prod.yml`, created in Part B.

---

## 1. The four containers

| Container | Compose service | Image | What it serves |
| :--- | :--- | :--- | :--- |
| `mary_frontend` | `frontend` | Built from `mary-element/Dockerfile` | Vue 3 app on Nginx. Host port **8080** maps to container port 80. Nginx forwards `/api/` and `/healthz` to `mary_backend`. |
| `mary_backend` | `backend` | Built from `mary-fastapi/Dockerfile` | FastAPI on Uvicorn, port **8000**. On startup it runs `Base.metadata.create_all` and creates any missing tables. |
| `mary_redis` | `redis` | `redis:7-alpine` | Session store. The API uses `REDIS_URL`, default `redis://redis:6379/0`. If Redis is down, that process keeps sessions in memory until it restarts. |
| `mary_db` | `db` | `postgres:16-alpine` | Postgres started by the development Compose file. Database name `mary_db`, user `mary_user`, password `mary_password`. Data volume `postgres_data`. |

`mary_backend` connects with `DATABASE_URL`. That URL is MySQL through the `aiomysql` driver. The development default in `docker-compose.yml` is:

```text
mysql+aiomysql://mary_admin:set-a-local-password@host.docker.internal:3306/mary_api_db_new
```

On a Windows PC, that MySQL server is installed on the PC. On DigitalOcean, that MySQL server is a Managed Database in the London region. The Postgres container `mary_db` still starts with the development Compose file, because `mary_backend` lists it under `depends_on`. Care records live in MySQL.

Startup creates tables. It does not load staff, clients, or lookup rows. Restore a MySQL dump when the new host must keep the current data.

---

## Part A — Windows development machine

### A1. Install the tools

1. Install [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/) and leave it running. The engine needs to be in the "running" state before any `docker` command.
2. Install MySQL Server 8.0 and add the MySQL `bin` directory to `PATH` so `mysql` and `mysqldump` open in PowerShell.
3. Confirm the tools:

```powershell
docker version
docker compose version
mysql --version
```

### A2. Confirm the project folders

From PowerShell:

```powershell
cd C:\Projects\Mary
dir mary-fastapi\Dockerfile
dir mary-element\Dockerfile
dir docker-compose.yml
```

Each command must find a file. The Compose build contexts are `./mary-fastapi` and `./mary-element`.

### A3. Create the MySQL database the API uses

Open a MySQL prompt as an administrator (`mysql -u root -p`) and run:

```sql
CREATE DATABASE IF NOT EXISTS mary_api_db_new
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'mary_admin'@'%' IDENTIFIED BY 'set-a-local-password';
GRANT ALL PRIVILEGES ON mary_api_db_new.* TO 'mary_admin'@'%';
FLUSH PRIVILEGES;
```

`mary_admin`@`%` is required because `mary_backend` connects through `host.docker.internal`, which arrives from the Docker network.

Allow MySQL through Windows Firewall on private networks if a container connection is refused. The server must listen on port **3306**. Check it:

```powershell
Test-NetConnection -ComputerName localhost -Port 3306
```

`TcpTestSucceeded` must be `True`.

To copy an existing database onto this PC, dump it on the old host and import it before the first API start:

```powershell
mysqldump -u root -p --routines --triggers --single-transaction mary_api_db_new > mary_api_db_new.sql
mysql -u mary_admin -p mary_api_db_new < mary_api_db_new.sql
```

### A4. Read the development Compose file

`C:\Projects\Mary\docker-compose.yml` already defines all four containers:

- `mary_frontend` publishes `8080:80` and depends on `backend`.
- `mary_backend` publishes `8000:8000`, adds `host.docker.internal:host-gateway`, mounts `./mary-fastapi/storage` at `/app/storage`, and depends on `db` and `redis`.
- `mary_db` is `postgres:16-alpine` with volume `postgres_data`. No host port is published.
- `mary_redis` is `redis:7-alpine`. No host port is published.

The API environment set by that file is:

```text
DATABASE_URL=mysql+aiomysql://mary_admin:set-a-local-password@host.docker.internal:3306/mary_api_db_new
REDIS_URL=redis://redis:6379/0
SECRET_KEY=set-a-long-random-string
```

These values are for the development PC. Part B replaces them.

### A5. Build and start all four containers

```powershell
cd C:\Projects\Mary
docker compose up -d --build
docker compose ps
```

The first build installs Python packages and the WeasyPrint system libraries in `mary_backend`, and it compiles the Vue app into `mary_frontend`. Wait until `docker compose ps` shows every container as `Up`.

| Name | Expected status | How you reach it |
| :--- | :--- | :--- |
| `mary_backend` | Up | http://localhost:8000 |
| `mary_frontend` | Up | http://localhost:8080 |
| `mary_redis` | Up | Compose network name `redis` only |
| `mary_db` | Up | Compose network only. Postgres, port 5432 inside the container |

`mary_backend` in a restart loop means MySQL rejected the connection during `create_all`. Read the log in step A7.

### A6. Check each service

```powershell
curl http://localhost:8000/healthz
curl http://localhost:8080/healthz
docker exec mary_redis redis-cli ping
docker exec mary_db pg_isready -U mary_user -d mary_db
```

Both health URLs return JSON with `"status": "ok"`. Redis replies `PONG`. `pg_isready` reports that `mary_db` is accepting connections.

Then open:

- Web app: http://localhost:8080
- API docs: http://localhost:8000/docs
- Health through the UI proxy: http://localhost:8080/healthz

Log in with a user from the restored MySQL database. An empty `mary_api_db_new` has tables and no users.

### A7. Logs, rebuild, and stop

```powershell
docker logs mary_backend --tail 80
docker compose logs -f backend

docker compose up -d --build backend
docker compose up -d --build frontend

docker compose down
```

`docker compose down` stops all four containers and keeps the `postgres_data` volume. Generated PDFs and uploads stay in `C:\Projects\Mary\mary-fastapi\storage`.

### A8. When the API will not stay up

| What you see | What to do |
| :--- | :--- |
| `mary_backend` restarts, log says it cannot connect to MySQL | MySQL is stopped, port 3306 is closed, or `mary_admin` cannot connect from Docker. Repeat A3. |
| Log mentions `caching_sha2_password` or the `cryptography` package | Rebuild from the current `mary-fastapi` tree. `requirements.txt` includes `cryptography`. |
| Compose cannot find a Dockerfile | Run the command from `C:\Projects\Mary`, with `mary-fastapi` and `mary-element` beside `docker-compose.yml`. |
| http://localhost:8080 returns 502 | `mary_backend` is down. http://localhost:8000/healthz must succeed first. |
| Login works until a restart, then the token is rejected | `mary_redis` was down, so the session lived only in that process. `docker exec mary_redis redis-cli ping` must return `PONG`. |

---

## Part B — DigitalOcean Droplet and Managed MySQL

Run `mary_frontend`, `mary_backend`, and `mary_redis` on one Ubuntu Droplet. Store care data on a DigitalOcean Managed MySQL 8 database in the same London region. Leave the development Postgres container `mary_db` off the Droplet. The Managed Database is the production database.

Use region **London (LON1)** for the Droplet and the database.

| Piece | Where it runs | Suggested size |
| :--- | :--- | :--- |
| `mary_frontend`, `mary_backend`, `mary_redis` | Ubuntu 24.04 Droplet | 4 GB RAM, 2 vCPUs, 80 GB disk |
| MySQL `mary_api_db_new` | Managed MySQL 8 | 1 GB RAM plan for a first production host |
| `mary_db` (Postgres) | Development Compose only | Do not create this container in production |

### B1. Create the Managed MySQL database

1. In the DigitalOcean control panel, open **Databases** and create a **MySQL 8** cluster.
2. Region: **London (LON1)**.
3. Give the cluster a name you will recognise, for example `mary-mysql`.
4. After it finishes provisioning, open the cluster and create a database named `mary_api_db_new`.
5. Download the **CA certificate**. You will copy it to the Droplet as `/var/mary/certs/ca-certificate.crt`.
6. Record the connection details from the panel. You need the host, port **25060**, the admin user, and the admin password. The host looks like `db-mysql-lon1-xxxxx.b.db.ondigitalocean.com`.

Trusted sources are added in B4, after the Droplet exists. Until then, only your own IP (if you add it) can connect.

### B2. Create the Droplet

1. Create a Droplet with **Ubuntu 24.04 LTS x64**, region **London (LON1)**, at least **4 GB RAM / 2 vCPUs**.
2. Add your SSH public key. Do not enable password login.
3. Note the public IPv4 address. The rest of this guide calls it `<DROPLET_IP>`.

### B3. Prepare the Droplet

```bash
ssh root@<DROPLET_IP>

adduser maryadmin
usermod -aG sudo maryadmin
rsync --archive --chown=maryadmin:maryadmin ~/.ssh /home/maryadmin
```

Write `/etc/ssh/sshd_config.d/99-hardening.conf`:

```text
PermitRootLogin no
PasswordAuthentication no
X11Forwarding no
MaxAuthTries 3
```

```bash
systemctl restart ssh
```

Reconnect as `maryadmin`, then set the host firewall. Publish SSH, HTTP, and HTTPS. Leave 3306, 5432, 6379, and 8000 closed on the public interface.

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp comment 'SSH'
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'
sudo ufw enable
```

Install Docker Engine and the Compose plugin:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker maryadmin
```

Log out and back in so the `docker` group applies, then check:

```bash
docker version
docker compose version
```

### B4. Allow the Droplet to reach MySQL

1. In the database cluster, open **Trusted sources**.
2. Add this Droplet. DigitalOcean then allows the Droplet's network onto port 25060.
3. Keep the database closed to the public internet. Do not add `0.0.0.0/0`.

### B5. Copy the application onto the Droplet

On the Droplet:

```bash
sudo mkdir -p /var/mary/storage /var/mary/certs /var/mary/mary-fastapi /var/mary/mary-element
sudo chown -R maryadmin:maryadmin /var/mary
```

From the Windows PC, copy both projects and the CA certificate. Run this in PowerShell, with the CA file you downloaded in B1:

```powershell
scp -r C:\Projects\Mary\mary-fastapi maryadmin@<DROPLET_IP>:/var/mary/
scp -r C:\Projects\Mary\mary-element maryadmin@<DROPLET_IP>:/var/mary/
scp C:\path\to\ca-certificate.crt maryadmin@<DROPLET_IP>:/var/mary/certs/ca-certificate.crt
```

On the Droplet, confirm the files Docker will build:

```bash
test -f /var/mary/mary-fastapi/Dockerfile && echo backend-ok
test -f /var/mary/mary-element/Dockerfile && echo frontend-ok
test -f /var/mary/certs/ca-certificate.crt && echo ca-ok
```

### B6. Write the production environment file

On the Droplet, create `/var/mary/.env.production`. Replace every placeholder with the values from the Managed Database panel. If the database password contains `@`, `:`, `/`, `#`, or `?`, URL-encode those characters inside `DATABASE_URL`.

Generate a secret on the Droplet:

```bash
openssl rand -hex 32
```

`/var/mary/.env.production`:

```env
PROJECT_NAME=Mary Care Management System
VERSION=1.0.0
API_V1_STR=/api/v1

SECRET_KEY=paste-the-openssl-value-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

DATABASE_URL=mysql+aiomysql://doadmin:URL_ENCODED_PASSWORD@db-mysql-lon1-xxxxx.b.db.ondigitalocean.com:25060/mary_api_db_new?ssl_ca=/etc/ssl/certs/do-mysql-ca.crt

REDIS_PASSWORD=choose-a-long-random-password
REDIS_URL=redis://:choose-a-long-random-password@redis:6379/0
```

Lock the file down:

```bash
chmod 600 /var/mary/.env.production
```

### B7. Write the production Compose file

Create `/var/mary/docker-compose.prod.yml`. This starts `mary_frontend`, `mary_backend`, and `mary_redis`. It does not start `mary_db`.

```yaml
services:
  frontend:
    build:
      context: ./mary-element
      dockerfile: Dockerfile
    container_name: mary_frontend
    ports:
      - "127.0.0.1:8080:80"
    depends_on:
      backend:
        condition: service_started
    restart: always

  backend:
    build:
      context: ./mary-fastapi
      dockerfile: Dockerfile
    container_name: mary_backend
    env_file:
      - .env.production
    ports:
      - "127.0.0.1:8000:8000"
    volumes:
      - /var/mary/storage:/app/storage
      - /var/mary/certs/ca-certificate.crt:/etc/ssl/certs/do-mysql-ca.crt:ro
    depends_on:
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    restart: always

  redis:
    image: redis:7-alpine
    container_name: mary_redis
    command: ["redis-server", "--appendonly", "yes", "--requirepass", "${REDIS_PASSWORD}"]
    volumes:
      - redis_data:/data
    restart: always

volumes:
  redis_data:
```

Ports `8080` and `8000` are bound to `127.0.0.1`. The public site is the host Nginx in B9. Redis has no published port.

`${REDIS_PASSWORD}` is read from `/var/mary/.env.production` when you run Compose from `/var/mary`. The same password is inside `REDIS_URL`.

### B8. Load existing care data, then start the containers

Install the MySQL client on the Droplet:

```bash
sudo apt-get install -y mysql-client
```

From the Windows PC, create the dump (if you did not already):

```powershell
mysqldump -u mary_admin -p --routines --triggers --single-transaction mary_api_db_new > mary_api_db_new.sql
scp .\mary_api_db_new.sql maryadmin@<DROPLET_IP>:/var/mary/mary_api_db_new.sql
```

On the Droplet, import into the Managed Database **before** the first `mary_backend` start. `create_all` on an empty database builds tables, and a later full dump then collides with those tables.

```bash
mysql -h db-mysql-lon1-xxxxx.b.db.ondigitalocean.com \
  -P 25060 \
  -u doadmin -p \
  --ssl-ca=/var/mary/certs/ca-certificate.crt \
  mary_api_db_new < /var/mary/mary_api_db_new.sql
```

Start the three containers:

```bash
cd /var/mary
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
docker compose --env-file .env.production -f docker-compose.prod.yml ps
```

`mary_backend` must reach `healthy`. A restart loop here is a database URL, trusted-source, or CA-path problem. Read:

```bash
docker logs mary_backend --tail 100
```

Check from the Droplet:

```bash
curl -fsS http://127.0.0.1:8000/healthz
curl -fsS http://127.0.0.1:8080/healthz
docker exec mary_redis redis-cli -a "$REDIS_PASSWORD" ping
```

Set `REDIS_PASSWORD` in that shell to the value from `.env.production`, or the `ping` is refused. A correct reply is `PONG`.

There is no `mary_db` container on this host. Confirm that with `docker ps`. The only database that should answer is the Managed MySQL cluster.

### B9. Publish the site with host Nginx and TLS

Point DNS `A` records for the site name at `<DROPLET_IP>` before requesting a certificate. The examples below use `app.stmarysteamcare.co.uk`. Use the name that you actually own.

```bash
sudo apt-get install -y nginx certbot python3-certbot-nginx
```

Create `/etc/nginx/sites-available/mary`:

```nginx
limit_req_zone $binary_remote_addr zone=login_limit:10m rate=5r/m;

server {
    listen 80;
    listen [::]:80;
    server_name app.stmarysteamcare.co.uk;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }

    location /api/v1/login {
        limit_req zone=login_limit burst=5 nodelay;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /healthz {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }
}
```

Enable it and obtain a certificate:

```bash
sudo ln -s /etc/nginx/sites-available/mary /etc/nginx/sites-enabled/mary
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d app.stmarysteamcare.co.uk
```

Certbot adds the HTTPS server and the HTTP redirect. Confirm renewal:

```bash
sudo certbot renew --dry-run
```

From any PC:

```bash
curl -fsS https://app.stmarysteamcare.co.uk/healthz
```

Open `https://app.stmarysteamcare.co.uk` and sign in with a user from the imported database.

### B10. Day-to-day commands on the Droplet

Rebuild after copying new code:

```bash
cd /var/mary
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build backend
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build frontend
```

Logs and a shell:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml logs -f backend
docker compose --env-file .env.production -f docker-compose.prod.yml exec backend bash
```

Stop the application containers:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml down
```

That stops `mary_frontend`, `mary_backend`, and `mary_redis`. It leaves the Managed MySQL cluster running. Uploaded files remain in `/var/mary/storage`.

### B11. Production checks

| Check | Command or place | Expected result |
| :--- | :--- | :--- |
| API on the Droplet | `curl -fsS http://127.0.0.1:8000/healthz` | `"status": "ok"` |
| UI container | `curl -fsS http://127.0.0.1:8080/healthz` | `"status": "ok"` |
| Public site | `curl -fsS https://app.stmarysteamcare.co.uk/healthz` | `"status": "ok"` |
| Redis | `docker exec mary_redis redis-cli -a '<password>' ping` | `PONG` |
| MySQL trusted path | Database panel, Trusted sources | This Droplet is listed |
| Postgres container | `docker ps --filter name=mary_db` | No running container |
| Public ports | DigitalOcean firewall and `ufw status` | 22, 80, 443 only |

---

## 3. How the two environments differ

| | Windows development | DigitalOcean |
| :--- | :--- | :--- |
| Compose file | `C:\Projects\Mary\docker-compose.yml` | `/var/mary/docker-compose.prod.yml` |
| `mary_frontend` | Port 8080 on the PC | 127.0.0.1:8080, then host Nginx on 443 |
| `mary_backend` | Port 8000 on the PC | 127.0.0.1:8000, then host Nginx on 443 |
| `mary_redis` | Open on the Compose network, no password | Same network, `requirepass` set |
| `mary_db` | Postgres 16 container, volume `postgres_data` | Not deployed |
| Database the API uses | MySQL 8 on the Windows PC, port 3306 | Managed MySQL 8 in LON1, port 25060, TLS with the CA file |
| `DATABASE_URL` host | `host.docker.internal` | Managed Database hostname |
| Care data | Restore a dump, or start empty | Import the dump before the first API start |
| File storage | `C:\Projects\Mary\mary-fastapi\storage` | `/var/mary/storage` |

Further production operations (Spaces backups, rollout, and rollback) stay in [10-digitalocean-deployment-guide.md](10-digitalocean-deployment-guide.md). Container restarts and incident steps stay in [11-operations-runbook.md](11-operations-runbook.md).
