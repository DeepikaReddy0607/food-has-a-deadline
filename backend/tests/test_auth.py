import pytest
from datetime import datetime, timezone, timedelta
from app.core.security import create_access_token
from app.core.config import settings


def test_successful_registration_supplier(client):
    """Verify supplier registration returns 201 and created user details."""
    payload = {
        "name": "Acme Farm",
        "email": "farmer@acmefarm.com",
        "password": "ValidPassword123!",
        "role": "SUPPLIER",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "farmer@acmefarm.com"
    assert data["role"] == "SUPPLIER"
    assert "user_id" in data
    assert "password" not in data


def test_successful_registration_receiver(client):
    """Verify receiver registration returns 201 and created user details."""
    payload = {
        "name": "Community Food Pantry",
        "email": "contact@foodpantry.org",
        "password": "ValidPassword123!",
        "role": "RECEIVER",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "contact@foodpantry.org"
    assert data["role"] == "RECEIVER"


def test_prevention_of_public_admin_registration(client):
    """Verify public registration as ADMIN is forbidden."""
    payload = {
        "name": "Malicious Admin",
        "email": "hacker@evil.com",
        "password": "AdminPassword123!",
        "role": "ADMIN",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422  # Pydantic validation rejection
    assert "ADMIN and COORDINATOR roles must be assigned administratively" in response.text


def test_prevention_of_public_coordinator_registration(client):
    """Verify public registration as COORDINATOR is forbidden."""
    payload = {
        "name": "Attempted Coordinator",
        "email": "wannabe@coord.com",
        "password": "CoordPassword123!",
        "role": "COORDINATOR",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422
    assert "ADMIN and COORDINATOR roles must be assigned administratively" in response.text


def test_duplicate_registration_rejection(client):
    """Verify registering an existing email returns 400 Bad Request."""
    payload = {
        "name": "Duplicate Test",
        "email": "duplicate@test.com",
        "password": "ValidPassword123!",
        "role": "SUPPLIER",
    }
    resp1 = client.post("/api/v1/auth/register", json=payload)
    assert resp1.status_code == 201

    resp2 = client.post("/api/v1/auth/register", json=payload)
    assert resp2.status_code == 400
    assert "already exists" in resp2.json()["detail"]


def test_successful_login(client):
    """Verify valid credentials return Bearer JWT token."""
    reg_payload = {
        "name": "Login User",
        "email": "login@test.com",
        "password": "SecurePassword123!",
        "role": "SUPPLIER",
    }
    client.post("/api/v1/auth/register", json=reg_payload)

    login_payload = {
        "email": "login@test.com",
        "password": "SecurePassword123!",
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in_minutes"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES
    assert data["user"]["email"] == "login@test.com"


def test_incorrect_password_rejection(client):
    """Verify wrong password returns 401 Unauthorized."""
    reg_payload = {
        "name": "User",
        "email": "wrongpass@test.com",
        "password": "CorrectPassword123!",
        "role": "RECEIVER",
    }
    client.post("/api/v1/auth/register", json=reg_payload)

    login_payload = {
        "email": "wrongpass@test.com",
        "password": "WrongPassword999!",
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_current_user_retrieval(client):
    """Verify GET /api/v1/auth/me returns current user info with valid token."""
    reg_payload = {
        "name": "Profile User",
        "email": "profile@test.com",
        "password": "SecurePassword123!",
        "role": "SUPPLIER",
    }
    client.post("/api/v1/auth/register", json=reg_payload)

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "profile@test.com", "password": "SecurePassword123!"},
    )
    token = login_resp.json()["access_token"]

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "profile@test.com"
    assert data["role"] == "SUPPLIER"
    assert data["is_active"] is True
    assert "hashed_password" not in data


def test_missing_auth_header_rejection(client):
    """Verify accessing protected endpoint without token returns 401."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert "Authentication credentials were not provided" in response.json()["detail"]


def test_invalid_jwt_rejection(client):
    """Verify forged/corrupted token returns 401."""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer this.is.an.invalid.token"},
    )
    assert response.status_code == 401
    assert "Invalid authentication token" in response.json()["detail"]


def test_expired_jwt_rejection(client, db_session):
    """Verify expired token returns 401."""
    # Register user
    reg_payload = {
        "name": "Expired Test",
        "email": "expired@test.com",
        "password": "SecurePassword123!",
        "role": "SUPPLIER",
    }
    reg_resp = client.post("/api/v1/auth/register", json=reg_payload)
    user_id = reg_resp.json()["user_id"]

    # Generate an expired token (-10 minutes)
    expired_token = create_access_token(
        subject=user_id,
        role="SUPPLIER",
        expires_delta=timedelta(minutes=-10),
    )

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


def test_role_based_access_restrictions(client, db_session):
    """Verify role-based access restrictions (403 for unauthorized roles, 200 for allowed)."""
    # 1. Register a SUPPLIER
    client.post(
        "/api/v1/auth/register",
        json={
            "name": "Supplier Only",
            "email": "supplier@test.com",
            "password": "Password123!",
            "role": "SUPPLIER",
        },
    )
    login_supplier = client.post(
        "/api/v1/auth/login",
        json={"email": "supplier@test.com", "password": "Password123!"},
    )
    supplier_token = login_supplier.json()["access_token"]

    # SUPPLIER tries to access coordinator protected area -> 403 Forbidden
    resp_forbidden = client.get(
        "/api/v1/protected/coordinator-area",
        headers={"Authorization": f"Bearer {supplier_token}"},
    )
    assert resp_forbidden.status_code == 403
    assert "Operation not permitted" in resp_forbidden.json()["detail"]

    # 2. Directly create a COORDINATOR user in DB to test allowed access
    from app.models.user import User
    from app.core.security import hash_password

    coord = User(
        email="coord@system.org",
        hashed_password=hash_password("CoordPass123!"),
        role="COORDINATOR",
        is_active=True,
    )
    db_session.add(coord)
    db_session.commit()
    db_session.refresh(coord)

    login_coord = client.post(
        "/api/v1/auth/login",
        json={"email": "coord@system.org", "password": "CoordPass123!"},
    )
    coord_token = login_coord.json()["access_token"]

    # COORDINATOR accesses coordinator protected area -> 200 OK
    resp_allowed = client.get(
        "/api/v1/protected/coordinator-area",
        headers={"Authorization": f"Bearer {coord_token}"},
    )
    assert resp_allowed.status_code == 200
    assert resp_allowed.json()["access"] == "GRANTED"
