"""LLM Provider & API Key management with encrypted Redis storage."""

import json
import uuid
import os
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import redis.asyncio as redis

from ...core.config import settings

try:
    from cryptography.fernet import Fernet
except ImportError:
    Fernet = None  # type: ignore

router = APIRouter()

# Redis connection pool (shared with conversations module)
_redis_pool: Optional[redis.Redis] = None
PROVIDER_PREFIX = "provider:"
PROVIDER_LIST_KEY = "providers"

# Encryption key from environment
_fernet: Optional[object] = None


def _get_fernet():
    """Get or create Fernet cipher for API key encryption."""
    global _fernet
    if _fernet is not None:
        return _fernet
    if Fernet is None:
        return None
    key = os.environ.get("ENCRYPTION_KEY", "")
    if not key:
        # Auto-generate and warn — production should set this explicitly
        key = Fernet.generate_key().decode()
        os.environ["ENCRYPTION_KEY"] = key
    try:
        _fernet = Fernet(key.encode() if isinstance(key, str) else key)
    except Exception:
        _fernet = None
    return _fernet


def _encrypt(value: str) -> str:
    """Encrypt a string value."""
    f = _get_fernet()
    if f is None:
        return value  # Fallback: no encryption
    return f.encrypt(value.encode()).decode()


def _decrypt(value: str) -> str:
    """Decrypt a string value."""
    f = _get_fernet()
    if f is None:
        return value
    try:
        return f.decrypt(value.encode()).decode()
    except Exception:
        return value  # Return as-is if decryption fails


def _mask_key(key: str) -> str:
    """Mask API key, showing only last 4 characters."""
    if len(key) <= 8:
        return "****"
    return f"{key[:3]}****...{key[-4:]}"


async def get_redis() -> redis.Redis:
    """Get or create Redis connection."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )
    return _redis_pool


# Provider catalog — defines all supported providers and their models
PROVIDER_CATALOG = {
    "openai": {
        "name": "OpenAI",
        "group": "international",
        "models": ["gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"],
        "key_prefix": "sk-",
        "env_var": "OPENAI_API_KEY",
    },
    "anthropic": {
        "name": "Anthropic",
        "group": "international",
        "models": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"],
        "key_prefix": "sk-ant-",
        "env_var": "ANTHROPIC_API_KEY",
    },
    "zhipu": {
        "name": "智谱 GLM",
        "group": "chinese",
        "models": ["glm-4", "glm-4v", "glm-3-turbo"],
        "key_prefix": "",
        "env_var": "ZHIPU_API_KEY",
    },
    "dashscope": {
        "name": "通义千问 Qwen",
        "group": "chinese",
        "models": ["qwen-max", "qwen-plus", "qwen-turbo"],
        "key_prefix": "sk-",
        "env_var": "DASHSCOPE_API_KEY",
    },
    "deepseek": {
        "name": "DeepSeek",
        "group": "chinese",
        "models": ["deepseek-chat", "deepseek-coder"],
        "key_prefix": "sk-",
        "env_var": "DEEPSEEK_API_KEY",
    },
    "baidu": {
        "name": "百度文心 ERNIE",
        "group": "chinese",
        "models": ["ernie-4.0", "ernie-3.5-turbo"],
        "key_prefix": "",
        "env_var": "BAIDU_API_KEY",
    },
    "moonshot": {
        "name": "月之暗面 Kimi",
        "group": "chinese",
        "models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
        "key_prefix": "sk-",
        "env_var": "MOONSHOT_API_KEY",
    },
    "yi": {
        "name": "零一万物 Yi",
        "group": "chinese",
        "models": ["yi-large", "yi-medium", "yi-spark"],
        "key_prefix": "",
        "env_var": "YI_API_KEY",
    },
    "baichuan": {
        "name": "百川 Baichuan",
        "group": "chinese",
        "models": ["baichuan4", "baichuan3-turbo"],
        "key_prefix": "",
        "env_var": "BAICHUAN_API_KEY",
    },
    "stepfun": {
        "name": "阶跃星辰 Step",
        "group": "chinese",
        "models": ["step-1-8k", "step-1-32k"],
        "key_prefix": "",
        "env_var": "STEPFUN_API_KEY",
    },
    "minimax": {
        "name": "MiniMax",
        "group": "chinese",
        "models": ["abab6.5-chat", "abab5.5-chat"],
        "key_prefix": "",
        "env_var": "MINIMAX_API_KEY",
    },
    "siliconflow": {
        "name": "硅基流动 SiliconFlow",
        "group": "chinese",
        "models": ["siliconflow-deepseek", "siliconflow-qwen"],
        "key_prefix": "sk-",
        "env_var": "SILICONFLOW_API_KEY",
    },
    "ollama": {
        "name": "Ollama (本地)",
        "group": "local",
        "models": ["ollama-llama3", "ollama-qwen2", "ollama-codellama"],
        "key_prefix": "",
        "env_var": "",
    },
}


# ---------- Pydantic models ----------

class ProviderKeyCreate(BaseModel):
    """Request to add an API key for a provider."""
    provider: str = Field(..., description="Provider ID, e.g. 'openai'")
    api_key: str = Field(..., min_length=1, description="API key value")
    label: Optional[str] = Field(None, description="Optional label for this key")


class ProviderKeyUpdate(BaseModel):
    """Request to update a provider key."""
    api_key: Optional[str] = None
    label: Optional[str] = None


class ProviderKeyInfo(BaseModel):
    """Provider key info (masked)."""
    id: str
    provider: str
    provider_name: str
    group: str
    masked_key: str
    label: str
    is_active: bool
    test_status: Optional[str] = None
    test_latency_ms: Optional[int] = None
    created_at: str


class ProviderCatalogItem(BaseModel):
    """Provider catalog entry."""
    id: str
    name: str
    group: str
    models: List[str]
    configured: bool
    key_count: int


class TestResult(BaseModel):
    """Connectivity test result."""
    status: str  # "ok" | "error"
    latency_ms: Optional[int] = None
    message: Optional[str] = None


# ---------- Endpoints ----------

@router.get("/catalog", response_model=List[ProviderCatalogItem])
async def list_provider_catalog():
    """List all supported providers with configuration status."""
    r = await get_redis()
    key_ids = await r.lrange(PROVIDER_LIST_KEY, 0, -1)

    # Count keys per provider
    provider_key_counts: dict[str, int] = {}
    if key_ids:
        keys = [f"{PROVIDER_PREFIX}{kid}" for kid in key_ids]
        raw_data = await r.mget(keys)
        for data in raw_data:
            if data:
                info = json.loads(data)
                p = info.get("provider", "")
                provider_key_counts[p] = provider_key_counts.get(p, 0) + 1

    result = []
    for pid, pinfo in PROVIDER_CATALOG.items():
        count = provider_key_counts.get(pid, 0)
        result.append(ProviderCatalogItem(
            id=pid,
            name=pinfo["name"],
            group=pinfo["group"],
            models=pinfo["models"],
            configured=count > 0,
            key_count=count,
        ))
    return result


@router.get("/keys", response_model=List[ProviderKeyInfo])
async def list_keys():
    """List all configured API keys (masked)."""
    r = await get_redis()
    key_ids = await r.lrange(PROVIDER_LIST_KEY, 0, -1)
    if not key_ids:
        return []

    keys = [f"{PROVIDER_PREFIX}{kid}" for kid in key_ids]
    raw_data = await r.mget(keys)

    result = []
    for data in raw_data:
        if data:
            info = json.loads(data)
            decrypted = _decrypt(info["api_key"])
            pinfo = PROVIDER_CATALOG.get(info["provider"], {})
            result.append(ProviderKeyInfo(
                id=info["id"],
                provider=info["provider"],
                provider_name=pinfo.get("name", info["provider"]),
                group=pinfo.get("group", "other"),
                masked_key=_mask_key(decrypted),
                label=info.get("label", ""),
                is_active=info.get("is_active", True),
                test_status=info.get("test_status"),
                test_latency_ms=info.get("test_latency_ms"),
                created_at=info["created_at"],
            ))
    return result


@router.post("/keys", response_model=ProviderKeyInfo, status_code=201)
async def add_key(req: ProviderKeyCreate):
    """Add a new API key for a provider."""
    if req.provider not in PROVIDER_CATALOG:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {req.provider}")

    r = await get_redis()
    key_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    record = {
        "id": key_id,
        "provider": req.provider,
        "api_key": _encrypt(req.api_key),
        "label": req.label or "",
        "is_active": True,
        "test_status": None,
        "test_latency_ms": None,
        "created_at": now,
    }

    await r.set(f"{PROVIDER_PREFIX}{key_id}", json.dumps(record, ensure_ascii=False))
    await r.lpush(PROVIDER_LIST_KEY, key_id)

    # Also set in environment so LiteLLM can use it immediately
    pinfo = PROVIDER_CATALOG[req.provider]
    if pinfo.get("env_var"):
        os.environ[pinfo["env_var"]] = req.api_key

    return ProviderKeyInfo(
        id=key_id,
        provider=req.provider,
        provider_name=pinfo["name"],
        group=pinfo["group"],
        masked_key=_mask_key(req.api_key),
        label=req.label or "",
        is_active=True,
        created_at=now,
    )


@router.delete("/keys/{key_id}", status_code=204)
async def delete_key(key_id: str):
    """Delete an API key."""
    r = await get_redis()
    deleted = await r.delete(f"{PROVIDER_PREFIX}{key_id}")
    if not deleted:
        raise HTTPException(status_code=404, detail="Key not found")
    await r.lrem(PROVIDER_LIST_KEY, 0, key_id)
    return None


@router.post("/keys/{key_id}/test", response_model=TestResult)
async def test_key(key_id: str):
    """Test connectivity for a specific API key."""
    r = await get_redis()
    data = await r.get(f"{PROVIDER_PREFIX}{key_id}")
    if not data:
        raise HTTPException(status_code=404, detail="Key not found")

    info = json.loads(data)
    decrypted_key = _decrypt(info["api_key"])
    provider = info["provider"]
    pinfo = PROVIDER_CATALOG.get(provider, {})

    # For Ollama, test differently
    if provider == "ollama":
        import httpx
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
                if resp.status_code == 200:
                    result = TestResult(status="ok", latency_ms=int(resp.elapsed.total_seconds() * 1000))
                else:
                    result = TestResult(status="error", message=f"HTTP {resp.status_code}")
        except Exception as e:
            result = TestResult(status="error", message=str(e))
    else:
        # Use LiteLLM for a minimal completion test
        import litellm
        import time

        models = pinfo.get("models", [])
        test_model = models[0] if models else provider

        # Map model name through LiteLLM mapping
        from abaqusgpt.llm.client import MODEL_MAPPING
        litellm_model = MODEL_MAPPING.get(test_model, test_model)

        # Set the key in env temporarily
        env_var = pinfo.get("env_var", "")
        old_val = os.environ.get(env_var, "")
        if env_var:
            os.environ[env_var] = decrypted_key

        try:
            start = time.monotonic()
            await litellm.acompletion(
                model=litellm_model,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=5,
            )
            elapsed = int((time.monotonic() - start) * 1000)
            result = TestResult(status="ok", latency_ms=elapsed)
        except Exception as e:
            result = TestResult(status="error", message=str(e)[:200])
        finally:
            if env_var:
                if old_val:
                    os.environ[env_var] = old_val
                else:
                    os.environ.pop(env_var, None)

    # Save test result to Redis
    info["test_status"] = result.status
    info["test_latency_ms"] = result.latency_ms
    await r.set(f"{PROVIDER_PREFIX}{key_id}", json.dumps(info, ensure_ascii=False))

    return result
