# Web platform edge URL

With Docker Compose, open the app at:

- **http://localhost:8080** — reverse proxy (Caddy) to Next (`/` and `/api/*`) and Evennia (`/auth/*`, `/webclient/*`, static/media).

Direct ports remain available for debugging:

- **http://localhost:3000** — Next only (production `frontend` service maps this port)
- **http://localhost:4001** — Evennia portal only

Set `EVENNIA_BASE_URL=http://evennia:4001` for the Next container (server-side BFF). Browsers should use the edge URL so session cookies and CSRF share one origin.

## Trusted proxies and client IP

Evennia resolves `X-Forwarded-For` using `UPSTREAM_IPS`. For **Browser → Caddy → Next (`/api/ui/...`) → Evennia**, the TCP peer on Evennia is the **Next** container, not Caddy. Trusted hops must include **both** reverse-proxy layers on the Docker network.

- **`AURNOM_TRUSTED_PROXY_HOSTS`** — comma-separated hostnames to resolve at startup (e.g. `edge,frontend`). Preferred.
- **`AURNOM_TRUSTED_PROXY_HOST`** — single hostname; still supported and merged with the list above.
- **`AURNOM_TRUSTED_PROXY_EXTRA_HOSTS`** — optional extra comma-separated hostnames.

Do not list entire Docker bridge CIDRs as trusted; only specific proxy services.

## CSRF and new hosts

`CSRF_TRUSTED_ORIGINS` in settings includes a few development hosts. For a new server or LAN IP, set:

- **`CSRF_TRUSTED_ORIGIN`** — comma-separated full origins, e.g. `http://10.0.0.140:8080,https://play.example.com`

Otherwise logins and form posts from that origin can fail (often seen as hangs or retries).

## Dev UI behind :8080 (Next `next dev` + HMR)

Default Compose builds **production** Next (`frontend` service). For **hot module reload** through Caddy:

1. Merge the dev overlay: [`docker-compose.dev-frontend.yml`](../../docker-compose.dev-frontend.yml) (repo root).
2. Set **`NEXT_ALLOWED_DEV_ORIGINS`** to the hostname or IP clients use in the browser **without** a scheme (e.g. `10.0.0.140` or `myhost.local`).
3. Bring the stack up with both files. Caddy uses **`CADDY_UPSTREAM_NEXT=frontend_dev:3000`** from the overlay so `/` and `/api/*` hit the dev server.

Example:

```bash
export NEXT_ALLOWED_DEV_ORIGINS=10.0.0.140
docker compose -f docker-compose.yml -f docker-compose.dev-frontend.yml up -d
```

Optional: `docker compose stop frontend` to stop the unused production Next container and save resources (edge still depends on it in the merged file unless you stop it after `up`).

The dev container does not publish port 3000 on the host by default (use edge **:8080**). To open Next directly, add `3001:3000` under `frontend_dev` in the overlay temporarily.

## Environment variables (see `.env.example`)

- `REDIS_URL` — Django cache + JWT denylist (Evennia container)
- `AURNOM_JWT_SECRET` — signing key for UI JWTs (required in production)
- `AURNOM_TRUSTED_PROXY_HOSTS` — see above
- `CSRF_TRUSTED_ORIGIN` — extra allowed CSRF origins for new hosts
- `NEXT_ALLOWED_DEV_ORIGINS` — dev-only; passed into the `frontend_dev` service for `next.config.ts`

Docker and permission pitfalls: [DOCKER_DEPLOY.md](DOCKER_DEPLOY.md).
