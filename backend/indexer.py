#!/usr/bin/env python3
"""
CLI indexer for the Engineering Command Center knowledge base.

Usage:
    python indexer.py --sync                      # clone/pull repos from GitHub
    python indexer.py --index [--repo NAME]       # embed + upsert into Qdrant
    python indexer.py --sync --index              # sync then immediately index
    python indexer.py --dry-run                   # count chunks without embedding
    python indexer.py --stats                     # Qdrant collection stats
    python indexer.py --search "query"            # test semantic search
    python indexer.py --delete-repo NAME          # remove repo from Qdrant
"""
from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

# Ensure the backend package is importable when run from backend/
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import get_settings
from app.schemas.repository_scan import SyncRequest
from app.services.chunker import Chunk, ChunkingService
from app.services.embedding import EmbeddingService
from app.services.qdrant import QdrantService
from app.services.repository_scanner import GitHubRepositoryService


def _get_commit_sha(repo_path: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def _walk_repo(repo_path: Path, chunker: ChunkingService) -> list[Path]:
    """Return all indexable files under repo_path, skipping .git/."""
    indexable: list[Path] = []
    for path in repo_path.rglob("*"):
        if ".git" in path.parts:
            continue
        if not path.is_file():
            continue
        if chunker.is_indexable(path):
            indexable.append(path)
    return indexable


async def run_sync(settings: Any, repo_name: str | None) -> None:
    """Clone / pull repos from GitHub into repos_base_path."""
    scanner = GitHubRepositoryService(settings)
    try:
        print(f"[SYNC] Discovering repos in org '{settings.github_org}' ...", flush=True)
        repos = await scanner.discover_repositories()

        if not repos:
            print("[SYNC] No repos matched the current filter settings.", flush=True)
            print(f"       GITHUB_ORG={settings.github_org}", flush=True)
            print(f"       GITHUB_REPO_PREFIX={settings.github_repo_prefix}", flush=True)
            print(f"       REPO_INCLUDE_PATTERNS={settings.repo_include_patterns}", flush=True)
            return

        if repo_name:
            names = [repo_name]
        else:
            names = []  # sync all discovered

        print(f"[SYNC] Found {len(repos)} matching repos — starting sync ...", flush=True)
        request = SyncRequest(names=names if names else None, force_reclone=False)
        response = await scanner.sync_all(request)

        print(
            f"\n[SYNC] Done — succeeded={response.succeeded} "
            f"failed={response.failed} elapsed={response.duration_seconds}s",
            flush=True,
        )
        for r in response.results:
            status = "✓" if r.state.value == "ok" else "✗"
            print(f"  {status} {r.name}  ({r.duration_seconds}s)"
                  + (f"  ERROR: {r.error}" if r.error else ""), flush=True)
    finally:
        await scanner.close()


class IndexerPipeline:
    def __init__(
        self,
        args: argparse.Namespace,
        settings: Any,
        chunker: ChunkingService,
        embedding: EmbeddingService,
        qdrant: QdrantService,
    ) -> None:
        self.args = args
        self.settings = settings
        self.chunker = chunker
        self.embedding = embedding
        self.qdrant = qdrant

    async def run(self) -> None:
        repos_path = Path(self.args.repos_path or self.settings.repos_base_path)

        if not repos_path.exists():
            print(f"[ERROR] repos_path does not exist: {repos_path}", flush=True)
            print(f"        Run --sync first to clone repos, or set REPOS_BASE_PATH correctly.", flush=True)
            return

        # Determine which repos to process
        if self.args.repo:
            repo_dirs = [repos_path / self.args.repo]
            if not repo_dirs[0].is_dir():
                print(f"[ERROR] Repo not found at: {repo_dirs[0]}", flush=True)
                print(f"        Run --sync --repo {self.args.repo} to clone it first.", flush=True)
                return
        else:
            repo_dirs = [d for d in repos_path.iterdir() if d.is_dir()]

        if not repo_dirs:
            print("[INFO] No repos found in repos_path.", flush=True)
            print(f"       Path: {repos_path}", flush=True)
            print(f"       Run:  python indexer.py --sync", flush=True)
            return

        pipeline_start = time.monotonic()
        total_files = 0
        total_chunks = 0
        total_vectors = 0
        total_repos = 0

        if not self.args.dry_run:
            await self.qdrant.create_collection()

        for repo_dir in sorted(repo_dirs):
            repo_name = repo_dir.name
            repo_start = time.monotonic()

            print(f"\n[REPO] {repo_name}", flush=True)
            commit_sha = _get_commit_sha(repo_dir)
            if commit_sha:
                print(f"  commit: {commit_sha[:12]}", flush=True)

            files = _walk_repo(repo_dir, self.chunker)
            print(f"  files scanned: {len(files)}", flush=True)

            all_chunks: list[Chunk] = []
            files_indexed = 0
            for file_path in files:
                try:
                    chunks = self.chunker.chunk_file(file_path, repo_dir, repo_name)
                    if chunks:
                        all_chunks.extend(chunks)
                        files_indexed += 1
                except Exception as exc:
                    print(f"  [WARN] Failed to chunk {file_path}: {exc}", flush=True)

            print(f"  files indexed: {files_indexed}", flush=True)
            print(f"  chunks created: {len(all_chunks)}", flush=True)

            if self.args.dry_run:
                print(f"  [DRY RUN] Skipping embed + upsert", flush=True)
                total_files += files_indexed
                total_chunks += len(all_chunks)
                total_repos += 1
                continue

            if all_chunks:
                texts = [c.text for c in all_chunks]
                try:
                    vectors = await self.embedding.embed_batch(
                        texts, task_type=self.settings.embedding_task_type_doc
                    )
                except Exception as exc:
                    print(f"  [ERROR] Embedding failed for {repo_name}: {exc}", flush=True)
                    continue

                try:
                    upserted = await self.qdrant.upsert_chunks(
                        all_chunks, vectors, commit_sha=commit_sha
                    )
                except Exception as exc:
                    print(f"  [ERROR] Upsert failed for {repo_name}: {exc}", flush=True)
                    continue

                total_vectors += upserted
                print(f"  vectors upserted: {upserted}", flush=True)

            elapsed = time.monotonic() - repo_start
            print(f"  elapsed: {elapsed:.1f}s", flush=True)

            total_files += files_indexed
            total_chunks += len(all_chunks)
            total_repos += 1

        total_elapsed = time.monotonic() - pipeline_start
        print(
            f"\n[SUMMARY] repos={total_repos} files={total_files} "
            f"chunks={total_chunks} vectors={total_vectors} "
            f"elapsed={total_elapsed:.1f}s",
            flush=True,
        )


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Engineering Command Center — Knowledge Base Indexer"
    )
    parser.add_argument("--sync", action="store_true",
                        help="Clone/pull repos from GitHub into repos_base_path")
    parser.add_argument("--index", action="store_true",
                        help="Embed + upsert repos into Qdrant")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true",
                        help="Chunk and count without embedding/upserting")
    parser.add_argument("--repo", default=None,
                        help="Operate on a single repo by name")
    parser.add_argument("--force", action="store_true",
                        help="Force re-clone even if repo already exists locally")
    parser.add_argument("--delete-repo", dest="delete_repo", default=None,
                        help="Delete all chunks for a repo from Qdrant")
    parser.add_argument("--stats", action="store_true",
                        help="Print Qdrant collection stats")
    parser.add_argument("--search", default=None, metavar="QUERY",
                        help="Run a test semantic search")
    parser.add_argument("--repos-path", dest="repos_path", default=None,
                        help="Override repos base path from .env")
    parser.add_argument("--workers", type=int, default=4,
                        help="Parallel embedding workers (default: 4)")
    args = parser.parse_args()

    settings = get_settings()
    chunker = ChunkingService(
        max_chars=settings.chunk_max_chars,
        overlap_chars=settings.chunk_overlap_chars,
        max_lines=settings.chunk_max_lines,
        overlap_lines=settings.chunk_overlap_lines,
    )
    embedding = EmbeddingService(settings)
    qdrant = QdrantService(settings)

    try:
        if args.stats:
            try:
                stats = await qdrant.get_collection_stats()
                print("[STATS]")
                for k, v in stats.items():
                    print(f"  {k}: {v}")
            except Exception as exc:
                print(f"[ERROR] Could not fetch stats: {exc}")
            return

        if args.delete_repo:
            await qdrant.create_collection()
            count = await qdrant.delete_repo(args.delete_repo)
            print(f"[DELETE] Deleted chunks for repo '{args.delete_repo}' (result: {count})")
            return

        if args.search:
            await qdrant.create_collection()
            query_vector = await embedding.embed_text(
                args.search, task_type=settings.embedding_task_type_query
            )
            results = await qdrant.search(query_vector=query_vector, limit=10)
            print(f"[SEARCH] '{args.search}' — {len(results)} results\n")
            for i, point in enumerate(results, 1):
                payload = point.payload or {}
                print(
                    f"  {i}. score={point.score:.4f}  repo={payload.get('repo')}  "
                    f"file={payload.get('file_path')}  line={payload.get('start_line')}"
                )
            return

        if args.sync:
            await run_sync(settings, args.repo)

        if args.index or args.dry_run:
            pipeline = IndexerPipeline(args, settings, chunker, embedding, qdrant)
            await pipeline.run()
            return

        if not args.sync:
            parser.print_help()
    finally:
        await qdrant.close()


if __name__ == "__main__":
    asyncio.run(main())
