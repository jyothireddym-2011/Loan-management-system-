def test_create_borrower_success(client, auth_headers):
    resp = client.post("/borrowers", json={
        "name": "Ravi Kumar", "aadhaar_number": "123456789012", "phone": "9998887776",
    }, headers=auth_headers)
    assert resp.status_code == 201
    body = resp.get_json()["borrower"]
    assert body["name"] == "Ravi Kumar"
    # Aadhaar is never returned in full.
    assert body["aadhaar_number"] == "XXXX-XXXX-9012"


def test_create_borrower_invalid_aadhaar(client, auth_headers):
    resp = client.post("/borrowers", json={"name": "Bad Aadhaar", "aadhaar_number": "123"}, headers=auth_headers)
    assert resp.status_code == 400


def test_duplicate_borrower_rejected(client, auth_headers):
    payload = {"name": "Ravi Kumar", "aadhaar_number": "123456789012"}
    first = client.post("/borrowers", json=payload, headers=auth_headers)
    assert first.status_code == 201
    second = client.post("/borrowers", json=payload, headers=auth_headers)
    assert second.status_code == 409
    assert "existing_borrower" in second.get_json()


def test_search_borrowers(client, auth_headers):
    client.post("/borrowers", json={"name": "Search Target", "aadhaar_number": "111122223333"}, headers=auth_headers)
    resp = client.get("/borrowers/search", query_string={"name": "search"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()["count"] == 1


def test_get_borrower_requires_auth(client):
    resp = client.get("/borrowers/1")
    assert resp.status_code == 401


def test_search_borrowers_pagination_and_sorting(client, auth_headers):
    for i in range(3):
        client.post("/borrowers", json={
            "name": f"Paginated Borrower {i}", "aadhaar_number": f"11112222{3330 + i}",
        }, headers=auth_headers)

    resp = client.get(
        "/borrowers/search",
        query_string={"name": "paginated", "page": 1, "page_size": 2, "sort_by": "id", "sort_dir": "ASC"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body["items"]) == 2
    assert body["pagination"]["total_items"] == 3
    assert body["pagination"]["total_pages"] == 2
    assert body["pagination"]["has_next"] is True
    assert body["pagination"]["has_prev"] is False

    resp_page2 = client.get(
        "/borrowers/search",
        query_string={"name": "paginated", "page": 2, "page_size": 2, "sort_by": "id", "sort_dir": "ASC"},
        headers=auth_headers,
    )
    assert resp_page2.get_json()["pagination"]["has_next"] is False
    assert resp_page2.get_json()["pagination"]["has_prev"] is True


def test_search_borrowers_rejects_invalid_sort_field(client, auth_headers):
    resp = client.get("/borrowers/search", query_string={"sort_by": "aadhaar_encrypted"}, headers=auth_headers)
    assert resp.status_code == 400


def test_search_borrowers_rejects_page_size_over_max(client, auth_headers):
    resp = client.get("/borrowers/search", query_string={"page_size": 500}, headers=auth_headers)
    assert resp.status_code == 400
