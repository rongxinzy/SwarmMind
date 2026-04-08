.PHONY: help install dev frontend backend restart stop status logs clean build build-ui typecheck test \
        lint lint-fix format format-check typecheck-py typecheck-js security health

# Defaults
BACKEND_DIR := .
UI_DIR := ui
PM2_NAME_API := swarmmind-api
PM2_NAME_UI := swarmmind-ui

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# ---- Install ----
install: ## Install all dependencies (backend + frontend)
	uv sync
	cd $(UI_DIR) && pnpm install

# ---- Build ----
build: format-py ## Build frontend (UI) for production (auto-formats Python first)
	cd $(UI_DIR) && pnpm run build

build-ui: build ## Alias for build

# ---- Lint & Format ----
lint: lint-py lint-js ## Run all linters (Python + JS/TS)

lint-py: ## Run Python linter (Ruff)
	@echo "🔍 Running Python linter (Ruff)..."
	uv run ruff check swarmmind/ tests/

lint-js: ## Run JavaScript/TypeScript linter (ESLint)
	@echo "🔍 Running JavaScript/TypeScript linter (ESLint)..."
	cd $(UI_DIR) && pnpm run lint

lint-fix: lint-fix-py lint-fix-js ## Fix all auto-fixable lint issues

lint-fix-py: ## Fix Python lint issues (Ruff)
	@echo "🔧 Fixing Python lint issues..."
	uv run ruff check --fix swarmmind/ tests/

lint-fix-js: ## Fix JavaScript/TypeScript lint issues (ESLint)
	@echo "🔧 Fixing JavaScript/TypeScript lint issues..."
	cd $(UI_DIR) && pnpm run lint:fix

format: format-py format-js ## Format all code

format-py: ## Format Python code (Ruff)
	@echo "✨ Formatting Python code..."
	uv run ruff format swarmmind/ tests/

format-js: ## Format JavaScript/TypeScript code (Prettier via ESLint)
	@echo "✨ JavaScript/TypeScript formatting handled by ESLint..."

format-check: format-check-py ## Check if all code is formatted

format-check-py: ## Check Python code formatting (Ruff)
	@echo "🔍 Checking Python code formatting..."
	uv run ruff format --check swarmmind/ tests/

# ---- Type Check ----
typecheck: typecheck-py typecheck-js ## Run type checks for all code

typecheck-py: ## Run Python type checker (mypy)
	@echo "🔍 Running Python type checker (mypy)..."
	uv run mypy swarmmind/

typecheck-js: ## Run TypeScript type check
	@echo "🔍 Running TypeScript type check..."
	cd $(UI_DIR) && pnpm run typecheck

# ---- Security ----
security: security-py security-js ## Run all security checks

security-py: ## Run Python security checks (bandit)
	@echo "🔒 Running Python security checks (bandit)..."
	uv run bandit -r swarmmind/ -f json -o bandit-report.json || true
	uv run bandit -r swarmmind/

security-js: ## Run JavaScript security audit (npm audit)
	@echo "🔒 Running JavaScript security audit..."
	cd $(UI_DIR) && pnpm audit --audit-level moderate

# ---- Test ----
test: ## Run Python backend tests with coverage
	@echo "🧪 Running Python tests with coverage..."
	uv run python -m pytest tests/ -v

test-fast: ## Run Python tests (fast mode, no coverage)
	@echo "🧪 Running Python tests (fast mode)..."
	uv run python -m pytest tests/ -v --no-cov -x

# ---- Health Check ----
health: ## Run all health checks (lint, typecheck, security, test)
	@echo "🏥 Running full health check..."
	$(MAKE) lint
	$(MAKE) typecheck
	$(MAKE) security
	$(MAKE) test
	@echo "✅ All health checks passed!"

# ---- CI ----
ci: install format-check lint typecheck security test ## Full CI pipeline
	@echo "✅ CI pipeline completed successfully!"

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
restart: ## Restart both services (restart to pick up code changes and .env updates)
	pm2 restart $(PM2_NAME_API) --update-env 2>/dev/null || pm2 start "uv run python -m swarmmind.api.supervisor" --name=$(PM2_NAME_API) --cwd=$(BACKEND_DIR); \
	pm2 delete $(PM2_NAME_UI) 2>/dev/null; \
	pm2 start "pnpm run dev" --name=$(PM2_NAME_UI) --cwd=$(UI_DIR)

restart-api: ## Restart backend only (--update-env picks up .env changes)
	pm2 restart $(PM2_NAME_API) --update-env 2>/dev/null || pm2 start "uv run python -m swarmmind.api.supervisor" --name=$(PM2_NAME_API) --cwd=$(BACKEND_DIR)

restart-ui: ## Recreate frontend only so PM2 always uses the current repo cwd
	@pm2 delete $(PM2_NAME_UI) 2>/dev/null; \
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
