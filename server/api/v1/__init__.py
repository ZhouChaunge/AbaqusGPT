"""API v1 router."""

from fastapi import APIRouter

from .diagnose import router as diagnose_router
from .generate import router as generate_router
from .mesh import router as mesh_router
from .chat import router as chat_router
from .knowledge import router as knowledge_router
from .conversations import router as conversations_router
from .providers import router as providers_router
from .models import router as models_router
from .workspace import router as workspace_router

router = APIRouter()

router.include_router(diagnose_router, prefix="/diagnose", tags=["Diagnose"])
router.include_router(generate_router, prefix="/generate", tags=["Generate"])
router.include_router(mesh_router, prefix="/mesh", tags=["Mesh"])
router.include_router(chat_router, prefix="/chat", tags=["Chat"])
router.include_router(knowledge_router, prefix="/knowledge", tags=["Knowledge"])
router.include_router(conversations_router, prefix="/conversations", tags=["Conversations"])
router.include_router(providers_router, prefix="/providers", tags=["Providers"])
router.include_router(models_router, prefix="/models", tags=["Models"])
router.include_router(workspace_router, prefix="/workspace", tags=["Workspace"])
