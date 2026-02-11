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
