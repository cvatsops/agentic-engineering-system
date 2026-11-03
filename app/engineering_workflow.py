
import json
from pathlib import Path

from app.models import (
    EngineeringTask,
    NormalizedRequirement,
    RequirementRequest,
    TaskStatus,
)
from app.orchestrator import Orchestrator


def normalize_requirement(
    request: RequirementRequest,
) -> NormalizedRequirement:
    text = request.requirement.strip()
    lower = text.lower()

    questions = []
    assumptions = []

    if request.scenario_type.value == "ambiguous":
        questions = [
            "What are the expected peak requests per second?",
            "What are the target availability and latency SLOs?",
            "Are there constraints on budget, database, or deployment region?",
        ]
        assumptions = [
            "Use a documented baseline for the initial design.",
            "Treat availability and latency targets as unconfirmed.",
            "Do not deploy or modify production resources.",
        ]
    else:
        assumptions = [
            "The output is a reviewable prototype, not a production deployment.",
            "Generated changes require automated validation and human approval.",
        ]

    functional = [
        "Expose well-defined APIs for the requested functionality.",
        "Provide automated tests for expected and failure scenarios.",
    ]

    if "url shortener" in lower or "short url" in lower:
        functional.extend([
            "Create a short code for an original URL.",
            "Redirect requests to the original URL.",
            "Persist URL mappings.",
            "Record and retrieve click analytics.",
        ])

    non_functional = [
        "Keep components modular and maintainable.",
        "Validate inputs and handle failures explicitly.",
        "Document security risks and scalability trade-offs.",
    ]

    if any(word in lower for word in ["scalable", "availability", "reliable"]):
        non_functional.extend([
            "Define measurable performance and availability targets.",
            "Document redundancy, capacity, and failure-recovery needs.",
        ])

    acceptance = [
        "The implementation plan and dependencies are explicit.",
        "Engineering artifacts are generated in a run-specific directory.",
        "Validation results and limitations are reported.",
        "Production-impacting actions require human approval.",
    ]

    return NormalizedRequirement(
        problem_statement=text,
        functional_requirements=functional,
        non_functional_requirements=non_functional,
        assumptions=assumptions,
        open_questions=questions,
        acceptance_criteria=acceptance,
    )


def build_tasks() -> list[EngineeringTask]:
    return [
        EngineeringTask(
            task_id="architecture",
            title="Design system architecture",
            description="Define components, data flow, and trade-offs.",
        ),
        EngineeringTask(
            task_id="api_contract",
            title="Define API contract",
            description="Specify endpoints, schemas, and errors.",
        ),
        EngineeringTask(
            task_id="implementation_plan",
            title="Create implementation plan",
            description="Sequence implementation work.",
            dependencies=["architecture", "api_contract"],
        ),
        EngineeringTask(
            task_id="test_plan",
            title="Create test strategy",
            description="Define functional, integration, and failure tests.",
            dependencies=["architecture", "api_contract"],
        ),
        EngineeringTask(
            task_id="validation",
            title="Validate engineering artifacts",
            description="Check required artifacts and consistency.",
            dependencies=[
                "architecture",
                "api_contract",
                "implementation_plan",
                "test_plan",
            ],
        ),
        EngineeringTask(
            task_id="summary",
            title="Prepare engineering summary",
            description="Summarize results, risks, and limitations.",
            dependencies=["validation"],
        ),
    ]


def create_handlers(
    output_dir: Path,
    requirement: NormalizedRequirement,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)

    def write_text(name: str, content: str) -> dict:
        path = output_dir / name
        path.write_text(content, encoding="utf-8")
        return {"artifact": name}

    def write_json(name: str, data: dict) -> dict:
        path = output_dir / name
        path.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8",
        )
        return {"artifact": name}

    async def architecture(task, dependencies):
        content = f"""# Architecture Overview

## Requirement
{requirement.problem_statement}

## Proposed components
- API layer: validates requests and exposes application endpoints.
- Business logic: implements the requested behavior.
- Persistence: stores durable application data.
- Analytics and observability: records relevant operational events.
- Validation: checks generated artifacts and test results.

## Design approach
Keep API, business logic, persistence, and validation separate.
Use stateless API instances where practical. Select the database,
caching strategy, and deployment topology based on measured load
and availability requirements.

## Trade-offs
A local SQLite prototype is simple to run but is not a
multi-region, horizontally scalable production database.

## Availability
No availability target is claimed for this prototype.
Production targets require explicit SLOs, redundancy,
load testing, monitoring, and recovery validation.
"""
        return write_text("architecture.md", content)

    async def api_contract(task, dependencies):
        contract = {
            "openapi": "3.1.0",
            "info": {
                "title": "Generated Engineering API",
                "version": "0.1.0",
            },
            "paths": {
                "/health": {
                    "get": {
                        "summary": "Check service health",
                        "responses": {
                            "200": {"description": "Service is healthy"},
                            "503": {"description": "Dependency unavailable"},
                        },
                    }
                },
                "/urls": {
                    "post": {
                        "summary": "Create a short URL",
                        "responses": {
                            "201": {"description": "URL created"},
                            "422": {"description": "Invalid input"},
                        },
                    }
                },
                "/{short_code}": {
                    "get": {
                        "summary": "Redirect to original URL",
                        "responses": {
                            "307": {"description": "Redirect"},
                            "404": {"description": "Unknown short code"},
                        },
                    }
                },
                "/urls/{short_code}/analytics": {
                    "get": {
                        "summary": "Retrieve click analytics",
                        "responses": {
                            "200": {"description": "Analytics returned"},
                            "404": {"description": "Unknown short code"},
                        },
                    }
                },
            },
        }
        return write_text(
            "api-contract.yaml",
            json.dumps(contract, indent=2),
        )

    async def implementation_plan(task, dependencies):
        plan = {
            "tasks": [
                {
                    "id": "implement_api",
                    "description": "Implement API and business logic",
                    "depends_on": ["architecture", "api_contract"],
                },
                {
                    "id": "implement_persistence",
                    "description": "Implement durable storage",
                    "depends_on": ["architecture"],
                },
                {
                    "id": "write_tests",
                    "description": "Write unit and integration tests",
                    "depends_on": ["implement_api", "implement_persistence"],
                },
                {
                    "id": "run_quality_gates",
                    "description": "Run tests and static checks",
                    "depends_on": ["write_tests"],
                },
            ]
        }
        return write_json("implementation-plan.json", plan)

    async def test_plan(task, dependencies):
        content = """# Test and Validation Strategy

## Functional tests
- Valid request creates the expected resource.
- Successful requests return the documented response.
- Invalid input is rejected.
- Unknown resources return the documented error.

## Integration tests
- Verify API behavior against a temporary test database.
- Verify persisted data is available across application instances.
- Verify analytics are updated after relevant operations.

## Failure tests
- Unknown identifiers.
- Invalid request bodies.
- Database unavailable.
- Duplicate identifier or collision handling.

## Quality gates
- Unit and integration tests pass.
- API responses match the contract.
- Required artifacts exist and are readable.
- Human review is required before accepting changes.
"""
        return write_text("test-plan.md", content)

    async def validation(task, dependencies):
        required = [
            "architecture.md",
            "api-contract.yaml",
            "implementation-plan.json",
            "test-plan.md",
        ]

        missing = [
            name for name in required
            if not (output_dir / name).is_file()
        ]

        result = {
            "passed": not missing,
            "checks": {
                "required_artifacts_exist": not missing,
            },
            "missing_artifacts": missing,
            "note": (
                "This stage validates artifact presence only. "
                "It does not claim generated code or runtime tests passed."
            ),
        }

        return write_json("validation-results.json", result)

    async def summary(task, dependencies):
        validation_data = json.loads(
            (output_dir / "validation-results.json").read_text(
                encoding="utf-8"
            )
        )

        content = f"""# Engineering Summary

## Requirement
{requirement.problem_statement}

## Deliverables
- Architecture overview
- API contract
- Implementation plan
- Test and validation strategy
- Validation results

## Validation outcome
Artifact completeness: {
    "PASS" if validation_data["passed"] else "FAIL"
}

## Assumptions
{chr(10).join("- " + item for item in requirement.assumptions)}

## Open questions
{chr(10).join("- " + item for item in requirement.open_questions)
 or "- None identified by the initial analyzer."}

## Risks and limitations
- The architecture is a proposal, not a production deployment.
- Artifact presence does not establish code correctness.
- Scalability and availability require load and failure testing.
- Generated changes require human review before acceptance.
"""
        return write_text("engineering-summary.md", content)

    return {
        "architecture": architecture,
        "api_contract": api_contract,
        "implementation_plan": implementation_plan,
        "test_plan": test_plan,
        "validation": validation,
        "summary": summary,
    }


async def run_workflow(
    workflow_id: str,
    request: RequirementRequest,
    artifacts_root: Path = Path("artifacts/runs"),
) -> dict:
    requirement = normalize_requirement(request)
    output_dir = artifacts_root / workflow_id
    tasks = build_tasks()

    handlers = create_handlers(output_dir, requirement)
    orchestrator = Orchestrator(handlers)
    completed_tasks = await orchestrator.execute(tasks)

    validation_path = output_dir / "validation-results.json"
    validation = json.loads(
        validation_path.read_text(encoding="utf-8")
    )

    return {
        "workflow_id": workflow_id,
        "status": (
            "completed"
            if validation["passed"]
            else "validation_failed"
        ),
        "normalized_requirement": requirement.model_dump(mode="json"),
        "tasks": [
            task.model_dump(mode="json")
            for task in completed_tasks
        ],
        "validation_results": validation,
        "artifact_directory": str(output_dir),
        "awaiting_human_approval": True,
    }
