.PHONY: fetch-data backend-test backend-lint frontend-install frontend-test frontend-lint frontend-build docker-up

fetch-data:
	cd backend && python -m app.data.fetch_data

backend-test:
	cd backend && python -m pytest -q

backend-lint:
	cd backend && python -m ruff check app

frontend-install:
	cd frontend && npm ci

frontend-test:
	cd frontend && npm test

frontend-lint:
	cd frontend && npm run lint

frontend-build:
	cd frontend && npm run build

docker-up:
	docker compose up --build
