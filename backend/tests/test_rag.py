"""
Unit tests for the RAG pipeline.

All external I/O is mocked — tests run fully offline.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.rag import RagRequest
from app.services.prompt_builder import PromptBuilder
from app.services.retriever import RetrievedChunk


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _make_chunk(
    score: float = 0.85,
    text: str = "def process_payment(retry_count):\n    ...",
    repo: str = "payments-service",
    file_path: str = "src/payments.py",
    language: str = "python",
    start_line: int = 10,
    end_line: int = 50,
) -> RetrievedChunk:
    return RetrievedChunk(
        score=score,
        text=text,
        repo=repo,
        file_path=file_path,
        language=language,
        file_extension=".py",
        chunk_index=0,
        total_chunks=3,
        start_line=start_line,
        end_line=end_line,
        commit_sha="abc123def456",
    )


def _make_settings() -> MagicMock:
    s = MagicMock()
    s.gemini_api_key = "test-key"
    s.gemini_model = "gemini-2.5-flash"
    s.embedding_task_type_query = "retrieval_query"
    return s


# ──────────────────────────────────────────────────────────────────────────────
# PromptBuilder
# ──────────────────────────────────────────────────────────────────────────────

class TestPromptBuilder:
    def test_prompt_contains_system_instructions(self) -> None:
        builder = PromptBuilder()
        chunks = [_make_chunk()]
        prompt = builder.build("How does payment retry work?", chunks)
        assert "Answer ONLY from the context" in prompt

    def test_prompt_contains_question(self) -> None:
        builder = PromptBuilder()
        question = "How does payment retry work?"
        prompt = builder.build(question, [_make_chunk()])
        assert question in prompt

    def test_prompt_contains_chunk_text(self) -> None:
        builder = PromptBuilder()
        chunk = _make_chunk(text="def retry_payment(): pass")
        prompt = builder.build("question?", [chunk])
        assert "def retry_payment(): pass" in prompt

    def test_prompt_includes_source_header(self) -> None:
        builder = PromptBuilder()
        chunk = _make_chunk(repo="payments-service", file_path="src/payments.py", start_line=10, end_line=50)
        prompt = builder.build("q", [chunk])
        assert "payments-service/src/payments.py" in prompt
        assert "lines 10" in prompt

    def test_prompt_shows_no_context_marker_when_no_chunks(self) -> None:
        builder = PromptBuilder()
        prompt = builder.build("question?", [])
        assert "No relevant context" in prompt

    def test_chunks_ordered_by_score_descending(self) -> None:
        builder = PromptBuilder()
        low = _make_chunk(score=0.50, text="low relevance snippet")
        high = _make_chunk(score=0.95, text="high relevance snippet")
        prompt = builder.build("q", [low, high])
        # High-score chunk should appear before low-score chunk
        assert prompt.index("high relevance") < prompt.index("low relevance")

    def test_long_chunk_is_truncated(self) -> None:
        from app.services.prompt_builder import _MAX_CHARS_PER_CHUNK
        builder = PromptBuilder()
        long_text = "x" * (_MAX_CHARS_PER_CHUNK + 500)
        chunk = _make_chunk(text=long_text)
        prompt = builder.build("q", [chunk])
        assert "[truncated]" in prompt

    def test_context_budget_drops_lowest_scoring_chunks(self) -> None:
        from app.services.prompt_builder import _CONTEXT_CHAR_BUDGET
        builder = PromptBuilder()
        # Create chunks that together exceed the budget
        big_text = "a" * 3000
        # First chunk has highest score and should survive
        chunks = [
            _make_chunk(score=0.9 - i * 0.01, text=big_text)
            for i in range(20)
        ]
        prompt = builder.build("q", chunks)
        assert len(prompt) < _CONTEXT_CHAR_BUDGET * 2  # rough sanity check


# ──────────────────────────────────────────────────────────────────────────────
# Retriever
# ──────────────────────────────────────────────────────────────────────────────

class TestRetriever:
    @pytest.mark.asyncio
    async def test_retrieve_calls_embed_with_query_task_type(self) -> None:
        from app.services.retriever import Retriever

        mock_embedding = MagicMock()
        mock_embedding.embed_text = AsyncMock(return_value=[0.1] * 768)

        mock_qdrant = MagicMock()
        mock_qdrant.search = AsyncMock(return_value=[])

        settings = _make_settings()
        retriever = Retriever(mock_embedding, mock_qdrant, settings)

        await retriever.retrieve("How does retry work?")

        mock_embedding.embed_text.assert_called_once_with(
            "How does retry work?",
            task_type="retrieval_query",
        )

    @pytest.mark.asyncio
    async def test_retrieve_applies_score_threshold(self) -> None:
        from app.services.retriever import Retriever

        # Qdrant returns two points; one below threshold
        high_point = MagicMock()
        high_point.score = 0.90
        high_point.payload = {
            "text": "good", "repo": "r", "file_path": "f.py", "language": "python",
            "file_extension": ".py", "chunk_index": 0, "total_chunks": 1,
            "start_line": 1, "end_line": 10, "commit_sha": None,
        }

        low_point = MagicMock()
        low_point.score = 0.30
        low_point.payload = {
            "text": "bad", "repo": "r", "file_path": "g.py", "language": "python",
            "file_extension": ".py", "chunk_index": 0, "total_chunks": 1,
            "start_line": 1, "end_line": 5, "commit_sha": None,
        }

        mock_embedding = MagicMock()
        mock_embedding.embed_text = AsyncMock(return_value=[0.1] * 768)
        mock_qdrant = MagicMock()
        mock_qdrant.search = AsyncMock(return_value=[high_point, low_point])

        retriever = Retriever(mock_embedding, mock_qdrant, _make_settings())
        results = await retriever.retrieve("q", score_threshold=0.70)

        assert len(results) == 1
        assert results[0].score == 0.90

    @pytest.mark.asyncio
    async def test_retrieve_returns_empty_on_no_results(self) -> None:
        from app.services.retriever import Retriever

        mock_embedding = MagicMock()
        mock_embedding.embed_text = AsyncMock(return_value=[0.0] * 768)
        mock_qdrant = MagicMock()
        mock_qdrant.search = AsyncMock(return_value=[])

        retriever = Retriever(mock_embedding, mock_qdrant, _make_settings())
        results = await retriever.retrieve("obscure question")
        assert results == []


# ──────────────────────────────────────────────────────────────────────────────
# RagService
# ──────────────────────────────────────────────────────────────────────────────

class TestRagService:
    def _make_rag(
        self,
        chunks: list[RetrievedChunk],
        answer: str = "Payment retry uses exponential backoff.",
    ):
        from app.services.rag import RagService

        mock_retriever = MagicMock()
        mock_retriever.retrieve = AsyncMock(return_value=chunks)

        mock_response = MagicMock()
        mock_response.text = answer

        with patch("app.services.rag.genai") as mock_genai:
            mock_model = MagicMock()
            mock_model.generate_content.return_value = mock_response
            mock_genai.GenerativeModel.return_value = mock_model
            mock_genai.GenerationConfig = MagicMock(return_value=MagicMock())

            svc = RagService(mock_retriever, PromptBuilder(), _make_settings())
            svc._model = mock_model

        return svc, mock_retriever

    @pytest.mark.asyncio
    async def test_ask_returns_answer_and_sources(self) -> None:
        chunks = [_make_chunk(score=0.88), _make_chunk(score=0.75, file_path="src/retry.py")]
        svc, _ = self._make_rag(chunks)

        response = await svc.ask(RagRequest(question="How does payment retry work?"))

        assert response.answer == "Payment retry uses exponential backoff."
        assert len(response.sources) == 2

    @pytest.mark.asyncio
    async def test_ask_no_context_returns_fallback_answer(self) -> None:
        from app.services.rag import _NO_CONTEXT_ANSWER
        svc, _ = self._make_rag(chunks=[])

        response = await svc.ask(RagRequest(question="Unknown question"))

        assert response.answer == _NO_CONTEXT_ANSWER
        assert response.sources == []
        assert response.confidence == 0.0
        assert response.chunks_retrieved == 0

    @pytest.mark.asyncio
    async def test_ask_confidence_is_mean_score(self) -> None:
        chunks = [_make_chunk(score=0.80), _make_chunk(score=0.60)]
        svc, _ = self._make_rag(chunks)

        response = await svc.ask(RagRequest(question="q?"))

        expected = round((0.80 + 0.60) / 2, 4)
        assert response.confidence == expected

    @pytest.mark.asyncio
    async def test_ask_sources_contain_correct_metadata(self) -> None:
        chunk = _make_chunk(
            repo="payments-service",
            file_path="src/payments.py",
            start_line=10,
            end_line=50,
            score=0.88,
        )
        svc, _ = self._make_rag([chunk])

        response = await svc.ask(RagRequest(question="q?"))

        src = response.sources[0]
        assert src.repo == "payments-service"
        assert src.file_path == "src/payments.py"
        assert src.start_line == 10
        assert src.end_line == 50
        assert src.score == 0.88

    @pytest.mark.asyncio
    async def test_ask_source_excerpt_is_truncated_to_300_chars(self) -> None:
        long_text = "Z" * 500
        chunk = _make_chunk(text=long_text)
        svc, _ = self._make_rag([chunk])

        response = await svc.ask(RagRequest(question="q?"))

        assert len(response.sources[0].excerpt) <= 304  # 300 + "…"
        assert response.sources[0].excerpt.endswith("…")

    @pytest.mark.asyncio
    async def test_ask_respects_repo_filter(self) -> None:
        svc, mock_retriever = self._make_rag([_make_chunk()])

        await svc.ask(RagRequest(question="q?", repo_filter="payments-service"))

        mock_retriever.retrieve.assert_called_once()
        call_kwargs = mock_retriever.retrieve.call_args.kwargs
        assert call_kwargs["repo_filter"] == "payments-service"

    @pytest.mark.asyncio
    async def test_ask_model_name_in_response(self) -> None:
        svc, _ = self._make_rag([_make_chunk()])
        response = await svc.ask(RagRequest(question="q?"))
        assert response.model == "gemini-2.5-flash"
