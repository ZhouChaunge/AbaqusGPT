"""Conversation history API endpoints with Redis persistence."""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import redis.asyncio as redis

from ...core.config import settings

router = APIRouter()

# Redis connection pool
_redis_pool: Optional[redis.Redis] = None

CONV_PREFIX = "conv:"
CONV_LIST_KEY = "conversations"


async def get_redis() -> redis.Redis:
    """Get or create Redis connection."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )
    return _redis_pool


class MessageItem(BaseModel):
    """A single message in a conversation."""
    id: str
    role: str
    content: str
    timestamp: str


class ConversationCreate(BaseModel):
    """Request to create a conversation."""
    title: Optional[str] = None
    domain: str = "general"
    messages: Optional[List[MessageItem]] = None


class ConversationUpdate(BaseModel):
    """Request to update a conversation."""
    title: Optional[str] = None
    domain: Optional[str] = None
    messages: Optional[List[MessageItem]] = None


class ConversationSummary(BaseModel):
    """Summary of a conversation for list view."""
    id: str
    title: str
    domain: str
    message_count: int
    created_at: str
    updated_at: str


class ConversationDetail(BaseModel):
    """Full conversation with messages."""
    id: str
    title: str
    domain: str
    messages: List[MessageItem]
    created_at: str
    updated_at: str


@router.get("/", response_model=List[ConversationSummary])
async def list_conversations():
    """List all conversations, newest first."""
    r = await get_redis()
    conv_ids = await r.lrange(CONV_LIST_KEY, 0, -1)
    if not conv_ids:
        return []

    keys = [f"{CONV_PREFIX}{cid}" for cid in conv_ids]
    raw_data = await r.mget(keys)

    conversations = []
    for data in raw_data:
        if data:
            conv = json.loads(data)
            conversations.append(ConversationSummary(
                id=conv["id"],
                title=conv["title"],
                domain=conv["domain"],
                message_count=len(conv.get("messages", [])),
                created_at=conv["created_at"],
                updated_at=conv["updated_at"],
            ))

    return conversations


@router.post("/", response_model=ConversationDetail, status_code=201)
async def create_conversation(req: ConversationCreate):
    """Create a new conversation."""
    r = await get_redis()
    conv_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    conv = {
        "id": conv_id,
        "title": req.title or "新对话",
        "domain": req.domain,
        "messages": [m.model_dump() for m in req.messages] if req.messages else [],
        "created_at": now,
        "updated_at": now,
    }

    await r.set(f"{CONV_PREFIX}{conv_id}", json.dumps(conv, ensure_ascii=False))
    await r.lpush(CONV_LIST_KEY, conv_id)

    return ConversationDetail(**conv)


@router.get("/{conv_id}", response_model=ConversationDetail)
async def get_conversation(conv_id: str):
    """Get a conversation by ID."""
    r = await get_redis()
    data = await r.get(f"{CONV_PREFIX}{conv_id}")
    if not data:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conv = json.loads(data)
    return ConversationDetail(**conv)


@router.put("/{conv_id}", response_model=ConversationDetail)
async def update_conversation(conv_id: str, req: ConversationUpdate):
    """Update a conversation (title, domain, or messages)."""
    r = await get_redis()
    data = await r.get(f"{CONV_PREFIX}{conv_id}")
    if not data:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conv = json.loads(data)

    if req.title is not None:
        conv["title"] = req.title
    if req.domain is not None:
        conv["domain"] = req.domain
    if req.messages is not None:
        conv["messages"] = [m.model_dump() for m in req.messages]

    conv["updated_at"] = datetime.now(timezone.utc).isoformat()

    await r.set(f"{CONV_PREFIX}{conv_id}", json.dumps(conv, ensure_ascii=False))

    return ConversationDetail(**conv)


@router.delete("/{conv_id}", status_code=204)
async def delete_conversation(conv_id: str):
    """Delete a conversation."""
    r = await get_redis()
    deleted = await r.delete(f"{CONV_PREFIX}{conv_id}")
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await r.lrem(CONV_LIST_KEY, 0, conv_id)
    return None
