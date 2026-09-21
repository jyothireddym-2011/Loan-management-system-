"""
Serves the OpenAPI spec + a Swagger UI page (production-roadmap item:
"Add Swagger/OpenAPI documentation"). No flasgger/flask-swagger-ui
dependency — Swagger UI is loaded from a CDN against our own static
openapi.yaml, which keeps the backend's dependency footprint small.
"""
import os

from flask import Blueprint, current_app, send_from_directory

docs_bp = Blueprint("docs", __name__)

_SWAGGER_HTML = """<!DOCTYPE html>
<html>
<head>
  <title>Lending Platform API Docs</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script>
    window.onload = () => SwaggerUIBundle({ url: "/openapi.yaml", dom_id: "#swagger-ui" });
  </script>
</body>
</html>"""


@docs_bp.route("/openapi.yaml", methods=["GET"])
def openapi_spec():
    return send_from_directory(current_app.root_path, "openapi.yaml", mimetype="text/yaml")


@docs_bp.route("/apidocs", methods=["GET"])
def swagger_ui():
    return _SWAGGER_HTML
