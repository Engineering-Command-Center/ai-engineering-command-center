from pydantic import BaseModel, Field


class SearchQuery(BaseModel):
    query: str = Field(..., min_length=1, max_length=2048)
    limit: int = Field(default=10, ge=1, le=50)
    repo_filter: str | None = None
    language_filter: str | None = None
    score_threshold: float | None = Field(default=None, ge=0.0, le=1.0)


class SearchResultItem(BaseModel):
    score: float
    text: str
    repo: str
    file_path: str
    language: str
    file_extension: str
    chunk_index: int
    total_chunks: int
    start_line: int
    end_line: int
    commit_sha: str | None


class SearchResponse(BaseModel):
    results: list[SearchResultItem]
    total: int
    query: str
    model: str


class CollectionStats(BaseModel):
    collection: str
    vectors_count: int
    points_count: int
    status: str
