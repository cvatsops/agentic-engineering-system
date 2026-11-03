
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RequirementType(str, Enum):
    GREENFIELD = "greenfield"
    BROWNFIELD = "brownfield"
    AMBIGUOUS = "ambiguous"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"


class RequirementRequest(BaseModel):
    requirement: str = Field(min_length=10)
    scenario_type: RequirementType
    repository_path: str | None = None


class NormalizedRequirement(BaseModel):
    problem_statement: str
    functional_requirements: list[str]
    non_functional_requirements: list[str]
    assumptions: list[str] = []
    open_questions: list[str] = []
    acceptance_criteria: list[str]


class EngineeringTask(BaseModel):
    task_id: str
    title: str
    description: str
    dependencies: list[str] = []
    status: TaskStatus = TaskStatus.PENDING
    output: dict[str, Any] = {}
    error: str | None = None


class TaskExecutionResult(BaseModel):
    task_id: str
    status: TaskStatus
    output: dict[str, Any] = {}
    error: str | None = None


class WorkflowResponse(BaseModel):
    workflow_id: str
    status: str
    normalized_requirement: NormalizedRequirement | None = None
    tasks: list[EngineeringTask]
    validation_results: dict[str, Any] = {}
    awaiting_human_approval: bool = False