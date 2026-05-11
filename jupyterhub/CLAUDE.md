# JupyterHub Multi-User — Claude Code Context

## What this is
Production multi-user JupyterLab + marimo on a single server, running as Docker containers behind Traefik v3. Users authenticate via LDAP/Active Directory. Each user gets an isolated JupyterLab container spawned on demand by JupyterHub.

## Files
| File | Purpose |
|------|---------|
| `Dockerfile.hub` | JupyterHub image — python:3.11-slim + Node.js + configurable-http-proxy + jupyterhub + ldapauthenticator + dockerspawner |
| `Dockerfile` | User image — jupyter/base-notebook + jupyterhub + marimo + marimo-jupyter-extension + jupyter-server-proxy |
| `jupyter_server_config.py` | Injected into user containers — MarimoProxyConfig settings |
| `jupyterhub_config.py` | Hub config — DockerSpawner, LDAP (lookup_dn mode), pre_spawn_hook, resource limits |
| `docker-compose.yml` | Hub service + networks + Traefik labels |
| `Makefile` | `make build`, `make up`, `make logs`, `make users`, `make restart` |

## Key operations
```bash
make build       # build both images (hub + user)
make up          # start hub
make restart     # pick up jupyterhub_config.py changes (no rebuild needed)
make logs        # tail hub logs
make users       # list running user containers
make shell       # exec into hub container
```

## Adapting to a new environment
Replace these values before deploying:
- `<YOUR_DOMAIN>` — public hostname (e.g. `jupyter.example.com`)
- `<YOUR_APP_DIR>` — base data directory on the host (e.g. `/app`)
- `<YOUR_DOCKER_SOCKET>` — Docker socket path (rootless: `/run/user/<UID>/docker.sock`)
- `<YOUR_SSH_USER>` — OS user running Docker

## CRITICAL gotchas (do not repeat these mistakes)
1. **configurable-http-proxy** must be installed via npm in `Dockerfile.hub` — hub crashes without it.
2. **DockerSpawner escapes usernames**: `.` → `-2e`, so `john.doe` → `john-2edoe`. Always use `spawner.escaped_name` in `pre_spawn_hook`, never `spawner.user.name`.
3. **`hub_ip = '0.0.0.0'`** is required (not `127.0.0.1`) so user containers can reach the hub API across Docker networks.
4. **`hub_connect_ip = 'jupyterhub'`** — the container name, not an IP. Docker DNS resolves it on `jupyterhub-net`.
5. **`jupyterhub-net`** is created by `docker compose up` via the `networks:` declaration — no manual step needed.
6. **marimo config** (`MarimoProxyConfig`) belongs in `jupyter_server_config.py` inside the USER image, not in `jupyterhub_config.py`.
7. **ldapauthenticator 2.x** dropped `admin_groups` and deprecated `use_ssl`. Use `c.Authenticator.admin_users` and `tls_strategy` instead.
8. **`lookup_dn = True`** mode: uses a service account to search LDAP first, then binds as the found user. Required for AD when you can't construct the user DN directly.
9. **Rootless Docker**: socket path differs from standard `/var/run/docker.sock`. Mount it without `:ro` — JupyterHub needs write access to spawn containers.
10. **Do not overwrite `jupyterhub_config.py`** after LDAP credentials are filled in — patch it in-place via Python scripts to avoid wiping secrets.
