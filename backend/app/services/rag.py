"""
RagService — orchestrates the full Retrieval-Augmented Generation pipeline.

Pipeline
--------
question + history
  → Cache check                   return cached response if same question seen recently
  → Retriever.retrieve()          embed question + Qdrant top-k search
  → PromptBuilder.build()         assemble system + history + context + question
  → Gemini generate_content()     call Gemini 2.5 Flash with full prompt
  → RagResponse                   answer + sources + confidence
  → Cache store                   save response for future identical questions
"""

from __future__ import annotations

import asyncio
import hashlib
import time

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

# ── Response cache ────────────────────────────────────────────────────────────
# Simple in-memory LRU-style cache keyed on (question + filters).
# History is intentionally excluded from the cache key — follow-up questions
# in a conversation are usually unique enough to miss the cache anyway, and
# caching by history would create an explosion of keys.
_CACHE_TTL_SECONDS = 3600   # 1 hour
_CACHE_MAX_SIZE = 200       # max entries; oldest evicted when full

_cache: dict[str, tuple[float, RagResponse]] = {}  # key → (expires_at, response)


def _cache_key(request: RagRequest) -> str:
    raw = "|".join([
        request.question.strip().lower(),
        request.repo_filter or "",
        request.language_filter or "",
        str(request.top_k),
        str(request.score_threshold),
    ])
    return hashlib.sha256(raw.encode()).hexdigest()


def _cache_get(key: str) -> RagResponse | None:
    entry = _cache.get(key)
    if entry is None:
        return None
    expires_at, response = entry
    if time.time() > expires_at:
        _cache.pop(key, None)
        return None
    return response


def _cache_set(key: str, response: RagResponse) -> None:
    # Evict oldest entry if at capacity
    if len(_cache) >= _CACHE_MAX_SIZE:
        oldest_key = min(_cache, key=lambda k: _cache[k][0])
        _cache.pop(oldest_key, None)
    _cache[key] = (time.time() + _CACHE_TTL_SECONDS, response)


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
        # ── Step 1: Cache check ───────────────────────────────────────────────
        # Only cache when there's no conversation history — follow-up questions
        # depend on prior context and should always hit the LLM fresh.
        use_cache = not request.history
        cache_key = _cache_key(request)
        if use_cache:
            cached = _cache_get(cache_key)
            if cached is not None:
                logger.info("rag_cache_hit", question=request.question[:80])
                return cached.model_copy(update={"cached": True})

        # ── Step 2: Retrieve ──────────────────────────────────────────────────
        chunks: list[RetrievedChunk] = await self._retriever.retrieve(
            question=request.question,
            top_k=request.top_k,
            score_threshold=request.score_threshold,
            repo_filter=request.repo_filter,
            language_filter=request.language_filter,
        )

        chunks_retrieved = len(chunks)

        # ── Step 3: Guard — no usable context ────────────────────────────────
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

        # ── Step 4: Build prompt (with conversation history) ─────────────────
        prompt = self._prompt_builder.build(
            question=request.question,
            chunks=chunks,
            history=request.history or [],
        )

        # ── Step 5: Generate ─────────────────────────────────────────────────
        loop = asyncio.get_running_loop()
        llm_response = await loop.run_in_executor(
            None,
            lambda: self._client.models.generate_content(
                model=self._settings.gemini_model,
                contents=prompt,
                config=self._generate_config,
            ),
        )
        answer_text: str = llm_response.text

        if llm_response.usage_metadata:
            prompt_tokens = llm_response.usage_metadata.prompt_token_count or 0
            completion_tokens = llm_response.usage_metadata.candidates_token_count or 0
            await self._tracker.record(prompt_tokens, completion_tokens)

        logger.info(
            "rag_generation_complete",
            chunks_used=chunks_retrieved,
            answer_chars=len(answer_text),
            model=self._settings.gemini_model,
            history_turns=len(request.history),
        )

        # ── Step 6: Build sources list ────────────────────────────────────────
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

        # ── Step 7: Confidence ────────────────────────────────────────────────
        confidence = round(sum(c.score for c in chunks) / len(chunks), 4)

        result = RagResponse(
            answer=answer_text,
            sources=sources,
            confidence=confidence,
            chunks_retrieved=chunks_retrieved,
            chunks_used=chunks_retrieved,
            model=self._settings.gemini_model,
            cached=False,
        )

        # ── Step 8: Store in cache (only for stateless requests) ──────────────
        if use_cache:
            _cache_set(cache_key, result)

        return result
