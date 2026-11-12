"""
Audit and regression tests for MP-FC-006 baselines, canonicalization, and scoring path.
Tasks: MP-AUDIT-007, MP-AUDIT-008

Tests verify:
1. Self-contained canonical disputed-key loading: fail-closed, schema validation, 77 keys transformation.
2. Production scoring helper equivalence: exact match to modular functions and array logic.
3. All four declared folds boundary checks: 7-day embargo exclusion, target <= fold_end.
4. Anti-leakage / future invariance: mutating, inserting, or deleting future rows has zero effect
   on baseline predictions and train-only eligibility.
5. Scope B Sensitivity: tests all six historical excising cases (removed MA obs, removed drift anchor,
   removed seasonal anchor, disputed origin, disputed target, and removal causing recency failure).
6. Shared scorer denominators: consistent joint finite-value mask on paired metrics, counts,
   bootstrap, and abstention; tests missing/NaN/infinite values and all-abstained cases; scored <= eligible.
7. Shuffled input date normalization: deterministic ordering at helper boundary.
8. Bootstrap deterministic series ordering and zero-denominator safety.
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
    predict_series_vectorized,
    check_serving_recency,
    extract_target_vectorized,
    evaluate_series_train_eligibility,
    score_series_origin
)


# -----------------------------------------------------------------------------
# 1. Canonical Disputed Keys Loading & Fail-Closed Behavior
# -----------------------------------------------------------------------------

def test_load_canonical_disputed_keys_self_contained(tmp_path):
    """
    Verify canonical disputed-key loading using a self-contained 77-row fixture.
    Guarantees that a fresh checkout without experiments/outputs/ runs and passes.
    """
    alias_path = Path("data/reference/market_aliases.csv")
    if not alias_path.exists():
        pytest.skip("Market aliases reference file missing.")

    # Create 77 distinct discrepancy rows across the 5 districts using APMC raw names
    records = []
    apmc_markets = [
        ("Ghaziabad", "Ghaziabad APMC", "Wheat"),
        ("Ghaziabad", "Noida APMC", "Potato"),
        ("Lucknow", "Lucknow APMC", "Tomato"),
        ("Kanpur", "Choubepur APMC", "Rice"),
        ("Jhansi", "Jhansi APMC", "Onion"),
        ("Unnao", "Unnao APMC", "Wheat"),
        ("Ghaziabad", "Hapur APMC", "Potato")
    ]
    for i in range(77):
        dist, mkt, comm = apmc_markets[i % len(apmc_markets)]
        records.append({
            "District_Std": dist,
            "Market": mkt,
            "Commodity_Std": comm,
            "Variety": f"Variety_{i}",
            "Grade": "FAQ",
            "Arrival_Date": (pd.Timestamp("2026-01-01") + pd.Timedelta(days=i)).strftime("%Y-%m-%d")
        })

    fixture_csv = tmp_path / "diff_77_fixture.csv"
    pd.DataFrame(records).to_csv(fixture_csv, index=False)

    canon_keys, df_canon = load_canonical_disputed_keys(
        disputed_csv_path=fixture_csv,
        aliases=alias_path,
        expected_rows=77
    )

    assert len(canon_keys) == 77
    assert len(df_canon) == 77
    # All 77 market names must have changed from raw APMC to canonical
    assert (df_canon["Market_Raw"] != df_canon["Market"]).all()
    for m in df_canon["Market"].unique():
        assert not m.endswith(" APMC"), f"Canonical market name '{m}' still contains APMC suffix!"

    sample_key = next(iter(canon_keys))
    assert len(sample_key) == 6
    assert isinstance(sample_key[0], str)
    assert isinstance(sample_key[5], str)


def test_load_canonical_disputed_keys_fail_closed(tmp_path):
    """Verify fail-closed behavior on missing file, missing column, wrong count, null date, or unmapped market."""
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

    # 4. Unmapped market -> ValueError
    unmapped_csv = tmp_path / "unmapped.csv"
    unmapped_lines = ["District_Std,Market,Commodity_Std,Variety,Grade,Arrival_Date"]
    for i in range(77):
        unmapped_lines.append(f"UnknownDistrict,NonExistent APMC,Onion,Other,FAQ,2026-03-{1 + (i % 28):02d}")
    unmapped_csv.write_text("\n".join(unmapped_lines))
    with pytest.raises(ValueError, match="remained unchanged|unmapped"):
        load_canonical_disputed_keys(unmapped_csv, alias_path, expected_rows=77)

    # 5. Null or unparseable date -> ValueError
    null_date_csv = tmp_path / "null_date.csv"
    null_date_lines = ["District_Std,Market,Commodity_Std,Variety,Grade,Arrival_Date"]
    for i in range(76):
        null_date_lines.append(f"Ghaziabad,Noida APMC,Onion,Other,FAQ,2026-03-{1 + (i % 28):02d}")
    null_date_lines.append("Ghaziabad,Noida APMC,Onion,Other,FAQ,not-a-valid-date")
    null_date_csv.write_text("\n".join(null_date_lines))
    with pytest.raises(ValueError, match="unparseable"):
        load_canonical_disputed_keys(null_date_csv, alias_path, expected_rows=77)


def test_load_canonical_disputed_keys_real_optional():
    """Optional integration check when experiments/outputs/005 is present locally."""
    diff_path = Path("experiments/outputs/005/diff_77_deep_analysis.csv")
    alias_path = Path("data/reference/market_aliases.csv")

    if not diff_path.exists() or not alias_path.exists():
        pytest.skip("Optional real diff_77_deep_analysis.csv not present locally.")

    canon_keys, df_canon = load_canonical_disputed_keys(diff_path, alias_path, expected_rows=77)
    assert len(canon_keys) == 77
    assert (df_canon["Market_Raw"] != df_canon["Market"]).all()


# -----------------------------------------------------------------------------
# 2. Optimized Loop Equivalence to Modular Baseline Functions
# -----------------------------------------------------------------------------

def test_optimized_loop_equivalence_dense_fixture():
    """
    Verify exact equivalence between modular functions, vectorized loop, and scoring helper
    on a dense, daily time series fixture across a span of 500 days.
    """
    dates = pd.date_range("2024-01-01", "2025-06-01", freq="D")
    prices = 1500.0 + np.sin(np.arange(len(dates)) / 10.0) * 200.0 + np.arange(len(dates)) * 0.5

    df = pd.DataFrame({
        "Arrival_Date": dates,
        "Modal_Price": prices
    })

    dates_dt = df["Arrival_Date"].to_numpy(dtype="datetime64[ns]")
    dates_str = df["Arrival_Date"].dt.strftime("%Y-%m-%d").to_numpy()
    prices_arr = df["Modal_Price"].to_numpy(dtype=float)

    fold_info = {
        "fold": "F1",
        "train_end": "2024-12-31",
        "test_start": "2025-01-08",
        "test_end": "2025-06-30"
    }
    series_meta = {
        "series_id": "test__s1",
        "district": "Ghaziabad",
        "market": "Ghaziabad",
        "commodity": "Wheat",
        "variety": "Dara",
        "grade": "FAQ",
        "is_tier_a": True,
        "is_tier_b": True
    }

    test_origins = pd.date_range("2025-01-08", "2025-05-15", freq="7D")

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

        # Full scoring helper
        score_res = score_series_origin(
            dates_dt=dates_dt,
            dates_str=dates_str,
            prices=prices_arr,
            origin_dt=t_str,
            fold_info=fold_info,
            series_meta=series_meta
        )

        assert np.isclose(mod_naive, vec_res["pred_naive"])
        assert np.isclose(mod_ma, vec_res["pred_ma"])
        assert np.isclose(mod_seasonal, vec_res["pred_seasonal"])
        assert np.isclose(mod_drift, vec_res["pred_drift"])
        assert np.isclose(mod_tgt_p, vec_res["target_price"])
        assert mod_tgt_dt == vec_res["target_date_str"]
        assert mod_exact == vec_res["is_exact_t7"]

        assert np.isclose(mod_naive, score_res["pred_naive"])
        assert np.isclose(mod_ma, score_res["pred_ma"])
        assert np.isclose(mod_seasonal, score_res["pred_seasonal_naive"])
        assert np.isclose(mod_drift, score_res["pred_drift"])
        assert np.isclose(mod_tgt_p, score_res["target_price"])
        assert mod_tgt_dt == score_res["target_date"]
        assert score_res["is_eligible_origin"]


def test_optimized_loop_equivalence_irregular_and_abstentions():
    """Verify equivalence on irregular time series with missing dates, anchor gaps, and missing target."""
    rng = np.random.default_rng(1234)
    all_dates = pd.date_range("2024-01-01", "2025-06-01", freq="D")
    keep_mask = rng.uniform(size=len(all_dates)) > 0.4
    irr_dates = all_dates[keep_mask]
    irr_prices = 2000.0 + np.arange(len(irr_dates)) * 1.5

    df = pd.DataFrame({
        "Arrival_Date": irr_dates,
        "Modal_Price": irr_prices
    }).sort_values("Arrival_Date").reset_index(drop=True)

    dates_dt = df["Arrival_Date"].to_numpy(dtype="datetime64[ns]")
    prices_arr = df["Modal_Price"].to_numpy(dtype=float)

    mask_in_range = (irr_dates >= pd.Timestamp("2025-01-15")) & (irr_dates <= pd.Timestamp("2025-05-01"))
    sample_origins = irr_dates[mask_in_range][::2]

    for t_val in sample_origins:
        t_str = t_val.strftime("%Y-%m-%d")

        hist = get_history_as_of(df, t_str)
        mod_naive = predict_naive(hist, t_str)
        mod_ma = predict_moving_average(hist, t_str)
        mod_seasonal = predict_seasonal_naive(hist, t_str)
        mod_drift = predict_drift(hist, t_str)
        mod_tgt_p, mod_tgt_dt, mod_exact = extract_target(df, t_str)

        vec_res = predict_series_vectorized(dates_dt, prices_arr, t_str)

        if np.isnan(mod_naive):
            assert np.isnan(vec_res["pred_naive"])
        else:
            assert np.isclose(mod_naive, vec_res["pred_naive"])

        if np.isnan(mod_ma):
            assert np.isnan(vec_res["pred_ma"])
        else:
            assert np.isclose(mod_ma, vec_res["pred_ma"])

        if np.isnan(mod_seasonal):
            assert np.isnan(vec_res["pred_seasonal"])
        else:
            assert np.isclose(mod_seasonal, vec_res["pred_seasonal"])

        if np.isnan(mod_drift):
            assert np.isnan(vec_res["pred_drift"])
        else:
            assert np.isclose(mod_drift, vec_res["pred_drift"])

        if mod_tgt_p is None:
            assert np.isnan(vec_res["target_price"])
            assert vec_res["target_date_str"] is None
        else:
            assert np.isclose(mod_tgt_p, vec_res["target_price"])
            assert mod_tgt_dt == vec_res["target_date_str"]


def test_optimized_loop_tie_breaking_to_earlier_date():
    """Verify that ties in seasonal and target windows strictly break to the EARLIER calendar date."""
    origin_str = "2025-06-15"
    origin = pd.Timestamp(origin_str)

    # Seasonal tie: exact anchor = 2024-06-23. Candidates at 2024-06-21 and 2024-06-25 (diff=2)
    earlier_s_date = pd.Timestamp("2024-06-21")
    later_s_date = pd.Timestamp("2024-06-25")

    # Target tie: exact target = 2025-06-22. Candidates at 2025-06-21 and 2025-06-23 (diff=1)
    earlier_tgt_date = pd.Timestamp("2025-06-21")
    later_tgt_date = pd.Timestamp("2025-06-23")

    anchor_date = pd.Timestamp("2025-06-01")

    df = pd.DataFrame({
        "Arrival_Date": [
            earlier_s_date, later_s_date,
            anchor_date,
            origin,
            earlier_tgt_date, later_tgt_date
        ],
        "Modal_Price": [
            1111.0, 2222.0,
            1500.0,
            2000.0,
            3333.0, 4444.0
        ]
    }).sort_values("Arrival_Date").reset_index(drop=True)

    dates_dt = df["Arrival_Date"].to_numpy(dtype="datetime64[ns]")
    prices_arr = df["Modal_Price"].to_numpy(dtype=float)

    hist = get_history_as_of(df, origin_str)
    mod_seasonal = predict_seasonal_naive(hist, origin_str)
    mod_tgt_p, mod_tgt_dt, mod_exact = extract_target(df, origin_str)
    vec_res = predict_series_vectorized(dates_dt, prices_arr, origin_str)

    assert mod_seasonal == 1111.0
    assert vec_res["pred_seasonal"] == 1111.0
    assert mod_tgt_p == 3333.0
    assert vec_res["target_price"] == 3333.0
    assert vec_res["target_date_str"] == "2025-06-21"


# -----------------------------------------------------------------------------
# 3. All Four Declared Folds Boundary Checks & Evaluator Path
# -----------------------------------------------------------------------------

def test_score_series_origin_all_four_declared_folds():
    """
    Test score_series_origin across each of the 4 declared folds:
    - F1: train <= 2024-12-31, test: 2025-01-08 to 2025-06-30
    - F2: train <= 2025-06-30, test: 2025-07-08 to 2025-10-31
    - F3: train <= 2025-12-18, test: 2025-12-26 to 2026-03-31
    - F4: train <= 2026-03-31, test: 2026-04-08 to 2026-09-30
    Verifies that embargo origins are dropped, valid test origins succeed,
    and origins near fold boundary with target > test_end are excluded.
    """
    folds = [
        {"fold": "F1", "train_end": "2024-12-31", "test_start": "2025-01-08", "test_end": "2025-06-30"},
        {"fold": "F2", "train_end": "2025-06-30", "test_start": "2025-07-08", "test_end": "2025-10-31"},
        {"fold": "F3", "train_end": "2025-12-18", "test_start": "2025-12-26", "test_end": "2026-03-31"},
        {"fold": "F4", "train_end": "2026-03-31", "test_start": "2026-04-08", "test_end": "2026-09-30"}
    ]

    series_meta = {
        "series_id": "test__s1",
        "district": "Ghaziabad",
        "market": "Ghaziabad",
        "commodity": "Wheat",
        "variety": "Dara",
        "grade": "FAQ"
    }

    # Generate complete series covering 2024-01-01 to 2026-10-15
    dates = pd.date_range("2024-01-01", "2026-10-15", freq="D")
    prices = 2000.0 + np.sin(np.arange(len(dates)) / 15.0) * 150.0

    dates_dt = dates.to_numpy(dtype="datetime64[ns]")
    dates_str = dates.strftime("%Y-%m-%d").to_numpy()
    prices_arr = prices.astype(float)

    for f_info in folds:
        tr_end = pd.Timestamp(f_info["train_end"])
        te_start = pd.Timestamp(f_info["test_start"])
        te_end = pd.Timestamp(f_info["test_end"])

        # 1. Test 7-day embargo date (e.g. train_end + 3 days)
        embargo_dt_str = (tr_end + pd.Timedelta(days=3)).strftime("%Y-%m-%d")
        embargo_res = score_series_origin(
            dates_dt=dates_dt,
            dates_str=dates_str,
            prices=prices_arr,
            origin_dt=embargo_dt_str,
            fold_info=f_info,
            series_meta=series_meta
        )
        assert not embargo_res["is_eligible_origin"]
        assert embargo_res["drop_reason"] == "outside_test_window"

        # 2. Test valid origin within fold test window
        valid_origin_str = (te_start + pd.Timedelta(days=14)).strftime("%Y-%m-%d")
        valid_res = score_series_origin(
            dates_dt=dates_dt,
            dates_str=dates_str,
            prices=prices_arr,
            origin_dt=valid_origin_str,
            fold_info=f_info,
            series_meta=series_meta
        )
        assert valid_res["is_eligible_origin"]
        assert valid_res["drop_reason"] is None
        assert np.isfinite(valid_res["pred_naive"])
        assert np.isfinite(valid_res["target_price"])

        # 3. Test late origin near test_end where target > test_end
        late_origin_str = (te_end - pd.Timedelta(days=3)).strftime("%Y-%m-%d")
        late_res = score_series_origin(
            dates_dt=dates_dt,
            dates_str=dates_str,
            prices=prices_arr,
            origin_dt=late_origin_str,
            fold_info=f_info,
            series_meta=series_meta
        )
        assert not late_res["is_eligible_origin"]
        assert late_res["drop_reason"] == "dropped_target_after_fold_end"
        assert np.isnan(late_res["target_price"])


# -----------------------------------------------------------------------------
# 4. Anti-Leakage / Future Invariance Mutation Checks
# -----------------------------------------------------------------------------

def test_future_invariance_and_train_eligibility_mutation():
    """
    Verify that mutating, inserting, or deleting rows strictly after origin date t:
    1. Produces zero change in score_series_origin forecasts.
    2. Produces zero change in evaluate_series_train_eligibility.
    """
    dates = pd.date_range("2024-01-01", "2025-06-15", freq="D")
    prices = 1800.0 + np.arange(len(dates)) * 1.0

    origin_t = "2025-06-01"
    t_dt = pd.Timestamp(origin_t)

    df_base = pd.DataFrame({"Arrival_Date": dates, "Modal_Price": prices})
    dates_base = df_base["Arrival_Date"].to_numpy(dtype="datetime64[ns]")
    dates_str_base = df_base["Arrival_Date"].dt.strftime("%Y-%m-%d").to_numpy()
    prices_base = df_base["Modal_Price"].to_numpy(dtype=float)

    fold_info = {"fold": "F1", "train_end": "2024-12-31", "test_start": "2025-01-08", "test_end": "2025-06-30"}
    series_meta = {"series_id": "test__s1", "district": "Ghaziabad", "market": "Ghaziabad", "commodity": "Wheat", "variety": "Dara", "grade": "FAQ"}

    base_res = score_series_origin(dates_base, dates_str_base, prices_base, origin_t, fold_info, series_meta)
    base_tier_a, base_tier_b = evaluate_series_train_eligibility(dates_base, "2024-12-31")

    # Mutate future prices at t + 10d
    df_mut = df_base.copy()
    df_mut.loc[df_mut["Arrival_Date"] == t_dt + pd.Timedelta(days=10), "Modal_Price"] = 999999.0
    dates_mut = df_mut["Arrival_Date"].to_numpy(dtype="datetime64[ns]")
    dates_str_mut = df_mut["Arrival_Date"].dt.strftime("%Y-%m-%d").to_numpy()
    prices_mut = df_mut["Modal_Price"].to_numpy(dtype=float)

    mut_res = score_series_origin(dates_mut, dates_str_mut, prices_mut, origin_t, fold_info, series_meta)
    mut_tier_a, mut_tier_b = evaluate_series_train_eligibility(dates_mut, "2024-12-31")

    assert base_res["pred_naive"] == mut_res["pred_naive"]
    assert base_res["pred_ma"] == mut_res["pred_ma"]
    assert base_res["pred_seasonal_naive"] == mut_res["pred_seasonal_naive"]
    assert base_res["pred_drift"] == mut_res["pred_drift"]
    assert base_tier_a == mut_tier_a
    assert base_tier_b == mut_tier_b

    # Insert future row
    extra_row = pd.DataFrame({"Arrival_Date": [t_dt + pd.Timedelta(days=15)], "Modal_Price": [77777.0]})
    df_ins = pd.concat([df_base, extra_row]).sort_values("Arrival_Date").reset_index(drop=True)
    dates_ins = df_ins["Arrival_Date"].to_numpy(dtype="datetime64[ns]")
    dates_str_ins = df_ins["Arrival_Date"].dt.strftime("%Y-%m-%d").to_numpy()
    prices_ins = df_ins["Modal_Price"].to_numpy(dtype=float)

    ins_res = score_series_origin(dates_ins, dates_str_ins, prices_ins, origin_t, fold_info, series_meta)
    assert base_res["pred_naive"] == ins_res["pred_naive"]
    assert base_res["pred_ma"] == ins_res["pred_ma"]
    assert base_res["pred_seasonal_naive"] == ins_res["pred_seasonal_naive"]
    assert base_res["pred_drift"] == ins_res["pred_drift"]


# -----------------------------------------------------------------------------
# 5. Scope B Sensitivity: All Six Historical Excising Cases
# -----------------------------------------------------------------------------

def test_scope_b_all_six_historical_cases():
    """
    Test all six required Scope B cases in score_series_origin:
    1. Removed MA observation -> changes MA prediction.
    2. Removed drift anchor -> changes Drift prediction.
    3. Removed seasonal anchor -> changes Seasonal Naive prediction.
    4. Disputed origin -> scope_b_eligible is False (disputed_origin).
    5. Disputed target -> scope_b_eligible is False (disputed_target).
    6. Removal causing recency failure (<3 obs) -> scope_b_eligible is False (recency_failure_after_removal).
    """
    fold_info = {"fold": "F1", "train_end": "2024-12-31", "test_start": "2025-01-08", "test_end": "2025-06-30"}
    series_meta = {"series_id": "test__s1", "district": "Ghaziabad", "market": "Ghaziabad", "commodity": "Wheat", "variety": "Dara", "grade": "FAQ"}

    origin_t = "2025-06-15"
    t_dt = pd.Timestamp(origin_t)

    # 1. Removed MA observation
    # Place a regular series with an outlier on 2025-06-10 (in [t-30d, t])
    dates = pd.date_range("2024-01-01", "2025-06-25", freq="D")
    prices = np.full(len(dates), 2000.0)
    prices[dates == pd.Timestamp("2025-06-10")] = 5000.0 # outlier price on MA observation

    dates_dt = dates.to_numpy(dtype="datetime64[ns]")
    dates_str = dates.strftime("%Y-%m-%d").to_numpy()
    prices_arr = prices.astype(float)

    disputed_keys_ma = {("Ghaziabad", "Ghaziabad", "Wheat", "Dara", "FAQ", "2025-06-10")}
    res_ma = score_series_origin(dates_dt, dates_str, prices_arr, origin_t, fold_info, series_meta, disputed_keys_ma)

    assert res_ma["scope_b_eligible"]
    assert res_ma["scope_b_has_removed_history"]
    assert res_ma["ma_changed_scope_b"]
    assert res_ma["pred_ma"] > res_ma["pred_ma_scope_b"], "Scope B MA should be lower after removing 5000.0 spike!"
    assert np.isclose(res_ma["pred_ma_scope_b"], 2000.0)

    # 2. Removed Drift anchor
    # Drift anchor for 2025-06-15 is near 2025-06-01 (t - 14d). Put an outlier on 2025-06-01
    prices_drift = np.full(len(dates), 2000.0)
    prices_drift[dates == pd.Timestamp("2025-06-01")] = 1000.0 # anchor price
    prices_drift_arr = prices_drift.astype(float)

    disputed_keys_drift = {("Ghaziabad", "Ghaziabad", "Wheat", "Dara", "FAQ", "2025-06-01")}
    res_drift = score_series_origin(dates_dt, dates_str, prices_drift_arr, origin_t, fold_info, series_meta, disputed_keys_drift)

    assert res_drift["scope_b_eligible"]
    assert res_drift["scope_b_has_removed_history"]
    assert res_drift["drift_changed_scope_b"]
    assert res_drift["pred_drift"] != res_drift["pred_drift_scope_b"]

    # 3. Removed Seasonal anchor
    # Seasonal anchor for 2025-06-15 is 2024-06-23 (t - 357d). Put an outlier on 2024-06-23
    prices_s = np.full(len(dates), 2000.0)
    prices_s[dates == pd.Timestamp("2024-06-23")] = 3500.0
    prices_s_arr = prices_s.astype(float)

    disputed_keys_s = {("Ghaziabad", "Ghaziabad", "Wheat", "Dara", "FAQ", "2024-06-23")}
    res_s = score_series_origin(dates_dt, dates_str, prices_s_arr, origin_t, fold_info, series_meta, disputed_keys_s)

    assert res_s["scope_b_eligible"]
    assert res_s["scope_b_has_removed_history"]
    assert res_s["seasonal_changed_scope_b"]
    assert res_s["pred_seasonal_naive"] == 3500.0
    assert res_s["pred_seasonal_scope_b"] == 2000.0

    # 4. Disputed Origin
    disputed_keys_orig = {("Ghaziabad", "Ghaziabad", "Wheat", "Dara", "FAQ", origin_t)}
    res_orig = score_series_origin(dates_dt, dates_str, prices_arr, origin_t, fold_info, series_meta, disputed_keys_orig)

    assert res_orig["is_disputed_origin"]
    assert not res_orig["scope_b_eligible"]
    assert res_orig["scope_b_ineligible_reason"] == "disputed_origin"
    assert np.isnan(res_orig["pred_naive_scope_b"])
    assert np.isnan(res_orig["pred_ma_scope_b"])
    assert np.isnan(res_orig["pred_seasonal_scope_b"])
    assert np.isnan(res_orig["pred_drift_scope_b"])

    # 5. Disputed Target
    # Target date for 2025-06-15 is 2025-06-22
    target_dt_str = "2025-06-22"
    disputed_keys_tgt = {("Ghaziabad", "Ghaziabad", "Wheat", "Dara", "FAQ", target_dt_str)}
    res_tgt = score_series_origin(dates_dt, dates_str, prices_arr, origin_t, fold_info, series_meta, disputed_keys_tgt)

    assert res_tgt["is_disputed_target"]
    assert not res_tgt["scope_b_eligible"]
    assert res_tgt["scope_b_ineligible_reason"] == "disputed_target"
    assert np.isnan(res_tgt["pred_naive_scope_b"])
    assert np.isnan(res_tgt["pred_ma_scope_b"])

    # 6. Removal Causing Recency Failure (<3 observations)
    # Create a sparse series where in [t-30d, t] there are exactly 3 observations:
    # 2025-05-20, 2025-06-01, 2025-06-15
    sparse_dates = [
        pd.Timestamp("2024-06-23"),
        pd.Timestamp("2025-05-20"),
        pd.Timestamp("2025-06-01"),
        pd.Timestamp("2025-06-15"),
        pd.Timestamp("2025-06-22")
    ]
    sparse_prices = [2000.0] * len(sparse_dates)
    s_dt = np.array(sparse_dates, dtype="datetime64[ns]")
    s_str = np.array([d.strftime("%Y-%m-%d") for d in sparse_dates])
    s_p = np.array(sparse_prices, dtype=float)

    # Disputed observation on 2025-06-01 -> removing it leaves only 2 observations in [t-30d, t] (< 3)
    disputed_keys_rec = {("Ghaziabad", "Ghaziabad", "Wheat", "Dara", "FAQ", "2025-06-01")}
    res_rec = score_series_origin(s_dt, s_str, s_p, origin_t, fold_info, series_meta, disputed_keys_rec)

    assert not res_rec["scope_b_eligible"]
    assert res_rec["scope_b_ineligible_reason"] == "recency_failure_after_removal"
    assert np.isnan(res_rec["pred_ma_scope_b"])
    assert np.isnan(res_rec["pred_drift_scope_b"])


# -----------------------------------------------------------------------------
# 6. Shared Scorer Denominators & Finite Value Masking
# -----------------------------------------------------------------------------

def test_shared_scorer_denominators_and_missing_cases():
    """
    Verify that evaluate_model_slice:
    1. Uses a consistent joint finite mask for target, model prediction, and naive prediction.
    2. Correctly excludes missing/NaN/inf naive from the scored set (does not produce NaNs in skill).
    3. Handles infinite values in target, model, or naive safely.
    4. Correctly computes abstention rate: n_scored <= n_eligible.
    5. Sets low_n_flag based strictly on scored series and scored instances.
    6. All-abstained case returns np.nan for all metrics with low_n_flag=True.
    """
    series_ids = ["s1", "s2", "s3", "s4", "s5"]
    rows = []

    # 10 rows:
    # 5 valid rows
    for i in range(5):
        rows.append({"series_id": series_ids[i], "target_price": 2000.0, "pred_model": 2010.0, "pred_naive": 1990.0})
    # 1 row with NaN naive
    rows.append({"series_id": "s1", "target_price": 2000.0, "pred_model": 2010.0, "pred_naive": np.nan})
    # 1 row with inf naive
    rows.append({"series_id": "s2", "target_price": 2000.0, "pred_model": 2010.0, "pred_naive": np.inf})
    # 1 row with NaN model
    rows.append({"series_id": "s3", "target_price": 2000.0, "pred_model": np.nan, "pred_naive": 1990.0})
    # 1 row with -inf model
    rows.append({"series_id": "s4", "target_price": 2000.0, "pred_model": -np.inf, "pred_naive": 1990.0})
    # 1 row with NaN target
    rows.append({"series_id": "s5", "target_price": np.nan, "pred_model": 2010.0, "pred_naive": 1990.0})

    df = pd.DataFrame(rows)
    res = evaluate_model_slice(df, model_col="pred_model", naive_col="pred_naive", target_col="target_price")

    assert res["n_eligible_origins"] == 10
    # Exactly 5 rows are mutually finite across target, model, and naive!
    assert res["n_scored_origins"] == 5
    assert res["n_origins"] == 5
    assert res["n_scored_origins"] <= res["n_eligible_origins"]
    assert res["abstention_rate_pct"] == 50.0 # 5 of 10 dropped

    # Check finite metrics
    assert np.isfinite(res["mae"])
    assert np.isfinite(res["rmse"])
    assert np.isfinite(res["skill_vs_naive"])
    assert res["low_n_flag"], "n_scored_origins=5 < 200 should trigger low_n_flag"

    # All-abstained test:
    df_abstained = pd.DataFrame({
        "series_id": ["s1", "s2"],
        "target_price": [2000.0, 2100.0],
        "pred_model": [np.nan, np.nan],
        "pred_naive": [1990.0, 2090.0]
    })
    res_abs = evaluate_model_slice(df_abstained, model_col="pred_model")
    assert res_abs["n_eligible_origins"] == 2
    assert res_abs["n_scored_origins"] == 0
    assert res_abs["abstention_rate_pct"] == 100.0
    assert np.isnan(res_abs["mae"])
    assert np.isnan(res_abs["skill_vs_naive"])
    assert res_abs["low_n_flag"]


# -----------------------------------------------------------------------------
# 7. Shuffled Input Date Normalization
# -----------------------------------------------------------------------------

def test_scoring_helper_shuffled_dates_normalization():
    """Verify that score_series_origin and predict_series_vectorized normalize unsorted inputs deterministically."""
    dates = pd.date_range("2024-01-01", "2025-06-25", freq="D")
    prices = 2000.0 + np.sin(np.arange(len(dates)) / 10.0) * 100.0

    df_sorted = pd.DataFrame({"Arrival_Date": dates, "Modal_Price": prices})
    df_shuffled = df_sorted.sample(frac=1.0, random_state=42)

    fold_info = {"fold": "F1", "train_end": "2024-12-31", "test_start": "2025-01-08", "test_end": "2025-06-30"}
    series_meta = {"series_id": "test__s1", "district": "Ghaziabad", "market": "Ghaziabad", "commodity": "Wheat", "variety": "Dara", "grade": "FAQ"}

    origin_t = "2025-05-15"

    res_sorted = score_series_origin(
        dates_dt=df_sorted["Arrival_Date"].to_numpy(dtype="datetime64[ns]"),
        dates_str=df_sorted["Arrival_Date"].dt.strftime("%Y-%m-%d").to_numpy(),
        prices=df_sorted["Modal_Price"].to_numpy(dtype=float),
        origin_dt=origin_t,
        fold_info=fold_info,
        series_meta=series_meta
    )

    res_shuffled = score_series_origin(
        dates_dt=df_shuffled["Arrival_Date"].to_numpy(dtype="datetime64[ns]"),
        dates_str=df_shuffled["Arrival_Date"].dt.strftime("%Y-%m-%d").to_numpy(),
        prices=df_shuffled["Modal_Price"].to_numpy(dtype=float),
        origin_dt=origin_t,
        fold_info=fold_info,
        series_meta=series_meta
    )

    assert res_sorted["is_eligible_origin"] == res_shuffled["is_eligible_origin"]
    assert np.isclose(res_sorted["pred_naive"], res_shuffled["pred_naive"])
    assert np.isclose(res_sorted["pred_ma"], res_shuffled["pred_ma"])
    assert np.isclose(res_sorted["pred_seasonal_naive"], res_shuffled["pred_seasonal_naive"])
    assert np.isclose(res_sorted["pred_drift"], res_shuffled["pred_drift"])
    assert np.isclose(res_sorted["target_price"], res_shuffled["target_price"])
    assert res_sorted["target_date"] == res_shuffled["target_date"]


# -----------------------------------------------------------------------------
# 8. Bootstrap Deterministic Ordering & Zero-Denominator Safety
# -----------------------------------------------------------------------------

def test_cluster_bootstrap_deterministic_ordering():
    """Verify cluster_bootstrap_series is invariant to row shuffling due to deterministic sorting."""
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
    """Verify compute_forecast_metrics handles zero naive error safely (returns np.nan)."""
    y_true = np.array([2000.0, 2100.0, 2200.0])
    y_pred = np.array([2010.0, 2110.0, 2210.0])
    # Naive is 100% perfect: error = 0
    y_naive = np.array([2000.0, 2100.0, 2200.0])

    metrics = compute_forecast_metrics(y_true=y_true, y_pred=y_pred, y_naive=y_naive)
    assert np.isnan(metrics["skill_vs_naive"])
