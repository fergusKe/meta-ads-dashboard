"""Agent 協作與工作流工具。"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Dict, List

from utils.history_manager import record_history
from utils.logging_manager import log_event


TaskCallable = Callable[[], Awaitable[Dict]]


@dataclass
class WorkflowStep:
    name: str
    task: TaskCallable
    depends_on: List[str] = field(default_factory=list)


class AgentWorkflow:
    """簡易的工作流引擎，支援依賴與紀錄。"""

    def __init__(self, name: str):
        self.name = name
        self.steps: Dict[str, WorkflowStep] = {}

    def add_step(self, step: WorkflowStep) -> None:
        self.steps[step.name] = step

    async def run(self) -> Dict[str, Dict]:
        log_event("workflow_start", {"workflow": self.name})
        results: Dict[str, Dict] = {}

        for step_name, step in self.steps.items():
            for dep in step.depends_on:
                if dep not in results:
                    raise RuntimeError(f"Step '{step_name}' 依賴未執行的步驟 '{dep}'")

            output = await step.task()
            results[step_name] = output
            record_history(step_name, inputs={}, output=output, metadata={"workflow": self.name})

        log_event("workflow_finished", {"workflow": self.name})
        return results


__all__ = ["AgentWorkflow", "WorkflowStep"]
