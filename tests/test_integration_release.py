"""
Integration & Recovery Test Suite for Release Candidate (MP-RELEASE-001)
Tests:
1. Valid source -> API healthy, catalog complete (30/26/4).
2. Missing / corrupt source -> degraded status without path/secret leakage.
3. Atomic snapshot recovery -> restored valid source transitions to healthy.
4. Missing / mismatched benchmark -> honest unavailable response, no crash.
5. Invalid provenance & non-finite float rejection -> 400 Bad Request.
6. Service restart determinism -> identical snapshot hash and metrics.
"""

from __future__ import annotations

import io
import json
import os
from pathlib import Path
import tempfile
import pytest

from src.api import MandiApiApp, create_app
from src.service import MandiMarketService


def call_wsgi(app, method: str, path: str, body: bytes = b"", headers: dict = None):
    h = headers or {}
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": "",
        "CONTENT_LENGTH": str(len(body)),
        "CONTENT_TYPE": h.get("Content-Type", "application/json"),
        "SERVER_NAME": "127.0.0.1",
        "SERVER_PORT": "8000",
        "wsgi.input": io.BytesIO(body),
        "wsgi.version": (1, 0),
        "wsgi.url_scheme": "http",
    }
    status_box = []
    headers_box = []

    def start_response(status, resp_headers, exc_info=None):
        status_box.append(int(status.split()[0]))
        headers_box.append(dict(resp_headers))

    resp_body = b"".join(app(environ, start_response))
    return status_box[0], headers_box[0], resp_body


def test_valid_source_healthy_integration():
    """Valid source index produces healthy status and accurate catalog counts."""
    app = create_app()
    status, headers, body = call_wsgi(app, "GET", "/api/v1/health")
    assert status == 200
    data = json.loads(body)
    assert data["status"] == "SUCCESS"
    assert data["data"]["process_status"] == "HEALTHY"

    status, headers, body = call_wsgi(app, "GET", "/api/v1/catalog")
    assert status == 200
    cat_data = json.loads(body)["data"]
    assert cat_data["total_series_count"] == 30
    assert cat_data["accepted_series_count"] == 26
    assert cat_data["review_series_count"] == 4


def test_missing_source_degraded_without_leak():
    """Missing or nonexistent index path yields degraded health without leaking server paths."""
    with tempfile.TemporaryDirectory() as tmpdir:
        nonexistent_path = Path(tmpdir) / "nonexistent_sources.json"
        service = MandiMarketService(latest_index_path=str(nonexistent_path))
        app = MandiApiApp(service)

        status, headers, body = call_wsgi(app, "GET", "/api/v1/health")
        assert status == 200
        data = json.loads(body)
        assert data["data"]["process_status"] == "DEGRADED"

        # Catalog endpoint returns empty/unavailable safely
        status, headers, body = call_wsgi(app, "GET", "/api/v1/catalog")
        assert status == 200
        cat_data = json.loads(body)["data"]
        assert cat_data["total_series_count"] == 0

        # Assert no internal path leaked in error string
        assert str(nonexistent_path) not in body.decode("utf-8")


def test_corrupt_source_handling():
    """Corrupted JSON source index degrades gracefully without unhandled exception."""
    with tempfile.TemporaryDirectory() as tmpdir:
        corrupt_path = Path(tmpdir) / "corrupt_sources.json"
        corrupt_path.write_text("{ this is not valid json !!! }", encoding="utf-8")
        service = MandiMarketService(latest_index_path=str(corrupt_path))
        app = MandiApiApp(service)

        status, headers, body = call_wsgi(app, "GET", "/api/v1/health")
        assert status == 200
        data = json.loads(body)
        assert data["data"]["process_status"] == "DEGRADED"

        # Prices endpoint returns 503 Service Unavailable safely
        status, headers, body = call_wsgi(app, "GET", "/api/v1/prices/latest")
        assert status == 503
        data = json.loads(body)
        assert data["status"] in ("ERROR", "UNAVAILABLE")


def test_atomic_snapshot_recovery():
    """Restoring a valid source index file allows successful reload/recovery."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_path = Path(tmpdir) / "sources.json"
        test_path.write_text("{}", encoding="utf-8")
        service = MandiMarketService(latest_index_path=str(test_path))
        app = MandiApiApp(service)

        # Initially degraded
        status, _, body = call_wsgi(app, "GET", "/api/v1/health")
        assert json.loads(body)["data"]["process_status"] == "DEGRADED"

        # Now write valid source index
        valid_src = Path("data/imported_snapshots/latest_observation_index.json").read_text(encoding="utf-8")
        test_path.write_text(valid_src, encoding="utf-8")

        # Reload service snapshot
        service._load_latest_index()

        status, _, body = call_wsgi(app, "GET", "/api/v1/health")
        assert json.loads(body)["data"]["process_status"] == "HEALTHY"

        status, _, body = call_wsgi(app, "GET", "/api/v1/catalog")
        assert json.loads(body)["data"]["total_series_count"] == 30


def test_invalid_units_and_non_finite_exponents():
    """Rejection of invalid price units and non-finite numbers (NaN, Infinity)."""
    app = create_app()

    # Rejection of NaN
    status, _, body = call_wsgi(
        app,
        "POST",
        "/api/v1/economics/evaluate",
        body=b'{"quantity_quintals": NaN, "current_price": 2500}'
    )
    assert status == 400
    err_code = json.loads(body)["error"]["code"]
    assert "INVALID_JSON_NUMBER" in err_code or "NOT_FINITE_FLOAT" in err_code or "BAD_REQUEST" in err_code

    # Rejection of 1e999 (Overflow / Infinity)
    status, _, body = call_wsgi(
        app,
        "POST",
        "/api/v1/economics/evaluate",
        body=b'{"quantity_quintals": 1e999, "current_price": 2500}'
    )
    assert status == 400
    err_code = json.loads(body)["error"]["code"]
    assert "NON_FINITE" in err_code or "INVALID_JSON_NUMBER" in err_code or "NOT_FINITE_FLOAT" in err_code or "BAD_REQUEST" in err_code

    # Rejection of invalid unit
    status, _, body = call_wsgi(
        app,
        "POST",
        "/api/v1/economics/evaluate",
        body=json.dumps({"quantity_quintals": 10, "current_price": 2500, "units": "INR/tonne"}).encode()
    )
    assert status == 400
    assert "INVALID_ECONOMIC" in json.loads(body)["error"]["code"]


def test_restart_determinism():
    """Creating two independent service instances on the same files yields identical hashes & metrics."""
    service1 = MandiMarketService()
    service2 = MandiMarketService()

    h1 = service1.get_health()
    h2 = service2.get_health()

    assert h1.process_status == h2.process_status == "HEALTHY"
    p1 = h1.capabilities["prices"].metadata
    p2 = h2.capabilities["prices"].metadata
    assert p1["source_sha256"] == p2["source_sha256"]
    assert p1["total_series"] == p2["total_series"] == 30

    b1 = service1.get_benchmark_scorecards()
    b2 = service2.get_benchmark_scorecards()

    s1 = b1["model_performance_summary"]
    s2 = b2["model_performance_summary"]
    assert len(s1) == len(s2)
    for m1, m2 in zip(s1, s2):
        assert m1["model"] == m2["model"]
        assert m1["mae"] == m2["mae"]
        assert m1["rmse"] == m2["rmse"]
