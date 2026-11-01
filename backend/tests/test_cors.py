import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import Settings

client = TestClient(app)

PROD_ORIGIN = "https://food-has-a-deadline.deepikareddyrudru.workers.dev"
LOCAL_ORIGIN = "http://localhost:5173"
UNAPPROVED_ORIGIN = "https://malicious-unapproved-site.com"


def test_cors_options_preflight_production_origin():
    """Verify OPTIONS preflight from the production Cloudflare Workers origin succeeds."""
    headers = {
        "Origin": PROD_ORIGIN,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type,authorization",
    }
    response = client.options("/api/v1/auth/register", headers=headers)
    
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}: {response.text}"
    assert response.headers.get("access-control-allow-origin") == PROD_ORIGIN
    assert response.headers.get("access-control-allow-credentials") == "true"
    
    # Verify allowed methods include required methods
    allow_methods = response.headers.get("access-control-allow-methods", "")
    for method in ["OPTIONS", "POST", "GET", "PATCH", "PUT", "DELETE"]:
        assert method in allow_methods, f"Method {method} not in {allow_methods}"
        
    # Verify allowed headers include Content-Type and Authorization
    allow_headers = response.headers.get("access-control-allow-headers", "").lower()
    assert "content-type" in allow_headers
    assert "authorization" in allow_headers


def test_cors_actual_post_request_production_origin():
    """Verify actual request from production origin includes Access-Control-Allow-Origin."""
    headers = {
        "Origin": PROD_ORIGIN,
    }
    # Send a request to an endpoint with the Origin header
    response = client.get("/health", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == PROD_ORIGIN
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_unapproved_origin_rejected():
    """Verify an unapproved origin is rejected and receives no Access-Control-Allow-Origin header."""
    headers = {
        "Origin": UNAPPROVED_ORIGIN,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    }
    response = client.options("/api/v1/auth/register", headers=headers)
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_cors_preserved_development_origins():
    """Verify existing localhost development origins continue to function correctly."""
    headers = {
        "Origin": LOCAL_ORIGIN,
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "authorization",
    }
    response = client.options("/health", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == LOCAL_ORIGIN
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_settings_property_parsing():
    """Verify Settings.cors_origins parses FRONTEND_URL and strips trailing slashes."""
    custom_settings = Settings(
        FRONTEND_URL="https://custom-preview.workers.dev/, http://preview.local:3000"
    )
    origins = custom_settings.cors_origins
    assert PROD_ORIGIN in origins
    assert "https://custom-preview.workers.dev" in origins
    assert "https://custom-preview.workers.dev/" not in origins
    assert "http://preview.local:3000" in origins
    assert LOCAL_ORIGIN in origins
    assert "*" not in origins
