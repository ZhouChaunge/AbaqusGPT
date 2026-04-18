"""Parser for Abaqus .msg files."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class MsgParseResult:
    """Result of parsing a .msg file."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    severe_warnings: list[str] = field(default_factory=list)

    # Convergence info
    last_increment: Optional[int] = None
    last_step: Optional[int] = None
    total_iterations: int = 0

    # Time info
    step_time: Optional[float] = None
    total_time: Optional[float] = None

    # Specific issues
    contact_issues: list[str] = field(default_factory=list)
    element_issues: list[str] = field(default_factory=list)
    material_issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "errors": self.errors,
            "warnings": self.warnings,
            "severe_warnings": self.severe_warnings,
            "last_increment": self.last_increment,
            "last_step": self.last_step,
            "total_iterations": self.total_iterations,
            "step_time": self.step_time,
            "total_time": self.total_time,
            "contact_issues": self.contact_issues,
            "element_issues": self.element_issues,
            "material_issues": self.material_issues,
        }


class MsgParser:
    """Parser for Abaqus .msg (message) files."""

    # Regex patterns for different message types
    PATTERNS = {
        "error": re.compile(r"^\s*\*\*\*ERROR:?\s*(.+)", re.MULTILINE),
        "warning": re.compile(r"^\s*\*\*\*WARNING:?\s*(.+)", re.MULTILINE),
        "severe_warning": re.compile(r"^\s*\*\*\*NOTE:.*SEVERE\s+DISCONTINUIT", re.MULTILINE | re.IGNORECASE),
        "increment": re.compile(r"INCREMENT\s+(\d+)\s+STARTS", re.IGNORECASE),
        "step": re.compile(r"STEP\s+(\d+)\s+INCREMENT\s+(\d+)", re.IGNORECASE),
        "iteration": re.compile(r"ITERATION\s+(\d+)", re.IGNORECASE),
        "time": re.compile(r"STEP TIME\s*=\s*([\d.E+-]+).*TOTAL TIME\s*=\s*([\d.E+-]+)", re.IGNORECASE),
        "convergence_fail": re.compile(r"TOO MANY ATTEMPTS|NOT CONVERGE|CONVERGENCE.*FAIL", re.IGNORECASE),
        "contact": re.compile(r"CONTACT|PENETRATION|OVERCLOSURE|SEPARATION", re.IGNORECASE),
        "element": re.compile(r"ELEMENT\s+\d+.*(?:DISTORT|NEGATIVE|JACOBIAN|HOUR)", re.IGNORECASE),
        "material": re.compile(r"(?:PLASTIC|DAMAGE|FAILURE|STRAIN).*(?:LIMIT|EXCEED|ERROR)", re.IGNORECASE),
    }

    def parse(self, file_path: Path) -> dict:
        """
        Parse an Abaqus .msg file.

        Args:
            file_path: Path to .msg file

        Returns:
            Dictionary with parsed information
        """
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        result = MsgParseResult()

        # Extract errors
        for match in self.PATTERNS["error"].finditer(content):
            error_text = match.group(1).strip()
            result.errors.append(error_text)

            # Categorize specific issues
            if self.PATTERNS["contact"].search(error_text):
                result.contact_issues.append(error_text)
            if self.PATTERNS["element"].search(error_text):
                result.element_issues.append(error_text)
            if self.PATTERNS["material"].search(error_text):
                result.material_issues.append(error_text)

        # Extract warnings
        for match in self.PATTERNS["warning"].finditer(content):
            warning_text = match.group(1).strip()
            result.warnings.append(warning_text)

            # Check for severe discontinuity warnings
            if "SEVERE" in warning_text.upper() or "DISCONTINUIT" in warning_text.upper():
                result.severe_warnings.append(warning_text)

        # Extract step and increment info
        step_matches = list(self.PATTERNS["step"].finditer(content))
        if step_matches:
            last_match = step_matches[-1]
            result.last_step = int(last_match.group(1))
            result.last_increment = int(last_match.group(2))

        # Count iterations
        result.total_iterations = len(self.PATTERNS["iteration"].findall(content))

        # Extract time info
        time_matches = list(self.PATTERNS["time"].finditer(content))
        if time_matches:
            last_time = time_matches[-1]
            result.step_time = float(last_time.group(1))
            result.total_time = float(last_time.group(2))

        return result.to_dict()

    def get_summary(self, parsed_data: dict) -> str:
        """
        Generate a human-readable summary of parsed data.

        Args:
            parsed_data: Dictionary from parse()

        Returns:
            Summary string
        """
        lines = []

        # Status
        if parsed_data["errors"]:
            lines.append("🔴 状态: 分析失败")
        elif parsed_data["warnings"]:
            lines.append("⚠️ 状态: 完成但有警告")
        else:
            lines.append("✅ 状态: 成功完成")

        # Progress
        if parsed_data["last_step"] is not None:
            lines.append(f"📍 位置: Step {parsed_data['last_step']}, Increment {parsed_data['last_increment']}")

        if parsed_data["total_iterations"]:
            lines.append(f"🔄 总迭代次数: {parsed_data['total_iterations']}")

        # Issues count
        lines.append(f"❌ 错误: {len(parsed_data['errors'])}")
        lines.append(f"⚠️ 警告: {len(parsed_data['warnings'])}")

        # Specific issues
        if parsed_data["contact_issues"]:
            lines.append(f"👆 接触问题: {len(parsed_data['contact_issues'])}")
        if parsed_data["element_issues"]:
            lines.append(f"🔲 单元问题: {len(parsed_data['element_issues'])}")
        if parsed_data["material_issues"]:
            lines.append(f"📦 材料问题: {len(parsed_data['material_issues'])}")

        return "\n".join(lines)
