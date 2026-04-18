"""Model generation API endpoints."""

from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from abaqusgpt.agents.inp_generator import InpGenerator

router = APIRouter()


class GenerateRequest(BaseModel):
    """Request model for code generation."""
    description: str = Field(..., description="Natural language description of the model")
    format: Literal["inp", "python"] = Field("inp", description="Output format")
    domain: Optional[str] = Field(None, description="Engineering domain for context")

    class Config:
        json_schema_extra = {
            "example": {
                "description": "创建一个20x10x5mm的钢板，底部固定，顶面施加10MPa压力",
                "format": "inp",
                "domain": "mechanical"
            }
        }


class GenerateResponse(BaseModel):
    """Response model for generated code."""
    code: str
    format: str
    warnings: list[str] = []
    metadata: dict = {}


@router.post("/", response_model=GenerateResponse)
async def generate_model(request: GenerateRequest):
    """
    Generate Abaqus input file or Python script from natural language.

    Supports:
    - inp: Abaqus input file format
    - python: Abaqus Python scripting
    """
    try:
        generator = InpGenerator()
        code = generator.generate(request.description, format=request.format)

        return GenerateResponse(
            code=code,
            format=request.format,
            warnings=[],
            metadata={
                "domain": request.domain,
                "description": request.description,
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class TemplateRequest(BaseModel):
    """Request for predefined templates."""
    template_name: str
    parameters: dict = {}


@router.post("/template", response_model=GenerateResponse)
async def generate_from_template(request: TemplateRequest):
    """
    Generate from predefined template with parameters.

    Templates include:
    - simple_beam: 简支梁
    - plate_bending: 板弯曲
    - contact_pair: 接触对
    - thermal_stress: 热应力
    """
    # TODO: Implement template system
    raise HTTPException(status_code=501, detail="Template system not yet implemented")


@router.get("/templates")
async def list_templates():
    """List available templates."""
    return {
        "templates": [
            {
                "name": "simple_beam",
                "description": "简支梁模型",
                "parameters": ["length", "width", "height", "material"],
            },
            {
                "name": "plate_bending",
                "description": "板弯曲模型",
                "parameters": ["size", "thickness", "load", "material"],
            },
            {
                "name": "contact_pair",
                "description": "接触对模型",
                "parameters": ["geometry", "friction", "contact_type"],
            },
        ]
    }
