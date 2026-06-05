from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_liveness(client: TestClient) -> None:
    response = client.get("/api/v1/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_health_degraded_when_services_down(client: TestClient) -> None:
    with (
        patch("app.services.gemini.GeminiService.health_check", new_callable=AsyncMock, return_value=False),
        patch("app.services.github.GitHubService.health_check", new_callable=AsyncMock, return_value=False),
        patch("app.services.qdrant.QdrantService.health_check", new_callable=AsyncMock, return_value=False),
    ):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "degraded"
