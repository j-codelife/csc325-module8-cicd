# CSC 325 Module 8 CI/CD

A minimal Django REST Framework backend for the individual CSC 325 Module 8 assignment.

## Local setup

Use Python 3.11 or newer with the pinned dependencies. Local tests passed on Python 3.14.8. The pipeline Python version and dependency compatibility will be reviewed against the professor's tutorial.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py test
python manage.py runserver
```

No database migrations are needed for this endpoint.

## API

`GET http://127.0.0.1:8000/api/health/` returns HTTP 200 with:

```json
{"status": "ok"}
```

```sh
curl http://127.0.0.1:8000/api/health/
```

POST requests return HTTP 405. Automated tests verify the GET response status, JSON content type and payload, and POST rejection.

## Project structure

```text
api/                 Endpoint, URL routing, and tests
config/              Django settings, root routing, and WSGI entry point
manage.py            Django management commands
requirements.txt     Pinned Python dependencies
```

The settings are for local development, with a development-only secret key and debug mode enabled. Deployment configuration and the GitHub Actions workflow are deferred until the professor's tutorial is available.
