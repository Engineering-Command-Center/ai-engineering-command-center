"""
RagService — orchestrates the full Retrieval-Augmented Generation pipeline.

Pipeline
--------
question
  → Retriever.retrieve()          embed question + Qdrant top-k search
  → PromptBuilder.build()         assemble system + context + question
  → Gemini generate_content()     call Gemini 2.5 Flash with full prompt
  → RagResponse                   answer + sources + confidence
"""

from __future__ import annotations

import asyncio

from google import genai
from google.genai import types

from app.core.config import Settings
from app.core.logging import get_logger
from app.schemas.rag import RagRequest, RagResponse, RagSource
from app.services.prompt_builder import PromptBuilder
from app.services.retriever import Retriever, RetrievedChunk
from app.services.token_tracker import get_token_tracker

logger = get_logger(__name__)

# Hard cap: if Qdrant returns zero chunks we refuse to send an empty-context
# prompt — the model would freely hallucinate instead of saying "I don't know".
_NO_CONTEXT_ANSWER = (
    "I could not find relevant information in the indexed codebase. "
    "Make sure the relevant repositories have been indexed by running the indexer."
)


class RagService:
    """
    Stateless orchestrator. All dependencies are injected so the service
    is easily testable with mocks.
    """

    def __init__(
        self,
        retriever: Retriever,
        prompt_builder: PromptBuilder,
        settings: Settings,
    ) -> None:
        self._retriever = retriever
        self._prompt_builder = prompt_builder
        self._settings = settings
        self._tracker = get_token_tracker()
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._generate_config = types.GenerateContentConfig(
            temperature=0.2,
            top_p=0.9,
            max_output_tokens=4096,
        )

    async def ask(self, request: RagRequest) -> RagResponse:
        # ── Step 1: Retrieve ──────────────────────────────────────────────────
        chunks: list[RetrievedChunk] = await self._retriever.retrieve(
            question=request.question,
            top_k=request.top_k,
            score_threshold=request.score_threshold,
            repo_filter=request.repo_filter,
            language_filter=request.language_filter,
        )

        chunks_retrieved = len(chunks)

        # ── Step 2: Guard — no usable context ────────────────────────────────
        if not chunks:
            logger.warning("rag_no_context", question=request.question[:120])
            return RagResponse(
                answer=_NO_CONTEXT_ANSWER,
                sources=[],
                confidence=0.0,
                chunks_retrieved=0,
                chunks_used=0,
                model=self._settings.gemini_model,
            )

        # ── Step 3: Build prompt ──────────────────────────────────────────────
        prompt = self._prompt_builder.build(request.question, chunks)

        # ── Step 4: Generate ─────────────────────────────────────────────────
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._client.models.generate_content(
                model=self._settings.gemini_model,
                contents=prompt,
                config=self._generate_config,
            ),
        )
        answer_text: str = response.text

        if response.usage_metadata:
            prompt = response.usage_metadata.prompt_token_count or 0
            completion = response.usage_metadata.candidates_token_count or 0
            await self._tracker.record(prompt, completion)

        logger.info(
            "rag_generation_complete",
            chunks_used=chunks_retrieved,
            answer_chars=len(answer_text),
            model=self._settings.gemini_model,
        )

        # ── Step 5: Build sources list ────────────────────────────────────────
        sources = [
            RagSource(
                repo=c.repo,
                file_path=c.file_path,
                language=c.language,
                start_line=c.start_line,
                end_line=c.end_line,
                score=c.score,
                excerpt=c.text[:300].rstrip() + ("…" if len(c.text) > 300 else ""),
                commit_sha=c.commit_sha,
            )
            for c in chunks
        ]

        # ── Step 6: Confidence ────────────────────────────────────────────────
        # Mean cosine similarity of retrieved chunks — a simple, interpretable
        # proxy. Values above 0.75 indicate strong contextual relevance.
        confidence = round(sum(c.score for c in chunks) / len(chunks), 4)

        return RagResponse(
            answer=answer_text,
            sources=sources,
            confidence=confidence,
            chunks_retrieved=chunks_retrieved,
            chunks_used=chunks_retrieved,
            model=self._settings.gemini_model,
        )
