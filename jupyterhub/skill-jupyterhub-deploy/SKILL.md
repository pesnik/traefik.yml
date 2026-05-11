---
name: jupyterhub-deploy
description: Deploy, configure, debug, and operate a multi-user JupyterHub + JupyterLab + marimo platform running on Docker behind Traefik with LDAP/Active Directory authentication. Use this skill when asked to: set up JupyterHub from scratch, add or remove users, fix login failures or LDAP authentication errors, change resource limits, update volumes or mounts, rebuild Docker images, configure marimo integration, patch jupyterhub_config.py without leaking secrets, or perform any maintenance on the Jupyter platform. Also use when asked about the architecture or how the stack works.
---

## What this skill covers

Multi-user JupyterLab + marimo on a single Docker host, behind Traefik v3, authenticated via LDAP/AD. Each user gets an isolated JupyterLab container spawned on demand by JupyterHub (DockerSpawner).

All technical detail is in `references/` — read the relevant file before acting.

- `references/architecture.md` — stack diagram, component versions, all critical gotchas
- `references/operations.md` — copy-paste recipes for every common task

## Deployment context

Fill these into your environment before using recipes from `references/`:

| Placeholder | Your value |
|-------------|-----------|
| `<YOUR_HOST>` | server IP or hostname |
| `<YOUR_SSH_USER>` | OS user running Docker |
| `<YOUR_DOMAIN>` | public FQDN for the hub |
| `<YOUR_APP_DIR>` | host directory mounted as user workspace |
| `<YOUR_DOCKER_SOCKET>` | Docker socket path (rootless: `/run/user/<UID>/docker.sock`) |
| `<YOUR_DEPLOY_DIR>` | directory containing these files on the server |

## Golden rules — memorise before touching anything

- **Never overwrite `jupyterhub_config.py`** after LDAP credentials are filled in. Patch in-place via Python scripts.
- **Use `spawner.escaped_name`** in `pre_spawn_hook` — DockerSpawner encodes `.` as `-2e` in container names and volume paths.
- **`hub_ip = '0.0.0.0'`** — never `127.0.0.1`; user containers must reach the Hub API across Docker networks.
- **Rootless Docker socket** is not `/var/run/docker.sock` — check the actual path and mount without `:ro`.
- **Patching nested dicts**: regex with `.*?` stops at the first `}`. Use a brace-counting line parser instead.
- After any config change: `make restart`. After any Dockerfile change: `make build-hub` or `make build-user`, then `make restart`.
