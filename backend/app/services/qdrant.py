from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    QueryResponse,
    ScoredPoint,
    VectorParams,
)

from app.core.config import Settings
from app.core.logging import get_logger
from app.services.chunker import Chunk

logger = get_logger(__name__)

_UPSERT_BATCH_SIZE = 100


class QdrantService:
    def __init__(self, settings: Settings) -> None:
        self._client = AsyncQdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            api_key=settings.qdrant_api_key,
        )
        self._collection = settings.knowledge_collection
        self._vector_size = settings.embedding_dimensions

    async def create_collection(self) -> None:
        collections = await self._client.get_collections()
        names = {c.name for c in collections.collections}

        if self._collection not in names:
            await self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(size=self._vector_size, distance=Distance.COSINE),
            )
            logger.info("qdrant_collection_created", collection=self._collection)

            for field in ("repo", "language", "file_extension"):
                await self._client.create_payload_index(
                    collection_name=self._collection,
                    field_name=field,
                    field_schema=PayloadSchemaType.KEYWORD,
                )
            logger.info("qdrant_payload_indexes_created", collection=self._collection)

    # Keep backward compat alias used by health endpoint
    async def ensure_collection(self) -> None:
        await self.create_collection()

    async def upsert_chunks(
        self,
        chunks: list[Chunk],
        vectors: list[list[float]],
        commit_sha: str | None = None,
    ) -> int:
        if not chunks:
            return 0

        indexed_at = datetime.now(timezone.utc).isoformat()
        points: list[PointStruct] = []

        for chunk, vector in zip(chunks, vectors):
            point_id = str(
                uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"{chunk.repo}:{chunk.file_path}:{chunk.chunk_index}",
                )
            )
            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "text": chunk.text,
                        "repo": chunk.repo,
                        "file_path": chunk.file_path,
                        "language": chunk.language,
                        "file_extension": chunk.file_extension,
                        "chunk_index": chunk.chunk_index,
                        "total_chunks": chunk.total_chunks,
                        "start_line": chunk.start_line,
                        "end_line": chunk.end_line,
                        "char_count": chunk.char_count,
                        "indexed_at": indexed_at,
                        "commit_sha": commit_sha,
                    },
                )
            )

        total_upserted = 0
        for i in range(0, len(points), _UPSERT_BATCH_SIZE):
            batch = points[i : i + _UPSERT_BATCH_SIZE]
            await self._client.upsert(collection_name=self._collection, points=batch)
            total_upserted += len(batch)
            logger.debug("qdrant_upsert_batch", count=len(batch), total=total_upserted)

        return total_upserted

    async def delete_repo(self, repo: str) -> int:
        result = await self._client.delete(
            collection_name=self._collection,
            points_selector=Filter(
                must=[FieldCondition(key="repo", match=MatchValue(value=repo))]
            ),
        )
        logger.info("qdrant_repo_deleted", repo=repo, status=result.status)
        # Qdrant delete doesn't return a count, so return -1 to indicate success
        return -1

    async def search(
        self,
        query_vector: list[float],
        limit: int = 10,
        repo_filter: str | None = None,
        language_filter: str | None = None,
    ) -> list[ScoredPoint]:
        must_conditions = []
        if repo_filter:
            must_conditions.append(
                FieldCondition(key="repo", match=MatchValue(value=repo_filter))
            )
        if language_filter:
            must_conditions.append(
                FieldCondition(key="language", match=MatchValue(value=language_filter))
            )

        query_filter: Filter | None = None
        if must_conditions:
            query_filter = Filter(must=must_conditions)

        response: QueryResponse = await self._client.query_points(
            collection_name=self._collection,
            query=query_vector,
            limit=limit,
            query_filter=query_filter,
            with_payload=True,
        )
        return response.points

    async def get_collection_stats(self) -> dict[str, Any]:
        info = await self._client.get_collection(collection_name=self._collection)
        return {
            "collection": self._collection,
            "vectors_count": info.vectors_count or 0,
            "indexed_vectors_count": info.indexed_vectors_count or 0,
            "points_count": info.points_count or 0,
            "status": str(info.status),
        }

    async def health_check(self) -> bool:
        try:
            await self._client.get_collections()
            return True
        except Exception:
            logger.warning("qdrant_health_check_failed")
            return False

    async def close(self) -> None:
        await self._client.close()
