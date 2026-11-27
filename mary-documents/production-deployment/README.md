# Production deployment package

Review date: 27 November 2026. This package describes the `mary-v2` stack in this folder. It does not start a droplet and it does not change DNS.

| Document | What it is |
| --- | --- |
| [01-production-readiness.md](01-production-readiness.md) | Pass/fail review of the current architecture and of the live hostnames |
| [02-digitalocean-deployment.md](02-digitalocean-deployment.md) | London architecture, sizes, cost, and the cutover procedure |
| [03-operations-runbook.md](03-operations-runbook.md) | Deploy, rollback, backup, restore, certificates, logs, restart, recovery |
| [templates/](templates/) | Files to copy and fill in. Names match the settings this application reads |

The application publishes one site. The browser loads the Vue app and calls `/api/v1` on that same site. A separate public API hostname needs an application change before it can be used. The readiness report explains that gap.
