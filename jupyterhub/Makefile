COMPOSE  = docker compose
HUB_IMG  = jupyterhub:latest
USER_IMG = jupyterlab-user:latest

.DEFAULT_GOAL := help

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ── Build ─────────────────────────────────────────────────────────────────────

build: build-hub build-user ## Build both hub and user images

build-hub: ## Build JupyterHub image
	docker build -t $(HUB_IMG) -f Dockerfile.hub .

build-user: ## Build user JupyterLab image (with marimo)
	docker build -t $(USER_IMG) -f Dockerfile .

# ── Lifecycle ─────────────────────────────────────────────────────────────────

up: ## Start JupyterHub (detached)
	$(COMPOSE) up -d

down: ## Stop and remove JupyterHub container (user containers are unaffected)
	$(COMPOSE) down

restart: ## Restart JupyterHub (picks up config changes)
	$(COMPOSE) restart jupyterhub

stop-all: ## Stop JupyterHub AND all active user containers
	$(COMPOSE) down
	docker ps --filter "name=jupyter-" -q | xargs -r docker stop

# ── Observability ─────────────────────────────────────────────────────────────

logs: ## Tail JupyterHub logs (Ctrl-C to exit)
	$(COMPOSE) logs -f jupyterhub

status: ## Show hub container status
	$(COMPOSE) ps

users: ## List all running user server containers
	@docker ps --filter "name=jupyter-" --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"

# ── Development / debug ───────────────────────────────────────────────────────

shell: ## Open a shell inside the hub container
	docker exec -it jupyterhub bash

config-check: ## Validate jupyterhub_config.py syntax
	docker run --rm \
		-v $(PWD)/jupyterhub_config.py:/srv/jupyterhub/jupyterhub_config.py:ro \
		$(HUB_IMG) \
		python3 -c "import jupyterhub; exec(open('/srv/jupyterhub/jupyterhub_config.py').read()); print('Config OK')"

# ── Cleanup ───────────────────────────────────────────────────────────────────

clean: down ## Remove containers, networks, and dangling images (keeps volumes)
	docker image rm -f $(HUB_IMG) $(USER_IMG) 2>/dev/null || true
	docker network rm jupyterhub-net 2>/dev/null || true

clean-all: clean ## Full clean including persistent hub state volume (WARNING: loses DB + sessions)
	docker volume rm jupyterlab_jupyterhub-data 2>/dev/null || true

.PHONY: help build build-hub build-user up down restart stop-all \
        logs status users shell config-check clean clean-all
