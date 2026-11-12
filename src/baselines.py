"""
APMC Mandi Price Forecasting Baselines & Evaluation Engine
Task: MP-FC-006

This module implements pure, leak-free time-series baseline forecasting models
and evaluation utilities for agricultural mandi commodity prices under the strict
As-Of operational constraint:
- A prediction at origin date t uses only observations dated <= t (t's own published price allowed).
- Any observations dated > t are strictly invisible.

Models implemented:
1. Naive Model: y_hat(t+7) = y(t).
2. Moving Average (MA): Mean of the last <=7 observations within [t-30d, t].
   Abstains if < 3 observations exist in the window.
3. Seasonal Naive: Observation nearest to (t + 7 - 364) within +/-3 days.
   Abstains if no observation exists in that window.
4. Drift Model: y(t) + 0.5 * slope * 7, using observation nearest to (t - 14) within +/-3 days.
   slope = (y(t) - y(t_anchor)) / (t - t_anchor).
   Abstains if no observation exists in the anchor window.

Target Definition:
- Modal price of the observation in [t+6, t+8] closest to t+7 (tie: earlier).
- Emits target_date and exact_t7 flag.
"""

from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union, Set
import numpy as np
import pandas as pd


def parse_date(d: Union[str, datetime, date, pd.Timestamp]) -> pd.Timestamp:
    """Normalize date input to normalized pd.Timestamp."""
    return pd.Timestamp(d).normalize()


def get_history_as_of(
    series_df: pd.DataFrame,
    origin_date: Union[str, datetime, date, pd.Timestamp],
    date_col: str = "Arrival_Date"
) -> pd.DataFrame:
    """
    Enforce As-Of rule: return strictly rows where date <= origin_date,
    sorted chronologically by date.
    """
    t = parse_date(origin_date)
    # Ensure datetime dtype
    if not pd.api.types.is_datetime64_any_dtype(series_df[date_col]):
        dates = pd.to_datetime(series_df[date_col])
    else:
        dates = series_df[date_col]

    mask = dates <= t
    sub = series_df.loc[mask].copy()
    if not pd.api.types.is_datetime64_any_dtype(sub[date_col]):
        sub[date_col] = pd.to_datetime(sub[date_col])
    return sub.sort_values(date_col).reset_index(drop=True)


def predict_naive(
    history_df: pd.DataFrame,
    origin_date: Union[str, datetime, date, pd.Timestamp],
    price_col: str = "Modal_Price",
    date_col: str = "Arrival_Date"
) -> float:
    """
    Naive baseline: y_hat(t+7) = y(t).
    Uses the exact observation on origin_date t.
    If no observation on date t, abstains (returns np.nan).
    """
    t = parse_date(origin_date)
    sub = history_df[history_df[date_col] == t]
    if sub.empty:
        return float(np.nan)
    return float(sub[price_col].iloc[-1])


def predict_moving_average(
    history_df: pd.DataFrame,
    origin_date: Union[str, datetime, date, pd.Timestamp],
    window_days: int = 30,
    max_obs: int = 7,
    min_obs: int = 3,
    price_col: str = "Modal_Price",
    date_col: str = "Arrival_Date"
) -> float:
    """
    Moving Average: Mean of the last <=7 observations within [t-30d, t].
    Abstains (returns np.nan) if total observations in window < 3.
    """
    t = parse_date(origin_date)
    t_start = t - pd.Timedelta(days=window_days)

    in_win = history_df[(history_df[date_col] >= t_start) & (history_df[date_col] <= t)]
    if len(in_win) < min_obs:
        return float(np.nan)

    tail_obs = in_win.tail(max_obs)
    return float(tail_obs[price_col].mean())


def predict_seasonal_naive(
    history_df: pd.DataFrame,
    origin_date: Union[str, datetime, date, pd.Timestamp],
    season_days: int = 364,
    horizon_days: int = 7,
    tolerance_days: int = 3,
    price_col: str = "Modal_Price",
    date_col: str = "Arrival_Date"
) -> float:
    """
    Seasonal Naive: Observation nearest to (t + horizon - season_days) within +/-tolerance_days.
    Default target seasonal date = t + 7 - 364 = t - 357 days.
    Tolerance window = [t - 360, t - 354].
    Tie-breaker: earlier date.
    Abstains (returns np.nan) if no observation in window.
    """
    t = parse_date(origin_date)
    target_s_date = t + pd.Timedelta(days=horizon_days - season_days)
    w_start = target_s_date - pd.Timedelta(days=tolerance_days)
    w_end = target_s_date + pd.Timedelta(days=tolerance_days)

    in_win = history_df[(history_df[date_col] >= w_start) & (history_df[date_col] <= w_end)].copy()
    if in_win.empty:
        return float(np.nan)

    in_win["diff_days"] = (in_win[date_col] - target_s_date).dt.days.abs()
    # Sort by diff_days ascending, then date_col ascending (earlier date tie-breaker)
    in_win = in_win.sort_values(["diff_days", date_col])
    return float(in_win[price_col].iloc[0])


def predict_drift(
    history_df: pd.DataFrame,
    origin_date: Union[str, datetime, date, pd.Timestamp],
    anchor_lag: int = 14,
    tolerance_days: int = 3,
    horizon_days: int = 7,
    drift_factor: float = 0.5,
    price_col: str = "Modal_Price",
    date_col: str = "Arrival_Date"
) -> float:
    """
    Drift Model: y(t) + 0.5 * slope * horizon
    Using observation nearest to (t - anchor_lag) within +/-tolerance_days.
    Default anchor = t - 14 days, window = [t - 17, t - 11].
    slope = (y(t) - y(t_anchor)) / (t - t_anchor).
    Tie-breaker: earlier date.
    Abstains if no observation on t, or no observation in anchor window, or delta_t <= 0.
    """
    t = parse_date(origin_date)
    curr_sub = history_df[history_df[date_col] == t]
    if curr_sub.empty:
        return float(np.nan)
    y_t = float(curr_sub[price_col].iloc[-1])

    target_anchor = t - pd.Timedelta(days=anchor_lag)
    w_start = target_anchor - pd.Timedelta(days=tolerance_days)
    w_end = target_anchor + pd.Timedelta(days=tolerance_days)

    in_win = history_df[(history_df[date_col] >= w_start) & (history_df[date_col] <= w_end)].copy()
    if in_win.empty:
        return float(np.nan)

    in_win["diff_days"] = (in_win[date_col] - target_anchor).dt.days.abs()
    in_win = in_win.sort_values(["diff_days", date_col])

    best_row = in_win.iloc[0]
    t_anchor = best_row[date_col]
    y_anchor = float(best_row[price_col])

    delta_days = (t - t_anchor).days
    if delta_days <= 0:
        return float(np.nan)

    slope = (y_t - y_anchor) / float(delta_days)
    return float(y_t + drift_factor * slope * horizon_days)


def extract_target(
    future_df: pd.DataFrame,
    origin_date: Union[str, datetime, date, pd.Timestamp],
    horizon_days: int = 7,
    window_min: int = 6,
    window_max: int = 8,
    price_col: str = "Modal_Price",
    date_col: str = "Arrival_Date"
) -> Tuple[Optional[float], Optional[str], bool]:
    """
    Extract target modal price in [t + window_min, t + window_max] closest to (t + horizon_days).
    Tie-breaker: earlier date.
    Returns: (target_price, target_date_str, is_exact_t7).
    If no observation in window, returns (None, None, False).
    """
    t = parse_date(origin_date)
    exact_t = t + pd.Timedelta(days=horizon_days)
    w_start = t + pd.Timedelta(days=window_min)
    w_end = t + pd.Timedelta(days=window_max)

    # Ensure datetime dtype
    if not pd.api.types.is_datetime64_any_dtype(future_df[date_col]):
        future_df = future_df.copy()
        future_df[date_col] = pd.to_datetime(future_df[date_col])

    in_win = future_df[(future_df[date_col] >= w_start) & (future_df[date_col] <= w_end)].copy()
    if in_win.empty:
        return None, None, False

    in_win["diff_days"] = (in_win[date_col] - exact_t).dt.days.abs()
    in_win = in_win.sort_values(["diff_days", date_col])

    best_row = in_win.iloc[0]
    target_dt = best_row[date_col]
    target_p = float(best_row[price_col])
    is_exact = bool(target_dt == exact_t)
    return target_p, target_dt.strftime("%Y-%m-%d"), is_exact


def compute_forecast_metrics(
    y_true: Union[np.ndarray, List[float], pd.Series],
    y_pred: Union[np.ndarray, List[float], pd.Series],
    y_naive: Optional[Union[np.ndarray, List[float], pd.Series]] = None,
    total_eligible_origins: Optional[int] = None
) -> Dict[str, Any]:
    """
    Compute standard forecasting evaluation metrics on joint finite predictions:
    - MAE (Rs/qtl)
    - RMSE
    - MAPE (%)
    - Median AE
    - Bias (y_pred - y_true)
    - Share within 5% (%)
    - Abstention rate (%)
    - Skill vs Naive: 1 - MAE / MAE_naive
    """
    y_t = np.asarray(y_true, dtype=float)
    y_p = np.asarray(y_pred, dtype=float)

    if y_naive is not None:
        y_n = np.asarray(y_naive, dtype=float)
        valid_mask = np.isfinite(y_t) & np.isfinite(y_p) & np.isfinite(y_n)
    else:
        valid_mask = np.isfinite(y_t) & np.isfinite(y_p)

    n_pred = int(valid_mask.sum())

    if total_eligible_origins is not None and total_eligible_origins > 0:
        abstention_rate = round(float((total_eligible_origins - n_pred) / total_eligible_origins * 100.0), 2)
    else:
        abstention_rate = 0.0

    if n_pred == 0:
        return {
            "n_origins": 0,
            "abstention_rate_pct": abstention_rate,
            "mae": np.nan,
            "rmse": np.nan,
            "mape_pct": np.nan,
            "median_ae": np.nan,
            "bias": np.nan,
            "share_within_5pct": np.nan,
            "skill_vs_naive": np.nan
        }

    y_t_val = y_t[valid_mask]
    y_p_val = y_p[valid_mask]

    errors = y_p_val - y_t_val
    abs_errors = np.abs(errors)

    mae = float(np.mean(abs_errors))
    rmse = float(np.sqrt(np.mean(errors ** 2)))

    # MAPE with zero protection
    with np.errstate(divide="ignore", invalid="ignore"):
        pct_errors = np.where(y_t_val > 0, abs_errors / y_t_val, np.nan)
    mape = float(np.nanmean(pct_errors) * 100.0) if np.any(np.isfinite(pct_errors)) else np.nan

    median_ae = float(np.median(abs_errors))
    bias = float(np.mean(errors))

    within_5 = float(np.mean(pct_errors <= 0.05) * 100.0) if np.any(np.isfinite(pct_errors)) else np.nan

    skill = np.nan
    if y_naive is not None:
        y_n_val = y_n[valid_mask]
        abs_err_naive = np.abs(y_n_val - y_t_val)
        mae_naive = float(np.mean(abs_err_naive))
        if mae_naive > 0 and np.isfinite(mae_naive):
            skill = float(1.0 - (mae / mae_naive))

    return {
        "n_origins": n_pred,
        "abstention_rate_pct": abstention_rate,
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "mape_pct": round(mape, 2) if not np.isnan(mape) else np.nan,
        "median_ae": round(median_ae, 4),
        "bias": round(bias, 4),
        "share_within_5pct": round(within_5, 2) if not np.isnan(within_5) else np.nan,
        "skill_vs_naive": round(skill, 4) if not np.isnan(skill) else np.nan
    }


def cluster_bootstrap_series(
    eval_df: pd.DataFrame,
    series_col: str = "series_id",
    target_col: str = "target_price",
    pred_col: str = "pred_price",
    naive_col: str = "pred_naive",
    n_resamples: int = 1000,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Cluster bootstrap over unique series: resample clusters of series with replacement.
    Computes 95% bootstrap confidence intervals for MAE and Skill vs Naive.

    Estimator Specification:
    - Weighting: Ratio-of-means cluster bootstrap estimator. Resamples series clusters,
      aggregates total absolute error and total observation count across the resampled
      clusters, and computes the ratio sum(errors) / sum(counts). This weights each
      observation equally while preserving intra-series error correlation.
    - Dependence Assumptions: Observations within the same series (cluster) are treated
      as dependent (autocorrelated errors across time). Series across distinct market-commodity
      identities are assumed mutually independent.
    - Determinism: Clusters are sorted deterministically prior to index sampling using
      numpy.random.default_rng(seed).
    """
    if len(eval_df) == 0:
        return {
            "mae_mean": np.nan,
            "mae_ci_lower": np.nan,
            "mae_ci_upper": np.nan,
            "skill_mean": np.nan,
            "skill_ci_lower": np.nan,
            "skill_ci_upper": np.nan
        }

    y_t = eval_df[target_col].to_numpy(dtype=float)
    y_p = eval_df[pred_col].to_numpy(dtype=float)
    has_naive = naive_col in eval_df.columns
    if has_naive:
        y_n = eval_df[naive_col].to_numpy(dtype=float)
        valid_mask = np.isfinite(y_t) & np.isfinite(y_p) & np.isfinite(y_n)
    else:
        valid_mask = np.isfinite(y_t) & np.isfinite(y_p)

    if not np.any(valid_mask):
        return {
            "mae_mean": np.nan,
            "mae_ci_lower": np.nan,
            "mae_ci_upper": np.nan,
            "skill_mean": np.nan,
            "skill_ci_lower": np.nan,
            "skill_ci_upper": np.nan
        }

    valid_df = eval_df.loc[valid_mask].copy()
    unique_series = np.sort(valid_df[series_col].unique())
    n_clusters = len(unique_series)

    if n_clusters == 0:
        return {
            "mae_mean": np.nan,
            "mae_ci_lower": np.nan,
            "mae_ci_upper": np.nan,
            "skill_mean": np.nan,
            "skill_ci_lower": np.nan,
            "skill_ci_upper": np.nan
        }

    s_map = {s: i for i, s in enumerate(unique_series)}
    sum_err_pred = np.zeros(n_clusters, dtype=float)
    sum_err_naive = np.zeros(n_clusters, dtype=float)
    counts = np.zeros(n_clusters, dtype=float)

    for s, grp in valid_df.groupby(series_col):
        idx = s_map[s]
        grp_yt = grp[target_col].to_numpy(dtype=float)
        grp_yp = grp[pred_col].to_numpy(dtype=float)
        sum_err_pred[idx] = np.sum(np.abs(grp_yp - grp_yt))
        if has_naive:
            grp_yn = grp[naive_col].to_numpy(dtype=float)
            sum_err_naive[idx] = np.sum(np.abs(grp_yn - grp_yt))
        counts[idx] = len(grp)

    rng = np.random.default_rng(seed)
    sampled_idx = rng.choice(n_clusters, size=(n_resamples, n_clusters), replace=True)

    sampled_counts = np.sum(counts[sampled_idx], axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        boot_maes = np.sum(sum_err_pred[sampled_idx], axis=1) / sampled_counts
        if has_naive:
            boot_naive_maes = np.sum(sum_err_naive[sampled_idx], axis=1) / sampled_counts
            boot_skills = np.where(boot_naive_maes > 0, 1.0 - (boot_maes / boot_naive_maes), np.nan)
        else:
            boot_skills = np.full(n_resamples, np.nan)

    return {
        "mae_mean": round(float(np.nanmean(boot_maes)), 4) if np.any(np.isfinite(boot_maes)) else np.nan,
        "mae_ci_lower": round(float(np.nanpercentile(boot_maes, 2.5)), 4) if np.any(np.isfinite(boot_maes)) else np.nan,
        "mae_ci_upper": round(float(np.nanpercentile(boot_maes, 97.5)), 4) if np.any(np.isfinite(boot_maes)) else np.nan,
        "skill_mean": round(float(np.nanmean(boot_skills)), 4) if np.any(np.isfinite(boot_skills)) else np.nan,
        "skill_ci_lower": round(float(np.nanpercentile(boot_skills, 2.5)), 4) if np.any(np.isfinite(boot_skills)) else np.nan,
        "skill_ci_upper": round(float(np.nanpercentile(boot_skills, 97.5)), 4) if np.any(np.isfinite(boot_skills)) else np.nan
    }


def evaluate_model_slice(
    sub_df: pd.DataFrame,
    model_col: str,
    target_col: str = "target_price",
    naive_col: str = "pred_naive",
    series_col: str = "series_id",
    n_resamples: int = 1000,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Evaluate a model on a data slice, reporting separate eligible and scored counts
    with LOW-N computed strictly on scored cases.
    Applies joint finite mask consistently to counts, metrics, bootstrap, and abstention.
    """
    n_eligible_origins = len(sub_df)
    n_eligible_series = int(sub_df[series_col].nunique()) if n_eligible_origins > 0 else 0

    if n_eligible_origins == 0:
        return {
            "n_eligible_origins": 0,
            "n_eligible_series": 0,
            "n_scored_origins": 0,
            "n_scored_series": 0,
            "n_origins": 0,
            "n_series": 0,
            "abstention_rate_pct": 100.0,
            "mae": np.nan,
            "mae_ci_lower": np.nan,
            "mae_ci_upper": np.nan,
            "rmse": np.nan,
            "mape_pct": np.nan,
            "median_ae": np.nan,
            "bias": np.nan,
            "share_within_5pct": np.nan,
            "skill_vs_naive": np.nan,
            "skill_ci_lower": np.nan,
            "skill_ci_upper": np.nan,
            "low_n_flag": True
        }

    y_true = sub_df[target_col].to_numpy(dtype=float)
    y_pred = sub_df[model_col].to_numpy(dtype=float)
    has_naive = naive_col in sub_df.columns
    y_naive = sub_df[naive_col].to_numpy(dtype=float) if has_naive else None

    # Joint finite mask: target, model, and naive must all be finite
    if has_naive:
        scored_mask = np.isfinite(y_true) & np.isfinite(y_pred) & np.isfinite(y_naive)
    else:
        scored_mask = np.isfinite(y_true) & np.isfinite(y_pred)

    n_scored_origins = int(scored_mask.sum())
    assert n_scored_origins <= n_eligible_origins, "Scored origins cannot exceed eligible origins!"
    n_scored_series = int(sub_df.loc[scored_mask, series_col].nunique()) if n_scored_origins > 0 else 0

    # LOW-N condition evaluated strictly on scored instances
    low_n_flag = bool(n_scored_origins < 200 or n_scored_series < 10)

    if n_scored_origins == 0:
        abstention_rate = 100.0 if n_eligible_origins > 0 else 0.0
        return {
            "n_eligible_origins": n_eligible_origins,
            "n_eligible_series": n_eligible_series,
            "n_scored_origins": 0,
            "n_scored_series": 0,
            "n_origins": 0,
            "n_series": 0,
            "abstention_rate_pct": abstention_rate,
            "mae": np.nan,
            "mae_ci_lower": np.nan,
            "mae_ci_upper": np.nan,
            "rmse": np.nan,
            "mape_pct": np.nan,
            "median_ae": np.nan,
            "bias": np.nan,
            "share_within_5pct": np.nan,
            "skill_vs_naive": np.nan,
            "skill_ci_lower": np.nan,
            "skill_ci_upper": np.nan,
            "low_n_flag": True
        }

    df_scored = sub_df.loc[scored_mask]

    metrics = compute_forecast_metrics(
        y_true=df_scored[target_col],
        y_pred=df_scored[model_col],
        y_naive=df_scored[naive_col] if has_naive else None,
        total_eligible_origins=n_eligible_origins
    )

    boot_res = cluster_bootstrap_series(
        eval_df=df_scored,
        series_col=series_col,
        target_col=target_col,
        pred_col=model_col,
        naive_col=naive_col if has_naive else None,
        n_resamples=n_resamples,
        seed=seed
    )

    return {
        "n_eligible_origins": n_eligible_origins,
        "n_eligible_series": n_eligible_series,
        "n_scored_origins": n_scored_origins,
        "n_scored_series": n_scored_series,
        "n_origins": n_scored_origins,
        "n_series": n_scored_series,
        "abstention_rate_pct": metrics["abstention_rate_pct"],
        "mae": metrics["mae"],
        "mae_ci_lower": boot_res["mae_ci_lower"],
        "mae_ci_upper": boot_res["mae_ci_upper"],
        "rmse": metrics["rmse"],
        "mape_pct": metrics["mape_pct"],
        "median_ae": metrics["median_ae"],
        "bias": metrics["bias"],
        "share_within_5pct": metrics["share_within_5pct"],
        "skill_vs_naive": metrics["skill_vs_naive"],
        "skill_ci_lower": boot_res["skill_ci_lower"],
        "skill_ci_upper": boot_res["skill_ci_upper"],
        "low_n_flag": low_n_flag
    }


def load_canonical_disputed_keys(
    disputed_csv_path: Union[str, Path],
    aliases: Union[pd.DataFrame, str, Path],
    expected_rows: int = 77
) -> Tuple[Set[Tuple[str, str, str, str, str, str]], pd.DataFrame]:
    """
    Load and canonicalize the disputed discrepancy keys using the accepted alias table.
    Fails closed if the file is absent, schema unexpected, count mismatches,
    or canonicalization fails.

    Returns:
    - Set of canonical 6-tuples: (District_Std, Market_Canonical, Commodity_Std, Variety, Grade, Arrival_Date)
    - Canonicalized DataFrame with both Market_Raw and Market columns.
    """
    from src.market_identity import load_market_aliases, apply_market_canonicalization

    p = Path(disputed_csv_path)
    if not p.is_file():
        raise FileNotFoundError(f"Required disputed keys file not found at: {p}")

    df = pd.read_csv(p)
    required_cols = ["District_Std", "Market", "Commodity_Std", "Variety", "Grade", "Arrival_Date"]
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Disputed keys file missing required columns: {missing_cols}")

    if len(df) != expected_rows:
        raise ValueError(f"Expected exactly {expected_rows} disputed rows, found {len(df)}")

    # Check Arrival_Date non-null and parseable
    if df["Arrival_Date"].isnull().any():
        raise ValueError("Disputed keys file contains null Arrival_Date values")
    try:
        pd.to_datetime(df["Arrival_Date"])
    except Exception as e:
        raise ValueError(f"Disputed keys file contains unparseable dates: {e}")

    if isinstance(aliases, (str, Path)):
        alias_df = load_market_aliases(aliases)
    else:
        alias_df = aliases

    # Apply market canonicalization
    df_canon = apply_market_canonicalization(
        df,
        alias_df,
        market_col="Market",
        district_col="District_Std"
    )

    # Assert market strings were transformed (all expected rows must change from raw APMC to canonical)
    unchanged_mask = df_canon["Market_Raw"] == df_canon["Market"]
    if unchanged_mask.any():
        unchanged = df_canon[unchanged_mask]
        raise ValueError(
            f"Expected all {expected_rows} market names to change under alias mapping, "
            f"but {len(unchanged)} remained unchanged: {unchanged['Market_Raw'].tolist()}"
        )

    keys = list(zip(
        df_canon["District_Std"].astype(str).str.strip(),
        df_canon["Market"].astype(str).str.strip(),
        df_canon["Commodity_Std"].astype(str).str.strip(),
        df_canon["Variety"].astype(str).str.strip(),
        df_canon["Grade"].astype(str).str.strip(),
        df_canon["Arrival_Date"].astype(str).str.strip()
    ))

    unique_keys = set(keys)
    if len(unique_keys) != expected_rows:
        raise ValueError(f"Expected {expected_rows} unique canonical keys, got {len(unique_keys)}")

    return unique_keys, df_canon


def predict_series_vectorized(
    dates_dt: np.ndarray,
    prices: np.ndarray,
    origin_dt: Union[np.datetime64, pd.Timestamp, str],
    horizon_days: int = 7,
    window_min: int = 6,
    window_max: int = 8,
    ma_window_days: int = 30,
    ma_max_obs: int = 7,
    ma_min_obs: int = 3,
    seasonal_lag_days: int = 357,
    seasonal_tol_days: int = 3,
    drift_lag_days: int = 14,
    drift_tol_days: int = 3,
    drift_factor: float = 0.5
) -> Dict[str, Any]:
    """
    Optimized vectorized baseline prediction on numpy arrays for a single series and origin date.
    Implements the exact indexing and tie-breaking logic used in the high-performance notebook loop.

    Guarantees:
    - History strictly <= origin_dt.
    - Deterministic order: sorts input if not chronological.
    - Tie-breaking: earlier calendar date.
    - Abstention: np.nan when preconditions not met.
    """
    # Ensure chronological order
    if len(dates_dt) > 1 and np.any(dates_dt[:-1] > dates_dt[1:]):
        sort_idx = np.argsort(dates_dt)
        dates_dt = dates_dt[sort_idx]
        prices = prices[sort_idx]

    t = pd.Timestamp(origin_dt).normalize()
    t_np = dates_dt.dtype.type(t) if len(dates_dt) > 0 and hasattr(dates_dt.dtype, 'type') else np.datetime64(t)

    # 1. Check observation on origin date t
    mask_t = dates_dt == t_np
    if not np.any(mask_t):
        return {
            "pred_naive": np.nan,
            "pred_ma": np.nan,
            "pred_seasonal": np.nan,
            "pred_drift": np.nan,
            "target_price": np.nan,
            "target_date_str": None,
            "is_exact_t7": False,
            "has_origin_obs": False
        }

    idx_t = np.where(mask_t)[0][-1]
    y_t = float(prices[idx_t])

    # 2. Moving Average: [t - 30d, t]
    win_30d_start = t_np - np.timedelta64(ma_window_days, 'D')
    mask_30d = (dates_dt >= win_30d_start) & (dates_dt <= t_np)
    n_30d = np.sum(mask_30d)
    if n_30d < ma_min_obs:
        pred_ma = np.nan
    else:
        obs_30d = prices[mask_30d]
        pred_ma = float(np.mean(obs_30d[-ma_max_obs:]))

    # 3. Seasonal Naive: target t - 357d in +/-3d [t-360, t-354]
    exact_seasonal_dt = t_np - np.timedelta64(seasonal_lag_days, 'D')
    s_win_start = exact_seasonal_dt - np.timedelta64(seasonal_tol_days, 'D')
    s_win_end = exact_seasonal_dt + np.timedelta64(seasonal_tol_days, 'D')
    mask_s = (dates_dt >= s_win_start) & (dates_dt <= s_win_end)
    if np.any(mask_s):
        s_indices = np.where(mask_s)[0]
        s_dts = dates_dt[s_indices]
        s_diffs = np.abs((s_dts - exact_seasonal_dt) / np.timedelta64(1, 'D'))
        best_s_local = np.lexsort((s_dts, s_diffs))[0]
        pred_seasonal = float(prices[s_indices[best_s_local]])
    else:
        pred_seasonal = np.nan

    # 4. Drift: anchor t - 14d in +/-3d [t-17, t-11]
    exact_anchor_dt = t_np - np.timedelta64(drift_lag_days, 'D')
    a_win_start = exact_anchor_dt - np.timedelta64(drift_tol_days, 'D')
    a_win_end = exact_anchor_dt + np.timedelta64(drift_tol_days, 'D')
    mask_a = (dates_dt >= a_win_start) & (dates_dt <= a_win_end)
    if np.any(mask_a):
        a_indices = np.where(mask_a)[0]
        a_dts = dates_dt[a_indices]
        a_diffs = np.abs((a_dts - exact_anchor_dt) / np.timedelta64(1, 'D'))
        best_a_local = np.lexsort((a_dts, a_diffs))[0]
        best_a_idx = a_indices[best_a_local]
        y_anchor = float(prices[best_a_idx])
        delta_days = float((t_np - dates_dt[best_a_idx]) / np.timedelta64(1, 'D'))
        if delta_days > 0:
            slope = (y_t - y_anchor) / delta_days
            pred_drift = float(y_t + drift_factor * slope * horizon_days)
        else:
            pred_drift = np.nan
    else:
        pred_drift = np.nan

    # 5. Target extraction: [t + 6, t + 8]
    exact_target_dt = t_np + np.timedelta64(horizon_days, 'D')
    win_tgt_start = t_np + np.timedelta64(window_min, 'D')
    win_tgt_end = t_np + np.timedelta64(window_max, 'D')
    mask_tgt = (dates_dt >= win_tgt_start) & (dates_dt <= win_tgt_end)
    if np.any(mask_tgt):
        tgt_indices = np.where(mask_tgt)[0]
        tgt_dts = dates_dt[tgt_indices]
        tgt_diffs = np.abs((tgt_dts - exact_target_dt) / np.timedelta64(1, 'D'))
        best_local_idx = np.lexsort((tgt_dts, tgt_diffs))[0]
        best_tgt_idx = tgt_indices[best_local_idx]
        target_price = float(prices[best_tgt_idx])
        target_dt_val = tgt_dts[best_local_idx]
        target_dt_str = pd.Timestamp(target_dt_val).strftime("%Y-%m-%d")
        is_exact_t7 = bool(target_dt_val == exact_target_dt)
    else:
        target_price = np.nan
        target_dt_str = None
        is_exact_t7 = False

    return {
        "pred_naive": y_t,
        "pred_ma": pred_ma,
        "pred_seasonal": pred_seasonal,
        "pred_drift": pred_drift,
        "target_price": target_price,
        "target_date_str": target_dt_str,
        "is_exact_t7": is_exact_t7,
        "has_origin_obs": True
    }


def check_serving_recency(
    dates_dt: np.ndarray,
    origin_dt: Union[np.datetime64, pd.Timestamp, str],
    window_days: int = 30,
    min_obs: int = 3
) -> bool:
    """
    Check if at least min_obs observations exist in [origin_dt - window_days, origin_dt].
    """
    t = pd.Timestamp(origin_dt).normalize()
    t_np = dates_dt.dtype.type(t) if len(dates_dt) > 0 and hasattr(dates_dt.dtype, 'type') else np.datetime64(t)
    win_start = t_np - np.timedelta64(window_days, 'D')
    mask = (dates_dt >= win_start) & (dates_dt <= t_np)
    return bool(np.sum(mask) >= min_obs)


def extract_target_vectorized(
    dates_dt: np.ndarray,
    prices: np.ndarray,
    origin_dt: Union[np.datetime64, pd.Timestamp, str],
    test_end_dt: Optional[Union[np.datetime64, pd.Timestamp, str]] = None,
    horizon_days: int = 7,
    window_min: int = 6,
    window_max: int = 8
) -> Dict[str, Any]:
    """
    Extract target observation in [t + window_min, t + window_max] closest to t + horizon_days.
    Tie-breaker: earlier calendar date.
    Checks test_end_dt bound if provided.
    """
    t = pd.Timestamp(origin_dt).normalize()
    t_np = dates_dt.dtype.type(t) if len(dates_dt) > 0 and hasattr(dates_dt.dtype, 'type') else np.datetime64(t)

    # Ensure chronological order
    if len(dates_dt) > 1 and np.any(dates_dt[:-1] > dates_dt[1:]):
        sort_idx = np.argsort(dates_dt)
        dates_dt = dates_dt[sort_idx]
        prices = prices[sort_idx]

    exact_target_dt = t_np + np.timedelta64(horizon_days, 'D')
    win_tgt_start = t_np + np.timedelta64(window_min, 'D')
    win_tgt_end = t_np + np.timedelta64(window_max, 'D')

    mask_tgt = (dates_dt >= win_tgt_start) & (dates_dt <= win_tgt_end)
    if not np.any(mask_tgt):
        return {
            "has_target": False,
            "target_price": np.nan,
            "target_dt": None,
            "target_dt_str": None,
            "is_exact_t7": False,
            "is_after_fold_end": False
        }

    tgt_indices = np.where(mask_tgt)[0]
    tgt_dts = dates_dt[tgt_indices]
    tgt_diffs = np.abs((tgt_dts - exact_target_dt) / np.timedelta64(1, 'D'))
    best_local_idx = np.lexsort((tgt_dts, tgt_diffs))[0]
    best_tgt_idx = tgt_indices[best_local_idx]

    target_dt_val = tgt_dts[best_local_idx]
    target_dt_str = pd.Timestamp(target_dt_val).strftime("%Y-%m-%d")
    target_price = float(prices[best_tgt_idx])
    is_exact_t7 = bool(target_dt_val == exact_target_dt)

    is_after_fold_end = False
    if test_end_dt is not None:
        te_end_val = dates_dt.dtype.type(pd.Timestamp(test_end_dt).normalize())
        if target_dt_val > te_end_val:
            is_after_fold_end = True

    return {
        "has_target": True,
        "target_price": np.nan if is_after_fold_end else target_price,
        "target_dt": target_dt_val,
        "target_dt_str": target_dt_str,
        "is_exact_t7": is_exact_t7,
        "is_after_fold_end": is_after_fold_end
    }


def evaluate_series_train_eligibility(
    dates_dt: np.ndarray,
    train_end_dt: Union[np.datetime64, pd.Timestamp, str],
    min_obs: int = 60,
    min_cov: float = 0.3,
    tier_b_min_obs: int = 120
) -> Tuple[bool, bool]:
    """
    Evaluate Tier A and Tier B train-only eligibility for a series up to train_end_dt.
    Tier A: n_obs >= 60 and coverage >= 0.30
    Tier B: Tier A and n_obs >= 120
    """
    tr_end = pd.Timestamp(train_end_dt).normalize()
    tr_end_np = dates_dt.dtype.type(tr_end) if len(dates_dt) > 0 and hasattr(dates_dt.dtype, 'type') else np.datetime64(tr_end)
    mask_tr = dates_dt <= tr_end_np
    n_obs = int(np.sum(mask_tr))
    if n_obs < min_obs:
        return False, False

    dts_tr = dates_dt[mask_tr]
    span = int((dts_tr[-1] - dts_tr[0]) / np.timedelta64(1, 'D')) + 1
    cov = n_obs / span if span > 0 else 0.0

    if cov < min_cov:
        return False, False

    is_tier_a = True
    is_tier_b = bool(n_obs >= tier_b_min_obs)
    return is_tier_a, is_tier_b


def score_series_origin(
    dates_dt: np.ndarray,
    dates_str: np.ndarray,
    prices: np.ndarray,
    origin_dt: Union[np.datetime64, pd.Timestamp, str],
    fold_info: Dict[str, Any],
    series_meta: Dict[str, Any],
    canonical_disputed_keys: Optional[Set[Tuple[str, str, str, str, str, str]]] = None,
    ma_window_days: int = 30,
    ma_min_obs: int = 3,
    ma_max_obs: int = 7,
    seasonal_lag_days: int = 357,
    seasonal_tol_days: int = 3,
    drift_lag_days: int = 14,
    drift_tol_days: int = 3,
    drift_factor: float = 0.5,
    horizon_days: int = 7,
    window_min: int = 6,
    window_max: int = 8
) -> Dict[str, Any]:
    """
    Unified production scoring helper for a single origin on a series.
    Evaluates:
    - Fold test window containment [test_start, test_end]
    - Origin observation presence and y(t)
    - 30-day serving recency (>= 3 obs in [t-30d, t])
    - Target extraction in [t+6, t+8] with earlier tie-breaking and target <= test_end
    - Standard baseline predictions (Naive, MA, Seasonal Naive, Drift) using predict_series_vectorized
    - Scope A sensitivity: exclusion if origin or target matches canonical 77 disputed keys
    - Scope B sensitivity: historical excising of disputed dates strictly < t across ALL 4 baselines,
      explicitly excluding disputed origin/target, recomputing clean recency, and generating
      clean counterfactual predictions.
    """
    # Deterministic chronological order
    if len(dates_dt) > 1 and np.any(dates_dt[:-1] > dates_dt[1:]):
        sort_idx = np.argsort(dates_dt)
        dates_dt = dates_dt[sort_idx]
        dates_str = dates_str[sort_idx]
        prices = prices[sort_idx]

    t_ts = pd.Timestamp(origin_dt).normalize()
    t_np = dates_dt.dtype.type(t_ts) if len(dates_dt) > 0 and hasattr(dates_dt.dtype, 'type') else np.datetime64(t_ts)

    te_start = pd.Timestamp(fold_info["test_start"]).normalize()
    te_end = pd.Timestamp(fold_info["test_end"]).normalize()
    te_start_np = dates_dt.dtype.type(te_start) if len(dates_dt) > 0 and hasattr(dates_dt.dtype, 'type') else np.datetime64(te_start)
    te_end_np = dates_dt.dtype.type(te_end) if len(dates_dt) > 0 and hasattr(dates_dt.dtype, 'type') else np.datetime64(te_end)

    fold_name = fold_info.get("fold", "")
    sid = series_meta.get("series_id", "")
    dist = series_meta.get("district", "")
    mkt = series_meta.get("market", "")
    comm = series_meta.get("commodity", "")
    var = series_meta.get("variety", "")
    grd = series_meta.get("grade", "")

    base_record = {
        "fold": fold_name,
        "series_id": sid,
        "district": dist,
        "market": mkt,
        "commodity": comm,
        "variety": var,
        "grade": grd,
        "is_tier_a": bool(series_meta.get("is_tier_a", False)),
        "is_tier_b": bool(series_meta.get("is_tier_b", False)),
        "origin_date": t_ts.strftime("%Y-%m-%d"),
        "target_date": None,
        "exact_t7": False,
        "target_price": np.nan,
        "y_t": np.nan,
        "pred_naive": np.nan,
        "pred_ma": np.nan,
        "pred_seasonal_naive": np.nan,
        "pred_drift": np.nan,
        "is_77_disputed": False,
        "in_77_scope_a": False,
        "is_disputed_origin": False,
        "is_disputed_target": False,
        "has_disputed_history": False,
        "scope_b_has_removed_history": False,
        "scope_b_eligible": False,
        "scope_b_ineligible_reason": None,
        "pred_naive_scope_b": np.nan,
        "pred_ma_scope_b": np.nan,
        "pred_seasonal_scope_b": np.nan,
        "pred_drift_scope_b": np.nan,
        "ma_changed_scope_b": False,
        "seasonal_changed_scope_b": False,
        "drift_changed_scope_b": False,
        "target_move_gt_2pct": False,
        "is_eligible_origin": False,
        "drop_reason": None
    }

    # 1. Fold test window check
    if t_np < te_start_np or t_np > te_end_np:
        base_record["drop_reason"] = "outside_test_window"
        return base_record

    # 2. Check observation on origin date t
    mask_t = (dates_dt == t_np)
    if not np.any(mask_t):
        base_record["drop_reason"] = "no_origin_observation"
        return base_record

    idx_t = np.where(mask_t)[0][-1]
    y_t = float(prices[idx_t])
    t_str = str(dates_str[idx_t])
    base_record["origin_date"] = t_str
    base_record["y_t"] = y_t

    # 3. Recency check: >= 3 observations in [t - 30d, t]
    recency_ok = check_serving_recency(dates_dt, t_np, window_days=ma_window_days, min_obs=ma_min_obs)
    if not recency_ok:
        base_record["drop_reason"] = "dropped_serving_recency_lt_3"
        return base_record

    # 4. Target extraction: modal price in [t + 6d, t + 8d]
    tgt_res = extract_target_vectorized(
        dates_dt=dates_dt,
        prices=prices,
        origin_dt=t_np,
        test_end_dt=te_end_np,
        horizon_days=horizon_days,
        window_min=window_min,
        window_max=window_max
    )

    if not tgt_res["has_target"]:
        base_record["drop_reason"] = "dropped_no_target_in_window"
        return base_record

    if tgt_res["is_after_fold_end"]:
        base_record["drop_reason"] = "dropped_target_after_fold_end"
        return base_record

    target_price = tgt_res["target_price"]
    target_dt_str = tgt_res["target_dt_str"]
    is_exact_t7 = tgt_res["is_exact_t7"]

    base_record["is_eligible_origin"] = True
    base_record["target_date"] = target_dt_str
    base_record["exact_t7"] = is_exact_t7
    base_record["target_price"] = target_price

    # 5. Standard Baseline Predictions
    preds = predict_series_vectorized(
        dates_dt=dates_dt,
        prices=prices,
        origin_dt=t_str,
        horizon_days=horizon_days,
        window_min=window_min,
        window_max=window_max,
        ma_window_days=ma_window_days,
        ma_max_obs=ma_max_obs,
        ma_min_obs=ma_min_obs,
        seasonal_lag_days=seasonal_lag_days,
        seasonal_tol_days=seasonal_tol_days,
        drift_lag_days=drift_lag_days,
        drift_tol_days=drift_tol_days,
        drift_factor=drift_factor
    )

    base_record["pred_naive"] = preds["pred_naive"]
    base_record["pred_ma"] = preds["pred_ma"]
    base_record["pred_seasonal_naive"] = preds["pred_seasonal"]
    base_record["pred_drift"] = preds["pred_drift"]

    # 6. Disputed keys matching & Scope A
    key_origin = (dist, mkt, comm, var, grd, t_str)
    key_target = (dist, mkt, comm, var, grd, target_dt_str)
    is_disputed_origin = bool(canonical_disputed_keys and key_origin in canonical_disputed_keys)
    is_disputed_target = bool(canonical_disputed_keys and key_target in canonical_disputed_keys)
    in_77_scope_a = is_disputed_origin or is_disputed_target

    base_record["is_disputed_origin"] = is_disputed_origin
    base_record["is_disputed_target"] = is_disputed_target
    base_record["is_77_disputed"] = in_77_scope_a
    base_record["in_77_scope_a"] = in_77_scope_a

    # 7. Scope B: Historical excising across ALL baselines
    series_meta_key = (dist, mkt, comm, var, grd)
    disputed_dates_for_series = {
        k[5] for k in canonical_disputed_keys if (k[0], k[1], k[2], k[3], k[4]) == series_meta_key
    } if canonical_disputed_keys else set()

    has_removed_history = bool(
        disputed_dates_for_series and any(d in disputed_dates_for_series for d in dates_str[dates_dt < t_np])
    )
    base_record["has_disputed_history"] = has_removed_history
    base_record["scope_b_has_removed_history"] = has_removed_history

    if is_disputed_origin:
        base_record["scope_b_eligible"] = False
        base_record["scope_b_ineligible_reason"] = "disputed_origin"
    elif is_disputed_target:
        base_record["scope_b_eligible"] = False
        base_record["scope_b_ineligible_reason"] = "disputed_target"
    else:
        # Build counterfactual clean history <= t
        clean_mask = (~np.isin(dates_str, list(disputed_dates_for_series))) & (dates_dt <= t_np)
        clean_dates_dt = dates_dt[clean_mask]
        clean_dates_str = dates_str[clean_mask]
        clean_prices = prices[clean_mask]

        # Re-verify serving recency on clean history
        clean_recency_ok = check_serving_recency(clean_dates_dt, t_np, window_days=ma_window_days, min_obs=ma_min_obs)
        if not clean_recency_ok:
            base_record["scope_b_eligible"] = False
            base_record["scope_b_ineligible_reason"] = "recency_failure_after_removal"
        else:
            base_record["scope_b_eligible"] = True
            clean_preds = predict_series_vectorized(
                dates_dt=clean_dates_dt,
                prices=clean_prices,
                origin_dt=t_str,
                horizon_days=horizon_days,
                window_min=window_min,
                window_max=window_max,
                ma_window_days=ma_window_days,
                ma_max_obs=ma_max_obs,
                ma_min_obs=ma_min_obs,
                seasonal_lag_days=seasonal_lag_days,
                seasonal_tol_days=seasonal_tol_days,
                drift_lag_days=drift_lag_days,
                drift_tol_days=drift_tol_days,
                drift_factor=drift_factor
            )
            base_record["pred_naive_scope_b"] = clean_preds["pred_naive"]
            base_record["pred_ma_scope_b"] = clean_preds["pred_ma"]
            base_record["pred_seasonal_scope_b"] = clean_preds["pred_seasonal"]
            base_record["pred_drift_scope_b"] = clean_preds["pred_drift"]

            # Change flags
            base_record["ma_changed_scope_b"] = bool(
                not np.isnan(preds["pred_ma"]) and not np.isnan(clean_preds["pred_ma"])
                and not np.isclose(preds["pred_ma"], clean_preds["pred_ma"])
            )
            base_record["seasonal_changed_scope_b"] = bool(
                not np.isnan(preds["pred_seasonal"]) and not np.isnan(clean_preds["pred_seasonal"])
                and not np.isclose(preds["pred_seasonal"], clean_preds["pred_seasonal"])
            )
            base_record["drift_changed_scope_b"] = bool(
                not np.isnan(preds["pred_drift"]) and not np.isnan(clean_preds["pred_drift"])
                and not np.isclose(preds["pred_drift"], clean_preds["pred_drift"])
            )

    # 8. Retrospective diagnostic flag
    base_record["target_move_gt_2pct"] = bool(y_t > 0 and (abs(target_price - y_t) / y_t) > 0.02)

    return base_record
