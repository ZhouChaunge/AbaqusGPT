"""
Workflow Definitions | 工作流定义
==================================

Predefined workflows for common simulation tasks.
常见仿真任务的预定义工作流。
"""

from .engine import Workflow, WorkflowStep

# =============================================================================
# Workflow 1: Modeling to Solving | 建模到求解
# =============================================================================

MODELING_TO_SOLVING = Workflow(
    name="modeling-to-solving",
    description="Complete workflow from model generation to analysis",
    description_cn="从模型生成到分析的完整工作流",
    steps=[
        WorkflowStep(
            name="generate-model",
            skill="inp-generator",
            description="Generate INP file from description",
            description_cn="从描述生成 INP 文件",
            requires_human_checkpoint=True,  # Review generated model
        ),
        WorkflowStep(
            name="check-mesh",
            skill="mesh-advisor",
            description="Check and optimize mesh quality",
            description_cn="检查和优化网格质量",
        ),
        WorkflowStep(
            name="validate-model",
            skill="domain-expert",
            description="Validate model settings",
            description_cn="验证模型设置",
            requires_human_checkpoint=True,  # Confirm before running
        ),
    ],
)


# =============================================================================
# Workflow 2: Diagnosis-Fix Loop | 诊断修复循环
# =============================================================================

DIAGNOSIS_FIX_LOOP = Workflow(
    name="diagnosis-fix-loop",
    description="Diagnose and iteratively fix convergence issues",
    description_cn="诊断并迭代修复收敛问题",
    steps=[
        WorkflowStep(
            name="parse-results",
            skill="converge-doctor",
            description="Parse and analyze result files",
            description_cn="解析和分析结果文件",
        ),
        WorkflowStep(
            name="diagnose-issues",
            skill="converge-doctor",
            description="Identify root causes",
            description_cn="识别根本原因",
        ),
        WorkflowStep(
            name="propose-fixes",
            skill="converge-doctor",
            description="Generate fix recommendations",
            description_cn="生成修复建议",
            requires_human_checkpoint=True,  # Review proposed fixes
        ),
        WorkflowStep(
            name="apply-fixes",
            skill="inp-generator",
            description="Apply selected fixes to model",
            description_cn="将选定的修复应用到模型",
            requires_human_checkpoint=True,  # Confirm changes
        ),
    ],
)


# =============================================================================
# Workflow 3: Full Simulation Lifecycle | 完整仿真生命周期
# =============================================================================

FULL_SIMULATION_LIFECYCLE = Workflow(
    name="full-simulation-lifecycle",
    description="Complete simulation lifecycle from modeling to optimization",
    description_cn="从建模到优化的完整仿真生命周期",
    steps=[
        # Phase 1: Modeling | 建模阶段
        WorkflowStep(
            name="requirements-analysis",
            skill="domain-expert",
            description="Analyze simulation requirements",
            description_cn="分析仿真需求",
        ),
        WorkflowStep(
            name="model-generation",
            skill="inp-generator",
            description="Generate initial model",
            description_cn="生成初始模型",
            requires_human_checkpoint=True,
        ),

        # Phase 2: Meshing | 网格划分阶段
        WorkflowStep(
            name="mesh-generation",
            skill="mesh-advisor",
            description="Generate and optimize mesh",
            description_cn="生成和优化网格",
        ),
        WorkflowStep(
            name="mesh-quality-check",
            skill="mesh-advisor",
            description="Check mesh quality",
            description_cn="检查网格质量",
            requires_human_checkpoint=True,
        ),

        # Phase 3: Solving | 求解阶段
        WorkflowStep(
            name="pre-check",
            skill="domain-expert",
            description="Pre-analysis validation",
            description_cn="分析前验证",
        ),

        # Phase 4: Diagnosis | 诊断阶段
        WorkflowStep(
            name="result-parsing",
            skill="converge-doctor",
            description="Parse analysis results",
            description_cn="解析分析结果",
        ),
        WorkflowStep(
            name="issue-diagnosis",
            skill="converge-doctor",
            description="Diagnose any issues",
            description_cn="诊断问题",
            requires_human_checkpoint=True,
        ),

        # Phase 5: Optimization | 优化阶段
        WorkflowStep(
            name="recommendations",
            skill="domain-expert",
            description="Generate optimization recommendations",
            description_cn="生成优化建议",
        ),
    ],
)


# =============================================================================
# Workflow Registry | 工作流注册表
# =============================================================================

WORKFLOW_REGISTRY = {
    "modeling-to-solving": MODELING_TO_SOLVING,
    "diagnosis-fix-loop": DIAGNOSIS_FIX_LOOP,
    "full-simulation-lifecycle": FULL_SIMULATION_LIFECYCLE,
}


def get_workflow(name: str) -> Workflow:
    """
    Get a predefined workflow by name.
    按名称获取预定义工作流。

    Args:
        name: Workflow name

    Returns:
        Workflow instance (copy)
    """
    if name not in WORKFLOW_REGISTRY:
        raise ValueError(f"Unknown workflow: {name}. Available: {list(WORKFLOW_REGISTRY.keys())}")

    # Return a copy to avoid modifying the original
    import copy
    return copy.deepcopy(WORKFLOW_REGISTRY[name])


def list_workflows() -> list:
    """
    List all available workflows.
    列出所有可用的工作流。
    """
    return [
        {
            "name": wf.name,
            "description": wf.description,
            "description_cn": wf.description_cn,
            "steps": len(wf.steps),
        }
        for wf in WORKFLOW_REGISTRY.values()
    ]
