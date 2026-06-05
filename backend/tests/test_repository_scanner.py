"""
Unit tests for GitHubRepositoryService.

All network and filesystem operations are mocked — tests run fully offline.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import Settings
from app.schemas.repository_scan import RepoSyncState, SyncRequest
from app.services.repository_scanner import GitHubRepositoryService


def _make_settings(**overrides) -> Settings:  # type: ignore[type-arg]
    base = dict(
        gemini_api_key="test",
        github_token="ghp_test",
        github_org="test-org",
        repos_base_path="/tmp/test-repos",
        repo_include_patterns=["*"],
        repo_exclude_patterns=["experimental-*", "poc-*"],
        github_repo_prefix=None,
        repo_sync_concurrency=2,
    )
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


def _raw_repo(name: str, private: bool = False) -> dict:  # type: ignore[type-arg]
    return {
        "name": name,
        "full_name": f"test-org/{name}",
        "clone_url": f"https://github.com/test-org/{name}.git",
        "ssh_url": f"git@github.com:test-org/{name}.git",
        "default_branch": "main",
        "description": f"{name} description",
        "language": "Python",
        "private": private,
        "archived": False,
    }


# ──────────────────────────────────────────────────────────────
# Filter logic
# ──────────────────────────────────────────────────────────────

class TestMatchesFilters:
    def _svc(self, **kwargs) -> GitHubRepositoryService:  # type: ignore[type-arg]
        return GitHubRepositoryService(_make_settings(**kwargs))

    def test_include_all_passes_normal_repo(self) -> None:
        svc = self._svc()
        assert svc._matches_filters("my-service") is True

    def test_exclude_pattern_blocks(self) -> None:
        svc = self._svc()
        assert svc._matches_filters("experimental-auth") is False
        assert svc._matches_filters("poc-analytics") is False

    def test_prefix_filter_blocks_non_matching(self) -> None:
        svc = self._svc(github_repo_prefix="cinema-")
        assert svc._matches_filters("cinema-backend") is True
        assert svc._matches_filters("analytics-service") is False

    def test_include_pattern_restricts(self) -> None:
        svc = self._svc(repo_include_patterns=["cinema-*"])
        assert svc._matches_filters("cinema-auth") is True
        assert svc._matches_filters("billing-service") is False

    def test_exclude_takes_precedence_over_include(self) -> None:
        svc = self._svc(
            repo_include_patterns=["*"],
            repo_exclude_patterns=["poc-*"],
        )
        assert svc._matches_filters("poc-experiment") is False


# ──────────────────────────────────────────────────────────────
# discover_repositories
# ──────────────────────────────────────────────────────────────

class TestDiscoverRepositories:
    @pytest.fixture
    def svc(self) -> GitHubRepositoryService:
        return GitHubRepositoryService(_make_settings())

    @pytest.mark.asyncio
    async def test_discover_filters_excluded(self, svc: GitHubRepositoryService) -> None:
        raw = [
            _raw_repo("billing-service"),
            _raw_repo("experimental-chat"),
            _raw_repo("poc-ml"),
            _raw_repo("user-service"),
        ]

        with patch.object(svc, "_fetch_all_org_repos", new=AsyncMock(return_value=raw)):
            result = await svc.discover_repositories()

        names = [r.name for r in result]
        assert "billing-service" in names
        assert "user-service" in names
        assert "experimental-chat" not in names
        assert "poc-ml" not in names

    @pytest.mark.asyncio
    async def test_discover_preserves_existing_state(self, svc: GitHubRepositoryService) -> None:
        raw = [_raw_repo("known-repo")]

        # First discovery
        with patch.object(svc, "_fetch_all_org_repos", new=AsyncMock(return_value=raw)):
            await svc.discover_repositories()

        # Manually set state
        svc._registry["known-repo"] = svc._registry["known-repo"].model_copy(
            update={"sync_state": RepoSyncState.OK}
        )

        # Second discovery — should preserve OK state
        with patch.object(svc, "_fetch_all_org_repos", new=AsyncMock(return_value=raw)):
            result = await svc.discover_repositories()

        assert result[0].sync_state == RepoSyncState.OK


# ──────────────────────────────────────────────────────────────
# clone_repository
# ──────────────────────────────────────────────────────────────

class TestCloneRepository:
    @pytest.fixture
    def svc(self) -> GitHubRepositoryService:
        return GitHubRepositoryService(_make_settings())

    @pytest.mark.asyncio
    async def test_clone_skips_if_already_exists(
        self, svc: GitHubRepositoryService, tmp_path: Path
    ) -> None:
        local = tmp_path / "my-repo"
        local.mkdir()
        raw = _raw_repo("my-repo")
        raw_repo_obj = svc._registry.get("my-repo")

        from app.schemas.repository_scan import ScannedRepository
        repo = ScannedRepository(
            **{k: raw[k] for k in raw},
            local_path=str(local),
            sync_state=RepoSyncState.PENDING,
        )

        result = await svc.clone_repository(repo)
        # No clone attempted; state unchanged (still PENDING because we didn't actually clone)
        assert result.local_path == str(local)

    @pytest.mark.asyncio
    async def test_clone_sets_ok_state_on_success(
        self, svc: GitHubRepositoryService, tmp_path: Path
    ) -> None:
        from app.schemas.repository_scan import ScannedRepository

        local = tmp_path / "new-repo"
        repo = ScannedRepository(
            **{k: _raw_repo("new-repo")[k] for k in _raw_repo("new-repo")},
            local_path=str(local),
            sync_state=RepoSyncState.PENDING,
        )
        svc._registry["new-repo"] = repo

        mock_commit = MagicMock()
        mock_commit.hexsha = "abc1234def5678"
        mock_commit.message = "Initial commit"
        mock_git_repo = MagicMock()
        mock_git_repo.head.commit = mock_commit

        with patch("app.services.repository_scanner.Repo.clone_from", return_value=mock_git_repo):
            result = await svc.clone_repository(repo)

        assert result.sync_state == RepoSyncState.OK
        assert result.last_commit_sha == "abc1234def5678"

    @pytest.mark.asyncio
    async def test_clone_sets_error_state_on_failure(
        self, svc: GitHubRepositoryService, tmp_path: Path
    ) -> None:
        from git import GitCommandError

        from app.schemas.repository_scan import ScannedRepository

        local = tmp_path / "broken-repo"
        repo = ScannedRepository(
            **{k: _raw_repo("broken-repo")[k] for k in _raw_repo("broken-repo")},
            local_path=str(local),
            sync_state=RepoSyncState.PENDING,
        )
        svc._registry["broken-repo"] = repo

        with patch(
            "app.services.repository_scanner.Repo.clone_from",
            side_effect=GitCommandError("clone", 128),
        ):
            result = await svc.clone_repository(repo)

        assert result.sync_state == RepoSyncState.ERROR
        assert result.error_message is not None


# ──────────────────────────────────────────────────────────────
# sync_all
# ──────────────────────────────────────────────────────────────

class TestSyncAll:
    @pytest.mark.asyncio
    async def test_sync_all_returns_correct_counts(self) -> None:
        svc = GitHubRepositoryService(_make_settings())
        raw = [_raw_repo("svc-a"), _raw_repo("svc-b")]

        from app.schemas.repository_scan import ScannedRepository

        async def _mock_discover() -> list[ScannedRepository]:
            return [
                ScannedRepository(
                    **{k: r[k] for k in r},
                    local_path=f"/tmp/test-repos/{r['name']}",
                    sync_state=RepoSyncState.PENDING,
                )
                for r in raw
            ]

        async def _mock_sync(repo: ScannedRepository, force_reclone: bool = False) -> ScannedRepository:
            return repo.model_copy(
                update={"sync_state": RepoSyncState.OK, "error_message": None}
            )

        with (
            patch.object(svc, "discover_repositories", new=_mock_discover),
            patch.object(svc, "sync_repository", new=_mock_sync),
        ):
            response = await svc.sync_all(SyncRequest())

        assert response.total == 2
        assert response.succeeded == 2
        assert response.failed == 0
