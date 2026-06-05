from datetime import datetime

from pydantic import BaseModel


class Repository(BaseModel):
    id: int
    name: str
    full_name: str
    description: str | None
    language: str | None
    stargazers_count: int
    open_issues_count: int
    updated_at: datetime
    html_url: str


class PullRequest(BaseModel):
    id: int
    number: int
    title: str
    state: str
    author: str
    created_at: datetime
    updated_at: datetime
    html_url: str
    repo: str


class RepositoryListResponse(BaseModel):
    repositories: list[Repository]
    total: int


class PullRequestListResponse(BaseModel):
    pull_requests: list[PullRequest]
    total: int
