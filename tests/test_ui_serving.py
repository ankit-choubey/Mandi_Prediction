"""
UI Asset Serving Tests (MP-APP-001B)
Tests for:
1. Root '/' and '/index.html' serving index.html with text/html
2. Static asset routing (/static/styles.css, /static/app.js, /static/favicon.svg)
3. Strict path traversal blocking (/static/../api.py -> 403 Forbidden)
4. Hidden file access blocking (/static/.hidden -> 403 Forbidden)
5. Method Not Allowed (POST to static assets -> 405)
6. Non-existent static files -> 404 Not Found
"""

from __future__ import annotations

import io
import json
from pathlib import Path
import pytest

from src.api import create_app


def call_app(app, method: str, path: str, body: bytes = b""):
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": "",
        "CONTENT_LENGTH": str(len(body)),
        "CONTENT_TYPE": "application/octet-stream",
        "SERVER_NAME": "127.0.0.1",
        "SERVER_PORT": "8000",
        "wsgi.input": io.BytesIO(body),
        "wsgi.version": (1, 0),
        "wsgi.url_scheme": "http",
    }
    status_box = []
    headers_box = []

    def start_response(status, headers, exc_info=None):
        status_box.append(int(status.split()[0]))
        headers_box.append(dict(headers))

    resp_body = b"".join(app(environ, start_response))
    return status_box[0], headers_box[0], resp_body


def test_root_serves_index_html():
    app = create_app()
    status, headers, body = call_app(app, "GET", "/")
    assert status == 200
    assert "text/html" in headers.get("Content-Type", "")
    assert b"APMC Mandi Intelligence System" in body
    assert b"Research Economics Calculator" in body


def test_static_css_and_js_serving():
    app = create_app()

    # CSS
    status, headers, body = call_app(app, "GET", "/static/styles.css")
    assert status == 200
    assert "text/css" in headers.get("Content-Type", "")
    assert b":root" in body

    # JS
    status, headers, body = call_app(app, "GET", "/static/app.js")
    assert status == 200
    assert "application/javascript" in headers.get("Content-Type", "")
    assert b"APMC Mandi Intelligence System" in body

    # SVG Favicon
    status, headers, body = call_app(app, "GET", "/static/favicon.svg")
    assert status == 200
    assert "image/svg+xml" in headers.get("Content-Type", "")


def test_path_traversal_rejection():
    app = create_app()

    traversal_paths = [
        "/static/../api.py",
        "/static/%2e%2e/api.py",
        "/static/..%2fapi.py",
        "/static/nested/../../api.py",
    ]
    for path in traversal_paths:
        status, headers, body = call_app(app, "GET", path)
        assert status == 403, f"Expected 403 Forbidden for {path}, got {status}"
        data = json.loads(body)
        assert data["status"] == "ERROR"
        assert "TRAVERSAL" in data["error"]["code"]


def test_hidden_file_access_rejection():
    app = create_app()
    status, headers, body = call_app(app, "GET", "/static/.env")
    assert status == 403
    data = json.loads(body)
    assert data["status"] == "ERROR"


def test_static_file_not_found():
    app = create_app()
    status, headers, body = call_app(app, "GET", "/static/nonexistent_file.xyz")
    assert status == 404
    data = json.loads(body)
    assert data["status"] == "ERROR"
    assert data["error"]["code"] == "STATIC_NOT_FOUND"


def test_static_file_method_not_allowed():
    app = create_app()
    status, headers, body = call_app(app, "POST", "/static/styles.css")
    assert status == 405
    data = json.loads(body)
    assert data["status"] == "ERROR"
    assert data["error"]["code"] == "METHOD_NOT_ALLOWED"
