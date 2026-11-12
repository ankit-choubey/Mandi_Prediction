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
from typing import Dict, List, Optional, Tuple, Any, Union
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
    Compute standard forecasting evaluation metrics on non-NaN predictions:
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
    
    valid_mask = ~np.isnan(y_t) & ~np.isnan(y_p)
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
    mape = float(np.nanmean(pct_errors) * 100.0) if np.any(~np.isnan(pct_errors)) else np.nan
    
    median_ae = float(np.median(abs_errors))
    bias = float(np.mean(errors))
    
    within_5 = float(np.mean(pct_errors <= 0.05) * 100.0) if np.any(~np.isnan(pct_errors)) else np.nan
    
    skill = np.nan
    if y_naive is not None:
        y_n = np.asarray(y_naive, dtype=float)[valid_mask]
        abs_err_naive = np.abs(y_n - y_t_val)
        mae_naive = float(np.mean(abs_err_naive))
        if mae_naive > 0:
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
    Optimized via series-level pre-aggregation for high performance.
    """
    valid_df = eval_df.dropna(subset=[target_col, pred_col, naive_col]).copy()
    unique_series = valid_df[series_col].unique()
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
        y_t = grp[target_col].to_numpy(dtype=float)
        y_p = grp[pred_col].to_numpy(dtype=float)
        y_n = grp[naive_col].to_numpy(dtype=float)
        sum_err_pred[idx] = np.sum(np.abs(y_p - y_t))
        sum_err_naive[idx] = np.sum(np.abs(y_n - y_t))
        counts[idx] = len(grp)
        
    rng = np.random.default_rng(seed)
    sampled_idx = rng.choice(n_clusters, size=(n_resamples, n_clusters), replace=True)
    
    sampled_counts = np.sum(counts[sampled_idx], axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        boot_maes = np.sum(sum_err_pred[sampled_idx], axis=1) / sampled_counts
        boot_naive_maes = np.sum(sum_err_naive[sampled_idx], axis=1) / sampled_counts
        boot_skills = np.where(boot_naive_maes > 0, 1.0 - (boot_maes / boot_naive_maes), np.nan)
        
    return {
        "mae_mean": round(float(np.nanmean(boot_maes)), 4),
        "mae_ci_lower": round(float(np.nanpercentile(boot_maes, 2.5)), 4),
        "mae_ci_upper": round(float(np.nanpercentile(boot_maes, 97.5)), 4),
        "skill_mean": round(float(np.nanmean(boot_skills)), 4),
        "skill_ci_lower": round(float(np.nanpercentile(boot_skills, 2.5)), 4),
        "skill_ci_upper": round(float(np.nanpercentile(boot_skills, 97.5)), 4)
    }
