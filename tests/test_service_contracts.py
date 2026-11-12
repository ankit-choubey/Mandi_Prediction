"""
Unit Tests for Service Layer and Contracts (MP-APP-001A)
APMC Mandi Intelligence System - Step 10 Backend
"""

from datetime import date, datetime, timedelta, timezone
import json
import math
import pytest

from src.service_contracts import (
    dumps_strict_json,
    safe_json_serialize,
    ServiceEnvelope,
    ServiceError,
    ServiceStatus,
    PriceSeriesRecord,
    CatalogData,
    HealthResponseData,
    ForecastServiceRequest,
    ForecastServiceResult,
)
from src.service import MandiMarketService, IST_TZ
from src.economic_model import EconomicParameters


class TestServiceContractsSerialization:
    """Verifies strict JSON serialization and data contracts."""

    def test_strict_json_replaces_nan_with_null(self):
        payload = {
            "valid_number": 2000.5,
            "nan_value": float("nan"),
            "inf_value": float("inf"),
            "string_val": "Lucknow",
        }
        res_json = dumps_strict_json(payload)
        parsed = json.loads(res_json)
        assert parsed["valid_number"] == 2000.5
        assert parsed["nan_value"] is None
        assert parsed["inf_value"] is None
        assert parsed["string_val"] == "Lucknow"

    def test_service_envelope_serialization(self):
        env = ServiceEnvelope(
            status=ServiceStatus.SUCCESS.value,
            data={"test_key": "test_value"},
        )
        res_json = dumps_strict_json(env.to_dict())
        parsed = json.loads(res_json)
        assert parsed["schema_version"] == "1.0.0"
        assert parsed["status"] == "SUCCESS"
        assert parsed["data"]["test_key"] == "test_value"
        assert parsed["error"] is None
        assert len(parsed["request_id"]) > 0


class TestMandiMarketService:
    """Verifies service business logic, data isolation, and dynamic calculations."""

    @pytest.fixture
    def service(self):
        return MandiMarketService()

    def test_health_endpoint_capability_matrix(self, service):
        health = service.get_health()
        assert health.process_status == "HEALTHY"
        assert health.uptime_seconds >= 0.0

        caps = health.capabilities
        assert "prices" in caps
        assert caps["prices"].available is True
        assert caps["prices"].status == "AVAILABLE"
        assert caps["prices"].metadata["total_series"] == 30

        assert "history" in caps
        assert caps["history"].available is False
        assert caps["history"].status == "UNAVAILABLE_RESTRICTED"

        assert "benchmarks" in caps
        assert caps["benchmarks"].available is True

        assert "forecast" in caps
        assert caps["forecast"].available is False
        assert "NO_APPROVED_SERVING_MODEL_ARTIFACT" in caps["forecast"].reason

        assert "economics" in caps
        assert caps["economics"].available is True
        assert caps["economics"].status == "RESEARCH_ONLY"

        assert "active_advice" in caps
        assert caps["active_advice"].available is False
        assert caps["active_advice"].status == "BLOCKED"

    def test_catalog_preserves_rice_vs_paddy_distinctly(self, service):
        catalog = service.get_catalog()
        assert catalog.total_series_count == 30
        assert "Ghaziabad" in catalog.districts
        assert "Jhansi" in catalog.districts
        assert "Kanpur" in catalog.districts
        assert "Lucknow" in catalog.districts
        assert "Unnao" in catalog.districts

        # Focus crops
        assert "Wheat" in catalog.focus_crops
        assert "Potato" in catalog.focus_crops
        assert "Rice" in catalog.focus_crops
        assert "Paddy(Common)" in catalog.focus_crops or "Paddy(Dhan)(Common)" in catalog.focus_crops

        # Rice and Paddy must be separate entries
        rice_series = [s for s in catalog.series_inventory if s["commodity"].lower() == "rice"]
        paddy_series = [s for s in catalog.series_inventory if "paddy" in s["commodity"].lower()]
        assert len(paddy_series) > 0, "Paddy series must be indexed"

    def test_latest_prices_queries_and_dynamic_age_calculation(self, service):
        # Query Lucknow Wheat
        prices = service.get_latest_prices(commodity="Wheat", district="Lucknow")
        assert len(prices) >= 1
        rec = prices[0]
        assert rec.district == "Lucknow"
        assert rec.commodity == "Wheat"
        assert rec.data_mode == "FILE_IMPORT"
        assert rec.is_live_verified is False
        assert rec.is_import_verified is True

        # Dynamic age check
        server_today = datetime.now(IST_TZ).date()
        obs_d = datetime.strptime(rec.observation_date[:10], "%Y-%m-%d").date()
        expected_age = (server_today - obs_d).days
        assert rec.age_days == expected_age

    def test_price_history_returns_honest_unavailable_without_raw_scan(self, service):
        hist = service.get_price_history(district="Lucknow", commodity="Wheat", page=1, page_size=20)
        assert hist["status"] == "HISTORY_UNAVAILABLE"
        assert hist["total_available"] == 0
        assert len(hist["records"]) == 0

        # Invalid pagination raises ValueError
        with pytest.raises(ValueError, match="page must be positive integer"):
            service.get_price_history(page=0)

        with pytest.raises(ValueError, match="page_size must be between 1 and 100"):
            service.get_price_history(page_size=500)

    def test_benchmark_scorecards_truthful_metrics(self, service):
        bench = service.get_benchmark_scorecards()
        assert bench["primary_benchmark_model"] == "naive_persistence"
        summary = {m["model"]: m for m in bench["model_performance_summary"]}

        # Persistence beats HGB on MAE
        assert summary["naive_persistence"]["mae"] == 106.96
        assert summary["hist_gradient_boosting"]["mae"] == 109.75
        assert summary["ridge_regression"]["mae"] == 110.32
        assert summary["naive_persistence"]["mae"] < summary["hist_gradient_boosting"]["mae"]

        # HGB improves RMSE
        assert summary["hist_gradient_boosting"]["rmse_improvement_vs_persistence_pct"] == 5.91

        # Crisis fold undercoverage
        f3_f4 = bench["fold_level_breakdown_naive_90"]
        assert f3_f4["F3"]["coverage_pct"] == 75.94
        assert f3_f4["F4"]["coverage_pct"] == 72.26

    def test_forecast_endpoint_unavailable_fail_closed(self, service):
        req = ForecastServiceRequest(
            district="Lucknow",
            market="Lucknow",
            commodity="Wheat",
            horizon_days=7,
        )
        res = service.evaluate_forecast(req)
        assert res.forecast_status == "FORECAST_UNAVAILABLE"
        assert res.point_forecast is None
        assert res.advisory_action == "BLOCKED"
        assert res.advisory_permitted is False

    def test_economics_endpoint_delegation(self, service):
        # Incomplete request with missing params
        incomplete_res = service.evaluate_economics({"quantity_quintals": 10.0, "current_price": 2000.0})
        assert incomplete_res["break_even_relation"] == "INCOMPLETE_PARAMETERS"
        assert incomplete_res["r_hold_point_net"] is None
        assert incomplete_res["advisory_action"] == "BLOCKED"

        # Complete request with explicit parameters
        complete_res = service.evaluate_economics({
            "quantity_quintals": 10.0,
            "current_price": 2000.0,
            "future_price_point": 2200.0,
            "future_price_lower": 2150.0,
            "future_price_upper": 2300.0,
            "params": {
                "storage_cost_per_quintal": 20.0,
                "quantity_loss_fraction": 0.01,
                "annual_carrying_rate": 0.07,
                "holding_period_days": 7,
            },
        })
        assert complete_res["break_even_relation"] in ("ENTIRELY_ABOVE_BREAK_EVEN", "STRADDLES_BREAK_EVEN")
        assert complete_res["r_hold_point_net"] is not None
        assert complete_res["advisory_action"] == "BLOCKED"
