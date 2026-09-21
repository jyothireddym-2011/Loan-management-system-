import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest

from app import create_app


@pytest.fixture()
def app():
    application = create_app("testing")
    yield application


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def auth_headers(client):
    client.post("/accounts/register", json={
        "name": "Test User", "email": "test@example.com", "phone": "9876543210",
        "password": "StrongPass1!", "confirm_password": "StrongPass1!",
    })
    resp = client.post("/accounts/login", json={"email": "test@example.com", "password": "StrongPass1!"})
    token = resp.get_json()["token"]
    return {"Authorization": f"Bearer {token}"}
