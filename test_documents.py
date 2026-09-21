import io


def test_upload_and_download_document(client, auth_headers):
    data = {
        "document": (io.BytesIO(b"hello world"), "id_proof.txt"),
        "doc_type": "id_proof",
    }
    resp = client.post("/documents/upload", data=data, headers=auth_headers, content_type="multipart/form-data")
    assert resp.status_code == 201
    doc_id = resp.get_json()["document"]["id"]

    download = client.get(f"/documents/{doc_id}/download", headers=auth_headers)
    assert download.status_code == 200
    assert download.data == b"hello world"


def test_upload_rejects_disallowed_extension(client, auth_headers):
    data = {"document": (io.BytesIO(b"MZ..."), "malware.exe")}
    resp = client.post("/documents/upload", data=data, headers=auth_headers, content_type="multipart/form-data")
    assert resp.status_code == 400


def test_download_scoped_to_owner(client, auth_headers, app):
    data = {"document": (io.BytesIO(b"secret"), "secret.txt")}
    resp = client.post("/documents/upload", data=data, headers=auth_headers, content_type="multipart/form-data")
    doc_id = resp.get_json()["document"]["id"]

    # A second user must not be able to download the first user's document.
    client.post("/accounts/register", json={
        "name": "Other User", "email": "other@example.com",
        "password": "StrongPass1!", "confirm_password": "StrongPass1!",
    })
    other_login = client.post("/accounts/login", json={"email": "other@example.com", "password": "StrongPass1!"})
    other_headers = {"Authorization": f"Bearer {other_login.get_json()['token']}"}

    resp = client.get(f"/documents/{doc_id}/download", headers=other_headers)
    assert resp.status_code == 404


def test_delete_document(client, auth_headers):
    data = {"document": (io.BytesIO(b"to delete"), "delete_me.txt")}
    upload = client.post("/documents/upload", data=data, headers=auth_headers, content_type="multipart/form-data")
    doc_id = upload.get_json()["document"]["id"]

    resp = client.delete(f"/documents/{doc_id}", headers=auth_headers)
    assert resp.status_code == 200

    resp2 = client.get(f"/documents/{doc_id}/download", headers=auth_headers)
    assert resp2.status_code == 404


def test_list_documents_is_paginated(client, auth_headers):
    for i in range(3):
        data = {"document": (io.BytesIO(f"file {i}".encode()), f"doc_{i}.txt")}
        client.post("/documents/upload", data=data, headers=auth_headers, content_type="multipart/form-data")

    resp = client.get("/documents", query_string={"page": 1, "page_size": 2}, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body["items"]) == 2
    assert body["pagination"]["total_items"] == 3
    assert body["pagination"]["has_next"] is True
