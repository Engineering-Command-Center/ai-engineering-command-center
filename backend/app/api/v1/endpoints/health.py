import time

from fastapi import APIRouter

from app.core.config import get_settings
from app.core.dependencies import GeminiDep, GitHubDep, QdrantDep
from app.schemas.health import HealthResponse, ReadinessResponse, ServiceStatus, TokenUsage
from app.services.index_state import IndexStateStore
from app.services.token_tracker import get_token_tracker

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/health", response_model=HealthResponse)
async def health(
    gemini: GeminiDep,
    github: GitHubDep,
    qdrant: QdrantDep,
) -> HealthResponse:
    statuses: list[ServiceStatus] = []

    for name, svc in [("gemini", gemini), ("github", github), ("qdrant", qdrant)]:
        start = time.monotonic()
        ok = await svc.health_check()
        latency = round((time.monotonic() - start) * 1000, 2)
        statuses.append(ServiceStatus(
            name=name,
            status="ok" if ok else "degraded",
            latency_ms=latency,
        ))

    overall = "ok" if all(s.status == "ok" for s in statuses) else "degraded"
    tracker_stats = get_token_tracker().stats()

    # ── Index state ───────────────────────────────────────────────────────────
    index_store = IndexStateStore(settings.index_state_path)
    all_repos = index_store.all_repos()
    last_indexed_at: str | None = None
    if all_repos:
        # Find the most recent indexed_at timestamp across all repos
        timestamps = [
            index_store._state[r].get("indexed_at", "")
            for r in all_repos
            if index_store._state.get(r, {}).get("indexed_at")
        ]
        if timestamps:
            last_indexed_at = max(timestamps)

    return HealthResponse(
        status=overall,
        version=settings.app_version,
        environment=settings.environment,
        services=statuses,
        token_usage=TokenUsage(**tracker_stats),
        last_indexed_at=last_indexed_at,
        indexed_repos=len(all_repos),
    )


@router.get("/ready", response_model=ReadinessResponse)
async def readiness(qdrant: QdrantDep) -> ReadinessResponse:
    qdrant_ok = await qdrant.health_check()
    return ReadinessResponse(ready=qdrant_ok, checks={"qdrant": qdrant_ok})


@router.get("/live")
async def liveness() -> dict[str, str]:
    return {"status": "alive"}
