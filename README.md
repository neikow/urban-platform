# Urban Platform

![Coverage](https://github.com/neikow/urban-platform/blob/python-coverage-comment-action-data/badge.svg)

## Getting started

Requirements: [uv](https://docs.astral.sh/uv/), Node.js 20+, Docker (for Redis) and
GNU gettext (`brew install gettext` / `apt install gettext`).

```bash
git clone git@github.com:neikow/urban-platform.git
cd urban-platform

make install   # Python + JS deps, git hooks, .env, migrations, translations, CSS
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
