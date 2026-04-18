"""
Workflow Engine | 工作流引擎
=============================

Core workflow orchestration engine.
核心工作流编排引擎。
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class WorkflowStatus(Enum):
    """Workflow execution status | 工作流执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(Enum):
    """Step execution status | 步骤执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowStep:
    """
    A single step in a workflow.
    工作流中的单个步骤。
    """
    name: str
    skill: str  # Skill name to execute | 要执行的技能名称
    description: str = ""
    description_cn: str = ""
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    status: StepStatus = StepStatus.PENDING
    error: Optional[str] = None
    requires_human_checkpoint: bool = False
    retry_count: int = 0
    max_retries: int = 3

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "skill": self.skill,
            "description": self.description,
            "description_cn": self.description_cn,
            "status": self.status.value,
            "error": self.error,
            "requires_human_checkpoint": self.requires_human_checkpoint,
        }


@dataclass
class Workflow:
    """
    A workflow definition containing multiple steps.
    包含多个步骤的工作流定义。
    """
    name: str
    description: str = ""
    description_cn: str = ""
    steps: List[WorkflowStep] = field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.PENDING
    current_step_index: int = 0
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        self.updated_at = datetime.now()

    @property
    def current_step(self) -> Optional[WorkflowStep]:
        """Get current step."""
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    @property
    def progress(self) -> float:
        """Calculate workflow progress (0.0 - 1.0)."""
        if not self.steps:
            return 0.0
        completed = sum(1 for s in self.steps if s.status == StepStatus.COMPLETED)
        return completed / len(self.steps)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "description_cn": self.description_cn,
            "status": self.status.value,
            "current_step_index": self.current_step_index,
            "progress": self.progress,
            "steps": [s.to_dict() for s in self.steps],
            "context": self.context,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Workflow":
        """Create from dictionary."""
        workflow = cls(
            name=data["name"],
            description=data.get("description", ""),
            description_cn=data.get("description_cn", ""),
        )
        workflow.status = WorkflowStatus(data.get("status", "pending"))
        workflow.current_step_index = data.get("current_step_index", 0)
        workflow.context = data.get("context", {})

        for step_data in data.get("steps", []):
            step = WorkflowStep(
                name=step_data["name"],
                skill=step_data["skill"],
                description=step_data.get("description", ""),
                description_cn=step_data.get("description_cn", ""),
            )
            step.status = StepStatus(step_data.get("status", "pending"))
            workflow.steps.append(step)

        return workflow


class WorkflowEngine:
    """
    Engine for executing workflows.
    执行工作流的引擎。

    Usage | 用法:
    ```python
    engine = WorkflowEngine()

    # Load a predefined workflow
    workflow = engine.load_workflow("diagnosis-fix-loop")

    # Execute
    result = await engine.run(workflow, context={
        "job_path": "path/to/job.msg"
    })
    ```
    """

    def __init__(self, state_dir: Optional[Path] = None):
        """
        Initialize workflow engine.

        Args:
            state_dir: Directory for state persistence
        """
        self.state_dir = state_dir or Path.cwd() / ".abaqusgpt"
        self.state_dir.mkdir(exist_ok=True)

        self._skill_registry: Dict[str, Callable] = {}
        self._human_checkpoint_handler: Optional[Callable] = None

    def register_skill(self, name: str, skill_callable: Callable) -> None:
        """Register a skill for workflow execution."""
        self._skill_registry[name] = skill_callable

    def set_human_checkpoint_handler(self, handler: Callable) -> None:
        """
        Set handler for human checkpoints.
        设置人机检查点处理器。

        Handler signature: async def handler(workflow, step) -> bool
        Returns True to continue, False to pause.
        """
        self._human_checkpoint_handler = handler

    async def run(
        self,
        workflow: Workflow,
        context: Optional[Dict[str, Any]] = None,
        auto_proceed: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute a workflow.
        执行工作流。

        Args:
            workflow: Workflow to execute
            context: Initial context data
            auto_proceed: Skip human checkpoints

        Returns:
            Execution result
        """
        # Initialize context
        if context:
            workflow.context.update(context)

        workflow.status = WorkflowStatus.RUNNING
        workflow.updated_at = datetime.now()

        try:
            while workflow.current_step_index < len(workflow.steps):
                step = workflow.current_step
                if step is None:
                    break

                # Check for human checkpoint
                if step.requires_human_checkpoint and not auto_proceed:
                    if self._human_checkpoint_handler:
                        should_continue = await self._human_checkpoint_handler(workflow, step)
                        if not should_continue:
                            workflow.status = WorkflowStatus.PAUSED
                            self._save_state(workflow)
                            return {
                                "status": "paused",
                                "workflow": workflow.to_dict(),
                                "message": f"Paused at step: {step.name}",
                            }

                # Execute step
                step.status = StepStatus.RUNNING
                self._save_state(workflow)

                try:
                    result = await self._execute_step(step, workflow.context)
                    step.outputs = result
                    step.status = StepStatus.COMPLETED

                    # Update context with outputs
                    workflow.context[f"{step.name}_result"] = result

                except Exception as e:
                    step.error = str(e)
                    step.retry_count += 1

                    if step.retry_count < step.max_retries:
                        continue  # Retry
                    else:
                        step.status = StepStatus.FAILED
                        workflow.status = WorkflowStatus.FAILED
                        self._save_state(workflow)
                        return {
                            "status": "failed",
                            "workflow": workflow.to_dict(),
                            "error": str(e),
                        }

                workflow.current_step_index += 1
                workflow.updated_at = datetime.now()
                self._save_state(workflow)

            # All steps completed
            workflow.status = WorkflowStatus.COMPLETED
            self._save_state(workflow)

            return {
                "status": "completed",
                "workflow": workflow.to_dict(),
                "results": workflow.context,
            }

        except Exception as e:
            workflow.status = WorkflowStatus.FAILED
            self._save_state(workflow)
            return {
                "status": "failed",
                "workflow": workflow.to_dict(),
                "error": str(e),
            }

    async def _execute_step(
        self,
        step: WorkflowStep,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single workflow step."""
        skill = self._skill_registry.get(step.skill)

        if skill is None:
            # Try to load skill dynamically
            from ..skills.loader import discover_skills
            skills = discover_skills()
            if step.skill in skills:
                skill_instance = skills[step.skill]
                skill = skill_instance.execute

        if skill is None:
            raise ValueError(f"Unknown skill: {step.skill}")

        # Merge step inputs with context
        step_context = {**context, **step.inputs}

        # Execute skill
        if callable(skill):
            import asyncio
            if asyncio.iscoroutinefunction(skill):
                return await skill(step_context)
            else:
                return skill(step_context)

        raise ValueError(f"Skill {step.skill} is not callable")

    def _save_state(self, workflow: Workflow) -> None:
        """Save workflow state to disk."""
        state_file = self.state_dir / f"workflow_{workflow.name}.json"
        state_file.write_text(
            json.dumps(workflow.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def load_state(self, workflow_name: str) -> Optional[Workflow]:
        """Load workflow state from disk."""
        state_file = self.state_dir / f"workflow_{workflow_name}.json"
        if state_file.exists():
            data = json.loads(state_file.read_text(encoding="utf-8"))
            return Workflow.from_dict(data)
        return None

    def resume(self, workflow: Workflow) -> None:
        """Resume a paused workflow."""
        if workflow.status == WorkflowStatus.PAUSED:
            workflow.status = WorkflowStatus.RUNNING

    def cancel(self, workflow: Workflow) -> None:
        """Cancel a running workflow."""
        workflow.status = WorkflowStatus.CANCELLED
        self._save_state(workflow)

    def get_progress(self, workflow: Workflow) -> Dict[str, Any]:
        """Get workflow progress report."""
        return {
            "name": workflow.name,
            "status": workflow.status.value,
            "progress": f"{workflow.progress * 100:.1f}%",
            "current_step": workflow.current_step.name if workflow.current_step else None,
            "completed_steps": sum(1 for s in workflow.steps if s.status == StepStatus.COMPLETED),
            "total_steps": len(workflow.steps),
        }
