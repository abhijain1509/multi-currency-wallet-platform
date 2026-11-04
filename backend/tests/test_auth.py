def test_signup_and_login(client):
    resp = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "alice@example.com",
            "password": "supersecret1",
            "full_name": "Alice",
            "default_currency": "EUR",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["user"]["email"] == "alice@example.com"
    assert body["user"]["default_currency"] == "EUR"
    assert body["access_token"]

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "supersecret1"},
    )
    assert login.status_code == 200
    assert login.json()["access_token"]


def test_duplicate_signup_conflicts(client):
    payload = {
        "email": "dup@example.com",
        "password": "supersecret1",
        "full_name": "Dup",
    }
    assert client.post("/api/v1/auth/signup", json=payload).status_code == 201
    assert client.post("/api/v1/auth/signup", json=payload).status_code == 409


def test_login_wrong_password(client):
    client.post(
        "/api/v1/auth/signup",
        json={"email": "bob@example.com", "password": "supersecret1", "full_name": "Bob"},
    )
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "bob@example.com", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


def test_profile_requires_auth(client):
    assert client.get("/api/v1/auth/profile").status_code in (401, 403)


def test_login_sets_httponly_cookie(client):
    client.post(
        "/api/v1/auth/signup",
        json={"email": "cookie@example.com", "password": "supersecret1", "full_name": "C"},
    )
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "cookie@example.com", "password": "supersecret1"},
    )
    assert resp.status_code == 200
    set_cookie = resp.headers.get("set-cookie", "").lower()
    assert "access_token=" in set_cookie
    assert "httponly" in set_cookie
    # The token must NOT be exposed to JS via a readable cookie flag.
    assert "samesite" in set_cookie


def test_cookie_authenticates_without_bearer_header(client):
    # Signup sets the httpOnly cookie in the client jar.
    client.post(
        "/api/v1/auth/signup",
        json={"email": "cookieauth@example.com", "password": "supersecret1", "full_name": "C"},
    )
    # No Authorization header — the cookie alone must authenticate.
    resp = client.get("/api/v1/auth/profile")
    assert resp.status_code == 200
    assert resp.json()["email"] == "cookieauth@example.com"


def test_logout_clears_cookie(client):
    client.post(
        "/api/v1/auth/signup",
        json={"email": "logout@example.com", "password": "supersecret1", "full_name": "C"},
    )
    assert client.get("/api/v1/auth/profile").status_code == 200
    client.post("/api/v1/auth/logout")
    assert client.get("/api/v1/auth/profile").status_code == 401


def test_update_profile(client, auth_headers):
    headers = auth_headers("carol@example.com")
    resp = client.patch(
        "/api/v1/auth/profile",
        json={"full_name": "Carol New", "default_currency": "GBP"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Carol New"
    assert resp.json()["default_currency"] == "GBP"


# Minimal valid 1x1 PNG.
_PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000a49444154789c6360000002000154a24f5f0000000049454e44ae426082"
)


def test_upload_photo(client, auth_headers, monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    headers = auth_headers("photo@example.com")
    resp = client.post(
        "/api/v1/auth/profile/photo",
        files={"file": ("avatar.png", _PNG_BYTES, "image/png")},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    photo_url = resp.json()["photo_url"]
    assert photo_url.startswith("/api/v1/media/")
    # The file was actually written to disk.
    assert (tmp_path / photo_url.rsplit("/", 1)[-1]).exists()


def test_upload_photo_rejects_non_image(client, auth_headers, monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    headers = auth_headers("photo2@example.com")
    resp = client.post(
        "/api/v1/auth/profile/photo",
        files={"file": ("note.txt", b"hello", "text/plain")},
        headers=headers,
    )
    assert resp.status_code == 415


def test_upload_photo_rejects_oversize(client, auth_headers, monkeypatch, tmp_path):
    from app.core.config import settings

    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    monkeypatch.setattr(settings, "max_upload_bytes", 10)
    headers = auth_headers("photo3@example.com")
    resp = client.post(
        "/api/v1/auth/profile/photo",
        files={"file": ("big.png", _PNG_BYTES, "image/png")},
        headers=headers,
    )
    assert resp.status_code == 413
