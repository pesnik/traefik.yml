import os

# ── Networking ────────────────────────────────────────────────────────────────
c.JupyterHub.ip = '0.0.0.0'
c.JupyterHub.port = 8000
c.JupyterHub.base_url = '/jupyter/'

# Hub API must be reachable by user containers across Docker networks
c.JupyterHub.hub_ip = '0.0.0.0'
c.JupyterHub.hub_connect_ip = 'jupyterhub'  # Docker DNS via container name

# ── DockerSpawner ─────────────────────────────────────────────────────────────
c.JupyterHub.spawner_class = 'dockerspawner.DockerSpawner'
c.DockerSpawner.image = 'jupyterlab-user:latest'

# Network shared between hub and user containers
c.DockerSpawner.network_name = 'jupyterhub-net'

c.DockerSpawner.default_url = '/lab'
c.DockerSpawner.remove = True

# Per-user persistent volume + optional shared read-only directory.
# {username} is the DockerSpawner-escaped name (e.g. john.doe → john-2edoe).
c.DockerSpawner.volumes = {
    '<YOUR_DEPLOY_DIR>/userdata/{username}': '/home/jovyan/work',
    '/scripts': {'bind': '/scripts', 'mode': 'ro'},
}

c.DockerSpawner.mem_limit = '4G'
c.DockerSpawner.cpu_limit = 2.0
c.DockerSpawner.name_template = 'jupyter-{username}'


async def pre_spawn_hook(spawner):
    # spawner.escaped_name matches the {username} in volume paths above.
    # Never use spawner.user.name here — it won't match for names with dots/special chars.
    username = spawner.escaped_name
    userdir = f'<YOUR_DEPLOY_DIR>/userdata/{username}'
    os.makedirs(userdir, mode=0o777, exist_ok=True)
    os.chmod(userdir, 0o777)
    os.chown(userdir, 1000, 100)  # jovyan:users

c.Spawner.pre_spawn_hook = pre_spawn_hook

# ── LDAP / Active Directory authentication ────────────────────────────────────
c.JupyterHub.authenticator_class = 'ldapauthenticator.LDAPAuthenticator'

c.LDAPAuthenticator.server_address = '<LDAP_HOST>'
c.LDAPAuthenticator.server_port = 389              # use 636 + tls_strategy for LDAPS

# lookup_dn=True: bind as service account first, search for the user DN, then
# bind as that DN. Required for Active Directory when you cannot construct the
# user DN directly from the username alone.
c.LDAPAuthenticator.lookup_dn = True
c.LDAPAuthenticator.lookup_dn_search_user = '<BIND_DN>'
c.LDAPAuthenticator.lookup_dn_search_password = '<BIND_PASSWORD>'
c.LDAPAuthenticator.user_search_base = '<SEARCH_BASE>'
c.LDAPAuthenticator.user_attribute = 'sAMAccountName'         # uid for OpenLDAP
c.LDAPAuthenticator.lookup_dn_user_dn_attribute = 'distinguishedName'  # cn for OpenLDAP

# Restrict to specific AD groups (comment out to allow all authenticated users)
# c.LDAPAuthenticator.allowed_groups = [
#     'CN=JupyterUsers,OU=Groups,<SEARCH_BASE>',
# ]

# Allow all authenticated LDAP users (use with or instead of allowed_groups)
c.Authenticator.allow_all = True

# Grant admin rights to specific usernames
c.Authenticator.admin_users = {'first.admin'}

# ── Persistence ────────────────────────────────────────────────────────────────
c.JupyterHub.db_url = 'sqlite:////srv/jupyterhub/jupyterhub.sqlite'
c.JupyterHub.cookie_secret_file = '/srv/jupyterhub/jupyterhub_cookie_secret'

# ── Idle culling (optional) ────────────────────────────────────────────────────
# Uncomment to shut down servers idle for >1 hour
# c.JupyterHub.services = [{
#     'name': 'idle-culler',
#     'command': ['python3', '-m', 'jupyterhub_idle_culler', '--timeout=3600'],
# }]
