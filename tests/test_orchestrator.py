
import asyncio

import pytest

from app.models import EngineeringTask, TaskStatus
from app.orchestrator import OrchestrationError, Orchestrator


@pytest.mark.asyncio
async def test_dependent_tasks_receive_upstream_output():
    async def design(task, dependencies):
        return {"api_contract": "POST /urls"}

    async def implementation(task, dependencies):
        contract = dependencies["design"]["api_contract"]
        return {"implemented_contract": contract}

    tasks = [
        EngineeringTask(
            task_id="design",
            title="Design API",
            description="Define API contract",
        ),
        EngineeringTask(
            task_id="implementation",
            title="Implement API",
            description="Implement the contract",
            dependencies=["design"],
        ),
    ]

    orchestrator = Orchestrator({
        "design": design,
        "implementation": implementation,
    })

    result = await orchestrator.execute(tasks)

    assert all(t.status == TaskStatus.SUCCEEDED for t in result)
    assert result[1].output["implemented_contract"] == "POST /urls"


@pytest.mark.asyncio
async def test_failure_blocks_dependent_task():
    async def fail(task, dependencies):
        raise RuntimeError("Design generation failed")

    async def downstream(task, dependencies):
        return {"unexpected": True}

    tasks = [
        EngineeringTask(
            task_id="design",
            title="Design",
            description="Design the API",
        ),
        EngineeringTask(
            task_id="implementation",
            title="Implement",
            description="Implement the API",
            dependencies=["design"],
        ),
    ]

    orchestrator = Orchestrator({
        "design": fail,
        "implementation": downstream,
    })

    result = await orchestrator.execute(tasks)

    assert result[0].status == TaskStatus.FAILED
    assert result[1].status == TaskStatus.BLOCKED


@pytest.mark.asyncio
async def test_failure_blocks_all_downstream_levels():
    async def fail(task, dependencies):
        raise RuntimeError("Design generation failed")

    async def downstream(task, dependencies):
        return {"unexpected": True}

    tasks = [
        EngineeringTask(
            task_id="design",
            title="Design",
            description="Design the API",
        ),
        EngineeringTask(
            task_id="implementation",
            title="Implement",
            description="Implement the API",
            dependencies=["design"],
        ),
        EngineeringTask(
            task_id="summary",
            title="Summarize",
            description="Summarize the implementation",
            dependencies=["implementation"],
        ),
    ]

    result = await Orchestrator({
        "design": fail,
        "implementation": downstream,
        "summary": downstream,
    }).execute(tasks)

    assert [task.status for task in result] == [
        TaskStatus.FAILED,
        TaskStatus.BLOCKED,
        TaskStatus.BLOCKED,
    ]


@pytest.mark.asyncio
async def test_dependency_cycle_is_rejected():
    tasks = [
        EngineeringTask(
            task_id="a",
            title="Task A",
            description="First task",
            dependencies=["b"],
        ),
        EngineeringTask(
            task_id="b",
            title="Task B",
            description="Second task",
            dependencies=["a"],
        ),
    ]

    orchestrator = Orchestrator({})

    with pytest.raises(OrchestrationError, match="cycle"):
        await orchestrator.execute(tasks)
