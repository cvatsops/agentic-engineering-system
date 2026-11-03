# Agentic Engineering System

A small FastAPI project with two independently runnable components:

- A URL-shortening service backed by SQLite, including click analytics.
- An agentic engineering workflow that converts a software requirement into architecture, API-contract, implementation-plan, test-plan, validation, and summary artifacts.

## Quick Start

Use Python 3.10 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run one service at a time.

```bash
# Engineering-workflow API
uvicorn app.main:app --reload

# URL-shortener API
uvicorn app.url_shortener:app --reload
```

Open Swagger UI at `http://127.0.0.1:8000/docs` to explore the API endpoints.

## URL Shortener

When running `app.url_shortener`, the API provides:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Check service and database health. |
| `POST` | `/urls` | Create a short URL. |
| `GET` | `/{short_code}` | Redirect to the original URL and record a click. |
| `GET` | `/urls/{short_code}/analytics` | Retrieve click analytics and the original URL. |

### Create a Short URL

```bash
curl -X POST http://127.0.0.1:8000/urls \
  -H 'Content-Type: application/json' \
  -d '{"original_url":"https://example.com"}'
```

The response contains the generated short code and URL details.

The local SQLite database defaults to `artifacts/url_shortener.db`.

## Engineering Workflow

When running `app.main`, submit a requirement to the engineering-workflow API.

```bash
curl -X POST http://127.0.0.1:8000/engineering/workflows \
  -H 'Content-Type: application/json' \
  -d '{
    "requirement": "Build a scalable URL shortener service with APIs, persistence, and analytics.",
    "scenario_type": "greenfield"
  }'
```

The response reports task states, validation results, and the generated artifact directory under:

```text
artifacts/runs/<workflow_id>/
```

The workflow decomposes a requirement into dependency-aware tasks and produces engineering artifacts, including:

- Architecture overview
- API contract
- Implementation plan
- Test plan
- Validation results
- Engineering summary

### Orchestration and Validation

The orchestrator executes tasks according to their dependencies, propagates upstream outputs to dependent tasks, and handles failures by preventing dependent tasks from executing when prerequisites fail.

A workflow is marked `completed` only when all tasks succeed and the required artifacts are present.

**Validation limitation:** Current validation checks workflow completion and artifact presence. It does not independently establish that the generated architecture, API contract, or implementation plan is correct or production-ready.

### Human Oversight

The workflow is deliberately review-only. It produces planning and validation artifacts but does not automatically apply code changes or deploy services.

The response includes `awaiting_human_approval` to indicate that human review is expected before follow-up engineering changes are accepted.

This flag communicates the review boundary; it should not be interpreted as proof of an implemented approval-enforcement mechanism.

## Assessment Scenarios

The system can be evaluated against the following requirement scenarios.

### 1. Greenfield

**Requirement:** Build a scalable URL shortener service with APIs, persistence, and analytics.

Evaluate whether the workflow:

- Decomposes the requirement into tasks with explicit dependencies.
- Generates the expected engineering artifacts.
- Reports task failures and validation outcomes accurately.
- Produces a final engineering summary with outstanding risks and limitations.

### 2. Brownfield

**Requirement example:** Add URL expiration support to an existing URL-shortener service.

A meaningful brownfield evaluation must establish that the system inspects the supplied repository, identifies relevant files and functions, and determines the impact on persistence, API behavior, and tests.

Generating a generic implementation plan alone does not demonstrate brownfield codebase reasoning. Repository inspection and impacted-code identification must be verified against the actual implementation.

### 3. Ambiguous Requirements

**Requirement example:** Make our URL service faster and more scalable.

Evaluate whether the workflow:

- Surfaces missing requirements and open questions.
- Labels assumptions explicitly.
- Distinguishes confirmed requirements from proposed design choices.
- Avoids inventing performance targets or capacity requirements.
- Identifies decisions that require clarification or human review.

## Tests

Run the test suite from the project root:

```bash
python -m pytest -v
```

The suite covers URL creation, redirects, analytics, persistence, task dependencies, failure propagation, dependency-cycle detection, and engineering-workflow generation.

A passing test suite verifies only the behaviors covered by the existing tests; the three assessment scenarios should also be evaluated end to end.

## Project Layout

```text
app/
  main.py                  # Engineering-workflow API
  engineering_workflow.py  # Artifact-producing workflow stages
  orchestrator.py          # Dependency-aware task executor
  url_shortener.py         # URL-shortener FastAPI application

tests/                     # Unit and integration tests
artifacts/                 # Local database and workflow artifacts
requirements.txt            # Python dependencies
README.md                   # Project documentation
```

## Scope and Limitations

- The engineering workflow generates reviewable planning artifacts rather than automatically implementing or deploying changes.
- Artifact-presence validation does not replace contract validation, code execution, integration testing, or production-readiness checks.
- Brownfield repository inspection must be implemented and verified before claiming that the system reasons about existing codebases.
- Human-review metadata does not by itself enforce an approval gate.

## Future Improvements

- Integrate an LLM or agent framework for richer requirement analysis and task planning.
- Add repository inspection and context-aware brownfield change analysis.
- Validate generated API contracts and implementation artifacts beyond checking file existence.
- Introduce explicit approval and rejection workflows before applying changes.
- Add execution traces, retry policies, and richer failure diagnostics.
- Expand integration and end-to-end tests for greenfield, brownfield, and ambiguous requirements.