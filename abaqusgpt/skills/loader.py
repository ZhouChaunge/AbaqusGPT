"""
Skill Loader | 技能加载器
==========================

Discover and load skills from the skills directory.
从 skills 目录发现并加载技能。
"""

import importlib
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .base import Skill, SkillMetadata, SkillRegistry


def parse_skill_md(skill_md_path: Path) -> Tuple[SkillMetadata, str]:
    """
    Parse SKILL.md file to extract metadata and content.
    解析 SKILL.md 文件，提取元数据和内容。

    Args:
        skill_md_path: Path to SKILL.md file

    Returns:
        Tuple of (metadata, content)
    """
    content = skill_md_path.read_text(encoding="utf-8")

    # Extract YAML frontmatter between --- markers
    frontmatter_pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
    match = re.match(frontmatter_pattern, content, re.DOTALL)

    if match:
        yaml_str = match.group(1)
        body = match.group(2)
        metadata = SkillMetadata.from_yaml(yaml_str)
    else:
        # No frontmatter, use defaults
        metadata = SkillMetadata(name=skill_md_path.parent.name)
        body = content

    return metadata, body


def load_skill(skill_dir: Path) -> Optional[Skill]:
    """
    Load a skill from a directory.
    从目录加载技能。

    The directory should contain:
    - SKILL.md: Skill metadata and documentation
    - __init__.py or skill.py: Skill implementation
    - templates/: Optional prompt templates

    Args:
        skill_dir: Path to skill directory

    Returns:
        Loaded skill instance or None if loading fails
    """
    skill_md = skill_dir / "SKILL.md"

    if not skill_md.exists():
        return None

    # Parse metadata
    metadata, _ = parse_skill_md(skill_md)

    # Try to import the skill module
    skill_module_name = skill_dir.name.replace("-", "_")

    try:
        # Try __init__.py first
        module_path = f"abaqusgpt.skills.{skill_module_name}"
        module = importlib.import_module(module_path)

        # Look for a Skill subclass
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, Skill)
                and attr is not Skill
            ):
                skill_instance = attr(metadata)

                # Load templates if available
                template_dir = skill_dir / "templates"
                skill_instance.load_templates(template_dir)

                return skill_instance

    except ImportError:
        pass

    return None


def discover_skills(skills_dir: Optional[Path] = None) -> Dict[str, Skill]:
    """
    Discover and load all skills from the skills directory.
    从 skills 目录发现并加载所有技能。

    Args:
        skills_dir: Path to skills directory. Defaults to abaqusgpt/skills/

    Returns:
        Dictionary mapping skill names to skill instances
    """
    if skills_dir is None:
        skills_dir = Path(__file__).parent

    skills: Dict[str, Skill] = {}
    registry = SkillRegistry()

    for item in skills_dir.iterdir():
        if not item.is_dir():
            continue

        # Skip special directories
        if item.name.startswith(("_", ".")):
            continue

        # Skip shared-references (not a skill)
        if item.name == "shared-references":
            continue

        skill = load_skill(item)
        if skill:
            skills[skill.name] = skill
            registry.register(type(skill), skill.metadata)

    return skills


def get_skill_list() -> List[Dict]:
    """
    Get a list of all available skills with their metadata.
    获取所有可用技能及其元数据的列表。

    Returns:
        List of skill info dictionaries
    """
    skills = discover_skills()

    return [
        {
            "name": skill.name,
            "version": skill.metadata.version,
            "description": skill.description,
            "triggers": skill.metadata.triggers,
            "priority": skill.metadata.priority.name,
        }
        for skill in skills.values()
    ]
