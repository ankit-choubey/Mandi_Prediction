"""
forecast_features.py — Shared Causal Feature Builder for APMC Mandi Price Forecasting

Implements strict causal price-only feature construction for training and inference.
Guarantees:
- Purely retrospective causal features: inputs visible strictly <= origin_date t.
- Zero future-target, target-move, or forecast-error leakage.
- Exact calendar lags (1, 3, 7, 14, 28 calendar days; unobserved days stay NaN).
- Preceding calendar rolling windows ([t-7, t-1] and [t-30, t-1]; minimum observations
  strictly enforced; std ddof=1 with missing burn-in for count < 2).
- Grade identity preservation: missing grade is SOURCE_NOT_PROVIDED, never merged with FAQ.
- Order-invariant conflict resolution: divergent quotes on the same date are rejected.
- Exact equivalence between batch training features and single-origin inference features.
- Exportable feature schema with units, data types, missingness policies, and code hash.
"""

from __future__ import annotations

import hashlib
import inspect
import math
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

import numpy as np
import pandas as pd

__version__ = "1.0.0"

GRADE_NOT_PROVIDED = "SOURCE_NOT_PROVIDED"
PUBLISHED_PRICE_UNIT = "Rs./Quintal"

CALENDAR_LAGS: Tuple[int, ...] = (1, 3, 7, 14, 28)
ROLLING_WINDOWS_DAYS: Tuple[int, ...] = (7, 30)

FEATURE_COLUMNS: List[str] = [
    "current_price",
    "price_lag_1",
    "price_lag_3",
    "price_lag_7",
    "price_lag_14",
    "price_lag_28",
    "last_observation_age_days",
    "rolling_count_7d",
    "rolling_mean_7d",
    "rolling_std_7d",
    "rolling_count_30d",
    "rolling_mean_30d",
    "rolling_std_30d",
    "day_of_week",
    "day_of_week_sin",
    "day_of_week_cos",
    "month",
    "month_sin",
    "month_cos",
    "day_of_month",
    "day_of_year",
]


@dataclass(frozen=True)
class SeriesIdentity:
    """Immutable, sorted, uniquely identifiable APMC series tuple."""
    district: str
    market: str
    commodity: str
    variety: str
    grade: str

    def as_tuple(self) -> Tuple[str, str, str, str, str]:
        return (self.district, self.market, self.commodity, self.variety, self.grade)

    def series_id(self) -> str:
        return f"{self.district}|{self.market}|{self.commodity}|{self.variety}|{self.grade}"


@dataclass
class TargetEvaluationResult:
    """Evaluation target extracted causal with respect to fold boundaries."""
    origin_date: str
    target_date: Optional[str]
    target_price: Optional[float]
    horizon_days: int
    offset_from_h7: Optional[int]
    exact_t7_price: Optional[float]
    target_status: str
    is_matured_before_cutoff: bool


def get_code_version_hash() -> str:
    """Compute deterministic SHA-256 hash of this module's source code."""
    source_code = inspect.getsource(inspect.getmodule(get_code_version_hash))
    return hashlib.sha256(source_code.encode("utf-8")).hexdigest()


def get_feature_schema() -> List[Dict[str, Any]]:
    """Export machine-readable feature schema including units, dtypes, and missingness."""
    return [
        {
            "name": "current_price",
            "dtype": "float64",
            "unit": PUBLISHED_PRICE_UNIT,
            "description": "Modal price observed on origin date t.",
            "missing_handling": "Preserved as NaN if unobserved on date t; requires explicit imputer during model training.",
            "causality": "Dated exactly t.",
        },
        {
            "name": "price_lag_1",
            "dtype": "float64",
            "unit": PUBLISHED_PRICE_UNIT,
            "description": "Modal price observed on exact calendar date t-1.",
            "missing_handling": "Preserved as NaN if date t-1 was unobserved; no forward-fill across calendar gaps.",
            "causality": "Dated exactly t-1.",
        },
        {
            "name": "price_lag_3",
            "dtype": "float64",
            "unit": PUBLISHED_PRICE_UNIT,
            "description": "Modal price observed on exact calendar date t-3.",
            "missing_handling": "Preserved as NaN if date t-3 was unobserved.",
            "causality": "Dated exactly t-3.",
        },
        {
            "name": "price_lag_7",
            "dtype": "float64",
            "unit": PUBLISHED_PRICE_UNIT,
            "description": "Modal price observed on exact calendar date t-7 (same day of week).",
            "missing_handling": "Preserved as NaN if date t-7 was unobserved.",
            "causality": "Dated exactly t-7.",
        },
        {
            "name": "price_lag_14",
            "dtype": "float64",
            "unit": PUBLISHED_PRICE_UNIT,
            "description": "Modal price observed on exact calendar date t-14.",
            "missing_handling": "Preserved as NaN if date t-14 was unobserved.",
            "causality": "Dated exactly t-14.",
        },
        {
            "name": "price_lag_28",
            "dtype": "float64",
            "unit": PUBLISHED_PRICE_UNIT,
            "description": "Modal price observed on exact calendar date t-28.",
            "missing_handling": "Preserved as NaN if date t-28 was unobserved.",
            "causality": "Dated exactly t-28.",
        },
        {
            "name": "last_observation_age_days",
            "dtype": "float64",
            "unit": "Days",
            "description": "Calendar days between origin date t and the most recent valid observation <= t.",
            "missing_handling": "0.0 if t is observed; k if last observed at t-k; NaN if no prior history exists.",
            "causality": "Uses only history <= t.",
        },
        {
            "name": "rolling_count_7d",
            "dtype": "int64",
            "unit": "Count",
            "description": "Number of trading observations in preceding 7 calendar days [t-7, t-1].",
            "missing_handling": "Always non-negative integer (0 to 7).",
            "causality": "Preceding window exclusive of t.",
        },
        {
            "name": "rolling_mean_7d",
            "dtype": "float64",
            "unit": PUBLISHED_PRICE_UNIT,
            "description": "Arithmetic mean of observed modal prices in preceding window [t-7, t-1].",
            "missing_handling": "NaN if rolling_count_7d < 1 (no observations in 7-day span).",
            "causality": "Preceding window exclusive of t.",
        },
        {
            "name": "rolling_std_7d",
            "dtype": "float64",
            "unit": PUBLISHED_PRICE_UNIT,
            "description": "Sample standard deviation (ddof=1) of observed prices in preceding window [t-7, t-1].",
            "missing_handling": "NaN if rolling_count_7d < 2 (burn-in requirement for sample variance).",
            "causality": "Preceding window exclusive of t.",
        },
        {
            "name": "rolling_count_30d",
            "dtype": "int64",
            "unit": "Count",
            "description": "Number of trading observations in preceding 30 calendar days [t-30, t-1].",
            "missing_handling": "Always non-negative integer (0 to 30).",
            "causality": "Preceding window exclusive of t.",
        },
        {
            "name": "rolling_mean_30d",
            "dtype": "float64",
            "unit": PUBLISHED_PRICE_UNIT,
            "description": "Arithmetic mean of observed modal prices in preceding window [t-30, t-1].",
            "missing_handling": "NaN if rolling_count_30d < 1.",
            "causality": "Preceding window exclusive of t.",
        },
        {
            "name": "rolling_std_30d",
            "dtype": "float64",
            "unit": PUBLISHED_PRICE_UNIT,
            "description": "Sample standard deviation (ddof=1) of observed prices in preceding window [t-30, t-1].",
            "missing_handling": "NaN if rolling_count_30d < 2 (burn-in requirement for sample variance).",
            "causality": "Preceding window exclusive of t.",
        },
        {
            "name": "day_of_week",
            "dtype": "int64",
            "unit": "DayIndex",
            "description": "Day of week of origin date t (0=Monday, 6=Sunday).",
            "missing_handling": "Deterministic calendar integer.",
            "causality": "Derived from origin date t.",
        },
        {
            "name": "day_of_week_sin",
            "dtype": "float64",
            "unit": "Trigonometric",
            "description": "sin(2 * pi * day_of_week / 7).",
            "missing_handling": "Deterministic float in [-1.0, 1.0].",
            "causality": "Derived from origin date t.",
        },
        {
            "name": "day_of_week_cos",
            "dtype": "float64",
            "unit": "Trigonometric",
            "description": "cos(2 * pi * day_of_week / 7).",
            "missing_handling": "Deterministic float in [-1.0, 1.0].",
            "causality": "Derived from origin date t.",
        },
        {
            "name": "month",
            "dtype": "int64",
            "unit": "MonthIndex",
            "description": "Calendar month of origin date t (1 to 12).",
            "missing_handling": "Deterministic calendar integer.",
            "causality": "Derived from origin date t.",
        },
        {
            "name": "month_sin",
            "dtype": "float64",
            "unit": "Trigonometric",
            "description": "sin(2 * pi * (month - 1) / 12).",
            "missing_handling": "Deterministic float in [-1.0, 1.0].",
            "causality": "Derived from origin date t.",
        },
        {
            "name": "month_cos",
            "dtype": "float64",
            "unit": "Trigonometric",
            "description": "cos(2 * pi * (month - 1) / 12).",
            "missing_handling": "Deterministic float in [-1.0, 1.0].",
            "causality": "Derived from origin date t.",
        },
        {
            "name": "day_of_month",
            "dtype": "int64",
            "unit": "DayOfMonth",
            "description": "Day of month of origin date t (1 to 31).",
            "missing_handling": "Deterministic calendar integer.",
            "causality": "Derived from origin date t.",
        },
        {
            "name": "day_of_year",
            "dtype": "int64",
            "unit": "DayOfYear",
            "description": "Day of year of origin date t (1 to 366).",
            "missing_handling": "Deterministic calendar integer.",
            "causality": "Derived from origin date t.",
        },
    ]


class ForecastFeatureBuilder:
    """
    Shared Causal Feature Builder for APMC mandi continuous price forecasting.
    Provides identical feature calculation for batch training datasets and
    single-origin live/offline inference.
    """

    def __init__(
        self,
        alias_mapping: Optional[Dict[Tuple[str, str], Dict[str, Any]]] = None,
    ):
        self.alias_mapping = alias_mapping or {}

    def normalize_series_identity(
        self,
        district: str,
        market: str,
        commodity: str,
        variety: str,
        grade: Optional[str] = None,
    ) -> SeriesIdentity:
        """Construct normalized, immutable series identity with canonical market handling."""
        d_clean = district.strip()
        m_raw = market.strip()
        c_clean = commodity.strip()
        v_clean = variety.strip() or "Other"

        # Market canonicalization
        m_canon = m_raw
        if self.alias_mapping:
            alias_key = (d_clean, m_raw)
            if alias_key in self.alias_mapping:
                entry = self.alias_mapping[alias_key]
                status = str(entry.get("status", "")).strip().upper()
                action = str(entry.get("action", "")).strip().upper()
                if status in ("ACCEPTED", "CANONICAL") or action in ("MAP_CANONICAL", "EXACT_CANONICAL", "ACCEPTED"):
                    m_canon = entry.get("market_canonical") or m_raw

        # Grade normalization: never silently merge missing grade with FAQ
        if grade is None or str(grade).strip() == "":
            g_norm = GRADE_NOT_PROVIDED
        else:
            g_norm = str(grade).strip()

        return SeriesIdentity(
            district=d_clean,
            market=m_canon,
            commodity=c_clean,
            variety=v_clean,
            grade=g_norm,
        )

    def resolve_raw_series_records(
        self,
        records: Sequence[Dict[str, Any]],
    ) -> Tuple[Dict[SeriesIdentity, Dict[date, float]], Dict[str, int]]:
        """
        Group records by SeriesIdentity and resolve calendar-date conflicts.
        Guarantees:
        - Exact duplicate prices on the same date are deduplicated to a single observation.
        - Divergent price quotes on the same date are rejected/quarantined as ambiguous.
        """
        raw_groups: Dict[SeriesIdentity, Dict[date, List[float]]] = {}
        conflict_count = 0
        duplicate_count = 0
        accepted_count = 0

        for r in records:
            d_val = str(r.get("District") or r.get("district") or "").strip()
            m_val = str(r.get("Market") or r.get("market") or "").strip()
            c_val = str(r.get("Commodity") or r.get("commodity") or "").strip()
            v_val = str(r.get("Variety") or r.get("variety") or "Other").strip()
            g_val = r.get("Grade") or r.get("grade") or r.get("grade_normalized")

            date_val = r.get("Arrival_Date") or r.get("arrival_date")
            if isinstance(date_val, datetime):
                obs_d = date_val.date()
            elif isinstance(date_val, date):
                obs_d = date_val
            elif isinstance(date_val, str):
                cleaned = date_val.strip()[:10]
                obs_d = None
                for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
                    try:
                        obs_d = datetime.strptime(cleaned, fmt).date()
                        break
                    except ValueError:
                        continue
                if obs_d is None:
                    continue
            else:
                continue

            price_raw = r.get("Modal_Price") or r.get("modal_price") or r.get("Price") or r.get("price")
            if price_raw is None:
                continue
            try:
                price = float(price_raw)
            except (ValueError, TypeError):
                continue
            if not math.isfinite(price) or price <= 0:
                continue

            series_key = self.normalize_series_identity(d_val, m_val, c_val, v_val, g_val)
            raw_groups.setdefault(series_key, {}).setdefault(obs_d, []).append(price)

        clean_series_map: Dict[SeriesIdentity, Dict[date, float]] = {}
        for s_key, date_dict in raw_groups.items():
            clean_date_map: Dict[date, float] = {}
            for obs_d, prices in date_dict.items():
                if len(prices) == 1:
                    clean_date_map[obs_d] = prices[0]
                    accepted_count += 1
                else:
                    unique_prices = set(prices)
                    if len(unique_prices) == 1:
                        # Identical quotes on same date: deduplicate safely
                        clean_date_map[obs_d] = prices[0]
                        duplicate_count += len(prices) - 1
                        accepted_count += 1
                    else:
                        # Divergent quotes: quarantine this date ambiguity entirely
                        conflict_count += len(prices)
            clean_series_map[s_key] = clean_date_map

        stats = {
            "accepted_dates": accepted_count,
            "deduplicated_records": duplicate_count,
            "conflicted_records_rejected": conflict_count,
        }
        return clean_series_map, stats

    def compute_origin_features(
        self,
        clean_history: Dict[date, float],
        origin_date: Union[date, str],
        series: Optional[SeriesIdentity] = None,
    ) -> Dict[str, Any]:
        """
        Compute causal price-only features for a single origin date.
        Strictly observes ONLY historical dates <= origin_date.
        """
        if isinstance(origin_date, str):
            t = datetime.strptime(origin_date[:10], "%Y-%m-%d").date()
        else:
            t = origin_date

        # Filter history causally: strictly <= t
        available_history = {d: p for d, p in clean_history.items() if d <= t}

        # 1. Current Price
        current_price = available_history.get(t, np.nan)

        # 2. Exact Calendar Lags (unobserved stays NaN)
        lags: Dict[str, float] = {}
        for lag_days in CALENDAR_LAGS:
            lag_target_date = t - timedelta(days=lag_days)
            lags[f"price_lag_{lag_days}"] = available_history.get(lag_target_date, np.nan)

        # 3. Last Observation Age
        prior_dates = [d for d in available_history.keys() if d <= t]
        if prior_dates:
            last_observed_date = max(prior_dates)
            last_obs_age = float((t - last_observed_date).days)
        else:
            last_obs_age = np.nan

        # 4. Rolling Preceding Windows (exclusive of t: [t-W, t-1])
        rolling_stats: Dict[str, Any] = {}
        for w_days in ROLLING_WINDOWS_DAYS:
            w_start = t - timedelta(days=w_days)
            w_end = t - timedelta(days=1)
            w_prices = [p for d, p in available_history.items() if w_start <= d <= w_end]

            count_w = len(w_prices)
            rolling_stats[f"rolling_count_{w_days}d"] = count_w
            if count_w >= 1:
                rolling_stats[f"rolling_mean_{w_days}d"] = float(np.mean(w_prices))
            else:
                rolling_stats[f"rolling_mean_{w_days}d"] = np.nan

            # Sample standard deviation (ddof=1) requires at least 2 observations
            if count_w >= 2:
                rolling_stats[f"rolling_std_{w_days}d"] = float(np.std(w_prices, ddof=1))
            else:
                rolling_stats[f"rolling_std_{w_days}d"] = np.nan

        # 5. Calendar Encodings
        dow = t.weekday()  # 0=Monday, 6=Sunday
        month = t.month
        day_of_month = t.day
        day_of_year = t.timetuple().tm_yday

        dow_sin = float(math.sin(2.0 * math.pi * dow / 7.0))
        dow_cos = float(math.cos(2.0 * math.pi * dow / 7.0))
        month_sin = float(math.sin(2.0 * math.pi * (month - 1) / 12.0))
        month_cos = float(math.cos(2.0 * math.pi * (month - 1) / 12.0))

        feat_dict: Dict[str, Any] = {
            "origin_date": t.isoformat(),
            "current_price": current_price,
            **lags,
            "last_observation_age_days": last_obs_age,
            **rolling_stats,
            "day_of_week": dow,
            "day_of_week_sin": dow_sin,
            "day_of_week_cos": dow_cos,
            "month": month,
            "month_sin": month_sin,
            "month_cos": month_cos,
            "day_of_month": day_of_month,
            "day_of_year": day_of_year,
        }

        if series is not None:
            feat_dict["series_id"] = series.series_id()
            feat_dict["district"] = series.district
            feat_dict["market"] = series.market
            feat_dict["commodity"] = series.commodity
            feat_dict["variety"] = series.variety
            feat_dict["grade"] = series.grade

        return feat_dict

    def compute_batch_features(
        self,
        records_or_df: Union[pd.DataFrame, Sequence[Dict[str, Any]]],
        origin_dates_by_series: Optional[Dict[SeriesIdentity, Sequence[Union[date, str]]]] = None,
    ) -> pd.DataFrame:
        """
        Compute batch feature DataFrame across multiple series and dates.
        Strictly preserves exact equivalence with single-origin inference features.
        """
        if isinstance(records_or_df, pd.DataFrame):
            records = records_or_df.to_dict(orient="records")
        else:
            records = list(records_or_df)

        clean_series_map, _ = self.resolve_raw_series_records(records)
        rows: List[Dict[str, Any]] = []

        # Sort series identities stably
        sorted_series = sorted(clean_series_map.keys(), key=lambda s: s.as_tuple())

        for series_key in sorted_series:
            clean_history = clean_series_map[series_key]
            if not clean_history:
                continue

            if origin_dates_by_series and series_key in origin_dates_by_series:
                target_dates = origin_dates_by_series[series_key]
            else:
                # Default to all observed dates for this series
                target_dates = sorted(clean_history.keys())

            for d_val in target_dates:
                feat = self.compute_origin_features(
                    clean_history=clean_history,
                    origin_date=d_val,
                    series=series_key,
                )
                rows.append(feat)

        if not rows:
            meta_cols = ["origin_date", "series_id", "district", "market", "commodity", "variety", "grade"]
            return pd.DataFrame(columns=meta_cols + FEATURE_COLUMNS)

        df = pd.DataFrame(rows)
        # Order columns deterministically
        meta_cols = ["origin_date", "series_id", "district", "market", "commodity", "variety", "grade"]
        present_meta = [c for c in meta_cols if c in df.columns]
        ordered_cols = present_meta + [c for c in FEATURE_COLUMNS if c in df.columns]
        return df[ordered_cols]

    @staticmethod
    def compute_target(
        clean_series_history: Dict[date, float],
        origin_date: Union[date, str],
        horizon_days: int = 7,
        target_window: Tuple[int, int] = (6, 8),
        fold_end: Optional[Union[date, str]] = None,
        train_cutoff: Optional[Union[date, str]] = None,
    ) -> TargetEvaluationResult:
        """
        Compute continuous evaluation target according to frozen project contract:
        - Horizon 7: nominal target is t+7.
        - Candidate window: [t+6, t+8].
        - Nearest observed to t+7 selected; earlier tie-break (t+6 preferred over t+8 if t+7 missing).
        - Enforces fold_end boundary (actual target_date <= fold_end).
        - Computes exact T+7 price for sensitivity analysis.
        - Checks training maturity: actual target_date <= train_cutoff.
        """
        if isinstance(origin_date, str):
            t = datetime.strptime(origin_date[:10], "%Y-%m-%d").date()
        else:
            t = origin_date

        fold_end_d = None
        if fold_end:
            fold_end_d = datetime.strptime(fold_end[:10], "%Y-%m-%d").date() if isinstance(fold_end, str) else fold_end

        cutoff_d = None
        if train_cutoff:
            cutoff_d = datetime.strptime(train_cutoff[:10], "%Y-%m-%d").date() if isinstance(train_cutoff, str) else train_cutoff

        exact_t7_date = t + timedelta(days=horizon_days)
        exact_t7_price = clean_series_history.get(exact_t7_date)

        # Check candidate offsets in priority order:
        # Distance 0: offset 0 (t+7)
        # Distance 1: offset -1 (t+6) [tie earlier!], then offset +1 (t+8)
        w_start, w_end = target_window
        candidate_offsets = [0, -1, 1]  # priority order

        selected_date: Optional[date] = None
        selected_offset: Optional[int] = None
        selected_price: Optional[float] = None

        for offset in candidate_offsets:
            actual_offset_days = horizon_days + offset
            if actual_offset_days < w_start or actual_offset_days > w_end:
                continue
            cand_date = t + timedelta(days=actual_offset_days)
            if cand_date in clean_series_history:
                selected_date = cand_date
                selected_offset = actual_offset_days
                selected_price = clean_series_history[cand_date]
                break

        if selected_date is None:
            return TargetEvaluationResult(
                origin_date=t.isoformat(),
                target_date=None,
                target_price=None,
                horizon_days=horizon_days,
                offset_from_h7=None,
                exact_t7_price=exact_t7_price,
                target_status="NO_TARGET_IN_WINDOW",
                is_matured_before_cutoff=False,
            )

        # Check fold boundary
        if fold_end_d and selected_date > fold_end_d:
            return TargetEvaluationResult(
                origin_date=t.isoformat(),
                target_date=selected_date.isoformat(),
                target_price=None,
                horizon_days=horizon_days,
                offset_from_h7=selected_offset - horizon_days,
                exact_t7_price=exact_t7_price,
                target_status="TARGET_EXCEEDS_FOLD_END",
                is_matured_before_cutoff=False,
            )

        # Check training cutoff maturity
        is_matured = (cutoff_d is None) or (selected_date <= cutoff_d)

        return TargetEvaluationResult(
            origin_date=t.isoformat(),
            target_date=selected_date.isoformat(),
            target_price=selected_price,
            horizon_days=horizon_days,
            offset_from_h7=selected_offset - horizon_days,
            exact_t7_price=exact_t7_price,
            target_status="VALID_TARGET",
            is_matured_before_cutoff=is_matured,
        )

    @staticmethod
    def evaluate_series_train_eligibility(
        observed_dates: Sequence[Union[date, str]],
        train_cutoff: Union[date, str],
        min_tier_a_obs: int = 60,
        min_tier_b_obs: int = 120,
        min_coverage: float = 0.30,
    ) -> Tuple[bool, bool, Dict[str, Any]]:
        """
        Evaluate series training eligibility for Tier A and Tier B.
        - Filter history <= train_cutoff.
        - Coverage calculated over inclusive first-to-last observed trading span in train window.
        """
        cutoff_d = datetime.strptime(train_cutoff[:10], "%Y-%m-%d").date() if isinstance(train_cutoff, str) else train_cutoff

        parsed_dates = []
        for d in observed_dates:
            if isinstance(d, datetime):
                parsed_dates.append(d.date())
            elif isinstance(d, date):
                parsed_dates.append(d)
            elif isinstance(d, str):
                parsed_dates.append(datetime.strptime(d[:10], "%Y-%m-%d").date())

        train_dates = sorted([d for d in parsed_dates if d <= cutoff_d])
        n_train = len(train_dates)

        if n_train == 0:
            return False, False, {
                "n_train": 0,
                "span_days": 0,
                "coverage": 0.0,
                "tier_a": False,
                "tier_b": False,
            }

        first_d = train_dates[0]
        last_d = train_dates[-1]
        span_days = (last_d - first_d).days + 1
        coverage = float(n_train) / float(span_days) if span_days > 0 else 1.0

        tier_a = (n_train >= min_tier_a_obs) and (coverage >= min_coverage)
        tier_b = (n_train >= min_tier_b_obs) and (coverage >= min_coverage)

        return tier_a, tier_b, {
            "n_train": n_train,
            "span_days": span_days,
            "coverage": coverage,
            "tier_a": tier_a,
            "tier_b": tier_b,
        }

    @staticmethod
    def evaluate_origin_recency(
        clean_history: Dict[date, float],
        origin_date: Union[date, str],
        window_days: int = 30,
        min_recency_obs: int = 3,
    ) -> bool:
        """
        Evaluate origin recency condition: >= min_recency_obs observations in [t - window_days, t].
        """
        t = datetime.strptime(origin_date[:10], "%Y-%m-%d").date() if isinstance(origin_date, str) else origin_date
        w_start = t - timedelta(days=window_days)
        obs_count = sum(1 for d in clean_history.keys() if w_start <= d <= t)
        return obs_count >= min_recency_obs

