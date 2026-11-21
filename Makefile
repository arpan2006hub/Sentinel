# =============================================================================
# Sentinel — Makefile (developer convenience targets)
# Requires GNU make + a POSIX shell (Git Bash on Windows). Every target is a
# thin wrapper around a plain command, documented in README.md.
# =============================================================================

PYTHON ?= python
.DEFAULT_GOAL := help
.PHONY: help setup install demo pipeline backend-dev test openapi weights seed \
        docker-build docker-up docker-down frontend-install frontend-dev lint clean

CYAN  := \033[0;36m
RESET := \033[0m

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-18s$(RESET) %s\n", $$1, $$2}'

setup: ## Create .env from the template (if missing)
	@if [ ! -f .env ]; then cp .env.example .env && echo "[setup] Created .env"; else echo "[setup] .env exists"; fi

install: ## Install Python dependencies (run inside your virtualenv)
	$(PYTHON) -m pip install -r requirements.txt

pipeline: ## Generate the synthetic scenario, fit baselines, correlate (~15 s CPU)
	$(PYTHON) scripts/run_all.py --regenerate

demo: ## Build a fully analysed demo case in the local evidence store (~15 s CPU)
	$(PYTHON) scripts/demo.py

seed: ## Initialise the SQLite database
	$(PYTHON) scripts/seed_database.py

backend-dev: ## Run the API with auto-reload on http://localhost:8000
	$(PYTHON) -m uvicorn app.main:app --app-dir backend --reload --host 0.0.0.0 --port 8000

test: ## Run the test suite (never loads the TimeSformer weights)
	$(PYTHON) -m pytest tests -q

openapi: ## Export the OpenAPI schema for frontend type generation
	$(PYTHON) scripts/export_openapi.py

weights: ## Download the TimeSformer weights (~485 MB, network only)
	$(PYTHON) -c "import sys; sys.path.insert(0,'.'); from ai.video.timesformer_crime_detector import TimesformerCrimeDetector as T; d=T(auto_download=True); print('loaded:', d.is_loaded, d.model_path)"

docker-build: ## Build the backend image (CPU torch; large download)
	docker compose --profile app build backend

docker-up: ## Run the backend container
	docker compose --profile app up -d backend

docker-down: ## Stop containers
	docker compose --profile app down

frontend-install: ## Install frontend dependencies (frontend team)
	cd frontend && npm install

frontend-dev: ## Run the Vite dev server (frontend team)
	cd frontend && npm run dev

lint: ## Lint Python code with ruff
	$(PYTHON) -m ruff check ai backend scripts tests

clean: ## Remove caches (keeps artifacts/, data/generated/ and the evidence store)
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache .mypy_cache frontend/dist 2>/dev/null || true
