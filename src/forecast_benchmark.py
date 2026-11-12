"""
APMC Mandi Price Forecasting Benchmark Engine
Task: MP-FC-007 / MP-FC-007R

Implements the first price-only machine learning benchmark across four temporal folds (F1-F4)
under strict As-Of operational constraints, comparing Ridge Regression and
HistGradientBoostingRegressor against four rescored empirical baselines (Naive, Moving Average,
Seasonal Naive, Damped Drift).

Key Architectural Guarantees:
1. Strict Retrospective Causality: Features at origin date t observe observations <= t only.
2. Label Maturity Enforcement: Training origins require actual target_date <= train_cutoff.
3. Chronological Inner Validation: Two expanding splits per fold for hyperparameter tuning with
   exact 7-calendar-day embargo separation between inner fit cutoff and validation origin window.
4. Response Formulation: Additive price change delta = y_target - y_t; reconstructed y_hat = y_t + delta.
5. Invertible Abstention: Non-positive or non-finite reconstructed forecasts abstain with explicit reason.
6. Common-Sample Paired Skill: Skill score evaluated on matched finite pairs with series-cluster bootstrap 95% CIs.
7. Consistent Estimands & Schemas: Complete schemas across all slices, numeric CI fields, and undefined skill when denominator <= 0.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
import math
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.baselines import (
    parse_date,
    predict_naive,
    predict_moving_average,
    predict_seasonal_naive,
    predict_drift,
    extract_target,
)
from src.forecast_features import (
    ForecastFeatureBuilder,
    SeriesIdentity,
    FEATURE_COLUMNS,
    CALENDAR_LAGS,
    ROLLING_WINDOWS_DAYS,
)


def extract_manifest_dispositions(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts disposition metrics from a pipeline manifest dictionary without
    measurement fallback constants.

    Enforces fail-closed schema checks and strict row conservation:
      accepted_rows + duplicates_deduplicated + conflicts_quarantined +
      low_obs_dropped + invalid_dropped_rows == total_raw_rows

    Raises:
        KeyError: If required manifest or summary_metrics fields are missing.
        ValueError: If row conservation identity is violated.
    """
    if "summary_metrics" not in manifest:
        raise KeyError("Manifest is missing required top-level section: 'summary_metrics'")

    sm = manifest["summary_metrics"]
    required_keys = [
        "total_raw_rows",
        "total_valid_parsed_rows",
        "total_dropped_raw_rows",
        "exact_duplicates_deduplicated",
        "ambiguous_same_grade_excluded_rows",
        "low_observation_series_dropped_rows",
        "final_clean_rows",
    ]
    missing = [k for k in required_keys if k not in sm]
    if missing:
        raise KeyError(f"summary_metrics is missing required fields: {missing}")

    raw_rows_in = int(sm["total_raw_rows"])
    valid_parsed_rows = int(sm["total_valid_parsed_rows"])
    invalid_dropped = int(sm["total_dropped_raw_rows"])
    duplicates = int(sm["exact_duplicates_deduplicated"])
    conflicts = int(sm["ambiguous_same_grade_excluded_rows"])
    low_obs = int(sm["low_observation_series_dropped_rows"])
    accepted = int(sm["final_clean_rows"])

    # Disjoint partition conservation check:
    sum_dispositions = accepted + duplicates + conflicts + low_obs + invalid_dropped
    if sum_dispositions != raw_rows_in:
        raise ValueError(
            f"Row conservation assertion violated: "
            f"accepted ({accepted}) + dups ({duplicates}) + conflicts ({conflicts}) + "
            f"low_obs ({low_obs}) + invalid ({invalid_dropped}) = {sum_dispositions} != raw_in ({raw_rows_in})"
        )

    # Valid parsed conservation check:
    sum_valid_dispositions = accepted + duplicates + conflicts + low_obs
    if sum_valid_dispositions != valid_parsed_rows:
        raise ValueError(
            f"Valid parsed row conservation violated: "
            f"accepted ({accepted}) + dups ({duplicates}) + conflicts ({conflicts}) + "
            f"low_obs ({low_obs}) = {sum_valid_dispositions} != valid_parsed ({valid_parsed_rows})"
        )

    return {
        "raw_rows_in": raw_rows_in,
        "valid_parsed_rows": valid_parsed_rows,
        "invalid_dropped_rows": invalid_dropped,
        "duplicates_deduplicated": duplicates,
        "conflicts_quarantined": conflicts,
        "low_obs_dropped": low_obs,
        "accepted_rows": accepted,
        "row_conservation_verified": True,
    }


def classify_date_regime(origin_d: Union[date, datetime, pd.Timestamp, str]) -> str:
    """
    Classifies an observation origin date into historical, transition, or modern regime:
    - HISTORICAL: before 2025-11-01
    - TRANSITION: from 2025-11-01 through 2026-02-28
    - MODERN: from 2026-03-01 onwards
    Note: Regimes are purely descriptive chronological groupings; no causal claims inferred.
    """
    d = parse_date(origin_d).date()
    if d < date(2025, 11, 1):
        return "HISTORICAL"
    elif d <= date(2026, 2, 28):
        return "TRANSITION"
    else:
        return "MODERN"


@dataclass(frozen=True)
class TemporalFold:
    fold_id: str
    train_cutoff: date
    test_start: date
    test_end: date
    embargo_days: int = 7
    max_train_origin: date = field(init=False)
    regime: str = "HISTORICAL"

    def __post_init__(self):
        object.__setattr__(
            self,
            "max_train_origin",
            self.train_cutoff - timedelta(days=self.embargo_days + 1),
        )


@dataclass(frozen=True)
class InnerSplit:
    name: str
    val_start: date
    val_end: date
    inner_fit_cutoff: date
    inner_fit_max_origin: date
    embargo_days: int = 7


def get_standard_folds() -> List[TemporalFold]:
    """Return the four standard temporal folds F1-F4 for the APMC price benchmark."""
    return [
        TemporalFold(
            fold_id="F1",
            train_cutoff=date(2024, 12, 31),
            test_start=date(2025, 1, 8),
            test_end=date(2025, 6, 30),
            embargo_days=7,
            regime="HISTORICAL",
        ),
        TemporalFold(
            fold_id="F2",
            train_cutoff=date(2025, 6, 30),
            test_start=date(2025, 7, 8),
            test_end=date(2025, 10, 31),
            embargo_days=7,
            regime="HISTORICAL",
        ),
        TemporalFold(
            fold_id="F3",
            train_cutoff=date(2025, 12, 18),
            test_start=date(2025, 12, 26),
            test_end=date(2026, 3, 31),
            embargo_days=7,
            regime="TRANSITION",
        ),
        TemporalFold(
            fold_id="F4",
            train_cutoff=date(2026, 3, 31),
            test_start=date(2026, 4, 8),
            test_end=date(2026, 9, 30),
            embargo_days=7,
            regime="MODERN",
        ),
    ]


def get_inner_splits(fold: TemporalFold) -> List[InnerSplit]:
    """
    Generate the two prespecified expanding inner chronological splits for a fold.
    Split 1: Validation window [T_train - 119d, T_train - 60d], fit cutoff val_start - 8d.
    Split 2: Validation window [T_train - 59d, T_train], fit cutoff val_start - 8d.
    Enforces (val_start - inner_fit_cutoff).days - 1 == 7 (exactly 7 excluded calendar dates).
    Training actual target_date <= inner_fit_cutoff; validation target <= val_end.
    inner_fit_max_origin is clearly labeled conservative cap = inner_fit_cutoff - 8d.
    """
    t_train = fold.train_cutoff
    embargo = fold.embargo_days

    # Split 1
    val1_start = t_train - timedelta(days=119)
    val1_end = t_train - timedelta(days=60)
    fit1_cutoff = val1_start - timedelta(days=embargo + 1)  # val1_start - 8 days
    fit1_max_origin = fit1_cutoff - timedelta(days=embargo + 1)  # conservative cap

    s1 = InnerSplit(
        name="inner_split_1",
        val_start=val1_start,
        val_end=val1_end,
        inner_fit_cutoff=fit1_cutoff,
        inner_fit_max_origin=fit1_max_origin,
        embargo_days=embargo,
    )

    # Split 2
    val2_start = t_train - timedelta(days=59)
    val2_end = t_train
    fit2_cutoff = val2_start - timedelta(days=embargo + 1)  # val2_start - 8 days
    fit2_max_origin = fit2_cutoff - timedelta(days=embargo + 1)  # conservative cap

    s2 = InnerSplit(
        name="inner_split_2",
        val_start=val2_start,
        val_end=val2_end,
        inner_fit_cutoff=fit2_cutoff,
        inner_fit_max_origin=fit2_max_origin,
        embargo_days=embargo,
    )

    return [s1, s2]


def extract_series_target(
    history: Dict[date, float],
    origin_t: date,
    max_target_date: Optional[date] = None,
    horizon_days: int = 7,
    window_min: int = 6,
    window_max: int = 8,
) -> Tuple[Optional[float], Optional[date], bool]:
    """
    Extract closest observed modal price in [origin_t + 6, origin_t + 8] to origin_t + 7.
    Tie-breaker: earlier date.
    The nearest target in window is selected FIRST; if that selected target exceeds max_target_date,
    the origin is rejected (returns None, None, False) to prevent boundary target leakage.
    Returns (target_price, target_date, is_exact_t7).
    """
    exact_d = origin_t + timedelta(days=horizon_days)
    w_start = origin_t + timedelta(days=window_min)
    w_end = origin_t + timedelta(days=window_max)

    candidates = []
    for d, p in history.items():
        if w_start <= d <= w_end:
            diff = abs((d - exact_d).days)
            candidates.append((diff, d, p))

    if not candidates:
        return None, None, False

    # Sort by diff ascending, then date ascending (earlier tie-breaker)
    candidates.sort(key=lambda x: (x[0], x[1]))
    best_diff, best_d, best_p = candidates[0]

    # Maturity / boundary gate: if nearest selected target exceeds max_target_date, origin is excluded
    if max_target_date is not None and best_d > max_target_date:
        return None, None, False

    return float(best_p), best_d, (best_diff == 0)


def build_candidate_ridge_model(alpha: float = 1.0) -> Pipeline:
    """Build Ridge regression pipeline with median imputation and standard scaling."""
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
        ("scaler", StandardScaler()),
        ("ridge", Ridge(alpha=alpha, random_state=42)),
    ])


def build_candidate_hgb_model(
    max_depth: int = 3,
    min_samples_leaf: int = 20,
    learning_rate: float = 0.05,
    max_iter: int = 100,
) -> HistGradientBoostingRegressor:
    """Build HistGradientBoostingRegressor with native missing-value handling and early_stopping=False."""
    return HistGradientBoostingRegressor(
        max_iter=max_iter,
        max_depth=max_depth,
        min_samples_leaf=min_samples_leaf,
        learning_rate=learning_rate,
        random_state=42,
        early_stopping=False,
    )


def compute_scope_a_disputed_mask(
    df: pd.DataFrame,
    canonical_keys: Set[Tuple[str, str, str, str, str, str]],
) -> pd.Series:
    """
    Computes a boolean mask indicating whether a prediction row matches any of the
    77 canonical disputed keys in either origin date or target date.
    Canonical key tuple: (District_Std, Market_Canonical, Commodity_Std, Variety, Grade, Arrival_Date_str)
    """
    if df.empty or not canonical_keys:
        return pd.Series(False, index=df.index, dtype=bool)

    orig_dates = pd.to_datetime(df["origin_date"]).dt.strftime("%Y-%m-%d").values
    trg_dates = pd.to_datetime(df["target_date"]).dt.strftime("%Y-%m-%d").values

    dists = df["district"].astype(str).str.strip().values
    mkts = df["market"].astype(str).str.strip().values
    comms = df["commodity"].astype(str).str.strip().values
    vars_ = df["variety"].astype(str).str.strip().values
    grds = df["grade"].astype(str).str.strip().values

    is_disputed = [
        ((d, m, c, v, g, od) in canonical_keys or (d, m, c, v, g, td) in canonical_keys)
        for d, m, c, v, g, od, td in zip(dists, mkts, comms, vars_, grds, orig_dates, trg_dates)
    ]

    return pd.Series(is_disputed, index=df.index, dtype=bool)


class ForecastBenchmarkEngine:
    """
    Executes and coordinates the end-to-end price forecasting benchmark.
    Caches causal feature calculations and baseline lookups to avoid repeated scanning.
    """

    def __init__(
        self,
        feature_builder: Optional[ForecastFeatureBuilder] = None,
        focus_crops: Optional[Sequence[str]] = None,
    ):
        self.builder = feature_builder or ForecastFeatureBuilder()
        self.focus_crops = list(focus_crops) if focus_crops else [
            "Wheat",
            "Potato",
            "Onion",
            "Tomato",
            "Paddy(Dhan)(Common)",
            "Rice",
        ]
        self.folds = get_standard_folds()
        # Internal cache per series: series_tuple -> {origin_t: dict_of_precomputed_data}
        self._series_cache: Dict[Tuple, Dict[date, Dict[str, Any]]] = {}

    def evaluate_eligibility(
        self,
        history: Dict[date, float],
        cutoff: date,
    ) -> Dict[str, Any]:
        """Evaluate Tier A and Tier B eligibility on historical dates <= cutoff."""
        dates = [d for d in history.keys() if d <= cutoff]
        t_a, t_b, stats = self.builder.evaluate_series_train_eligibility(dates, cutoff)
        return {
            "tier_a": t_a,
            "tier_b": t_b,
            "train_observations": stats["n_train"],
            "coverage": stats["coverage"],
            "span_days": stats["span_days"],
        }

    def _get_or_compute_series_cache(
        self,
        series_key: SeriesIdentity,
        clean_history: Dict[date, float],
    ) -> Dict[date, Dict[str, Any]]:
        """Precomputes/caches causal features, nearest target, and baselines for all origins of a series."""
        s_tup = series_key.as_tuple()
        if s_tup in self._series_cache:
            return self._series_cache[s_tup]

        cache_dict: Dict[date, Dict[str, Any]] = {}
        sorted_dates = sorted(clean_history.keys())
        if not sorted_dates:
            self._series_cache[s_tup] = cache_dict
            return cache_dict

        # Prepare cumulative DataFrame for baseline computations
        full_df = pd.DataFrame([
            {"Arrival_Date": pd.Timestamp(d), "Modal_Price": clean_history[d]}
            for d in sorted_dates
        ])

        for t in sorted_dates:
            # Check origin recency >= 3 in [t-30d, t]
            if not self.builder.evaluate_origin_recency(clean_history, t, window_days=30, min_recency_obs=3):
                continue

            y_t = clean_history[t]

            # Extract unbounded nearest target in [t+6, t+8]
            y_trg, d_trg, is_exact = extract_series_target(
                clean_history,
                origin_t=t,
                max_target_date=None,
            )

            # Causal features at origin t
            feat = self.builder.compute_origin_features(clean_history, t, series_key)

            # Sub-dataframe <= t for baselines
            sub_df = full_df[full_df["Arrival_Date"] <= pd.Timestamp(t)]
            b_naive = predict_naive(sub_df, t)
            b_ma = predict_moving_average(sub_df, t, window_days=30, max_obs=7, min_obs=3)
            b_seasonal = predict_seasonal_naive(sub_df, t, season_days=364, horizon_days=7, tolerance_days=3)
            b_drift = predict_drift(sub_df, t, anchor_lag=14, tolerance_days=3, horizon_days=7, drift_factor=0.5)

            cache_dict[t] = {
                "y_t": y_t,
                "y_trg": y_trg,
                "d_trg": d_trg,
                "exact_t7": is_exact,
                "features": feat,
                "naive_pred": b_naive,
                "ma_pred": b_ma,
                "seasonal_pred": b_seasonal,
                "drift_pred": b_drift,
            }

        self._series_cache[s_tup] = cache_dict
        return cache_dict

    def prepare_dataset_partitions(
        self,
        series_map: Dict[SeriesIdentity, Dict[date, float]],
        fold: TemporalFold,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Extract training rows (with strict label maturity) and outer test rows for a fold.
        Evaluates Tier A and Tier B eligibility, populates is_tier_a and is_tier_b flags,
        and assigns date-based regime on origin dates.
        Returns: (train_df, test_df)
        """
        train_rows: List[Dict[str, Any]] = []
        test_rows: List[Dict[str, Any]] = []

        # Sort series stably
        sorted_series = sorted(series_map.keys(), key=lambda s: s.as_tuple())

        for series_key in sorted_series:
            clean_history = series_map[series_key]
            if not clean_history:
                continue

            # Evaluate training eligibility up to fold train cutoff
            elig = self.evaluate_eligibility(clean_history, fold.train_cutoff)
            if not elig["tier_a"] and not elig["tier_b"]:
                continue

            is_tier_a = bool(elig["tier_a"])
            is_tier_b = bool(elig["tier_b"])
            # Legacy label: TierB if TierB else TierA
            tier_label = "TierB" if is_tier_b else "TierA"

            cached_origins = self._get_or_compute_series_cache(series_key, clean_history)

            for t, data in cached_origins.items():
                y_t = data["y_t"]
                y_trg = data["y_trg"]
                d_trg = data["d_trg"]
                is_exact = data["exact_t7"]
                feat = data["features"]

                if y_trg is None or d_trg is None:
                    continue

                delta = y_trg - y_t
                date_regime = classify_date_regime(t)

                # Training Partition: t <= max_train_origin AND target matured <= train_cutoff
                if t <= fold.max_train_origin and d_trg <= fold.train_cutoff:
                    row = {
                        "fold": fold.fold_id,
                        "is_tier_a": is_tier_a,
                        "is_tier_b": is_tier_b,
                        "tier": tier_label,
                        "date_regime": date_regime,
                        "district": series_key.district,
                        "market": series_key.market,
                        "commodity": series_key.commodity,
                        "variety": series_key.variety,
                        "grade": series_key.grade,
                        "origin_date": t,
                        "target_date": d_trg,
                        "exact_t7": is_exact,
                        "y_t": y_t,
                        "y_true": y_trg,
                        "target_delta": delta,
                    }
                    for col in FEATURE_COLUMNS:
                        row[col] = feat.get(col, np.nan)
                    train_rows.append(row)

                # Outer Test Partition: t in [test_start, test_end] AND target matured <= test_end
                elif fold.test_start <= t <= fold.test_end and d_trg <= fold.test_end:
                    row = {
                        "fold": fold.fold_id,
                        "is_tier_a": is_tier_a,
                        "is_tier_b": is_tier_b,
                        "tier": tier_label,
                        "date_regime": date_regime,
                        "district": series_key.district,
                        "market": series_key.market,
                        "commodity": series_key.commodity,
                        "variety": series_key.variety,
                        "grade": series_key.grade,
                        "origin_date": t,
                        "target_date": d_trg,
                        "exact_t7": is_exact,
                        "y_t": y_t,
                        "y_true": y_trg,
                        "target_delta": delta,
                        "naive_pred": data["naive_pred"],
                        "ma_pred": data["ma_pred"],
                        "seasonal_pred": data["seasonal_pred"],
                        "drift_pred": data["drift_pred"],
                    }
                    for col in FEATURE_COLUMNS:
                        row[col] = feat.get(col, np.nan)
                    test_rows.append(row)

        train_df = pd.DataFrame(train_rows)
        test_df = pd.DataFrame(test_rows)
        return train_df, test_df

    def tune_candidate_models(
        self,
        series_map: Dict[SeriesIdentity, Dict[date, float]],
        fold: TemporalFold,
    ) -> Dict[str, Any]:
        """
        Tune Ridge and HistGradientBoosting across the two expanding inner splits.
        Candidate selection ranks configurations on identical common validation origin keys
        where all configs in the comparison family produce valid, finite positive predictions.
        Deterministic tie-break prefers simpler regularized models (higher alpha, depth 3).
        """
        inner_splits = get_inner_splits(fold)

        # Grids
        ridge_alphas = [0.1, 1.0, 10.0]
        hgb_configs = [
            {"config_id": "hgb_depth3", "max_depth": 3, "min_samples_leaf": 20, "learning_rate": 0.05, "max_iter": 100},
            {"config_id": "hgb_depth5", "max_depth": 5, "min_samples_leaf": 30, "learning_rate": 0.05, "max_iter": 100},
        ]

        # Containers for validation predictions across both inner splits
        # key: config, value: Dict[origin_key, (y_true, y_hat)]
        ridge_val_preds: Dict[float, Dict[Tuple[str, str], Tuple[float, float]]] = {a: {} for a in ridge_alphas}
        hgb_val_preds: Dict[str, Dict[Tuple[str, str], Tuple[float, float]]] = {c["config_id"]: {} for c in hgb_configs}

        split_diagnostics = []

        for split in inner_splits:
            inner_train_rows = []
            inner_val_rows = []

            for series_key, clean_history in series_map.items():
                # Inner training eligibility evaluated up to inner_fit_cutoff
                elig = self.evaluate_eligibility(clean_history, split.inner_fit_cutoff)
                if not elig["tier_a"] and not elig["tier_b"]:
                    continue

                cached_origins = self._get_or_compute_series_cache(series_key, clean_history)

                for t, data in cached_origins.items():
                    y_t = data["y_t"]
                    y_trg = data["y_trg"]
                    d_trg = data["d_trg"]
                    feat = data["features"]

                    if y_trg is None or d_trg is None:
                        continue

                    delta = y_trg - y_t
                    s_id_str = f"{series_key.district}__{series_key.market}__{series_key.commodity}__{series_key.variety}__{series_key.grade}"
                    origin_key = (s_id_str, str(t))

                    # Inner fit training partition: t <= inner_fit_max_origin and target matured <= inner_fit_cutoff
                    if t <= split.inner_fit_max_origin and d_trg <= split.inner_fit_cutoff:
                        r = {"y_t": y_t, "y_true": y_trg, "target_delta": delta, "origin_key": origin_key}
                        for col in FEATURE_COLUMNS:
                            r[col] = feat.get(col, np.nan)
                        inner_train_rows.append(r)

                    # Inner validation partition: t in [val_start, val_end] and target matured <= split.val_end
                    elif split.val_start <= t <= split.val_end and d_trg <= split.val_end:
                        r = {"y_t": y_t, "y_true": y_trg, "target_delta": delta, "origin_key": origin_key}
                        for col in FEATURE_COLUMNS:
                            r[col] = feat.get(col, np.nan)
                        inner_val_rows.append(r)

            split_diag = {
                "split_name": split.name,
                "inner_fit_cutoff": str(split.inner_fit_cutoff),
                "val_window": f"{split.val_start}..{split.val_end}",
                "train_samples": len(inner_train_rows),
                "val_samples": len(inner_val_rows),
            }
            split_diagnostics.append(split_diag)

            if len(inner_train_rows) < 30 or len(inner_val_rows) < 10:
                continue

            df_tr = pd.DataFrame(inner_train_rows)
            df_va = pd.DataFrame(inner_val_rows)

            X_tr = df_tr[FEATURE_COLUMNS]
            y_tr = df_tr["target_delta"].values
            X_va = df_va[FEATURE_COLUMNS]
            y_va_true = df_va["y_true"].values
            y_va_t = df_va["y_t"].values
            val_keys = df_va["origin_key"].tolist()

            # Fit and evaluate Ridge models
            for alpha in ridge_alphas:
                model = build_candidate_ridge_model(alpha=alpha)
                model.fit(X_tr, y_tr)
                delta_pred = model.predict(X_va)
                y_hat = y_va_t + delta_pred
                for k, yt, yh in zip(val_keys, y_va_true, y_hat):
                    if math.isfinite(yh) and yh > 0:
                        ridge_val_preds[alpha][k] = (float(yt), float(yh))

            # Fit and evaluate HGB models
            for cfg in hgb_configs:
                cid = cfg["config_id"]
                model = build_candidate_hgb_model(
                    max_depth=cfg["max_depth"],
                    min_samples_leaf=cfg["min_samples_leaf"],
                    learning_rate=cfg["learning_rate"],
                    max_iter=cfg["max_iter"],
                )
                model.fit(X_tr, y_tr)
                delta_pred = model.predict(X_va)
                y_hat = y_va_t + delta_pred
                for k, yt, yh in zip(val_keys, y_va_true, y_hat):
                    if math.isfinite(yh) and yh > 0:
                        hgb_val_preds[cid][k] = (float(yt), float(yh))

        # Ridge Hyperparameter Selection on Pooled Common Origins
        # Find common validation origins across all ridge alphas
        ridge_sets = [set(ridge_val_preds[a].keys()) for a in ridge_alphas]
        common_ridge_keys = sorted(set.intersection(*ridge_sets)) if ridge_sets else []
        n_common_ridge = len(common_ridge_keys)

        best_ridge_alpha = 1.0  # default fallback
        best_ridge_mae = float("inf")
        ridge_scores = {}

        for alpha in sorted(ridge_alphas, reverse=True):  # higher alpha first for deterministic tie-breaker
            valid_n = len(ridge_val_preds[alpha])
            if n_common_ridge >= 10:
                mae = float(np.mean([
                    abs(ridge_val_preds[alpha][k][0] - ridge_val_preds[alpha][k][1])
                    for k in common_ridge_keys
                ]))
                ridge_scores[str(alpha)] = {
                    "mae": mae,
                    "common_n": n_common_ridge,
                    "valid_n": valid_n,
                }
                if mae < best_ridge_mae:
                    best_ridge_mae = mae
                    best_ridge_alpha = alpha
            else:
                ridge_scores[str(alpha)] = {
                    "mae": None,
                    "common_n": n_common_ridge,
                    "valid_n": valid_n,
                    "note": "INADEQUATE_COMMON_SAMPLES_USED_DEFAULT",
                }

        # HGB Hyperparameter Selection on Pooled Common Origins
        # Find common validation origins across all HGB configs
        hgb_sets = [set(hgb_val_preds[c["config_id"]].keys()) for c in hgb_configs]
        common_hgb_keys = sorted(set.intersection(*hgb_sets)) if hgb_sets else []
        n_common_hgb = len(common_hgb_keys)

        best_hgb_cfg = hgb_configs[0]  # default fallback (hgb_depth3)
        best_hgb_mae = float("inf")
        hgb_scores = {}

        for cfg in hgb_configs:  # hgb_depth3 is checked before hgb_depth5 for deterministic tie-break
            cid = cfg["config_id"]
            valid_n = len(hgb_val_preds[cid])
            if n_common_hgb >= 10:
                mae = float(np.mean([
                    abs(hgb_val_preds[cid][k][0] - hgb_val_preds[cid][k][1])
                    for k in common_hgb_keys
                ]))
                hgb_scores[cid] = {
                    "mae": mae,
                    "common_n": n_common_hgb,
                    "valid_n": valid_n,
                }
                if mae < best_hgb_mae:
                    best_hgb_mae = mae
                    best_hgb_cfg = cfg
            else:
                hgb_scores[cid] = {
                    "mae": None,
                    "common_n": n_common_hgb,
                    "valid_n": valid_n,
                    "note": "INADEQUATE_COMMON_SAMPLES_USED_DEFAULT",
                }

        return {
            "fold_id": fold.fold_id,
            "split_diagnostics": split_diagnostics,
            "best_ridge_alpha": best_ridge_alpha,
            "ridge_tuning_scores": ridge_scores,
            "common_ridge_sample_size": n_common_ridge,
            "best_hgb_config": best_hgb_cfg,
            "hgb_tuning_scores": hgb_scores,
            "common_hgb_sample_size": n_common_hgb,
        }

    def train_and_predict_outer(
        self,
        train_df: pd.DataFrame,
        test_df: pd.DataFrame,
        ridge_alpha: float = 1.0,
        hgb_config: Optional[Dict[str, Any]] = None,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Refit chosen candidate models on full mature outer training partition,
        and generate test predictions with response inversion and abstention checks.
        """
        if hgb_config is None:
            hgb_config = {"max_depth": 3, "min_samples_leaf": 20, "learning_rate": 0.05, "max_iter": 100}

        if train_df.empty or test_df.empty:
            out_df = test_df.copy()
            out_df["ridge_pred"] = np.nan
            out_df["ridge_abstention"] = "NO_TRAINING_DATA"
            out_df["hgb_pred"] = np.nan
            out_df["hgb_abstention"] = "NO_TRAINING_DATA"
            return out_df, {"fitted": False, "reason": "EMPTY_PARTITION"}

        X_tr = train_df[FEATURE_COLUMNS]
        y_tr = train_df["target_delta"].values
        X_te = test_df[FEATURE_COLUMNS]
        y_te_t = test_df["y_t"].values

        # 1. Ridge refit
        ridge_model = build_candidate_ridge_model(alpha=ridge_alpha)
        ridge_model.fit(X_tr, y_tr)
        ridge_delta = ridge_model.predict(X_te)
        ridge_reconstructed = y_te_t + ridge_delta

        ridge_preds: List[float] = []
        ridge_reasons: List[str] = []
        for val in ridge_reconstructed:
            if not math.isfinite(val) or val <= 0:
                ridge_preds.append(np.nan)
                ridge_reasons.append("NON_POSITIVE_RECONSTRUCTED_FORECAST")
            else:
                ridge_preds.append(float(val))
                ridge_reasons.append("SCORED")

        # 2. HistGradientBoosting refit
        hgb_model = build_candidate_hgb_model(
            max_depth=hgb_config.get("max_depth", 3),
            min_samples_leaf=hgb_config.get("min_samples_leaf", 20),
            learning_rate=hgb_config.get("learning_rate", 0.05),
            max_iter=hgb_config.get("max_iter", 100),
        )
        hgb_model.fit(X_tr, y_tr)
        hgb_delta = hgb_model.predict(X_te)
        hgb_reconstructed = y_te_t + hgb_delta

        hgb_preds: List[float] = []
        hgb_reasons: List[str] = []
        for val in hgb_reconstructed:
            if not math.isfinite(val) or val <= 0:
                hgb_preds.append(np.nan)
                hgb_reasons.append("NON_POSITIVE_RECONSTRUCTED_FORECAST")
            else:
                hgb_preds.append(float(val))
                hgb_reasons.append("SCORED")

        pred_df = test_df.copy()
        pred_df["ridge_pred"] = ridge_preds
        pred_df["ridge_abstention"] = ridge_reasons
        pred_df["hgb_pred"] = hgb_preds
        pred_df["hgb_abstention"] = hgb_reasons

        models_dict = {
            "fitted": True,
            "ridge_model": ridge_model,
            "ridge_alpha": ridge_alpha,
            "hgb_model": hgb_model,
            "hgb_config": hgb_config,
        }
        return pred_df, models_dict


def compute_slice_metrics(
    df: pd.DataFrame,
    pred_col: str,
    true_col: str = "y_true",
    naive_col: str = "naive_pred",
    n_bootstrap: int = 1000,
    seed: int = 42,
) -> Dict[str, Any]:
    """
    Compute rigorous evaluation metrics on non-abstained finite predictions:
    MAE, RMSE, MeanBias, MedianAE, MAPE, Within-5% Accuracy.
    Paired Naive Skill Score on common finite evaluated origins with series-cluster bootstrap 95% CIs.
    Pre-aggregates cluster counts and errors for fast, mathematically identical BLAS bootstrap.
    Returns complete schema across all slices including empty/all-abstain cases.
    """
    total_samples = len(df)
    valid_mask = (
        df[pred_col].notna()
        & np.isfinite(df[pred_col])
        & df[true_col].notna()
        & np.isfinite(df[true_col])
    ) if not df.empty else pd.Series([], dtype=bool)

    scored_df = df[valid_mask].copy() if not df.empty else pd.DataFrame(columns=df.columns)
    scored_count = len(scored_df)
    abstention_count = total_samples - scored_count

    # Empty / Zero Scored Slices: return complete schema with NaNs
    if scored_count == 0:
        return {
            "total_samples": total_samples,
            "scored_count": 0,
            "abstention_count": abstention_count,
            "unique_series": 0,
            "coverage": 0.0,
            "is_low_n": True,
            "mae": np.nan,
            "mae_ci_lower": np.nan,
            "mae_ci_upper": np.nan,
            "mae_ci_95": (np.nan, np.nan),
            "rmse": np.nan,
            "bias": np.nan,
            "median_ae": np.nan,
            "mape": np.nan,
            "pct_within_5pct": np.nan,
            "paired_count": 0,
            "paired_mae": np.nan,
            "paired_naive_mae": np.nan,
            "skill": np.nan,
            "skill_ci_lower": np.nan,
            "skill_ci_upper": np.nan,
            "skill_ci_95": (np.nan, np.nan),
        }

    y_t = np.array(scored_df[true_col].values, dtype=float, copy=True)
    y_t.flags.writeable = False
    y_p = np.array(scored_df[pred_col].values, dtype=float, copy=True)
    y_p.flags.writeable = False
    errors = np.array(y_p - y_t, dtype=float, copy=True)
    errors.flags.writeable = False
    abs_errors = np.array(np.abs(errors), dtype=float, copy=True)
    abs_errors.flags.writeable = False

    mae = float(np.mean(abs_errors))
    bias = float(np.mean(errors))
    rmse = float(np.sqrt(np.mean(errors * errors)))
    med_ae = float(np.median(abs_errors))

    # MAPE on positive true prices
    pos_mask = y_t > 0
    if np.any(pos_mask):
        mape = float(np.mean(abs_errors[pos_mask] / y_t[pos_mask])) * 100.0
        pct_within_5 = float(np.mean(abs_errors[pos_mask] / y_t[pos_mask] <= 0.05)) * 100.0
    else:
        mape = np.nan
        pct_within_5 = np.nan

    # Paired naive skill evaluation on common non-abstained finite subset
    paired_mask = (
        scored_df[naive_col].notna()
        & np.isfinite(scored_df[naive_col])
    )
    paired_df = scored_df[paired_mask].copy()
    paired_count = len(paired_df)

    # Series clustering count for LOW-N check
    scored_series_keys = (
        scored_df["district"].astype(str)
        + "__"
        + scored_df["market"].astype(str)
        + "__"
        + scored_df["commodity"].astype(str)
        + "__"
        + scored_df["variety"].astype(str)
        + "__"
        + scored_df["grade"].astype(str)
    )
    scored_df["_series_id"] = scored_series_keys
    unique_series = sorted(scored_series_keys.unique())
    num_series = len(unique_series)
    is_low_n = (scored_count < 200) or (num_series < 10)

    # Paired MAE and Skill
    if paired_count > 0:
        paired_df["_series_id"] = (
            paired_df["district"].astype(str)
            + "__"
            + paired_df["market"].astype(str)
            + "__"
            + paired_df["commodity"].astype(str)
            + "__"
            + paired_df["variety"].astype(str)
            + "__"
            + paired_df["grade"].astype(str)
        )
        y_true_p = np.array(paired_df[true_col].values, dtype=float, copy=True)
        y_true_p.flags.writeable = False
        y_model_p = np.array(paired_df[pred_col].values, dtype=float, copy=True)
        y_model_p.flags.writeable = False
        y_naive_p = np.array(paired_df[naive_col].values, dtype=float, copy=True)
        y_naive_p.flags.writeable = False

        err_model = np.abs(y_true_p - y_model_p)
        err_naive = np.abs(y_true_p - y_naive_p)

        denom = float(np.sum(err_naive))
        numer = float(np.sum(err_model))
        paired_mae = float(np.mean(err_model))
        paired_naive_mae = float(np.mean(err_naive))

        if denom > 0:
            skill = 1.0 - (numer / denom)
        else:
            skill = np.nan
    else:
        paired_mae = np.nan
        paired_naive_mae = np.nan
        skill = np.nan

    # Series-Cluster Bootstrap 95% CIs via Pre-aggregation
    mae_ci = (np.nan, np.nan)
    skill_ci = (np.nan, np.nan)

    if n_bootstrap > 0 and num_series >= 2:
        # 1. Unpaired MAE CI Bootstrap
        grp_mae = pd.DataFrame({
            "_sid": scored_df["_series_id"].values,
            "cnt": 1,
            "err": abs_errors,
        }).groupby("_sid", sort=True).sum()

        C_mae = grp_mae["cnt"].values.astype(float)
        E_mae = grp_mae["err"].values.astype(float)
        n_clusters = len(grp_mae)

        rng = np.random.default_rng(seed)
        boot_maes = []
        for _ in range(n_bootstrap):
            idx = rng.integers(0, n_clusters, size=n_clusters)
            counts = np.bincount(idx, minlength=n_clusters)
            b_total = np.dot(counts, C_mae)
            if b_total > 0:
                b_num = np.dot(counts, E_mae)
                boot_maes.append(b_num / b_total)

        if boot_maes:
            mae_ci = (
                float(np.percentile(boot_maes, 2.5)),
                float(np.percentile(boot_maes, 97.5)),
            )

        # 2. Paired Skill CI Bootstrap
        if paired_count >= 10:
            grp_skill = pd.DataFrame({
                "_sid": paired_df["_series_id"].values,
                "err_m": err_model,
                "err_n": err_naive,
            }).groupby("_sid", sort=True).sum()

            E_num = grp_skill["err_m"].values.astype(float)
            E_den = grp_skill["err_n"].values.astype(float)
            n_p_clusters = len(grp_skill)

            if n_p_clusters >= 2:
                rng_skill = np.random.default_rng(seed)
                boot_skills = []
                for _ in range(n_bootstrap):
                    idx = rng_skill.integers(0, n_p_clusters, size=n_p_clusters)
                    counts = np.bincount(idx, minlength=n_p_clusters)
                    b_den = np.dot(counts, E_den)
                    if b_den > 0:
                        b_num = np.dot(counts, E_num)
                        boot_skills.append(1.0 - (b_num / b_den))

                if boot_skills:
                    skill_ci = (
                        float(np.percentile(boot_skills, 2.5)),
                        float(np.percentile(boot_skills, 97.5)),
                    )

    return {
        "total_samples": total_samples,
        "scored_count": scored_count,
        "abstention_count": abstention_count,
        "unique_series": num_series,
        "coverage": float(scored_count / total_samples) if total_samples > 0 else 0.0,
        "is_low_n": is_low_n,
        "mae": mae,
        "mae_ci_lower": mae_ci[0],
        "mae_ci_upper": mae_ci[1],
        "mae_ci_95": mae_ci,
        "rmse": rmse,
        "bias": bias,
        "median_ae": med_ae,
        "mape": mape,
        "pct_within_5pct": pct_within_5,
        "paired_count": paired_count,
        "paired_mae": paired_mae,
        "paired_naive_mae": paired_naive_mae,
        "skill": skill,
        "skill_ci_lower": skill_ci[0],
        "skill_ci_upper": skill_ci[1],
        "skill_ci_95": skill_ci,
    }
