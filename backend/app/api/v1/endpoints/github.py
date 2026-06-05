from fastapi import APIRouter, Query

from app.core.dependencies import GitHubDep
from app.schemas.github import PullRequestListResponse, RepositoryListResponse

router = APIRouter(prefix="/github", tags=["github"])


@router.get("/repos", response_model=RepositoryListResponse, summary="List org repositories")
async def list_repos(
    github: GitHubDep,
    per_page: int = Query(default=30, ge=1, le=100),
    page: int = Query(default=1, ge=1),
) -> RepositoryListResponse:
    return await github.list_repositories(per_page=per_page, page=page)


@router.get(
    "/repos/{repo}/pulls",
    response_model=PullRequestListResponse,
    summary="List open PRs for a repository",
)
async def list_pull_requests(repo: str, github: GitHubDep) -> PullRequestListResponse:
    return await github.list_open_pull_requests(repo)
