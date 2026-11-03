
from uuid import uuid4

from fastapi import FastAPI

from app.engineering_workflow import run_workflow
from app.models import RequirementRequest

app = FastAPI(
    title="Agentic Engineering System",
    version="0.1.0",
)


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/engineering/workflows")
async def create_engineering_workflow(
    request: RequirementRequest,
):
    workflow_id = uuid4().hex[:12]

    return await run_workflow(
        workflow_id=workflow_id,
        request=request,
    )