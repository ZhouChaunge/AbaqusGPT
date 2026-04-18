"""Mesh analysis API endpoints."""

from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

from abaqusgpt.agents.mesh_advisor import MeshAdvisor

router = APIRouter()


class MeshQualityMetrics(BaseModel):
    """Mesh quality metrics."""
    total_elements: int
    total_nodes: int
    element_types: list[str]
    quality_distribution: dict
    problem_elements: int


class MeshAnalysisResponse(BaseModel):
    """Response model for mesh analysis."""
    metrics: MeshQualityMetrics
    analysis: str
    recommendations: list[str]
    warnings: list[str]


class MeshTextRequest(BaseModel):
    """Request for analyzing mesh from text."""
    inp_content: str


@router.post("/analyze", response_model=MeshAnalysisResponse)
async def analyze_mesh(
    file: UploadFile = File(...),
    detailed: bool = Query(False, description="Include detailed element-by-element analysis"),
):
    """
    Analyze mesh quality from .inp file.

    Returns quality metrics and optimization suggestions.
    """
    suffix = Path(file.filename).suffix.lower()
    if suffix != ".inp":
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {suffix}. Only .inp files are supported."
        )

    with NamedTemporaryFile(delete=False, suffix=".inp") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        advisor = MeshAdvisor()
        result = advisor.analyze(tmp_path)

        return MeshAnalysisResponse(
            metrics=MeshQualityMetrics(
                total_elements=0,
                total_nodes=0,
                element_types=[],
                quality_distribution={"good": 0, "warning": 0, "bad": 0},
                problem_elements=0,
            ),
            analysis=result,
            recommendations=[],
            warnings=[],
        )
    finally:
        tmp_path.unlink(missing_ok=True)


@router.post("/recommend-element")
async def recommend_element(
    dimension: str = Query(..., description="solid, shell, or beam"),
    analysis_type: str = Query("general", description="general, stress, impact, thermal"),
    large_deformation: bool = Query(False),
    contact: bool = Query(False),
):
    """
    Recommend suitable element types based on analysis requirements.
    """
    from abaqusgpt.knowledge.element_library import recommend_element

    recommendations = recommend_element(
        dimension=dimension,
        analysis_type=analysis_type,
        large_deformation=large_deformation,
        contact=contact,
    )

    return {
        "recommendations": recommendations,
        "criteria": {
            "dimension": dimension,
            "analysis_type": analysis_type,
            "large_deformation": large_deformation,
            "contact": contact,
        }
    }


@router.get("/element-info/{element_type}")
async def get_element_info(element_type: str):
    """
    Get detailed information about an element type.
    """
    from abaqusgpt.knowledge.element_library import get_element_info

    info = get_element_info(element_type)
    if not info:
        raise HTTPException(status_code=404, detail=f"Element type '{element_type}' not found")

    return info
