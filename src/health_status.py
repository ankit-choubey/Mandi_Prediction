"""
Health Status & Operational Freshness Engine
APMC Mandi Market Intelligence System
Author: Om Awasthi (Owner 4: Current-Data Output & Operational Reliability)

This module provides the operational health reporting, freshness evaluation,
and reconciliation ledger for the Mandi Prediction data pipeline.

Key Capabilities:
1. Seven Operational State Transitions:
   - SUCCESS: Live fetch and validation completed with new observations.
   - UNCHANGED: Live fetch succeeded; incoming records match current store.
   - PARTIAL: Source pagination incomplete or partial payload returned.
   - QUARANTINED: Ingestion completed, but some records failed validation.
   - SOURCE_DOWN: Upstream API is offline; fell back to prior validated store.
   - UNINITIALIZED: Critical failure; no prior validated snapshot exists.
   - STALE_DATA: Observations exceed configured freshness thresholds.
2. Distinct Timestamp Accounting:
   - Separates 'observation_date' (when trade happened) from 'retrieval_timestamp' (when system fetched).
3. Freshness Policy:
   - <= 2 calendar days from evaluation reference: CURRENT
   - 3 to 5 calendar days: DELAYED
   - > 5 calendar days: STALE
4. Full Section-8 Reconciliation Ledger.
"""

import os
import json
import hashlib
from enum import Enum
from dataclasses import dataclass, field, asdict
from datetime import datetime, date, timezone, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple

# =============================================================================
# CONSTANTS & SOURCE METADATA
# =============================================================================

DEFAULT_SOURCE_NAME = "Government of India Daily Mandi Prices (data.gov.in / AGMARKNET)"
DEFAULT_RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
DEFAULT_SOURCE_URL = f"https://api.data.gov.in/resource/{DEFAULT_RESOURCE_ID}"

# Freshness thresholds in calendar days
FRESHNESS_CURRENT_MAX_DAYS = 2
FRESHNESS_DELAYED_MAX_DAYS = 5


class OperationalState(str, Enum):
    """The 7 mandatory operational pipeline states defined in Section 4."""
    SUCCESS = "SUCCESS"              # Fetch and validation succeed with fresh data
    UNCHANGED = "UNCHANGED"          # Fetch succeeded but source data has not changed
    PARTIAL = "PARTIAL"              # Source responds with partial/incomplete data
    QUARANTINED = "QUARANTINED"      # Some records fail validation and are quarantined
    SOURCE_DOWN = "SOURCE_DOWN"      # Source unavailable, but prior validated snapshot exists
    UNINITIALIZED = "UNINITIALIZED"  # No validated snapshot exists at all
    STALE_DATA = "STALE_DATA"        # Latest observations are older than threshold


class FreshnessStatus(str, Enum):
    """Observation freshness ratings."""
    CURRENT = "CURRENT"      # <= 2 calendar days
    DELAYED = "DELAYED"      # 3 to 5 calendar days
    STALE = "STALE"          # > 5 calendar days
    UNKNOWN = "UNKNOWN"      # Cannot be determined


class RecommendationStatus(str, Enum):
    """Recommendation safety status for farmer-facing advisories."""
    ACTIVE = "ACTIVE"                    # Permitted; current market observation
    DELAYED = "DELAYED"                  # Permitted with explicit delay disclosure
    BLOCKED = "BLOCKED"                  # Blocked; stale, missing, down, uninitialized, or future
    HISTORICAL_ONLY = "HISTORICAL_ONLY"  # Permitted strictly for retrospective research/backtest
    DEMO = "DEMO"                        # Permitted strictly as simulated demonstration


BLOCKED_RECOMMENDATION_MESSAGE = (
    "Insufficient information to recommend storage. "
    "Latest market-price data is stale or unavailable."
)


@dataclass
class ReconciliationLedger:
    """Reconciliation metrics matching Section 8 of the execution plan."""
    source_total_records: int = 0
    records_fetched: int = 0
    records_parsed: int = 0
    records_accepted: int = 0
    records_quarantined: int = 0
    records_unchanged: int = 0
    records_corrected: int = 0
    records_new: int = 0
    current_unique_keys: int = 0
    latest_observation_date: Optional[str] = None
    last_successful_fetch_utc: Optional[str] = None
    snapshot_sha256: Optional[str] = None

    def validate_arithmetic(self) -> Dict[str, Any]:
        """Verify that records account properly without silent loss."""
        accounted = self.records_accepted + self.records_quarantined
        is_balanced = (self.records_parsed == accounted) or (self.records_fetched == accounted)
        return {
            "is_balanced": is_balanced,
            "discrepancy": self.records_fetched - accounted if not is_balanced else 0
        }


@dataclass
class HealthReport:
    """Comprehensive health and status report container."""
    source_name: str = DEFAULT_SOURCE_NAME
    resource_id: str = DEFAULT_RESOURCE_ID
    operational_state: OperationalState = OperationalState.UNINITIALIZED
    freshness_status: FreshnessStatus = FreshnessStatus.UNKNOWN
    freshness_lag_days: Optional[int] = None
    latest_observation_date: Optional[str] = None
    last_successful_fetch_utc: Optional[str] = None
    last_successful_fetch_local: Optional[str] = None
    system_execution_time_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    system_execution_time_local: str = field(
        default_factory=lambda: datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=5, minutes=30))).strftime("%Y-%m-%d %H:%M:%S IST")
    )
    is_source_live: bool = False
    is_fallback_active: bool = False
    reconciliation: ReconciliationLedger = field(default_factory=ReconciliationLedger)
    districts_represented: List[str] = field(default_factory=list)
    markets_count: int = 0
    commodities_count: int = 0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        d = asdict(self)
        d["operational_state"] = self.operational_state.value
        d["freshness_status"] = self.freshness_status.value
        return d


class HealthStatusEngine:
    """Engine responsible for computing pipeline health, freshness, and operational states."""

    def __init__(
        self,
        current_ref_date: Optional[date] = None,
        freshness_current_days: int = FRESHNESS_CURRENT_MAX_DAYS,
        freshness_delayed_days: int = FRESHNESS_DELAYED_MAX_DAYS
    ):
        self.ref_date = current_ref_date or datetime.now(timezone.utc).date()
        self.freshness_current_days = freshness_current_days
        self.freshness_delayed_days = freshness_delayed_days

    def evaluate_freshness(self, observation_date_str: Optional[str]) -> Tuple[FreshnessStatus, Optional[int]]:
        """
        Evaluate freshness of the newest observation date.
        
        Rule:
        - lag <= 2 days: CURRENT
        - 3 <= lag <= 5 days: DELAYED
        - lag > 5 days: STALE
        """
        if not observation_date_str:
            return FreshnessStatus.UNKNOWN, None

        try:
            # Handle ISO or YYYY-MM-DD
            obs_date = datetime.strptime(observation_date_str[:10], "%Y-%m-%d").date()
        except ValueError:
            try:
                obs_date = datetime.strptime(observation_date_str[:10], "%d/%m/%Y").date()
            except ValueError:
                return FreshnessStatus.UNKNOWN, None

        lag_days = (self.ref_date - obs_date).days

        # Future-dated observation (lag < 0): rejected from CURRENT, flagged as UNKNOWN
        if lag_days < 0:
            return FreshnessStatus.UNKNOWN, lag_days
        elif lag_days <= self.freshness_current_days:
            return FreshnessStatus.CURRENT, lag_days
        elif lag_days <= self.freshness_delayed_days:
            return FreshnessStatus.DELAYED, lag_days
        else:
            return FreshnessStatus.STALE, lag_days

    def determine_state(
        self,
        is_fetch_success: bool,
        is_source_available: bool,
        has_prior_snapshot: bool,
        is_partial_response: bool,
        records_quarantined: int,
        records_new: int,
        freshness: FreshnessStatus,
    ) -> OperationalState:
        """
        Determine which of the 7 mutually exclusive operational states applies.
        """
        # 1. Total Failure: No source and no prior data
        if not is_source_available and not has_prior_snapshot:
            return OperationalState.UNINITIALIZED

        # 2. Source Down with fallback
        if not is_source_available and has_prior_snapshot:
            return OperationalState.SOURCE_DOWN

        # 3. Partial / truncated response from live source
        if is_partial_response:
            return OperationalState.PARTIAL

        # 4. Quarantined records during validation
        if records_quarantined > 0:
            return OperationalState.QUARANTINED

        # 5. Live fetch succeeded but observations are stale (e.g. source hasn't published new data)
        if freshness in (FreshnessStatus.STALE, FreshnessStatus.DELAYED):
            return OperationalState.STALE_DATA

        # 6. Fetch succeeded but zero new records (idempotent / unchanged)
        if is_fetch_success and records_new == 0:
            return OperationalState.UNCHANGED

        # 7. Clean success
        if is_fetch_success and records_new > 0:
            return OperationalState.SUCCESS

        return OperationalState.SUCCESS

    def build_report_from_summary(
        self,
        summary_dict: Dict[str, Any],
        is_source_live: bool = False,
        source_available: bool = True,
        is_partial: bool = False,
        records_new_override: Optional[int] = None
    ) -> HealthReport:
        """Build a full HealthReport from a validation_summary.json structure."""
        counts = summary_dict.get("counts", {})
        coverage = summary_dict.get("temporal_coverage", {})
        artifacts = summary_dict.get("published_artifacts", {})

        latest_obs_str = coverage.get("latest_arrival_date")
        fetch_utc = summary_dict.get("execution_timestamp_utc")

        # Convert fetch_utc to local IST string
        fetch_local_str = None
        if fetch_utc:
            try:
                dt_utc = datetime.fromisoformat(fetch_utc.replace("Z", "+00:00"))
                dt_ist = dt_utc.astimezone(timezone(timedelta(hours=5, minutes=30)))
                fetch_local_str = dt_ist.strftime("%Y-%m-%d %H:%M:%S IST")
            except Exception:
                fetch_local_str = fetch_utc

        freshness_status, lag_days = self.evaluate_freshness(latest_obs_str)

        # Count fields
        raw_rows = counts.get("total_input_raw_records", 0)
        accepted_rows = counts.get("total_accepted_clean_records", 0)
        invalid_q = counts.get("total_quarantined_invalid_records", 0)
        conflict_q = counts.get("total_quarantined_conflicting_records", 0)
        total_quarantined = invalid_q + conflict_q
        exact_dups = counts.get("total_exact_duplicates_deduplicated", 0)
        unique_keys = counts.get("unique_series_retained", 0)

        # New records logic
        records_new = records_new_override if records_new_override is not None else accepted_rows

        accepted_meta = artifacts.get("accepted_dataset_csv", {})
        snapshot_sha = accepted_meta.get("sha256")

        ledger = ReconciliationLedger(
            source_total_records=raw_rows,
            records_fetched=raw_rows,
            records_parsed=raw_rows,
            records_accepted=accepted_rows,
            records_quarantined=total_quarantined,
            records_unchanged=exact_dups,
            records_corrected=conflict_q,
            records_new=records_new,
            current_unique_keys=unique_keys,
            latest_observation_date=latest_obs_str,
            last_successful_fetch_utc=fetch_utc,
            snapshot_sha256=snapshot_sha
        )

        has_snapshot = bool(accepted_rows > 0)
        op_state = self.determine_state(
            is_fetch_success=True,
            is_source_available=source_available,
            has_prior_snapshot=has_snapshot,
            is_partial_response=is_partial,
            records_quarantined=total_quarantined,
            records_new=records_new,
            freshness=freshness_status
        )

        warnings = []
        if total_quarantined > 0:
            warnings.append(f"{total_quarantined} records quarantined ({invalid_q} invalid price/bounds, {conflict_q} conflicting same-day quotes).")
        if not latest_obs_str:
            warnings.append("MISSING OBSERVATION DATE WARNING: Dataset contains no valid observation date.")
        elif lag_days is not None and lag_days < 0:
            warnings.append(f"FUTURE-DATED OBSERVATION WARNING: Latest observation ({latest_obs_str}) is {abs(lag_days)} days ahead of reference date ({self.ref_date}).")
        elif freshness_status == FreshnessStatus.STALE:
            warnings.append(f"STALE DATA WARNING: Latest observation ({latest_obs_str}) is {lag_days} days behind reference date ({self.ref_date}).")
        elif freshness_status == FreshnessStatus.DELAYED:
            warnings.append(f"DELAYED DATA NOTICE: Latest observation ({latest_obs_str}) is {lag_days} days old.")
        if is_partial:
            warnings.append("PARTIAL DATA WARNING: Source pagination did not complete 100% of pages.")
        if not source_available and has_snapshot:
            warnings.append("FALLBACK ACTIVE: Live source was unavailable. Report is generated from prior validated offline snapshot.")

        return HealthReport(
            source_name=DEFAULT_SOURCE_NAME,
            resource_id=DEFAULT_RESOURCE_ID,
            operational_state=op_state,
            freshness_status=freshness_status,
            freshness_lag_days=lag_days,
            latest_observation_date=latest_obs_str,
            last_successful_fetch_utc=fetch_utc,
            last_successful_fetch_local=fetch_local_str,
            is_source_live=is_source_live,
            is_fallback_active=(not source_available and has_snapshot),
            reconciliation=ledger,
            districts_represented=counts.get("unique_districts", []),
            markets_count=counts.get("unique_markets_count", 0),
            commodities_count=counts.get("unique_commodities_count", 0),
            warnings=warnings,
            errors=[]
        )

    @classmethod
    def load_from_processed_directory(
        cls,
        processed_dir: str,
        current_ref_date: Optional[date] = None,
        source_available: bool = True,
        is_partial: bool = False
    ) -> HealthReport:
        """Helper to instantiate engine and parse local data/processed directory."""
        summary_path = os.path.join(processed_dir, "validation_summary.json")
        if not os.path.exists(summary_path):
            # Return uninitialized report
            engine = cls(current_ref_date=current_ref_date)
            return HealthReport(
                operational_state=OperationalState.UNINITIALIZED,
                freshness_status=FreshnessStatus.UNKNOWN,
                errors=[f"Validation summary file not found: {summary_path}"]
            )

        with open(summary_path, "r", encoding="utf-8") as f:
            summary_dict = json.load(f)

        engine = cls(current_ref_date=current_ref_date)
        return engine.build_report_from_summary(
            summary_dict,
            is_source_live=False,
            source_available=source_available,
            is_partial=is_partial
        )


@dataclass
class SafetyGateDecision:
    """Standardized decision payload produced by the recommendation safety gate."""
    is_permitted: bool
    recommendation_status: str       # "ACTIVE", "DELAYED", "BLOCKED", "HISTORICAL_ONLY", "DEMO"
    freshness_status: str            # "CURRENT", "DELAYED", "STALE", "UNKNOWN"
    operational_state: str           # e.g., "SUCCESS", "STALE_DATA", "SOURCE_DOWN", etc.
    observation_date: Optional[str]
    reference_date: str
    lag_days: Optional[int]
    message: str
    blocked_reason: Optional[str] = None
    warning: Optional[str] = None
    is_demo: bool = False
    is_historical: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RecommendationSafetyGate:
    """
    Operational Safety Gate for Farmer-Facing Advisory and Storage Recommendations.

    Enforces that active recommendations (such as sell vs store decisions or market condition advice)
    cannot be issued on stale market quotes, missing dates, future dates, uninitialized pipelines,
    or downed sources without verified fresh alternative feeds.
    """

    def __init__(
        self,
        current_ref_date: Optional[date] = None,
        freshness_current_days: int = FRESHNESS_CURRENT_MAX_DAYS,
        freshness_delayed_days: int = FRESHNESS_DELAYED_MAX_DAYS
    ):
        self.ref_date = current_ref_date or datetime.now(timezone.utc).date()
        self.engine = HealthStatusEngine(
            current_ref_date=self.ref_date,
            freshness_current_days=freshness_current_days,
            freshness_delayed_days=freshness_delayed_days
        )

    def evaluate_gate(
        self,
        observation_date: Optional[Union[str, date, datetime]] = None,
        operational_state: Optional[OperationalState] = None,
        is_demo: bool = False,
        is_historical_analysis: bool = False,
        source_available: bool = True,
        has_verified_fresh_alternative: bool = False
    ) -> SafetyGateDecision:
        """
        Evaluate whether a farmer-facing recommendation may proceed.
        """
        ref_str = self.ref_date.isoformat()

        # Parse observation date to string YYYY-MM-DD
        obs_str: Optional[str] = None
        if observation_date is not None:
            if isinstance(observation_date, (datetime, date)):
                obs_str = observation_date.strftime("%Y-%m-%d")
            else:
                obs_str = str(observation_date).strip()[:10]

        # 1. Demo Mode Isolation
        if is_demo:
            return SafetyGateDecision(
                is_permitted=False,
                recommendation_status=RecommendationStatus.DEMO.value,
                freshness_status=FreshnessStatus.UNKNOWN.value,
                operational_state=operational_state.value if operational_state else OperationalState.UNCHANGED.value,
                observation_date=obs_str,
                reference_date=ref_str,
                lag_days=None,
                message="DEMO MODE — Illustrative simulation only; not a real mandi feed.",
                blocked_reason="Demo simulation data cannot be used for commercial or operational advice.",
                warning="DEMO RUN: Not a real market observation.",
                is_demo=True,
                is_historical=False
            )

        # 2. Historical Research / Backtest Mode
        if is_historical_analysis:
            freshness, lag = self.engine.evaluate_freshness(obs_str)
            return SafetyGateDecision(
                is_permitted=True,
                recommendation_status=RecommendationStatus.HISTORICAL_ONLY.value,
                freshness_status=freshness.value,
                operational_state=operational_state.value if operational_state else OperationalState.SUCCESS.value,
                observation_date=obs_str,
                reference_date=ref_str,
                lag_days=lag,
                message="Historical analysis only; not an active market advisory.",
                blocked_reason=None,
                warning="HISTORICAL EVALUATION: Output reflects past data for research and backtesting.",
                is_demo=False,
                is_historical=True
            )

        # 3. Uninitialized Pipeline
        if operational_state == OperationalState.UNINITIALIZED:
            return SafetyGateDecision(
                is_permitted=False,
                recommendation_status=RecommendationStatus.BLOCKED.value,
                freshness_status=FreshnessStatus.UNKNOWN.value,
                operational_state=OperationalState.UNINITIALIZED.value,
                observation_date=obs_str,
                reference_date=ref_str,
                lag_days=None,
                message=BLOCKED_RECOMMENDATION_MESSAGE,
                blocked_reason="System uninitialized; no validated market snapshot exists.",
                warning="Pipeline is uninitialized.",
                is_demo=False,
                is_historical=False
            )

        # 4. Source Down without Fresh Alternative
        if (operational_state == OperationalState.SOURCE_DOWN or not source_available) and not has_verified_fresh_alternative:
            freshness, lag = self.engine.evaluate_freshness(obs_str)
            return SafetyGateDecision(
                is_permitted=False,
                recommendation_status=RecommendationStatus.BLOCKED.value,
                freshness_status=freshness.value,
                operational_state=OperationalState.SOURCE_DOWN.value,
                observation_date=obs_str,
                reference_date=ref_str,
                lag_days=lag,
                message=BLOCKED_RECOMMENDATION_MESSAGE,
                blocked_reason="Upstream source is down and no fresh alternative data feed is verified.",
                warning="Source unavailable; fallback data is not verified as current.",
                is_demo=False,
                is_historical=False
            )

        # 5. Missing or Unparseable Observation Date
        if not obs_str:
            return SafetyGateDecision(
                is_permitted=False,
                recommendation_status=RecommendationStatus.BLOCKED.value,
                freshness_status=FreshnessStatus.UNKNOWN.value,
                operational_state=operational_state.value if operational_state else OperationalState.STALE_DATA.value,
                observation_date=None,
                reference_date=ref_str,
                lag_days=None,
                message=BLOCKED_RECOMMENDATION_MESSAGE,
                blocked_reason="Observation date is missing or invalid; cannot confirm freshness.",
                warning="Missing observation date cannot be treated as current.",
                is_demo=False,
                is_historical=False
            )

        freshness, lag = self.engine.evaluate_freshness(obs_str)

        # 6. Future-Dated Observation
        if lag is not None and lag < 0:
            return SafetyGateDecision(
                is_permitted=False,
                recommendation_status=RecommendationStatus.BLOCKED.value,
                freshness_status=FreshnessStatus.UNKNOWN.value,
                operational_state=OperationalState.QUARANTINED.value,
                observation_date=obs_str,
                reference_date=ref_str,
                lag_days=lag,
                message=BLOCKED_RECOMMENDATION_MESSAGE,
                blocked_reason=f"Observation date ({obs_str}) is in the future relative to reference date ({ref_str}).",
                warning=f"Future-dated record ({abs(lag)} days ahead of reference date) rejected.",
                is_demo=False,
                is_historical=False
            )

        # 7. Stale Data (lag > 5 days)
        if freshness == FreshnessStatus.STALE:
            op_st = operational_state.value if operational_state else OperationalState.STALE_DATA.value
            return SafetyGateDecision(
                is_permitted=False,
                recommendation_status=RecommendationStatus.BLOCKED.value,
                freshness_status=FreshnessStatus.STALE.value,
                operational_state=op_st,
                observation_date=obs_str,
                reference_date=ref_str,
                lag_days=lag,
                message=BLOCKED_RECOMMENDATION_MESSAGE,
                blocked_reason=f"Market data is stale ({lag} calendar days lag > threshold {self.engine.freshness_delayed_days} days).",
                warning=f"STALE DATA WARNING: Latest observation is {lag} days old. Not a live price.",
                is_demo=False,
                is_historical=False
            )

        # 8. Delayed Data (3 to 5 days lag)
        if freshness == FreshnessStatus.DELAYED:
            op_st = operational_state.value if operational_state else OperationalState.SUCCESS.value
            return SafetyGateDecision(
                is_permitted=True,
                recommendation_status=RecommendationStatus.DELAYED.value,
                freshness_status=FreshnessStatus.DELAYED.value,
                operational_state=op_st,
                observation_date=obs_str,
                reference_date=ref_str,
                lag_days=lag,
                message=f"Notice: Market observations are delayed by {lag} days. Not a live or today's price quote.",
                blocked_reason=None,
                warning=f"DELAYED DATA NOTICE: Observation date is {obs_str} ({lag} days lag).",
                is_demo=False,
                is_historical=False
            )

        # 9. Current Data (0 to 2 days lag)
        op_st = operational_state.value if operational_state else OperationalState.SUCCESS.value
        return SafetyGateDecision(
            is_permitted=True,
            recommendation_status=RecommendationStatus.ACTIVE.value,
            freshness_status=FreshnessStatus.CURRENT.value,
            operational_state=op_st,
            observation_date=obs_str,
            reference_date=ref_str,
            lag_days=lag,
            message=f"Market data is current as of observation date {obs_str}.",
            blocked_reason=None,
            warning=None,
            is_demo=False,
            is_historical=False
        )
