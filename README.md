# Urban Platform

## Installation
### Development Environment Setup
We use [uv](https://docs.astral.sh/uv/) to manage our development
$environment. To set up the project, follow these steps:
```bash
git clone git@github.com:neikow/urban-platform.git
cd urban-platform

uv sync
pre-commit install

cp .env.example .env
```

This will install all necessary dependencies and set up the development
environment.

### Running the Application
To run the application in development mode, use the following command:
```bash
python manage.py migrate
python manage.py runserver
```

### Internationalization
To collect translation messages, run:
```bash
python manage.py makemessages -a
```
To compile translation messages, run:
```bash
python manage.py compilemessages
```

## E2E Testing

E2E tests run against a real Django server with a persistent SQLite database. This simulates real user interactions and persists data between test runs.

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

| Email               | Password    | Role                    |
|---------------------|-------------|-------------------------|
| e2e.user@email.com  | password123 | Regular user            |
| e2e.admin@email.com | password123 | Admin (Moderator group) |
