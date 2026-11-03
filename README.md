# Agentic Engineering System

A small FastAPI project with two independently runnable components:

- A URL-shortening service backed by SQLite, including click analytics.
- An engineering workflow that converts a requirement into architecture,
  API-contract, implementation-plan, test-plan, validation, and summary
  artifacts.

## Quick start

Use Python 3.10 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run one service at a time:

```bash
# Engineering-workflow API
uvicorn app.main:app --reload

# URL-shortener API
uvicorn app.url_shortener:app --reload
```

## URL shortener

When running `app.url_shortener`, the API provides:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Check database connectivity. |
| `POST` | `/urls` | Create a short URL. |
| `GET` | `/{short_code}` | Redirect and record a click. |
| `GET` | `/urls/{short_code}/analytics` | Retrieve click count and the original URL. |

Create a URL:

```bash
curl -X POST http://127.0.0.1:8000/urls \
  -H 'Content-Type: application/json' \
  -d '{"original_url":"https://example.com"}'
```

The local SQLite database defaults to `artifacts/url_shortener.db`.

## Engineering workflow

When running `app.main`, submit a requirement with:

```bash
curl -X POST http://127.0.0.1:8000/engineering/workflows \
  -H 'Content-Type: application/json' \
  -d '{
    "requirement": "Create a URL shortener with click analytics.",
    "scenario_type": "greenfield"
  }'
```

The response reports every task state, validation outcome, and the generated
artifact directory under `artifacts/runs/<workflow_id>/`. A successful workflow
returns `"status": "completed"` only after all tasks have succeeded and the
required artifacts are present.

The workflow is deliberately review-only: it creates planning and validation
artifacts, but does not deploy services or automatically apply code changes.
The response keeps `awaiting_human_approval` set to `true` so a person remains
responsible for accepting follow-up changes.

## Tests

```bash
python -m pytest -q
```

The suite covers URL creation, redirects, analytics, persistence, task
dependencies, failure propagation, cycle detection, and end-to-end workflow
generation.

## Project layout

```text
app/
  main.py                  # Engineering-workflow API
  engineering_workflow.py  # Artifact-producing workflow stages
  orchestrator.py          # Dependency-aware task executor
  url_shortener.py         # URL-shortener FastAPI application
tests/                     # Unit and integration tests
```
