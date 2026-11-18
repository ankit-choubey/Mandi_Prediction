"""
Mandi Market Service Layer (MP-APP-001A)
APMC Mandi Intelligence System - Step 10 Dataset-First Backend
Implements business logic separating storage readers, freshness calculation,
scorecard reporting, forecast gating, and research economics.
"""

from __future__ import annotations

from datetime import datetime, date, timezone, timedelta
import csv
import hashlib
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

# Official Six Focus Crops per master specification
DECLARED_FOCUS_CROPS = [
    "Wheat",
    "Potato",
    "Onion",
    "Tomato",
    "Paddy(Common)",
    "Rice",
]

# Documented spelling aliases mapping to canonical focus crops
PADDY_SPELLING_ALIASES = {
    "Paddy(Dhan)(Common)": "Paddy(Common)",
    "Dhan": "Paddy(Common)",
}

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

        env_index_path = os.environ.get("APMC_LATEST_INDEX_PATH")
        self.latest_index_path = Path(latest_index_path) if latest_index_path else (
            Path(env_index_path) if env_index_path else (
                REPO_ROOT / "data" / "imported_snapshots" / "latest_observation_index.json"
            )
        )
        self.calibration_envelope_path = Path(calibration_envelope_path) if calibration_envelope_path else (
            REPO_ROOT / "experiments" / "reports" / "FC008" / "calibration_envelope_v1.json"
        )

        self.index_loaded = False
        self.index_error: Optional[str] = None
        self.index_metadata: Dict[str, Any] = {}
        self.series_data: Dict[str, Dict[str, Any]] = {}

        self._load_latest_index()

    def reload_index(self, index_path: Optional[Path | str] = None) -> HealthResponseData:
        """
        Public supported method for reloading market price index snapshot.
        Atomically updates internal series dictionary and metadata if the target file is valid.
        """
        if index_path:
            self.latest_index_path = Path(index_path)
        self._load_latest_index()
        return self.get_health()

    def _load_latest_index(self) -> None:
        """Loads and indexes latest market observations with bounded resource and type guards."""
        default_index_path = REPO_ROOT / "data" / "imported_snapshots" / "latest_observation_index.json"
        if not self.latest_index_path.exists() and self.latest_index_path == default_index_path:
            # Auto-compile index from operational_sources.json if present and default snapshot missing
            try:
                op_cfg_path = REPO_ROOT / "data" / "reference" / "operational_sources.json"
                if op_cfg_path.exists():
                    from src.live_price_ingestion import (
                        LivePriceIngestionClient,
                        DataMode,
                        publish_latest_observation_index,
                    )
                    with open(op_cfg_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                    sources = cfg.get("sources", [])
                    target_files = [
                        str(REPO_ROOT / s["file_path"]) if not os.path.isabs(s["file_path"]) else s["file_path"]
                        for s in sources
                        if s.get("role") == "LATEST_SNAPSHOT" and os.path.exists(
                            str(REPO_ROOT / s["file_path"]) if not os.path.isabs(s["file_path"]) else s["file_path"]
                        )
                    ]
                    if target_files:
                        self.latest_index_path.parent.mkdir(parents=True, exist_ok=True)
                        client = LivePriceIngestionClient(
                            data_mode=DataMode.FILE_IMPORT,
                            snapshots_root=str(self.latest_index_path.parent),
                        )
                        campaign = client.execute_file_import(file_path=target_files)
                        publish_latest_observation_index(
                            campaign, output_path=str(self.latest_index_path)
                        )
            except Exception as ex:
                logger.warning("Auto-generation of latest observation index failed: %s", ex)

        if not self.latest_index_path.exists():
            self.index_loaded = False
            self.index_error = "Market price index file not found"
            return

        try:
            file_size = self.latest_index_path.stat().st_size
            if file_size > 10 * 1024 * 1024:
                self.index_loaded = False
                self.index_error = f"Market price index file exceeds 10 MB limit ({file_size} bytes)"
                return

            with open(self.latest_index_path, "rb") as f:
                raw_bytes = f.read()
            index_file_sha256 = hashlib.sha256(raw_bytes).hexdigest()
            payload = json.loads(raw_bytes.decode("utf-8"))

            if not isinstance(payload, dict):
                self.index_loaded = False
                self.index_error = "Market price index root must be an object"
                return

            raw_series = payload.get("series")
            if raw_series is None:
                self.index_loaded = False
                self.index_error = "Market price index missing 'series' key"
                return

            if isinstance(raw_series, list):
                if len(raw_series) == 0:
                    self.index_loaded = False
                    self.index_error = "Market price index contains no series records"
                    return
                s_map = {}
                for idx, item in enumerate(raw_series):
                    if not isinstance(item, dict):
                        continue
                    sid = item.get("series_id") or f"series_{idx}"
                    s_map[sid] = item
                candidates = s_map
            elif isinstance(raw_series, dict):
                if len(raw_series) == 0:
                    self.index_loaded = False
                    self.index_error = "Market price index contains no series records"
                    return
                candidates = raw_series
            else:
                self.index_loaded = False
                self.index_error = "Market price index series must be an object or list"
                return

            if len(candidates) > 50000:
                self.index_loaded = False
                self.index_error = f"Market price index contains too many series records ({len(candidates)})"
                return

            valid_series = {}
            for sid, rec in candidates.items():
                if not isinstance(rec, dict):
                    continue
                mp = rec.get("modal_price")
                if mp is None or type(mp) is bool or not isinstance(mp, (int, float)) or not math.isfinite(float(mp)) or float(mp) <= 0:
                    continue
                if not rec.get("district") or not rec.get("commodity"):
                    continue
                valid_series[sid] = rec

            if not valid_series:
                self.index_loaded = False
                self.index_error = "Market price index contains no valid series records"
                return

            self.series_data = valid_series
            self.index_metadata = {
                "index_version": payload.get("index_version", "1.0.0"),
                "generated_at_utc": payload.get("generated_at_utc"),
                "total_series_indexed": len(self.series_data),
                "composite_source_sha256": payload.get("composite_source_sha256"),
                "index_file_sha256": index_file_sha256,
            }
            self.index_loaded = True
            self.index_error = None
        except Exception as e:
            self.index_loaded = False
            self.index_error = f"Failed to parse index JSON: {type(e).__name__}"
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
                    "index_file_sha256": self.index_metadata.get("index_file_sha256"),
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
        bm_cards = self.get_benchmark_scorecards()
        if bm_cards.get("status") == "AVAILABLE":
            capabilities["benchmarks"] = ServiceCapability(
                available=True,
                status="AVAILABLE",
                metadata={
                    "primary_model": "naive_persistence",
                    "verified_mae": 106.955,
                    "hgb_rmse_improvement_pct": 5.915,
                    "nominal_coverage_90_pct": 89.955,
                    "f3_f4_undercoverage_disclosed": True,
                },
            )
        else:
            capabilities["benchmarks"] = ServiceCapability(
                available=False,
                status="UNAVAILABLE",
                reason=bm_cards.get("message", "Benchmark reports unavailable"),
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
        startup_time_utc = self.start_datetime_utc.isoformat().replace("+00:00", "Z")

        return HealthResponseData(
            process_status=process_status,
            uptime_seconds=round(uptime, 2),
            server_time_utc=now_utc.isoformat().replace("+00:00", "Z"),
            server_time_ist=now_ist.isoformat(),
            date_policy_timezone="Asia/Kolkata (UTC+05:30)",
            capabilities=capabilities,
            startup_time_utc=startup_time_utc,
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

            # Derive price_display_permitted for catalog inventory
            s_caps = s_rec.get("capabilities", {})
            src_perm = s_caps.get("price_display_permitted")
            is_acc = (s_rec.get("status") == "ACCEPTED" and s_rec.get("market_alias_status") == "ACCEPTED")
            valid_dt = (age_days >= 0)
            valid_mp = (float(s_rec.get("modal_price", 0.0)) > 0.0 and math.isfinite(float(s_rec.get("modal_price", 0.0))))

            if src_perm is False:
                disp_perm = False
            elif not is_acc or not valid_dt or not valid_mp:
                disp_perm = False
            else:
                disp_perm = True

            inventory.append({
                "series_id": s_id,
                "district": dist,
                "market": m_can,
                "commodity": comm,
                "variety": s_rec.get("variety", "Common"),
                "grade": s_rec.get("grade", "UNKNOWN"),
                "latest_observation_date": obs_date_str,
                "age_days": age_days,
                "status": s_rec.get("status", "UNKNOWN"),
                "market_alias_status": s_rec.get("market_alias_status", "UNKNOWN"),
                "price_display_permitted": disp_perm,
                "disposition": "ACCEPTED" if disp_perm else "REVIEW",
            })

        acc_count = sum(1 for item in inventory if item["price_display_permitted"])
        rev_count = len(inventory) - acc_count

        return CatalogData(
            total_series_count=len(self.series_data),
            focus_crops=DECLARED_FOCUS_CROPS,
            districts=sorted(list(districts)),
            markets=sorted(markets, key=lambda x: (x["district"], x["market_canonical"])),
            commodities=sorted(list(commodities)),
            series_inventory=inventory,
            commodity_aliases=PADDY_SPELLING_ALIASES,
            accepted_series_count=acc_count,
            review_series_count=rev_count,
        )

    def get_latest_prices(
        self,
        commodity: Optional[str] = None,
        district: Optional[str] = None,
        market: Optional[str] = None,
        verified_only: bool = False,
        disposition: Optional[str] = None,
    ) -> List[PriceSeriesRecord]:
        """
        Query matching latest price records from the bounded imported index.
        Returns matching exact series rather than choosing one variety/grade arbitrarily.
        Dynamically derives price_display_permitted from source disposition and identity.
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
        disp_filter = disposition.strip().upper() if disposition else None

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

            # Derive price_display_permitted strictly from identity and source evidence
            source_caps = s_rec.get("capabilities", {})
            source_perm = source_caps.get("price_display_permitted")
            is_accepted = (s_rec.get("status") == "ACCEPTED" and s_rec.get("market_alias_status") == "ACCEPTED")
            has_valid_date = (age_days >= 0)
            has_valid_modal = (float(s_rec.get("modal_price", 0.0)) > 0.0 and math.isfinite(float(s_rec.get("modal_price", 0.0))))

            if source_perm is False:
                display_permitted = False
            elif not is_accepted or not has_valid_date or not has_valid_modal:
                display_permitted = False
            else:
                display_permitted = True

            # Disposition / verified_only filtering
            if verified_only and not display_permitted:
                continue
            if disp_filter in ("ACCEPTED", "VERIFIED", "APPROVED") and not display_permitted:
                continue
            if disp_filter in ("REVIEW", "UNKNOWN_MARKET_REVIEW", "UNAPPROVED", "QUARANTINED") and display_permitted:
                continue

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
                grade=s_rec.get("grade", "UNKNOWN"),
                observation_date=obs_str,
                age_days=age_days,
                modal_price=float(s_rec.get("modal_price", 0.0)),
                min_price=min_price_clean,
                max_price=max_price_clean,
                price_unit=s_rec.get("price_unit", "Rs./Quintal"),
                market_alias_status=s_rec.get("market_alias_status", "UNKNOWN"),
                status=s_rec.get("status", "UNKNOWN"),
                status_reason=s_rec.get("status_reason", ""),
                data_mode="FILE_IMPORT",
                import_timestamp_utc=s_rec.get("import_timestamp_utc", ""),
                is_live_verified=False,  # FILE_IMPORT never masquerades as live-verified
                is_import_verified=bool(s_rec.get("is_import_verified", False)),
                source_file_hashes=src_hashes,
                capabilities={
                    "price_display_permitted": display_permitted,
                    "forecast_eligible": False,
                    "economics_eligible": False,
                    "active_advice_permitted": False,  # Server-derived fail-closed
                },
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
        Exposes verified benchmark scorecards and limitations loaded directly from source CSVs:
        - FC007_VERIFIED/scorecard_overall.csv
        - FC008/intervals_overall.csv
        - FC008/intervals_by_fold.csv
        Exposes exact numbers matching verified records.
        """
        reports_root = Path(os.environ.get("APMC_REPORTS_ROOT", REPO_ROOT / "experiments" / "reports"))
        point_file = reports_root / "FC007_VERIFIED" / "scorecard_overall.csv"
        interval_file = reports_root / "FC008" / "intervals_overall.csv"
        fold_file = reports_root / "FC008" / "intervals_by_fold.csv"

        if not point_file.exists() or not interval_file.exists() or not fold_file.exists():
            return {
                "status": "BENCHMARK_UNAVAILABLE",
                "message": "Verified benchmark scorecard reports are unavailable.",
                "model_performance_summary": [],
                "fold_level_breakdown_naive_90": {},
            }

        try:
            with open(point_file, "r", encoding="utf-8") as f:
                points = {row["model"]: row for row in csv.DictReader(f)}
            with open(interval_file, "r", encoding="utf-8") as f:
                intervals = {(row["model"], float(row["nominal_level"])): row for row in csv.DictReader(f)}
            with open(fold_file, "r", encoding="utf-8") as f:
                folds = {
                    (row["slice_name"], row["model"], float(row["nominal_level"])): row
                    for row in csv.DictReader(f)
                }

            models_config = [
                ("naive_persistence", "naive", "Primary Reference Baseline", "PRIMARY_WINNER_MAE"),
                ("hist_gradient_boosting", "hist_gradient_boosting", "Exploratory Tree Model", "NON_WINNING_MAE_BEST_RMSE"),
                ("ridge_regression", "ridge", "Exploratory Linear Regularized Model", "NON_WINNING"),
            ]

            rmse_naive = float(points["naive"]["rmse"])

            summary_rows = []
            for display_name, internal_name, role, status in models_config:
                pt = points[internal_name]
                mae_val = float(pt["mae"])
                rmse_val = float(pt["rmse"])
                cov_90 = float(intervals[(internal_name, 0.9)]["empirical_coverage_pct"])
                cov_95 = float(intervals[(internal_name, 0.95)]["empirical_coverage_pct"])
                skill_val = 100.0 * float(pt["skill"])

                row_dict = {
                    "model": display_name,
                    "role": role,
                    "mae": mae_val,
                    "rmse": rmse_val,
                    "skill_vs_persistence_mae_pct": skill_val,
                    "coverage_90_pct": cov_90,
                    "coverage_95_pct": cov_95,
                    "status": status,
                }
                if internal_name != "naive":
                    rmse_imp = ((rmse_naive - rmse_val) / rmse_naive) * 100.0
                    row_dict["rmse_improvement_vs_persistence_pct"] = rmse_imp
                summary_rows.append(row_dict)

            fold_breakdown = {}
            for f_key in ["F2", "F3", "F4"]:
                slice_key = f"Fold_{f_key}"
                if (slice_key, "naive", 0.9) in folds:
                    f_row = folds[(slice_key, "naive", 0.9)]
                    cov_pct = float(f_row["empirical_coverage_pct"])
                    f_status = "NOMINAL_COVERAGE_ACHIEVED" if cov_pct >= 90.0 else "SEVERE_UNDERCOVERAGE_CRISIS_REGIME"
                    fold_breakdown[f_key] = {
                        "coverage_pct": cov_pct,
                        "status": f_status,
                        "mean_width": float(f_row.get("mean_width", 0.0)),
                        "issued_count": int(f_row.get("issued_count", 0)),
                    }

            return {
                "status": "AVAILABLE",
                "primary_benchmark_model": "naive_persistence",
                "primary_decision_rule": "Lowest Outer-Loop Mean Absolute Error (MAE) on Common Evaluation Origins",
                "metric_denominators": {
                    "point_metrics_scope": {
                        "total_origins": 64776,
                        "unique_series": 401,
                        "folds": ["F1", "F2", "F3", "F4"],
                        "target_tolerance": "t+7 calendar days (6-8 day tolerance)",
                        "units": "INR/quintal",
                    },
                    "interval_metrics_scope": {
                        "total_issued_origins": 26918,
                        "unique_series": 365,
                        "evaluated_folds": ["F2", "F3", "F4"],
                        "abstained_fold": "F1 (First outer fold, no earlier residuals for calibration)",
                        "target_tolerance": "t+7 calendar days (6-8 day tolerance)",
                        "units": "INR/quintal",
                    },
                },
                "model_performance_summary": summary_rows,
                "fold_level_breakdown_naive_90": fold_breakdown,
                "critical_disclosures": [
                    "Persistence baseline (MAE ~106.96) beats HGB (~109.75) and Ridge (~110.32) on primary MAE.",
                    "HGB achieves ~5.91% RMSE improvement over persistence, but does NOT beat persistence on MAE.",
                    "Overall 90% coverage (~89.95%) is pooled across folds and does not establish conditional validity.",
                    "During high-volatility crisis regimes (F3 and F4), empirical coverage collapses to ~75.94% and ~72.26%.",
                    "Retrospective model scores cannot authorize live operational farmer advice.",
                ],
            }
        except Exception as e:
            return {
                "status": "BENCHMARK_UNAVAILABLE",
                "message": f"Failed to load verified benchmark scorecards: {type(e).__name__}",
                "model_performance_summary": [],
                "fold_level_breakdown_naive_90": {},
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

    def get_demonstration_cases(self) -> List[Dict[str, Any]]:
        """
        Returns list of verified historical test cases from the 5-district benchmark
        for real-time demonstration of the classification and intelligence engine.
        """
        cases = self._get_demo_case_registry()
        return [
            {
                "id": c["id"],
                "title": c["title"],
                "district": c["district"],
                "market": c["market"],
                "commodity": c["commodity"],
                "variety": c["variety"],
                "observation_date": c["observation_date"],
                "current_price": c["current_price"],
                "expected_condition_T7": c["expected_condition_T7"],
            }
            for c in cases
        ]

    def get_demonstration_inference(self, case_id: str) -> Optional[Dict[str, Any]]:
        """
        Returns complete intelligence card payload for a selected historical test case,
        including prediction probabilities, actual T+7 outcome, spatial comparisons,
        and explicit safety gate blocking disclosures.
        """
        for c in self._get_demo_case_registry():
            if c["id"] == case_id:
                return c
        return None

    def _get_demo_case_registry(self) -> List[Dict[str, Any]]:
        """Static verified registry of 5 district test case studies documented in Final Report Section 6."""
        return [
            {
                "id": "lucknow_wheat",
                "title": "Lucknow APMC — Wheat (Dara)",
                "district": "Lucknow",
                "market": "Lucknow APMC",
                "commodity": "Wheat",
                "variety": "Dara",
                "grade": "FAQ",
                "observation_date": "2026-08-25",
                "current_price": 2425.0,
                "min_price": 2425.0,
                "max_price": 2425.0,
                "intraday_spread": 0.0,
                "rolling_avg_7d": 2448.71,
                "price_change_7d_pct": -6.37,
                "volatility_7d_std": 65.08,
                "district_summary": {
                    "district_avg_price": 2522.64,
                    "reporting_mandis": 4,
                    "mandi_vs_district_pct": -3.87,
                },
                "neighbouring_summary": {
                    "neighbor_avg_price": 2498.51,
                    "price_difference": -73.51,
                    "spatial_comparison": "Target price lower than neighbour average",
                },
                "expected_condition_T7": "NORMAL",
                "condition_confidence": 68.04,
                "advisory_action": "BLOCKED",
                "advisory_permitted": False,
                "all_probabilities": {
                    "Unfavorable": 15.13,
                    "Normal": 68.04,
                    "Favorable": 16.83,
                },
                "actual_outcome_T7": {
                    "actual_price_T7": 2547.84,
                    "actual_pct_change": 5.07,
                    "actual_condition": "Favorable",
                },
                "safety_gate": {
                    "status": "BLOCKED",
                    "advisory_permitted": False,
                    "directive": "STALE DATA — ACTIVE ADVISORY BLOCKED",
                    "reason": "Historical retrospective demonstration only. Retrospective fold models cannot be served as active commercial trading advice to farmers without approved prospective validation (Step 13).",
                    "freshness_status": "STALE",
                    "lag_days": 84,
                },
                "methodological_note": (
                    "Point regression was disqualified due to high decimal noise and false precision. "
                    "The system operates as a 3-class condition classifier (Favorable / Normal / Unfavorable) "
                    "reflecting discrete operational harvest decisions."
                ),
            },
            {
                "id": "kanpur_potato",
                "title": "Uttaripura APMC (Kanpur) — Potato (Other)",
                "district": "Kanpur",
                "market": "Uttaripura APMC",
                "commodity": "Potato",
                "variety": "Other",
                "grade": "FAQ",
                "observation_date": "2026-08-25",
                "current_price": 550.0,
                "min_price": 550.0,
                "max_price": 550.0,
                "intraday_spread": 0.0,
                "rolling_avg_7d": 564.54,
                "price_change_7d_pct": -8.33,
                "volatility_7d_std": 38.33,
                "district_summary": {
                    "district_avg_price": 550.0,
                    "reporting_mandis": 3,
                    "mandi_vs_district_pct": 0.0,
                },
                "neighbouring_summary": {
                    "neighbor_avg_price": 700.0,
                    "price_difference": -150.0,
                    "spatial_comparison": "Target price lower than neighbour average",
                },
                "expected_condition_T7": "FAVORABLE",
                "condition_confidence": 38.8,
                "advisory_action": "BLOCKED",
                "advisory_permitted": False,
                "all_probabilities": {
                    "Unfavorable": 33.62,
                    "Normal": 27.58,
                    "Favorable": 38.8,
                },
                "actual_outcome_T7": {
                    "actual_price_T7": 550.0,
                    "actual_pct_change": 0.0,
                    "actual_condition": "Normal",
                },
                "safety_gate": {
                    "status": "BLOCKED",
                    "advisory_permitted": False,
                    "directive": "STALE DATA — ACTIVE ADVISORY BLOCKED",
                    "reason": "Historical retrospective demonstration only. Commercial potato storage in UP requires 6-month seasonal contracts (March-Oct); short-term 7-day tactical holding is economically infeasible.",
                    "freshness_status": "STALE",
                    "lag_days": 84,
                },
                "methodological_note": (
                    "Track D supply chain analysis proves that tactical 7-day storage for perishables "
                    "leads to commercial losses in >90% of sessions. Hence advisory commands remain strictly blocked."
                ),
            },
            {
                "id": "ghaziabad_onion",
                "title": "Noida APMC (Ghaziabad) — Onion (Other)",
                "district": "Ghaziabad",
                "market": "Noida APMC",
                "commodity": "Onion",
                "variety": "Other",
                "grade": "FAQ",
                "observation_date": "2026-08-25",
                "current_price": 3502.59,
                "min_price": 3500.0,
                "max_price": 3790.75,
                "intraday_spread": 290.75,
                "rolling_avg_7d": 3087.90,
                "price_change_7d_pct": 59.21,
                "volatility_7d_std": 615.60,
                "district_summary": {
                    "district_avg_price": 3219.64,
                    "reporting_mandis": 3,
                    "mandi_vs_district_pct": 8.79,
                },
                "neighbouring_summary": {
                    "neighbor_avg_price": 3219.64,
                    "price_difference": 282.95,
                    "spatial_comparison": "Target price higher than neighbour average",
                },
                "expected_condition_T7": "NORMAL",
                "condition_confidence": 38.73,
                "advisory_action": "BLOCKED",
                "advisory_permitted": False,
                "all_probabilities": {
                    "Unfavorable": 23.75,
                    "Normal": 38.73,
                    "Favorable": 37.52,
                },
                "actual_outcome_T7": {
                    "actual_price_T7": 4000.0,
                    "actual_pct_change": 14.20,
                    "actual_condition": "Favorable",
                },
                "safety_gate": {
                    "status": "BLOCKED",
                    "advisory_permitted": False,
                    "directive": "STALE DATA — ACTIVE ADVISORY BLOCKED",
                    "reason": "Historical retrospective demonstration only. Advisory action blocked pending approved prospective validation.",
                    "freshness_status": "STALE",
                    "lag_days": 84,
                },
                "methodological_note": (
                    "Demonstrates high volatility handling during pre-harvest price surges. "
                    "Ensemble classifier avoids overfitting to the short-term 59% weekly surge."
                ),
            },
            {
                "id": "jhansi_wheat",
                "title": "Moth APMC (Jhansi) — Wheat (Other)",
                "district": "Jhansi",
                "market": "Moth APMC",
                "commodity": "Wheat",
                "variety": "Other",
                "grade": "FAQ",
                "observation_date": "2026-08-25",
                "current_price": 2613.98,
                "min_price": 2585.0,
                "max_price": 2625.0,
                "intraday_spread": 40.0,
                "rolling_avg_7d": 2585.01,
                "price_change_7d_pct": 0.88,
                "volatility_7d_std": 25.77,
                "district_summary": {
                    "district_avg_price": 2475.63,
                    "reporting_mandis": 7,
                    "mandi_vs_district_pct": 5.59,
                },
                "neighbouring_summary": {
                    "neighbor_avg_price": 2475.63,
                    "price_difference": 138.35,
                    "spatial_comparison": "Target price higher than neighbour average",
                },
                "expected_condition_T7": "NORMAL",
                "condition_confidence": 75.16,
                "advisory_action": "BLOCKED",
                "advisory_permitted": False,
                "all_probabilities": {
                    "Unfavorable": 14.97,
                    "Normal": 75.16,
                    "Favorable": 9.88,
                },
                "actual_outcome_T7": {
                    "actual_price_T7": 2662.47,
                    "actual_pct_change": 1.86,
                    "actual_condition": "Normal",
                },
                "safety_gate": {
                    "status": "BLOCKED",
                    "advisory_permitted": False,
                    "directive": "STALE DATA — ACTIVE ADVISORY BLOCKED",
                    "reason": "Historical retrospective demonstration only. Advisory action blocked pending approved prospective validation.",
                    "freshness_status": "STALE",
                    "lag_days": 84,
                },
                "methodological_note": (
                    "High-confidence NORMAL prediction (75.16%). Low price volatility in wheat "
                    "cannot offset loading/unloading and double mandi friction."
                ),
            },
            {
                "id": "unnao_rice",
                "title": "Purwa APMC (Unnao) — Rice (Common)",
                "district": "Unnao",
                "market": "Purwa APMC",
                "commodity": "Rice",
                "variety": "Common",
                "grade": "FAQ",
                "observation_date": "2026-08-25",
                "current_price": 2502.45,
                "min_price": 2490.0,
                "max_price": 2550.36,
                "intraday_spread": 60.36,
                "rolling_avg_7d": 2479.74,
                "price_change_7d_pct": -0.94,
                "volatility_7d_std": 91.15,
                "district_summary": {
                    "district_avg_price": 2502.45,
                    "reporting_mandis": 1,
                    "mandi_vs_district_pct": 0.0,
                },
                "neighbouring_summary": {
                    "neighbor_avg_price": 2611.93,
                    "price_difference": -109.48,
                    "spatial_comparison": "Target price lower than neighbour average",
                },
                "expected_condition_T7": "NORMAL",
                "condition_confidence": 42.73,
                "advisory_action": "BLOCKED",
                "advisory_permitted": False,
                "all_probabilities": {
                    "Unfavorable": 30.24,
                    "Normal": 42.73,
                    "Favorable": 27.02,
                },
                "actual_outcome_T7": {
                    "actual_price_T7": 2513.27,
                    "actual_pct_change": 0.43,
                    "actual_condition": "Normal",
                },
                "safety_gate": {
                    "status": "BLOCKED",
                    "advisory_permitted": False,
                    "directive": "STALE DATA — ACTIVE ADVISORY BLOCKED",
                    "reason": "Historical retrospective demonstration only. Advisory action blocked pending approved prospective validation.",
                    "freshness_status": "STALE",
                    "lag_days": 84,
                },
                "methodological_note": (
                    "Rigorous commodity distinction: Rice is strictly segregated from Paddy(Common) "
                    "in accordance with Section 4 identity rules."
                ),
            },
        ]
