.PHONY: setup dev backend frontend test seed

## First-time install (Python + Node dependencies)
setup:
	uv sync
	cd frontend && npm install

## Start backend and frontend together
dev:
	@echo "Starting backend on :8000 and frontend on :5173..."
	@echo "Press Ctrl+C to stop both."
	DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run uvicorn backend.main:app --reload --port 8000 & \
	cd frontend && npm run dev

## Start backend only
backend:
	DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run uvicorn backend.main:app --reload --port 8000

## Start frontend only
frontend:
	cd frontend && npm run dev

## Run all tests
test:
	uv run pytest
	cd frontend && npm test

## Manually re-seed database (usually not needed — auto-seeds on first startup)
seed:
	uv run python -m backend.seed.loader
