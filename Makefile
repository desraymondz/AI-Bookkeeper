# See planning/03-tech-stack.md section 10.3
.PHONY: setup sync deps-check verify hooks db migrate seed api web tunnel webhook lint format typecheck test e2e eval check prod-up

API := cd api &&
WEB := cd web &&

setup:
	cp -n .env.example .env || true
	$(API) uv sync
	$(WEB) pnpm install

sync:
	$(API) uv sync --locked
	$(WEB) pnpm install --frozen-lockfile

deps-check:
	$(API) uv lock --check
	$(WEB) pnpm install --frozen-lockfile --lockfile-only

verify: deps-check lint typecheck test
	$(WEB) pnpm build

hooks:
	git config core.hooksPath scripts/git-hooks

db:
	docker compose up -d --wait postgres

migrate:
	$(API) uv run alembic upgrade head

seed:
	$(API) uv run bk seed

api:
	$(API) uv run uvicorn bookkeeper.main:app --reload --port 8000

web:
	$(WEB) pnpm dev

tunnel:
	scripts/dev-tunnel.sh

webhook:
	$(API) uv run bk set-webhook

lint:
	$(API) uv run ruff check . && uv run ruff format --check .
	$(WEB) pnpm check

format:
	$(API) uv run ruff format . && uv run ruff check --fix .
	$(WEB) pnpm format

typecheck:
	$(API) uv run mypy src tests
	$(WEB) pnpm typecheck

test:
	$(API) uv run pytest
	$(WEB) pnpm test

e2e:
	$(WEB) pnpm e2e

eval:
	$(API) uv run bk eval

check: lint typecheck test

prod-up:
	docker compose --profile prod up -d --build
