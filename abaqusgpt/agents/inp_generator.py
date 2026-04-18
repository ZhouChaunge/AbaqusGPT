"""InpGenerator - Generate Abaqus input files from natural language."""

from ..llm.client import get_llm_client


class InpGenerator:
    """Agent for generating Abaqus inp files or Python scripts."""

    def __init__(self, model: str = None):
        self.llm = get_llm_client(model=model)

    def generate(self, description: str, format: str = "inp") -> str:
        """
        Generate Abaqus input file or Python script from description.

        Args:
            description: Natural language description of the model
            format: Output format ('inp' or 'python')

        Returns:
            Generated code as string
        """
        if format == "inp":
            return self._generate_inp(description)
        elif format == "python":
            return self._generate_python(description)
        else:
            raise ValueError(f"Unsupported format: {format}")

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
