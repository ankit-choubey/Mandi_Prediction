"""
test_forecast_features.py — Acceptance Test Suite for Shared Causal Feature Builder

Tests:
1. Exact calendar lag construction (unobserved calendar dates stay NaN).
2. Row shuffle invariance.
3. Preceding rolling window boundaries ([t-W, t-1] strictly exclusive of t).
4. Missing sample standard deviation burn-in (ddof=1, count < 2 returns NaN).
5. Future observation insertion/deletion leaves historical features unchanged.
6. Target mutations do not leak into feature vectors.
7. Exact equivalence between batch features and single-origin inference features.
8. Tier A and Tier B series training eligibility and origin recency.
9. Target extraction, nearest-in-window, earlier tie-break, fold boundary, and training maturity.
10. Schema and deterministic code hash validation.
"""

import math
import random
from datetime import date, datetime, timedelta
import numpy as np
import pandas as pd
import pytest

from src.forecast_features import (
    CALENDAR_LAGS,
    FEATURE_COLUMNS,
    GRADE_NOT_PROVIDED,
    ROLLING_WINDOWS_DAYS,
    ForecastFeatureBuilder,
    SeriesIdentity,
    get_code_version_hash,
    get_feature_schema,
)


class TestForecastFeatureBuilder:
    @pytest.fixture
    def builder(self):
        return ForecastFeatureBuilder()

    @pytest.fixture
    def sample_series(self):
        return SeriesIdentity(
            district="Kanpur",
            market="Kanpur(Grain)",
            commodity="Potato",
            variety="Other",
            grade="FAQ",
        )

    def test_schema_and_code_hash(self):
        schema = get_feature_schema()
        assert len(schema) == 21
        names = [f["name"] for f in schema]
        assert names == FEATURE_COLUMNS
        for feat in schema:
            assert "name" in feat
            assert "dtype" in feat
            assert "unit" in feat
            assert "description" in feat
            assert "missing_handling" in feat

        code_hash = get_code_version_hash()
        assert isinstance(code_hash, str)
        assert len(code_hash) == 64

    def test_exact_calendar_lags_and_missingness(self, builder, sample_series):
        # Create history with specific calendar gaps:
        # t = 2026-11-10
        # t-1 = 2026-11-09: observed 500
        # t-3 = 2026-11-07: unobserved (missing)
        # t-7 = 2026-11-03: observed 480
        # t-14 = 2026-10-27: unobserved
        # t-28 = 2026-10-13: observed 450
        t = date(2026, 11, 10)
        history = {
            t: 520.0,
            date(2026, 11, 9): 500.0,
            date(2026, 11, 3): 480.0,
            date(2026, 10, 13): 450.0,
        }

        feat = builder.compute_origin_features(history, t, series=sample_series)

        assert feat["current_price"] == 520.0
        assert feat["price_lag_1"] == 500.0
        assert np.isnan(feat["price_lag_3"])  # Missing stays NaN!
        assert feat["price_lag_7"] == 480.0
        assert np.isnan(feat["price_lag_14"])  # Missing stays NaN!
        assert feat["price_lag_28"] == 450.0
        assert feat["last_observation_age_days"] == 0.0

    def test_rolling_window_preceding_exclusive_and_burn_in(self, builder, sample_series):
        # t = 2026-11-10
        # Preceding 7d window is [2026-11-03, 2026-11-09]
        # Current price P_t = 1000 should NOT be included in rolling statistics!
        t = date(2026, 11, 10)

        # Case 1: 0 observations in [t-7, t-1]
        hist_empty = {t: 1000.0}
        f_empty = builder.compute_origin_features(hist_empty, t, series=sample_series)
        assert f_empty["rolling_count_7d"] == 0
        assert np.isnan(f_empty["rolling_mean_7d"])
        assert np.isnan(f_empty["rolling_std_7d"])

        # Case 2: 1 observation in [t-7, t-1] -> mean defined, std is NaN (burn-in check!)
        hist_one = {
            t: 1000.0,
            date(2026, 11, 8): 600.0,
        }
        f_one = builder.compute_origin_features(hist_one, t, series=sample_series)
        assert f_one["rolling_count_7d"] == 1
        assert f_one["rolling_mean_7d"] == 600.0
        assert np.isnan(f_one["rolling_std_7d"])  # count < 2 burn-in!

        # Case 3: 2 observations in [t-7, t-1] -> mean and sample std defined
        hist_two = {
            t: 1000.0,
            date(2026, 11, 8): 600.0,
            date(2026, 11, 6): 400.0,
        }
        f_two = builder.compute_origin_features(hist_two, t, series=sample_series)
        assert f_two["rolling_count_7d"] == 2
        assert f_two["rolling_mean_7d"] == 500.0
        # std of [600, 400] with ddof=1 is sqrt((100^2 + 100^2)/1) = sqrt(20000) ~ 141.421356
        assert abs(f_two["rolling_std_7d"] - np.std([600.0, 400.0], ddof=1)) < 1e-6

    def test_future_isolation_and_no_leakage(self, builder, sample_series):
        # Base history up to t
        t = date(2026, 11, 10)
        base_history = {
            date(2026, 11, 9): 500.0,
            date(2026, 11, 8): 510.0,
            date(2026, 11, 3): 480.0,
        }

        f_base = builder.compute_origin_features(base_history, t, series=sample_series)

        # Mutated history with future observations (at t+1, t+7, t+14)
        mut_history = dict(base_history)
        mut_history[date(2026, 11, 11)] = 9999.0
        mut_history[date(2026, 11, 17)] = 8888.0

        f_mut = builder.compute_origin_features(mut_history, t, series=sample_series)

        # Features at t must be strictly identical!
        for col in FEATURE_COLUMNS:
            v_base = f_base[col]
            v_mut = f_mut[col]
            if np.isnan(v_base):
                assert np.isnan(v_mut), f"Column {col} leaked future NaN mismatch!"
            else:
                assert v_base == v_mut, f"Column {col} changed under future insertion!"

    def test_row_shuffle_invariance(self, builder):
        # Generate random records for 2 series over 60 days
        rng = random.Random(42)
        records = []
        start_d = date(2026, 1, 1)

        for s_dist in ("Kanpur", "Ghaziabad"):
            for day_i in range(60):
                cur_d = start_d + timedelta(days=day_i)
                if rng.random() > 0.3:  # 70% present
                    records.append({
                        "District": s_dist,
                        "Market": f"{s_dist} Market",
                        "Commodity": "Potato",
                        "Variety": "Other",
                        "Grade": "FAQ",
                        "Arrival_Date": cur_d.isoformat(),
                        "Modal_Price": 500.0 + day_i * 2 + rng.uniform(-10, 10),
                    })

        df1 = builder.compute_batch_features(records)

        # Shuffle records randomly
        shuffled_records = list(records)
        rng.shuffle(shuffled_records)
        df2 = builder.compute_batch_features(shuffled_records)

        # Both resulting DataFrames must have identical rows when sorted by series_id & origin_date
        df1_sorted = df1.sort_values(by=["series_id", "origin_date"]).reset_index(drop=True)
        df2_sorted = df2.sort_values(by=["series_id", "origin_date"]).reset_index(drop=True)

        pd.testing.assert_frame_equal(df1_sorted, df2_sorted)

    def test_batch_vs_inference_exact_equality(self, builder, sample_series):
        # Generate 45 days of trade data
        start_d = date(2026, 8, 1)
        records = []
        clean_hist = {}
        for i in range(45):
            d = start_d + timedelta(days=i)
            # simulate 5-day trading weeks (skip Sundays)
            if d.weekday() != 6:
                p = 1000.0 + i * 5.0
                clean_hist[d] = p
                records.append({
                    "District": sample_series.district,
                    "Market": sample_series.market,
                    "Commodity": sample_series.commodity,
                    "Variety": sample_series.variety,
                    "Grade": sample_series.grade,
                    "Arrival_Date": d.isoformat(),
                    "Modal_Price": p,
                })

        # Batch features
        batch_df = builder.compute_batch_features(records)

        # For every date in batch, compute single-origin inference feature
        for _, row in batch_df.iterrows():
            t = date.fromisoformat(row["origin_date"])
            single_feat = builder.compute_origin_features(clean_hist, t, series=sample_series)

            for col in FEATURE_COLUMNS:
                b_val = row[col]
                s_val = single_feat[col]
                if np.isnan(b_val):
                    assert np.isnan(s_val), f"Mismatch at {t} col {col}: batch={b_val}, single={s_val}"
                else:
                    assert abs(b_val - s_val) < 1e-9, f"Mismatch at {t} col {col}: batch={b_val}, single={s_val}"

    def test_target_extraction_and_earlier_tie_break(self, builder):
        t = date(2026, 9, 1)

        # Case 1: Exact t+7 is observed -> selects t+7
        hist1 = {
            date(2026, 9, 8): 1000.0,  # t+7
            date(2026, 9, 7): 950.0,   # t+6
            date(2026, 9, 9): 1050.0,  # t+8
        }
        res1 = builder.compute_target(hist1, t, horizon_days=7)
        assert res1.target_status == "VALID_TARGET"
        assert res1.target_date == "2026-09-08"
        assert res1.target_price == 1000.0
        assert res1.offset_from_h7 == 0

        # Case 2: Exact t+7 unobserved, both t+6 and t+8 observed -> tie earlier selects t+6!
        hist2 = {
            date(2026, 9, 7): 950.0,   # t+6
            date(2026, 9, 9): 1050.0,  # t+8
        }
        res2 = builder.compute_target(hist2, t, horizon_days=7)
        assert res2.target_status == "VALID_TARGET"
        assert res2.target_date == "2026-09-07"  # EARLIER tie-break!
        assert res2.target_price == 950.0
        assert res2.offset_from_h7 == -1

        # Case 3: Only t+8 observed
        hist3 = {
            date(2026, 9, 9): 1050.0,  # t+8
        }
        res3 = builder.compute_target(hist3, t, horizon_days=7)
        assert res3.target_status == "VALID_TARGET"
        assert res3.target_date == "2026-09-09"
        assert res3.target_price == 1050.0
        assert res3.offset_from_h7 == 1

        # Case 4: No target in window [t+6, t+8]
        hist4 = {
            date(2026, 9, 5): 800.0,
            date(2026, 9, 10): 1100.0,
        }
        res4 = builder.compute_target(hist4, t, horizon_days=7)
        assert res4.target_status == "NO_TARGET_IN_WINDOW"
        assert res4.target_date is None
        assert res4.target_price is None

        # Case 5: Target exceeds fold_end
        res5 = builder.compute_target(hist1, t, horizon_days=7, fold_end=date(2026, 9, 7))
        assert res5.target_status == "TARGET_EXCEEDS_FOLD_END"
        assert res5.target_price is None

        # Case 6: Training cutoff maturity check
        res6_matured = builder.compute_target(hist1, t, horizon_days=7, train_cutoff=date(2026, 9, 8))
        assert res6_matured.is_matured_before_cutoff is True

        res6_unmatured = builder.compute_target(hist1, t, horizon_days=7, train_cutoff=date(2026, 9, 7))
        assert res6_unmatured.is_matured_before_cutoff is False

    def test_series_train_eligibility_tier_a_tier_b(self, builder):
        # 100 observations over 200 calendar days -> coverage = 100/200 = 0.50
        dates_100 = [date(2024, 1, 1) + timedelta(days=i * 2) for i in range(100)]
        cutoff = date(2024, 12, 31)

        t_a, t_b, stats = builder.evaluate_series_train_eligibility(dates_100, cutoff)
        # N=100 >= 60, coverage=0.5 >= 0.30 -> Tier A = True
        # N=100 < 120 -> Tier B = False
        assert t_a is True
        assert t_b is False
        assert stats["n_train"] == 100
        assert stats["coverage"] >= 0.30

        # Add 30 more observations -> N=130 >= 120 -> Tier B = True
        dates_130 = [date(2024, 1, 1) + timedelta(days=i * 2) for i in range(130)]
        t_a_130, t_b_130, stats_130 = builder.evaluate_series_train_eligibility(dates_130, cutoff)
        assert t_a_130 is True
        assert t_b_130 is True

        # Test low coverage (< 0.30)
        # 70 observations over 300 days -> coverage = 70/300 = 0.233 < 0.30
        dates_low_cov = [date(2024, 1, 1) + timedelta(days=i * 4) for i in range(70)]
        t_a_low, t_b_low, stats_low = builder.evaluate_series_train_eligibility(dates_low_cov, cutoff)
        assert t_a_low is False
        assert t_b_low is False
        assert stats_low["coverage"] < 0.30

    def test_origin_recency_check(self, builder):
        t = date(2026, 5, 1)
        # 3 observations in [t-30, t]: e.g. t-5, t-15, t-25
        hist_rec = {
            date(2026, 4, 26): 500.0,
            date(2026, 4, 16): 510.0,
            date(2026, 4, 6): 520.0,
        }
        assert builder.evaluate_origin_recency(hist_rec, t, window_days=30, min_recency_obs=3) is True

        # Only 2 observations in [t-30, t]
        hist_low = {
            date(2026, 4, 26): 500.0,
            date(2026, 4, 16): 510.0,
            date(2026, 3, 1): 520.0,  # outside 30-day window!
        }
        assert builder.evaluate_origin_recency(hist_low, t, window_days=30, min_recency_obs=3) is False
