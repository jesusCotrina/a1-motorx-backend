from tests.conftest import TEST_EMAIL, TEST_PASSWORD


def test_login_ok(client):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["user"]["email"] == TEST_EMAIL
    assert data["user"]["role"] == "admin"
    assert data["user"]["role_name"] == "Administrador"


def test_login_wrong_password(client):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": TEST_EMAIL, "password": "nope"},
    )
    assert resp.status_code == 401


def test_login_unknown_email(client):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "nadie@taller.app", "password": TEST_PASSWORD},
    )
    assert resp.status_code == 401


def test_login_email_case_insensitive(client):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": TEST_EMAIL.upper(), "password": TEST_PASSWORD},
    )
    assert resp.status_code == 200


def test_me_requires_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_with_token(client):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
    ).json()
    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {login['access_token']}"},
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == TEST_EMAIL


def test_refresh_flow(client):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
    ).json()
    resp = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login["refresh_token"]},
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_refresh_rejects_access_token(client):
    login = client.post(
        "/api/v1/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
    ).json()
    resp = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login["access_token"]},
    )
    assert resp.status_code == 401
