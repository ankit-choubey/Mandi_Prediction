"""
Mandi Market Service Layer (MP-APP-001A)
APMC Mandi Intelligence System - Step 10 Dataset-First Backend
Implements business logic separating storage readers, freshness calculation,
scorecard reporting, forecast gating, and research economics.
"""

from __future__ import annotations

from datetime import datetime, date, timezone, timedelta
import json
import math
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple

from src.service_contracts import (
    ServiceStatus,
    ServiceError,
    ServiceEnvelope,
    ServiceCapability,
    HealthResponseData,
    PriceSeriesRecord,
    CatalogData,
    ForecastServiceRequest,
    ForecastServiceResult,
)
from src.economic_model import (
    EconomicParameters,
    ResearchEconomicRequest,
    ResearchEconomicResult,
    evaluate_research_economics,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

# Official Focus Crops & Districts per master specification
DECLARED_FOCUS_CROPS = [
    "Wheat",
    "Potato",
    "Onion",
    "Tomato",
    "Paddy(Common)",
    "Paddy(Dhan)(Common)",
    "Rice",
]

# Asia/Kolkata timezone offset (UTC+05:30)
IST_TZ = timezone(timedelta(hours=5, minutes=30))


class MandiMarketService:
    """
    High-integrity market intelligence service implementing dataset-first capabilities:
    - Dynamic observation age recomputed using Asia/Kolkata date policy.
    - Zero synthetic data generation and fail-closed advisory gating.
    - Preserves distinct Rice versus Paddy series identities.
    - Audited benchmark scorecards and honest unavailable responses.
    """

    def __init__(
        self,
        latest_index_path: Optional[Path | str] = None,
        calibration_envelope_path: Optional[Path | str] = None,
    ):
        self.start_time = time.time()
        self.start_datetime_utc = datetime.now(timezone.utc)

        self.latest_index_path = Path(latest_index_path) if latest_index_path else (
            REPO_ROOT / "data" / "imported_snapshots" / "latest_observation_index.json"
        )
        self.calibration_envelope_path = Path(calibration_envelope_path) if calibration_envelope_path else (
            REPO_ROOT / "experiments" / "reports" / "FC008" / "calibration_envelope_v1.json"
        )

        self.index_loaded = False
        self.index_error: Optional[str] = None
        self.index_metadata: Dict[str, Any] = {}
        self.series_data: Dict[str, Dict[str, Any]] = {}

        self._load_latest_index()

    def _load_latest_index(self) -> None:
        """Loads and indexes latest market observations without swallowing errors."""
        if not self.latest_index_path.exists():
            self.index_loaded = False
            self.index_error = f"Index file not found: {self.latest_index_path}"
            return

        try:
            with open(self.latest_index_path, "r", encoding="utf-8") as f:
                payload = json.load(f)

            self.index_metadata = {
                "index_version": payload.get("index_version", "1.0.0"),
                "generated_at_utc": payload.get("generated_at_utc"),
                "total_series_indexed": payload.get("total_series_indexed", 0),
                "composite_source_sha256": payload.get("composite_source_sha256"),
            }
            self.series_data = payload.get("series", {})
            self.index_loaded = True
            self.index_error = None
        except Exception as e:
            self.index_loaded = False
            self.index_error = f"Failed to parse index JSON: {str(e)}"
            self.series_data = {}

    def get_server_date_ist(self) -> date:
        """Computes current date under Asia/Kolkata date policy."""
        return datetime.now(IST_TZ).date()

    def get_health(self) -> HealthResponseData:
        """
        Health and capability readiness inspection.
        Distinguishes running process from availability of individual capabilities.
        """
        now_utc = datetime.now(timezone.utc)
        now_ist = datetime.now(IST_TZ)
        uptime = time.time() - self.start_time

        capabilities: Dict[str, ServiceCapability] = {}

        # 1. Prices capability
        if self.index_loaded:
            capabilities["prices"] = ServiceCapability(
                available=True,
                status="AVAILABLE",
                metadata={
                    "total_series": len(self.series_data),
                    "index_version": self.index_metadata.get("index_version"),
                    "generated_at_utc": self.index_metadata.get("generated_at_utc"),
                    "source_sha256": self.index_metadata.get("composite_source_sha256"),
                },
            )
        else:
            capabilities["prices"] = ServiceCapability(
                available=False,
                status="DEGRADED",
                reason=self.index_error or "Market price index unavailable",
            )

        # 2. History capability
        capabilities["history"] = ServiceCapability(
            available=False,
            status="UNAVAILABLE_RESTRICTED",
            reason="Full panel local scans restricted; historical time-series queries require configured snapshots.",
        )

        # 3. Model Benchmark capability
        capabilities["benchmarks"] = ServiceCapability(
            available=True,
            status="AVAILABLE",
            metadata={
                "primary_model": "naive_persistence",
                "verified_mae": 106.96,
                "hgb_rmse_improvement_pct": 5.91,
                "nominal_coverage_90_pct": 89.95,
                "f3_f4_undercoverage_disclosed": True,
            },
        )

        # 4. Forecast capability
        capabilities["forecast"] = ServiceCapability(
            available=False,
            status="UNAVAILABLE",
            reason="NO_APPROVED_SERVING_MODEL_ARTIFACT: Retrospective temporal fold models (F1-F4) cannot be served as current operational forecasts without approved prospective validation.",
        )

        # 5. Economics capability
        capabilities["economics"] = ServiceCapability(
            available=True,
            status="RESEARCH_ONLY",
            reason="Calculations conditional on user-entered parameters; commercial cost feeds unverified.",
            metadata={
                "gating_policy": "FAIL_CLOSED_BLOCKED",
                "mode": "RESEARCH_AND_USER_ENTERED_ONLY",
            },
        )

        # 6. Active Farmer Advisory capability
        capabilities["active_advice"] = ServiceCapability(
            available=False,
            status="BLOCKED",
            reason="Advisory action is strictly blocked pending approved prospective validation and live market verification.",
        )

        process_status = "HEALTHY" if self.index_loaded else "DEGRADED"

        return HealthResponseData(
            process_status=process_status,
            uptime_seconds=round(uptime, 2),
            server_time_utc=now_utc.isoformat(),
            server_time_ist=now_ist.isoformat(),
            date_policy_timezone="Asia/Kolkata (UTC+05:30)",
            capabilities=capabilities,
        )

    def get_catalog(self) -> CatalogData:
        """
        Returns catalog of supported districts, markets, commodities, and series.
        Preserves Rice versus Paddy distinctly. Never merges identities heuristically.
        """
        districts: set[str] = set()
        markets: List[Dict[str, str]] = []
        market_keys: set[str] = set()
        commodities: set[str] = set()
        inventory: List[Dict[str, Any]] = []

        server_today = self.get_server_date_ist()

        for s_id, s_rec in sorted(self.series_data.items()):
            dist = s_rec.get("district", "Unknown")
            districts.add(dist)

            m_can = s_rec.get("market_canonical") or s_rec.get("market_raw", "Unknown")
            m_raw = s_rec.get("market_raw", m_can)
            m_pair = f"{dist}__{m_can}"
            if m_pair not in market_keys:
                market_keys.add(m_pair)
                markets.append({
                    "district": dist,
                    "market_canonical": m_can,
                    "market_raw": m_raw,
                })

            comm = s_rec.get("commodity", "Unknown")
            commodities.add(comm)

            # Recompute age dynamically
            obs_date_str = str(s_rec.get("latest_observation_date", ""))
            try:
                obs_d = datetime.strptime(obs_date_str[:10], "%Y-%m-%d").date()
                age_days = (server_today - obs_d).days
            except ValueError:
                age_days = -1

            inventory.append({
                "series_id": s_id,
                "district": dist,
                "market": m_can,
                "commodity": comm,
                "variety": s_rec.get("variety", "Common"),
                "grade": s_rec.get("grade", "FAQ"),
                "latest_observation_date": obs_date_str,
                "age_days": age_days,
                "status": s_rec.get("status", "ACCEPTED"),
            })

        return CatalogData(
            total_series_count=len(self.series_data),
            focus_crops=DECLARED_FOCUS_CROPS,
            districts=sorted(list(districts)),
            markets=sorted(markets, key=lambda x: (x["district"], x["market_canonical"])),
            commodities=sorted(list(commodities)),
            series_inventory=inventory,
        )

    def get_latest_prices(
        self,
        commodity: Optional[str] = None,
        district: Optional[str] = None,
        market: Optional[str] = None,
    ) -> List[PriceSeriesRecord]:
        """
        Query matching latest price records from the bounded imported index.
        Returns ALL matching exact series rather than choosing one variety/grade arbitrarily.
        Dynamically recomputes age_days from server date in Asia/Kolkata.
        Preserves null min/max bounds and FILE_IMPORT data mode.
        """
        if not self.index_loaded:
            raise RuntimeError(self.index_error or "Market price index unavailable")

        server_today = self.get_server_date_ist()
        matches: List[PriceSeriesRecord] = []

        comm_filter = commodity.strip().lower() if commodity else None
        dist_filter = district.strip().lower() if district else None
        mkt_filter = market.strip().lower() if market else None

        for s_id, s_rec in sorted(self.series_data.items()):
            rec_comm = s_rec.get("commodity", "").strip().lower()
            rec_dist = s_rec.get("district", "").strip().lower()
            rec_m_can = s_rec.get("market_canonical", "").strip().lower()
            rec_m_raw = s_rec.get("market_raw", "").strip().lower()

            if comm_filter and rec_comm != comm_filter:
                continue
            if dist_filter and rec_dist != dist_filter:
                continue
            if mkt_filter and mkt_filter not in (rec_m_can, rec_m_raw):
                continue

            # Compute dynamic age
            obs_str = str(s_rec.get("latest_observation_date", ""))
            try:
                obs_d = datetime.strptime(obs_str[:10], "%Y-%m-%d").date()
                age_days = (server_today - obs_d).days
            except ValueError:
                age_days = -1

            # Null min/max preservation: do NOT default to modal_price!
            min_p = s_rec.get("min_price")
            max_p = s_rec.get("max_price")
            min_price_clean = float(min_p) if min_p is not None and math.isfinite(float(min_p)) else None
            max_price_clean = float(max_p) if max_p is not None and math.isfinite(float(max_p)) else None

            # Safe source file hashes
            src_hashes = s_rec.get("source_file_hashes", [])
            if not isinstance(src_hashes, list):
                src_hashes = [str(src_hashes)]

            rec = PriceSeriesRecord(
                series_id=s_id,
                district=s_rec.get("district", "Unknown"),
                market_canonical=s_rec.get("market_canonical", "Unknown"),
                market_raw=s_rec.get("market_raw", "Unknown"),
                commodity=s_rec.get("commodity", "Unknown"),
                variety=s_rec.get("variety", "Common"),
                grade=s_rec.get("grade", "FAQ"),
                observation_date=obs_str,
                age_days=age_days,
                modal_price=float(s_rec.get("modal_price", 0.0)),
                min_price=min_price_clean,
                max_price=max_price_clean,
                price_unit=s_rec.get("price_unit", "Rs./Quintal"),
                market_alias_status=s_rec.get("market_alias_status", "UNKNOWN"),
                status=s_rec.get("status", "ACCEPTED"),
                status_reason=s_rec.get("status_reason", ""),
                data_mode="FILE_IMPORT",
                import_timestamp_utc=s_rec.get("import_timestamp_utc", ""),
                is_live_verified=False,  # FILE_IMPORT never masquerades as live-verified
                is_import_verified=bool(s_rec.get("is_import_verified", True)),
                source_file_hashes=src_hashes,
                capabilities=s_rec.get("capabilities", {
                    "price_display_permitted": True,
                    "forecast_eligible": False,
                    "economics_eligible": False,
                    "active_advice_permitted": False,
                }),
            )
            matches.append(rec)

        return matches

    def get_price_history(
        self,
        district: Optional[str] = None,
        market: Optional[str] = None,
        commodity: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """
        Bounded price history endpoint.
        Never scans or loads raw full panels on request. Returns honest unavailable
        unless an authorized, bounded snapshot is configured.
        """
        # Validate pagination inputs
        if page < 1:
            raise ValueError(f"page must be positive integer, got {page}")
        if page_size < 1 or page_size > 100:
            raise ValueError(f"page_size must be between 1 and 100, got {page_size}")

        # In dataset-first mode without local raw scan authorization, return honest unavailable
        return {
            "status": "HISTORY_UNAVAILABLE",
            "message": "Full-panel historical raw scans are restricted on local runtime. Use pre-indexed historical snapshots.",
            "query": {
                "district": district,
                "market": market,
                "commodity": commodity,
                "start_date": start_date,
                "end_date": end_date,
                "page": page,
                "page_size": page_size,
            },
            "records": [],
            "total_available": 0,
        }

    def get_benchmark_scorecards(self) -> Dict[str, Any]:
        """
        Exposes verified benchmark scorecards and limitations.
        Accurately reports persistence baseline winning MAE, HGB RMSE gain, and crisis fold undercoverage.
        """
        return {
            "primary_benchmark_model": "naive_persistence",
            "primary_decision_rule": "Lowest Outer-Loop Mean Absolute Error (MAE) on Common Evaluation Origins",
            "metric_denominators": {
                "total_evaluation_rows_f2_f4": 26918,
                "evaluated_outer_folds": ["F2", "F3", "F4"],
                "abstained_outer_fold": "F1 (First outer fold, no prior calibration)",
                "target_horizon": "t+7 calendar days",
            },
            "model_performance_summary": [
                {
                    "model": "naive_persistence",
                    "role": "Primary Reference Baseline",
                    "mae": 106.96,
                    "rmse": 187.72,
                    "skill_vs_persistence_mae_pct": 0.0,
                    "coverage_90_pct": 89.95,
                    "coverage_95_pct": 94.72,
                    "status": "PRIMARY_WINNER_MAE",
                },
                {
                    "model": "hist_gradient_boosting",
                    "role": "Exploratory Tree Model",
                    "mae": 109.75,
                    "rmse": 176.62,
                    "skill_vs_persistence_mae_pct": -2.61,  # Worse MAE than persistence
                    "rmse_improvement_vs_persistence_pct": 5.91,
                    "coverage_90_pct": 88.42,
                    "coverage_95_pct": 93.81,
                    "status": "NON_WINNING_MAE_BEST_RMSE",
                },
                {
                    "model": "ridge_regression",
                    "role": "Exploratory Linear Regularized Model",
                    "mae": 110.32,
                    "rmse": 178.61,
                    "skill_vs_persistence_mae_pct": -3.14,
                    "rmse_improvement_vs_persistence_pct": 4.85,
                    "coverage_90_pct": 88.15,
                    "coverage_95_pct": 93.54,
                    "status": "NON_WINNING",
                },
            ],
            "fold_level_breakdown_naive_90": {
                "F2": {"coverage_pct": 94.48, "status": "NOMINAL_COVERAGE_ACHIEVED"},
                "F3": {"coverage_pct": 75.94, "status": "SEVERE_UNDERCOVERAGE_CRISIS_REGIME"},
                "F4": {"coverage_pct": 72.26, "status": "SEVERE_UNDERCOVERAGE_CRISIS_REGIME"},
            },
            "critical_disclosures": [
                "Persistence baseline (106.96) beats HGB (109.75) and Ridge (110.32) on primary MAE.",
                "HGB achieves 5.91% RMSE improvement, but does NOT beat persistence on MAE.",
                "Overall 90% coverage (89.95%) is driven by pooled sample size and does not establish conditional validity.",
                "During high-volatility crisis regimes (F3 and F4), empirical coverage collapses to 75.94% and 72.26%.",
                "Retrospective model scores cannot authorize live operational farmer advice.",
            ],
        }

    def evaluate_forecast(self, req: ForecastServiceRequest) -> ForecastServiceResult:
        """
        Forecast endpoint.
        Returns specific FORECAST_UNAVAILABLE with version and reason metadata.
        Does not fit models on request or masquerade historical intervals as live forecasts.
        """
        series_id = f"{req.district}|{req.market}|{req.commodity}|{req.variety}|{req.grade}"
        return ForecastServiceResult(
            series_id=series_id,
            horizon_days=req.horizon_days,
            point_forecast=None,
            interval_lower=None,
            interval_upper=None,
            nominal_level=0.90,
            forecast_status="FORECAST_UNAVAILABLE",
            reason=(
                "NO_APPROVED_SERVING_MODEL_ARTIFACT: Retrospective temporal fold models (F1-F4) "
                "cannot be served as current operational forecasts without approved prospective validation."
            ),
            advisory_action="BLOCKED",
            advisory_permitted=False,
        )

    def evaluate_economics(self, req_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Research economics evaluation endpoint.
        Delegates strictly to repaired canonical contract.
        """
        request_obj = ResearchEconomicRequest.from_dict(req_data)
        result_obj = evaluate_research_economics(request_obj)
        return result_obj.to_dict()
