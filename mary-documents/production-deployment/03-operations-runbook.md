# Operations runbook

Run these on the London droplet as the `deploy` user, from `/var/mary`, unless a step says otherwise. The Compose project name is `mary-prod`.

```bash
cd /var/mary
export COMPOSE="docker compose --env-file .env.production -f docker-compose.prod.yml"
```

## Deploy

1. Take a Managed MySQL backup from the DigitalOcean control panel.
2. Copy `/var/mary/storage` to Spaces (see Backup below) if the release changes file handling.
3. Build a tagged image set. Replace the date with the release date.

```bash
IMAGE_TAG=2026-11-27 $COMPOSE build
IMAGE_TAG=2026-11-27 $COMPOSE up -d
```

4. Check:

```bash
$COMPOSE ps
curl -fsS https://registryv2.stmarysteamcare.co.uk/healthz
```

5. Sign in and open one known page: Dashboard for an administrator, the planner for staff, the Carer Portal for a carer.

`AUTO_CREATE_TABLES` stays `false`. Apply reviewed SQL before `up` when a release adds a column. There is no migration history in this tree.

## Rollback

1. Start the previous tag. Images from the last build remain on the droplet until they are removed.

```bash
IMAGE_TAG=2026-11-22 $COMPOSE up -d
```

2. If the release changed the database, roll the database back from the backup taken in Deploy step 1. An old application image against a new schema is not a safe mix.
3. Check `/healthz` and one sign-in.

## Database backup

Managed MySQL daily backups are the primary copy. Confirm in the control panel that the last backup finished.

Once a week, also take a logical dump from the droplet and store it outside the droplet:

```bash
mysqldump --ssl-mode=REQUIRED --ssl-ca=/var/mary/certs/ca-certificate.crt \
  --single-transaction --routines --triggers \
  -h DB_HOST -P 25060 -u mary_app -p mary_api_db_new \
  | gzip > /var/mary/backups/mary_api_db_new-$(date +%F).sql.gz
```

Copy that file to the London Space and delete dumps older than 30 days from the droplet disk. Do not commit the dump.

## Database restore

1. Put the site in maintenance by stopping the API. Nginx will answer 502 for `/api/` while it is stopped.

```bash
$COMPOSE stop backend
```

2. Restore into a new database name first when the dump is a drill. Restore over `mary_api_db_new` only during a real recovery.

```bash
gunzip -c /var/mary/backups/mary_api_db_new-DATE.sql.gz \
  | mysql --ssl-mode=REQUIRED --ssl-ca=/var/mary/certs/ca-certificate.crt \
      -h DB_HOST -P 25060 -u mary_app -p mary_api_db_new
```

3. Start the API and check a known service-user count with an administrator. Do not announce the site restored until that count matches the backup.

A DigitalOcean point-in-time restore creates a new cluster. After that restore, change `DATABASE_URL` to the new host, recreate the backend container, and move the trusted source to this droplet.

## Care-file backup and restore

Install `rclone` once and configure a remote named `mary-spaces` from `/var/mary/backup.env`.

Nightly copy:

```bash
rclone sync /var/mary/storage mary-spaces:mary-care-files/storage --fast-list
```

Restore:

```bash
$COMPOSE stop backend
rclone sync mary-spaces:mary-care-files/storage /var/mary/storage --fast-list
sudo chown -R 1000:1000 /var/mary/storage
$COMPOSE start backend
```

`sync` makes the destination match the source. A restore from Spaces overwrites droplet files that are newer than the Space. During a drill, restore into `/var/mary/storage-restore` and compare.

Cron, as `deploy`:

```cron
15 2 * * * rclone sync /var/mary/storage mary-spaces:mary-care-files/storage --fast-list
```

## SSL renewal

The proxy serves `/etc/nginx/certs/fullchain.pem` and `privkey.pem`. Let's Encrypt keeps the live files under `/etc/letsencrypt/live/<name>/`. Renewal has to copy them and reload Nginx.

```cron
20 3 * * * /var/mary/mary-documents/production-deployment/templates/renew-certificate.sh >> /var/log/mary-certbot.log 2>&1
```

The script is safe to run every day. Certbot renews when the certificate is inside its renewal window, about 30 days before expiry.

Check the served certificate:

```bash
echo | openssl s_client -servername registryv2.stmarysteamcare.co.uk \
  -connect registryv2.stmarysteamcare.co.uk:443 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates
```

The subject must be `registryv2.stmarysteamcare.co.uk`. Alert if the end date is within 14 days.

## Logs

```bash
$COMPOSE logs --since 30m backend
$COMPOSE logs --since 30m proxy
```

Docker keeps three files of 10 MB for each service. That is about 30 MB. It will not hold a month of audit history. Application audit events are in MySQL (`m_audit_logs`), not in these files.

Password-reset failures are in the backend log as `SMTP is not configured` or `Password reset email was not sent`.

For a longer retain, ship the JSON logs to a London log store. That shipper is not in this repository.

## Restart

```bash
$COMPOSE restart backend
$COMPOSE restart proxy
$COMPOSE restart redis
```

Restarting Redis drops in-memory keys that have not been written to the AOF yet. Sessions that Redis no longer has must sign in again. Prefer `restart backend` or `restart proxy` during the day.

A full stack restart:

```bash
$COMPOSE up -d
```

## Health and alerts

Configure a DigitalOcean uptime check, or an external check, every minute:

- URL: `https://registryv2.stmarysteamcare.co.uk/healthz`
- Expect HTTP 200 and the text `mary-api-fastapi`
- Alert after two failures

`/healthz` proves the API process and Redis. It does not prove MySQL. Once a day, from the droplet, run:

```bash
$COMPOSE exec backend python -c "import asyncio; from sqlalchemy import text; from app.db.session import AsyncSessionLocal, engine
async def main():
    async with AsyncSessionLocal() as db:
        print('db', int((await db.execute(text('SELECT 1'))).scalar() or 0))
    await engine.dispose()
asyncio.run(main())"
```

Expect `db 1`. Alert on disk use above 80% for `/` and for `/var/mary`.

## Disaster recovery

| Loss | Action |
| --- | --- |
| Bad application release | Rollback to the previous `IMAGE_TAG`. Restore the database only if that release changed it |
| Droplet will not boot | Restore the weekly Droplet Backup, or build a new droplet from this guide and attach the same Managed MySQL trusted source. Restore `/var/mary/storage` from Spaces. Issue a new Let's Encrypt certificate. Move the DNS A record |
| MySQL cluster lost | Restore the DigitalOcean backup to a new cluster, or load the weekly `mysqldump`. Update `DATABASE_URL`. Recreate the backend container |
| Care files deleted | Stop the backend, restore from Spaces, start the backend |
| Redis volume lost | Start Redis again. Users sign in again. Care records are in MySQL and in `/var/mary/storage` |
| Certificate expired | Run `templates/renew-certificate.sh`. If the account is locked out, the HTTP-01 challenge on port 80 still has to reach this droplet |
| DNS pointed at the old Apache droplet by mistake | Point `registryv2` back at the new droplet. The old droplet is the Laravel site and will not serve this API |

Recovery time for the small production layout is the time to create a droplet, restore the dump, restore Spaces, and change DNS. With a 300 second TTL, plan on about one hour once the backups have been proven. Run that drill on staging before go-live.

## Go-live order

1. Staging restore of the database and a sample of care files.
2. Production droplet and Managed MySQL, backups on, firewall on.
3. Certificate name matches `registryv2.stmarysteamcare.co.uk`.
4. Sign-in, document preview, password reset, and `/healthz` succeed.
5. Lower DNS TTL, then change the A record in the maintenance window.
6. Watch `/healthz` and the backend log for one hour.
7. Raise DNS TTL after the old address is no longer required.
