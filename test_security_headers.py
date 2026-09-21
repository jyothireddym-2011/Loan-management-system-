"""
Verifies every response carries the baseline security headers, that HSTS
is only sent over "https", and that framework-fingerprinting headers are
stripped.
"""


def test_security_headers_present_on_every_response(client):
    resp = client.get("/health")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["Referrer-Policy"] == "no-referrer"
    assert "geolocation=()" in resp.headers["Permissions-Policy"]
    assert resp.headers["Cache-Control"] == "no-store"
    assert "Server" not in resp.headers
    assert "X-Powered-By" not in resp.headers


def test_hsts_absent_over_plain_http(client):
    resp = client.get("/health")
    assert "Strict-Transport-Security" not in resp.headers


def test_hsts_present_when_forwarded_proto_is_https(client):
    resp = client.get("/health", headers={"X-Forwarded-Proto": "https"})
    assert resp.headers["Strict-Transport-Security"] == "max-age=63072000; includeSubDomains"


def test_readiness_check_reports_database_reachable(client):
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "ok"
    assert body["database"] == "reachable"


def test_liveness_check_does_not_touch_database(client):
    resp = client.get("/health/live")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"
