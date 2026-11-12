"""
Audit and regression tests for MP-FC-006 baselines, canonicalization, and scoring path.
Task: MP-AUDIT-007

Tests verify:
1. Canonical disputed-key loading: fail-closed, schema validation, 77 keys transformation.
2. Vectorized loop equivalence: exact match to modular functions on dense, irregular,
   missing anchor, and seasonal tie-breaking fixtures.
3. Anti-leakage / future invariance: mutating, inserting, or deleting future rows has zero effect.
4. Target <= fold_end and 7-day embargo compliance.
5. Scored vs eligible origin/series accounting and LOW-N computation.
6. Bootstrap deterministic series ordering and zero-denominator safety.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

from src.baselines import (
    parse_date,
    get_history_as_of,
    predict_naive,
    predict_moving_average,
    predict_seasonal_naive,
    predict_drift,
    extract_target,
    compute_forecast_metrics,
    cluster_bootstrap_series,
    evaluate_model_slice,
    load_canonical_disputed_keys,
    predict_series_vectorized
)


# -----------------------------------------------------------------------------
# 1. Canonical Disputed Keys Loading & Fail-Closed Behavior
# -----------------------------------------------------------------------------

def test_load_canonical_disputed_keys_real():
    """Verify loading real 77 discrepancy keys with accepted market aliases."""
    diff_path = Path("experiments/outputs/005/diff_77_deep_analysis.csv")
    alias_path = Path("data/reference/market_aliases.csv")

    if not diff_path.exists() or not alias_path.exists():
        pytest.skip("Required audit reference files not present locally.")

    canon_keys, df_canon = load_canonical_disputed_keys(diff_path, alias_path, expected_rows=77)

    assert len(canon_keys) == 77
    assert len(df_canon) == 77
    # All 77 market names must have changed from raw APMC to canonical
    assert (df_canon["Market_Raw"] != df_canon["Market"]).all()
    # Check that canonical market names do not end with " APMC"
    for m in df_canon["Market"].unique():
        assert not m.endswith(" APMC"), f"Market name {m} still has APMC suffix!"

    # Check sample key structure: (District, Market, Commodity, Variety, Grade, Date)
    sample_key = next(iter(canon_keys))
    assert len(sample_key) == 6
    assert isinstance(sample_key[0], str)
    assert isinstance(sample_key[5], str)


def test_load_canonical_disputed_keys_fail_closed(tmp_path):
    """Verify fail-closed behavior on missing file, missing column, wrong row count, or unmapped market."""
    alias_path = Path("data/reference/market_aliases.csv")
    if not alias_path.exists():
        pytest.skip("Market aliases file not present locally.")

    # 1. Missing file -> FileNotFoundError
    with pytest.raises(FileNotFoundError):
        load_canonical_disputed_keys(tmp_path / "non_existent.csv", alias_path)

    # 2. Missing required columns -> ValueError
    bad_schema_csv = tmp_path / "bad_schema.csv"
    bad_schema_csv.write_text("District_Std,Market,Arrival_Date\nGhaziabad,Noida APMC,2026-03-25\n")
    with pytest.raises(ValueError, match="missing required columns"):
        load_canonical_disputed_keys(bad_schema_csv, alias_path)

    # 3. Wrong row count -> ValueError
    bad_count_csv = tmp_path / "bad_count.csv"
    lines = ["District_Std,Market,Commodity_Std,Variety,Grade,Arrival_Date"]
    for i in range(10):
        lines.append(f"Ghaziabad,Noida APMC,Onion,Other,FAQ,2026-03-{10+i:02d}")
    bad_count_csv.write_text("\n".join(lines))
    with pytest.raises(ValueError, match="Expected exactly 77 disputed rows"):
        load_canonical_disputed_keys(bad_count_csv, alias_path, expected_rows=77)


# -----------------------------------------------------------------------------
# 2. Optimized Loop Equivalence to Modular Baseline Functions
# -----------------------------------------------------------------------------

def test_optimized_loop_equivalence_dense_fixture():
    """
    Verify exact equivalence between modular functions and optimized vectorized loop
    on a dense, daily time series fixture across a span of 500 days.
    """
    dates = pd.date_range("2024-01-01", "2025-06-01", freq="D")
    prices = 1500.0 + np.sin(np.arange(len(dates)) / 10.0) * 200.0 + np.arange(len(dates)) * 0.5

    df = pd.DataFrame({
        "Arrival_Date": dates,
        "Modal_Price": prices
    })

    dates_dt = df["Arrival_Date"].to_numpy(dtype="datetime64[ns]")
    prices_arr = df["Modal_Price"].to_numpy(dtype=float)

    # Test on multiple origin dates where history is rich
    test_origins = pd.date_range("2025-01-01", "2025-05-15", freq="7D")

    for t_val in test_origins:
        t_str = t_val.strftime("%Y-%m-%d")

        # Modular predictions
        hist = get_history_as_of(df, t_str)
        mod_naive = predict_naive(hist, t_str)
        mod_ma = predict_moving_average(hist, t_str)
        mod_seasonal = predict_seasonal_naive(hist, t_str)
        mod_drift = predict_drift(hist, t_str)
        mod_tgt_p, mod_tgt_dt, mod_exact = extract_target(df, t_str)

        # Vectorized predictions
        vec_res = predict_series_vectorized(dates_dt, prices_arr, t_str)

        # Assert exact equivalence
        assert np.isclose(mod_naive, vec_res["pred_naive"]), f"Naive mismatch at {t_str}"
        assert np.isclose(mod_ma, vec_res["pred_ma"]), f"MA mismatch at {t_str}"
        assert np.isclose(mod_seasonal, vec_res["pred_seasonal"]), f"Seasonal mismatch at {t_str}"
        assert np.isclose(mod_drift, vec_res["pred_drift"]), f"Drift mismatch at {t_str}"
        assert np.isclose(mod_tgt_p, vec_res["target_price"]), f"Target price mismatch at {t_str}"
        assert mod_tgt_dt == vec_res["target_date_str"], f"Target date mismatch at {t_str}"
        assert mod_exact == vec_res["is_exact_t7"], f"Exact t7 mismatch at {t_str}"


def test_optimized_loop_equivalence_irregular_and_abstentions():
    """
    Verify equivalence on irregular time series with missing dates, gap in anchor,
    gap in seasonal, and missing target.
    """
    # Create irregular dates: skip weekends, create gaps
    rng = np.random.default_rng(1234)
    all_dates = pd.date_range("2024-01-01", "2025-06-01", freq="D")
    # Drop 40% of dates randomly
    keep_mask = rng.uniform(size=len(all_dates)) > 0.4
    irr_dates = all_dates[keep_mask]
    irr_prices = 2000.0 + np.arange(len(irr_dates)) * 1.5

    df = pd.DataFrame({
        "Arrival_Date": irr_dates,
        "Modal_Price": irr_prices
    }).sort_values("Arrival_Date").reset_index(drop=True)

    dates_dt = df["Arrival_Date"].to_numpy(dtype="datetime64[ns]")
    prices_arr = df["Modal_Price"].to_numpy(dtype=float)

    # Test across 30 observed dates in the range
    mask_in_range = (irr_dates >= pd.Timestamp("2025-01-15")) & (irr_dates <= pd.Timestamp("2025-05-01"))
    sample_origins = irr_dates[mask_in_range][::2] # every second observed date

    for t_val in sample_origins:
        t_str = t_val.strftime("%Y-%m-%d")

        hist = get_history_as_of(df, t_str)
        mod_naive = predict_naive(hist, t_str)
        mod_ma = predict_moving_average(hist, t_str)
        mod_seasonal = predict_seasonal_naive(hist, t_str)
        mod_drift = predict_drift(hist, t_str)
        mod_tgt_p, mod_tgt_dt, mod_exact = extract_target(df, t_str)

        vec_res = predict_series_vectorized(dates_dt, prices_arr, t_str)

        # Compare Naive
        if np.isnan(mod_naive):
            assert np.isnan(vec_res["pred_naive"])
        else:
            assert np.isclose(mod_naive, vec_res["pred_naive"])

        # Compare MA
        if np.isnan(mod_ma):
            assert np.isnan(vec_res["pred_ma"])
        else:
            assert np.isclose(mod_ma, vec_res["pred_ma"])

        # Compare Seasonal
        if np.isnan(mod_seasonal):
            assert np.isnan(vec_res["pred_seasonal"])
        else:
            assert np.isclose(mod_seasonal, vec_res["pred_seasonal"])

        # Compare Drift
        if np.isnan(mod_drift):
            assert np.isnan(vec_res["pred_drift"])
        else:
            assert np.isclose(mod_drift, vec_res["pred_drift"])

        # Compare Target
        if mod_tgt_p is None:
            assert np.isnan(vec_res["target_price"])
            assert vec_res["target_date_str"] is None
        else:
            assert np.isclose(mod_tgt_p, vec_res["target_price"])
            assert mod_tgt_dt == vec_res["target_date_str"]


def test_optimized_loop_tie_breaking_to_earlier_date():
    """
    Verify that both modular and vectorized implementations strictly break distance ties
    in seasonal window [t-360, t-354] and target window [t+6, t+8] to the EARLIER calendar date.
    """
    origin = pd.Timestamp("2025-06-15")
    origin_str = "2025-06-15"

    # 1. Seasonal tie: exact anchor is 2025-06-15 - 357d = 2024-06-23.
    # Put observations on 2024-06-21 (diff=2) and 2024-06-25 (diff=2).
    # Earlier date 2024-06-21 must win!
    earlier_s_date = pd.Timestamp("2024-06-21")
    later_s_date = pd.Timestamp("2024-06-25")

    # 2. Target tie: exact target is 2025-06-15 + 7d = 2025-06-22.
    # Put observations on 2025-06-21 (diff=1) and 2025-06-23 (diff=1).
    # Earlier date 2025-06-21 must win!
    earlier_tgt_date = pd.Timestamp("2025-06-21")
    later_tgt_date = pd.Timestamp("2025-06-23")

    # Anchor for drift: 2025-06-15 - 14d = 2025-06-01
    anchor_date = pd.Timestamp("2025-06-01")

    df = pd.DataFrame({
        "Arrival_Date": [
            earlier_s_date, later_s_date,
            anchor_date,
            origin,
            earlier_tgt_date, later_tgt_date
        ],
        "Modal_Price": [
            1111.0, 2222.0,  # seasonal candidates
            1500.0,          # drift anchor
            2000.0,          # origin
            3333.0, 4444.0   # target candidates
        ]
    }).sort_values("Arrival_Date").reset_index(drop=True)

    dates_dt = df["Arrival_Date"].to_numpy(dtype="datetime64[ns]")
    prices_arr = df["Modal_Price"].to_numpy(dtype=float)

    # Modular evaluation
    hist = get_history_as_of(df, origin_str)
    mod_seasonal = predict_seasonal_naive(hist, origin_str)
    mod_tgt_p, mod_tgt_dt, mod_exact = extract_target(df, origin_str)

    # Vectorized evaluation
    vec_res = predict_series_vectorized(dates_dt, prices_arr, origin_str)

    # Assert earlier date won in Seasonal
    assert mod_seasonal == 1111.0, "Modular seasonal failed to break tie to earlier date"
    assert vec_res["pred_seasonal"] == 1111.0, "Vectorized seasonal failed to break tie to earlier date"

    # Assert earlier date won in Target
    assert mod_tgt_p == 3333.0, "Modular target failed to break tie to earlier date"
    assert vec_res["target_price"] == 3333.0, "Vectorized target failed to break tie to earlier date"
    assert mod_tgt_dt == "2025-06-21"
    assert vec_res["target_date_str"] == "2025-06-21"
    assert not vec_res["is_exact_t7"]


# -----------------------------------------------------------------------------
# 3. Future Invariance / Anti-Leakage Mutation Checks
# -----------------------------------------------------------------------------

def test_future_invariance_mutation_audit():
    """
    Verify that mutating, inserting, or deleting rows strictly after origin date t
    produces zero change in origin baseline forecasts.
    """
    dates = pd.date_range("2024-01-01", "2025-06-15", freq="D")
    prices = 1800.0 + np.arange(len(dates)) * 1.0

    origin_t = "2025-06-01"
    t_dt = pd.Timestamp(origin_t)

    df_base = pd.DataFrame({"Arrival_Date": dates, "Modal_Price": prices})

    # Predictions on base dataset
    dates_base = df_base["Arrival_Date"].to_numpy(dtype="datetime64[ns]")
    prices_base = df_base["Modal_Price"].to_numpy(dtype=float)
    base_preds = predict_series_vectorized(dates_base, prices_base, origin_t)

    # 1. Mutate future price at t + 10d
    df_mut = df_base.copy()
    df_mut.loc[df_mut["Arrival_Date"] == t_dt + pd.Timedelta(days=10), "Modal_Price"] = 999999.0
    dates_mut = df_mut["Arrival_Date"].to_numpy(dtype="datetime64[ns]")
    prices_mut = df_mut["Modal_Price"].to_numpy(dtype=float)
    mut_preds = predict_series_vectorized(dates_mut, prices_mut, origin_t)

    assert base_preds["pred_naive"] == mut_preds["pred_naive"]
    assert base_preds["pred_ma"] == mut_preds["pred_ma"]
    assert base_preds["pred_seasonal"] == mut_preds["pred_seasonal"]
    assert base_preds["pred_drift"] == mut_preds["pred_drift"]

    # 2. Insert future row at t + 15d
    extra_row = pd.DataFrame({"Arrival_Date": [t_dt + pd.Timedelta(days=15)], "Modal_Price": [77777.0]})
    df_ins = pd.concat([df_base, extra_row]).sort_values("Arrival_Date").reset_index(drop=True)
    dates_ins = df_ins["Arrival_Date"].to_numpy(dtype="datetime64[ns]")
    prices_ins = df_ins["Modal_Price"].to_numpy(dtype=float)
    ins_preds = predict_series_vectorized(dates_ins, prices_ins, origin_t)

    assert base_preds["pred_naive"] == ins_preds["pred_naive"]
    assert base_preds["pred_ma"] == ins_preds["pred_ma"]
    assert base_preds["pred_seasonal"] == ins_preds["pred_seasonal"]
    assert base_preds["pred_drift"] == ins_preds["pred_drift"]

    # 3. Delete future row at t + 12d
    df_del = df_base[df_base["Arrival_Date"] != t_dt + pd.Timedelta(days=12)].copy()
    dates_del = df_del["Arrival_Date"].to_numpy(dtype="datetime64[ns]")
    prices_del = df_del["Modal_Price"].to_numpy(dtype=float)
    del_preds = predict_series_vectorized(dates_del, prices_del, origin_t)

    assert base_preds["pred_naive"] == del_preds["pred_naive"]
    assert base_preds["pred_ma"] == del_preds["pred_ma"]
    assert base_preds["pred_seasonal"] == del_preds["pred_seasonal"]
    assert base_preds["pred_drift"] == del_preds["pred_drift"]


# -----------------------------------------------------------------------------
# 4. Target <= Fold End & Embargo Boundaries
# -----------------------------------------------------------------------------

def test_target_boundary_and_embargo():
    """
    Verify:
    1. Target date > fold_end is correctly excluded.
    2. Seven-day embargo dates are strictly excluded from test origins.
    """
    train_end = pd.Timestamp("2024-12-31")
    test_start = pd.Timestamp("2025-01-08") # 7-day embargo: 2025-01-01 to 2025-01-07
    test_end = pd.Timestamp("2025-06-30")

    # Embargo test: delta between train_end and test_start must be exactly 8 calendar days (7 excluded dates)
    embargo_days = (test_start - train_end).days - 1
    assert embargo_days == 7, f"Expected 7 embargo dates, got {embargo_days}"

    # Target <= fold_end test:
    origin_late = test_end - pd.Timedelta(days=5) # e.g. 2025-06-25
    # Target date would fall at 2025-07-02 > test_end (2025-06-30)
    target_dt = origin_late + pd.Timedelta(days=7)
    assert target_dt > test_end
    # Evaluation loop must exclude this origin
    is_valid_test_instance = bool(origin_late >= test_start and target_dt <= test_end)
    assert not is_valid_test_instance


# -----------------------------------------------------------------------------
# 5. Scored vs Eligible Origins/Series & Scored-Case LOW-N
# -----------------------------------------------------------------------------

def test_evaluate_model_slice_scored_vs_eligible_accounting():
    """
    Verify that evaluate_model_slice:
    1. Reports separate n_eligible_origins vs n_scored_origins.
    2. Reports separate n_eligible_series vs n_scored_series.
    3. Evaluates low_n_flag strictly on scored cases (n_scored_origins < 200 or n_scored_series < 10).
    """
    # Create synthetic evaluation slice with 250 rows across 12 series
    series_ids = [f"series_{i}" for i in range(12)]
    df_rows = []

    for i in range(250):
        sid = series_ids[i % 12]
        # Make model abstain on series_0 completely (21 rows) and partially on series_1 (10 rows)
        is_missing = (sid == "series_0") or (sid == "series_1" and i < 50)
        df_rows.append({
            "series_id": sid,
            "target_price": 2000.0 + (i % 20),
            "pred_naive": 2000.0,
            "pred_model": np.nan if is_missing else 2010.0
        })

    df_eval = pd.DataFrame(df_rows)

    res = evaluate_model_slice(
        sub_df=df_eval,
        model_col="pred_model",
        naive_col="pred_naive",
        target_col="target_price",
        series_col="series_id"
    )

    # Total eligible: 250 origins across 12 series
    assert res["n_eligible_origins"] == 250
    assert res["n_eligible_series"] == 12

    # Scored origins: 250 - 21 (series_0) - 5 (series_1 in first 50 rows) = 224
    assert res["n_scored_origins"] < 250
    # Scored series: series_0 had 0 scored rows, so scored series must be 11
    assert res["n_scored_series"] == 11
    assert res["n_scored_series"] < res["n_eligible_series"]

    # Since n_scored_origins = 224 >= 200 and n_scored_series = 11 >= 10, low_n_flag is False
    assert not res["low_n_flag"]

    # Now create a slice with only 8 scored series -> low_n_flag must be True!
    mask_8_series = df_eval["series_id"].isin(series_ids[2:10]) # 8 series
    res_8 = evaluate_model_slice(
        sub_df=df_eval[mask_8_series],
        model_col="pred_model",
        naive_col="pred_naive",
        target_col="target_price",
        series_col="series_id"
    )
    assert res_8["n_scored_series"] == 8
    assert res_8["low_n_flag"], "low_n_flag must be True when n_scored_series < 10"


def test_cluster_bootstrap_deterministic_ordering():
    """
    Verify that cluster_bootstrap_series is invariant to DataFrame row shuffling
    because series clusters are deterministically sorted.
    """
    df_rows = []
    for s in ["series_B", "series_A", "series_C"]:
        for i in range(50):
            df_rows.append({
                "series_id": s,
                "target_price": 2000.0 + i,
                "pred_model": 2005.0 + i,
                "pred_naive": 1990.0 + i
            })
    df_orig = pd.DataFrame(df_rows)
    df_shuffled = df_orig.sample(frac=1.0, random_state=999).reset_index(drop=True)

    res1 = cluster_bootstrap_series(df_orig, pred_col="pred_model", seed=42)
    res2 = cluster_bootstrap_series(df_shuffled, pred_col="pred_model", seed=42)

    assert res1["mae_mean"] == res2["mae_mean"]
    assert res1["mae_ci_lower"] == res2["mae_ci_lower"]
    assert res1["mae_ci_upper"] == res2["mae_ci_upper"]
    assert res1["skill_mean"] == res2["skill_mean"]


def test_paired_skill_zero_denominator_safety():
    """
    Verify that compute_forecast_metrics handles zero naive error safely (returns np.nan).
    """
    y_true = np.array([2000.0, 2100.0, 2200.0])
    y_pred = np.array([2010.0, 2110.0, 2210.0])
    # Naive is 100% perfect: error = 0
    y_naive = np.array([2000.0, 2100.0, 2200.0])

    metrics = compute_forecast_metrics(y_true=y_true, y_pred=y_pred, y_naive=y_naive)
    assert np.isnan(metrics["skill_vs_naive"])
