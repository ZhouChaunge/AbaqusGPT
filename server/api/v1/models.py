"""Models API — list available models and manage active model selection."""

import json
from typing import Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import redis.asyncio as redis

from ...core.config import settings

router = APIRouter()

_redis_pool: Optional[redis.Redis] = None
ACTIVE_MODEL_KEY = "active_model"


async def get_redis() -> redis.Redis:
    """Get or create Redis connection."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )
    return _redis_pool


# Import provider catalog from providers module
from .providers import PROVIDER_CATALOG, get_redis as providers_get_redis


class ModelInfo(BaseModel):
    """Model information."""
    id: str
    name: str
    provider: str
    provider_name: str
    group: str
    configured: bool = True


class ModelListResponse(BaseModel):
    """Response for model list."""
    models: List[ModelInfo]
    active_model: str


class ActiveModelRequest(BaseModel):
    """Request to set active model."""
    model: str


@router.get("/", response_model=ModelListResponse)
async def list_models():
    """List all available models from configured providers."""
    r = await get_redis()

    # Get configured providers (those with at least one key)
    from .providers import PROVIDER_LIST_KEY, PROVIDER_PREFIX
    key_ids = await r.lrange(PROVIDER_LIST_KEY, 0, -1)

    configured_providers: set[str] = set()
    if key_ids:
        keys = [f"{PROVIDER_PREFIX}{kid}" for kid in key_ids]
        raw_data = await r.mget(keys)
        for data in raw_data:
            if data:
                info = json.loads(data)
                configured_providers.add(info["provider"])

    # Always include ollama (no key needed)
    configured_providers.add("ollama")

    # Build model list from ALL providers, marking configured status
    models: List[ModelInfo] = []
    for pid, pinfo in PROVIDER_CATALOG.items():
        is_configured = pid in configured_providers
        for model_id in pinfo["models"]:
            models.append(ModelInfo(
                id=model_id,
                name=model_id,
                provider=pid,
                provider_name=pinfo["name"],
                group=pinfo["group"],
                configured=is_configured,
            ))

    # Get active model
    active = await r.get(ACTIVE_MODEL_KEY)
    if not active:
        active = settings.DEFAULT_MODEL

    return ModelListResponse(models=models, active_model=active)


@router.put("/active")
async def set_active_model(req: ActiveModelRequest):
    """Set the currently active model."""
    # Validate model exists in configured providers
    all_models = set()
    for pinfo in PROVIDER_CATALOG.values():
        for m in pinfo["models"]:
            all_models.add(m)
    if req.model not in all_models:
        raise HTTPException(status_code=400, detail=f"Unknown model: {req.model}")
    r = await get_redis()
    await r.set(ACTIVE_MODEL_KEY, req.model)
    return {"model": req.model}


@router.get("/active")
async def get_active_model():
    """Get the currently active model."""
    r = await get_redis()
    active = await r.get(ACTIVE_MODEL_KEY)
    if not active:
        active = settings.DEFAULT_MODEL
    return {"model": active}
