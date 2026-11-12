"""
APMC Mandi Price Forecasting Benchmark Engine
Task: MP-FC-007

Implements the first price-only machine learning benchmark across four temporal folds (F1-F4)
under strict As-Of operational constraints, comparing Ridge Regression and
HistGradientBoostingRegressor against four rescored empirical baselines (Naive, Moving Average,
Seasonal Naive, Damped Drift).

Key Architectural Guarantees:
1. Strict Retrospective Causality: Features at origin date t observe observations <= t only.
2. Label Maturity Enforcement: Training origins require actual target_date <= train_cutoff.
3. Chronological Inner Validation: Two expanding splits per fold for hyperparameter tuning.
4. Response Formulation: Additive price change delta = y_target - y_t; reconstructed y_hat = y_t + delta.
5. Invertible Abstention: Non-positive or non-finite reconstructed forecasts abstain with explicit reason.
6. Common-Sample Paired Skill: Skill score evaluated on matched finite pairs with series-cluster bootstrap 95% CIs.
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
            regime="TRANSITION",
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
    Split 1: Validation window [T_train - 119d, T_train - 60d], fit cutoff T_train - 120d.
    Split 2: Validation window [T_train - 59d, T_train], fit cutoff T_train - 60d.
    """
    t_train = fold.train_cutoff
    embargo = fold.embargo_days

    # Split 1
    val1_start = t_train - timedelta(days=119)
    val1_end = t_train - timedelta(days=60)
    fit1_cutoff = t_train - timedelta(days=120)
    fit1_max_origin = fit1_cutoff - timedelta(days=embargo + 1)

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
    fit2_cutoff = t_train - timedelta(days=60)
    fit2_max_origin = fit2_cutoff - timedelta(days=embargo + 1)

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
    Enforces max_target_date bound (e.g. train_cutoff for training maturity or test_end for outer test).
    Returns (target_price, target_date, is_exact_t7).
    """
    exact_d = origin_t + timedelta(days=horizon_days)
    w_start = origin_t + timedelta(days=window_min)
    w_end = origin_t + timedelta(days=window_max)

    candidates = []
    for d, p in history.items():
        if w_start <= d <= w_end:
            if max_target_date is not None and d > max_target_date:
                continue
            diff = abs((d - exact_d).days)
            candidates.append((diff, d, p))

    if not candidates:
        return None, None, False

    # Sort by diff ascending, then date ascending (earlier tie-breaker)
    candidates.sort(key=lambda x: (x[0], x[1]))
    best_diff, best_d, best_p = candidates[0]
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
    """Build HistGradientBoostingRegressor with native missing-value handling."""
    return HistGradientBoostingRegressor(
        max_iter=max_iter,
        max_depth=max_depth,
        min_samples_leaf=min_samples_leaf,
        learning_rate=learning_rate,
        random_state=42,
        early_stopping=False,
    )


class ForecastBenchmarkEngine:
    """
    Executes and coordinates the end-to-end price forecasting benchmark.
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

    def prepare_dataset_partitions(
        self,
        series_map: Dict[SeriesIdentity, Dict[date, float]],
        fold: TemporalFold,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Extract training rows (with strict label maturity) and outer test rows for a fold.
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

            tier_label = "TierA" if elig["tier_a"] else "TierB"

            sorted_dates = sorted(clean_history.keys())
            for t in sorted_dates:
                # Check origin recency >= 3 in [t-30d, t]
                if not self.builder.evaluate_origin_recency(clean_history, t, window_days=30, min_recency_obs=3):
                    continue

                y_t = clean_history[t]

                # Training Partition: t <= max_train_origin AND target matured <= train_cutoff
                if t <= fold.max_train_origin:
                    y_trg, d_trg, is_exact = extract_series_target(
                        clean_history,
                        origin_t=t,
                        max_target_date=fold.train_cutoff,
                    )
                    if y_trg is not None and d_trg is not None:
                        delta = y_trg - y_t
                        feat = self.builder.compute_origin_features(clean_history, t, series_key)
                        row = {
                            "fold": fold.fold_id,
                            "tier": tier_label,
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
                elif fold.test_start <= t <= fold.test_end:
                    y_trg, d_trg, is_exact = extract_series_target(
                        clean_history,
                        origin_t=t,
                        max_target_date=fold.test_end,
                    )
                    if y_trg is not None and d_trg is not None:
                        delta = y_trg - y_t
                        feat = self.builder.compute_origin_features(clean_history, t, series_key)

                        # Calculate audited baselines using historical observations <= t
                        # Construct a sub-series history DataFrame for audited baseline calls
                        hist_sub = {d: p for d, p in clean_history.items() if d <= t}
                        sub_df = pd.DataFrame([
                            {"Arrival_Date": pd.Timestamp(d), "Modal_Price": p}
                            for d, p in hist_sub.items()
                        ]).sort_values("Arrival_Date").reset_index(drop=True)

                        b_naive = predict_naive(sub_df, t)
                        b_ma = predict_moving_average(sub_df, t, window_days=30, max_obs=7, min_obs=3)
                        b_seasonal = predict_seasonal_naive(sub_df, t, season_days=364, horizon_days=7, tolerance_days=3)
                        b_drift = predict_drift(sub_df, t, anchor_lag=14, tolerance_days=3, horizon_days=7, drift_factor=0.5)

                        row = {
                            "fold": fold.fold_id,
                            "tier": tier_label,
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
                            "naive_pred": b_naive,
                            "ma_pred": b_ma,
                            "seasonal_pred": b_seasonal,
                            "drift_pred": b_drift,
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
        Selection is based on pooled inner validation MAE on matched available origins.
        """
        inner_splits = get_inner_splits(fold)

        # Grids
        ridge_alphas = [0.1, 1.0, 10.0]
        hgb_configs = [
            {"config_id": "hgb_depth3", "max_depth": 3, "min_samples_leaf": 20, "learning_rate": 0.05, "max_iter": 100},
            {"config_id": "hgb_depth5", "max_depth": 5, "min_samples_leaf": 30, "learning_rate": 0.05, "max_iter": 100},
        ]

        # Containers for validation predictions across both inner splits
        # key: config, value: List[Tuple[y_true, y_hat]]
        ridge_val_preds: Dict[float, List[Tuple[float, float]]] = {a: [] for a in ridge_alphas}
        hgb_val_preds: Dict[str, List[Tuple[float, float]]] = {c["config_id"]: [] for c in hgb_configs}

        split_diagnostics = []

        for split in inner_splits:
            # 1. Build inner train rows and inner validation rows
            inner_train_rows = []
            inner_val_rows = []

            for series_key, clean_history in series_map.items():
                # Inner training eligibility evaluated up to inner_fit_cutoff
                elig = self.evaluate_eligibility(clean_history, split.inner_fit_cutoff)
                if not elig["tier_a"] and not elig["tier_b"]:
                    continue

                sorted_dates = sorted(clean_history.keys())
                for t in sorted_dates:
                    if not self.builder.evaluate_origin_recency(clean_history, t, window_days=30, min_recency_obs=3):
                        continue

                    y_t = clean_history[t]

                    # Inner fit training partition: t <= inner_fit_max_origin and target matured <= inner_fit_cutoff
                    if t <= split.inner_fit_max_origin:
                        y_trg, d_trg, _ = extract_series_target(
                            clean_history,
                            origin_t=t,
                            max_target_date=split.inner_fit_cutoff,
                        )
                        if y_trg is not None and d_trg is not None:
                            delta = y_trg - y_t
                            feat = self.builder.compute_origin_features(clean_history, t, series_key)
                            r = {"y_t": y_t, "y_true": y_trg, "target_delta": delta}
                            for col in FEATURE_COLUMNS:
                                r[col] = feat.get(col, np.nan)
                            inner_train_rows.append(r)

                    # Inner validation partition: t in [val_start, val_end] and target matured <= fold.train_cutoff
                    elif split.val_start <= t <= split.val_end:
                        y_trg, d_trg, _ = extract_series_target(
                            clean_history,
                            origin_t=t,
                            max_target_date=fold.train_cutoff,
                        )
                        if y_trg is not None and d_trg is not None:
                            delta = y_trg - y_t
                            feat = self.builder.compute_origin_features(clean_history, t, series_key)
                            r = {"y_t": y_t, "y_true": y_trg, "target_delta": delta}
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
                # Inadequate inner data for this split, skip fit
                continue

            df_tr = pd.DataFrame(inner_train_rows)
            df_va = pd.DataFrame(inner_val_rows)

            X_tr = df_tr[FEATURE_COLUMNS]
            y_tr = df_tr["target_delta"].values
            X_va = df_va[FEATURE_COLUMNS]
            y_va_true = df_va["y_true"].values
            y_va_t = df_va["y_t"].values

            # Fit and evaluate Ridge models
            for alpha in ridge_alphas:
                model = build_candidate_ridge_model(alpha=alpha)
                model.fit(X_tr, y_tr)
                delta_pred = model.predict(X_va)
                y_hat = y_va_t + delta_pred
                for yt, yh in zip(y_va_true, y_hat):
                    if math.isfinite(yh) and yh > 0:
                        ridge_val_preds[alpha].append((float(yt), float(yh)))

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
                for yt, yh in zip(y_va_true, y_hat):
                    if math.isfinite(yh) and yh > 0:
                        hgb_val_preds[cid].append((float(yt), float(yh)))

        # Compute pooled inner validation MAE
        # Ridge selection (tie-breaker: higher alpha -> simpler regularized model)
        best_ridge_alpha = 1.0  # default fallback
        best_ridge_mae = float("inf")
        ridge_scores = {}
        for alpha in sorted(ridge_alphas, reverse=True):  # higher alpha first for deterministic tie-breaker
            pairs = ridge_val_preds[alpha]
            if len(pairs) >= 10:
                mae = float(np.mean([abs(yt - yh) for yt, yh in pairs]))
                ridge_scores[str(alpha)] = {"mae": mae, "n": len(pairs)}
                if mae < best_ridge_mae:
                    best_ridge_mae = mae
                    best_ridge_alpha = alpha
            else:
                ridge_scores[str(alpha)] = {"mae": None, "n": len(pairs), "note": "INADEQUATE_SAMPLES"}

        # HGB selection (tie-breaker: lower depth -> simpler tree model)
        best_hgb_cfg = hgb_configs[0]  # default fallback
        best_hgb_mae = float("inf")
        hgb_scores = {}
        for cfg in hgb_configs:
            cid = cfg["config_id"]
            pairs = hgb_val_preds[cid]
            if len(pairs) >= 10:
                mae = float(np.mean([abs(yt - yh) for yt, yh in pairs]))
                hgb_scores[cid] = {"mae": mae, "n": len(pairs)}
                if mae < best_hgb_mae:
                    best_hgb_mae = mae
                    best_hgb_cfg = cfg
            else:
                hgb_scores[cid] = {"mae": None, "n": len(pairs), "note": "INADEQUATE_SAMPLES"}

        return {
            "fold_id": fold.fold_id,
            "split_diagnostics": split_diagnostics,
            "best_ridge_alpha": best_ridge_alpha,
            "ridge_tuning_scores": ridge_scores,
            "best_hgb_config": best_hgb_cfg,
            "hgb_tuning_scores": hgb_scores,
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

        # Check Ridge non-positive / non-finite forecasts
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

        # Check HGB non-positive / non-finite forecasts
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
    """
    total_samples = len(df)
    valid_mask = (
        df[pred_col].notna()
        & np.isfinite(df[pred_col])
        & df[true_col].notna()
        & np.isfinite(df[true_col])
    )
    scored_df = df[valid_mask].copy()
    scored_count = len(scored_df)

    if scored_count == 0:
        return {
            "total_samples": total_samples,
            "scored_count": 0,
            "coverage": 0.0,
            "is_low_n": True,
            "mae": np.nan,
            "rmse": np.nan,
            "bias": np.nan,
            "median_ae": np.nan,
            "mape": np.nan,
            "pct_within_5pct": np.nan,
            "paired_naive_mae": np.nan,
            "skill": np.nan,
            "skill_ci_95": (np.nan, np.nan),
            "mae_ci_95": (np.nan, np.nan),
        }

    y_t = scored_df[true_col].values
    y_p = scored_df[pred_col].values
    errors = y_p - y_t
    abs_errors = np.abs(errors)

    mae = float(np.mean(abs_errors))
    rmse = float(np.sqrt(np.mean(errors ** 2)))
    bias = float(np.mean(errors))
    med_ae = float(np.median(abs_errors))

    # MAPE on positive true prices
    pos_mask = y_t > 0
    if np.any(pos_mask):
        mape = float(np.mean(np.abs(errors[pos_mask]) / y_t[pos_mask])) * 100.0
        pct_within_5 = float(np.mean(np.abs(errors[pos_mask]) / y_t[pos_mask] <= 0.05)) * 100.0
    else:
        mape = np.nan
        pct_within_5 = np.nan

    # Paired naive skill evaluation on common non-abstained finite subset
    paired_mask = (
        scored_df[naive_col].notna()
        & np.isfinite(scored_df[naive_col])
    )
    paired_df = scored_df[paired_mask].copy()

    # Series clustering count for LOW-N check
    series_keys = (
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
    unique_series = series_keys.unique()
    num_series = len(unique_series)
    is_low_n = (scored_count < 200) or (num_series < 10)

    if len(paired_df) > 0:
        y_true_p = paired_df[true_col].values
        y_model_p = paired_df[pred_col].values
        y_naive_p = paired_df[naive_col].values

        denom = float(np.sum(np.abs(y_true_p - y_naive_p)))
        numer = float(np.sum(np.abs(y_true_p - y_model_p)))
        paired_naive_mae = float(np.mean(np.abs(y_true_p - y_naive_p)))

        if denom > 0:
            skill = 1.0 - (numer / denom)
        else:
            skill = np.nan
    else:
        paired_naive_mae = np.nan
        skill = np.nan

    # Series-cluster bootstrap for 95% CIs
    mae_ci = (np.nan, np.nan)
    skill_ci = (np.nan, np.nan)

    if len(paired_df) >= 10 and num_series >= 2 and n_bootstrap > 0:
        rng = np.random.default_rng(seed)
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
        p_series = paired_df["_series_id"].unique()
        n_p_series = len(p_series)

        # Pre-group by series for fast cluster sampling
        groups = [
            (
                g[true_col].values,
                g[pred_col].values,
                g[naive_col].values,
            )
            for _, g in paired_df.groupby("_series_id")
        ]

        boot_maes = []
        boot_skills = []

        for _ in range(n_bootstrap):
            idx = rng.integers(0, len(groups), size=len(groups))
            sampled = [groups[i] for i in idx]
            b_yt = np.concatenate([s[0] for s in sampled])
            b_yp = np.concatenate([s[1] for s in sampled])
            b_yn = np.concatenate([s[2] for s in sampled])

            b_err_m = np.abs(b_yt - b_yp)
            b_err_n = np.abs(b_yt - b_yn)

            b_mae = float(np.mean(b_err_m))
            b_denom = float(np.sum(b_err_n))
            b_numer = float(np.sum(b_err_m))

            boot_maes.append(b_mae)
            if b_denom > 0:
                boot_skills.append(1.0 - (b_numer / b_denom))

        if boot_maes:
            mae_ci = (
                float(np.percentile(boot_maes, 2.5)),
                float(np.percentile(boot_maes, 97.5)),
            )
        if boot_skills:
            skill_ci = (
                float(np.percentile(boot_skills, 2.5)),
                float(np.percentile(boot_skills, 97.5)),
            )

    return {
        "total_samples": total_samples,
        "scored_count": scored_count,
        "unique_series": num_series,
        "coverage": float(scored_count / total_samples) if total_samples > 0 else 0.0,
        "is_low_n": is_low_n,
        "mae": mae,
        "rmse": rmse,
        "bias": bias,
        "median_ae": med_ae,
        "mape": mape,
        "pct_within_5pct": pct_within_5,
        "paired_naive_mae": paired_naive_mae,
        "skill": skill,
        "skill_ci_95": skill_ci,
        "mae_ci_95": mae_ci,
    }
