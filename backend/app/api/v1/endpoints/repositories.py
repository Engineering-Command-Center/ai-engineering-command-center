from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status

from app.core.dependencies import RepoScannerDep
from app.schemas.repository_scan import (
    RepositoryScanResponse,
    ScannedRepository,
    SyncRequest,
    SyncResponse,
)

router = APIRouter(prefix="/repositories", tags=["repositories"])


@router.get(
    "",
    response_model=RepositoryScanResponse,
    summary="List all tracked repositories and their sync state",
)
async def list_repositories(scanner: RepoScannerDep) -> RepositoryScanResponse:
    """
    Returns the current in-memory registry state.
    Call POST /repositories/sync first if the registry is empty.
    """
    return scanner.list_repositories()


@router.post(
    "/discover",
    response_model=list[ScannedRepository],
    summary="Discover repositories from GitHub org (no clone/pull)",
)
async def discover_repositories(scanner: RepoScannerDep) -> list[ScannedRepository]:
    """
    Hits the GitHub API and populates the registry with repos matching the
    configured include/exclude patterns. Does NOT clone or pull.
    """
    return await scanner.discover_repositories()


@router.post(
    "/sync",
    response_model=SyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Clone/sync repositories",
)
async def sync_repositories(
    request: SyncRequest,
    scanner: RepoScannerDep,
) -> SyncResponse:
    """
    Discovers and syncs repositories.

    - Omit `names` to sync every repository matching the configured filters.
    - Provide `names` to sync a specific subset.
    - Set `force_reclone=true` to delete and re-clone local copies.

    This is a synchronous call — it waits until all sync operations complete.
    For large organisations consider running it as a background task.
    """
    return await scanner.sync_all(request)


@router.post(
    "/sync/background",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger repository sync in the background (non-blocking)",
)
async def sync_repositories_background(
    request: SyncRequest,
    background_tasks: BackgroundTasks,
    scanner: RepoScannerDep,
) -> dict[str, str]:
    """
    Enqueues the sync job and returns immediately with HTTP 202.
    Poll GET /repositories to observe progress.
    """

    async def _run() -> None:
        await scanner.sync_all(request)

    background_tasks.add_task(_run)
    return {"status": "accepted", "message": "Sync job enqueued. Poll GET /repositories for progress."}


@router.get(
    "/{repo_name}",
    response_model=ScannedRepository,
    summary="Get a single repository by name",
)
async def get_repository(repo_name: str, scanner: RepoScannerDep) -> ScannedRepository:
    repos = scanner.list_repositories()
    for repo in repos.repositories:
        if repo.name == repo_name:
            return repo
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Repository '{repo_name}' not found in registry.")
