"""
INP Generator Skill | INP 生成器技能
======================================

Generate Abaqus .inp files from natural language or templates.
从自然语言或模板生成 Abaqus .inp 文件。
"""

from pathlib import Path
from typing import Any, Dict, Optional

from ...llm.client import get_llm_client
from ..base import Skill, SkillMetadata


class InpGeneratorSkill(Skill):
    """
    Skill for generating Abaqus input files.
    生成 Abaqus 输入文件的技能。
    """

    # Built-in templates | 内置模板
    TEMPLATES = {
        "cantilever": {
            "name": "Cantilever Beam | 悬臂梁",
            "parameters": ["length", "width", "height", "load", "material"],
            "description": "Simple cantilever beam with end load",
        },
        "plate_hole": {
            "name": "Plate with Hole | 带孔平板",
            "parameters": ["width", "height", "hole_radius", "pressure", "material"],
            "description": "Rectangular plate with circular hole under tension",
        },
        "contact_3d": {
            "name": "3D Contact | 三维接触",
            "parameters": ["geometry_type", "friction", "contact_type"],
            "description": "Generic 3D contact problem setup",
        },
    }

    def __init__(self, metadata: Optional[SkillMetadata] = None):
        super().__init__(metadata)
        self.llm = get_llm_client()

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute INP generation.
        执行 INP 生成。

        Args:
            context: Generation parameters
                - description: Natural language description
                - template: Template name (alternative to description)
                - parameters: Template parameters
                - format: "inp" or "python"
                - output_path: Optional output file path

        Returns:
            Generated content and metadata
        """
        description = context.get("description")
        template_name = context.get("template")
        output_format = context.get("format", "inp")
        output_path = context.get("output_path")

        # Generate content
        if template_name:
            content = self._generate_from_template(
                template_name,
                context.get("parameters", {})
            )
        elif description:
            if output_format == "python":
                content = self._generate_python(description)
            else:
                content = self._generate_inp(description)
        else:
            return {
                "status": "error",
                "message": "Either 'description' or 'template' is required",
            }

        # Validate generated content
        validation = self._validate_inp(content) if output_format == "inp" else {}

        # Write to file if path provided
        if output_path and validation.get("syntax_ok", True):
            Path(output_path).write_text(content, encoding="utf-8")

        return {
            "status": "success",
            "format": output_format,
            "content": content,
            "output_path": output_path,
            "validation": validation,
        }

    def _generate_inp(self, description: str) -> str:
        """Generate Abaqus .inp file content."""
        prompt = f"""You are an expert Abaqus analyst. Generate a complete Abaqus input (.inp) file based on the following description.

Description: {description}

Requirements:
1. Include all necessary sections: *HEADING, *NODE, *ELEMENT, *MATERIAL, *BOUNDARY, *STEP, etc.
2. Use appropriate element types for the geometry
3. Include comments explaining each section
4. Follow Abaqus input file syntax strictly

Output ONLY the .inp file content, no explanations.
"""
        return self.llm.chat(prompt)

    def _generate_python(self, description: str) -> str:
        """Generate Abaqus Python script."""
        prompt = f"""You are an expert Abaqus analyst. Generate a complete Abaqus Python script based on the following description.

Description: {description}

Requirements:
1. Use abaqus, abaqusConstants, and part modules
2. Create the model, part, material, assembly, step, load, and mesh
3. Include comments explaining each step
4. Follow Abaqus scripting interface conventions

Output ONLY the Python script content, no explanations.
"""
        return self.llm.chat(prompt)

    def _generate_from_template(self, template_name: str, parameters: dict) -> str:
        """Generate from a predefined template."""
        template = self.TEMPLATES.get(template_name)

        if not template:
            return f"** ERROR: Unknown template: {template_name}"

        # For now, use LLM to fill template
        prompt = f"""Generate an Abaqus .inp file for: {template['name']}
Description: {template['description']}

Parameters:
{parameters}

Include all standard sections with proper Abaqus syntax.
"""
        return self.llm.chat(prompt)

    def _validate_inp(self, content: str) -> dict:
        """Validate .inp file syntax."""
        validation = {
            "syntax_ok": True,
            "warnings": [],
            "errors": [],
        }

        lines = content.split("\n")

        # Check for required sections
        required_keywords = ["*HEADING", "*NODE", "*ELEMENT", "*END STEP"]
        found_keywords = set()

        for line in lines:
            line_upper = line.strip().upper()
            for kw in required_keywords:
                if line_upper.startswith(kw):
                    found_keywords.add(kw)

        missing = set(required_keywords) - found_keywords
        if missing:
            validation["warnings"].append(f"Missing sections: {missing}")

        # Check for common syntax issues
        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Check keyword format
            if stripped.startswith("*") and not stripped.startswith("**"):
                # Keywords should be uppercase (warning only)
                keyword = stripped.split(",")[0]
                if keyword != keyword.upper():
                    validation["warnings"].append(
                        f"Line {i}: Keyword should be uppercase: {keyword}"
                    )

        return validation

    def list_templates(self) -> Dict[str, dict]:
        """List available templates."""
        return self.TEMPLATES


def create_inp_generator() -> InpGeneratorSkill:
    """Factory function to create an InpGeneratorSkill instance."""
    metadata = SkillMetadata(
        name="inp-generator",
        version="1.0.0",
        description="Generate Abaqus .inp files from natural language or templates",
        description_cn="从自然语言或模板生成 Abaqus .inp 文件",
        triggers=["generate", "inp", "create model", "生成", "建模"],
    )
    return InpGeneratorSkill(metadata)
