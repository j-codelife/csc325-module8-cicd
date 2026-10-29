# CSC 325 Module 8 CI/CD

A minimal Django REST Framework backend for the individual CSC 325 Module 8 assignment.

## Local setup

Use Python 3.13. The `.python-version` file selects the same Python minor version for GitHub Actions and Render.

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

POST requests return HTTP 405. The existing API tests verify the GET response status, JSON content type and payload, and POST rejection. Additional tests cover production configuration and deployment verification without contacting Render.

## Project structure

```text
api/                 Endpoint, URL routing, and tests
config/              Django settings, root routing, and WSGI entry point
scripts/             Render deployment verification and its tests
.github/workflows/   Four-job GitHub Actions workflow
.python-version      Shared Python 3.13 selection
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
| Deploy | Test | Deploy the tested commit to Render and verify it is live and healthy |

Each job uses a fresh runner. Jobs that need installed packages install them independently, using pip's download cache. A virtual environment is not transferred between jobs.

Deploy runs only for a push to `main` after Test succeeds. Pull requests never deploy. The deployment script submits the workflow's commit SHA, polls that deployment for up to 15 minutes, verifies Render reports the same commit as live, then checks the public health endpoint for up to two minutes. A failed, canceled, mismatched, timed-out, or unhealthy deployment fails the job. Missing configuration also fails explicitly.

Deploy jobs do not run concurrently. Avoid additional manual deploys while a workflow deploy is in progress. A successful request to start deployment alone does not make the job pass.

## Production settings

Debug mode is off by default. Set these environment variables in Render:

| Variable | Value |
| --- | --- |
| `DJANGO_DEBUG` | `false` |
| `DJANGO_SECRET_KEY` | A generated private random value, at least 50 characters |
| `DJANGO_ALLOWED_HOSTS` | The exact assigned hostname, such as `your-service.onrender.com`, without a scheme or path |

Production refuses to start without `DJANGO_SECRET_KEY`. Local development uses a development-only fallback only when `DJANGO_DEBUG=true`. Environment files are not loaded automatically; use shell environment variables locally and Render's environment settings on the host.

Production redirects HTTP to HTTPS and trusts Render's `X-Forwarded-Proto` header. It also enables secure cookies, HSTS, and Django's security, CSRF, and clickjacking middleware. Run this configuration behind Render's HTTPS proxy.

The application has no database-backed features or static assets. No database service, migrations, persistent disk, or static-file build is needed.

## Render setup after approval

The following steps create or change external resources. Local preparation does not perform them.

1. After approving the commit and push, open a pull request from `feature/django-backend` to `main` and verify Setup, Dependencies, and Test pass; Deploy should be skipped.
2. After approving the merge, sign in to Render and create a **Web Service** connected to `j-codelife/csc325-module8-cicd`.
3. Select branch `main`, language **Python 3**, and leave Root Directory blank. Choose the desired region and instance plan.
4. Set Build Command to `python -m pip install -r requirements.txt`.
5. Set Start Command to `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --access-logfile - --error-logfile -`.
6. Set Health Check Path to `/api/health/` and Auto-Deploy to **Off**. GitHub Actions must control subsequent deployments so failed tests cannot be bypassed by Render deploying each push independently.
7. Add the three production environment variables listed above before deployment. Generate the secret privately in Render. Use the hostname assigned to the service for `DJANGO_ALLOWED_HOSTS`.
8. Leave `PYTHON_VERSION` unset so Render reads `3.13` from `.python-version`. An existing `PYTHON_VERSION` variable overrides this file; remove it or set it to a fully qualified Python 3.13 patch version.
9. Create the service. Render starts an initial build as part of service creation; this is a one-time setup deployment. Subsequent assignment demonstrations must show a GitHub Actions deployment after passing tests.
10. In Render **Account Settings → API Keys**, create a private API key authorized to trigger and read deployments for this service. Record the service ID beginning with `srv-` from its dashboard URL and the public HTTPS URL.
11. In GitHub **Settings → Secrets and variables → Actions**, add the following repository configuration:

| Type | Name | Value |
| --- | --- | --- |
| Secret | `RENDER_API_KEY` | The private Render API key |
| Variable | `RENDER_SERVICE_ID` | The Render service ID beginning with `srv-` |
| Variable | `RENDER_SERVICE_URL` | The public HTTPS origin, such as `https://your-service.onrender.com`, without an endpoint path |

Keep the Django production secret in Render and the API key in GitHub Actions secrets. Do not paste secret values into chat, commit them, or put them in repository variables. The deployment helper sends the API key only to the Render API, not to the public health endpoint.

The first merged workflow can fail Deploy until Render and these GitHub values exist. Once configured, re-run all jobs for the latest `main` workflow run to test the complete pipeline. Do not re-run an older commit after newer changes have been deployed, because the helper deliberately deploys that run's exact commit.

The public assignment endpoint is `https://your-service.onrender.com/api/health/`. A root-path 404 is expected because the backend exposes only the API endpoint. Free Render services can sleep while idle and take time to restart.

Branch protection is a separate GitHub setting to configure only after approval. Require passing Setup, Dependencies, and Test checks for pull requests targeting `main`; do not require Deploy because pull requests skip it. Block force pushes and branch deletion. Keep the final demonstration endpoint change for a separate recorded commit.

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

Reference documentation: [Render web services](https://render.com/docs/web-services), [Python versions](https://render.com/docs/python-version), [deployment API](https://api-docs.render.com/reference/create-deploy), [deployment status API](https://api-docs.render.com/reference/retrieve-deploy), and [Django deployment settings](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/).
