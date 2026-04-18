"""Convergence diagnosis API endpoints."""

from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

from abaqusgpt.agents.converge_doctor import ConvergeDoctor

router = APIRouter()


class DiagnoseResponse(BaseModel):
    """Response model for diagnosis."""
    status: str
    errors: list[str]
    warnings: list[str]
    last_step: Optional[int]
    last_increment: Optional[int]
    diagnosis: str
    suggestions: list[str]


class DiagnoseTextRequest(BaseModel):
    """Request model for text-based diagnosis."""
    content: str
    file_type: str = "msg"  # msg, sta, dat


@router.post("/file", response_model=DiagnoseResponse)
async def diagnose_file(
    file: UploadFile = File(...),
    verbose: bool = Query(False, description="Include detailed output"),
    domain: Optional[str] = Query(None, description="Engineering domain for context"),
):
    """
    Diagnose convergence issues from uploaded file.

    Supports: .msg, .sta, .dat files
    """
    # Validate file extension
    suffix = Path(file.filename).suffix.lower()
    if suffix not in [".msg", ".sta", ".dat"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {suffix}. Supported: .msg, .sta, .dat"
        )

    # Save to temp file
    with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        doctor = ConvergeDoctor()
        result = doctor.diagnose(tmp_path, verbose=verbose)

        # Parse result into structured response
        return DiagnoseResponse(
            status="error" if "错误" in result or "失败" in result else "warning",
            errors=[],  # Would be extracted from parsed data
            warnings=[],
            last_step=None,
            last_increment=None,
            diagnosis=result,
            suggestions=[],
        )
    finally:
        # Cleanup temp file
        tmp_path.unlink(missing_ok=True)


@router.post("/text", response_model=DiagnoseResponse)
async def diagnose_text(request: DiagnoseTextRequest):
    """
    Diagnose from pasted text content.

    Useful for quick diagnosis without file upload.
    """
    # Create temp file with content
    suffix = f".{request.file_type}"
    with NamedTemporaryFile(delete=False, suffix=suffix, mode="w") as tmp:
        tmp.write(request.content)
        tmp_path = Path(tmp.name)

    try:
        doctor = ConvergeDoctor()
        result = doctor.diagnose(tmp_path, verbose=False)

        return DiagnoseResponse(
            status="error" if "错误" in result or "失败" in result else "warning",
            errors=[],
            warnings=[],
            last_step=None,
            last_increment=None,
            diagnosis=result,
            suggestions=[],
        )
    finally:
        tmp_path.unlink(missing_ok=True)
