"""
AbaqusGPT Skill System | 技能系统
=================================

Modular skill architecture inspired by ARIS (Auto Research In Sleep).
借鉴 ARIS 系统的模块化技能架构。

Each skill is a self-contained module with:
- SKILL.md: Skill metadata and documentation
- templates/: Prompt templates and configurations
- Core Python implementation

每个技能是独立模块，包含：
- SKILL.md: 技能元数据和文档
- templates/: 提示模板和配置
- 核心 Python 实现
"""

from .base import Skill, SkillMetadata, SkillRegistry
from .loader import discover_skills, load_skill

__all__ = [
    "Skill",
    "SkillMetadata",
    "SkillRegistry",
    "load_skill",
    "discover_skills",
]
