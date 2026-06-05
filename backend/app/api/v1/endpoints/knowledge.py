from fastapi import APIRouter

from app.core.dependencies import EmbeddingDep, QdrantDep, SettingsDep
from app.schemas.knowledge import CollectionStats, SearchQuery, SearchResponse, SearchResultItem

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.post("/search", response_model=SearchResponse)
async def search_knowledge(
    request: SearchQuery,
    embedding: EmbeddingDep,
    qdrant: QdrantDep,
    settings: SettingsDep,
) -> SearchResponse:
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
async def get_stats(qdrant: QdrantDep) -> CollectionStats:
    stats = await qdrant.get_collection_stats()
    return CollectionStats(
        collection=stats["collection"],
        vectors_count=stats["vectors_count"],
        points_count=stats["points_count"],
        status=stats["status"],
    )


@router.delete("/repos/{repo_name}")
async def delete_repo(repo_name: str, qdrant: QdrantDep) -> dict:
    deleted = await qdrant.delete_repo(repo_name)
    return {"deleted": deleted}
