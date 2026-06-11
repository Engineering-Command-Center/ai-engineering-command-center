from fastapi import APIRouter, Cookie, HTTPException

from app.core.config import get_settings
from app.core.dependencies import EmbeddingDep, QdrantDep, SettingsDep
from app.schemas.knowledge import CollectionStats, SearchQuery, SearchResponse, SearchResultItem
from app.services.auth import COOKIE_NAME, decode_jwt

router = APIRouter(prefix="/knowledge", tags=["knowledge"])
settings = get_settings()


def _require_auth(ecc_token: str | None) -> None:
    if not ecc_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if not decode_jwt(settings, ecc_token):
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def _require_admin(ecc_token: str | None) -> None:
    if not ecc_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token_data = decode_jwt(settings, ecc_token)
    if not token_data or not token_data.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")


@router.post("/search", response_model=SearchResponse)
async def search_knowledge(
    request: SearchQuery,
    embedding: EmbeddingDep,
    qdrant: QdrantDep,
    settings: SettingsDep,
    ecc_token: str | None = Cookie(default=None),
) -> SearchResponse:
    _require_auth(ecc_token)
    query_vector = await embedding.embed_text(
        request.query, task_type=settings.embedding_task_type_query
    )

    scored_points = await qdrant.search(
        query_vector=query_vector,
        limit=request.limit,
        repo_filter=request.repo_filter,
        language_filter=request.language_filter,
    )

    results: list[SearchResultItem] = []
    for point in scored_points:
        if request.score_threshold is not None and point.score < request.score_threshold:
            continue
        payload = point.payload or {}
        results.append(
            SearchResultItem(
                score=point.score,
                text=payload.get("text", ""),
                repo=payload.get("repo", ""),
                file_path=payload.get("file_path", ""),
                language=payload.get("language", ""),
                file_extension=payload.get("file_extension", ""),
                chunk_index=payload.get("chunk_index", 0),
                total_chunks=payload.get("total_chunks", 0),
                start_line=payload.get("start_line", 0),
                end_line=payload.get("end_line", 0),
                commit_sha=payload.get("commit_sha"),
            )
        )

    return SearchResponse(
        results=results,
        total=len(results),
        query=request.query,
        model=settings.embedding_model,
    )


@router.get("/stats", response_model=CollectionStats)
async def get_stats(qdrant: QdrantDep, ecc_token: str | None = Cookie(default=None)) -> CollectionStats:
    _require_auth(ecc_token)
    stats = await qdrant.get_collection_stats()
    return CollectionStats(
        collection=stats["collection"],
        vectors_count=stats["vectors_count"],
        points_count=stats["points_count"],
        status=stats["status"],
    )


@router.delete("/repos/{repo_name}")
async def delete_repo(repo_name: str, qdrant: QdrantDep, ecc_token: str | None = Cookie(default=None)) -> dict:
    _require_admin(ecc_token)
    deleted = await qdrant.delete_repo(repo_name)
    return {"deleted": deleted}
