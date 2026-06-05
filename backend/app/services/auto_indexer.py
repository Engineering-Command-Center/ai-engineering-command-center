"""
AutoIndexer — scheduled sync + incremental index pipeline.

Run cycle (triggered by the scheduler every N hours):

1. Discover all repos in the GitHub org (respects include/exclude filters).
2. For each repo (up to repo_sync_concurrency in parallel):
   a. git pull (clone if new repo).
   b. Get current HEAD SHA.
   c. Compare with last indexed SHA from IndexStateStore.
      - If SHA unchanged → skip (nothing new to index).
      - If SHA changed   → get changed files via `git diff --name-only`.
      - If never indexed → index all files.
   d. Chunk + embed + upsert only the changed files.
   e. Save new SHA to IndexStateStore on success.

This means a repo with 500 files but only 3 changed files since last run
will only embed those 3 files — not re-process the whole repo.
"""

from __future__ import annotations

import asyncio
import subprocess
import time
from pathlib import Path

from app.core.config import Settings
from app.core.logging import get_logger
from app.schemas.repository_scan import SyncRequest
from app.services.chunker import Chunk, ChunkingService
from app.services.embedding import EmbeddingService
from app.services.index_state import IndexStateStore
from app.services.qdrant import QdrantService
from app.services.repository_scanner import GitHubRepositoryService

logger = get_logger(__name__)


def _get_head_sha(repo_path: Path) -> str | None:
    """Return the current HEAD commit SHA of a local git repo."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as exc:
        logger.warning("get_head_sha_failed", path=str(repo_path), error=str(exc))
    return None


def _get_changed_files(repo_path: Path, old_sha: str, new_sha: str) -> list[Path]:
    """
    Return paths of files that changed between old_sha and new_sha.
    Uses `git diff --name-only --diff-filter=ACMR` which covers:
      A = Added, C = Copied, M = Modified, R = Renamed
    Deleted files are intentionally excluded — their Qdrant points are left as-is
    (stale but harmless; a full re-index would clean them up).
    """
    try:
        result = subprocess.run(
            [
                "git", "-C", str(repo_path),
                "diff", "--name-only", "--diff-filter=ACMR",
                old_sha, new_sha,
            ],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            logger.warning(
                "git_diff_failed",
                repo=repo_path.name,
                stderr=result.stderr[:200],
            )
            return []
        paths = [
            repo_path / line.strip()
            for line in result.stdout.splitlines()
            if line.strip()
        ]
        return [p for p in paths if p.exists() and p.is_file()]
    except Exception as exc:
        logger.warning("get_changed_files_failed", path=str(repo_path), error=str(exc))
        return []


def _walk_all_files(repo_path: Path, chunker: ChunkingService) -> list[Path]:
    """Return all indexable files in a repo (used for first-time indexing)."""
    files: list[Path] = []
    for path in repo_path.rglob("*"):
        if ".git" in path.parts:
            continue
        if path.is_file() and chunker.is_indexable(path):
            files.append(path)
    return files


class AutoIndexer:
    """
    Orchestrates the scheduled sync + incremental index cycle.
    One instance is created at startup and reused across all scheduled runs.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._chunker = ChunkingService(
            max_chars=settings.chunk_max_chars,
            overlap_chars=settings.chunk_overlap_chars,
            max_lines=settings.chunk_max_lines,
            overlap_lines=settings.chunk_overlap_lines,
        )
        self._embedding = EmbeddingService(settings)
        self._qdrant = QdrantService(settings)
        self._state = IndexStateStore(settings.index_state_path)
        self._repos_path = Path(settings.repos_base_path)

    async def run_cycle(self) -> None:
        """
        Entry point called by the scheduler.
        Discover → sync → incremental index for every repo.
        """
        cycle_start = time.monotonic()
        logger.info("auto_index_cycle_start")

        scanner = GitHubRepositoryService(self._settings)
        try:
            # ── Step 1: Discover all repos in the org ─────────────────────────
            repos = await scanner.discover_repositories()
            if not repos:
                logger.warning("auto_index_no_repos_discovered")
                return

            logger.info("auto_index_repos_discovered", count=len(repos))

            # ── Step 2: Ensure Qdrant collection exists ────────────────────────
            await self._qdrant.create_collection()

            # ── Step 3: Sync + index each repo (bounded concurrency) ───────────
            semaphore = asyncio.Semaphore(self._settings.repo_sync_concurrency)

            async def _process_repo(repo_name: str, clone_url: str, default_branch: str) -> None:
                async with semaphore:
                    await self._sync_and_index_repo(
                        scanner, repo_name, clone_url, default_branch
                    )

            await asyncio.gather(*[
                _process_repo(r.name, r.clone_url, r.default_branch)
                for r in repos
            ])

        finally:
            await scanner.close()

        elapsed = time.monotonic() - cycle_start
        logger.info("auto_index_cycle_complete", elapsed_seconds=round(elapsed, 1))

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _sync_and_index_repo(
        self,
        scanner: GitHubRepositoryService,
        repo_name: str,
        clone_url: str,
        default_branch: str,
    ) -> None:
        repo_path = self._repos_path / repo_name

        # ── a. Git pull (clone if new) ─────────────────────────────────────────
        from app.schemas.repository_scan import SyncRequest as SR
        sync_resp = await scanner.sync_all(SR(names=[repo_name], force_reclone=False))
        if sync_resp.failed > 0:
            logger.error("auto_index_sync_failed", repo=repo_name)
            return

        # ── b. Get current HEAD SHA ────────────────────────────────────────────
        current_sha = _get_head_sha(repo_path)
        if not current_sha:
            logger.warning("auto_index_no_sha", repo=repo_name)
            return

        # ── c. Compare with last indexed SHA ──────────────────────────────────
        last_sha = self._state.get_sha(repo_name)

        if last_sha == current_sha:
            logger.info("auto_index_repo_unchanged", repo=repo_name, sha=current_sha[:12])
            return

        if last_sha is None:
            # Never indexed — process all files
            logger.info("auto_index_repo_first_time", repo=repo_name)
            files_to_index = _walk_all_files(repo_path, self._chunker)
        else:
            # Incremental — only files changed between last_sha and current_sha
            files_to_index = _get_changed_files(repo_path, last_sha, current_sha)
            logger.info(
                "auto_index_repo_incremental",
                repo=repo_name,
                old_sha=last_sha[:12],
                new_sha=current_sha[:12],
                changed_files=len(files_to_index),
            )

        if not files_to_index:
            # git diff returned 0 indexable files (e.g. only deleted files changed)
            logger.info("auto_index_no_indexable_changes", repo=repo_name)
            self._state.set_sha(repo_name, current_sha)
            return

        # ── d. Chunk + embed + upsert only changed files ─────────────────────
        success = await self._index_files(files_to_index, repo_path, repo_name, current_sha)

        # ── e. Save SHA only on success ───────────────────────────────────────
        if success:
            self._state.set_sha(repo_name, current_sha)

    async def _index_files(
        self,
        files: list[Path],
        repo_path: Path,
        repo_name: str,
        commit_sha: str,
    ) -> bool:
        """Chunk, embed, and upsert the given files. Returns True on success."""
        all_chunks: list[Chunk] = []

        for file_path in files:
            if not self._chunker.is_indexable(file_path):
                continue
            try:
                chunks = self._chunker.chunk_file(file_path, repo_path, repo_name)
                all_chunks.extend(chunks)
            except Exception as exc:
                logger.warning("auto_index_chunk_error", file=str(file_path), error=str(exc))

        if not all_chunks:
            logger.info("auto_index_no_chunks", repo=repo_name)
            return True  # Nothing to embed — still mark sha as done

        logger.info("auto_index_embedding", repo=repo_name, chunks=len(all_chunks))

        try:
            vectors = await self._embedding.embed_batch(
                [c.text for c in all_chunks],
                task_type=self._settings.embedding_task_type_doc,
            )
        except Exception as exc:
            logger.error("auto_index_embed_failed", repo=repo_name, error=str(exc))
            return False

        try:
            upserted = await self._qdrant.upsert_chunks(all_chunks, vectors, commit_sha=commit_sha)
            logger.info("auto_index_upserted", repo=repo_name, vectors=upserted)
        except Exception as exc:
            logger.error("auto_index_upsert_failed", repo=repo_name, error=str(exc))
            return False

        return True
