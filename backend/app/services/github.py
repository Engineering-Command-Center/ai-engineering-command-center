import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import Settings
from app.core.logging import get_logger
from app.schemas.github import (
    PullRequest,
    PullRequestListResponse,
    Repository,
    RepositoryListResponse,
)

logger = get_logger(__name__)

GITHUB_API_BASE = "https://api.github.com"


class GitHubService:
    def __init__(self, settings: Settings) -> None:
        self._org = settings.github_org
        self._client = httpx.AsyncClient(
            base_url=GITHUB_API_BASE,
            headers={
                "Authorization": f"Bearer {settings.github_token}",
                "Accept": "application/vnd.github.v3+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def list_repositories(self, per_page: int = 30, page: int = 1) -> RepositoryListResponse:
        response = await self._client.get(
            f"/orgs/{self._org}/repos",
            params={"per_page": per_page, "page": page, "sort": "updated"},
        )
        response.raise_for_status()
        data = response.json()

        repos = [
            Repository(
                id=r["id"],
                name=r["name"],
                full_name=r["full_name"],
                description=r.get("description"),
                language=r.get("language"),
                stargazers_count=r["stargazers_count"],
                open_issues_count=r["open_issues_count"],
                updated_at=r["updated_at"],
                html_url=r["html_url"],
            )
            for r in data
        ]

        logger.info("github_repos_fetched", count=len(repos), org=self._org)
        return RepositoryListResponse(repositories=repos, total=len(repos))

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def list_open_pull_requests(self, repo: str) -> PullRequestListResponse:
        response = await self._client.get(
            f"/repos/{self._org}/{repo}/pulls",
            params={"state": "open", "per_page": 100},
        )
        response.raise_for_status()
        data = response.json()

        prs = [
            PullRequest(
                id=pr["id"],
                number=pr["number"],
                title=pr["title"],
                state=pr["state"],
                author=pr["user"]["login"],
                created_at=pr["created_at"],
                updated_at=pr["updated_at"],
                html_url=pr["html_url"],
                repo=repo,
            )
            for pr in data
        ]

        return PullRequestListResponse(pull_requests=prs, total=len(prs))

    async def health_check(self) -> bool:
        try:
            response = await self._client.get(f"/orgs/{self._org}")
            return response.status_code == 200
        except Exception:
            logger.warning("github_health_check_failed")
            return False

    async def close(self) -> None:
        await self._client.aclose()
