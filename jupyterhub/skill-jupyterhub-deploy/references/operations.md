# Operations Runbook

Substitute `<YOUR_*>` placeholders with your environment values (see `SKILL.md` for the table).

---

## Daily commands

```bash
make up            # start hub
make down          # stop hub (user containers unaffected)
make restart       # reload config (no rebuild)
make logs          # tail hub logs
make users         # list running user containers
make status        # hub container status
make shell         # exec into hub
make config-check  # validate config syntax
```

---

## Deploy from scratch

1. Ensure `traefik-network` exists: `docker network ls | grep traefik`
2. Fill LDAP values in `jupyterhub_config.py`:
```python
c.LDAPAuthenticator.server_address              = '<LDAP_HOST>'
c.LDAPAuthenticator.server_port                 = 389        # 636 for LDAPS
c.LDAPAuthenticator.lookup_dn_search_user       = '<BIND_DN>'
c.LDAPAuthenticator.lookup_dn_search_password   = '<BIND_PASSWORD>'
c.LDAPAuthenticator.user_search_base            = '<SEARCH_BASE>'
c.LDAPAuthenticator.user_attribute              = 'sAMAccountName'  # or 'uid'
c.LDAPAuthenticator.lookup_dn_user_dn_attribute = 'distinguishedName'  # or 'cn'
c.Authenticator.admin_users                     = {'first.admin'}
```
3. Update `docker-compose.yml`: Docker socket path, Traefik hostname label, volume host paths.
4. `make build` → `make up` → `make logs`
5. Confirm "JupyterHub is now running" in logs, then:
```bash
curl -sk https://<YOUR_DOMAIN>/jupyter | head -5   # expect HTML
```

---

## Add a user (pre-provision before first login)

```bash
docker exec jupyterhub python3 -c "
import os, re
def esc(n): return re.sub(r'[^a-zA-Z0-9_-]', lambda m: '-%02x' % ord(m.group()), n)
for username in ['new.user1', 'new.user2']:
    d = f'<YOUR_DEPLOY_DIR>/userdata/{esc(username)}'
    os.makedirs(d, mode=0o777, exist_ok=True)
    os.chmod(d, 0o777)
    os.chown(d, 1000, 100)
    print(f'Created: {d}')
"
```

Users are also auto-provisioned on first login via `pre_spawn_hook` in `jupyterhub_config.py`.

---

## Make a user admin

```python
# patch script — scp to remote, run, delete
path = "<YOUR_DEPLOY_DIR>/jupyterhub_config.py"
with open(path) as f: content = f.read()
content = content.replace(
    'c.Authenticator.admin_users = {"existing.admin"}',
    'c.Authenticator.admin_users = {"existing.admin", "new.admin"}'
)
with open(path, "w") as f: f.write(content)
print("Done")
```
Then `make restart`.

---

## Debug login failure

1. Add `c.JupyterHub.log_level = 'DEBUG'` to `jupyterhub_config.py`, `make restart`
2. Attempt login
3. `docker logs jupyterhub 2>&1 | grep -i "ldap\|bind\|dn\|user\|auth\|fail"`
4. Look for the exact DN being attempted

Stuck on groups? Temporarily set `c.Authenticator.allow_all = True`, restart, confirm login works.

---

## Find a user's LDAP groups

```bash
docker cp find_groups.py jupyterhub:/tmp/find_groups.py
docker exec jupyterhub python3 /tmp/find_groups.py
```

`find_groups.py` template (reads credentials from the live config — no hardcoding):
```python
import re
path = "/srv/jupyterhub/jupyterhub_config.py"
with open(path) as f: cfg = f.read()
def get(k): m = re.search(rf"c\.LDAPAuthenticator\.{k}\s*=\s*['\"]([^'\"]+)['\"]", cfg); return m.group(1) if m else None

from ldap3 import Server, Connection
c = Connection(
    Server(get("server_address"), port=int(re.search(r"server_port\s*=\s*(\d+)", cfg).group(1))),
    user=get("lookup_dn_search_user"),
    password=get("lookup_dn_search_password"),
    auto_bind=True
)
c.search(get("user_search_base"), "(sAMAccountName=<username>)", attributes=["memberOf"])
for e in c.entries: print(e)
```

---

## Patch jupyterhub_config.py safely

Never SCP the local file over the remote — it overwrites credentials.

```bash
# 1. Write patch script locally
cat > /tmp/patch.py << 'EOF'
path = "<YOUR_DEPLOY_DIR>/jupyterhub_config.py"
with open(path) as f: content = f.read()
content = content.replace("old_value", "new_value")
with open(path, "w") as f: f.write(content)
print("Done")
EOF

# 2. Copy to remote, run, clean up
scp /tmp/patch.py <YOUR_SSH_USER>@<YOUR_HOST>:/tmp/patch.py
ssh <YOUR_SSH_USER>@<YOUR_HOST> 'python3 /tmp/patch.py && rm /tmp/patch.py'

# 3. Restart
ssh <YOUR_SSH_USER>@<YOUR_HOST> 'cd <YOUR_DEPLOY_DIR> && make restart'
```

---

## Rebuild images

```bash
# Hub Dockerfile changed:
make build-hub && make restart

# User Dockerfile changed (new packages, marimo version, etc.):
make build-user
# existing running servers keep old image until user restarts their server
# new spawns immediately use the new image
```

---

## Change resource limits

Edit in `jupyterhub_config.py`:
```python
c.DockerSpawner.mem_limit = '4G'
c.DockerSpawner.cpu_limit = 2.0
```
Then `make restart`. Active servers are unaffected until they restart.

---

## Verify Traefik registration

```bash
curl -s http://localhost:8080/api/http/routers | python3 -m json.tool | grep -A5 jupyterhub
```
Expected: `"rule": "Host(...) && PathPrefix('/jupyter')"`, `"provider": "docker"`.

---

## Stop a specific user's server

```bash
# Use the escaped username (dots encoded as -2e, e.g. john.doe → john-2edoe)
docker stop jupyter-<escaped_username>
```

Hub will show the user as stopped; they can restart from the hub UI.

---

## Full cleanup

```bash
make clean-all   # removes containers, images, networks, hub DB volume
```

User data in `<YOUR_DEPLOY_DIR>/userdata/` is **not** deleted — it lives on the host filesystem.
