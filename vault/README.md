# Vault

HashiCorp Vault running behind Traefik, accessible at `http://vault.localhost`.

## Stack

- **Image**: `hashicorp/vault:latest`
- **Storage**: Raft integrated storage (no external dependencies)
- **Proxy**: Traefik on `traefik_default` network
- **Security**: non-root user, `cap_drop: ALL`, `IPC_LOCK`, `no-new-privileges`

## Directory structure

```
vault/
├── compose.yml
├── config/
│   └── vault.hcl        # server config (mounted read-only)
└── policies/            # HCL policy files (mounted read-only)
```

Named Docker volumes:
- `vault_vault-file` — Raft storage
- `vault_vault-logs` — audit log output

## First-time setup

**1. Start**

```bash
docker compose up -d
```

**2. Initialize** — generates unseal keys and root token. Shown once, save them somewhere safe.

```bash
docker exec vault-vault-1 vault operator init \
  -key-shares=3 \
  -key-threshold=2 \
  -address=http://127.0.0.1:8200
```

Output:

```
Unseal Key 1: <key1>
Unseal Key 2: <key2>
Unseal Key 3: <key3>

Initial Root Token: hvs.XXXXXXXXXXXX
```

**3. Unseal** — run twice with any 2 of the 3 keys.

```bash
docker exec -it vault-vault-1 vault operator unseal -address=http://127.0.0.1:8200
# Enter key when prompted — repeat with a second key
```

**4. Enable audit logging** — requires a root token, do this once after unsealing.

```bash
docker exec vault-vault-1 env VAULT_TOKEN=<root-token> \
  vault audit enable file file_path=/vault/logs/audit.log \
  -address=http://127.0.0.1:8200
```

Vault is now available at `http://vault.localhost`.

## Day-to-day operations

```bash
# Start / stop
docker compose up -d
docker compose down

# Logs
docker compose logs -f vault

# Shell inside container
docker exec -it vault-vault-1 sh

# Check seal status
docker exec vault-vault-1 vault status -address=http://127.0.0.1:8200
```

> Vault re-seals on every restart. Unseal again with step 3 after each `docker compose up`.

## Security notes

| Control | Value |
|---|---|
| User | `vault` (uid 100, gid 1000) — never root |
| Capabilities | `IPC_LOCK` only, all others dropped |
| Privilege escalation | blocked via `no-new-privileges` |
| mlock | enabled — secrets cannot swap to disk |
| Config mount | read-only |
| TLS | terminated by Traefik; enable in `vault.hcl` for production |

## Adding policies

Place `.hcl` files in `policies/` — they are mounted read-only at `/vault/policies` inside the container.

```bash
vault policy write my-policy /vault/policies/my-policy.hcl
```

## Traefik integration note

Traefik v3 skips containers Docker marks as `unhealthy`. The healthcheck uses
`vault status` rather than an HTTP probe because BusyBox wget ignores query
parameters (`?sealedok=true` etc.), causing false unhealthy states. `vault
status` exits `2` when sealed (not an error) and `1` only on connection
failure — so Traefik sees the container as healthy throughout the
init/unseal lifecycle.

## Upgrading

Raft storage is forward-compatible across minor versions. To upgrade:

```bash
docker compose pull
docker compose up -d
# unseal after restart
```
