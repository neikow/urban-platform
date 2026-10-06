# Common development tasks. Run `make help` for the list.

.DEFAULT_GOAL := help
MANAGE := uv run python manage.py

.PHONY: help
help: ## Show this help
	@grep -hE '^[a-zA-Z0-9_-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "} {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

.PHONY: install
install: ## Install dependencies, the e2e browser, git hooks and a local .env
	uv sync
	npm ci
	uv run playwright install chromium
	uv run pre-commit install
	@test -f .env || (cp .env.example .env && echo "Created .env from .env.example")
	$(MANAGE) migrate
	$(MANAGE) compilemessages --ignore=.venv --ignore=node_modules
	npm run styles:build

.PHONY: dev
dev: ## Run Redis (Docker), Django, Tailwind watcher and Celery together
	uv run python scripts/dev.py

.PHONY: dev-no-docker
dev-no-docker: ## Same as dev, with Redis already running
	uv run python scripts/dev.py --no-docker

.PHONY: migrate
migrate: ## Apply database migrations
	$(MANAGE) migrate

.PHONY: migrations
migrations: ## Create migrations for model changes
	$(MANAGE) makemigrations

.PHONY: messages
messages: ## Update the French catalogs, then compile them
	$(MANAGE) makemessages -l fr --ignore=node_modules --ignore=.venv --ignore=docs
	$(MANAGE) compilemessages --ignore=.venv --ignore=node_modules

.PHONY: css
css: ## Build the Tailwind stylesheet once
	npm run styles:build

.PHONY: test
test: ## Run unit tests in parallel
	uv run pytest -n auto

.PHONY: e2e
e2e: ## Run the end-to-end suite headless (sets up its own database and server)
	uv run python scripts/e2e.py ci

.PHONY: lint
lint: ## Lint Python code
	uv run ruff check .

.PHONY: format
format: ## Format Python code and Django templates
	uv run ruff format .
	uv run ruff check --fix .
	uv run pre-commit run djangofmt --all-files

.PHONY: types
types: ## Type-check with mypy
	uv run mypy .

.PHONY: check
check: ## Everything CI runs before tests: lint, format check, types, security, migrations
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy .
	uv run bandit -q -c pyproject.toml -r core home about legal pedagogy publications urban_platform scripts
	$(MANAGE) makemigrations --check --dry-run

.PHONY: docs
docs: ## Serve the admin documentation locally
	cd docs && uv run mkdocs serve
