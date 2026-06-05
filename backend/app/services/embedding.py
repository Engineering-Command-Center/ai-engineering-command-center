import asyncio

from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    def __init__(self, settings: Settings) -> None:
        self._client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(api_version="v1"),
        )
        self._model = settings.embedding_model
        self._dimensions = settings.embedding_dimensions
        self._batch_size = settings.embedding_batch_size
        # Semaphore is created lazily inside the running event loop to avoid
        # "no current event loop" errors when the service is instantiated
        # outside an async context (e.g. CLI startup code).
        self._semaphore: asyncio.Semaphore | None = None

    def _get_semaphore(self) -> asyncio.Semaphore:
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(5)
        return self._semaphore

    def _embed_config(self, task_type: str) -> types.EmbedContentConfig:
        return types.EmbedContentConfig(
            task_type=task_type.upper(),
            output_dimensionality=self._dimensions,
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
    async def embed_text(self, text: str, task_type: str = "retrieval_document") -> list[float]:
        loop = asyncio.get_running_loop()
        async with self._get_semaphore():
            result = await loop.run_in_executor(
                None,
                lambda: self._client.models.embed_content(
                    model=self._model,
                    contents=text,
                    config=self._embed_config(task_type),
                ),
            )
        return result.embeddings[0].values  # type: ignore[return-value]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
    async def embed_batch(
        self, texts: list[str], task_type: str = "retrieval_document"
    ) -> list[list[float]]:
        if not texts:
            return []

        loop = asyncio.get_running_loop()
        batches: list[list[str]] = []
        for i in range(0, len(texts), self._batch_size):
            batches.append(texts[i : i + self._batch_size])

        results: list[list[float]] = []
        for batch in batches:
            async with self._get_semaphore():
                batch_vectors = await loop.run_in_executor(
                    None,
                    lambda b=batch: self._embed_batch_sync(b, task_type),
                )
            results.extend(batch_vectors)

        return results

    def _embed_batch_sync(self, texts: list[str], task_type: str) -> list[list[float]]:
        result = self._client.models.embed_content(
            model=self._model,
            contents=texts,
            config=self._embed_config(task_type),
        )
        return [e.values for e in result.embeddings]  # type: ignore[return-value]
