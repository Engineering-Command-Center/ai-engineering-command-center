from fastapi import APIRouter

from app.core.dependencies import RagDep
from app.schemas.rag import RagRequest, RagResponse

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post(
    "/chat",
    response_model=RagResponse,
    summary="Ask a question answered from the indexed codebase (RAG)",
    response_description=(
        "LLM answer grounded in retrieved source chunks, with per-chunk "
        "sources, cosine-similarity confidence score, and retrieval stats."
    ),
)
async def rag_chat(request: RagRequest, rag: RagDep) -> RagResponse:
    """
    Full RAG pipeline:

    1. Embed the question with `text-embedding-004` (RETRIEVAL_QUERY task).
    2. Fetch the top-k most similar chunks from Qdrant (`engineering_knowledge`).
    3. Build a grounded prompt: system instructions + labelled context blocks +
       the original question.
    4. Stream the prompt through Gemini 2.5 Flash (temperature=0.2).
    5. Return the answer, ranked sources, and a confidence score.

    **Confidence** is the mean cosine similarity of the retrieved chunks — a
    value above 0.75 indicates the codebase contains highly relevant material.
    """
    return await rag.ask(request)
