"""Every route should be reachable both at its legacy path and under
/api/v1, per the REST versioning requirement — this locks that in."""


def test_health_available_unversioned_and_versioned(client):
    assert client.get("/health").status_code == 200
    assert client.get("/api/v1/health").status_code == 200


def test_register_and_login_work_under_v1(client):
    reg = client.post("/api/v1/accounts/register", json={
        "name": "V1 User", "email": "v1user@example.com", "phone": "9876543210",
        "password": "StrongPass1!", "confirm_password": "StrongPass1!",
    })
    assert reg.status_code == 201

    login = client.post("/api/v1/accounts/login", json={
        "email": "v1user@example.com", "password": "StrongPass1!",
    })
    assert login.status_code == 200
    token = login.get_json()["token"]

    me = client.get("/api/v1/accounts/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.get_json()["user"]["email"] == "v1user@example.com"


def test_legacy_and_v1_share_the_same_underlying_data(client, auth_headers):
    create = client.post("/borrowers", json={
        "name": "Shared Data Borrower", "aadhaar_number": "555566667777",
    }, headers=auth_headers)
    borrower_id = create.get_json()["borrower"]["id"]

    via_v1 = client.get(f"/api/v1/borrowers/{borrower_id}", headers=auth_headers)
    assert via_v1.status_code == 200
    assert via_v1.get_json()["borrower"]["name"] == "Shared Data Borrower"
