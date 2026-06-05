from google import genai
from google.genai import types

from app.core.config import Settings
from app.core.logging import get_logger
from app.schemas.chat import ChatMessage, ChatResponse
from app.services.token_tracker import get_token_tracker

logger = get_logger(__name__)


class GeminiService:
    def __init__(self, settings: Settings) -> None:
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model_name = settings.gemini_model
        self._tracker = get_token_tracker()

    async def chat(self, message: str, history: list[ChatMessage]) -> ChatResponse:
        contents: list[types.Content] = [
            types.Content(role=msg.role, parts=[types.Part(text=msg.content)])
            for msg in history
        ]
        contents.append(types.Content(role="user", parts=[types.Part(text=message)]))

        response = await self._client.aio.models.generate_content(
            model=self._model_name,
            contents=contents,
        )

        usage = None
        if response.usage_metadata:
            prompt = response.usage_metadata.prompt_token_count or 0
            completion = response.usage_metadata.candidates_token_count or 0
            await self._tracker.record(prompt, completion)
            usage = {
                "prompt_tokens": prompt,
                "completion_tokens": completion,
                "total_tokens": response.usage_metadata.total_token_count or 0,
            }

        logger.info("gemini_chat_complete", model=self._model_name)
        return ChatResponse(reply=response.text, model=self._model_name, usage=usage)

    async def health_check(self) -> bool:
        try:
            models = self._client.models.list()
            return any(self._model_name in m.name for m in models)
        except Exception:
            logger.warning("gemini_health_check_failed")
            return False
