from datetime import datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field, computed_field


class RepoSyncState(StrEnum):
    PENDING = "pending"
    CLONING = "cloning"
    SYNCING = "syncing"
    OK = "ok"
    ERROR = "error"
    SKIPPED = "skipped"


class ScannedRepository(BaseModel):
    """Represents a repository tracked by the scanner."""

    name: str
    full_name: str
    clone_url: str
    ssh_url: str
    default_branch: str
    description: str | None
    language: str | None
    private: bool
    archived: bool
    local_path: str
    sync_state: RepoSyncState = RepoSyncState.PENDING
    last_synced_at: datetime | None = None
    last_commit_sha: str | None = None
    last_commit_message: str | None = None
    error_message: str | None = None
    size_kb: int | None = None

    @computed_field  # type: ignore[misc]
    @property
    def is_cloned(self) -> bool:
        return Path(self.local_path).exists()


class SyncRequest(BaseModel):
    """Body for POST /repositories/sync."""

    names: list[str] | None = Field(
        default=None,
        description="Specific repo names to sync. Omit to sync all discovered repos.",
    )
    force_reclone: bool = Field(
        default=False,
        description="Delete and re-clone even if the local copy already exists.",
    )


class SyncResult(BaseModel):
    """Result of a single repository sync operation."""

    name: str
    state: RepoSyncState
    duration_seconds: float
    error: str | None = None


class SyncResponse(BaseModel):
    """Response for POST /repositories/sync."""

    total: int
    succeeded: int
    failed: int
    skipped: int
    results: list[SyncResult]
    duration_seconds: float


class RepositoryScanResponse(BaseModel):
    """Response for GET /repositories."""

    repositories: list[ScannedRepository]
    total: int
    cloned: int
    pending: int
    errored: int
