# Web platform edge URL

With Docker Compose, open the app at:

- **http://localhost:8080** — reverse proxy (Caddy) to Next (`/` and `/api/*`) and Evennia (`/auth/*`, `/webclient/*`, static/media).

Direct ports remain available for debugging:

- **http://localhost:3000** — Next only
- **http://localhost:4001** — Evennia portal only

Set `EVENNIA_BASE_URL=http://evennia:4001` for the Next container (server-side BFF). Browsers should use the edge URL so session cookies and CSRF share one origin.

Environment variables (see `.env.example`):

- `REDIS_URL` — Django cache + JWT denylist (Evennia container)
- `AURNOM_JWT_SECRET` — signing key for UI JWTs (required in production)
- `AURNOM_TRUSTED_PROXY_HOST` — hostname of the edge service (`edge` in compose) for `UPSTREAM_IPS`
