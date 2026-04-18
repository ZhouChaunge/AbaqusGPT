"""
Skill Base Classes | 技能基类
==============================

Core abstractions for the skill system.
技能系统的核心抽象。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type

import yaml


class SkillPriority(Enum):
    """Skill execution priority | 技能执行优先级"""
    P0 = 0  # Critical path | 关键路径
    P1 = 1  # High priority | 高优先级
    P2 = 2  # Normal | 普通
    P3 = 3  # Low priority | 低优先级


@dataclass
class SkillMetadata:
    """
    Skill metadata parsed from SKILL.md frontmatter.
    从 SKILL.md 头部解析的技能元数据。

    Example SKILL.md:
    ```yaml
    ---
    name: converge-doctor
    version: 1.0.0
    description: Diagnose Abaqus convergence issues
    description_cn: 诊断 Abaqus 收敛问题
    triggers:
      - "diagnose"
      - "convergence"
      - "收敛"
    priority: P1
    dependencies: []
    ---
    ```
    """
    name: str
    version: str = "1.0.0"
    description: str = ""
    description_cn: str = ""
    triggers: List[str] = field(default_factory=list)
    priority: SkillPriority = SkillPriority.P2
    dependencies: List[str] = field(default_factory=list)
    author: str = ""
    tags: List[str] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, yaml_str: str) -> "SkillMetadata":
        """Parse metadata from YAML frontmatter."""
        data = yaml.safe_load(yaml_str) or {}

        priority_str = data.get("priority", "P2")
        try:
            priority = SkillPriority[priority_str]
        except KeyError:
            priority = SkillPriority.P2

        return cls(
            name=data.get("name", "unknown"),
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            description_cn=data.get("description_cn", ""),
            triggers=data.get("triggers", []),
            priority=priority,
            dependencies=data.get("dependencies", []),
            author=data.get("author", ""),
            tags=data.get("tags", []),
        )


class Skill(ABC):
    """
    Abstract base class for all skills.
    所有技能的抽象基类。

    Usage | 用法:
    ```python
    class ConvergeDoctorSkill(Skill):
        def execute(self, context):
            # Diagnose convergence issues
            return diagnosis_result
    ```
    """

    def __init__(self, metadata: Optional[SkillMetadata] = None):
        self.metadata = metadata or SkillMetadata(name=self.__class__.__name__)
        self._templates: Dict[str, str] = {}

    @property
    def name(self) -> str:
        """Skill name | 技能名称"""
        return self.metadata.name

    @property
    def description(self) -> str:
        """Skill description | 技能描述"""
        return self.metadata.description or self.metadata.description_cn

    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the skill with given context.
        使用给定上下文执行技能。

        Args:
            context: Execution context containing inputs and shared state
                     执行上下文，包含输入和共享状态

        Returns:
            Result dictionary with outputs and status
            包含输出和状态的结果字典
        """
        pass

    def validate_inputs(self, context: Dict[str, Any]) -> bool:
        """
        Validate required inputs before execution.
        执行前验证必需的输入。

        Override this method to add custom validation.
        重写此方法以添加自定义验证。
        """
        return True

    def get_template(self, name: str) -> Optional[str]:
        """Get a prompt template by name | 按名称获取提示模板"""
        return self._templates.get(name)

    def load_templates(self, template_dir: Path) -> None:
        """Load all templates from directory | 从目录加载所有模板"""
        if not template_dir.exists():
            return

        for template_file in template_dir.glob("*.md"):
            self._templates[template_file.stem] = template_file.read_text(encoding="utf-8")

    def __repr__(self) -> str:
        return f"<Skill {self.name} v{self.metadata.version}>"


class SkillRegistry:
    """
    Global registry for skill discovery and lookup.
    技能发现和查找的全局注册表。

    Usage | 用法:
    ```python
    registry = SkillRegistry()
    registry.register(ConvergeDoctorSkill)

    skill = registry.get("converge-doctor")
    result = skill.execute(context)
    ```
    """

    _instance: Optional["SkillRegistry"] = None

    def __new__(cls) -> "SkillRegistry":
        """Singleton pattern | 单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._skills: Dict[str, Type[Skill]] = {}
            cls._instance._instances: Dict[str, Skill] = {}
        return cls._instance

    def register(self, skill_class: Type[Skill], metadata: Optional[SkillMetadata] = None) -> None:
        """
        Register a skill class.
        注册技能类。
        """
        instance = skill_class(metadata)
        self._skills[instance.name] = skill_class
        self._instances[instance.name] = instance

    def get(self, name: str) -> Optional[Skill]:
        """
        Get a skill instance by name.
        按名称获取技能实例。
        """
        return self._instances.get(name)

    def find_by_trigger(self, trigger: str) -> List[Skill]:
        """
        Find skills that match a trigger keyword.
        查找匹配触发关键词的技能。
        """
        matches = []
        trigger_lower = trigger.lower()

        for skill in self._instances.values():
            for skill_trigger in skill.metadata.triggers:
                if trigger_lower in skill_trigger.lower():
                    matches.append(skill)
                    break

        return sorted(matches, key=lambda s: s.metadata.priority.value)

    def list_all(self) -> List[Skill]:
        """List all registered skills | 列出所有已注册的技能"""
        return list(self._instances.values())

    def clear(self) -> None:
        """Clear all registrations (for testing) | 清除所有注册（测试用）"""
        self._skills.clear()
        self._instances.clear()


# Global registry instance | 全局注册表实例
_registry = SkillRegistry()


def register_skill(metadata: Optional[SkillMetadata] = None) -> Callable:
    """
    Decorator to register a skill class.
    注册技能类的装饰器。

    Usage | 用法:
    ```python
    @register_skill()
    class MySkill(Skill):
        ...
    ```
    """
    def decorator(cls: Type[Skill]) -> Type[Skill]:
        _registry.register(cls, metadata)
        return cls
    return decorator
