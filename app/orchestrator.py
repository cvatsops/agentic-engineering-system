
import asyncio
from collections.abc import Awaitable, Callable

from app.models import EngineeringTask, TaskStatus


TaskHandler = Callable[
    [EngineeringTask, dict[str, dict]], Awaitable[dict]
]


class OrchestrationError(Exception):
    pass


class Orchestrator:
    def __init__(self, handlers: dict[str, TaskHandler]):
        self.handlers = handlers

    async def execute(
        self, tasks: list[EngineeringTask]
    ) -> list[EngineeringTask]:
        task_map = {task.task_id: task for task in tasks}

        if len(task_map) != len(tasks):
            raise OrchestrationError("Duplicate task IDs")

        for task in tasks:
            unknown = set(task.dependencies) - set(task_map)
            if unknown:
                raise OrchestrationError(
                    f"{task.task_id} has unknown dependencies: "
                    f"{sorted(unknown)}"
                )

            if task.task_id in task.dependencies:
                raise OrchestrationError(
                    f"{task.task_id} cannot depend on itself"
                )

        self._check_cycles(task_map)

        completed_outputs: dict[str, dict] = {}
        remaining = set(task_map)

        while remaining:
            # Propagate a dependency failure through every downstream level
            # before deciding whether any work is runnable. A single pass can
            # otherwise leave a task blocked by a task that was only just
            # marked BLOCKED, which is not an orchestration deadlock.
            while True:
                blocked = [
                    task_map[task_id]
                    for task_id in remaining
                    if any(
                        task_map[dep].status in {
                            TaskStatus.FAILED,
                            TaskStatus.BLOCKED,
                        }
                        for dep in task_map[task_id].dependencies
                    )
                ]

                if not blocked:
                    break

                for task in blocked:
                    task.status = TaskStatus.BLOCKED
                    task.error = "A dependency did not succeed"
                    remaining.remove(task.task_id)

            ready = [
                task_map[task_id]
                for task_id in sorted(remaining)
                if all(
                    task_map[dep].status == TaskStatus.SUCCEEDED
                    for dep in task_map[task_id].dependencies
                )
            ]

            if not ready:
                if remaining:
                    raise OrchestrationError(
                        "No executable tasks remain; check task states"
                    )
                break

            # Execute all currently independent tasks concurrently.
            outcomes = await asyncio.gather(
                *[
                    self._run_task(task, completed_outputs)
                    for task in ready
                ],
                return_exceptions=True,
            )

            for task, outcome in zip(ready, outcomes):
                if isinstance(outcome, Exception):
                    task.status = TaskStatus.FAILED
                    task.error = str(outcome)
                else:
                    task.status = TaskStatus.SUCCEEDED
                    task.output = outcome
                    completed_outputs[task.task_id] = outcome

                remaining.remove(task.task_id)

        return tasks

    async def _run_task(
        self,
        task: EngineeringTask,
        completed_outputs: dict[str, dict],
    ) -> dict:
        handler = self.handlers.get(task.task_id)

        if handler is None:
            raise OrchestrationError(
                f"No handler registered for {task.task_id}"
            )

        task.status = TaskStatus.RUNNING

        # Pass only the outputs of this task's direct dependencies.
        dependency_outputs = {
            dep: completed_outputs[dep]
            for dep in task.dependencies
            if dep in completed_outputs
        }

        return await handler(task, dependency_outputs)

    @staticmethod
    def _check_cycles(
        task_map: dict[str, EngineeringTask]
    ) -> None:
        visited: set[str] = set()
        active: set[str] = set()

        def visit(task_id: str) -> None:
            if task_id in active:
                raise OrchestrationError(
                    f"Dependency cycle detected at {task_id}"
                )

            if task_id in visited:
                return

            active.add(task_id)

            for dependency in task_map[task_id].dependencies:
                visit(dependency)

            active.remove(task_id)
            visited.add(task_id)

        for task_id in task_map:
            visit(task_id)
