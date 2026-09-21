"""
Security response headers.

This is a pure JSON API (no HTML is ever served, no browser renders our
responses directly), so the header set is scoped to what actually matters
for that threat model rather than a copy-pasted "full browser CSP":

- X-Content-Type-Options: stops browsers from MIME-sniffing a JSON error
  body as something executable if a response is ever embedded/proxied.
- X-Frame-Options / frame-ancestors: defense in depth against clickjacking
  if a misconfigured proxy ever serves an HTML representation of an error.
- Referrer-Policy: don't leak our URLs (which can contain resource IDs)
  to third parties via the Referer header on outbound links from any
  client UI.
- Permissions-Policy: explicitly disable browser features this API never
  needs, in case a browser client renders any response.
- Strict-Transport-Security: only sent when the request actually arrived
  over TLS (directly or via a trusted `X-Forwarded-Proto: https`) so it's
  never emitted for plain-HTTP local/dev traffic, where it would be both
  meaningless and potentially confusing.
- Cache-Control: no-store on every response by default — this API returns
  authenticated, often sensitive data (borrower PII, loan amounts), and
  nothing here should ever be cached by an intermediary or the browser.
- Server-identifying headers (`Server`, `X-Powered-By`) are removed/never
  set, so a scanner can't fingerprint the stack from response headers.
"""
from __future__ import annotations

from flask import request

_PERMISSIONS_POLICY = "geolocation=(), camera=(), microphone=(), payment=()"


def register_security_headers(app) -> None:
    @app.after_request
    def _add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = _PERMISSIONS_POLICY
        response.headers.setdefault("Cache-Control", "no-store")

        is_https = request.is_secure or request.headers.get("X-Forwarded-Proto", "").lower() == "https"
        if is_https:
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"

        # Never advertise the WSGI server / framework version.
        response.headers.pop("Server", None)
        response.headers.pop("X-Powered-By", None)

        return response
