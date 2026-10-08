# Urban Platform

![Coverage](https://github.com/neikow/urban-platform/blob/python-coverage-comment-action-data/badge.svg)

## Getting started

Requirements: [uv](https://docs.astral.sh/uv/), Node.js 24 (see `.nvmrc`), Docker (for Redis) and
GNU gettext (`brew install gettext` / `apt install gettext`).

```bash
git clone git@github.com:neikow/urban-platform.git
cd urban-platform

make install   # Python + JS deps, git hooks, .env, migrations, translations, map tiles, CSS
make dev       # Redis, Django on :8000, Tailwind watcher and Celery, stopped with Ctrl+C
```

Run `make help` for every task. The ones you will use most:

| Command         | What it does                                                    |
|-----------------|-----------------------------------------------------------------|
| `make test`     | Unit tests, in parallel                                         |
| `make e2e`      | End-to-end suite, headless (see below for the interactive mode) |
| `make check`    | What CI runs before tests: ruff, mypy, bandit, missing migrations |
| `make format`   | Format Python code and templates                                |
| `make messages` | Update and compile the French translations                      |

### Front end

TypeScript and the Tailwind stylesheet live in `frontend/src/` and are built by Vite into
`urban_platform/static/dist/` (git-ignored), which templates load with `{% static 'dist/…' %}`.
`make dev` rebuilds on change; `make assets` type-checks and builds once.

- `main.ts` is loaded on every page; page-specific entries (`pages/vote.ts`, …) are listed in
  `vite.config.ts` and loaded with `<script type="module">` from the template that needs them.
- Templates contain no JavaScript. Use the data attributes handled by
  `frontend/src/lib/behaviors.ts` (`data-dialog-open`, `data-dialog-close`, `data-dismiss`,
  `data-autosubmit`, `data-password-toggle`) and pass data with `json_script`.
- Prefer theme tokens (`text-2xs`, `tracking-label`, `text-display-*`, defined in
  `frontend/src/styles/main.css`) over arbitrary values.

### Territory and maps

The area a website covers is the `Territory` setting: its outline, names, postal codes
and the city addresses are searched in. `manage.py configure_territory <INSEE code>`
sets it from geo.api.gouv.fr (a commune, or an arrondissement of Paris, Lyon or
Marseille); `make territory` sets the bundled 7th arrondissement of Marseille, which
`make install` does for development.

The basemap is self-hosted: a [PMTiles](https://docs.protomaps.com/pmtiles/) extract around
the territory, cut from the daily OpenStreetMap builds of [Protomaps](https://protomaps.com)
and drawn by `protomaps-leaflet`. No request leaves the site, and the maps cannot be panned
outside the extract (`tiles_bounds` in `publications/geo.py`).

The image ships no tiles: the `refresh_map_tiles` Celery task extracts them into
`MEDIA_ROOT/map-tiles/` (shared by the worker and nginx) when there are none, when the
territory changes, then once the interval set in the admin (Settings › Map, 30 days by
default) has passed. `manage.py build_map_tiles --refresh` runs it now. In development,
`make map-tiles` writes an extract into the static files instead, with the `pmtiles` CLI
(`brew install pmtiles`) or Docker. Tiles are read with HTTP range requests: nginx
supports them, and the project's `runserver` adds them for development.

### Translations

Code and templates use English strings; the French catalog lives in each app's
`locale/fr/`. After adding or changing a string, run `make messages` and fill in the
new `msgstr` entries. Prefer `{% blocktrans trimmed %}` for multi-line text so the
template formatter cannot change the msgid.

## Deploying a website

Every website (one per association) runs the same image with its own database, described
by environment variables. After `migrate`, `manage.py bootstrap_tenant` brings the database
in line with them (the `migrator` service of `docker-compose.yml` runs both). It is
idempotent and runs at every deployment; it only fills what is missing, so nothing the
association edited is overwritten (see `core/tenant.py`).

| Variable | Use |
|---|---|
| `BASE_URL` | Public URL, e.g. `https://aix.example.org`: the Wagtail site and the links in emails |
| `WEBSITE_NAME` | Default name, until the association sets one (Settings › Identité visuelle) |
| `TENANT_ADMIN_EMAIL` | First administrator, created without a password and invited by email to choose one |
| `TENANT_TERRITORY` | INSEE code of the area (e.g. `13001`); changing it moves the website to the new area |
| `TENANT_CONTACT_EMAIL` | Contact address, until the association sets one |
| `APP_VERSION` | Build argument: the release, reported by `/healthz/` |

On a new database, the bootstrap also publishes starter content in the home page and the
"À propos" pages.

## E2E Testing

E2E tests run against a real Django server with a persistent SQLite database. This simulates real user interactions and
persists data between test runs.

### Setup

First, set up the E2E environment (creates database, runs migrations, populates test data):

```bash
python scripts/e2e.py setup
```

### Running Tests

1. **Start the E2E server** in one terminal:
   ```bash
   python scripts/e2e.py serve
   ```

2. **Run the tests** in another terminal:
   ```bash
   python scripts/e2e.py test
   ```

   Or run tests with the browser visible:
   ```bash
   python scripts/e2e.py test --headed
   ```

   Run specific tests:
   ```bash
   python scripts/e2e.py test e2e/tests/test_auth_flows.py
   ```

### Other Commands

- **Reset database** (delete and recreate):
  ```bash
  python scripts/e2e.py reset
  ```

- **Populate database** (without resetting):
  ```bash
  python scripts/e2e.py populate
  ```

- **Run migrations only**:
  ```bash
  python scripts/e2e.py migrate
  ```

- **Run CI**:
  This prepares and runs the full E2E suite in headless mode, suitable for CI environments:
  ```bash
  python scripts/e2e.py ci
  ```

### Test Users

The following test users are created by the setup script:

| Email                      | Password      | Role                    | Note                   |
|----------------------------|---------------|-------------------------|------------------------|
| e2e.user@email.com         | password123   | Regular user            |                        |
| e2e.admin@email.com        | password123   | Admin (Moderator group) |                        |
| e2e.delete.test@email.com  | DeleteTest123 | Regular user            | Used for deletion test |
