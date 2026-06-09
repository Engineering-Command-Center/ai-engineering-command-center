import time

from fastapi import APIRouter, Cookie

from app.core.config import get_settings
from app.core.dependencies import RagDep
from app.schemas.rag import RagRequest, RagResponse
from app.services.auth import decode_jwt
from app.services.usage_tracker import get_usage_tracker

router = APIRouter(prefix="/rag", tags=["rag"])
settings = get_settings()


@router.post(
    "/chat",
    response_model=RagResponse,
    summary="Ask a question answered from the indexed codebase (RAG)",
)
async def rag_chat(
    request: RagRequest,
    rag: RagDep,
    ecc_token: str | None = Cookie(default=None),
) -> RagResponse:
    start = time.monotonic()
    result = await rag.ask(request)
    response_ms = int((time.monotonic() - start) * 1000)

    # Log usage (best-effort — never fail the request if tracking errors)
    try:
        email, name = "anonymous", "Anonymous"
        if ecc_token:
            token_data = decode_jwt(settings, ecc_token)
            if token_data:
                email = token_data.sub
                name = token_data.name
        tracker = get_usage_tracker(settings.usage_db_path)
        tracker.log(
            email=email,
            name=name,
            question=request.question,
            repo_filter=request.repo_filter,
            confidence=result.confidence,
            chunks=result.chunks_retrieved,
            cached=result.cached,
            response_ms=response_ms,
        )
    except Exception:
        pass

    return result
