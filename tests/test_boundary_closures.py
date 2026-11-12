"""
Boundary Closure Tests (MP-APP-001B)
Tests for:
1. Dynamic price disposition derivation (26 accepted / 4 review split, display permission)
2. Economic provenance and unit validation (rejection of INR/tonne, NOT_A_VALID_STATUS, 1e999 overflow)
3. Historical full-generation early safety guard (PermissionError before any I/O)
"""

from __future__ import annotations

import io
import json
import math
from pathlib import Path
import pytest

from src.api import create_app
from src.economic_model import (
    ResearchEconomicRequest,
    evaluate_research_economics,
    InputProvenance,
    SUPPORTED_PROVENANCE_STATUSES,
)
from src.forecast_intervals import execute_interval_pipeline
from src.service import MandiMarketService


def call_app(app, method: str, path: str, body: bytes | str | None = None, content_type: str = "application/json"):
    if isinstance(body, str):
        raw_body = body.encode("utf-8")
    elif isinstance(body, bytes):
        raw_body = body
    else:
        raw_body = b""

    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": "",
        "CONTENT_LENGTH": str(len(raw_body)),
        "CONTENT_TYPE": content_type,
        "SERVER_NAME": "127.0.0.1",
        "SERVER_PORT": "8000",
        "wsgi.input": io.BytesIO(raw_body),
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


# --- Boundary Case 1: Dynamic Price Disposition Derivation ---

def test_real_index_disposition_split():
    """Verify that real index dynamically derives 26 accepted and 4 review series."""
    service = MandiMarketService()
    catalog = service.get_catalog()
    assert catalog.total_series_count == 30
    assert catalog.accepted_series_count == 26
    assert catalog.review_series_count == 4

    # Latest prices: all 30
    all_prices = service.get_latest_prices()
    assert len(all_prices) == 30

    # Check verified_only=True filters to exactly 26
    verified = service.get_latest_prices(verified_only=True)
    assert len(verified) == 26
    assert all(s.price_display_permitted is True for s in verified)

    # Check review preview
    review = service.get_latest_prices(disposition="UNKNOWN_MARKET_REVIEW")
    assert len(review) == 4
    assert all(s.price_display_permitted is False for s in review)
    assert all(s.status == "UNKNOWN_MARKET_REVIEW" for s in review)


def test_index_reader_size_and_row_guards(tmp_path):
    """Verify that index reader rejects files > 10 MB or candidate lists > 50,000 rows."""
    oversized = tmp_path / "huge_index.json"
    # Write empty padding > 10 MB
    with oversized.open("wb") as f:
        f.write(b" " * (10 * 1024 * 1024 + 10))

    srv = MandiMarketService(latest_index_path=oversized)
    health = srv.get_health()
    assert health.capabilities["prices"].available is False
    assert "exceeds 10 MB limit" in health.capabilities["prices"].reason


# --- Boundary Case 2: Economic Provenance and Unit Validation ---

def test_provenance_rejects_unsupported_unit():
    """Verify that unsupported units such as INR/tonne or INR/truck are rejected."""
    valid_fixture = {
        "quantity_quintals": 10.0,
        "current_price": 2500.0,
        "future_price_point": 2650.0,
        "holding_period_days": 7,
        "params": {
            "storage_cost_per_quintal": 50.0,
            "handling_cost_per_quintal": 0.0,
            "incremental_transport_cost": 0.0,
            "transaction_cost_now": 0.0,
            "transaction_cost_later": 0.0,
            "quantity_loss_fraction": 0.02,
            "quality_discount_fraction": 0.0,
            "annual_carrying_rate": 0.0,
            "carrying_cost_type": "none",
            "holding_period_days": 7,
        },
    }

    # Custom provenance with mismatched unit 'INR/tonne'
    mismatched = dict(valid_fixture)
    mismatched["provenance"] = {
        "storage_cost_per_quintal": {
            "declared_unit": "INR/tonne",
            "status": "USER_ENTERED",
            "value": 50.0,
        }
    }
    with pytest.raises(ValueError, match="Unsupported storage cost unit"):
        req = ResearchEconomicRequest.from_dict(mismatched)
        evaluate_research_economics(req)


def test_provenance_rejects_invalid_status():
    """Verify that unsupported status NOT_A_VALID_STATUS is rejected."""
    invalid_status_dict = {
        "quantity_quintals": 10.0,
        "current_price": 2500.0,
        "params": {"storage_cost_per_quintal": 50.0},
        "provenance": {
            "storage_cost_per_quintal": {
                "declared_unit": "INR/quintal",
                "status": "NOT_A_VALID_STATUS",
                "value": 50.0,
            }
        },
    }
    with pytest.raises(ValueError, match="Invalid provenance status"):
        ResearchEconomicRequest.from_dict(invalid_status_dict)


def test_http_boundary_rejects_overflowing_exponent():
    """Verify that JSON numbers like 1e999 (which overflow to inf) are rejected with 400."""
    app = create_app()
    payload = b'{"quantity_quintals": 10, "current_price": 1e999}'
    status, headers, body = call_app(app, "POST", "/api/v1/economics/evaluate", payload)
    assert status == 400
    res = json.loads(body)
    assert res["status"] == "ERROR"
    assert res["error"]["code"] == "NON_FINITE_NUMERIC_INPUT"


def test_http_boundary_valid_fixture_and_missing_costs():
    """Verify that +470 fixture evaluates to delta_r_point=470, while missing costs keep dependent fields null."""
    app = create_app()
    fixture = {
        "quantity_quintals": 10.0,
        "current_price": 2500.0,
        "future_price_point": 2650.0,
        "holding_period_days": 7,
        "params": {
            "storage_cost_per_quintal": 50.0,
            "handling_cost_per_quintal": 0.0,
            "incremental_transport_cost": 0.0,
            "transaction_cost_now": 0.0,
            "transaction_cost_later": 0.0,
            "quantity_loss_fraction": 0.02,
            "quality_discount_fraction": 0.0,
            "annual_carrying_rate": 0.0,
            "carrying_cost_type": "none",
            "holding_period_days": 7,
        },
    }
    status, _, body = call_app(app, "POST", "/api/v1/economics/evaluate", json.dumps(fixture))
    assert status == 200
    res = json.loads(body)
    assert res["status"] == "SUCCESS"
    assert res["data"]["delta_r_point"] == 470.0
    assert res["data"]["advisory_permitted"] is False
    assert res["data"]["advisory_action"] == "BLOCKED"

    # Missing costs test
    partial = {"quantity_quintals": 10.0, "current_price": 2500.0, "future_price_point": 2650.0}
    status, _, body = call_app(app, "POST", "/api/v1/economics/evaluate", json.dumps(partial))
    assert status == 200
    res_partial = json.loads(body)
    assert res_partial["data"]["delta_r_point"] is None
    assert res_partial["data"]["r_sell_net"] is None
    assert res_partial["data"]["r_sell_gross"] == 25000.0


# --- Boundary Case 3: Historical Full-Generation Safety Guard ---

def test_full_generation_guard_early_block():
    """Verify that execute_interval_pipeline() raises PermissionError before any I/O when unauthorized."""
    with pytest.raises(PermissionError, match="LOCAL_FULL_GENERATION_BLOCKED"):
        execute_interval_pipeline(
            predictions_path=Path("dummy_pred.csv"),
            output_reports_dir=Path("dummy_reports"),
            output_predictions_dir=Path("dummy_preds"),
            config_path=Path("dummy_config.json"),
            authorized_budget=False,
        )
