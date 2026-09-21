def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_register_success(client):
    resp = client.post("/accounts/register", json={
        "name": "Alice", "email": "alice@example.com", "phone": "9876543210",
        "password": "StrongPass1!", "confirm_password": "StrongPass1!",
    })
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["success"] is True
    assert body["user"]["email"] == "alice@example.com"


def test_register_weak_password_rejected(client):
    resp = client.post("/accounts/register", json={
        "name": "Bob", "email": "bob@example.com",
        "password": "weak", "confirm_password": "weak",
    })
    assert resp.status_code == 400
    assert resp.get_json()["success"] is False


def test_register_duplicate_email_rejected(client):
    payload = {
        "name": "Carl", "email": "carl@example.com",
        "password": "StrongPass1!", "confirm_password": "StrongPass1!",
    }
    first = client.post("/accounts/register", json=payload)
    assert first.status_code == 201
    second = client.post("/accounts/register", json=payload)
    assert second.status_code == 409


def test_login_success_and_me(client):
    client.post("/accounts/register", json={
        "name": "Dana", "email": "dana@example.com",
        "password": "StrongPass1!", "confirm_password": "StrongPass1!",
    })
    login = client.post("/accounts/login", json={"email": "dana@example.com", "password": "StrongPass1!"})
    assert login.status_code == 200
    token = login.get_json()["token"]

    me = client.get("/accounts/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.get_json()["user"]["email"] == "dana@example.com"


def test_login_wrong_password_rejected(client):
    client.post("/accounts/register", json={
        "name": "Eve", "email": "eve@example.com",
        "password": "StrongPass1!", "confirm_password": "StrongPass1!",
    })
    resp = client.post("/accounts/login", json={"email": "eve@example.com", "password": "WrongPass1!"})
    assert resp.status_code == 401


def test_me_without_token_rejected(client):
    resp = client.get("/accounts/me")
    assert resp.status_code == 401


def test_logout_revokes_token(client, auth_headers):
    resp = client.post("/accounts/logout", headers=auth_headers)
    assert resp.status_code == 200

    resp2 = client.get("/accounts/me", headers=auth_headers)
    assert resp2.status_code == 401
