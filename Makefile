.PHONY: backend-start backend-test backend-lint backend-typecheck evaluation-test evaluation-lint evaluation-typecheck frontend-install frontend-start frontend-test frontend-lint frontend-typecheck frontend-build check

backend-start:
	uv run --all-packages --directory backend uvicorn e3sm_assist.app:app --reload

backend-test:
	uv run --all-packages pytest backend/tests

backend-lint:
	uv run --all-packages ruff check backend

backend-typecheck:
	uv run --all-packages mypy backend

evaluation-test:
	E3SM_ASSIST_EVALUATOR=e3sm_assist.evaluation_adapter:evaluate uv run --all-packages pytest evaluation

evaluation-lint:
	uv run --all-packages ruff check evaluation

evaluation-typecheck:
	uv run --all-packages mypy evaluation

frontend-install:
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

check: backend-test backend-lint backend-typecheck evaluation-test evaluation-lint evaluation-typecheck
