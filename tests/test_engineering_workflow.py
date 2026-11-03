import pytest

from app.engineering_workflow import run_workflow
from app.models import RequirementRequest, RequirementType, TaskStatus


@pytest.mark.asyncio
async def test_workflow_completes_all_tasks(tmp_path):
    result = await run_workflow(
        workflow_id="workflow-test",
        request=RequirementRequest(
            requirement="Create a URL shortener with click analytics.",
            scenario_type=RequirementType.GREENFIELD,
        ),
        artifacts_root=tmp_path,
    )

    assert result["status"] == "completed"
    assert all(
        task["status"] == TaskStatus.SUCCEEDED.value
        for task in result["tasks"]
    )
    assert (tmp_path / "workflow-test" / "engineering-summary.md").is_file()
