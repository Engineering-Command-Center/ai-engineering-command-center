from pydantic import BaseModel, Field


class RagSource(BaseModel):
    """A single source chunk that contributed to the answer."""

    repo: str
    file_path: str
    language: str
    start_line: int
    end_line: int
    score: float
    # Excerpt shown to the caller — first 300 chars of the chunk text
    excerpt: str
    commit_sha: str | None


class RagRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2048)
    # Optional filters forwarded to Qdrant
    repo_filter: str | None = Field(
        default=None,
        description="Restrict retrieval to a specific repository.",
    )
    language_filter: str | None = Field(
        default=None,
        description="Restrict retrieval to a specific language (e.g. 'python').",
    )
    # Number of chunks to retrieve from Qdrant before passing to the LLM.
    # More chunks = richer context but longer prompt.
    top_k: int = Field(default=10, ge=1, le=20)
    # Minimum cosine similarity score — chunks below this are discarded.
    score_threshold: float = Field(default=0.0, ge=0.0, le=1.0)


class RagResponse(BaseModel):
    answer: str
    sources: list[RagSource]
    # Mean cosine score of the retrieved chunks — proxy for retrieval confidence
    confidence: float
    # Stats useful for debugging
    chunks_retrieved: int
    chunks_used: int
    model: str
