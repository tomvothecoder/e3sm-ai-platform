.DEFAULT_GOAL := help

.PHONY: help sync check clean backend-env backend-sync backend-start backend-test backend-lint backend-typecheck evaluation-test evaluation-lint evaluation-typecheck frontend-sync frontend-start frontend-test frontend-lint frontend-typecheck frontend-build observability-up observability-down observability-status observability-logs

# =============================================================================
# Help
# =============================================================================

help:
	@printf '%s\n' 'E3SM AI Platform commands:' '' \
	  '  sync                          Synchronize all Python and frontend dependencies' \
	  '  check                         Run backend and evaluation checks' \
	  '  clean                         Remove generated files and local caches' '' \
	  'Backend:' \
	  '  backend-env                   Create backend/.env from the example when absent' \
	  '  backend-sync                  Synchronize backend Python dependencies only' \
	  '  backend-start                 Run the FastAPI service with reload' \
	  '  backend-test                  Run backend tests' \
	  '  backend-lint                  Run Ruff on the backend' \
	  '  backend-typecheck             Run ty on the backend' '' \
	  'Frontend:' \
	  '  frontend-sync                 Synchronize frontend dependencies only' \
	  '  frontend-start                Run the Vite development server' \
	  '  frontend-test                 Run frontend tests' \
	  '  frontend-lint                 Run ESLint' \
	  '  frontend-typecheck            Run TypeScript type checks' \
	  '  frontend-build                Build the frontend for production' '' \
	  'Evaluation:' \
	  '  evaluation-test               Run E3SM Compass contract evaluation' \
	  '  evaluation-lint               Run Ruff on evaluation code' \
	  '  evaluation-typecheck          Run ty on evaluation code' '' \
	  'Observability:' \
	  '  observability-up              Start the local Collector and Jaeger stack' \
	  '  observability-down            Stop the local observability stack' \
	  '  observability-status          Show local observability stack status' \
	  '  observability-logs            Follow local observability stack logs'

# =============================================================================
# Quality checks
# =============================================================================

sync:
	uv sync --all-packages --all-groups
	$(MAKE) frontend-sync

check: backend-test backend-lint backend-typecheck evaluation-test evaluation-lint evaluation-typecheck

# =============================================================================
# Backend
# =============================================================================

backend-env:
	@if [ -e backend/.env ]; then \
	  printf '%s\n' 'backend/.env already exists; leaving it unchanged.'; \
	else \
	  cp backend/.env.example backend/.env; \
	  printf '%s\n' 'Created backend/.env from backend/.env.example.'; \
	fi

backend-sync:
	uv sync --package e3sm-ai-platform-backend --all-groups

backend-start:
	uv run --all-packages --directory backend uvicorn e3sm_ai_platform.api.app:app --reload

backend-test:
	uv run --all-packages pytest backend/tests

backend-lint:
	uv run --all-packages ruff check backend

backend-typecheck:
	uv run --all-packages ty check backend

# =============================================================================
# Frontend
# =============================================================================

frontend-sync:
	npm --prefix frontend ci

frontend-start:
	npm --prefix frontend run dev

frontend-test:
	npm --prefix frontend test -- --run

frontend-lint:
	npm --prefix frontend run lint

frontend-typecheck:
	npm --prefix frontend run typecheck

frontend-build:
	npm --prefix frontend run build

# =============================================================================
# Evaluation
# =============================================================================

evaluation-test:
	E3SM_COMPASS_EVALUATOR=e3sm_ai_platform.evaluation:evaluate uv run --all-packages pytest evaluation

evaluation-lint:
	uv run --all-packages ruff check evaluation

evaluation-typecheck:
	uv run --all-packages ty check evaluation

# =============================================================================
# Maintenance
# =============================================================================

clean:
	rm -rf .pytest_cache .ruff_cache .coverage coverage dist
	rm -rf backend/.data backend/.pytest_cache backend/.ruff_cache backend/dist
	rm -rf evaluation/.pytest_cache evaluation/.ruff_cache evaluation/dist
	rm -rf frontend/dist frontend/coverage
	python3 -c "from pathlib import Path; import shutil; [shutil.rmtree(path) for path in Path('.').rglob('__pycache__')]; [path.unlink() for path in Path('.').rglob('*.py[cod]')]"

# =============================================================================
# Observability
# =============================================================================

observability-up:
	docker compose -f deploy/observability/docker-compose.yml up -d --wait

observability-down:
	docker compose -f deploy/observability/docker-compose.yml down

observability-status:
	docker compose -f deploy/observability/docker-compose.yml ps

observability-logs:
	docker compose -f deploy/observability/docker-compose.yml logs -f
