# Deployment

The site and the API are one origin. Nginx publishes the only public ports, serves the Vue app, and forwards `/api/` to FastAPI. Redis stays on the Compose network. MySQL stays outside the containers: on the Windows PC for development, and on DigitalOcean Managed MySQL in London for production.

Run these commands from `C:\Projects\Mary\mary-v2` (or `/var/mary` on the droplet). Do not use `C:\Projects\Mary\docker-compose.yml`, `mary-documents\`, or the `Xmary-*` folders.

## Development (Windows)

1. Install Docker Desktop and leave it in Linux container mode. Install MySQL 8 locally if it is not already running, and allow the Docker network to connect to it.
2. Copy `.env.example` to `.env` if `.env` is not already present. Set `SECRET_KEY`, `DATABASE_URL`, and `REDIS_PASSWORD`. Use the same alphanumeric password in `REDIS_URL`.
3. Start the stack:

```powershell
docker compose up -d --build
```

4. Open http://127.0.0.1:8080. API docs, while `ENVIRONMENT=development`, are on http://127.0.0.1:8000/docs. Those ports are bound to localhost, not the LAN.

`AUTO_CREATE_TABLES=true` creates missing tables on an empty development database. It does not alter tables that already exist. Restore a dump when the local database must match production data.

For day-to-day Vue edits, run `npm run dev` in `mary-element`. Vite listens on 127.0.0.1:3000 and proxies `/api` to the API on 127.0.0.1:8000.

## Production (Ubuntu on DigitalOcean)

Use a London droplet, 4 GB RAM and 2 vCPUs, and a London Managed MySQL 8 database. Keep port 25060 closed except for this droplet. On the host firewall, allow 22, 80, and 443 only.

1. Install Docker Engine and the Compose plugin. Create a non-root deploy user. Disable SSH password login.
2. Copy this directory to `/var/mary`. Do not copy `storage\` care files into the image; they are mounted at runtime. Do not copy private keys.
3. Put the Managed MySQL CA certificate at `/var/mary/certs/ca-certificate.crt`.
4. Import the database dump **before** the first API start. The production stack will not create tables.
5. Copy `.env.production.example` to `.env.production`, fill in every value, and run `chmod 600 .env.production`. `DATABASE_URL` must include `ssl_ca=/etc/ssl/certs/do-mysql-ca.crt`. `PUBLIC_BASE_URL`, `DOMAIN`, and `CORS_ORIGINS` must be the same `https://` site.
6. Create the care-file directory, owned by uid 1000 (the user inside the API container):

```bash
sudo mkdir -p /var/mary/storage /var/mary/certs
sudo chown -R 1000:1000 /var/mary/storage
```

7. Start:

```bash
cd /var/mary
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
```

The first HTTPS certificate is a two-day self-signed placeholder so Nginx can boot. Point DNS at the droplet, then replace it:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml --profile tls run --rm certbot certonly \
  --webroot -w /var/www/certbot -d "$DOMAIN" \
  --email you@example.com --agree-tos --no-eff-email

docker compose --env-file .env.production -f docker-compose.prod.yml exec proxy \
  sh -c 'cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem /etc/nginx/certs/fullchain.pem && cp /etc/letsencrypt/live/$DOMAIN/privkey.pem /etc/nginx/certs/privkey.pem && nginx -s reload'
```

Renew with the same `certbot renew` command and the same copy. Reload Nginx after every renewal.

Check `https://your-domain/healthz`. It returns `{"status":"ok"}` only when the API and Redis are up.

## What is the same on both machines

The frontend image and the backend image are Linux images. Docker Desktop builds the same kind of image the droplet runs. Build with `linux/amd64` if the droplet is a regular DigitalOcean VM.

The environment file is the difference: database URL, secrets, public URL, and whether tables are auto-created. Production also turns off API docs, in-memory sessions, and table auto-creation, and it refuses to start if `SECRET_KEY` or the mailbox password is still a placeholder.

## Updates and rollback

Tag the images you intend to keep, then start that tag:

```bash
IMAGE_TAG=2026-11-22 docker compose --env-file .env.production -f docker-compose.prod.yml build
IMAGE_TAG=2026-11-22 docker compose --env-file .env.production -f docker-compose.prod.yml up -d
```

To go back, run `up -d` again with the previous `IMAGE_TAG`. There is no migration history in this tree. Take a Managed MySQL backup before a schema change, and restore that backup if the release has to be undone.

## Secrets that were removed from source

Mailbox passwords for `service@stmarysteamcare.co.uk` and `support@stmarysteamcare.co.uk` were written in Python files. Those values are gone from this tree. Rotate both passwords at the mail host, then set `SMTP_USER` and `SMTP_PASSWORD` in the environment file. Until that is done, password-reset mail is not sent. The API still answers the reset form with the same message whether or not the address exists.

The application connects as `mary_app`. That password is only in the gitignored `.env`. Startup still refuses a `DATABASE_URL` that contains the old committed password. `mary_app` exists for `localhost`, `127.0.0.1`, and `::1`, and it can use only `mary_api_db_new` for select, insert, update, delete, create, drop, alter, index, references, temporary tables, and lock tables. It does not have FILE, SHUTDOWN, SUPER, GRANT, or CREATE USER. A query from the backend container connected as `mary_app`@`127.0.0.1`.

`mary_admin`@`%` is still present and still has server-wide privileges. MySQL still listens on every interface. The firewall rules `Port 3306` and `Port 33060` still allow any remote address. Writing `C:\ProgramData\MySQL\MySQL Server 8.0\my.ini`, restarting the `MySQL80` service, and disabling those rules were access denied from this session. Finish that from an elevated PowerShell prompt:

```powershell
Disable-NetFirewallRule -DisplayName "Port 3306"
Disable-NetFirewallRule -DisplayName "Port 33060"
```

Under `[mysqld]` in `C:\ProgramData\MySQL\MySQL Server 8.0\my.ini`, add:

```
bind-address=127.0.0.1
mysqlx-bind-address=127.0.0.1
```

Then run `Restart-Service MySQL80`. Docker Desktop reaches MySQL as `127.0.0.1`, so the stack keeps working after the firewall rules are disabled and after MySQL listens only on localhost.

The previous `mary_admin` password was only in `.env`, and that URL now uses `mary_app`. To take `mary_admin` off the network without that password, start MySQL once from an elevated prompt with `--skip-grant-tables`, copy `mary_admin` onto `localhost`, `127.0.0.1`, and `::1`, drop `mary_admin`@`%`, and start the normal service again. Do not leave `--skip-grant-tables` running. `m_patient_care_types` now has unique key `uq_patient_care_su_type` on `(su_id, care_type_id)`.

The private key in `C:\Projects\Mary\ssh key\` must stay off the droplet and out of any image. Rotate it if it has been copied or committed.
