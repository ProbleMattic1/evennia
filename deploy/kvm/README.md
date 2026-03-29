# Production KVM deployment runbook

This directory contains everything needed to run the four-host production setup.
Nothing here belongs in the game application or the local dev repo.

## What goes on which host

| Host | VPS | What runs |
|------|-----|-----------|
| KVM 8 | `deploy/kvm/postgres/` | PostgreSQL 14 — primary DB |
| KVM 4 | `deploy/kvm/evennia/` | Evennia game server |
| KVM 2 | `deploy/kvm/edge/` | Caddy reverse proxy + Next.js production |
| KVM 1 | `deploy/kvm/ops/` | Monitoring (Prometheus, Grafana, Uptime Kuma) + scheduled backup |

## What NEVER goes on a VPS

- The full monorepo checkout.
- Application source files (`game/`, `frontend/`).
- Dev bind-mounts (`./evennia`, `.:/usr/src/game`).
- The root `docker-compose.yml` (dev-only).
- Any `.env` file committed to git.

Each VPS only needs the contents of its subfolder, plus a `.env` file you create from `.env.example`.

## Networking prerequisites

All four VMs need a **private LAN** (most VPS providers offer this).
Assign each a stable private IP and replace the placeholder `10.0.0.X/Y` values in each `.env`.

Firewall rules (minimum):

```
KVM 8: 5432 open only to KVM 4 private IP (and KVM 1 for backup)
KVM 4: 4000/4001/4002 open only to KVM 2 private IP (and admin IP)
KVM 2: 80/443 open to the world; nothing else public
KVM 1: no public ports; 9090/3000/3001 on loopback only; SSH from admin IP only
```

## How images reach the servers (CI workflow)

CI (`.github/workflows/publish.yml`) builds and pushes on every merge to `main`:

- `ghcr.io/yourorg/aurnom-evennia:<sha>` — built from the repo-root `Dockerfile`
- `ghcr.io/yourorg/aurnom-web:<sha>` — built from `deploy/kvm/edge/Dockerfile.frontend`

On each VPS, update `IMAGE_TAG` in `.env` to the new tag, then run:

```sh
docker compose pull
docker compose up -d
```

## First-time startup order

Follow this order — each step depends on the previous.

### 1. KVM 8 — Database

```sh
# On KVM 8
cp .env.example .env && vim .env   # set real POSTGRES_PASSWORD
docker compose up -d
docker compose ps                  # confirm postgres is healthy
```

Verify no public exposure:

```sh
# Should show only 0.0.0.0:5432 if you did NOT map it, or private IP only
ss -tlnp | grep 5432
```

### 2. KVM 4 — Evennia (first deploy: run migrations before starting the server)

```sh
# On KVM 4
cp .env.example .env && vim .env   # set POSTGRES_HOST, passwords, IMAGE_TAG
docker compose run --rm evennia evennia migrate --noinput
docker compose up -d
docker compose ps                  # confirm evennia healthcheck passes
```

### 3. KVM 2 — Edge

```sh
# On KVM 2
cp .env.example .env && vim .env   # set DOMAIN, EVENNIA_HOST, IMAGE_TAG
docker compose up -d
# Caddy will provision TLS automatically on first request to your domain.
```

Test proxy and WebSocket paths:

```sh
curl -I https://game.yourdomain.com/api/         # should reach Evennia
curl -I https://game.yourdomain.com/             # should reach Next.js
```

### 4. KVM 1 — Ops

```sh
# On KVM 1
cp .env.example .env && vim .env   # set GRAFANA_ADMIN_PASSWORD, DB creds for backup
docker compose up -d
```

Run a backup immediately to verify:

```sh
docker compose --profile backup run --rm backup
ls backups/
```

## Routine updates (rolling forward)

```sh
# On each VPS (order: KVM 4, then KVM 2; KVM 8 rarely needs restarts)
vim .env        # update IMAGE_TAG to new release tag
docker compose pull
docker compose up -d

# Only if migrations are needed (check release notes):
docker compose run --rm evennia evennia migrate --noinput
```

## Notes on Caddy + Evennia WebSocket

Caddy proxies `/webclient*` with `Upgrade` and `Connection` headers forwarded to port `4002` on KVM 4.
If your Evennia web client uses a different path, adjust the `Caddyfile` `handle` block accordingly.

The `EVENNIA_BASE_URL` env var is consumed by the Next.js server-side renders to call game APIs
from inside the Docker network; browser calls always go through the public domain.

## Backup offsite sync (cron on KVM 1)

After the backup container writes `.sql.gz` files to `BACKUP_STAGING_DIR`, sync them offsite.
Example using `rclone` (install on the KVM 1 host):

```sh
# /etc/cron.d/aurnom-backup
0 3 * * * root docker compose -f /opt/aurnom-ops/docker-compose.yml --profile backup run --rm backup && rclone sync /opt/aurnom-ops/backups remote:your-bucket/aurnom-db
```
