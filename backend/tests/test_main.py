from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Food Has a Deadline"
    assert data["tagline"] == "Move food before time runs out."
    assert "version" in data
    assert "docs_url" in data


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app_name"] == "Food Has a Deadline"
    assert "database" in data
    assert "status" in data["database"]
    assert "connected" in data["database"]
