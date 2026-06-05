from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.services.embedding import EmbeddingService
from app.services.gemini import GeminiService
from app.services.github import GitHubService
from app.services.prompt_builder import PromptBuilder
from app.services.qdrant import QdrantService
from app.services.rag import RagService
from app.services.repository_scanner import GitHubRepositoryService
from app.services.retriever import Retriever

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_gemini_service(settings: SettingsDep) -> GeminiService:
    return GeminiService(settings)


def get_github_service(settings: SettingsDep) -> GitHubService:
    return GitHubService(settings)


def get_qdrant_service(settings: SettingsDep) -> QdrantService:
    return QdrantService(settings)


@lru_cache(maxsize=1)
def _repo_scanner_singleton(settings: Settings) -> GitHubRepositoryService:
    # Singleton: registry state must survive across requests.
    return GitHubRepositoryService(settings)


def get_repo_scanner(settings: SettingsDep) -> GitHubRepositoryService:
    return _repo_scanner_singleton(settings)


def get_embedding_service(settings: SettingsDep) -> EmbeddingService:
    return EmbeddingService(settings)


def get_retriever(
    embedding: Annotated[EmbeddingService, Depends(get_embedding_service)],
    qdrant: Annotated[QdrantService, Depends(get_qdrant_service)],
    settings: SettingsDep,
) -> Retriever:
    return Retriever(embedding, qdrant, settings)


def get_rag_service(
    retriever: Annotated[Retriever, Depends(get_retriever)],
    settings: SettingsDep,
) -> RagService:
    return RagService(retriever, PromptBuilder(), settings)


GeminiDep = Annotated[GeminiService, Depends(get_gemini_service)]
GitHubDep = Annotated[GitHubService, Depends(get_github_service)]
QdrantDep = Annotated[QdrantService, Depends(get_qdrant_service)]
RepoScannerDep = Annotated[GitHubRepositoryService, Depends(get_repo_scanner)]
EmbeddingDep = Annotated[EmbeddingService, Depends(get_embedding_service)]
RagDep = Annotated[RagService, Depends(get_rag_service)]
