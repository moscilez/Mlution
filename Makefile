.PHONY: dev test lint format migrate seed reset-db
dev:
	docker compose up --build
test:
	cd backend && python -m pytest -q
	cd frontend && npm test
lint:
	cd backend && python -m ruff check app tests migrations
	cd frontend && npm run lint && npm run typecheck
format:
	cd backend && python -m ruff format app tests migrations
	cd frontend && npm run format
migrate:
	docker compose exec backend python -m alembic upgrade head
seed:
	docker compose exec backend python -m app.seed
reset-db:
	@echo "Destructive reset is intentionally manual: docker compose down --volumes"
