"""Knowledge base API endpoints."""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from abaqusgpt.knowledge.error_codes import ERROR_DATABASE, get_error_info, get_errors_by_category
from abaqusgpt.knowledge.element_library import ELEMENT_LIBRARY

router = APIRouter()


# Category name mappings
CATEGORY_NAMES = {
    "convergence": "收敛错误",
    "stability": "稳定性问题",
    "element": "单元错误",
    "singularity": "奇异性问题",
    "contact": "接触问题",
    "material": "材料问题",
    "boundary": "边界条件问题",
    "solver": "求解器问题",
    "output": "输出问题",
}


class ErrorInfoFrontend(BaseModel):
    """Error information model for frontend."""
    code: str
    name: str
    description: str
    causes: List[str]
    solutions: List[str]


class ErrorListResponse(BaseModel):
    """Response model for error list."""
    errors: List[ErrorInfoFrontend]


class ElementInfoFrontend(BaseModel):
    """Element information model for frontend."""
    name: str
    type: str
    description: str
    nodes: int
    integration_points: int
    applications: List[str]
    tips: List[str]


class ElementListResponse(BaseModel):
    """Response model for element list."""
    elements: List[ElementInfoFrontend]


class SearchResult(BaseModel):
    """Search result model."""
    type: str  # error, element, material, etc.
    title: str
    content: str
    relevance: float


@router.get("/errors", response_model=ErrorListResponse)
async def list_errors(
    category: Optional[str] = Query(None, description="Filter by category"),
):
    """
    List known Abaqus error codes and solutions.
    
    Categories:
    - convergence: 收敛问题
    - contact: 接触问题
    - element: 单元问题
    - material: 材料问题
    - stability: 稳定性问题
    - singularity: 奇异性问题
    """
    if category:
        raw_errors = get_errors_by_category(category)
    else:
        raw_errors = [{"pattern": k, **v} for k, v in ERROR_DATABASE.items()]
    
    # Transform to frontend format
    errors = []
    for err in raw_errors:
        cat = err.get("category", "unknown")
        errors.append(ErrorInfoFrontend(
            code=err.get("pattern", "UNKNOWN"),
            name=CATEGORY_NAMES.get(cat, cat.title()),
            description=err.get("causes", ["无描述"])[0] if err.get("causes") else "无描述",
            causes=err.get("causes", []),
            solutions=err.get("solutions", []),
        ))
    
    return ErrorListResponse(errors=errors)


@router.get("/errors/{pattern}")
async def get_error(pattern: str):
    """Get information about a specific error pattern."""
    # Search for matching error
    for key, info in ERROR_DATABASE.items():
        if pattern.upper() in key:
            return {"pattern": key, **info}
    
    raise HTTPException(status_code=404, detail=f"Error pattern '{pattern}' not found")


# Integration point counts for common element types
INTEGRATION_POINTS = {
    "full": {"8": 8, "4": 4, "6": 9, "10": 4, "15": 6, "20": 27},
    "reduced": {"8": 1, "4": 1, "6": 2, "10": 1, "15": 1, "20": 8},
}


@router.get("/elements", response_model=ElementListResponse)
async def list_elements(
    dimension: Optional[str] = Query(None, description="Filter by dimension: 3, shell, beam"),
    integration: Optional[str] = Query(None, description="Filter by integration: full, reduced"),
):
    """List available element types."""
    elements = []
    
    for elem_type, info in ELEMENT_LIBRARY.items():
        # Apply filters
        if dimension:
            if str(info.get("dimensions")) != dimension:
                continue
        if integration:
            if info.get("integration") != integration:
                continue
        
        # Calculate integration points
        nodes = info.get("nodes", 0)
        integ_type = info.get("integration", "full")
        integ_points = INTEGRATION_POINTS.get(integ_type, {}).get(str(nodes), nodes)
        
        elements.append(ElementInfoFrontend(
            name=elem_type,
            type=info.get("integration", "full"),
            description=info.get("name_cn", info.get("name", "")),
            nodes=nodes,
            integration_points=integ_points,
            applications=info.get("use_cases", []),
            tips=info.get("warnings", []),
        ))
    
    return ElementListResponse(elements=elements)


@router.get("/search")
async def search_knowledge(
    query: str = Query(..., description="Search query"),
    domain: Optional[str] = Query(None, description="Filter by domain"),
    limit: int = Query(10, description="Maximum results"),
):
    """
    Search across all knowledge bases.
    
    Searches errors, elements, materials, and domain-specific knowledge.
    """
    results = []
    query_upper = query.upper()
    
    # Search errors
    for pattern, info in ERROR_DATABASE.items():
        if query_upper in pattern or any(query.lower() in cause.lower() for cause in info["causes"]):
            results.append(SearchResult(
                type="error",
                title=pattern,
                content="; ".join(info["causes"][:2]),
                relevance=0.9 if query_upper in pattern else 0.7,
            ))
    
    # Search elements
    for name, info in ELEMENT_LIBRARY.items():
        if query_upper in name or query.lower() in info.get("name_cn", "").lower():
            results.append(SearchResult(
                type="element",
                title=name,
                content=info.get("name_cn", info.get("name", "")),
                relevance=0.9 if query_upper in name else 0.7,
            ))
    
    # Sort by relevance and limit
    results.sort(key=lambda x: x.relevance, reverse=True)
    return results[:limit]


@router.get("/domain/{domain}")
async def get_domain_knowledge(
    domain: str,
    topic: Optional[str] = Query(None, description="Specific topic within domain"),
):
    """
    Get domain-specific knowledge.
    
    Domains: geotechnical, structural, mechanical, thermal, impact, composite, biomechanics, electromagnetic
    """
    domain_info = {
        "geotechnical": {
            "name": "岩土工程",
            "content": """# 岩土工程分析指南

## 常用本构模型
- **Mohr-Coulomb**: 经典强度准则，适用于土体和岩石
- **Drucker-Prager**: 适用于岩土材料的塑性分析
- **Cam-Clay (Modified)**: 适用于正常固结粘土
- **Cap Plasticity**: 考虑体积屈服的模型

## 推荐单元
- C3D8R: 通用三维实体单元
- C3D4: 四面体单元，适合复杂几何
- C3D10M: 二次四面体，精度更高

## 关键注意事项
1. 初始地应力平衡（*GEOSTATIC）
2. 孔隙水压力与有效应力
3. 开挖步骤的模拟
4. 接触面摩擦设置
""",
        },
        "structural": {
            "name": "结构工程",
            "content": """# 结构工程分析指南

## 常用材料模型
- **混凝土损伤塑性 (CDP)**: 适用于混凝土结构
- **钢材塑性**: 考虑硬化和软化行为
- **钢筋混凝土**: 使用嵌入式单元 (*EMBEDDED)

## 推荐单元
- C3D8R: 三维实体
- S4R: 壳单元
- B31: 梁单元
- T3D2: 桁架单元

## 关键注意事项
1. 几何非线性 (NLGEOM=YES)
2. 损伤演化与开裂
3. 钢筋与混凝土的粘结
4. 地震荷载时程分析
""",
        },
        "mechanical": {
            "name": "机械工程",
            "content": """# 机械工程分析指南

## 常用分析类型
- 静力分析
- 动力学分析
- 接触分析
- 疲劳分析

## 推荐单元
- C3D8R: 通用三维实体
- C3D20R: 二次六面体，高精度
- C3D10M: 改进的四面体单元

## 关键注意事项
1. 接触对设置（主从面选择）
2. 网格细化策略
3. 载荷历程定义
4. 结果收敛性检查
""",
        },
        "thermal": {
            "name": "热分析",
            "content": """# 热分析指南

## 分析类型
- 稳态热传导
- 瞬态热传导
- 热-结构耦合

## 推荐单元
- DC3D8: 热传导六面体
- DC3D4: 热传导四面体
- C3D8T: 热-结构耦合单元

## 关键注意事项
1. 边界条件：对流、辐射
2. 材料热物性随温度变化
3. 时间步控制
4. 初始温度场
""",
        },
        "impact": {
            "name": "冲击分析",
            "content": """# 冲击分析指南

## 分析方法
- Abaqus/Explicit 显式动力学
- 高应变率材料模型

## 常用材料模型
- Johnson-Cook: 考虑应变率效应
- Cowper-Symonds: 应变率强化

## 关键注意事项
1. 质量缩放 (Mass Scaling)
2. 沙漏控制
3. 时间步稳定性
4. 单元删除准则
""",
        },
        "composite": {
            "name": "复合材料",
            "content": """# 复合材料分析指南

## 分析方法
- 传统层合板理论
- 渐进损伤分析

## 推荐单元
- S4R/S8R: 壳单元
- SC8R: 连续壳单元
- C3D8R: 实体单元（厚度方向细化）

## 关键注意事项
1. 铺层顺序定义
2. 失效准则（Hashin, Tsai-Wu）
3. 分层失效模拟
4. 材料方向定义
""",
        },
        "biomechanics": {
            "name": "生物力学",
            "content": """# 生物力学分析指南

## 常用材料模型
- 超弹性 (Hyperelastic): 软组织
- 粘弹性 (Viscoelastic): 时间依赖行为
- 各向异性材料

## 推荐单元
- C3D10M: 四面体（复杂几何）
- C3D8RH: 混合公式（近似不可压缩）

## 关键注意事项
1. 材料不可压缩性处理
2. 大变形分析
3. 接触模拟（关节、植入物）
4. CT/MRI数据导入
""",
        },
        "electromagnetic": {
            "name": "电磁分析",
            "content": """# 电磁分析指南

## 分析类型
- 静电分析
- 稳态电流
- 电磁感应

## 推荐单元
- DC3D8E: 电传导单元
- EMC3D8: 电磁单元

## 关键注意事项
1. 材料电磁属性
2. 边界条件设置
3. 多物理场耦合
4. 网格要求
""",
        },
    }
    
    if domain not in domain_info:
        raise HTTPException(status_code=404, detail=f"Domain '{domain}' not found")
    
    return domain_info[domain]
