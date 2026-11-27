# DigitalOcean deployment guide

**Region:** London (`lon1`) for every resource.  
**Application:** `mary-v2` (Vue in `mary-element`, API in `mary-fastapi`).  
**Public site:** one name. Recommended: `https://registryv2.stmarysteamcare.co.uk`.  
**Prices:** US dollars, excluding VAT, from DigitalOcean's published droplet and Managed MySQL lists checked in November 2026. Confirm the London total in the control panel before ordering. A droplet that runs all month costs its listed monthly price.

The commands below provision a new droplet. They do not attach to `178.62.35.79`. That address is serving the current Apache site.

## 1. Architecture

```text
                    DNS  (one A record)
                         |
                         v
              +---------------------+
              |  London droplet     |
              |  UFW: 22, 80, 443   |
              |                     |
              |  Nginx (TLS)        |
              |    /      -> Vue    |
              |    /api/  -> FastAPI|
              |  Redis (private)    |
              |  /var/mary/storage  |
              +----------+----------+
                         |
                         | TLS 25060, trusted source = this droplet
                         v
              +---------------------+         nightly copy
              | Managed MySQL 8     |         +------------------+
              | London, backups on  |         | Spaces, London   |
              +---------------------+         | care-file copies |
                                              +------------------+

Let's Encrypt validates on port 80 and stores the certificate in the proxy volume.
Uptime and disk alerts watch the droplet from outside.
```

High availability, when the single droplet is no longer enough:

```text
DNS -> London load balancer (TLS can stay on the droplets or move to the balancer)
         |-- app droplet A: Nginx, Vue, API, shared Redis client
         |-- app droplet B: Nginx, Vue, API, shared Redis client
         |
         +-- Managed Redis or one small Redis droplet (sessions)
         +-- Managed MySQL primary + standby, London
         +-- Spaces for care files (both app servers mount or sync the same copy)
```

The current frontend calls `/api/v1` on the page's own host. Both app servers can do that behind one load balancer. They cannot keep separate Redis databases or separate care-file disks.

`registryv2-api.stmarysteamcare.co.uk` is not an application setting. Leave it unpublished, or point it at the same site, until `mary-element/src/service/api.js` is changed and a new frontend image is built.

## 2. Server sizes

| Stage | Droplet | Database | When to use it |
| --- | --- | --- | --- |
| Development | None. Use the Windows PC and local MySQL | Local MySQL | Day-to-day work. Not this guide |
| Staging | Basic, 1 vCPU, 2 GiB RAM, 50 GiB ($12/month) | Managed MySQL, 1 GiB ($15.15/month) | A London copy for a release trial. Restore a reduced dump, not the only copy of production |
| Production | Basic, 2 vCPU, 4 GiB RAM, 80 GiB ($24/month) | Managed MySQL, 2 GiB ($30.45/month) | First live launch. Matches the memory WeasyPrint needs |
| High availability | Two production droplets, plus a load balancer | Managed MySQL 4 GiB primary ($60.90/month) and a standby node | Only after Redis and care files are shared. See the cost table |

Add the Managed MySQL CA, a 100 GiB volume only if `/var/mary/storage` outgrows the droplet disk ($0.10 per GiB, so 100 GiB is $10/month), and Spaces at $5/month for the off-site file copy.

## 3. Cost estimate

| Piece | Single droplet, database on the same machine | Small production (use this) | High availability |
| --- | --- | --- | --- |
| App droplet | $24 | $24 | $48 (two droplets) |
| Weekly droplet backup, 20% | $4.80 | $4.80 | $9.60 |
| Managed MySQL | — | $30.45 (2 GiB) | $60.90 primary. Budget about the same again for a standby. Confirm the standby line in the London panel |
| Spaces, 250 GiB | $5 | $5 | $5 |
| Load balancer | — | — | $12, the published starting price. Confirm in the panel |
| Shared Redis | included on the app droplet | included on the app droplet | $12 Basic droplet, or Managed Caching at the price shown in the panel |
| **Monthly total** | **about $34** | **about $64** | **about $210 to $270** |

The single-droplet column keeps MySQL on the app disk. Use it only for a short trial. A failed disk takes the site and the records together. The small production column is the launch target.

Bandwidth on the $24 droplet includes 4,000 GiB outbound. Overage is $0.01 per GiB. This application will not reach that on agency traffic.

## 4. DNS

Create records at the DNS host for `stmarysteamcare.co.uk`. TTL 300 during cutover.

| Name | Type | Value |
| --- | --- | --- |
| `registryv2` | A | IPv4 of the new droplet |
| `registryv2` | AAAA | IPv6 of the new droplet, when the droplet has one |

Do not point `registryv2` at `178.62.35.79` until the maintenance window. Issue the certificate on the new droplet first, using the new address.

Optional, after the single site works:

| Name | Type | Value |
| --- | --- | --- |
| `registryv2-api` | A | same droplet, only if you later split the API |

## 5. Provision the droplet

1. Create a London Ubuntu 24.04 droplet, Basic, 2 vCPU, 4 GiB RAM.
2. Add the deploy user's SSH public key. Do not upload `C:\Projects\Mary\ssh key\`.
3. Turn on weekly Droplet Backups.
4. Note the public IPv4 address.

Harden the host as root, then use the deploy user:

```bash
adduser --disabled-password deploy
usermod -aG sudo deploy
install -d -m 700 -o deploy -g deploy /home/deploy/.ssh
# paste the public key into /home/deploy/.ssh/authorized_keys
# mode 600, owner deploy

printf '%s\n' \
  'PermitRootLogin no' \
  'PasswordAuthentication no' \
  'KbdInteractiveAuthentication no' \
  > /etc/ssh/sshd_config.d/10-mary.conf
systemctl reload ssh

apt-get update
apt-get install -y unattended-upgrades ufw fail2ban
dpkg-reconfigure -plow unattended-upgrades

ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

Install Docker Engine and the Compose plugin from Docker's Ubuntu repository, then:

```bash
usermod -aG docker deploy
```

Log in again as `deploy` so the group applies.

## 6. Managed MySQL

1. Create a London Managed MySQL 8 cluster, 1 vCPU, 2 GiB RAM.
2. Turn on daily backups.
3. Trusted sources: the droplet only. Do not leave 25060 open to the world.
4. Download the CA certificate to the droplet:

```bash
sudo mkdir -p /var/mary/certs /var/mary/storage
sudo chown -R 1000:1000 /var/mary/storage
# save the CA as /var/mary/certs/ca-certificate.crt
```

5. Create the database `mary_api_db_new` and a user `mary_app` with rights only on that database: select, insert, update, delete, create, drop, alter, index, references, create temporary tables, lock tables. Do not grant FILE, SUPER, SHUTDOWN, or the ability to create users.
6. Restore the dump before the API starts. Production will not create tables.

```bash
mysql --ssl-mode=REQUIRED --ssl-ca=/var/mary/certs/ca-certificate.crt \
  -h DB_HOST -P 25060 -u mary_app -p mary_api_db_new < mary_api_db_new.sql
```

URL-encode any reserved character in the password before it goes into `DATABASE_URL`.

## 7. Application deploy

```bash
sudo mkdir -p /var/mary
sudo chown deploy:deploy /var/mary
# copy this mary-v2 directory to /var/mary
# do not copy storage care files into the image
# do not copy .env or ssh keys

cd /var/mary
cp .env.production.example .env.production
chmod 600 .env.production
# fill .env.production from templates/backend.env
```

`DOMAIN`, `PUBLIC_BASE_URL`, `CORS_ORIGINS`, and `ALLOWED_HOSTS` are the same site:

```text
DOMAIN=registryv2.stmarysteamcare.co.uk
PUBLIC_BASE_URL=https://registryv2.stmarysteamcare.co.uk
CORS_ORIGINS=https://registryv2.stmarysteamcare.co.uk
ALLOWED_HOSTS=registryv2.stmarysteamcare.co.uk
```

Build for the droplet's CPU. A DigitalOcean basic droplet is `linux/amd64`.

```bash
cd /var/mary
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
```

The proxy generates a 2-day self-signed certificate so Nginx can bind to 443. Replace it as soon as DNS points at this droplet:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml --profile tls run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  -d registryv2.stmarysteamcare.co.uk \
  --key-type ecdsa \
  --email dpo@stmarysteamcare.co.uk --agree-tos --no-eff-email

docker compose --env-file .env.production -f docker-compose.prod.yml exec proxy \
  sh -c 'cp /etc/letsencrypt/live/registryv2.stmarysteamcare.co.uk/fullchain.pem /etc/nginx/certs/fullchain.pem && cp /etc/letsencrypt/live/registryv2.stmarysteamcare.co.uk/privkey.pem /etc/nginx/certs/privkey.pem && nginx -s reload'
```

Install the renewal script from `templates/renew-certificate.sh` and the cron line in the runbook.

## 8. Checks before DNS cutover

From the droplet:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml ps
curl -fsS https://registryv2.stmarysteamcare.co.uk/healthz
```

Expected health body: `{"status":"ok","service":"mary-api-fastapi","version":"1.0.0"}`.

Then, from a workstation:

- The padlock name is `registryv2.stmarysteamcare.co.uk`, issuer Let's Encrypt, protocol TLS 1.2 or 1.3.
- `http://` redirects to `https://`.
- Sign in, open one service-user document in the page, sign out.
- Send one password reset to a test mailbox.
- Confirm port 8000 and port 6379 do not answer from the public internet.

## 9. Spaces backup target

Create a London Space, private. Create a limited access key. Store the key in `/var/mary/backup.env` with mode 600. The runbook uses `rclone` to copy `/var/mary/storage` there. The application does not read this file.

## 10. What the templates replace

| You asked for | What to fill |
| --- | --- |
| `VITE_API_URL`, `VITE_APP_NAME` | Nothing in the current build. See `templates/frontend.env` |
| `APP_ENV`, `APP_URL`, `FRONTEND_URL` | `ENVIRONMENT`, `PUBLIC_BASE_URL`, `CORS_ORIGINS` |
| `SMTP_USERNAME` | `SMTP_USER` |
| `DB_HOST`, `DB_PORT`, `DB_DATABASE`, `DB_USERNAME`, `DB_PASSWORD` | One `DATABASE_URL`. The worksheet in `templates/database.env` builds that URL |
| Nginx frontend and backend vhosts | One vhost. `templates/nginx-single-origin.conf` |
| A second API vhost | `templates/nginx-split-api.conf`, unused until the frontend is changed |
