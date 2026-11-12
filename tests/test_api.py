"""
WSGI HTTP API Adapter Tests and Loopback Smoke Test (MP-APP-001A)
APMC Mandi Intelligence System - Step 10 Backend
Exercises pure-standard-library WSGI application directly and through a real loopback HTTP server.
"""

from datetime import datetime
import http.client
import io
import json
from pathlib import Path
import threading
import time
from typing import Any, Dict, Tuple
from wsgiref.simple_server import make_server
import pytest

from src.api import create_app
from src.service import MandiMarketService


def call_wsgi_app(
    app,
    method: str,
    path: str,
    query_string: str = "",
    body: Optional[bytes] = None,
    content_type: str = "application/json",
) -> Tuple[int, Dict[str, str], Dict[str, Any]]:
    """Helper to invoke WSGI application directly without a socket."""
    body_bytes = body or b""
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query_string,
        "CONTENT_LENGTH": str(len(body_bytes)),
        "CONTENT_TYPE": content_type,
        "wsgi.input": io.BytesIO(body_bytes),
        "SERVER_NAME": "localhost",
        "SERVER_PORT": "80",
        "wsgi.version": (1, 0),
        "wsgi.url_scheme": "http",
    }
    response_status = [200]
    response_headers = [{}]

    def start_response(status, headers, exc_info=None):
        code = int(status.split()[0])
        response_status[0] = code
        response_headers[0] = dict(headers)

    chunks = app(environ, start_response)
    resp_body = b"".join(chunks).decode("utf-8")
    parsed_json = json.loads(resp_body) if resp_body else {}
    return response_status[0], response_headers[0], parsed_json


class TestWsgiApiEndpoints:
    """Verifies WSGI routing, serialization, error codes, and request validation."""

    @pytest.fixture
    def app(self, tmp_path):
        from pathlib import Path
        default_p = Path("data/imported_snapshots/latest_observation_index.json")
        if default_p.exists():
            service = MandiMarketService(latest_index_path=default_p)
        else:
            sample_series = {}
            districts = ["Ghaziabad", "Jhansi", "Kanpur", "Lucknow", "Unnao"]
            commodities = ["Wheat", "Potato", "Rice", "Paddy(Common)", "Tomato", "Onion"]
            for d in districts:
                for c in commodities:
                    sid = f"{c}_{d}_mkt_Common_FAQ"
                    sample_series[sid] = {
                        "district": d,
                        "market_canonical": f"{d} Mandi",
                        "market_raw": f"{d} Mandi",
                        "commodity": c,
                        "variety": "Common",
                        "grade": "FAQ",
                        "latest_observation_date": "2026-11-11",
                        "modal_price": 2000.0,
                        "min_price": 1900.0,
                        "max_price": 2100.0,
                        "price_unit": "Rs./Quintal",
                        "market_alias_status": "ACCEPTED",
                        "status": "ACCEPTED",
                        "is_import_verified": True,
                    }
            p = tmp_path / "latest_observation_index.json"
            p.write_text(json.dumps({
                "index_version": "1.0.0",
                "generated_at_utc": "2026-11-11T18:00:00Z",
                "total_series_indexed": len(sample_series),
                "composite_source_sha256": "clean_checkout_fixture_hash",
                "series": sample_series,
            }))
            service = MandiMarketService(latest_index_path=p)
        return create_app(service)

    def test_health_endpoint_get(self, app):
        status, headers, body = call_wsgi_app(app, "GET", "/api/v1/health")
        assert status == 200
        assert headers["Content-Type"].startswith("application/json")
        assert body["status"] == "SUCCESS"
        assert body["data"]["process_status"] == "HEALTHY"
        assert "prices" in body["data"]["capabilities"]

    def test_catalog_endpoint_get(self, app):
        status, headers, body = call_wsgi_app(app, "GET", "/api/v1/catalog")
        assert status == 200
        assert body["status"] == "SUCCESS"
        assert body["data"]["total_series_count"] == 30
        assert "Wheat" in body["data"]["focus_crops"]

    def test_latest_prices_endpoint_get(self, app):
        status, headers, body = call_wsgi_app(app, "GET", "/api/v1/prices/latest", "commodity=Wheat")
        assert status == 200
        assert body["status"] == "SUCCESS"
        assert body["data"]["total_matching_series"] >= 1
        series = body["data"]["series"]
        assert all(s["commodity"] == "Wheat" for s in series)
        assert all(s["data_mode"] == "FILE_IMPORT" for s in series)
        assert all(s["is_live_verified"] is False for s in series)

    def test_price_history_endpoint_honest_unavailable(self, app):
        status, headers, body = call_wsgi_app(app, "GET", "/api/v1/prices/history")
        assert status == 200
        assert body["status"] == "UNAVAILABLE"
        assert body["data"]["status"] == "HISTORY_UNAVAILABLE"

    def test_models_benchmark_endpoint_get(self, app):
        status, headers, body = call_wsgi_app(app, "GET", "/api/v1/models/benchmark")
        assert status == 200
        assert body["status"] == "SUCCESS"
        assert body["data"]["primary_benchmark_model"] == "naive_persistence"

    def test_forecast_endpoint_post_unavailable(self, app):
        req_payload = json.dumps({
            "district": "Lucknow",
            "market": "Lucknow",
            "commodity": "Wheat",
            "horizon_days": 7,
        }).encode("utf-8")
        status, headers, body = call_wsgi_app(app, "POST", "/api/v1/forecast", body=req_payload)
        assert status == 200
        assert body["status"] == "UNAVAILABLE"
        assert body["data"]["forecast_status"] == "FORECAST_UNAVAILABLE"
        assert body["data"]["advisory_action"] == "BLOCKED"

    def test_economics_endpoint_post_incomplete_params(self, app):
        req_payload = json.dumps({
            "quantity_quintals": 1.0,
            "current_price": 2000.0,
            "future_price_point": 2200.0,
        }).encode("utf-8")
        status, headers, body = call_wsgi_app(app, "POST", "/api/v1/economics/evaluate", body=req_payload)
        assert status == 200
        assert body["status"] == "SUCCESS"
        assert body["data"]["break_even_relation"] == "INCOMPLETE_PARAMETERS"
        assert body["data"]["r_hold_point_net"] is None
        assert body["data"]["advisory_action"] == "BLOCKED"

    def test_method_not_allowed_on_mismatched_verbs(self, app):
        # POST to GET-only endpoint
        status, _, body = call_wsgi_app(app, "POST", "/api/v1/health")
        assert status == 405
        assert body["error"]["code"] == "METHOD_NOT_ALLOWED"

        # GET to POST-only endpoint
        status, _, body = call_wsgi_app(app, "GET", "/api/v1/forecast")
        assert status == 405
        assert body["error"]["code"] == "METHOD_NOT_ALLOWED"

    def test_not_found_on_unknown_route(self, app):
        status, _, body = call_wsgi_app(app, "GET", "/api/v1/nonexistent_route")
        assert status == 404
        assert body["error"]["code"] == "NOT_FOUND"

    def test_malformed_json_returns_400(self, app):
        bad_json = b"{\"unclosed_json: "
        status, _, body = call_wsgi_app(app, "POST", "/api/v1/economics/evaluate", body=bad_json)
        assert status == 400
        assert "INVALID_JSON" in body["error"]["code"]

    def test_invalid_economic_domain_returns_400(self, app):
        bad_req = json.dumps({
            "quantity_quintals": -10.0,  # Negative quantity rejected
            "current_price": 2000.0,
        }).encode("utf-8")
        status, _, body = call_wsgi_app(app, "POST", "/api/v1/economics/evaluate", body=bad_req)
        assert status == 400
        assert body["error"]["code"] == "INVALID_ECONOMIC_PARAMETERS"

    def test_text_plain_content_type_rejected(self, app):
        status, _, body = call_wsgi_app(
            app,
            "POST",
            "/api/v1/economics/evaluate",
            body=b"quantity_quintals=1",
            content_type="text/plain",
        )
        assert status in (400, 415)
        assert body["status"] == "ERROR"

    def test_nan_in_json_body_rejected(self, app):
        status, _, body = call_wsgi_app(
            app,
            "POST",
            "/api/v1/economics/evaluate",
            body=b'{"quantity_quintals": NaN, "current_price": 2000.0}',
            content_type="application/json",
        )
        assert status == 400
        assert body["status"] == "ERROR"

    def test_negative_horizon_rejected(self, app):
        status, _, body = call_wsgi_app(
            app,
            "POST",
            "/api/v1/forecast",
            body=b'{"district": "Lucknow", "market": "Lucknow", "commodity": "Wheat", "horizon_days": -1}',
            content_type="application/json",
        )
        assert status == 400
        assert body["status"] == "ERROR"

    def test_empty_economics_body_rejected(self, app):
        status, _, body = call_wsgi_app(
            app,
            "POST",
            "/api/v1/economics/evaluate",
            body=b"",
            content_type="application/json",
        )
        assert status == 400
        assert body["status"] == "ERROR"


class TestRealLoopbackHttpSmoke:
    """
    Real Loopback HTTP Smoke Test.
    Binds strictly to loopback (127.0.0.1) on an ephemeral port.
    Executes actual TCP requests over http.client and shuts down cleanly in finally block.
    """

    def test_real_loopback_get_and_post_smoke(self, tmp_path):
        default_p = Path("data/imported_snapshots/latest_observation_index.json")
        if default_p.exists():
            service = MandiMarketService(latest_index_path=default_p)
        else:
            sample_series = {}
            districts = ["Ghaziabad", "Jhansi", "Kanpur", "Lucknow", "Unnao"]
            commodities = ["Wheat", "Potato", "Rice", "Paddy(Common)", "Tomato", "Onion"]
            for d in districts:
                for c in commodities:
                    sid = f"{c}_{d}_mkt_Common_FAQ"
                    sample_series[sid] = {
                        "district": d,
                        "market_canonical": f"{d} Mandi",
                        "market_raw": f"{d} Mandi",
                        "commodity": c,
                        "variety": "Common",
                        "grade": "FAQ",
                        "latest_observation_date": "2026-11-11",
                        "modal_price": 2000.0,
                        "min_price": 1900.0,
                        "max_price": 2100.0,
                        "price_unit": "Rs./Quintal",
                        "market_alias_status": "ACCEPTED",
                        "status": "ACCEPTED",
                        "is_import_verified": True,
                    }
            p = tmp_path / "latest_observation_index.json"
            p.write_text(json.dumps({
                "index_version": "1.0.0",
                "generated_at_utc": "2026-11-11T18:00:00Z",
                "total_series_indexed": len(sample_series),
                "composite_source_sha256": "clean_checkout_fixture_hash",
                "series": sample_series,
            }))
            service = MandiMarketService(latest_index_path=p)
        app = create_app(service)

        # Bind to 127.0.0.1 on ephemeral port (port 0 selects free port)
        server = make_server("127.0.0.1", 0, app)
        host, port = server.server_address
        assert host == "127.0.0.1", "Must bind strictly to loopback"

        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        try:
            # 1. Test GET /api/v1/health
            t0 = time.time()
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            conn.request("GET", "/api/v1/health")
            resp = conn.getresponse()
            d_health = (time.time() - t0) * 1000.0

            assert resp.status == 200
            data_health = json.loads(resp.read().decode("utf-8"))
            assert data_health["status"] == "SUCCESS"
            assert data_health["data"]["process_status"] == "HEALTHY"
            conn.close()

            # 2. Test GET /api/v1/prices/latest?commodity=Wheat
            t0 = time.time()
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            conn.request("GET", "/api/v1/prices/latest?commodity=Wheat")
            resp = conn.getresponse()
            d_prices = (time.time() - t0) * 1000.0

            assert resp.status == 200
            data_prices = json.loads(resp.read().decode("utf-8"))
            assert data_prices["status"] == "SUCCESS"
            assert data_prices["data"]["total_matching_series"] >= 1
            conn.close()

            # 3. Test POST /api/v1/economics/evaluate
            t0 = time.time()
            econ_body = json.dumps({
                "quantity_quintals": 1.0,
                "current_price": 2000.0,
                "future_price_point": 2200.0,
            })
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            headers = {"Content-Type": "application/json"}
            conn.request("POST", "/api/v1/economics/evaluate", body=econ_body, headers=headers)
            resp = conn.getresponse()
            d_econ = (time.time() - t0) * 1000.0

            assert resp.status == 200
            data_econ = json.loads(resp.read().decode("utf-8"))
            assert data_econ["status"] == "SUCCESS"
            assert data_econ["data"]["break_even_relation"] == "INCOMPLETE_PARAMETERS"
            assert data_econ["data"]["r_hold_point_net"] is None
            conn.close()

            print(f"\n[HTTP Smoke] /health: {d_health:.2f}ms | /prices/latest: {d_prices:.2f}ms | /economics: {d_econ:.2f}ms")

        finally:
            # Clean server shutdown guaranteed
            server.shutdown()
            server.server_close()
            server_thread.join(timeout=2)
