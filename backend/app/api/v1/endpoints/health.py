import time

from fastapi import APIRouter

from app.core.config import get_settings
from app.core.dependencies import GeminiDep, GitHubDep, QdrantDep
from app.schemas.health import HealthResponse, ReadinessResponse, ServiceStatus, TokenUsage
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

    return HealthResponse(
        status=overall,
        version=settings.app_version,
        environment=settings.environment,
        services=statuses,
        token_usage=TokenUsage(**tracker_stats),
    )


@router.get("/ready", response_model=ReadinessResponse)
async def readiness(qdrant: QdrantDep) -> ReadinessResponse:
    qdrant_ok = await qdrant.health_check()
    return ReadinessResponse(ready=qdrant_ok, checks={"qdrant": qdrant_ok})


@router.get("/live")
async def liveness() -> dict[str, str]:
    return {"status": "alive"}
