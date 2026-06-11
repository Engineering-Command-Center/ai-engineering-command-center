from fastapi import APIRouter, Cookie, HTTPException

from app.core.config import get_settings
from app.core.dependencies import GeminiDep
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.auth import decode_jwt

router = APIRouter(prefix="/chat", tags=["chat"])
settings = get_settings()


@router.post("", response_model=ChatResponse, summary="Chat with AI assistant")
async def chat(
    request: ChatRequest,
    gemini: GeminiDep,
    ecc_token: str | None = Cookie(default=None),
) -> ChatResponse:
    if not ecc_token or not decode_jwt(settings, ecc_token):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return await gemini.chat(request.message, request.history)
