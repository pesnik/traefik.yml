# Integrated storage (Raft) — no external backend dependency.
# /vault/file is pre-created vault:vault in the image so the named
# volume inherits correct ownership without a chown step.
storage "raft" {
  path    = "/vault/file"
  node_id = "vault-node-1"
}

listener "tcp" {
  address     = "0.0.0.0:8200"
  # TLS terminated by Traefik — acceptable for local/homelab use.
  # For production, set tls_disable = false and provide cert/key.
  tls_disable = true
}

# Must match the public URL Traefik exposes so Vault issues correct redirects
api_addr     = "http://vault.localhost"
cluster_addr = "http://vault:8201"

ui = true

# Leave mlock enabled — paired with IPC_LOCK cap in compose
disable_mlock = false
