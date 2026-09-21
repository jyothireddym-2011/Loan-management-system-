def _create_record(client, headers, aadhaar="999988887777", amount="200000"):
    return client.post("/api/lending/create", json={
        "borrower_name": "Anita Sharma", "aadhaar_number": aadhaar, "phone_number": "9123456780",
        "lender_name": "XYZ Lenders", "amount": amount, "agreement_filename": "agr.pdf",
        "photo_filename": "photo.jpg", "password": "SecurePass1!", "confirm_password": "SecurePass1!",
    }, headers=headers)


def test_create_lending_record_success(client, auth_headers):
    resp = _create_record(client, auth_headers)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["risk"]["risk"] in {"Low", "Medium", "High"}


def test_duplicate_aadhaar_rejected(client, auth_headers):
    first = _create_record(client, auth_headers)
    assert first.status_code == 201
    second = _create_record(client, auth_headers)
    assert second.status_code == 409
    assert second.get_json()["duplicate"]["duplicate"] is True


def test_check_duplicate_preview(client, auth_headers):
    _create_record(client, auth_headers)
    resp = client.get("/api/lending/check-duplicate", query_string={
        "aadhaar_number": "999988887777", "new_amount": "10000",
    }, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["duplicate"] is True
    assert body["dual_amount"] == "210000.00"


def test_pay_wrong_password_rejected(client, auth_headers):
    _create_record(client, auth_headers)
    resp = client.post("/api/lending/pay", json={
        "borrower_name": "Anita Sharma", "aadhaar_number": "999988887777",
        "paying_amount": "1000", "password": "WrongPass1!", "confirm_password": "WrongPass1!",
        "agreement_filename": "agr.pdf",
    }, headers=auth_headers)
    assert resp.status_code == 400


def test_pay_success_updates_amount(client, auth_headers):
    _create_record(client, auth_headers)
    resp = client.post("/api/lending/pay", json={
        "borrower_name": "Anita Sharma", "aadhaar_number": "999988887777",
        "paying_amount": "50000", "password": "SecurePass1!", "confirm_password": "SecurePass1!",
        "agreement_filename": "agr_v2.pdf",
    }, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()["new_amount"] == "150000.00"


def test_remove_record(client, auth_headers):
    _create_record(client, auth_headers)
    resp = client.post("/api/lending/remove", json={
        "borrower_name": "Anita Sharma", "aadhaar_number": "999988887777",
        "password": "SecurePass1!", "confirm_password": "SecurePass1!",
    }, headers=auth_headers)
    assert resp.status_code == 200

    followup = client.get("/api/lending/999988887777", headers=auth_headers)
    assert followup.status_code == 404


def test_frequent_updates_never_reported_low_risk(client, auth_headers):
    _create_record(client, auth_headers, amount="100")  # tiny amount, would normally be Low
    for _ in range(4):
        client.post("/api/lending/pay", json={
            "borrower_name": "Anita Sharma", "aadhaar_number": "999988887777",
            "paying_amount": "1", "password": "SecurePass1!", "confirm_password": "SecurePass1!",
            "agreement_filename": "agr.pdf",
        }, headers=auth_headers)
    resp = client.get("/api/lending/999988887777", headers=auth_headers)
    assert resp.get_json()["record"]["risk_level"] != "Low"


# --- Security regression tests (this refactor) --------------------------
# These lock in the fix for the unauthenticated-PII-exposure bug: every
# /api/lending/* route must now reject anonymous requests with 401.

def test_lending_endpoints_reject_anonymous_requests(client, auth_headers):
    _create_record(client, auth_headers)

    assert client.get("/api/lending/999988887777").status_code == 401
    assert client.get("/api/lending/check-duplicate", query_string={"aadhaar_number": "999988887777"}).status_code == 401
    assert client.post("/api/lending/create", json={}).status_code == 401
    assert client.post("/api/lending/pay", json={}).status_code == 401
    assert client.post("/api/lending/remove", json={}).status_code == 401
