"""
GitHubRepositoryService — discovers, clones, and syncs GitHub org repositories.

Design notes:
- Git operations are blocking (libgit2/gitpython). They run in a ThreadPoolExecutor
  so they never block the asyncio event loop.
- State is kept in an in-memory registry (dict keyed by repo name). This is intentional
  for the foundation phase; persistence via Qdrant/DB is added in the next phase.
- Concurrency is bounded by settings.repo_sync_concurrency to avoid hammering GitHub's
  clone endpoints and local disk I/O simultaneously.
"""

import asyncio
import fnmatch
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
UTC = timezone.utc
from pathlib import Path

import httpx
from git import GitCommandError, InvalidGitRepositoryError, Repo
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import Settings
from app.core.logging import get_logger
from app.schemas.repository_scan import (
    RepoSyncState,
    RepositoryScanResponse,
    ScannedRepository,
    SyncRequest,
    SyncResponse,
    SyncResult,
)

logger = get_logger(__name__)

GITHUB_API_BASE = "https://api.github.com"
# GitHub returns up to 100 repos per page
_PAGE_SIZE = 100


class GitHubRepositoryService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._org = settings.github_org
        self._base_path = Path(settings.repos_base_path)
        self._include_patterns: list[str] = settings.repo_include_patterns
        self._exclude_patterns: list[str] = settings.repo_exclude_patterns
        self._prefix: str | None = settings.github_repo_prefix
        self._concurrency = settings.repo_sync_concurrency

        # In-memory state registry: repo_name → ScannedRepository
        self._registry: dict[str, ScannedRepository] = {}

        self._http = httpx.AsyncClient(
            base_url=GITHUB_API_BASE,
            headers={
                "Authorization": f"Bearer {settings.github_token}",
                "Accept": "application/vnd.github.v3+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )
        # Single executor shared across the service lifetime
        self._executor = ThreadPoolExecutor(
            max_workers=self._concurrency,
            thread_name_prefix="ecc-git",
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    async def discover_repositories(self) -> list[ScannedRepository]:
        """
        Fetch all repositories in the configured GitHub org, apply prefix +
        include/exclude filters, and populate the in-memory registry.

        Already-known repos retain their sync state; newly discovered repos
        start as PENDING.
        """
        raw = await self._fetch_all_org_repos()
        discovered: list[ScannedRepository] = []

        for raw_repo in raw:
            name: str = raw_repo["name"]

            if not self._matches_filters(name):
                continue

            local_path = self._local_path(name)

            if name in self._registry:
                # Preserve sync state for repos we already know about
                existing = self._registry[name]
                discovered.append(existing)
            else:
                repo = ScannedRepository(
                    name=name,
                    full_name=raw_repo["full_name"],
                    clone_url=raw_repo["clone_url"],
                    ssh_url=raw_repo["ssh_url"],
                    default_branch=raw_repo.get("default_branch") or "main",
                    description=raw_repo.get("description"),
                    language=raw_repo.get("language"),
                    private=raw_repo["private"],
                    archived=raw_repo.get("archived", False),
                    local_path=str(local_path),
                    sync_state=RepoSyncState.OK if local_path.exists() else RepoSyncState.PENDING,
                )
                self._registry[name] = repo
                discovered.append(repo)

        logger.info(
            "repositories_discovered",
            org=self._org,
            total=len(raw),
            after_filters=len(discovered),
        )
        return discovered

    async def clone_repository(self, repo: ScannedRepository) -> ScannedRepository:
        """
        Clone a repository that does not yet exist locally.
        Updates and returns the mutated ScannedRepository.
        """
        self._base_path.mkdir(parents=True, exist_ok=True)
        local_path = Path(repo.local_path)

        if local_path.exists():
            logger.debug("clone_skip_exists", repo=repo.name, path=str(local_path))
            return repo

        repo = repo.model_copy(update={"sync_state": RepoSyncState.CLONING})
        self._registry[repo.name] = repo

        clone_url = self._authenticated_clone_url(repo.clone_url)

        try:
            git_repo = await asyncio.get_event_loop().run_in_executor(
                self._executor,
                lambda: Repo.clone_from(
                    clone_url,
                    str(local_path),
                    branch=repo.default_branch,
                    # no depth arg = full clone (depth=0 is invalid in git)
                ),
            )
            last_commit = git_repo.head.commit
            repo = repo.model_copy(
                update={
                    "sync_state": RepoSyncState.OK,
                    "last_synced_at": datetime.now(UTC),
                    "last_commit_sha": last_commit.hexsha,
                    "last_commit_message": last_commit.message.strip()[:200],
                    "size_kb": _dir_size_kb(local_path),
                    "error_message": None,
                }
            )
            logger.info("repository_cloned", repo=repo.name, sha=last_commit.hexsha[:8])
        except GitCommandError as exc:
            repo = repo.model_copy(
                update={
                    "sync_state": RepoSyncState.ERROR,
                    "error_message": str(exc)[:500],
                }
            )
            logger.error("repository_clone_failed", repo=repo.name, error=str(exc))
        finally:
            self._registry[repo.name] = repo

        return repo

    async def sync_repository(self, repo: ScannedRepository, force_reclone: bool = False) -> ScannedRepository:
        """
        Sync a repository:
        - If not cloned (or force_reclone=True): clone it.
        - If already cloned: fetch + fast-forward to origin/<default_branch>.

        Returns the updated ScannedRepository.
        """
        local_path = Path(repo.local_path)

        if force_reclone and local_path.exists():
            logger.info("repository_force_reclone", repo=repo.name)
            await asyncio.get_event_loop().run_in_executor(
                self._executor,
                lambda: shutil.rmtree(str(local_path), ignore_errors=True),
            )

        if not local_path.exists():
            return await self.clone_repository(repo)

        # Pull latest changes
        repo = repo.model_copy(update={"sync_state": RepoSyncState.SYNCING})
        self._registry[repo.name] = repo

        try:
            git_repo, last_commit = await asyncio.get_event_loop().run_in_executor(
                self._executor,
                lambda: self._pull_latest(local_path, repo.default_branch),
            )
            repo = repo.model_copy(
                update={
                    "sync_state": RepoSyncState.OK,
                    "last_synced_at": datetime.now(UTC),
                    "last_commit_sha": last_commit.hexsha,
                    "last_commit_message": last_commit.message.strip()[:200],
                    "size_kb": _dir_size_kb(local_path),
                    "error_message": None,
                }
            )
            logger.info("repository_synced", repo=repo.name, sha=last_commit.hexsha[:8])
        except (GitCommandError, InvalidGitRepositoryError, ValueError) as exc:
            repo = repo.model_copy(
                update={
                    "sync_state": RepoSyncState.ERROR,
                    "error_message": str(exc)[:500],
                }
            )
            logger.error("repository_sync_failed", repo=repo.name, error=str(exc))
        finally:
            self._registry[repo.name] = repo

        return repo

    async def sync_all(self, request: SyncRequest) -> SyncResponse:
        """
        Discover + sync repositories according to the SyncRequest.

        - If request.names is provided: sync only those repos (must be discoverable).
        - Otherwise: discover all matching repos and sync them.
        - Respects request.force_reclone.
        """
        wall_start = time.monotonic()

        # Always refresh discovery so the registry is up-to-date
        all_repos = await self.discover_repositories()

        if request.names:
            name_set = set(request.names)
            to_sync = [r for r in all_repos if r.name in name_set]
            skipped_count = len(name_set) - len(to_sync)
        else:
            to_sync = all_repos
            skipped_count = 0

        # Bounded parallel sync via semaphore
        semaphore = asyncio.Semaphore(self._concurrency)
        results: list[SyncResult] = []

        async def _sync_one(repo: ScannedRepository) -> SyncResult:
            async with semaphore:
                t0 = time.monotonic()
                updated = await self.sync_repository(repo, force_reclone=request.force_reclone)
                return SyncResult(
                    name=updated.name,
                    state=updated.sync_state,
                    duration_seconds=round(time.monotonic() - t0, 3),
                    error=updated.error_message,
                )

        results = list(await asyncio.gather(*[_sync_one(r) for r in to_sync]))

        succeeded = sum(1 for r in results if r.state == RepoSyncState.OK)
        failed = sum(1 for r in results if r.state == RepoSyncState.ERROR)

        return SyncResponse(
            total=len(to_sync),
            succeeded=succeeded,
            failed=failed,
            skipped=skipped_count,
            results=results,
            duration_seconds=round(time.monotonic() - wall_start, 3),
        )

    def list_repositories(self) -> RepositoryScanResponse:
        """Return current registry state."""
        repos = list(self._registry.values())
        return RepositoryScanResponse(
            repositories=repos,
            total=len(repos),
            cloned=sum(1 for r in repos if r.sync_state == RepoSyncState.OK),
            pending=sum(1 for r in repos if r.sync_state == RepoSyncState.PENDING),
            errored=sum(1 for r in repos if r.sync_state == RepoSyncState.ERROR),
        )

    async def close(self) -> None:
        await self._http.aclose()
        self._executor.shutdown(wait=False)

    # ──────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=15))
    async def _fetch_all_org_repos(self) -> list[dict]:  # type: ignore[type-arg]
        """Page through GitHub's org repos endpoint and return raw dicts."""
        results: list[dict] = []  # type: ignore[type-arg]
        page = 1

        while True:
            params: dict[str, str | int] = {
                "per_page": _PAGE_SIZE,
                "page": page,
                "sort": "full_name",
                "direction": "asc",
            }
            if self._prefix:
                # GitHub has no server-side prefix filter for org repos;
                # we apply it client-side below. Still worth keeping the
                # field in config so callers know intent.
                pass

            response = await self._http.get(f"/orgs/{self._org}/repos", params=params)
            response.raise_for_status()
            page_data: list[dict] = response.json()  # type: ignore[type-arg]

            if not page_data:
                break
            results.extend(page_data)

            # GitHub sends a Link header when there are more pages
            if "next" not in response.headers.get("Link", ""):
                break
            page += 1

        return results

    def _matches_filters(self, name: str) -> bool:
        """
        Returns True if the repo name passes all filters:
          1. Optional prefix check (fast-path rejection)
          2. At least one include pattern matches
          3. No exclude pattern matches
        """
        if self._prefix and not name.startswith(self._prefix):
            return False

        included = any(fnmatch.fnmatch(name, pat) for pat in self._include_patterns)
        if not included:
            return False

        excluded = any(fnmatch.fnmatch(name, pat) for pat in self._exclude_patterns)
        if excluded:
            logger.debug("repository_excluded_by_pattern", repo=name)
            return False

        return True

    def _local_path(self, name: str) -> Path:
        return self._base_path / name

    def _authenticated_clone_url(self, https_url: str) -> str:
        """Embed token into HTTPS URL so clone works without SSH keys."""
        token = self._settings.github_token
        # https://github.com/org/repo  →  https://<token>@github.com/org/repo
        return https_url.replace("https://", f"https://{token}@", 1)

    @staticmethod
    def _pull_latest(local_path: Path, default_branch: str) -> tuple[Repo, object]:
        """
        Blocking git operations — called inside ThreadPoolExecutor.
        Fetches from origin and fast-forwards HEAD to origin/<branch>.
        Raises on merge conflicts or diverged histories.
        """
        git_repo = Repo(str(local_path))
        origin = git_repo.remotes["origin"]
        origin.fetch(prune=True)

        # Resolve the tracking branch
        try:
            remote_ref = origin.refs[default_branch]
        except IndexError:
            # Fallback: try HEAD
            remote_ref = origin.refs[git_repo.active_branch.name]

        git_repo.head.reset(remote_ref.commit, index=True, working_tree=True)
        return git_repo, git_repo.head.commit


def _dir_size_kb(path: Path) -> int:
    """Returns total size of a directory tree in KB (best-effort)."""
    try:
        total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
        return total // 1024
    except OSError:
        return 0
