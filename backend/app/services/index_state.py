"""
IndexStateStore — persists the last successfully indexed commit SHA for each repo.

Stored as a simple JSON file on disk so state survives server restarts.

Format:
{
    "auth-service":      {"sha": "abc123def456", "indexed_at": "2026-06-04T10:00:00Z"},
    "payments-service":  {"sha": "789xyz000111", "indexed_at": "2026-06-04T08:30:00Z"}
}

The SHA is used by AutoIndexer to compute `git diff --name-only <old_sha> <current_sha>`,
so only files that actually changed since the last index run are re-embedded.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
UTC = timezone.utc
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)


class IndexStateStore:
    def __init__(self, state_path: str) -> None:
        self._path = Path(state_path)
        self._state: dict[str, dict[str, str]] = self._load()

    # ── Public API ────────────────────────────────────────────────────────────

    def get_sha(self, repo_name: str) -> str | None:
        """Return the last indexed commit SHA for *repo_name*, or None if never indexed."""
        return self._state.get(repo_name, {}).get("sha")

    def set_sha(self, repo_name: str, sha: str) -> None:
        """Record that *repo_name* was successfully indexed at *sha*."""
        self._state[repo_name] = {
            "sha": sha,
            "indexed_at": datetime.now(UTC).isoformat(),
        }
        self._save()
        logger.debug("index_state_updated", repo=repo_name, sha=sha[:12])

    def all_repos(self) -> list[str]:
        return list(self._state.keys())

    # ── Internal ──────────────────────────────────────────────────────────────

    def _load(self) -> dict[str, dict[str, str]]:
        if not self._path.exists():
            logger.info("index_state_not_found_starting_fresh", path=str(self._path))
            return {}
        try:
            data = json.loads(self._path.read_text())
            logger.info("index_state_loaded", repos=len(data), path=str(self._path))
            return data
        except Exception as exc:
            logger.warning("index_state_load_failed_starting_fresh", error=str(exc))
            return {}

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(self._state, indent=2))
        except Exception as exc:
            logger.error("index_state_save_failed", error=str(exc))
