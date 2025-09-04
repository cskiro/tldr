"""Test main application."""

from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient):
    """Test root endpoint returns correct response."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "TLDR API"
    assert data["version"] == "0.1.0"
    assert data["docs"] == "/docs"


def test_health_check_endpoint(client: TestClient):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "tldr-api"


def test_api_root_endpoint(client: TestClient):
    """Test API root endpoint."""
    response = client.get("/api/v1/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "TLDR API v1"
