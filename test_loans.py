def _make_borrower(client, headers, aadhaar="123456789012"):
    resp = client.post("/borrowers", json={"name": "Loan Borrower", "aadhaar_number": aadhaar}, headers=headers)
    return resp.get_json()["borrower"]["id"]


def test_create_loan_success(client, auth_headers):
    borrower_id = _make_borrower(client, auth_headers)
    resp = client.post("/loans", json={
        "borrower_id": borrower_id, "lender_name": "ABC Finance", "loan_amount": "50000.00",
        "nominee_signature": "sig1", "lender_signature": "sig2", "borrower_signature": "sig3",
    }, headers=auth_headers)
    assert resp.status_code == 201
    loan = resp.get_json()["loan"]
    assert loan["loan_amount"] == "50000.00"
    assert loan["remaining_amount"] == "50000.00"


def test_create_loan_missing_signature_rejected(client, auth_headers):
    borrower_id = _make_borrower(client, auth_headers)
    resp = client.post("/loans", json={
        "borrower_id": borrower_id, "lender_name": "ABC Finance", "loan_amount": "50000.00",
        "nominee_signature": "", "lender_signature": "sig2", "borrower_signature": "sig3",
    }, headers=auth_headers)
    assert resp.status_code == 400


def test_payment_reduces_remaining_amount(client, auth_headers):
    borrower_id = _make_borrower(client, auth_headers)
    loan = client.post("/loans", json={
        "borrower_id": borrower_id, "lender_name": "ABC Finance", "loan_amount": "50000.00",
        "nominee_signature": "s1", "lender_signature": "s2", "borrower_signature": "s3",
    }, headers=auth_headers).get_json()["loan"]

    resp = client.post(f"/loans/{loan['id']}/payments", json={"amount_paid": "15000.50"}, headers=auth_headers)
    assert resp.status_code == 201
    updated = resp.get_json()["loan"]
    assert updated["paid_amount"] == "15000.50"
    assert updated["remaining_amount"] == "34999.50"


def test_payment_exceeding_balance_rejected(client, auth_headers):
    borrower_id = _make_borrower(client, auth_headers)
    loan = client.post("/loans", json={
        "borrower_id": borrower_id, "lender_name": "ABC Finance", "loan_amount": "1000.00",
        "nominee_signature": "s1", "lender_signature": "s2", "borrower_signature": "s3",
    }, headers=auth_headers).get_json()["loan"]

    resp = client.post(f"/loans/{loan['id']}/payments", json={"amount_paid": "5000.00"}, headers=auth_headers)
    assert resp.status_code == 400


def test_payment_history(client, auth_headers):
    borrower_id = _make_borrower(client, auth_headers)
    loan = client.post("/loans", json={
        "borrower_id": borrower_id, "lender_name": "ABC Finance", "loan_amount": "1000.00",
        "nominee_signature": "s1", "lender_signature": "s2", "borrower_signature": "s3",
    }, headers=auth_headers).get_json()["loan"]

    client.post(f"/loans/{loan['id']}/payments", json={"amount_paid": "200.00"}, headers=auth_headers)
    client.post(f"/loans/{loan['id']}/payments", json={"amount_paid": "300.00"}, headers=auth_headers)

    resp = client.get(f"/loans/{loan['id']}/payments", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body["payments"]) == 2
    assert body["remaining_amount"] == "500.00"


def test_payment_history_is_paginated_and_defaults_to_chronological_order(client, auth_headers):
    borrower_id = _make_borrower(client, auth_headers)
    loan = client.post("/loans", json={
        "borrower_id": borrower_id, "lender_name": "ABC Finance", "loan_amount": "1000.00",
        "nominee_signature": "s1", "lender_signature": "s2", "borrower_signature": "s3",
    }, headers=auth_headers).get_json()["loan"]

    client.post(f"/loans/{loan['id']}/payments", json={"amount_paid": "100.00"}, headers=auth_headers)
    client.post(f"/loans/{loan['id']}/payments", json={"amount_paid": "200.00"}, headers=auth_headers)
    client.post(f"/loans/{loan['id']}/payments", json={"amount_paid": "300.00"}, headers=auth_headers)

    resp = client.get(f"/loans/{loan['id']}/payments", query_string={"page_size": 2}, headers=auth_headers)
    body = resp.get_json()
    assert len(body["payments"]) == 2
    assert body["pagination"]["total_items"] == 3
    # default sort_dir for payment history is ASC (chronological), unlike
    # every other list endpoint which defaults to DESC (newest-first).
    assert body["payments"][0]["amount_paid"] == "100.00"


def test_borrower_loans_list_is_paginated(client, auth_headers):
    borrower_id = _make_borrower(client, auth_headers)
    for amt in ("1000.00", "2000.00", "3000.00"):
        client.post("/loans", json={
            "borrower_id": borrower_id, "lender_name": "ABC Finance", "loan_amount": amt,
            "nominee_signature": "s1", "lender_signature": "s2", "borrower_signature": "s3",
        }, headers=auth_headers)

    resp = client.get(f"/borrowers/{borrower_id}/loans", query_string={"page_size": 2}, headers=auth_headers)
    body = resp.get_json()
    assert len(body["loans"]) == 2
    assert body["pagination"]["total_items"] == 3
    assert body["pagination"]["has_next"] is True
