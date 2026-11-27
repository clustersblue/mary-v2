# Deploy the new app beside the old one

**Droplet:** Ubuntu 24.04, 1 vCPU, 2 GB RAM, Reserved IP `178.62.35.79`  
**New name:** `https://registryv2.stmarysteamcare.co.uk`  
**DNS:** leave the A record at `178.62.35.79`. Do not use `178.62.0.1`. That address is the network gateway.

The old names (`api`, `doc`, `home`, `homeapi`, `registry`, and the one.com website forwards) stay as they are. Apache keeps ports 80 and 443. The new containers listen only on `127.0.0.1`.

This droplet has 2 GB of RAM and the old app is already running. The new site can start here. A care-note PDF or an access-request PDF can run the machine out of memory. Resize to 2 vCPU and 4 GB before staff rely on those downloads.

## 1. Sign in and record what is already running

From your PC:

```bash
ssh root@178.62.35.79
```

On the droplet:

```bash
ss -tlnp | awk 'NR==1 || /:80|:443|:8000|:6379/'
apache2ctl -S
curl -fsS -o /dev/null -w "%{http_code}\n" http://127.0.0.1/
```

Expect Apache to own ports 80 and 443. If a different program owns them, stop and keep that program. Do not stop Apache.

Confirm an old name still answers before you change anything:

```bash
curl -sI https://registry.stmarysteamcare.co.uk/ | head -n 5
```

## 2. Install Docker

Skip this step if `docker compose version` already prints a version.

```bash
apt-get update
apt-get install -y ca-certificates curl
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" > /etc/apt/sources.list.d/docker.list
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
```

## 3. Create a separate database

In the DigitalOcean database panel for the existing London cluster:

1. Add a database named `mary_api_db_new`.
2. Add a user named `mary_app` restricted to that database.
3. Confirm the droplet is a trusted source. The app will use the **private** host, the name that starts with `private-`, port `25060`.

Do not point the new app at `defaultdb`. Do not put `doadmin` in the application settings. A password character such as `@`, `#`, or `%` must be URL-encoded inside `DATABASE_URL`.

Download the cluster CA certificate on the droplet:

```bash
mkdir -p /var/mary/certs /var/mary/storage /var/mary/app
# Save the CA from the database panel as /var/mary/certs/ca-certificate.crt
chown -R 1000:1000 /var/mary/storage
```

## 4. Load the schema into the new database

Production refuses to create tables by itself. From the Windows PC, export the local Mary database and copy the dump to the droplet. Do not export the old droplet's `defaultdb`.

```powershell
mysqldump --single-transaction --routines --triggers -u mary_app -p mary_api_db_new > mary_api_db_new.sql
scp mary_api_db_new.sql root@178.62.35.79:/var/mary/
```

On the droplet, import into the new managed database:

```bash
mysql --ssl-mode=REQUIRED --ssl-ca=/var/mary/certs/ca-certificate.crt \
  -h PRIVATE_DB_HOST -P 25060 -u mary_app -p mary_api_db_new \
  < /var/mary/mary_api_db_new.sql
rm /var/mary/mary_api_db_new.sql
```

Replace `PRIVATE_DB_HOST` with the private host from the database panel.

## 5. Copy the new code

From `C:\Projects\Mary\mary-v2` on the Windows PC. Do not copy `.env`, `.env.production`, `mary-fastapi\storage`, or any SSH key.

```powershell
scp -r C:\Projects\Mary\mary-v2\mary-element C:\Projects\Mary\mary-v2\mary-fastapi C:\Projects\Mary\mary-v2\deploy C:\Projects\Mary\mary-v2\docker-compose.prod.yml C:\Projects\Mary\mary-v2\docker-compose.prod.shared-host.yml C:\Projects\Mary\mary-v2\.env.production.example root@178.62.35.79:/var/mary/app/
```

## 6. Write the production environment file

On the droplet:

```bash
cd /var/mary/app
cp .env.production.example .env.production
chmod 600 .env.production
openssl rand -hex 32
openssl rand -hex 32
```

Use the two random values for `SECRET_KEY` and `REDIS_PASSWORD`. Edit `.env.production`:

```env
ENVIRONMENT=production
SECRET_KEY=first-random-value
ACCESS_TOKEN_EXPIRE_MINUTES=1440

DATABASE_URL=mysql+aiomysql://mary_app:URL_ENCODED_PASSWORD@PRIVATE_DB_HOST:25060/mary_api_db_new?ssl_ca=/etc/ssl/certs/do-mysql-ca.crt
AUTO_CREATE_TABLES=false

REDIS_PASSWORD=second-random-value
REDIS_URL=redis://:second-random-value@redis:6379/0
SESSION_MEMORY_FALLBACK=false

DOMAIN=registryv2.stmarysteamcare.co.uk
PUBLIC_BASE_URL=https://registryv2.stmarysteamcare.co.uk
CORS_ORIGINS=https://registryv2.stmarysteamcare.co.uk
ALLOWED_HOSTS=registryv2.stmarysteamcare.co.uk

STORAGE_HOST_PATH=/var/mary/storage
MYSQL_CA_PATH=/var/mary/certs/ca-certificate.crt

SMTP_HOST=send.one.com
SMTP_PORT=465
SMTP_USER=mailbox-username
SMTP_PASSWORD=mailbox-password
SMTP_FROM=mailbox-username

GEMINI_API_KEY=
OPENAI_API_KEY=
```

`REDIS_URL` must use the same password as `REDIS_PASSWORD`. The API will not start while `SMTP_USER` or `SMTP_PASSWORD` is empty. Port 465 is required.

## 7. Start the new containers

Start only the site, the API, and Redis. Do not start `proxy`. The proxy binds ports 80 and 443 and would fight Apache.

```bash
cd /var/mary/app
docker compose --env-file .env.production \
  -f docker-compose.prod.yml \
  -f docker-compose.prod.shared-host.yml \
  up -d --build frontend backend redis
```

Check:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml -f docker-compose.prod.shared-host.yml ps
curl -fsS http://127.0.0.1:18000/healthz
curl -fsS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:18080/
ss -tlnp | awk 'NR==1 || /:80|:443|:18000|:18080/'
```

Expected health body: `{"status":"ok","service":"mary-api-fastapi","version":"1.0.0"}`. The page returns `200`. Apache still owns ports 80 and 443. `18000` and `18080` listen on `127.0.0.1` only.

If the backend restarts, read the log:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml -f docker-compose.prod.shared-host.yml logs --tail 80 backend
```

## 8. Add the Apache site for this one name

Enable the proxy modules:

```bash
a2enmod proxy proxy_http headers ssl rewrite
systemctl reload apache2
```

Create `/etc/apache2/sites-available/registryv2.conf`:

```apache
<VirtualHost *:80>
    ServerName registryv2.stmarysteamcare.co.uk
    RewriteEngine On
    RewriteRule ^ https://%{HTTP_HOST}%{REQUEST_URI} [END,NE,R=permanent]
</VirtualHost>

<VirtualHost *:443>
    ServerName registryv2.stmarysteamcare.co.uk
    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/registryv2.stmarysteamcare.co.uk/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/registryv2.stmarysteamcare.co.uk/privkey.pem

    ProxyPreserveHost On
    RequestHeader set X-Forwarded-Proto "https"
    LimitRequestBody 26214400

    ProxyPass        /api/ http://127.0.0.1:18000/api/
    ProxyPassReverse /api/ http://127.0.0.1:18000/api/
    ProxyPass        /healthz http://127.0.0.1:18000/healthz
    ProxyPassReverse /healthz http://127.0.0.1:18000/healthz
    ProxyPass        / http://127.0.0.1:18080/
    ProxyPassReverse / http://127.0.0.1:18080/

    Header always set Strict-Transport-Security "max-age=15552000"
    Header always set X-Content-Type-Options "nosniff"
    Header always set Referrer-Policy "strict-origin-when-cross-origin"
    Header always set X-Frame-Options "SAMEORIGIN"
    Header always set Content-Security-Policy "default-src 'self'; base-uri 'self'; frame-ancestors 'self'; frame-src 'self' blob:; object-src 'self' blob:; img-src 'self' data: blob:; font-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; connect-src 'self'"
</VirtualHost>
```

The certificate files do not exist yet. Enable a temporary HTTP-only site so the certificate request can succeed. Replace the file with this shorter version for that one step:

```apache
<VirtualHost *:80>
    ServerName registryv2.stmarysteamcare.co.uk
    DocumentRoot /var/www/html
</VirtualHost>
```

```bash
apache2ctl configtest
a2ensite registryv2
systemctl reload apache2
certbot certonly --apache -d registryv2.stmarysteamcare.co.uk \
  --key-type ecdsa \
  --email dpo@stmarysteamcare.co.uk --agree-tos --no-eff-email
```

After the certificate is issued, put the full virtual-host file back, then:

```bash
apache2ctl configtest
systemctl reload apache2
```

Renewal is already Certbot's job when the Apache plugin issued the certificate. Confirm the timer:

```bash
systemctl list-timers | grep certbot
```

## 9. Prove both systems

New system:

```bash
curl -fsS https://registryv2.stmarysteamcare.co.uk/healthz
```

Old system, from your PC. Each of these must still answer as it did before the deploy:

- `https://registry.stmarysteamcare.co.uk`
- `https://api.stmarysteamcare.co.uk`
- `https://home.stmarysteamcare.co.uk`

Then in a browser, open `https://registryv2.stmarysteamcare.co.uk`, sign in, open one page, and sign out.

## 10. Later releases

On the droplet, from `/var/mary/app`, after copying the changed source:

```bash
docker compose --env-file .env.production \
  -f docker-compose.prod.yml \
  -f docker-compose.prod.shared-host.yml \
  up -d --build frontend backend redis
```

Do not add `proxy` to that command. Reload Apache only when the virtual host changed:

```bash
apache2ctl configtest && systemctl reload apache2
```
