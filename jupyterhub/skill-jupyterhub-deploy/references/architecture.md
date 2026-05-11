# Architecture & Gotchas

## Stack

```
Browser → https://<YOUR_DOMAIN>/jupyter
              │
          Traefik v3 (container, TLS cert)
          routes via Docker labels on traefik-network
              │
          JupyterHub (container: jupyterhub)
          on: traefik-network + jupyterhub-net
          port 8000 → configurable-http-proxy (Node.js binary)
          port 8081 → Hub API
              │ DockerSpawner
          jupyter-{escaped_username} containers
          on: jupyterhub-net only
          <YOUR_APP_DIR> → /home/jovyan/work (rw)
          /scripts → /scripts (ro)
```

- Docker: rootless or standard — socket path varies (see `<YOUR_DOCKER_SOCKET>`)
- Auth: LDAP/Active Directory via ldapauthenticator 2.x, `lookup_dn=True` mode
- marimo: runs inside user containers via `jupyter-server-proxy` (marimo-jupyter-extension)

## Component versions (tested)

| Component | Version |
|-----------|---------|
| JupyterHub | 5.x |
| ldapauthenticator | 2.x |
| dockerspawner | 14.x |
| Traefik | v3.x |
| User base image | jupyter/base-notebook:latest |
| marimo | ≥0.23.4 |
| Hub Python | 3.11 |

## Image split

| Image | Built from | Purpose |
|-------|-----------|---------|
| `jupyterhub:latest` | `Dockerfile.hub` | Hub process only |
| `jupyterlab-user:latest` | `Dockerfile` | Spawned per user on login |

User image must include `jupyterhub==5.*` for the `jupyterhub-singleuser` binary.

---

## Critical gotchas

### 1. configurable-http-proxy is Node.js — not Python
Hub crashes on startup without it. `Dockerfile.hub` must include:
```dockerfile
RUN apt-get install -y nodejs npm && npm install -g configurable-http-proxy
```

### 2. DockerSpawner escapes usernames
Non-alphanumeric characters are encoded as `-%02x`. Examples:
- `john.doe` → `john-2edoe` (`.` = 0x2E)
- `jane_smith` → `jane_smith` (underscore: safe)
- `bob-jones` → `bob-jones` (hyphen: safe)

`{username}` in volume path templates uses the escaped name automatically.
In `pre_spawn_hook`, always use `spawner.escaped_name`, never `spawner.user.name`.

Compute manually:
```python
import re
def escaped(name):
    return re.sub(r'[^a-zA-Z0-9_-]', lambda m: '-%02x' % ord(m.group()), name)
```

### 3. hub_ip must be 0.0.0.0
User containers cannot reach the loopback interface. Required:
```python
c.JupyterHub.hub_ip = '0.0.0.0'
c.JupyterHub.hub_connect_ip = 'jupyterhub'  # container name on jupyterhub-net
```

### 4. Rootless Docker socket path
Standard path `/var/run/docker.sock` does not exist in rootless mode.
Find it with: `systemctl --user status docker` or `echo $DOCKER_HOST`
Mount without `:ro` — JupyterHub needs write access to create/delete containers.

### 5. Userdata directory permissions
Rootless Docker UID mapping can cause mismatches. Always apply both:
```python
os.chmod(userdir, 0o777)
os.chown(userdir, 1000, 100)  # jovyan:users
```

### 6. ldapauthenticator 2.x API changes
- `admin_groups` removed → use `c.Authenticator.admin_users = {'username'}`
- `use_ssl` deprecated → remove the line; for LDAPS use `c.LDAPAuthenticator.tls_strategy = 'before_bind'`

### 7. marimo config placement
`MarimoProxyConfig` goes in `jupyter_server_config.py` inside the **user image** — NOT in `jupyterhub_config.py`.
Required settings:
```python
c.MarimoProxyConfig.no_sandbox = True
c.MarimoProxyConfig.host = "127.0.0.1"   # override IPv6 detection
c.MarimoProxyConfig.marimo_path = "/opt/conda/bin/marimo"
```

### 8. Patching nested dicts with regex
`re.sub(r'\{.*?\}', ...)` stops at the first `}` inside a nested dict value. Use a brace-counting line parser:
```python
depth = 0
for i in range(start, len(lines)):
    depth += lines[i].count("{") - lines[i].count("}")
    if depth <= 0 and i >= start:
        end = i; break
lines[start:end+1] = [new_block]
```

---

## LDAP authentication flow (lookup_dn mode)

```
User submits username + password
    → bind as lookup_dn_search_user (service account)
    → search user_search_base for (user_attribute=username)
    → get full DN from lookup_dn_user_dn_attribute
    → bind as that DN with user's password
    → success: allow_all or group check
```

Debug by adding `c.JupyterHub.log_level = 'DEBUG'`, restarting, attempting login, and reading logs for the exact DN being attempted.

Common failures:
- `Failed to bind` → wrong DN path or wrong credentials
- `User not allowed` + `attributes:{}` → group DN wrong; temporarily use `allow_all = True`
- `IndentationError` after patching → only first line of a multi-line block was commented

---

## Network topology

| Network | Members | Purpose |
|---------|---------|---------|
| `traefik-network` | Traefik, JupyterHub | Traefik → hub port 8000 |
| `jupyterhub-net` | JupyterHub, all user containers | Hub API ↔ user servers |

Traefik never routes to user containers directly — JupyterHub's internal proxy handles that.
`jupyterhub-net` is created by `docker compose up` via the `networks:` declaration — no manual step needed.
