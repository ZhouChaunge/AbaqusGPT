"""Parser for Abaqus .sta files."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class StaParseResult:
    """Result of parsing a .sta file."""

    steps: list[dict] = field(default_factory=list)
    total_increments: int = 0
    completed: bool = False

    # Last state
    last_step: Optional[int] = None
    last_increment: Optional[int] = None
    last_time: Optional[float] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "steps": self.steps,
            "total_increments": self.total_increments,
            "completed": self.completed,
            "last_step": self.last_step,
            "last_increment": self.last_increment,
            "last_time": self.last_time,
        }


class StaParser:
    """Parser for Abaqus .sta (status) files."""

    # Column format for .sta file
    # SUMMARY OF JOB INFORMATION:
    #  STEP      INC     ATT  SEVERE     EQUIL    TOTAL   TOTAL       STEP       INC OF
    #                        DISCON    ITERS    ITERS    TIME/      TIME/LPF    TIME/LPF
    #                        ITERS                     FREQ                     MONITOR

    STEP_PATTERN = re.compile(
        r"^\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d.E+-]+)\s+([\d.E+-]+)",
        re.MULTILINE
    )

    def parse(self, file_path: Path) -> dict:
        """
        Parse an Abaqus .sta file.

        Args:
            file_path: Path to .sta file

        Returns:
            Dictionary with parsed information
        """
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        result = StaParseResult()

        increments = []

        for match in self.STEP_PATTERN.finditer(content):
            increment_data = {
                "step": int(match.group(1)),
                "increment": int(match.group(2)),
                "attempts": int(match.group(3)),
                "severe_discon_iters": int(match.group(4)),
                "equil_iters": int(match.group(5)),
                "total_iters": int(match.group(6)),
                "total_time": float(match.group(7)),
                "step_time": float(match.group(8)),
            }
            increments.append(increment_data)

        if increments:
            result.steps = increments
            result.total_increments = len(increments)

            last = increments[-1]
            result.last_step = last["step"]
            result.last_increment = last["increment"]
            result.last_time = last["total_time"]

            # Check if completed (step time reached 1.0)
            result.completed = last["step_time"] >= 1.0 - 1e-6

        return result.to_dict()

    def get_convergence_history(self, parsed_data: dict) -> list[dict]:
        """
        Extract convergence history for analysis.

        Args:
            parsed_data: Dictionary from parse()

        Returns:
            List of convergence data points
        """
        history = []

        for step_data in parsed_data.get("steps", []):
            history.append({
                "step": step_data["step"],
                "increment": step_data["increment"],
                "iterations": step_data["total_iters"],
                "attempts": step_data["attempts"],
                "severe_warnings": step_data["severe_discon_iters"],
            })

        return history

    def identify_problem_increments(self, parsed_data: dict) -> list[dict]:
        """
        Identify increments with potential convergence issues.

        Args:
            parsed_data: Dictionary from parse()

        Returns:
            List of problematic increments with reasons
        """
        problems = []

        for step_data in parsed_data.get("steps", []):
            issues = []

            # High iteration count
            if step_data["total_iters"] > 10:
                issues.append(f"高迭代次数 ({step_data['total_iters']})")

            # Multiple attempts
            if step_data["attempts"] > 1:
                issues.append(f"多次尝试 ({step_data['attempts']})")

            # Severe discontinuity iterations
            if step_data["severe_discon_iters"] > 0:
                issues.append(f"严重不连续 ({step_data['severe_discon_iters']})")

            if issues:
                problems.append({
                    "step": step_data["step"],
                    "increment": step_data["increment"],
                    "issues": issues
                })

        return problems
