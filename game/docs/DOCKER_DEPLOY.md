# Docker build and run (permissions and context)

## `~/.docker` ownership

If you ever run Docker as root (`sudo docker …`), files under `~/.docker` may be owned by root. Your user then sees errors such as:

`open …/.docker/buildx/.lock: permission denied`

Fix:

```bash
sudo chown -R "$USER:$USER" ~/.docker
```

Prefer using the **`docker` group** (no `sudo`) for routine `docker compose` work:

```bash
sudo usermod -aG docker "$USER"
# log out and back in
```

## Bind mounts and root-owned files

Evennia runs as root inside the container by default. Python may create **`__pycache__`** directories on the host under bind-mounted paths (e.g. `evennia/`, `game/`) **owned by root**. That can cause:

- Host tools failing to read those trees
- **`docker compose build`** failing with `error from sender: open …/__pycache__: permission denied` when the build context sender runs as a normal user

Fix ownership on the repo (or at least `evennia/` and `game/`):

```bash
sudo chown -R "$USER:$USER" /path/to/aurnom
```

The repo root `.dockerignore` file excludes `**/__pycache__/` and `*.py[cod]` from the **Evennia image** context so Docker does not need to read those paths when building.

## Do not widen trust blindly

Do **not** add your entire Docker bridge CIDR to `UPSTREAM_IPS` in Django settings. Trusted proxy entries must be **specific** reverse-proxy hops (see [WEB_PLATFORM_EDGE.md](WEB_PLATFORM_EDGE.md)).
