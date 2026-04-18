"""Parser for Abaqus .inp files."""

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class InpParseResult:
    """Result of parsing an .inp file."""

    # Geometry
    num_nodes: int = 0
    num_elements: int = 0
    element_types: list[str] = field(default_factory=list)
    element_sets: list[str] = field(default_factory=list)
    node_sets: list[str] = field(default_factory=list)

    # Materials
    materials: list[str] = field(default_factory=list)

    # Steps
    steps: list[dict] = field(default_factory=list)

    # Other
    has_contact: bool = False
    has_nlgeom: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "num_nodes": self.num_nodes,
            "num_elements": self.num_elements,
            "element_types": self.element_types,
            "element_sets": self.element_sets,
            "node_sets": self.node_sets,
            "materials": self.materials,
            "steps": self.steps,
            "has_contact": self.has_contact,
            "has_nlgeom": self.has_nlgeom,
        }


class InpParser:
    """Parser for Abaqus .inp (input) files."""

    # Keyword patterns
    PATTERNS = {
        "node": re.compile(r"^\*NODE", re.IGNORECASE | re.MULTILINE),
        "element": re.compile(r"^\*ELEMENT\s*,\s*TYPE\s*=\s*(\w+)", re.IGNORECASE | re.MULTILINE),
        "elset": re.compile(r"^\*ELSET\s*,\s*ELSET\s*=\s*(\w+)", re.IGNORECASE | re.MULTILINE),
        "nset": re.compile(r"^\*NSET\s*,\s*NSET\s*=\s*(\w+)", re.IGNORECASE | re.MULTILINE),
        "material": re.compile(r"^\*MATERIAL\s*,\s*NAME\s*=\s*(\w+)", re.IGNORECASE | re.MULTILINE),
        "step": re.compile(r"^\*STEP", re.IGNORECASE | re.MULTILINE),
        "contact": re.compile(r"^\*(?:CONTACT|SURFACE INTERACTION|TIE)", re.IGNORECASE | re.MULTILINE),
        "nlgeom": re.compile(r"NLGEOM\s*=\s*YES", re.IGNORECASE),
    }

    def parse(self, file_path: Path) -> dict:
        """
        Parse an Abaqus .inp file.

        Args:
            file_path: Path to .inp file

        Returns:
            Dictionary with parsed information
        """
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        result = InpParseResult()

        # Count nodes (approximate by counting lines in *NODE block)
        result.num_nodes = self._count_data_lines(content, "*NODE")

        # Extract element types and count
        element_types = self.PATTERNS["element"].findall(content)
        result.element_types = list(set(element_types))
        result.num_elements = self._count_data_lines(content, "*ELEMENT")

        # Extract element sets
        result.element_sets = self.PATTERNS["elset"].findall(content)

        # Extract node sets
        result.node_sets = self.PATTERNS["nset"].findall(content)

        # Extract materials
        result.materials = self.PATTERNS["material"].findall(content)

        # Count steps
        result.steps = [{"name": f"Step-{i+1}"} for i in range(len(self.PATTERNS["step"].findall(content)))]

        # Check for contact
        result.has_contact = bool(self.PATTERNS["contact"].search(content))

        # Check for NLGEOM
        result.has_nlgeom = bool(self.PATTERNS["nlgeom"].search(content))

        return result.to_dict()

    def parse_mesh(self, file_path: Path) -> dict:
        """
        Parse mesh-specific information from .inp file.

        Args:
            file_path: Path to .inp file

        Returns:
            Dictionary with mesh information
        """
        # For now, use the same as parse()
        # In a full implementation, would extract node coordinates and element connectivity
        return self.parse(file_path)

    def _count_data_lines(self, content: str, keyword: str) -> int:
        """
        Count data lines following a keyword block.

        Args:
            content: File content
            keyword: Abaqus keyword (e.g., "*NODE")

        Returns:
            Approximate count of data lines
        """
        pattern = re.compile(
            rf"^{re.escape(keyword)}.*?\n((?:(?!\*)[^\n]*\n)*)",
            re.IGNORECASE | re.MULTILINE
        )

        count = 0
        for match in pattern.finditer(content):
            data_block = match.group(1)
            # Count non-empty lines
            lines = [line for line in data_block.strip().split("\n") if line.strip()]
            count += len(lines)

        return count

    def validate(self, file_path: Path) -> list[str]:
        """
        Validate .inp file for common issues.

        Args:
            file_path: Path to .inp file

        Returns:
            List of validation warnings/errors
        """
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        issues = []

        # Check for required sections
        if not self.PATTERNS["node"].search(content):
            issues.append("Missing *NODE definition")

        if not self.PATTERNS["element"].search(content):
            issues.append("Missing *ELEMENT definition")

        if not self.PATTERNS["material"].search(content):
            issues.append("Missing *MATERIAL definition")

        if not self.PATTERNS["step"].search(content):
            issues.append("Missing *STEP definition")

        # Check for unbalanced *STEP / *END STEP
        step_count = len(self.PATTERNS["step"].findall(content))
        end_step_count = len(re.findall(r"^\*END\s+STEP", content, re.IGNORECASE | re.MULTILINE))

        if step_count != end_step_count:
            issues.append(f"Unbalanced *STEP ({step_count}) and *END STEP ({end_step_count})")

        return issues
