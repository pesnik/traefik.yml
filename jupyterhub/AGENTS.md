# JupyterHub Deployment Runbook for AI Agents

Complete knowledge base for deploying and operating this JupyterHub instance. No external research required.

---

## Architecture

```
Browser → https://<YOUR_DOMAIN>/jupyter
              │
          Traefik v3 (container, port 443)
          TLS cert (wildcard or per-domain)
          label routing via Docker socket
              │
          JupyterHub container (jupyterhub-net + traefik-network)
          port 8000 → configurable-http-proxy
          port 8081 → Hub API
              │ DockerSpawner
          jupyter-{escaped_username} containers
          each on jupyterhub-net
          <YOUR_APP_DIR> → /home/jovyan/work (rw)
          /scripts → /scripts (ro)
```

## Component versions (tested)
- JupyterHub: 5.x
- ldapauthenticator: 2.x
- dockerspawner: 14.x
- Traefik: v3.x
- User base image: jupyter/base-notebook:latest
- marimo: ≥0.23.4

---

## Fresh deployment

### Prerequisites
- Docker running on target server (rootless or standard)
- `traefik-network` Docker network already exists
- Traefik container running with Docker provider
- TLS cert available

### Step 1 — Configure
Fill these values in `jupyterhub_config.py`:
```python
c.LDAPAuthenticator.server_address            = '<LDAP_HOST>'
c.LDAPAuthenticator.server_port               = 389        # 636 for LDAPS
c.LDAPAuthenticator.lookup_dn_search_user     = '<BIND_DN>'
c.LDAPAuthenticator.lookup_dn_search_password = '<BIND_PASSWORD>'
c.LDAPAuthenticator.user_search_base          = '<SEARCH_BASE>'
c.LDAPAuthenticator.user_attribute            = 'sAMAccountName'  # or 'uid' for OpenLDAP
c.LDAPAuthenticator.lookup_dn_user_dn_attribute = 'distinguishedName'  # or 'cn' for OpenLDAP
c.Authenticator.admin_users                   = {'first.admin'}
```

Also update `docker-compose.yml`:
- Docker socket path
- Traefik hostname label
- Volume host paths

### Step 2 — Build and start
```bash
make build    # builds jupyterhub:latest and jupyterlab-user:latest
make up       # starts hub, creates jupyterhub-net, registers with Traefik
make logs     # watch for "JupyterHub is now running"
```

### Step 3 — Verify
```bash
# Traefik registered the route?
curl -s http://localhost:8080/api/http/routers | python3 -m json.tool | grep -A3 jupyterhub

# Hub is up?
curl -k https://<YOUR_DOMAIN>/jupyter
```

---

## LDAP authentication flow (lookup_dn mode)

```
User enters username + password
    │
Bind as lookup_dn_search_user with lookup_dn_search_password
    │
Search user_search_base for (user_attribute=username)
    │
Get user's full DN from lookup_dn_user_dn_attribute
    │
Bind as that DN with the user's password
    │  success → allow_all or group check
    │  fail    → "Invalid username or password"
```

### Debugging login failures

**"Failed to bind"** — credentials wrong or DN path wrong.
Enable debug: add `c.JupyterHub.log_level = 'DEBUG'`, restart, try login, read logs for exact DN attempted.

**"User not allowed" + `attributes:{}`** — auth succeeded but group check failed.
Set `c.Authenticator.allow_all = True` temporarily. Once login works, query the correct groups:
```bash
docker exec jupyterhub python3 -c "
from ldap3 import Server, Connection
c = Connection(Server('<LDAP_HOST>'), user='<BIND_DN>', password='<BIND_PW>', auto_bind=True)
c.search('<SEARCH_BASE>', '(sAMAccountName=<username>)', attributes=['memberOf'])
for e in c.entries: print(e)
"
```

---

## DockerSpawner username escaping — the #1 gotcha

DockerSpawner escapes non-alphanumeric characters for container names and volume paths.

| Username | Escaped | Notes |
|----------|---------|-------|
| `john.doe` | `john-2edoe` | `.` = 0x2E → `-2e` |
| `jane_smith` | `jane_smith` | underscore is safe |
| `bob-jones` | `bob-jones` | hyphen is safe |

**Always use `spawner.escaped_name` in `pre_spawn_hook`**, never `spawner.user.name`.
The `{username}` in volume templates uses the escaped name automatically.

Compute manually:
```python
import re
def escaped(name):
    return re.sub(r'[^a-zA-Z0-9_-]', lambda m: '-%02x' % ord(m.group()), name)
```

---

## Adding users

Pre-create directory before first login:
```bash
docker exec jupyterhub python3 -c "
import os, re
def esc(n): return re.sub(r'[^a-zA-Z0-9_-]', lambda m: '-%02x' % ord(m.group()), n)
for username in ['new.user']:
    d = f'<YOUR_APP_DIR>/jupyterlab/userdata/{esc(username)}'
    os.makedirs(d, mode=0o777, exist_ok=True)
    os.chmod(d, 0o777)
    os.chown(d, 1000, 100)
    print(d)
"
```
Users are also auto-provisioned on first login via `pre_spawn_hook`.

---

## Patching jupyterhub_config.py safely

Never overwrite the remote file — it contains credentials. Patch in-place:

```python
# save as /tmp/patch.py, scp to remote, run, delete
path = "/path/to/jupyterhub_config.py"
with open(path) as f:
    content = f.read()
content = content.replace("old_line", "new_line")
with open(path, "w") as f:
    f.write(content)
print("Done")
```

When patching multi-line dicts, use a brace-counting parser — `re.sub` with `.*?` stops at the first `}` inside nested dicts.

---

## marimo integration

- `marimo-jupyter-extension` + `jupyter-server-proxy` installed in the **user image** (`Dockerfile`)
- `jupyterhub` package also in user image (provides `jupyterhub-singleuser` binary)
- `MarimoProxyConfig` settings in `jupyter_server_config.py` — `COPY`d into user image at `/etc/jupyter/`
- `no_sandbox = True` required (no uv/venv in container)
- `host = "127.0.0.1"` required (overrides IPv6 detection)
- JupyterHub sets `base_url` automatically — do not hardcode it

---

## Dockerfile.hub requirements

`configurable-http-proxy` is a Node.js binary — **hub crashes on startup without it**:
```dockerfile
RUN apt-get install -y nodejs npm && npm install -g configurable-http-proxy
```

---

## Network topology

| Network | Who joins | Purpose |
|---------|-----------|---------|
| `traefik-network` | Traefik, JupyterHub | Traefik → hub port 8000 |
| `jupyterhub-net` | JupyterHub, all user containers | Hub API ↔ user servers |

---

## Rootless Docker notes

Socket path example: `/run/user/1000/docker.sock`
Mount in `docker-compose.yml`:
```yaml
- /run/user/<UID>/docker.sock:/var/run/docker.sock
```
Do not add `:ro` — JupyterHub needs write access.
Use `chmod 777` on userdata dirs to avoid cross-namespace permission issues.

---

## Operations reference

| Task | Command |
|------|---------|
| Start | `make up` |
| Stop | `make down` |
| Restart (config change) | `make restart` |
| Rebuild hub | `make build-hub && make restart` |
| Rebuild user image | `make build-user` |
| Logs | `make logs` |
| List user servers | `make users` |
| Shell in hub | `make shell` |
| Validate config | `make config-check` |
| Clean (keeps data) | `make clean` |
| Full reset | `make clean-all` |
