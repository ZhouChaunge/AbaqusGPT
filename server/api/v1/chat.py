"""Chat API endpoints with streaming support."""

import asyncio
from typing import Optional, List, Literal
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import json

from abaqusgpt.agents.qa_agent import QAAgent
from abaqusgpt.agents.domain_expert import DomainExpert

router = APIRouter()


class Message(BaseModel):
    """Chat message."""
    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    """Request model for chat."""
    message: str = Field(..., description="User message")
    domain: Optional[str] = Field(None, description="Engineering domain")
    model: Optional[str] = Field(None, description="LLM model to use")
    history: List[Message] = Field(default_factory=list, description="Conversation history")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "C3D8R和C3D8有什么区别？",
                "domain": "mechanical",
                "history": []
            }
        }


class ChatResponse(BaseModel):
    """Response model for chat."""
    response: str
    domain: Optional[str]
    sources: List[str] = []


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with AbaqusGPT.
    
    Optionally specify a domain for specialized responses:
    - geotechnical: 岩土工程
    - structural: 结构工程
    - mechanical: 机械工程
    - thermal: 热分析
    - impact: 冲击动力学
    - composite: 复合材料
    - biomechanics: 生物力学
    - electromagnetic: 电磁分析
    """
    try:
        if request.domain:
            expert = DomainExpert(domain=request.domain, model=request.model)
            response = expert.answer(request.message, history=request.history)
        else:
            agent = QAAgent(model=request.model)
            response = agent.answer(request.message)
        
        return ChatResponse(
            response=response,
            domain=request.domain,
            sources=[],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    Chat with streaming response.
    
    Returns Server-Sent Events (SSE) stream.
    """
    async def generate():
        try:
            if request.domain:
                expert = DomainExpert(domain=request.domain, model=request.model)
                # For now, simulate streaming by chunking the response
                response = expert.answer(request.message, history=request.history)
            else:
                agent = QAAgent(model=request.model)
                response = agent.answer(request.message)
            
            # Simulate streaming by yielding chunks
            chunk_size = 20
            for i in range(0, len(response), chunk_size):
                chunk = response[i:i + chunk_size]
                yield f"data: {json.dumps({'content': chunk})}\n\n"
                await asyncio.sleep(0.02)  # Small delay for effect
            
            yield f"data: {json.dumps({'done': True})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get("/domains")
async def list_domains():
    """List available engineering domains."""
    return {
        "domains": [
            {
                "id": "geotechnical",
                "name": "岩土工程",
                "name_en": "Geotechnical Engineering",
                "icon": "🏗️",
                "description": "土力学、岩石力学、基础工程、隧道工程等",
            },
            {
                "id": "structural",
                "name": "结构工程",
                "name_en": "Structural Engineering",
                "icon": "🏛️",
                "description": "混凝土结构、钢结构、抗震分析等",
            },
            {
                "id": "mechanical",
                "name": "机械工程",
                "name_en": "Mechanical Engineering",
                "icon": "⚙️",
                "description": "机械零件、接触分析、装配体等",
            },
            {
                "id": "thermal",
                "name": "热分析",
                "name_en": "Thermal Analysis",
                "icon": "🔥",
                "description": "传热、热应力、焊接仿真等",
            },
            {
                "id": "impact",
                "name": "冲击动力学",
                "name_en": "Impact Dynamics",
                "icon": "💥",
                "description": "碰撞、爆炸、穿甲、Explicit分析等",
            },
            {
                "id": "composite",
                "name": "复合材料",
                "name_en": "Composite Materials",
                "icon": "🔗",
                "description": "层合板、纤维增强、渐进损伤等",
            },
            {
                "id": "biomechanics",
                "name": "生物力学",
                "name_en": "Biomechanics",
                "icon": "🩺",
                "description": "软组织、骨骼、植入物分析等",
            },
            {
                "id": "electromagnetic",
                "name": "电磁分析",
                "name_en": "Electromagnetic Analysis",
                "icon": "⚡",
                "description": "电磁场、感应加热、多物理场耦合等",
            },
        ]
    }
