"""Abaqus element type library."""

from typing import Optional

ELEMENT_LIBRARY = {
    # 3D Solid Elements - Linear
    "C3D8": {
        "name": "8-node linear brick (full integration)",
        "name_cn": "8节点线性六面体（全积分）",
        "dimensions": 3,
        "nodes": 8,
        "integration": "full",
        "dof_per_node": 3,
        "use_cases": [
            "精确应力分析",
            "不涉及大变形的问题",
            "薄结构较少的模型"
        ],
        "warnings": [
            "全积分可能导致剪切锁死",
            "弯曲主导问题中精度较低",
            "网格较粗时不推荐"
        ],
        "alternatives": ["C3D8R", "C3D8I", "C3D20R"]
    },

    "C3D8R": {
        "name": "8-node linear brick (reduced integration)",
        "name_cn": "8节点线性六面体（减缩积分）",
        "dimensions": 3,
        "nodes": 8,
        "integration": "reduced",
        "dof_per_node": 3,
        "use_cases": [
            "大变形分析",
            "接触问题",
            "塑性分析",
            "一般结构分析"
        ],
        "warnings": [
            "需要沙漏控制",
            "厚度方向至少需要2层单元",
            "不适合弯曲主导问题"
        ],
        "alternatives": ["C3D8", "C3D8I", "C3D20R"]
    },

    "C3D8I": {
        "name": "8-node linear brick (incompatible modes)",
        "name_cn": "8节点线性六面体（非协调模式）",
        "dimensions": 3,
        "nodes": 8,
        "integration": "full",
        "dof_per_node": 3,
        "use_cases": [
            "弯曲问题",
            "薄壁结构",
            "需要较少单元的情况"
        ],
        "warnings": [
            "计算成本高于C3D8R",
            "大变形时可能不稳定",
            "不适合接触分析"
        ],
        "alternatives": ["C3D8R", "C3D20R"]
    },

    # 3D Solid Elements - Quadratic
    "C3D20": {
        "name": "20-node quadratic brick (full integration)",
        "name_cn": "20节点二次六面体（全积分）",
        "dimensions": 3,
        "nodes": 20,
        "integration": "full",
        "dof_per_node": 3,
        "use_cases": [
            "高精度应力分析",
            "弯曲问题",
            "应力集中区域"
        ],
        "warnings": [
            "计算成本高",
            "不推荐用于接触",
            "大变形时可能有问题"
        ],
        "alternatives": ["C3D20R", "C3D10"]
    },

    "C3D20R": {
        "name": "20-node quadratic brick (reduced integration)",
        "name_cn": "20节点二次六面体（减缩积分）",
        "dimensions": 3,
        "nodes": 20,
        "integration": "reduced",
        "dof_per_node": 3,
        "use_cases": [
            "高精度分析",
            "弯曲问题",
            "应力梯度大的区域"
        ],
        "warnings": [
            "计算成本较高",
            "接触分析中可能有问题",
            "需要较规则的网格"
        ],
        "alternatives": ["C3D10M", "C3D8R"]
    },

    "C3D10": {
        "name": "10-node quadratic tetrahedron",
        "name_cn": "10节点二次四面体",
        "dimensions": 3,
        "nodes": 10,
        "integration": "full",
        "dof_per_node": 3,
        "use_cases": [
            "复杂几何自动网格",
            "高精度需求",
            "一般结构分析"
        ],
        "warnings": [
            "比六面体需要更多单元",
            "应力集中处需加密"
        ],
        "alternatives": ["C3D10M", "C3D4"]
    },

    "C3D10M": {
        "name": "10-node modified quadratic tetrahedron",
        "name_cn": "10节点改进二次四面体",
        "dimensions": 3,
        "nodes": 10,
        "integration": "modified",
        "dof_per_node": 3,
        "use_cases": [
            "接触分析",
            "大变形",
            "复杂几何"
        ],
        "warnings": [
            "计算成本高于C3D10",
            "精度略低于C3D10"
        ],
        "alternatives": ["C3D10", "C3D4"]
    },

    "C3D4": {
        "name": "4-node linear tetrahedron",
        "name_cn": "4节点线性四面体",
        "dimensions": 3,
        "nodes": 4,
        "integration": "full",
        "dof_per_node": 3,
        "use_cases": [
            "快速预分析",
            "填充复杂区域"
        ],
        "warnings": [
            "精度很低",
            "过于刚硬",
            "需要非常密的网格",
            "不推荐用于正式分析"
        ],
        "alternatives": ["C3D10", "C3D10M"]
    },

    # Shell Elements
    "S4": {
        "name": "4-node shell (full integration)",
        "name_cn": "4节点壳（全积分）",
        "dimensions": "shell",
        "nodes": 4,
        "integration": "full",
        "dof_per_node": 6,
        "use_cases": [
            "薄壁结构",
            "板件弯曲",
            "精确应力分析"
        ],
        "warnings": [
            "可能出现剪切锁死",
            "扭曲网格时精度下降"
        ],
        "alternatives": ["S4R", "S8R"]
    },

    "S4R": {
        "name": "4-node shell (reduced integration)",
        "name_cn": "4节点壳（减缩积分）",
        "dimensions": "shell",
        "nodes": 4,
        "integration": "reduced",
        "dof_per_node": 6,
        "use_cases": [
            "一般壳分析",
            "大变形",
            "接触问题"
        ],
        "warnings": [
            "需要沙漏控制",
            "厚度/跨度比<1/10"
        ],
        "alternatives": ["S4", "S8R"]
    },

    "S3": {
        "name": "3-node triangular shell",
        "name_cn": "3节点三角形壳",
        "dimensions": "shell",
        "nodes": 3,
        "integration": "full",
        "dof_per_node": 6,
        "use_cases": [
            "过渡区域",
            "复杂曲面"
        ],
        "warnings": [
            "精度较低",
            "仅用于过渡",
            "避免主要分析区域使用"
        ],
        "alternatives": ["S4R", "STRI65"]
    },

    # Beam Elements
    "B31": {
        "name": "2-node linear beam",
        "name_cn": "2节点线性梁",
        "dimensions": "beam",
        "nodes": 2,
        "integration": "1-point",
        "dof_per_node": 6,
        "use_cases": [
            "框架结构",
            "桁架",
            "细长结构"
        ],
        "warnings": [
            "不适合短粗梁",
            "忽略剪切变形"
        ],
        "alternatives": ["B32", "B31OS"]
    },

    "B32": {
        "name": "3-node quadratic beam",
        "name_cn": "3节点二次梁",
        "dimensions": "beam",
        "nodes": 3,
        "integration": "2-point",
        "dof_per_node": 6,
        "use_cases": [
            "曲线梁",
            "需要更高精度",
            "弯曲变形大"
        ],
        "warnings": [
            "计算成本高于B31"
        ],
        "alternatives": ["B31"]
    },

    # Explicit Elements
    "C3D8R (Explicit)": {
        "name": "8-node brick for Explicit",
        "name_cn": "8节点六面体（Explicit）",
        "dimensions": 3,
        "nodes": 8,
        "integration": "reduced",
        "dof_per_node": 3,
        "use_cases": [
            "冲击分析",
            "碰撞模拟",
            "高速变形"
        ],
        "warnings": [
            "沙漏控制非常重要",
            "时间步受最小单元限制"
        ],
        "alternatives": ["C3D10M"]
    },

    # =========================================================================
    # Additional Shell Elements | 补充壳单元
    # =========================================================================

    "S8R": {
        "name": "8-node quadratic shell (reduced integration)",
        "name_cn": "8节点二次壳（减缩积分）",
        "dimensions": "shell",
        "nodes": 8,
        "integration": "reduced",
        "dof_per_node": 6,
        "use_cases": [
            "高精度壳分析",
            "曲面结构",
            "应力集中区域"
        ],
        "warnings": [
            "计算成本高于S4R",
            "网格过渡需注意"
        ],
        "alternatives": ["S4R", "S4"]
    },

    "SC8R": {
        "name": "8-node continuum shell (reduced integration)",
        "name_cn": "8节点连续体壳（减缩积分）",
        "dimensions": "shell",
        "nodes": 8,
        "integration": "reduced",
        "dof_per_node": 3,
        "use_cases": [
            "复合材料层合板",
            "厚度方向应力输出",
            "三维效应壳分析"
        ],
        "warnings": [
            "厚度方向至少需要1个单元",
            "比传统壳单元计算量大"
        ],
        "alternatives": ["S4R", "S8R"]
    },

    "STRI65": {
        "name": "6-node triangular shell (5 integration points)",
        "name_cn": "6节点三角形壳（5积分点）",
        "dimensions": "shell",
        "nodes": 6,
        "integration": "full",
        "dof_per_node": 6,
        "use_cases": [
            "复杂曲面过渡",
            "高精度三角形区域"
        ],
        "warnings": [
            "比S8R计算成本高",
            "尽量使用四边形"
        ],
        "alternatives": ["S8R", "S4R"]
    },

    # =========================================================================
    # Additional Beam Elements | 补充梁单元
    # =========================================================================

    "B31OS": {
        "name": "2-node linear beam (open section)",
        "name_cn": "2节点线性梁（开口截面）",
        "dimensions": "beam",
        "nodes": 2,
        "integration": "1-point",
        "dof_per_node": 7,
        "use_cases": [
            "开口薄壁截面",
            "翘曲约束",
            "工字钢、槽钢"
        ],
        "warnings": [
            "需要定义翘曲自由度",
            "仅用于开口截面"
        ],
        "alternatives": ["B31"]
    },

    "B33": {
        "name": "2-node cubic beam",
        "name_cn": "2节点三次梁",
        "dimensions": "beam",
        "nodes": 2,
        "integration": "3-point",
        "dof_per_node": 6,
        "use_cases": [
            "Euler-Bernoulli梁理论",
            "细长梁",
            "忽略剪切变形"
        ],
        "warnings": [
            "不考虑剪切变形",
            "仅适用于细长梁"
        ],
        "alternatives": ["B31", "B32"]
    },

    "PIPE31": {
        "name": "2-node linear pipe element",
        "name_cn": "2节点线性管单元",
        "dimensions": "beam",
        "nodes": 2,
        "integration": "1-point",
        "dof_per_node": 6,
        "use_cases": [
            "管道系统",
            "圆形截面管",
            "内外压分析"
        ],
        "warnings": [
            "仅适用于圆形截面"
        ],
        "alternatives": ["B31"]
    },

    # =========================================================================
    # Connector Elements | 连接单元
    # =========================================================================

    "CONN3D2": {
        "name": "3D connector element",
        "name_cn": "三维连接器单元",
        "dimensions": "connector",
        "nodes": 2,
        "integration": "none",
        "dof_per_node": 6,
        "use_cases": [
            "弹簧连接",
            "阻尼器",
            "铰接",
            "螺栓连接"
        ],
        "warnings": [
            "需要定义连接器截面属性",
            "运动学约束需仔细设置"
        ],
        "alternatives": ["SPRING", "DASHPOT"],
        "keywords": "*CONNECTOR SECTION, *CONNECTOR BEHAVIOR"
    },

    "CONN2D2": {
        "name": "2D connector element",
        "name_cn": "二维连接器单元",
        "dimensions": "connector",
        "nodes": 2,
        "integration": "none",
        "dof_per_node": 3,
        "use_cases": [
            "平面问题连接",
            "平面弹簧"
        ],
        "warnings": [
            "仅用于二维分析"
        ],
        "alternatives": ["CONN3D2"]
    },

    # =========================================================================
    # Special Elements | 特殊单元
    # =========================================================================

    "MASS": {
        "name": "Point mass element",
        "name_cn": "质点单元",
        "dimensions": "point",
        "nodes": 1,
        "integration": "none",
        "dof_per_node": 3,
        "use_cases": [
            "集中质量",
            "非结构质量",
            "简化配重"
        ],
        "warnings": [
            "无刚度",
            "仅提供惯性"
        ],
        "alternatives": [],
        "keywords": "*MASS"
    },

    "ROTARYI": {
        "name": "Rotary inertia element",
        "name_cn": "转动惯量单元",
        "dimensions": "point",
        "nodes": 1,
        "integration": "none",
        "dof_per_node": 3,
        "use_cases": [
            "转动惯量",
            "旋转机械",
            "动力学分析"
        ],
        "warnings": [
            "需要与参考节点关联",
            "需要定义惯量张量"
        ],
        "alternatives": [],
        "keywords": "*ROTARY INERTIA"
    },

    "SPRING1": {
        "name": "Spring element to ground",
        "name_cn": "接地弹簧单元",
        "dimensions": "point",
        "nodes": 1,
        "integration": "none",
        "dof_per_node": 6,
        "use_cases": [
            "边界弹性约束",
            "弹性地基"
        ],
        "warnings": [
            "仅连接到固定参考"
        ],
        "alternatives": ["SPRING2"]
    },

    "SPRING2": {
        "name": "Spring element between nodes",
        "name_cn": "节点间弹簧单元",
        "dimensions": "spring",
        "nodes": 2,
        "integration": "none",
        "dof_per_node": 6,
        "use_cases": [
            "节点间弹性连接",
            "离散弹簧"
        ],
        "warnings": [
            "注意弹簧方向定义"
        ],
        "alternatives": ["CONN3D2"],
        "keywords": "*SPRING"
    },

    "DASHPOT1": {
        "name": "Dashpot element to ground",
        "name_cn": "接地阻尼器单元",
        "dimensions": "point",
        "nodes": 1,
        "integration": "none",
        "dof_per_node": 6,
        "use_cases": [
            "边界阻尼",
            "耗能边界"
        ],
        "warnings": [
            "仅用于动力学分析"
        ],
        "alternatives": ["DASHPOT2"]
    },

    "DASHPOT2": {
        "name": "Dashpot element between nodes",
        "name_cn": "节点间阻尼器单元",
        "dimensions": "dashpot",
        "nodes": 2,
        "integration": "none",
        "dof_per_node": 6,
        "use_cases": [
            "节点间阻尼",
            "结构阻尼"
        ],
        "warnings": [
            "仅用于动力学分析"
        ],
        "alternatives": ["CONN3D2"],
        "keywords": "*DASHPOT"
    },

    # =========================================================================
    # Cohesive Elements | 内聚单元
    # =========================================================================

    "COH3D8": {
        "name": "8-node 3D cohesive element",
        "name_cn": "8节点三维内聚单元",
        "dimensions": "cohesive",
        "nodes": 8,
        "integration": "full",
        "dof_per_node": 3,
        "use_cases": [
            "界面分层",
            "裂纹扩展",
            "复合材料分层"
        ],
        "warnings": [
            "需要定义损伤起始和演化",
            "网格需与主体一致"
        ],
        "alternatives": ["COH3D6"],
        "keywords": "*COHESIVE SECTION, *DAMAGE INITIATION, *DAMAGE EVOLUTION"
    },

    "COH3D6": {
        "name": "6-node 3D cohesive element",
        "name_cn": "6节点三维内聚单元",
        "dimensions": "cohesive",
        "nodes": 6,
        "integration": "full",
        "dof_per_node": 3,
        "use_cases": [
            "三角形区域分层",
            "过渡区域内聚"
        ],
        "warnings": [
            "精度低于COH3D8"
        ],
        "alternatives": ["COH3D8"]
    },

    # =========================================================================
    # Thermal Elements | 热单元
    # =========================================================================

    "DC3D8": {
        "name": "8-node linear heat transfer brick",
        "name_cn": "8节点线性传热六面体",
        "dimensions": 3,
        "nodes": 8,
        "integration": "full",
        "dof_per_node": 1,
        "use_cases": [
            "稳态传热",
            "瞬态传热"
        ],
        "warnings": [
            "仅温度自由度",
            "需耦合用于热-结构分析"
        ],
        "alternatives": ["DC3D20"]
    },

    "DC3D20": {
        "name": "20-node quadratic heat transfer brick",
        "name_cn": "20节点二次传热六面体",
        "dimensions": 3,
        "nodes": 20,
        "integration": "full",
        "dof_per_node": 1,
        "use_cases": [
            "高精度传热",
            "温度梯度大的区域"
        ],
        "warnings": [
            "计算成本高"
        ],
        "alternatives": ["DC3D8"]
    },
}


def get_element_info(element_type: str) -> Optional[dict]:
    """
    Get information about an element type.

    Args:
        element_type: Element type name (e.g., 'C3D8R')

    Returns:
        Element information dictionary or None if not found
    """
    return ELEMENT_LIBRARY.get(element_type.upper())


def recommend_element(
    dimension: str,
    analysis_type: str = "general",
    large_deformation: bool = False,
    contact: bool = False
) -> list[str]:
    """
    Recommend suitable element types based on analysis requirements.

    Args:
        dimension: 'solid', 'shell', or 'beam'
        analysis_type: 'general', 'stress', 'impact'
        large_deformation: Whether large deformation is expected
        contact: Whether contact is involved

    Returns:
        List of recommended element types
    """
    recommendations = []

    if dimension == "solid":
        if contact or large_deformation:
            recommendations = ["C3D8R", "C3D10M"]
        elif analysis_type == "stress":
            recommendations = ["C3D20R", "C3D10"]
        else:
            recommendations = ["C3D8R", "C3D8I"]

    elif dimension == "shell":
        if large_deformation or contact:
            recommendations = ["S4R"]
        else:
            recommendations = ["S4R", "S4"]

    elif dimension == "beam":
        recommendations = ["B31", "B32"]

    return recommendations
