.PHONY: db-up db-down install migrate test test-v test-e2e run logs clean

# ──────────────────────────────────────────────
# Database
# ──────────────────────────────────────────────
db-up:
	docker-compose up -d

db-down:
	docker-compose down

# ──────────────────────────────────────────────
# Dependencies
# ──────────────────────────────────────────────
install:
	pip install -r requirements.txt

# ──────────────────────────────────────────────
# Database Migrations
# ──────────────────────────────────────────────
migrate:
	alembic upgrade head

# ──────────────────────────────────────────────
# Testing
# ──────────────────────────────────────────────
test:
	python -m pytest

test-v:
	python -m pytest -v

test-e2e:
	python -m pytest tests/e2e/ -v

# ──────────────────────────────────────────────
# Development
# ──────────────────────────────────────────────
run:
	uvicorn services.api.app.main:app --reload --host 0.0.0.0 --port 8000

# ──────────────────────────────────────────────
# Cleanup
# ──────────────────────────────────────────────
clean:
	@echo "Cleaning __pycache__, .pyc, and test databases..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "test_*.db" -delete 2>/dev/null || true
	@echo "Done."
