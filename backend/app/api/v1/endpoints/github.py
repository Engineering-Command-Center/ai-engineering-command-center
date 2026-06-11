from fastapi import APIRouter, Cookie, HTTPException, Query

from app.core.config import get_settings
from app.core.dependencies import GitHubDep
from app.schemas.github import PullRequestListResponse, RepositoryListResponse
from app.services.auth import decode_jwt

router = APIRouter(prefix="/github", tags=["github"])
settings = get_settings()


def _require_auth(ecc_token: str | None) -> None:
    if not ecc_token or not decode_jwt(settings, ecc_token):
        raise HTTPException(status_code=401, detail="Not authenticated")


@router.get("/repos", response_model=RepositoryListResponse, summary="List org repositories")
async def list_repos(
    github: GitHubDep,
    per_page: int = Query(default=30, ge=1, le=100),
    page: int = Query(default=1, ge=1),
    ecc_token: str | None = Cookie(default=None),
) -> RepositoryListResponse:
    _require_auth(ecc_token)
    return await github.list_repositories(per_page=per_page, page=page)


@router.get(
    "/repos/{repo}/pulls",
    response_model=PullRequestListResponse,
    summary="List open PRs for a repository",
)
async def list_pull_requests(
    repo: str, github: GitHubDep, ecc_token: str | None = Cookie(default=None)
) -> PullRequestListResponse:
    _require_auth(ecc_token)
    return await github.list_open_pull_requests(repo)
