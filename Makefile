# See planning/03-tech-stack.md section 10.3
.PHONY: setup sync deps-check verify hooks db migrate seed seed-base reset-books api web tunnel webhook lint format typecheck test e2e eval check prod-up

API := cd api &&
WEB := cd web &&

ifdef QUIET
PYTEST_FLAGS := -q --no-header --tb=short -rfE
JS_REPORTER := --reporter=dot
BUILD := out=$$(pnpm build 2>&1) || { echo "$$out" | tail -n 60; exit 1; }
else
PYTEST_FLAGS :=
JS_REPORTER :=
BUILD := pnpm build
endif

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
	$(WEB) $(BUILD)

hooks:
	git config core.hooksPath scripts/git-hooks

db:
	docker compose up -d --wait postgres

migrate:
	$(API) uv run alembic upgrade head

seed:
	$(API) uv run bk seed

seed-base:
	$(API) uv run bk seed --no-entries

reset-books:
	$(API) uv run bk reset-books --yes

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
	$(API) uv run pytest $(PYTEST_FLAGS)
	$(WEB) pnpm test $(JS_REPORTER)

e2e:
	$(WEB) pnpm e2e $(JS_REPORTER)

eval:
	$(API) uv run bk eval

check: lint typecheck test

prod-up:
	docker compose --profile prod up -d --build
