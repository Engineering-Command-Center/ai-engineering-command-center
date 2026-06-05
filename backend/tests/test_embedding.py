"""Tests for EmbeddingService."""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from app.services.embedding import EmbeddingService


def _make_settings(batch_size: int = 5) -> MagicMock:
    s = MagicMock()
    s.gemini_api_key = "test-key"
    s.embedding_model = "models/text-embedding-004"
    s.embedding_batch_size = batch_size
    return s


def _make_fake_vector(dim: int = 768, seed: int = 0) -> list[float]:
    return [float(seed + i) / (dim + 1) for i in range(dim)]


# ---------------------------------------------------------------------------
# test_embed_text_returns_correct_dimension
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_embed_text_returns_correct_dimension() -> None:
    settings = _make_settings()
    expected_vector = _make_fake_vector(768)

    with patch("app.services.embedding.genai") as mock_genai:
        mock_genai.embed_content.return_value = {"embedding": expected_vector}
        service = EmbeddingService(settings)
        result = await service.embed_text("hello world")

    assert isinstance(result, list)
    assert len(result) == 768
    assert result == expected_vector


# ---------------------------------------------------------------------------
# test_embed_batch_splits_into_batches
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_embed_batch_splits_into_batches() -> None:
    """With batch_size=3 and 7 texts, _embed_batch_sync should be called 3 times."""
    settings = _make_settings(batch_size=3)
    texts = [f"text {i}" for i in range(7)]

    call_count = 0

    def fake_embed_content(model, content, task_type):
        nonlocal call_count
        call_count += 1
        # Return a list of vectors equal in count to input
        return {"embedding": [_make_fake_vector(768, seed=i) for i in range(len(content))]}

    with patch("app.services.embedding.genai") as mock_genai:
        mock_genai.embed_content.side_effect = fake_embed_content
        service = EmbeddingService(settings)
        result = await service.embed_batch(texts)

    # ceil(7 / 3) == 3 batches
    assert call_count == 3
    assert len(result) == 7


# ---------------------------------------------------------------------------
# test_embed_batch_preserves_order
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_embed_batch_preserves_order() -> None:
    """Each vector should correspond to the text at the same position."""
    settings = _make_settings(batch_size=3)
    n = 7
    texts = [f"doc {i}" for i in range(n)]

    def fake_embed_content(model, content, task_type):
        # Each batch: return a distinct vector per text using global index embedded in text
        vectors = []
        for t in content:
            idx = int(t.split()[1])
            vectors.append([float(idx)] * 768)
        return {"embedding": vectors}

    with patch("app.services.embedding.genai") as mock_genai:
        mock_genai.embed_content.side_effect = fake_embed_content
        service = EmbeddingService(settings)
        result = await service.embed_batch(texts)

    assert len(result) == n
    for i, vec in enumerate(result):
        assert vec[0] == float(i), f"Vector at position {i} has wrong value: {vec[0]}"


# ---------------------------------------------------------------------------
# test_embed_batch_empty
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_embed_batch_empty() -> None:
    settings = _make_settings()
    with patch("app.services.embedding.genai"):
        service = EmbeddingService(settings)
        result = await service.embed_batch([])
    assert result == []
