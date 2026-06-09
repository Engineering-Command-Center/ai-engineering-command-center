from pydantic import BaseModel


class ServiceStatus(BaseModel):
    name: str
    status: str
    latency_ms: float | None = None
    detail: str | None = None


class TokenUsage(BaseModel):
    requests: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    since: str


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    services: list[ServiceStatus]
    token_usage: TokenUsage | None = None
    last_indexed_at: str | None = None   # ISO timestamp of most recently indexed repo
    indexed_repos: int = 0               # total repos that have been indexed at least once


class ReadinessResponse(BaseModel):
    ready: bool
    checks: dict[str, bool]
