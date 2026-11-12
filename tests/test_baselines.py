"""
Unit tests for APMC Mandi Price Forecasting Baselines & Evaluation Engine.
Task: MP-FC-006

Tests verify:
1. Strict As-Of temporal boundary / anti-leakage invariant:
   Modifying or corrupting future data (dated > t) has zero effect on predictions.
2. Naive baseline: y(t); abstains if missing on t.
3. Moving Average baseline: mean of last <=7 observations in [t-30d, t], abstains if <3.
4. Seasonal Naive baseline: nearest to t+7-364 in +/-3 days; tie-breaker earlier; abstains if none.
5. Drift baseline: y(t) + 0.5 * slope * 7 using nearest to t-14 in +/-3 days; abstains if missing.
6. Target extractor: modal price in [t+6, t+8] nearest to t+7; tie-breaker earlier; exact_t7 flag.
7. Forecast metrics: MAE, RMSE, MAPE, Median AE, Bias, Share within 5%, Abstention rate, Skill vs Naive.
8. Cluster bootstrap: deterministic confidence intervals under seed 42.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from src.baselines import (
    parse_date,
    get_history_as_of,
    predict_naive,
    predict_moving_average,
    predict_seasonal_naive,
    predict_drift,
    extract_target,
    compute_forecast_metrics,
    cluster_bootstrap_series
)


@pytest.fixture
def sample_series_history():
    """
    Generate synthetic daily/intermittent time series for testing.
    Origin date: 2025-06-15.
    """
    dates = pd.date_range("2024-01-01", "2025-07-01", freq="D")
    prices = [2000.0 + i * 2.0 for i in range(len(dates))]
    df = pd.DataFrame({
        "Arrival_Date": dates,
        "Modal_Price": prices,
        "series_id": "Ghaziabad__Ghaziabad__Wheat__Dara__FAQ"
    })
    return df


def test_as_of_leakage_immunity(sample_series_history):
    """
    CRITICAL ANTI-LEAKAGE INVARIANT:
    Corrupting, scaling, or inserting extreme outliers in all observations
    strictly AFTER origin date t MUST NOT alter any baseline forecast at t.
    """
    origin_t = "2025-06-15"
    
    # 1. Baseline predictions on clean history
    clean_hist = get_history_as_of(sample_series_history, origin_t)
    naive_clean = predict_naive(clean_hist, origin_t)
    ma_clean = predict_moving_average(clean_hist, origin_t)
    seasonal_clean = predict_seasonal_naive(clean_hist, origin_t)
    drift_clean = predict_drift(clean_hist, origin_t)
    
    assert not np.isnan(naive_clean)
    assert not np.isnan(ma_clean)
    assert not np.isnan(seasonal_clean)
    assert not np.isnan(drift_clean)
    
    # 2. Corrupt future data (dates > t)
    corrupted_df = sample_series_history.copy()
    future_mask = corrupted_df["Arrival_Date"] > pd.Timestamp(origin_t)
    corrupted_df.loc[future_mask, "Modal_Price"] = 999999.99  # Massive corruption
    
    # 3. Predict via get_history_as_of on corrupted dataset
    corrupted_hist = get_history_as_of(corrupted_df, origin_t)
    naive_after = predict_naive(corrupted_hist, origin_t)
    ma_after = predict_moving_average(corrupted_hist, origin_t)
    seasonal_after = predict_seasonal_naive(corrupted_hist, origin_t)
    drift_after = predict_drift(corrupted_hist, origin_t)
    
    assert naive_clean == naive_after
    assert ma_clean == ma_after
    assert seasonal_clean == seasonal_after
    assert drift_clean == drift_after


def test_predict_naive():
    """Verify Naive baseline behavior."""
    df = pd.DataFrame({
        "Arrival_Date": pd.to_datetime(["2025-01-10", "2025-01-11", "2025-01-12"]),
        "Modal_Price": [2100.0, 2150.0, 2200.0]
    })
    
    # Existing date
    p = predict_naive(df, "2025-01-11")
    assert p == 2150.0
    
    # Missing date -> np.nan
    p_missing = predict_naive(df, "2025-01-13")
    assert np.isnan(p_missing)


def test_predict_moving_average():
    """Verify Moving Average baseline (<=7 obs in [t-30d, t], min 3 obs)."""
    # Case 1: < 3 obs in 30 days -> abstains
    df_sparse = pd.DataFrame({
        "Arrival_Date": pd.to_datetime(["2025-01-01", "2025-01-15"]),
        "Modal_Price": [2000.0, 2100.0]
    })
    p_sparse = predict_moving_average(df_sparse, "2025-01-15")
    assert np.isnan(p_sparse)
    
    # Case 2: >= 3 obs in 30 days -> mean of last <= 7
    dates = pd.date_range("2025-01-01", "2025-01-15", freq="D")
    prices = [100.0 + i * 10.0 for i in range(len(dates))] # 100, 110, ...
    df_dense = pd.DataFrame({"Arrival_Date": dates, "Modal_Price": prices})
    
    p_ma = predict_moving_average(df_dense, "2025-01-15", max_obs=7, min_obs=3)
    # Last 7 obs up to 2025-01-15 are indices 8 to 14:
    # prices: 180, 190, 200, 210, 220, 230, 240 -> mean = 210.0
    assert p_ma == pytest.approx(210.0)
    
    # Case 3: Exactly 4 obs in 30 days
    df_4 = df_dense.iloc[-4:]
    p_4 = predict_moving_average(df_4, "2025-01-15", max_obs=7, min_obs=3)
    assert p_4 == pytest.approx(df_4["Modal_Price"].mean())


def test_predict_seasonal_naive():
    """
    Seasonal Naive: Observation nearest to (t + 7 - 364) = (t - 357) within +/-3 days.
    Window is [t - 360, t - 354]. Tie-breaker: earlier date.
    """
    t = pd.Timestamp("2025-06-15")
    target_seasonal = t + pd.Timedelta(days=7 - 364) # 2024-06-23
    
    # Observation exactly on target seasonal date
    df_exact = pd.DataFrame({
        "Arrival_Date": [target_seasonal],
        "Modal_Price": [1850.0]
    })
    assert predict_seasonal_naive(df_exact, t) == 1850.0
    
    # Observation within +/-3 days (e.g. target_seasonal + 2 days)
    df_near = pd.DataFrame({
        "Arrival_Date": [target_seasonal + pd.Timedelta(days=2)],
        "Modal_Price": [1870.0]
    })
    assert predict_seasonal_naive(df_near, t) == 1870.0
    
    # Multiple observations in window -> pick closest
    df_multi = pd.DataFrame({
        "Arrival_Date": [
            target_seasonal - pd.Timedelta(days=2), # diff = 2
            target_seasonal + pd.Timedelta(days=1)  # diff = 1 (closer)
        ],
        "Modal_Price": [1800.0, 1900.0]
    })
    assert predict_seasonal_naive(df_multi, t) == 1900.0
    
    # Tie in distance (diff=1 day on both sides) -> earlier date
    df_tie = pd.DataFrame({
        "Arrival_Date": [
            target_seasonal - pd.Timedelta(days=1), # earlier
            target_seasonal + pd.Timedelta(days=1)  # later
        ],
        "Modal_Price": [1810.0, 1890.0]
    })
    assert predict_seasonal_naive(df_tie, t) == 1810.0
    
    # Outside +/-3 days -> abstain
    df_out = pd.DataFrame({
        "Arrival_Date": [target_seasonal - pd.Timedelta(days=4)],
        "Modal_Price": [1700.0]
    })
    assert np.isnan(predict_seasonal_naive(df_out, t))


def test_predict_drift():
    """
    Drift: y(t) + 0.5 * slope * 7, anchor at t - 14 within +/-3 days.
    slope = (y(t) - y(t_anchor)) / (t - t_anchor).
    """
    t = pd.Timestamp("2025-06-15")
    anchor_dt = t - pd.Timedelta(days=14) # 2025-06-01
    
    df = pd.DataFrame({
        "Arrival_Date": [anchor_dt, t],
        "Modal_Price": [2000.0, 2140.0]
    })
    # y(t) = 2140, y(t_anchor) = 2000, delta_days = 14
    # slope = (2140 - 2000) / 14 = 10.0 Rs/day
    # forecast = 2140 + 0.5 * 10.0 * 7 = 2140 + 35.0 = 2175.0
    pred = predict_drift(df, t)
    assert pred == pytest.approx(2175.0)
    
    # Missing anchor -> abstain
    df_no_anchor = pd.DataFrame({
        "Arrival_Date": [t - pd.Timedelta(days=25), t],
        "Modal_Price": [2000.0, 2140.0]
    })
    assert np.isnan(predict_drift(df_no_anchor, t))
    
    # Missing y(t) -> abstain
    df_no_t = pd.DataFrame({
        "Arrival_Date": [anchor_dt],
        "Modal_Price": [2000.0]
    })
    assert np.isnan(predict_drift(df_no_t, t))


def test_extract_target():
    """
    Target: modal price in [t+6, t+8] closest to t+7. Tie-breaker: earlier date.
    Returns: (target_price, target_date, is_exact_t7).
    """
    t = pd.Timestamp("2025-06-15")
    t7 = t + pd.Timedelta(days=7) # 2025-06-22
    
    # Exact t+7 available
    df_exact = pd.DataFrame({
        "Arrival_Date": [t + pd.Timedelta(days=6), t7, t + pd.Timedelta(days=8)],
        "Modal_Price": [2100.0, 2200.0, 2300.0]
    })
    price, dt_str, is_exact = extract_target(df_exact, t)
    assert price == 2200.0
    assert dt_str == "2025-06-22"
    assert is_exact is True
    
    # Only t+6 available
    df_t6 = pd.DataFrame({
        "Arrival_Date": [t + pd.Timedelta(days=6)],
        "Modal_Price": [2100.0]
    })
    price, dt_str, is_exact = extract_target(df_t6, t)
    assert price == 2100.0
    assert dt_str == "2025-06-21"
    assert is_exact is False
    
    # Tie between t+6 and t+8 (both 1 day from t+7) -> earlier (t+6)
    df_tie = pd.DataFrame({
        "Arrival_Date": [t + pd.Timedelta(days=6), t + pd.Timedelta(days=8)],
        "Modal_Price": [2100.0, 2300.0]
    })
    price, dt_str, is_exact = extract_target(df_tie, t)
    assert price == 2100.0
    assert dt_str == "2025-06-21"
    assert is_exact is False
    
    # Empty in window -> None
    df_empty = pd.DataFrame({
        "Arrival_Date": [t + pd.Timedelta(days=5), t + pd.Timedelta(days=10)],
        "Modal_Price": [2000.0, 2400.0]
    })
    price, dt_str, is_exact = extract_target(df_empty, t)
    assert price is None
    assert dt_str is None
    assert is_exact is False


def test_compute_forecast_metrics():
    """Verify arithmetic precision of forecast metrics."""
    y_true = np.array([2000.0, 2100.0, 2200.0, 2300.0])
    y_pred = np.array([2050.0, 2100.0, 2150.0, 2350.0])
    y_naive = np.array([2000.0, 2050.0, 2100.0, 2200.0])
    
    # Errors: [50, 0, -50, 50]
    # Abs errors: [50, 0, 50, 50] -> MAE = 37.5
    # Sq errors: [2500, 0, 2500, 2500] -> MSE = 1875.0 -> RMSE = sqrt(1875) ≈ 43.3013
    # Pct errors: [50/2000 (2.5%), 0 (0%), 50/2200 (2.27%), 50/2300 (2.17%)] -> all <= 5% -> 100%
    # Median AE: sorted [0, 50, 50, 50] -> median = 50.0
    # Bias: (50 + 0 - 50 + 50) / 4 = 12.5
    # Naive abs errors: [0, 50, 100, 100] -> MAE_naive = 62.5
    # Skill vs Naive: 1 - 37.5 / 62.5 = 1 - 0.6 = 0.4 (40%)
    
    metrics = compute_forecast_metrics(y_true, y_pred, y_naive, total_eligible_origins=4)
    assert metrics["n_origins"] == 4
    assert metrics["abstention_rate_pct"] == 0.0
    assert metrics["mae"] == 37.5
    assert metrics["rmse"] == pytest.approx(43.3013, rel=1e-4)
    assert metrics["median_ae"] == 50.0
    assert metrics["bias"] == 12.5
    assert metrics["share_within_5pct"] == 100.0
    assert metrics["skill_vs_naive"] == 0.4


def test_cluster_bootstrap_series():
    """Verify cluster bootstrap determinism and confidence interval structure."""
    df_eval = pd.DataFrame({
        "series_id": ["s1", "s1", "s2", "s2", "s3", "s3"],
        "target_price": [2000.0, 2050.0, 2100.0, 2150.0, 2200.0, 2250.0],
        "pred_price":   [2020.0, 2040.0, 2110.0, 2140.0, 2220.0, 2260.0],
        "pred_naive":   [2000.0, 2000.0, 2100.0, 2100.0, 2200.0, 2200.0]
    })
    
    res1 = cluster_bootstrap_series(df_eval, n_resamples=100, seed=42)
    res2 = cluster_bootstrap_series(df_eval, n_resamples=100, seed=42)
    
    assert res1 == res2
    assert res1["mae_ci_lower"] <= res1["mae_mean"] <= res1["mae_ci_upper"]
    assert res1["skill_ci_lower"] <= res1["skill_mean"] <= res1["skill_ci_upper"]

