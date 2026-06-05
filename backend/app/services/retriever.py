"""
Retriever — embedding-based semantic search over the Qdrant knowledge base.

Responsibility: given a natural-language question, return the top-k most
relevant indexed chunks, already filtered and ranked by cosine similarity.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings
from app.core.logging import get_logger
from app.services.embedding import EmbeddingService
from app.services.qdrant import QdrantService

logger = get_logger(__name__)


@dataclass
class RetrievedChunk:
    """A single chunk returned by the retriever."""

    score: float
    text: str
    repo: str
    file_path: str
    language: str
    file_extension: str
    chunk_index: int
    total_chunks: int
    start_line: int
    end_line: int
    commit_sha: str | None


class Retriever:
    """
    Converts a question to a query embedding then fetches the top-k chunks
    from Qdrant.  Applies an optional score threshold so that only chunks
    above a minimum cosine similarity are returned — preventing unrelated
    snippets from polluting the LLM context.
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        qdrant_service: QdrantService,
        settings: Settings,
    ) -> None:
        self._embedding = embedding_service
        self._qdrant = qdrant_service
        self._settings = settings

    async def retrieve(
        self,
        question: str,
        top_k: int = 10,
        score_threshold: float = 0.0,
        repo_filter: str | None = None,
        language_filter: str | None = None,
    ) -> list[RetrievedChunk]:
        """
        Embed *question* with the RETRIEVAL_QUERY task type (important: this is
        different from RETRIEVAL_DOCUMENT used at index time — using the correct
        task type improves recall on asymmetric retrieval tasks).
        """
        query_vector = await self._embedding.embed_text(
            question,
            task_type=self._settings.embedding_task_type_query,
        )

        scored_points = await self._qdrant.search(
            query_vector=query_vector,
            limit=top_k,
            repo_filter=repo_filter,
            language_filter=language_filter,
        )

        chunks: list[RetrievedChunk] = []
        for point in scored_points:
            if point.score < score_threshold:
                continue
            p = point.payload or {}
            chunks.append(
                RetrievedChunk(
                    score=round(point.score, 6),
                    text=p.get("text", ""),
                    repo=p.get("repo", ""),
                    file_path=p.get("file_path", ""),
                    language=p.get("language", ""),
                    file_extension=p.get("file_extension", ""),
                    chunk_index=p.get("chunk_index", 0),
                    total_chunks=p.get("total_chunks", 0),
                    start_line=p.get("start_line", 0),
                    end_line=p.get("end_line", 0),
                    commit_sha=p.get("commit_sha"),
                )
            )

        logger.info(
            "retrieval_complete",
            question_chars=len(question),
            retrieved=len(scored_points),
            after_threshold=len(chunks),
            score_threshold=score_threshold,
        )
        return chunks
