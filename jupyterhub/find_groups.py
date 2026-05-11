import re, sys

# Pull connection details from the live config (no manual input needed)
with open("/srv/jupyterhub/jupyterhub_config.py") as f:
    cfg = f.read()

def get(key):
    m = re.search(rf"c\.LDAPAuthenticator\.{key}\s*=\s*['\"]([^'\"]+)['\"]", cfg)
    return m.group(1) if m else None

host     = get("server_address")
port     = int(re.search(r"c\.LDAPAuthenticator\.server_port\s*=\s*(\d+)", cfg).group(1) or 389)
bind_dn  = get("lookup_dn_search_user")
bind_pw  = get("lookup_dn_search_password")
base     = get("user_search_base")
u_attr   = get("user_attribute") or "sAMAccountName"

if not all([host, bind_dn, bind_pw, base]):
    sys.exit("Could not parse config — check keys")

from ldap3 import Server, Connection, SUBTREE, ALL_ATTRIBUTES

s = Server(host, port=port)
c = Connection(s, user=bind_dn, password=bind_pw, auto_bind=True)

# Find the user's DN
TARGET_USER = "<username>"   # replace with the sAMAccountName to look up

c.search(base, f"({u_attr}={TARGET_USER})", attributes=["distinguishedName", "cn", "memberOf"])
if not c.entries:
    sys.exit(f"User {TARGET_USER} not found under {base}")

user_entry = c.entries[0]
user_dn = str(user_entry.entry_dn)
print(f"\nUser DN: {user_dn}")

# Print groups from memberOf if available
if hasattr(user_entry, "memberOf") and user_entry.memberOf:
    print("\nGroups (memberOf):")
    for g in user_entry.memberOf:
        print(f"  {g}")
else:
    # Fallback: search groups that have this user as member
    print("\nmemberOf not returned, searching groups directly...")
    c.search(base, f"(|(member={user_dn})(uniqueMember={user_dn}))",
             attributes=["cn", "distinguishedName"])
    for e in c.entries:
        print(f"  {e.entry_dn}")
