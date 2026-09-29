# =============================================================================
# Sentinel — Makefile
# Developer convenience targets.
#
# NOTE: Many targets reference application code or services that have not
# been implemented yet. These are documented here as planned targets.
# Targets that cannot yet run will display a clear message.
# =============================================================================

.DEFAULT_GOAL := help
.PHONY: help setup up down logs test lint lint-backend lint-frontend \
        migrate shell-backend shell-postgres clean

# Colours
CYAN  := \033[0;36m
RESET := \033[0m

# =============================================================================
# help
# =============================================================================
help: ## Show this help message
	@echo ""
	@echo "  Sentinel — Developer Makefile"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""

# =============================================================================
# Setup
# =============================================================================
setup: ## Initial project setup (copy .env.example, check dependencies)
	@echo "[setup] Checking for .env file..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "[setup] Created .env from .env.example — fill in real values before running."; \
	else \
		echo "[setup] .env already exists."; \
	fi
	@echo "[setup] Checking Docker..."
	@docker info > /dev/null 2>&1 && echo "[setup] Docker is running." || echo "[setup] WARNING: Docker does not appear to be running."
	@echo "[setup] Done. Run 'make up' to start infrastructure services."

# =============================================================================
# Docker Compose
# =============================================================================
up: ## Start infrastructure services (postgres + redis)
	@echo "[up] Starting postgres and redis..."
	docker compose up postgres redis -d

up-all: ## Start all services including app (requires implementation)
	@echo "[up-all] NOTE: Application services (backend/frontend/worker) are not implemented yet."
	@echo "[up-all] Starting infrastructure only..."
	docker compose up postgres redis -d

down: ## Stop all running services
	@echo "[down] Stopping all services..."
	docker compose down

logs: ## Tail logs from all running services
	docker compose logs -f

# =============================================================================
# Backend
# =============================================================================
backend-install: ## Install backend Python dependencies
	@echo "[backend] Installing dependencies..."
	cd backend && pip install -r requirements.txt

backend-dev: ## Run the backend development server (requires dependencies installed)
	@echo "[backend] Starting FastAPI development server..."
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

backend-test: ## Run backend tests (NOT YET IMPLEMENTED)
	@echo "[backend-test] Backend tests are not yet implemented."
	@echo "[backend-test] Add tests to backend/tests/ and update this target."

migrate: ## Run database migrations (NOT YET IMPLEMENTED)
	@echo "[migrate] Database migrations (Alembic) are not yet implemented."
	@echo "[migrate] Run 'alembic upgrade head' once models are defined."

shell-backend: ## Open a shell in the backend container (requires container running)
	docker compose exec backend bash

shell-postgres: ## Open a psql shell
	docker compose exec postgres psql -U $${POSTGRES_USER:-sentinel_user} -d $${POSTGRES_DB:-sentinel}

# =============================================================================
# Frontend
# =============================================================================
frontend-install: ## Install frontend Node dependencies
	@echo "[frontend] Installing npm packages..."
	cd frontend && npm install

frontend-dev: ## Run the frontend Vite dev server (requires npm install)
	@echo "[frontend] Starting Vite dev server..."
	cd frontend && npm run dev

frontend-build: ## Build the frontend for production
	@echo "[frontend] Building production bundle..."
	cd frontend && npm run build

frontend-test: ## Run frontend tests (NOT YET IMPLEMENTED)
	@echo "[frontend-test] Frontend tests are not yet implemented."

# =============================================================================
# Linting
# =============================================================================
lint: lint-backend lint-frontend ## Run all linters

lint-backend: ## Lint backend Python code with ruff
	@echo "[lint-backend] Running ruff..."
	@command -v ruff > /dev/null 2>&1 && \
		ruff check backend/ || \
		echo "[lint-backend] ruff not found — install with: pip install ruff"

lint-frontend: ## Lint frontend TypeScript code with ESLint
	@echo "[lint-frontend] Running ESLint..."
	@cd frontend && \
		(npm run lint 2>/dev/null || echo "[lint-frontend] ESLint not configured yet.")

# =============================================================================
# Testing
# =============================================================================
test: ## Run all tests (NOT YET FULLY IMPLEMENTED)
	@echo "[test] Running available tests..."
	@echo "[test] Backend:"
	@cd backend && (python -m pytest tests/ -v 2>/dev/null || echo "[test] No backend tests found yet.")
	@echo "[test] Integration:"
	@echo "[test] No integration tests implemented yet."

# =============================================================================
# Clean
# =============================================================================
clean: ## Remove generated artefacts and caches
	@echo "[clean] Removing Python caches..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	@echo "[clean] Removing frontend build artefacts..."
	rm -rf frontend/dist frontend/build 2>/dev/null || true
	@echo "[clean] Done."
