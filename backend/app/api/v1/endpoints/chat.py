from fastapi import APIRouter

from app.core.dependencies import GeminiDep
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse, summary="Chat with AI assistant")
async def chat(request: ChatRequest, gemini: GeminiDep) -> ChatResponse:
    return await gemini.chat(request.message, request.history)
