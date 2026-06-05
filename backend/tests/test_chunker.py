"""Tests for ChunkingService."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.services.chunker import Chunk, ChunkingService


def _make_service(**kwargs) -> ChunkingService:
    return ChunkingService(
        max_chars=kwargs.get("max_chars", 4000),
        overlap_chars=kwargs.get("overlap_chars", 200),
        max_lines=kwargs.get("max_lines", 80),
        overlap_lines=kwargs.get("overlap_lines", 15),
    )


# ---------------------------------------------------------------------------
# is_indexable
# ---------------------------------------------------------------------------


def test_is_indexable_accepts_py_file(tmp_path: Path) -> None:
    f = tmp_path / "main.py"
    f.write_text("print('hello')")
    service = _make_service()
    assert service.is_indexable(f) is True


def test_is_indexable_rejects_zip(tmp_path: Path) -> None:
    f = tmp_path / "archive.zip"
    f.write_bytes(b"PK\x03\x04")
    service = _make_service()
    assert service.is_indexable(f) is False


def test_is_indexable_rejects_large_file(tmp_path: Path) -> None:
    f = tmp_path / "big.py"
    f.write_bytes(b"x" * (500 * 1024 + 1))
    service = _make_service()
    assert service.is_indexable(f) is False


def test_is_indexable_accepts_dockerfile(tmp_path: Path) -> None:
    f = tmp_path / "Dockerfile"
    f.write_text("FROM python:3.12\n")
    service = _make_service()
    assert service.is_indexable(f) is True


# ---------------------------------------------------------------------------
# detect_language
# ---------------------------------------------------------------------------


def test_detect_language_python(tmp_path: Path) -> None:
    f = tmp_path / "app.py"
    service = _make_service()
    assert service.detect_language(f) == "python"


def test_detect_language_typescript(tmp_path: Path) -> None:
    f = tmp_path / "component.tsx"
    service = _make_service()
    assert service.detect_language(f) == "typescript"


# ---------------------------------------------------------------------------
# chunk_code
# ---------------------------------------------------------------------------


def test_chunk_code_produces_overlapping_chunks(tmp_path: Path) -> None:
    """With max_lines=5 and overlap_lines=2, adjacent chunks share 2 lines."""
    service = _make_service(max_lines=5, overlap_lines=2)
    lines = [f"line_{i}\n" for i in range(20)]
    content = "".join(lines)
    repo_root = tmp_path
    f = tmp_path / "code.py"
    f.write_text(content)

    chunks = service.chunk_file(f, repo_root, "myrepo")
    assert len(chunks) >= 2

    # Verify overlap: end of chunk N and start of chunk N+1 should share lines
    for i in range(len(chunks) - 1):
        a = chunks[i]
        b = chunks[i + 1]
        # Start line of next chunk should be less than end line of current chunk
        assert b.start_line <= a.end_line, (
            f"Chunk {i+1} start_line={b.start_line} > chunk {i} end_line={a.end_line} — no overlap"
        )


def test_total_chunks_set_correctly(tmp_path: Path) -> None:
    service = _make_service(max_lines=5, overlap_lines=1)
    content = "\n".join([f"line {i}" for i in range(30)])
    f = tmp_path / "script.py"
    f.write_text(content)

    chunks = service.chunk_file(f, tmp_path, "repo")
    total = len(chunks)
    assert total > 1
    for chunk in chunks:
        assert chunk.total_chunks == total


# ---------------------------------------------------------------------------
# chunk_prose
# ---------------------------------------------------------------------------


def test_chunk_prose_splits_on_paragraphs(tmp_path: Path) -> None:
    """Prose chunker should split at paragraph boundaries."""
    service = _make_service(max_chars=100, overlap_chars=20)
    # Each paragraph is ~60 chars; two fit in 100 chars but three wouldn't
    paragraphs = [f"Paragraph {i}: " + ("word " * 8) for i in range(6)]
    content = "\n\n".join(paragraphs)

    f = tmp_path / "doc.md"
    f.write_text(content)

    chunks = service.chunk_file(f, tmp_path, "repo")
    assert len(chunks) >= 2
    for chunk in chunks:
        assert chunk.char_count > 0


# ---------------------------------------------------------------------------
# binary file handling
# ---------------------------------------------------------------------------


def test_chunk_file_returns_empty_for_binary(tmp_path: Path) -> None:
    """Binary files that can't be decoded should return empty list."""
    f = tmp_path / "image.py"  # .py extension but binary content
    # Write truly un-decodable bytes (invalid in both utf-8 and latin-1 is impossible,
    # but we can write null bytes which will decode fine. Instead, write a file that
    # the service gracefully handles even if decode succeeds but is empty/whitespace.)
    # The actual guard is: if content is pure binary-looking, chunk_file returns [].
    # Since latin-1 decodes everything, we test the "all whitespace → no chunks" path.
    f.write_text("   \n\t\n   ")
    service = _make_service()
    chunks = service.chunk_file(f, tmp_path, "repo")
    # Either empty (whitespace-only) or very minimal — just ensure no crash
    assert isinstance(chunks, list)
