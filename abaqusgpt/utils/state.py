"""
State Manager | 状态管理器
===========================

Persistent state management for long-running tasks.
长时间任务的持久化状态管理。
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class AbaqusGPTState:
    """
    Persistent state for AbaqusGPT sessions.
    AbaqusGPT 会话的持久化状态。

    Inspired by ARIS REVIEW_STATE.json pattern.
    灵感来自 ARIS 的 REVIEW_STATE.json 模式。
    """
    # Workflow state | 工作流状态
    workflow: str = ""
    stage: str = ""
    current_step: int = 0

    # Job information | 作业信息
    job_name: str = ""
    job_path: str = ""
    last_increment: int = 0

    # Error tracking | 错误追踪
    last_error: str = ""
    error_count: int = 0

    # Fix tracking | 修复追踪
    applied_fixes: List[str] = field(default_factory=list)
    pending_trials: List[str] = field(default_factory=list)

    # History | 历史记录
    history: List[Dict[str, Any]] = field(default_factory=list)

    # Timestamps | 时间戳
    created_at: str = ""
    updated_at: str = ""
    expires_at: str = ""

    def __post_init__(self):
        now = datetime.now()
        if not self.created_at:
            self.created_at = now.isoformat()
        self.updated_at = now.isoformat()
        if not self.expires_at:
            self.expires_at = (now + timedelta(hours=24)).isoformat()

    def is_expired(self) -> bool:
        """Check if state has expired."""
        if not self.expires_at:
            return False
        return datetime.now() > datetime.fromisoformat(self.expires_at)

    def add_history(self, action: str, details: Optional[Dict] = None) -> None:
        """Add an entry to history."""
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details or {},
        })
        self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AbaqusGPTState":
        """Create from dictionary."""
        return cls(**data)


class StateManager:
    """
    Manager for persistent state.
    持久化状态管理器。

    Usage | 用法:
    ```python
    manager = StateManager()

    # Load or create state
    state = manager.load("my_job")

    # Update state
    state.stage = "diagnosis"
    state.add_history("diagnosed", {"errors": 3})

    # Save state
    manager.save(state)
    ```
    """

    DEFAULT_STATE_FILE = "abaqusgpt-state.json"

    def __init__(self, state_dir: Optional[Path] = None):
        """
        Initialize state manager.

        Args:
            state_dir: Directory for state files. Defaults to current directory.
        """
        self.state_dir = Path(state_dir) if state_dir else Path.cwd()
        self._current_state: Optional[AbaqusGPTState] = None

    @property
    def state_file(self) -> Path:
        """Get the state file path."""
        return self.state_dir / self.DEFAULT_STATE_FILE

    def load(self, job_name: Optional[str] = None) -> AbaqusGPTState:
        """
        Load state from disk or create new.
        从磁盘加载状态或创建新状态。

        Args:
            job_name: Optional job name to filter state

        Returns:
            Loaded or new state
        """
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text(encoding="utf-8"))
                state = AbaqusGPTState.from_dict(data)

                # Check expiration
                if state.is_expired():
                    self._archive_state(state)
                    state = AbaqusGPTState(job_name=job_name or "")

                # Check job name match
                if job_name and state.job_name and state.job_name != job_name:
                    # Different job, create new state
                    self._archive_state(state)
                    state = AbaqusGPTState(job_name=job_name)

                self._current_state = state
                return state

            except (json.JSONDecodeError, TypeError, KeyError):
                # Invalid state file, create new
                pass

        # Create new state
        state = AbaqusGPTState(job_name=job_name or "")
        self._current_state = state
        return state

    def save(self, state: Optional[AbaqusGPTState] = None) -> None:
        """
        Save state to disk.
        将状态保存到磁盘。

        Args:
            state: State to save. Uses current state if not provided.
        """
        state = state or self._current_state
        if state is None:
            raise ValueError("No state to save")

        state.updated_at = datetime.now().isoformat()

        self.state_file.write_text(
            json.dumps(state.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        self._current_state = state

    def clear(self) -> None:
        """Clear current state and remove state file."""
        if self.state_file.exists():
            self.state_file.unlink()
        self._current_state = None

    def _archive_state(self, state: AbaqusGPTState) -> None:
        """Archive expired or replaced state."""
        archive_dir = self.state_dir / ".abaqusgpt-archive"
        archive_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_file = archive_dir / f"state_{timestamp}.json"

        archive_file.write_text(
            json.dumps(state.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def get_history(self, limit: int = 10) -> List[Dict]:
        """Get recent history entries."""
        if self._current_state is None:
            return []
        return self._current_state.history[-limit:]

    def update(self, **kwargs) -> AbaqusGPTState:
        """
        Update current state with given values.
        使用给定值更新当前状态。

        Args:
            **kwargs: State fields to update

        Returns:
            Updated state
        """
        if self._current_state is None:
            self._current_state = AbaqusGPTState()

        for key, value in kwargs.items():
            if hasattr(self._current_state, key):
                setattr(self._current_state, key, value)

        self.save()
        return self._current_state
