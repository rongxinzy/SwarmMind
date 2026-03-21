.PHONY: help install dev frontend backend restart stop status logs clean

# Defaults
BACKEND_DIR := .
UI_DIR := ui
PM2_NAME_API := swarmmind-api
PM2_NAME_UI := swarmmind-ui

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

# ---- Install ----
install: ## Install all dependencies (backend + frontend)
	uv sync
	cd $(UI_DIR) && pnpm install

# ---- Dev ----
dev: ## Run both backend and frontend via PM2 (background)
	@pm2 delete $(PM2_NAME_API) $(PM2_NAME_UI) 2>/dev/null; \
	pm2 start "uv run python -m swarmmind.api.supervisor" --name=$(PM2_NAME_API) --cwd=$(BACKEND_DIR); \
	pm2 start "pnpm run dev" --name=$(PM2_NAME_UI) --cwd=$(UI_DIR); \
	pm2 logs --nostream --lines 5

frontend: ## Run frontend only via PM2
	@pm2 delete $(PM2_NAME_UI) 2>/dev/null; \
	pm2 start "pnpm run dev" --name=$(PM2_NAME_UI) --cwd=$(UI_DIR)

backend: ## Run backend only via PM2
	@pm2 delete $(PM2_NAME_API) 2>/dev/null; \
	pm2 start "uv run python -m swarmmind.api.supervisor" --name=$(PM2_NAME_API) --cwd=$(BACKEND_DIR)

# ---- PM2 ----
# IMPORTANT: Use `pm2 stop` to stop processes gracefully. DO NOT use `kill -9` on PM2 processes.
# `kill -9` kills the process but PM2 will auto-restart it, creating a zombie loop.
# Only use `kill -9` as a last resort if PM2 stop fails.
restart: ## Restart both services (delete + start to pick up code changes)
	pm2 delete $(PM2_NAME_API) $(PM2_NAME_UI) 2>/dev/null; \
	pm2 start "uv run python -m swarmmind.api.supervisor" --name=$(PM2_NAME_API) --cwd=$(BACKEND_DIR); \
	pm2 start "pnpm run dev" --name=$(PM2_NAME_UI) --cwd=$(UI_DIR)

stop: ## Stop both services gracefully (use this, NOT kill -9)
	pm2 stop $(PM2_NAME_API) $(PM2_NAME_UI)

status: ## Show PM2 status
	pm2 status

logs: ## Tail PM2 logs
	pm2 logs

logs-api: ## Tail backend logs only
	pm2 logs $(PM2_NAME_API) --nostream --lines 30

logs-ui: ## Tail frontend logs only
	pm2 logs $(PM2_NAME_UI) --nostream --lines 30

clean: ## Stop and delete all PM2 processes
	pm2 delete all 2>/dev/null; echo "All PM2 processes deleted"
