"""
Mesh Advisor Skill | 网格顾问技能
==================================

Provide mesh quality advice and element selection guidance.
提供网格质量建议和单元选择指导。
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from ...knowledge.element_library import ELEMENT_LIBRARY
from ...llm.client import get_llm_client
from ...parsers.inp_parser import InpParser
from ..base import Skill, SkillMetadata


class MeshAdvisorSkill(Skill):
    """
    Skill for mesh quality analysis and element selection.
    网格质量分析和单元选择的技能。
    """

    # Quality thresholds | 质量阈值
    THRESHOLDS = {
        "aspect_ratio": {"good": 3, "warning": 10, "bad": 20},
        "skewness": {"good": 0.5, "warning": 0.85, "bad": 0.95},
        "jacobian": {"good": 0.5, "warning": 0.1, "bad": 0.01},
        "min_angle_quad": {"good": 45, "warning": 30, "bad": 15},
        "min_angle_tri": {"good": 30, "warning": 15, "bad": 5},
    }

    def __init__(self, metadata: Optional[SkillMetadata] = None):
        super().__init__(metadata)
        self.inp_parser = InpParser()
        self.llm = get_llm_client()

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute mesh advice generation.
        执行网格建议生成。

        Args:
            context: Contains query type and parameters
                - query_type: "element_recommendation" | "quality_check"
                - analysis_type: Analysis type for recommendations
                - geometry_type: Geometry type for recommendations
                - inp_path: Path for quality check

        Returns:
            Mesh advice result dictionary
        """
        query_type = context.get("query_type", "element_recommendation")

        if query_type == "element_recommendation":
            return self._recommend_elements(context)
        elif query_type == "quality_check":
            return self._check_quality(context)
        else:
            return {
                "status": "error",
                "message": f"Unknown query type: {query_type}",
            }

    def _recommend_elements(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Recommend element types based on analysis and geometry."""
        analysis_type = context.get("analysis_type", "static")
        geometry_type = context.get("geometry_type", "solid")
        features = context.get("features", [])  # e.g., ["large_deformation", "contact"]

        recommendations = []

        # Filter elements by geometry type
        for elem_name, elem_info in ELEMENT_LIBRARY.items():
            dims = elem_info.get("dimensions")

            # Match geometry type
            if geometry_type == "solid" and dims == 3:
                score = self._score_element(elem_info, analysis_type, features)
                recommendations.append({
                    "element": elem_name,
                    "name": elem_info.get("name"),
                    "name_cn": elem_info.get("name_cn"),
                    "score": score,
                    "use_cases": elem_info.get("use_cases", []),
                    "warnings": elem_info.get("warnings", []),
                })
            elif geometry_type == "shell" and dims == "shell":
                score = self._score_element(elem_info, analysis_type, features)
                recommendations.append({
                    "element": elem_name,
                    "name": elem_info.get("name"),
                    "name_cn": elem_info.get("name_cn"),
                    "score": score,
                    "use_cases": elem_info.get("use_cases", []),
                    "warnings": elem_info.get("warnings", []),
                })

        # Sort by score
        recommendations.sort(key=lambda x: x["score"], reverse=True)

        return {
            "status": "success",
            "query": {
                "analysis_type": analysis_type,
                "geometry_type": geometry_type,
                "features": features,
            },
            "recommendations": recommendations[:5],  # Top 5
            "all_options": len(recommendations),
        }

    def _score_element(
        self,
        elem_info: dict,
        analysis_type: str,
        features: List[str]
    ) -> float:
        """Score an element's suitability for given analysis."""
        score = 50.0  # Base score

        use_cases = " ".join(elem_info.get("use_cases", []))
        warnings = " ".join(elem_info.get("warnings", []))
        integration = elem_info.get("integration", "")

        # Analysis type matching
        if analysis_type == "static":
            if "精确" in use_cases or "一般" in use_cases:
                score += 20
        elif analysis_type == "dynamic":
            if "接触" in use_cases or integration == "reduced":
                score += 20
        elif analysis_type == "large_deformation":
            if "大变形" in use_cases:
                score += 30
            if integration == "reduced":
                score += 10

        # Feature matching
        if "large_deformation" in features:
            if "大变形" in use_cases:
                score += 20
            if "大变形" in warnings:
                score -= 10

        if "contact" in features:
            if "接触" in use_cases:
                score += 20
            if "接触" in warnings:
                score -= 15

        if "bending" in features:
            if "弯曲" in use_cases:
                score += 20
            if "弯曲" in warnings or "剪切锁死" in warnings:
                score -= 15

        return score

    def _check_quality(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Check mesh quality from .inp file."""
        inp_path = context.get("inp_path")

        if not inp_path:
            return {
                "status": "error",
                "message": "inp_path is required for quality check",
            }

        file_path = Path(inp_path)
        if not file_path.exists():
            return {
                "status": "error",
                "message": f"File not found: {inp_path}",
            }

        # Parse mesh data
        mesh_data = self.inp_parser.parse_mesh(file_path)

        # Calculate metrics
        metrics = {
            "total_elements": mesh_data.get("num_elements", 0),
            "total_nodes": mesh_data.get("num_nodes", 0),
            "element_types": mesh_data.get("element_types", []),
        }

        # Generate recommendations using LLM
        llm_recommendations = self._generate_recommendations(metrics)

        return {
            "status": "success",
            "metrics": metrics,
            "recommendations": llm_recommendations,
        }

    def _generate_recommendations(self, metrics: dict) -> str:
        """Generate mesh improvement recommendations using LLM."""
        prompt = f"""You are an expert in finite element mesh quality.

Analyze the following mesh data and provide recommendations:

Mesh Data:
- Total elements: {metrics['total_elements']}
- Total nodes: {metrics['total_nodes']}
- Element types: {metrics['element_types']}

Provide specific recommendations for:
1. Mesh density improvements
2. Element type suggestions
3. Problem areas to refine
4. Best practices for this type of model

Be concise and actionable. Use Chinese for the response.
"""
        return self.llm.chat(prompt)


def create_mesh_advisor() -> MeshAdvisorSkill:
    """Factory function to create a MeshAdvisorSkill instance."""
    metadata = SkillMetadata(
        name="mesh-advisor",
        version="1.0.0",
        description="Provide mesh quality advice and element selection guidance",
        description_cn="提供网格质量建议和单元选择指导",
        triggers=["mesh", "element", "网格", "单元", "划分"],
    )
    return MeshAdvisorSkill(metadata)
