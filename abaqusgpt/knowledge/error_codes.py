"""Abaqus error codes database."""

from typing import Optional

ERROR_DATABASE = {
    # Convergence errors
    "TOO MANY ATTEMPTS MADE FOR THIS INCREMENT": {
        "category": "convergence",
        "severity": "critical",
        "causes": [
            "时间步太大，导致求解器无法找到平衡状态",
            "接触设置不当，如穿透过大或接触刚度不合理",
            "材料参数导致局部失稳或软化",
            "边界条件或载荷突变",
            "网格质量差，导致数值问题"
        ],
        "solutions": [
            "减小初始增量步大小 (*STATIC, 0.01 而非 0.1)",
            "增加最大增量数 (*STEP, INC=10000)",
            "检查并调整接触对定义",
            "添加阻尼或稳定化 (*STATIC, STABILIZE)",
            "检查边界条件是否有跳变，考虑使用 AMPLITUDE 平滑过渡"
        ],
        "reference": "Abaqus Analysis User's Guide 7.2.1"
    },

    "NEGATIVE EIGENVALUE": {
        "category": "stability",
        "severity": "warning",
        "causes": [
            "结构发生失稳（屈曲）",
            "材料软化导致刚度矩阵负定",
            "接触分离导致约束丧失",
            "使用了不当的单元类型"
        ],
        "solutions": [
            "启用几何非线性 (NLGEOM=YES)",
            "考虑使用 Riks 方法处理失稳问题",
            "检查是否需要先进行屈曲分析",
            "添加初始缺陷或扰动"
        ],
        "reference": "Abaqus Analysis User's Guide 6.2.4"
    },

    "EXCESSIVE DISTORTION": {
        "category": "element",
        "severity": "critical",
        "causes": [
            "单元变形过大，超出允许范围",
            "网格太粗，无法捕捉变形梯度",
            "材料模型不适合大变形分析",
            "边界条件导致局部应变集中"
        ],
        "solutions": [
            "加密网格，特别是在大变形区域",
            "启用 NLGEOM=YES",
            "使用适合大变形的单元类型 (如 C3D8R)",
            "检查材料模型是否支持大应变",
            "考虑使用自适应网格 (ALE)"
        ],
        "reference": "Abaqus Analysis User's Guide 10.2.1"
    },

    "ZERO PIVOT": {
        "category": "singularity",
        "severity": "critical",
        "causes": [
            "模型存在刚体运动（约束不足）",
            "存在未连接的节点或单元",
            "材料刚度为零或接近零",
            "接触完全分离"
        ],
        "solutions": [
            "检查边界条件是否完全约束刚体运动",
            "检查模型连接性，确保所有部件正确连接",
            "检查材料参数是否合理",
            "添加软弹簧或使用 *EQUATION 消除奇异性"
        ],
        "reference": "Abaqus Analysis User's Guide 7.1.1"
    },

    "CONTACT OVERCLOSURE": {
        "category": "contact",
        "severity": "warning",
        "causes": [
            "初始几何存在穿透",
            "接触面定义不正确",
            "主从面选择不当",
            "接触刚度设置过高"
        ],
        "solutions": [
            "使用 *CONTACT CONTROLS 调整初始穿透处理",
            "检查并修正几何，消除初始穿透",
            "重新定义接触面，确保法向一致",
            "调整接触刚度或使用 penalty 方法"
        ],
        "reference": "Abaqus Analysis User's Guide 35.1.1"
    },

    "SEVERE DISCONTINUITY ITERATION": {
        "category": "contact",
        "severity": "warning",
        "causes": [
            "接触状态频繁变化（开-闭-开）",
            "摩擦状态不稳定（滑动-粘着）",
            "载荷或边界条件变化过快"
        ],
        "solutions": [
            "减小增量步大小",
            "使用接触稳定化 (*CONTACT STABILIZATION)",
            "调整摩擦系数或使用指数摩擦模型",
            "平滑载荷曲线"
        ],
        "reference": "Abaqus Analysis User's Guide 35.1.2"
    },

    "ELEMENT HAS NEGATIVE JACOBIAN": {
        "category": "element",
        "severity": "critical",
        "causes": [
            "单元翻转或严重扭曲",
            "网格质量差",
            "大变形导致单元退化"
        ],
        "solutions": [
            "重新划分网格，提高网格质量",
            "使用二次单元替代线性单元",
            "启用沙漏控制",
            "减小增量步大小"
        ],
        "reference": "Abaqus Analysis User's Guide 26.1.1"
    },

    "PLASTICITY ALGORITHM DID NOT CONVERGE": {
        "category": "material",
        "severity": "critical",
        "causes": [
            "塑性应变增量过大",
            "硬化曲线数据不连续",
            "材料参数不合理"
        ],
        "solutions": [
            "减小增量步大小",
            "平滑硬化曲线数据",
            "检查屈服应力和硬化模量是否合理",
            "增加数据点密度"
        ],
        "reference": "Abaqus Analysis User's Guide 22.2.1"
    },

    "TIME INCREMENT REQUIRED IS LESS THAN THE MINIMUM": {
        "category": "convergence",
        "severity": "critical",
        "causes": [
            "局部非线性太强",
            "接触条件变化剧烈",
            "最小增量步设置过大"
        ],
        "solutions": [
            "减小最小增量步限制",
            "使用自动时间步控制",
            "检查导致局部剧烈变化的原因",
            "添加稳定化"
        ],
        "reference": "Abaqus Analysis User's Guide 7.2.1"
    },

    "HYPERELASTIC MATERIAL HAS BECOME UNSTABLE": {
        "category": "material",
        "severity": "critical",
        "causes": [
            "超弹性材料参数导致能量不稳定",
            "变形超出材料模型适用范围",
            "不当的材料模型选择"
        ],
        "solutions": [
            "检查材料参数（应满足 Drucker 稳定性条件）",
            "使用实验数据重新拟合参数",
            "尝试不同的超弹性模型",
            "限制最大应变范围"
        ],
        "reference": "Abaqus Analysis User's Guide 22.5.1"
    },

    # =========================================================================
    # Additional Contact Errors | 补充接触错误
    # =========================================================================

    "CONTACT CONSTRAINT OVERCONSTRAINTS": {
        "category": "contact",
        "severity": "warning",
        "causes": [
            "接触约束与边界条件冲突",
            "多个接触对约束同一节点",
            "接触约束与MPC冲突"
        ],
        "solutions": [
            "检查边界条件与接触区域是否重叠",
            "使用tied约束代替刚性接触",
            "调整接触主从面定义",
            "使用Abaqus/Standard的自动过约束处理"
        ],
        "reference": "Abaqus Analysis User's Guide 35.1.1"
    },

    "SLAVE NODE IS INITIALLY IN CONTACT": {
        "category": "contact",
        "severity": "warning",
        "causes": [
            "初始几何穿透",
            "网格不匹配",
            "装配位置不正确"
        ],
        "solutions": [
            "使用*CONTACT CLEARANCE调整初始间隙",
            "使用*CONTACT INTERFERENCE允许初始穿透",
            "修正几何模型消除穿透"
        ],
        "reference": "Abaqus Analysis User's Guide 35.3.1"
    },

    "EXCESSIVE CONTACT ADJUSTMENT REQUIRED": {
        "category": "contact",
        "severity": "warning",
        "causes": [
            "初始穿透量过大",
            "网格尺寸不匹配严重",
            "几何间隙与接触容差不匹配"
        ],
        "solutions": [
            "修正几何减少初始穿透",
            "使用更细的网格",
            "分多个增量步逐步消除穿透"
        ],
        "reference": "Abaqus Analysis User's Guide 35.3.4"
    },

    "CONTACT SURFACE TRACKING LOST": {
        "category": "contact",
        "severity": "critical",
        "causes": [
            "接触面相对滑动过大",
            "增量步过大",
            "接触搜索算法失效"
        ],
        "solutions": [
            "减小增量步大小",
            "使用更密的接触网格",
            "增加接触跟踪范围",
            "考虑使用general contact"
        ],
        "reference": "Abaqus Analysis User's Guide 35.2.1"
    },

    # =========================================================================
    # Additional Material Errors | 补充材料错误
    # =========================================================================

    "NEGATIVE EIGENVALUE IN MATERIAL STIFFNESS": {
        "category": "material",
        "severity": "critical",
        "causes": [
            "材料刚度矩阵不正定",
            "超弹性材料能量函数不稳定",
            "损伤演化导致刚度下降过快"
        ],
        "solutions": [
            "检查材料参数（弹性模量、泊松比）",
            "使用稳定化方法（*STABILIZE）",
            "调整损伤演化参数",
            "使用粘性正则化"
        ],
        "reference": "Abaqus Analysis User's Guide 22.1.1"
    },

    "CREEP STRAIN RATE IS TOO LARGE": {
        "category": "material",
        "severity": "warning",
        "causes": [
            "蠕变参数导致应变率过大",
            "温度变化引起蠕变加速",
            "增量步过大"
        ],
        "solutions": [
            "减小增量步大小",
            "检查蠕变本构参数",
            "使用显式蠕变积分"
        ],
        "reference": "Abaqus Analysis User's Guide 22.2.4"
    },

    "DAMAGE HAS EXCEEDED THE MAXIMUM ALLOWED": {
        "category": "material",
        "severity": "critical",
        "causes": [
            "损伤变量超过临界值",
            "单元完全失效",
            "损伤演化过快"
        ],
        "solutions": [
            "使用单元删除（*ELEMENT DELETION）",
            "调整损伤演化参数",
            "增加损伤正则化长度",
            "减小增量步"
        ],
        "reference": "Abaqus Analysis User's Guide 24.1.1"
    },

    "VISCOELASTIC MATERIAL MODEL ERROR": {
        "category": "material",
        "severity": "critical",
        "causes": [
            "Prony级数参数不合理",
            "松弛时间过短",
            "频域参数与时域不一致"
        ],
        "solutions": [
            "确保∑gi ≤ 1",
            "检查松弛时间的合理性",
            "从实验数据重新拟合参数"
        ],
        "reference": "Abaqus Analysis User's Guide 22.7.1"
    },

    # =========================================================================
    # Boundary Condition Errors | 边界条件错误
    # =========================================================================

    "PRESCRIBED MOTION IS INCOMPATIBLE": {
        "category": "boundary",
        "severity": "critical",
        "causes": [
            "位移边界条件相互冲突",
            "刚体运动约束与边界条件冲突",
            "MPC与边界条件冲突"
        ],
        "solutions": [
            "检查边界条件定义",
            "移除冲突的约束",
            "使用软弹簧代替硬约束"
        ],
        "reference": "Abaqus Analysis User's Guide 34.3.1"
    },

    "BOUNDARY CONDITION AND LOAD AT SAME DOF": {
        "category": "boundary",
        "severity": "warning",
        "causes": [
            "在同一自由度上同时施加位移和力",
            "载荷与约束冲突"
        ],
        "solutions": [
            "移除冲突的载荷或边界条件",
            "使用弹簧连接代替硬约束"
        ],
        "reference": "Abaqus Analysis User's Guide 34.3.2"
    },

    "MPC INCONSISTENT WITH BOUNDARY CONDITIONS": {
        "category": "boundary",
        "severity": "critical",
        "causes": [
            "MPC约束与边界条件冲突",
            "MPC链式约束不一致",
            "边界条件阻止了MPC所需的运动"
        ],
        "solutions": [
            "检查MPC定义与边界条件",
            "调整MPC主从节点选择",
            "使用coupling约束代替MPC"
        ],
        "reference": "Abaqus Analysis User's Guide 34.2.2"
    },

    "APPLIED LOAD EXCEEDS REASONABLE RANGE": {
        "category": "boundary",
        "severity": "warning",
        "causes": [
            "载荷幅值过大",
            "单位系统不一致",
            "载荷施加位置错误"
        ],
        "solutions": [
            "检查载荷单位和幅值",
            "确认单位系统一致性",
            "使用渐进加载"
        ],
        "reference": "Abaqus Analysis User's Guide 34.4.1"
    },

    # =========================================================================
    # Solver Errors | 求解器错误
    # =========================================================================

    "LINEAR SOLVER FAILED": {
        "category": "solver",
        "severity": "critical",
        "causes": [
            "刚度矩阵奇异",
            "内存不足",
            "矩阵病态"
        ],
        "solutions": [
            "检查边界条件是否充分约束刚体运动",
            "增加内存分配",
            "使用迭代求解器代替直接求解器",
            "检查几何和材料参数"
        ],
        "reference": "Abaqus Analysis User's Guide 6.1.1"
    },

    "ITERATIVE SOLVER DID NOT CONVERGE": {
        "category": "solver",
        "severity": "critical",
        "causes": [
            "预处理器选择不当",
            "矩阵条件数过高",
            "迭代次数不足"
        ],
        "solutions": [
            "尝试不同的预处理器",
            "增加最大迭代次数",
            "改用直接求解器",
            "改善网格质量"
        ],
        "reference": "Abaqus Analysis User's Guide 6.1.3"
    },

    "INSUFFICIENT MEMORY FOR SOLVER": {
        "category": "solver",
        "severity": "critical",
        "causes": [
            "模型规模过大",
            "内存分配不足",
            "求解器选择不当"
        ],
        "solutions": [
            "增加内存分配（memory参数）",
            "使用迭代求解器",
            "使用域分解并行",
            "简化模型或使用子模型"
        ],
        "reference": "Abaqus Analysis User's Guide 3.4.1"
    },

    "CUTBACK TOO SEVERE": {
        "category": "solver",
        "severity": "warning",
        "causes": [
            "非线性过强导致步长急剧减小",
            "材料或接触行为突变",
            "几何不稳定"
        ],
        "solutions": [
            "增加最大迭代次数",
            "使用line search",
            "添加稳定化",
            "检查模型非线性来源"
        ],
        "reference": "Abaqus Analysis User's Guide 7.2.3"
    },

    # =========================================================================
    # Output and Post-processing Errors | 输出和后处理错误
    # =========================================================================

    "OUTPUT REQUEST INVALID": {
        "category": "output",
        "severity": "warning",
        "causes": [
            "请求的输出变量不适用于当前单元类型",
            "输出频率设置不合理",
            "输出集定义错误"
        ],
        "solutions": [
            "检查输出变量与单元类型的兼容性",
            "使用适当的输出频率",
            "检查输出集定义"
        ],
        "reference": "Abaqus Analysis User's Guide 4.1.1"
    },

    "ODB FILE SIZE LIMIT EXCEEDED": {
        "category": "output",
        "severity": "warning",
        "causes": [
            "输出频率过高",
            "输出变量过多",
            "模型规模大且步数多"
        ],
        "solutions": [
            "减少输出频率",
            "只输出关键变量",
            "使用选择性输出集",
            "分多个作业运行"
        ],
        "reference": "Abaqus Analysis User's Guide 4.1.2"
    },
}


def get_error_info(error_text: str) -> Optional[dict]:
    """
    Look up error information from the database.

    Args:
        error_text: Error message text

    Returns:
        Error information dictionary or None if not found
    """
    error_upper = error_text.upper()

    for pattern, info in ERROR_DATABASE.items():
        if pattern in error_upper:
            return {
                "pattern": pattern,
                **info
            }

    return None


def get_errors_by_category(category: str) -> list[dict]:
    """
    Get all errors of a specific category.

    Args:
        category: Error category (convergence, contact, element, material, stability, singularity)

    Returns:
        List of error information dictionaries
    """
    return [
        {"pattern": pattern, **info}
        for pattern, info in ERROR_DATABASE.items()
        if info["category"] == category
    ]
