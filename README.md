# CSC 325 Module 8 CI/CD

A minimal Django REST Framework backend for the individual CSC 325 Module 8 assignment, with a simulated deployment stage. Actual public deployment is deferred; the original publicly accessible application requirement remains outstanding.

## Local setup

Use Python 3.13. The `.python-version` file selects this version for GitHub Actions.

```sh
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export DJANGO_DEBUG=true
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

POST requests return HTTP 405. The two API tests verify the GET response status, JSON content type and payload, and POST rejection. Four additional tests cover general Django configuration.

## Project structure

```text
api/                 Endpoint, URL routing, and tests
config/              Django settings, root routing, WSGI entry point, and configuration tests
.github/workflows/   Four-job GitHub Actions workflow
.python-version      Python 3.13 selection
manage.py            Django management commands
requirements.txt     Pinned Python dependencies
```

## GitHub Actions

The workflow is `.github/workflows/csc325_ci_cd.yml`. Every push to `main` and pull request targeting `main` triggers it.

| Job | Prerequisite | Purpose |
| --- | --- | --- |
| Setup | None | Configure and verify Python 3.13 |
| Dependencies | Setup | Install pinned dependencies and check compatibility |
| Test | Dependencies | Run Django checks, the complete test suite, and production configuration checks |
| Deploy | Test | Print `Deploying application (simulation)` |

Each job uses a fresh runner. Jobs that need installed packages install them independently, using pip's download cache. A virtual environment is not transferred between jobs.

Deploy runs only for a push to `main` after Test succeeds. Failed tests block Deploy, and pull requests skip Deploy. The simulation prints its confirmation and exits successfully. It does not contact a hosting provider or require GitHub secrets or repository variables.

## Django configuration

General environment-based settings and security middleware are retained. Debug mode is off by default, and starting with debug disabled requires `DJANGO_SECRET_KEY`. Set `DJANGO_DEBUG=true` for local development to use the development-only fallback key.

`DJANGO_ALLOWED_HOSTS` accepts comma-separated hostnames and defaults to `localhost,127.0.0.1,[::1]`. Environment files are not loaded automatically. HTTPS redirects, secure cookies, and HSTS remain enabled when debug is disabled. No hosting provider's proxy headers are trusted.

The Test job checks production configuration using a temporary generated key that is not stored. These checks validate settings; they do not deploy the application.

## Feature branch and branch protection

Continue work on `feature/django-backend`. After approval to commit and push, open a pull request targeting `main` and verify Setup, Dependencies, and Test pass. Deploy should be skipped for the pull request and run after an approved merge to `main`.

Branch protection is a separate GitHub setting to configure only after approval. Require passing Setup, Dependencies, and Test checks for pull requests targeting `main`; do not require Deploy because pull requests skip it. Block force pushes and branch deletion.

Keep the small endpoint change for a separate recorded commit during the final video demonstration. The existing endpoint response is unchanged.

## Local validation

With the virtual environment active and `DJANGO_DEBUG=true`:

```sh
python manage.py check
python manage.py test --verbosity 2
python -m pip check
git diff --check
```

To check production settings locally without storing a key, use a temporary generated value:

```sh
DJANGO_DEBUG=false DJANGO_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(64))')" python manage.py check --deploy --fail-level WARNING
```
