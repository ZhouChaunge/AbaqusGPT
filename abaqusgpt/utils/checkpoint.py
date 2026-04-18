"""
Human Checkpoint | 人机检查点
==============================

Pause workflow for human review and confirmation.
暂停工作流以供人工审查和确认。
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional


class CheckpointDecision(Enum):
    """Human checkpoint decision | 人机检查点决策"""
    APPROVE = "approve"       # Continue with proposed action | 继续执行建议的操作
    REJECT = "reject"         # Reject and stop | 拒绝并停止
    MODIFY = "modify"         # Modify and continue | 修改后继续
    SKIP = "skip"             # Skip this step | 跳过此步骤
    TIMEOUT = "timeout"       # Auto-proceed after timeout | 超时后自动继续


@dataclass
class CheckpointResult:
    """Result of a human checkpoint | 人机检查点的结果"""
    decision: CheckpointDecision
    modifications: Dict[str, Any]
    comment: str
    timestamp: datetime
    auto_proceeded: bool = False

    def approved(self) -> bool:
        """Check if checkpoint was approved."""
        return self.decision in (CheckpointDecision.APPROVE, CheckpointDecision.TIMEOUT)


class HumanCheckpoint:
    """
    Human checkpoint handler for workflow pause/resume.
    工作流暂停/恢复的人机检查点处理器。

    Inspired by ARIS HUMAN_CHECKPOINT mechanism.
    灵感来自 ARIS 的 HUMAN_CHECKPOINT 机制。

    Usage | 用法:
    ```python
    checkpoint = HumanCheckpoint()

    @checkpoint.require("Review proposed fixes")
    async def apply_fixes(fixes: List[str]):
        # Wait for human approval before applying
        ...

    # Or use directly
    result = await checkpoint.wait(
        title="Confirm Analysis",
        description="Review the following diagnosis",
        data={"errors": [...], "recommendations": [...]},
        timeout=300  # 5 minutes
    )

    if result.approved():
        # Proceed with action
        ...
    ```
    """

    def __init__(
        self,
        auto_proceed: bool = False,
        default_timeout: int = 300,  # 5 minutes
        callback: Optional[Callable] = None,
    ):
        """
        Initialize human checkpoint handler.

        Args:
            auto_proceed: If True, automatically approve all checkpoints
            default_timeout: Default timeout in seconds (0 = no timeout)
            callback: Optional callback for UI integration
        """
        self.auto_proceed = auto_proceed
        self.default_timeout = default_timeout
        self.callback = callback
        self._history: List[CheckpointResult] = []

    async def wait(
        self,
        title: str,
        description: str = "",
        data: Optional[Dict[str, Any]] = None,
        options: Optional[List[str]] = None,
        timeout: Optional[int] = None,
    ) -> CheckpointResult:
        """
        Wait for human decision at checkpoint.
        在检查点等待人工决策。

        Args:
            title: Checkpoint title
            description: Detailed description
            data: Data to display for review
            options: Available options (defaults to approve/reject)
            timeout: Timeout in seconds (None = use default)

        Returns:
            CheckpointResult with human decision
        """
        timeout = timeout if timeout is not None else self.default_timeout

        # Auto-proceed mode
        if self.auto_proceed:
            result = CheckpointResult(
                decision=CheckpointDecision.APPROVE,
                modifications={},
                comment="Auto-proceeded",
                timestamp=datetime.now(),
                auto_proceeded=True,
            )
            self._history.append(result)
            return result

        # Display checkpoint info
        self._display_checkpoint(title, description, data, options)

        # Wait for input (with timeout)
        try:
            if self.callback:
                # Use callback for UI integration
                decision_data = await asyncio.wait_for(
                    self.callback(title, description, data, options),
                    timeout=timeout if timeout > 0 else None
                )
            else:
                # Console input
                decision_data = await asyncio.wait_for(
                    self._console_input(title, options),
                    timeout=timeout if timeout > 0 else None
                )

            result = CheckpointResult(
                decision=CheckpointDecision(decision_data.get("decision", "approve")),
                modifications=decision_data.get("modifications", {}),
                comment=decision_data.get("comment", ""),
                timestamp=datetime.now(),
            )

        except asyncio.TimeoutError:
            # Timeout - auto-proceed
            result = CheckpointResult(
                decision=CheckpointDecision.TIMEOUT,
                modifications={},
                comment=f"Auto-proceeded after {timeout}s timeout",
                timestamp=datetime.now(),
                auto_proceeded=True,
            )

        self._history.append(result)
        self._log_decision(title, result)

        return result

    def _display_checkpoint(
        self,
        title: str,
        description: str,
        data: Optional[Dict],
        options: Optional[List[str]],
    ) -> None:
        """Display checkpoint information to console."""
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table

        console = Console()

        console.print()
        console.print(Panel(
            f"[bold yellow]🔔 HUMAN CHECKPOINT[/bold yellow]\n\n"
            f"[bold]{title}[/bold]\n\n"
            f"{description}",
            title="⏸️ 等待人工确认",
            border_style="yellow",
        ))

        if data:
            # Display data as table
            table = Table(title="审查数据 | Review Data")
            table.add_column("Key", style="cyan")
            table.add_column("Value", style="white")

            for key, value in data.items():
                if isinstance(value, list):
                    value = "\n".join(f"• {v}" for v in value[:5])
                    if len(data[key]) > 5:
                        value += f"\n... and {len(data[key]) - 5} more"
                table.add_row(key, str(value))

            console.print(table)

        console.print()
        console.print("[dim]Options: (y) Approve | (n) Reject | (s) Skip | (m) Modify[/dim]")

    async def _console_input(
        self,
        title: str,
        options: Optional[List[str]],
    ) -> Dict[str, Any]:
        """Get input from console."""
        # Use asyncio to make input non-blocking
        loop = asyncio.get_event_loop()

        # Run input in executor
        response = await loop.run_in_executor(
            None,
            lambda: input("\n请输入选择 | Enter choice (y/n/s/m): ").strip().lower()
        )

        decision_map = {
            "y": "approve",
            "yes": "approve",
            "n": "reject",
            "no": "reject",
            "s": "skip",
            "skip": "skip",
            "m": "modify",
            "modify": "modify",
        }

        decision = decision_map.get(response, "approve")

        modifications = {}
        comment = ""

        if decision == "modify":
            comment = await loop.run_in_executor(
                None,
                lambda: input("请输入修改说明 | Enter modification: ").strip()
            )

        return {
            "decision": decision,
            "modifications": modifications,
            "comment": comment,
        }

    def _log_decision(self, title: str, result: CheckpointResult) -> None:
        """Log the checkpoint decision."""
        from rich.console import Console

        console = Console()

        decision_emoji = {
            CheckpointDecision.APPROVE: "✅",
            CheckpointDecision.REJECT: "❌",
            CheckpointDecision.MODIFY: "✏️",
            CheckpointDecision.SKIP: "⏭️",
            CheckpointDecision.TIMEOUT: "⏰",
        }

        emoji = decision_emoji.get(result.decision, "❓")
        auto_note = " (auto)" if result.auto_proceeded else ""

        console.print(f"\n{emoji} Checkpoint '{title}': {result.decision.value}{auto_note}")
        if result.comment:
            console.print(f"   Comment: {result.comment}")

    def require(self, title: str, description: str = "") -> Callable:
        """
        Decorator to require human checkpoint before function execution.
        在函数执行前要求人机检查点的装饰器。

        Usage | 用法:
        ```python
        @checkpoint.require("Confirm action")
        async def dangerous_action():
            ...
        ```
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                result = await self.wait(
                    title=title,
                    description=description,
                    data={"args": args, "kwargs": kwargs} if args or kwargs else None,
                )

                if not result.approved():
                    raise CheckpointRejected(f"Checkpoint '{title}' was rejected")

                # Apply modifications if any
                if result.modifications:
                    kwargs.update(result.modifications)

                return await func(*args, **kwargs)

            return wrapper
        return decorator

    def get_history(self, limit: int = 10) -> List[CheckpointResult]:
        """Get recent checkpoint history."""
        return self._history[-limit:]


class CheckpointRejected(Exception):
    """Exception raised when a checkpoint is rejected."""
    pass


# Convenience function | 便捷函数
def checkpoint(
    title: str,
    description: str = "",
    auto_proceed: bool = False,
) -> Callable:
    """
    Decorator for human checkpoint.
    人机检查点装饰器。

    Usage | 用法:
    ```python
    @checkpoint("Review changes before apply")
    async def apply_changes():
        ...
    ```
    """
    handler = HumanCheckpoint(auto_proceed=auto_proceed)
    return handler.require(title, description)
