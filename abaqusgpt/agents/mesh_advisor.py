"""MeshAdvisor - Analyze mesh quality and provide optimization suggestions."""

from pathlib import Path

from rich.panel import Panel
from rich.table import Table

from ..llm.client import get_llm_client
from ..parsers.inp_parser import InpParser


class MeshAdvisor:
    """Agent for analyzing mesh quality."""

    # Quality thresholds
    THRESHOLDS = {
        "aspect_ratio": {"good": 3, "warning": 10, "bad": 20},
        "skewness": {"good": 0.5, "warning": 0.85, "bad": 0.95},
        "jacobian": {"good": 0.5, "warning": 0.1, "bad": 0.01},
        "min_angle_quad": {"good": 45, "warning": 30, "bad": 15},
        "min_angle_tri": {"good": 30, "warning": 15, "bad": 5},
    }

    def __init__(self, model: str = None):
        self.inp_parser = InpParser()
        self.llm = get_llm_client(model=model)

    def analyze(self, file_path: Path) -> str:
        """
        Analyze mesh quality from .inp file.

        Args:
            file_path: Path to .inp file

        Returns:
            Mesh quality report
        """
        # Parse inp file
        mesh_data = self.inp_parser.parse_mesh(file_path)

        # Calculate quality metrics
        metrics = self._calculate_metrics(mesh_data)

        # Generate recommendations
        recommendations = self._generate_recommendations(mesh_data, metrics)

        return self._format_report(mesh_data, metrics, recommendations)

    def _calculate_metrics(self, mesh_data: dict) -> dict:
        """Calculate mesh quality metrics."""
        metrics = {
            "total_elements": mesh_data.get("num_elements", 0),
            "total_nodes": mesh_data.get("num_nodes", 0),
            "element_types": mesh_data.get("element_types", []),
            "quality_distribution": {
                "good": 0,
                "warning": 0,
                "bad": 0
            }
        }

        # In a full implementation, would calculate actual metrics
        # This is a placeholder structure

        return metrics

    def _generate_recommendations(self, mesh_data: dict, metrics: dict) -> str:
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

    def _format_report(self, mesh_data: dict, metrics: dict, recommendations: str) -> str:
        """Format the mesh quality report."""
        output = []

        # Summary table
        table = Table(title="📊 网格质量报告")
        table.add_column("指标", style="cyan")
        table.add_column("值", style="white")

        table.add_row("总单元数", str(metrics["total_elements"]))
        table.add_row("总节点数", str(metrics["total_nodes"]))
        table.add_row("单元类型", ", ".join(metrics["element_types"]) or "N/A")

        output.append(table)

        # Recommendations
        output.append(Panel(recommendations, title="💡 优化建议"))

        return "\n".join(str(o) for o in output)
