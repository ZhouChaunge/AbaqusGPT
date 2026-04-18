"""
Converge Doctor Skill | 收敛医生技能
=====================================

Diagnose Abaqus convergence issues.
诊断 Abaqus 收敛问题。
"""

from pathlib import Path
from typing import Any, Dict

from ...knowledge.error_codes import ERROR_DATABASE
from ...llm.client import get_llm_client
from ...parsers.msg_parser import MsgParser
from ...parsers.sta_parser import StaParser
from ..base import Skill, SkillMetadata


class ConvergeDoctorSkill(Skill):
    """
    Skill for diagnosing Abaqus convergence issues.
    诊断 Abaqus 收敛问题的技能。
    """

    def __init__(self, metadata: SkillMetadata | None = None):
        super().__init__(metadata)
        self.msg_parser = MsgParser()
        self.sta_parser = StaParser()
        self.llm = get_llm_client()

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute convergence diagnosis.
        执行收敛诊断。

        Args:
            context: Must contain "file_path" (str)
                    Optional: "verbose" (bool)

        Returns:
            Diagnosis result dictionary
        """
        file_path = Path(context.get("file_path", ""))
        verbose = context.get("verbose", False)

        if not file_path.exists():
            return {
                "status": "error",
                "message": f"File not found: {file_path}",
            }

        # Parse file based on extension
        suffix = file_path.suffix.lower()

        if suffix == ".msg":
            parsed_data = self.msg_parser.parse(file_path)
        elif suffix == ".sta":
            parsed_data = self.sta_parser.parse(file_path)
        else:
            return {
                "status": "error",
                "message": f"Unsupported file type: {suffix}",
            }

        # Check known error patterns
        known_issues = self._check_known_errors(parsed_data)

        # Generate diagnosis using LLM
        diagnosis = self._generate_diagnosis(parsed_data, known_issues)

        # Extract recommendations
        recommendations = self._extract_recommendations(known_issues)

        return {
            "status": "success",
            "errors_found": parsed_data.get("errors", []),
            "warnings": parsed_data.get("warnings", []),
            "known_patterns": [issue["pattern"] for issue in known_issues],
            "diagnosis": diagnosis,
            "recommendations": recommendations,
            "last_increment": parsed_data.get("last_increment"),
            "verbose_data": parsed_data if verbose else None,
        }

    def _check_known_errors(self, parsed_data: dict) -> list:
        """Check parsed data against known error patterns."""
        issues = []

        for error in parsed_data.get("errors", []):
            for pattern, info in ERROR_DATABASE.items():
                if pattern.lower() in error.lower():
                    issues.append({
                        "pattern": pattern,
                        "error": error,
                        "info": info
                    })
                    break

        return issues

    def _generate_diagnosis(self, parsed_data: dict, known_issues: list) -> str:
        """Generate diagnosis using LLM."""
        prompt = f"""You are an expert Abaqus analyst. Diagnose the following convergence issue.

Parsed Data:
- Errors: {parsed_data.get('errors', [])}
- Warnings: {parsed_data.get('warnings', [])}
- Last successful increment: {parsed_data.get('last_increment', 'N/A')}
- Total iterations: {parsed_data.get('total_iterations', 'N/A')}

Known issues matched: {[i['pattern'] for i in known_issues]}

Provide:
1. Root cause analysis (most likely cause first)
2. Specific fix recommendations with Abaqus keywords/parameters
3. Prevention tips for future

Be concise and actionable. Use Chinese for the response.
"""

        return self.llm.chat(prompt)

    def _extract_recommendations(self, known_issues: list) -> list:
        """Extract recommendations from known issues."""
        recommendations = []

        for issue in known_issues:
            info = issue.get("info", {})
            for solution in info.get("solutions", []):
                if solution not in recommendations:
                    recommendations.append(solution)

        return recommendations

    def validate_inputs(self, context: Dict[str, Any]) -> bool:
        """Validate that file_path is provided."""
        return "file_path" in context


# Create default instance for convenience
def create_converge_doctor() -> ConvergeDoctorSkill:
    """Factory function to create a ConvergeDoctorSkill instance."""
    metadata = SkillMetadata(
        name="converge-doctor",
        version="1.0.0",
        description="Diagnose and fix Abaqus convergence issues",
        description_cn="诊断并修复 Abaqus 收敛问题",
        triggers=["diagnose", "convergence", "收敛", "不收敛", "报错", "error"],
    )
    return ConvergeDoctorSkill(metadata)
