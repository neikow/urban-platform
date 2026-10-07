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

### Maps

The basemap is self-hosted: a [PMTiles](https://docs.protomaps.com/pmtiles/) extract of
Marseille, cut from the daily OpenStreetMap builds of [Protomaps](https://protomaps.com) and
drawn by `protomaps-leaflet`. No request leaves the site, and the maps cannot be panned
outside the extract (`LOCAL_AREA_TILES_BOUNDS` in `publications/geo.py`).

The archive (~35 MB) is not committed. `make map-tiles` downloads the latest one into
`publications/static/publications/geo/`, with the `pmtiles` CLI (`brew install pmtiles`) or
Docker. The Docker image fetches it at build time. It is read with HTTP range requests:
nginx supports them, and the project's `runserver` adds them for development.

### Translations

Code and templates use English strings; the French catalog lives in each app's
`locale/fr/`. After adding or changing a string, run `make messages` and fill in the
new `msgstr` entries. Prefer `{% blocktrans trimmed %}` for multi-line text so the
template formatter cannot change the msgid.

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
