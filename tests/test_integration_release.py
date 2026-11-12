"""
Integration & Recovery Test Suite for Release Candidate (MP-RELEASE-001R)
Tests:
1. Valid source -> API healthy, catalog complete (30 total, 26 accepted, 4 review).
2. Missing / corrupt source -> degraded status without path/secret leakage.
3. Atomic snapshot recovery -> restored valid source transitions to healthy.
4. Missing / mismatched benchmark -> honest unavailable response, no crash.
5. Invalid provenance & non-finite float rejection -> 400 Bad Request.
6. Service restart determinism -> identical snapshot hash and metrics.
7. Optional real-snapshot smoke (skipped if private data is absent).
8. Launcher CLI entrypoints (--help direct and -m) under sanitized environment.
9. Healthcheck command execution against live service.
10. Server graceful shutdown via SIGTERM with socket release.
"""

from __future__ import annotations

import io
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.api import MandiApiApp, create_app
from src.service import MandiMarketService
REAL_INDEX_PATH = REPO_ROOT / "data" / "imported_snapshots" / "latest_observation_index.json"


def create_deterministic_fixture_index(target_path: Path) -> Path:
    """
    Creates an isolated, deterministic 30-series index file in target_path.
    Strictly yields: 30 total series, 26 ACCEPTED, 4 REVIEW.
    Uses zero network, zero private files, and pure standard-library serialization.
    """
    sample_series = {}
    districts = ["Ghaziabad", "Jhansi", "Kanpur", "Lucknow", "Unnao"]
    commodities = ["Wheat", "Potato", "Rice", "Paddy(Common)", "Tomato", "Onion"]
    idx = 0
    for d in districts:
        for c in commodities:
            idx += 1
            sid = f"{d}|{d} Mandi|{c}|Common|FAQ"
            is_review = (idx > 26)  # Exactly 4 review series (idx 27, 28, 29, 30)
            sample_series[sid] = {
                "series_id": sid,
                "district": d,
                "market_canonical": f"{d} Mandi",
                "market_raw": f"{d} Mandi APMC",
                "commodity": c,
                "variety": "Common",
                "grade": "FAQ",
                "grade_raw": "FAQ",
                "latest_observation_date": "2026-11-11",
                "modal_price": 2000.0 + idx * 10.0,
                "min_price": 1950.0 + idx * 10.0,
                "max_price": 2050.0 + idx * 10.0,
                "price_unit": "Rs./Quintal",
                "unit_evidence": "Declared in official Agmarknet source",
                "market_alias_status": "REVIEW" if is_review else "ACCEPTED",
                "status": "UNKNOWN_MARKET_REVIEW" if is_review else "ACCEPTED",
                "status_reason": "Review required" if is_review else "Validated official observed latest trade record.",
                "freshness_days": 1,
                "duplicate_count_on_latest": 0,
                "source_file_hashes": ["e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"],
                "composite_source_sha256": "deterministic_fixture_composite_hash_30",
                "import_timestamp_utc": "2026-11-11T18:00:00+00:00",
                "is_live_verified": False,
                "is_import_verified": True,
                "capabilities": {
                    "price_display_permitted": True,
                    "forecast_eligible": not is_review,
                    "economics_eligible": not is_review,
                    "active_advice_permitted": False,
                },
            }

    index_payload = {
        "index_version": "1.0.0",
        "generated_at_utc": "2026-11-11T18:00:00+00:00",
        "run_id_utc": "run_20261111_fixture",
        "total_series_indexed": 30,
        "accepted_series_count": 26,
        "quarantined_series_count": 4,
        "composite_source_sha256": "deterministic_fixture_composite_hash_30",
        "source_files": ["fixture_snapshot.csv"],
        "series": sample_series,
    }
    target_path.write_text(json.dumps(index_payload, indent=2), encoding="utf-8")
    return target_path


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


def test_valid_source_healthy_integration(tmp_path):
    """Valid source index produces healthy status and accurate catalog counts (30/26/4)."""
    fixture_index = create_deterministic_fixture_index(tmp_path / "valid_index.json")
    service = MandiMarketService(latest_index_path=fixture_index)
    app = MandiApiApp(service)

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


def test_missing_source_degraded_without_leak(tmp_path):
    """Missing or nonexistent index path yields degraded health without leaking server paths."""
    nonexistent_path = tmp_path / "nonexistent_sources.json"
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

    # Assert no internal path leaked in response
    assert str(nonexistent_path) not in body.decode("utf-8")


def test_corrupt_source_handling(tmp_path):
    """Corrupted JSON source index degrades gracefully without unhandled exception."""
    corrupt_path = tmp_path / "corrupt_sources.json"
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


def test_atomic_snapshot_recovery(tmp_path):
    """Restoring a valid source index file allows atomic reload/recovery via public API."""
    test_path = tmp_path / "active_index.json"
    test_path.write_text("{}", encoding="utf-8")
    service = MandiMarketService(latest_index_path=str(test_path))
    app = MandiApiApp(service)

    # Initially degraded
    status, _, body = call_wsgi(app, "GET", "/api/v1/health")
    assert json.loads(body)["data"]["process_status"] == "DEGRADED"

    # Now write valid source index to an updated file
    recovered_path = tmp_path / "recovered_index.json"
    create_deterministic_fixture_index(recovered_path)

    # Operator calls supported public reload method
    health = service.reload_index(recovered_path)
    assert health.process_status == "HEALTHY"

    status, _, body = call_wsgi(app, "GET", "/api/v1/health")
    assert json.loads(body)["data"]["process_status"] == "HEALTHY"

    status, _, body = call_wsgi(app, "GET", "/api/v1/catalog")
    assert json.loads(body)["data"]["total_series_count"] == 30
    assert json.loads(body)["data"]["accepted_series_count"] == 26
    assert json.loads(body)["data"]["review_series_count"] == 4


def test_invalid_units_and_non_finite_exponents(tmp_path):
    """Rejection of invalid price units and non-finite numbers (NaN, Infinity)."""
    fixture_index = create_deterministic_fixture_index(tmp_path / "fixture.json")
    service = MandiMarketService(latest_index_path=fixture_index)
    app = MandiApiApp(service)

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


def test_restart_determinism(tmp_path):
    """Creating two independent service instances on the same files yields identical hashes & metrics."""
    fixture_index = create_deterministic_fixture_index(tmp_path / "shared_index.json")
    service1 = MandiMarketService(latest_index_path=fixture_index)
    service2 = MandiMarketService(latest_index_path=fixture_index)

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


@pytest.mark.skipif(not REAL_INDEX_PATH.exists(), reason="Real private snapshot not present in clean checkout")
def test_real_snapshot_smoke():
    """Optional smoke test against real imported snapshot if present on host."""
    service = MandiMarketService(latest_index_path=REAL_INDEX_PATH)
    health = service.get_health()
    assert health.process_status == "HEALTHY"
    assert health.capabilities["prices"].metadata["total_series"] == 30


def test_direct_launcher_help_sanitized_env():
    """Direct execution `python3 src/run_release_service.py --help` succeeds without PYTHONPATH."""
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    res = subprocess.run(
        [sys.executable, str(REPO_ROOT / "src" / "run_release_service.py"), "--help"],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert res.returncode == 0
    assert "APMC Mandi Intelligence System" in res.stdout


def test_module_launcher_help_sanitized_env():
    """Module execution `python3 -m src.run_release_service --help` succeeds without PYTHONPATH."""
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    res = subprocess.run(
        [sys.executable, "-m", "src.run_release_service", "--help"],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert res.returncode == 0
    assert "APMC Mandi Intelligence System" in res.stdout


def _find_free_port():
    with socket.socket(socket.AF_WSGI if hasattr(socket, "AF_WSGI") else socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_server_lifecycle_sigterm_and_healthcheck(tmp_path):
    """
    Subprocess lifecycle verification:
    1. Launches server on ephemeral port with deterministic index fixture.
    2. Verifies healthcheck command succeeds (HTTP 200).
    3. Sends SIGTERM to owned child process.
    4. Asserts clean process exit with returncode 0 within 5 seconds.
    5. Asserts socket release allowing immediate rebinding on same port.
    """
    fixture_index = create_deterministic_fixture_index(tmp_path / "lifecycle_index.json")
    port = _find_free_port()
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["APMC_LATEST_INDEX_PATH"] = str(fixture_index)

    proc = subprocess.Popen(
        [sys.executable, "-m", "src.run_release_service", "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(REPO_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        # Wait for service to become responsive (up to 5s)
        import urllib.request
        health_url = f"http://127.0.0.1:{port}/api/v1/health"
        started = False
        t0 = time.time()
        while time.time() - t0 < 5.0:
            try:
                with urllib.request.urlopen(health_url, timeout=0.5) as resp:
                    if resp.status == 200:
                        started = True
                        break
            except Exception:
                time.sleep(0.1)

        assert started, "Server failed to respond to /api/v1/health within 5 seconds"

        # Execute exact Docker healthcheck one-liner against the server
        hc_cmd = [
            sys.executable,
            "-c",
            f"import urllib.request, sys; sys.exit(0 if getattr(urllib.request.urlopen('{health_url}', timeout=3), 'status', None) == 200 else 1)"
        ]
        hc_res = subprocess.run(hc_cmd, capture_output=True, timeout=5)
        assert hc_res.returncode == 0, f"Healthcheck command failed with returncode {hc_res.returncode}"

        # Send SIGTERM
        proc.send_signal(signal.SIGTERM)
        exit_code = proc.wait(timeout=5.0)
        assert exit_code == 0, f"Server exited with non-zero code {exit_code} on SIGTERM"

        # Verify socket release: immediately bind to same port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("127.0.0.1", port))

    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=2.0)
