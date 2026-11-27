# Production readiness report

**Review date:** 27 November 2026  
**Code reviewed:** `C:\Projects\Mary\mary-v2`  
**Stated addresses:** `https://registryv2.stmarysteamcare.co.uk` and `https://registryv2-api.stmarysteamcare.co.uk`  
**Verdict:** Do not cut this stack over to those two addresses yet. The repository can run as one London site after the failed items below are closed. The hostnames that are live today are a different application.

## What is running today

On 27 November 2026 both names resolved to the same address, `178.62.35.79`.

| Check | Result |
| --- | --- |
| TLS protocol offered | TLS 1.3 |
| Certificate issuer | Let's Encrypt, intermediate `YE1` |
| Signature | SHA-384 with ECDSA |
| Validity | 29 September 2026 to 28 December 2026 |
| Name on the certificate | `api.marysteam.co.uk` only |
| Software that answered | Apache, with a Laravel session cookie |

The certificate is a real Let's Encrypt certificate, and TLS 1.3 is the right protocol. The certificate name is `api.marysteam.co.uk`. It does not cover `registryv2.stmarysteamcare.co.uk` or `registryv2-api.stmarysteamcare.co.uk`. A browser that checks the name will reject the connection. Renewal has to happen before 28 December 2026 for the name that is actually on the certificate.

The response is Apache and Laravel. The `mary-v2` stack is Nginx, Vue, and FastAPI. Putting this repository on that droplet replaces the site that is there now. Plan a maintenance window or use a new droplet.

## What this repository is built to run

```text
Browser
  |
  |  HTTPS, one name, ports 80 and 443
  v
Nginx proxy          certificate from Let's Encrypt
  |-- /            --> Vue static files
  |-- /api/        --> FastAPI, not published on the host
  |-- /healthz     --> FastAPI
  |
  +-- Redis        private Compose network, password required
  |
  +-- MySQL        DigitalOcean Managed MySQL in London, TLS, port 25060
  |
  +-- /var/mary/storage   care PDFs on the droplet disk
```

The Vue client uses a relative address, `/api/v1`. It does not read `VITE_API_URL`. `docker-compose.prod.yml` publishes ports 80 and 443 only. FastAPI and Redis have no host port. Production startup refuses a missing `SECRET_KEY`, a wildcard CORS origin, an `http://` public URL, an empty mailbox password, in-memory sessions, and automatic table creation.

## Pass / fail

| Area | Result | Evidence |
| --- | --- | --- |
| One public site, API behind Nginx | Pass | `deploy/nginx/prod.conf.template`, `src/service/api.js` |
| Two public hostnames, separate API origin | Fail | No setting points the built app at `registryv2-api`. CORS is a list of full `https://` origins and defaults to the one site |
| TLS design for the new stack | Pass, with an open task | TLS 1.2 and 1.3, HSTS, Let's Encrypt webroot. First boot certificate is a 2-day self-signed RSA 2048 certificate. Renewal is a manual command. Nothing in Compose runs `certbot renew` on a schedule |
| TLS on the live hostnames | Fail | Certificate name is `api.marysteam.co.uk`. It expires 28 December 2026 |
| Authentication | Pass, with limits | Opaque `mary_tok_` session in Redis. Production refuses to issue a token when Redis is down. Default life is 24 hours (`ACCESS_TOKEN_EXPIRE_MINUTES=1440`). The browser can keep the token in `localStorage` when Remember me is ticked. Logout in the page clears the browser copy. A copied token still works until Redis expires it |
| CORS and host check | Pass for one site | Production requires `https://` origins. `TrustedHostMiddleware` allows the public hostname. A second API hostname fails this until both names are configured and the client is rebuilt |
| Secrets | Pass | `.env.production` is gitignored. `chmod 600` is in the deploy steps. The image does not contain the database password. Production rejects the old committed database password and a short `SECRET_KEY` |
| Mail | Fail until filled | Reset mail is implemented. `SMTP_USER` and `SMTP_PASSWORD` are empty in development. Production will not start while they are empty. The client speaks implicit TLS on port 465 only |
| Logging | Partial | Docker keeps three JSON files of 10 MB each, on the droplet. There is no central log store and no alert when the API returns 503 |
| Health check | Partial | `/healthz` checks Redis. It returns `{"status":"ok"}` when MySQL is down |
| Backups | Fail | No backup job is defined for Managed MySQL or for `/var/mary/storage`. Redis AOF covers sessions on that one disk |
| Monitoring | Fail | No uptime check, disk alert, or certificate-expiry alert is configured |
| Database placement | Pass as a design | Managed MySQL in London, TLS, trusted sources limited to the droplet. The application account should be limited to `mary_api_db_new`. `doadmin` in the example URL is broader than the app needs |
| Care-file durability | Fail | PDFs live on the droplet disk. A droplet rebuild without a copy of `/var/mary/storage` loses them. Two app servers cannot share that directory |
| Schema change | Partial | There is no migration tool. `AUTO_CREATE_TABLES` is false in production. A release that needs a new column requires a reviewed SQL change and a backup taken first |
| Rate limiting | Partial | Nginx limits login and password reset. Other routes are not limited at the proxy |
| Content Security Policy | Partial | `frame-src` and `object-src` allow same-origin blob previews. `script-src` and `style-src` still allow `unsafe-inline`, and scripts allow `unsafe-eval` |
| Scalability | Partial | One FastAPI process is enough for an agency of this size. WeasyPrint PDF work shares that process. A second droplet does not share sessions or care files |
| High availability | Fail | One proxy, one API container, one Redis, one disk. A droplet reboot is a full outage |
| Disaster recovery | Partial | Image tags can roll the app back. Database rollback depends on a Managed MySQL backup that is not yet required by the deploy steps. Care files have no second copy |
| Windows development database | Out of scope for the droplet | The local MySQL service still listens on every interface and `mary_admin`@`%` still exists. That is a development-machine risk. It is not the production database |

## Risks

1. **Cutover replaces a live Laravel site.** Both requested names already answer on Apache. A deploy to `178.62.35.79` takes that site down.
2. **The live certificate name is wrong for these hostnames** and expires on 28 December 2026.
3. **Care PDFs have one copy,** on the droplet disk.
4. **MySQL failure looks healthy.** `/healthz` stays ok when the database is unreachable, so a monitor that only calls `/healthz` will stay green.
5. **Certificate renewal is easy to miss.** The documented command is manual. A missed renewal takes HTTPS down.
6. **Sessions and files are local.** A second API droplet would not see the same logins or the same PDFs.
7. **A split API hostname will break the built frontend** until `baseURL` in `mary-element/src/service/api.js` is changed and CORS lists the page's origin.
8. **Mailbox passwords are not in the environment yet.** Production startup stops until they are set. Reset mail still needs port 465.

## Recommended improvements, in order

1. Keep one public name for the launch. Use `https://registryv2.stmarysteamcare.co.uk` for the page and for `/api/`. Leave `registryv2-api` as a DNS name that redirects to that site, or remove it until the client can call another origin.
2. Issue a Let's Encrypt certificate whose name is exactly that site. Use ECDSA. Renew twice a day and reload Nginx. Alert at 14 days before expiry.
3. Run the app on a new London droplet, or schedule a replacement of the Apache site. Do not share the Laravel document root with this stack.
4. Use Managed MySQL in London. Create an application user with rights only on `mary_api_db_new`. Allow port 25060 from the droplet only.
5. Turn on Managed MySQL daily backups. Copy `/var/mary/storage` to Spaces every night. Test a restore before go-live.
6. Add a MySQL ping to the health check, or monitor a query from outside `/healthz`.
7. Add an uptime check on `https://<site>/healthz` and a disk-space alert on the droplet.
8. Schedule `certbot renew` and the certificate copy that the proxy already expects.
9. Fill `SMTP_USER`, `SMTP_PASSWORD`, and `PUBLIC_BASE_URL`, then prove one reset message to a test mailbox.
10. After launch, plan a stricter Content Security Policy. Removing `unsafe-inline` and `unsafe-eval` needs a frontend build change. It is not required to boot the site, and it is required before calling the header strict.

## Security recommendations

- SSH keys only. No password login. A non-root deploy user. The private key in `C:\Projects\Mary\ssh key\` stays off the droplet.
- Host firewall: 22, 80, and 443. Do not publish 3306, 6379, or 8000.
- `chmod 600 .env.production`. Generate `SECRET_KEY` and `REDIS_PASSWORD` with `openssl rand -hex 32`.
- Managed MySQL trusted sources: the droplet only. Store the CA at `/var/mary/certs/ca-certificate.crt`.
- HSTS is already set for six months. Add `includeSubDomains` only after every name on that parent serves HTTPS.
- Login and reset limits are already in the Nginx template. Keep them.
- Rotate the mailbox password at the mail host. The application reads `SMTP_USER` and `SMTP_PASSWORD`.
- Do not commit `.env`, `.env.production`, care files, or database dumps.

## Infrastructure recommendations

- Region: London (`lon1`) for the droplet, the database, Spaces, and any load balancer. Care records should stay in the UK.
- Database: DigitalOcean Managed MySQL 8. A database on the app droplet is a single disk for both the site and the records.
- App server: one Basic droplet, 2 vCPU and 4 GiB RAM, for the first production launch. WeasyPrint needs that memory.
- Redis: keep it on the Compose network for the single-server launch. A second app server needs one shared Redis.
- Files: Spaces for the off-site copy. The app still reads `/var/mary/storage` until a later change stores files in Spaces directly.
- High availability is a later stage. It needs two app droplets, a load balancer, shared Redis, shared file storage, and a MySQL standby. The current code does not provide those shared pieces.

## SSL/TLS judgement

Let's Encrypt is the right certificate authority for this site. The repository is set up for it: HTTP-01 on port 80, TLS 1.2 and TLS 1.3, session cache, and HSTS.

The certificate that is live on the two requested names is not suitable for them. It is a Let's Encrypt ECDSA certificate for a different name, `api.marysteam.co.uk`. Replace it with a certificate issued for the name the browser uses. ECDSA P-256 from Let's Encrypt is the preferred key. RSA 2048 is acceptable. The 2-day self-signed certificate created at first boot is only there so Nginx can start. Replace it before anyone uses the site.

Renewal has to be automatic. Let's Encrypt certificates last about 90 days. A renew job that copies `fullchain.pem` and `privkey.pem` into `/etc/nginx/certs` and reloads Nginx is the missing piece. The runbook contains that job.
