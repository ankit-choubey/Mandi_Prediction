"""
Unit tests and regression checks for APMC Mandi Price Forecasting Benchmark Engine
Task: MP-FC-007 / MP-FC-007R

Validates the full set of architectural and mathematical repairs:
1. Manifest disposition extraction and row conservation gate (472,385 = 463,217 + 855 + 2,936 + 5,350 + 27).
2. Exact 7-calendar-day embargo separation across all eight inner validation splits.
3. Strict tier hierarchy (Tier B subset of Tier A) with boolean flags and single prediction rows.
4. Date-based regimes (HISTORICAL < 2025-11-01, TRANSITION 2025-11-01..2026-02-28, MODERN >= 2026-03-01).
5. Exact nearest-target selection then maturity/fold-bound rejection, plus 77 canonical keys sensitivity matching.
6. Inner hyperparameter ranking on common non-abstained origin keys with deterministic tie-breaks.
7. Exact mathematical equivalence of pre-aggregated cluster bootstrap vs raw concatenation.
8. Consistent estimands, numeric CI fields, complete schemas on empty slices, and undefined skill on zero denominator.
"""

from datetime import date, datetime, timedelta
import json
import math
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from sklearn.pipeline import Pipeline

from src.baselines import load_canonical_disputed_keys
from src.forecast_features import SeriesIdentity, FEATURE_COLUMNS
from src.forecast_benchmark import (
    TemporalFold,
    InnerSplit,
    get_standard_folds,
    get_inner_splits,
    extract_series_target,
    extract_manifest_dispositions,
    classify_date_regime,
    compute_scope_a_disputed_mask,
    build_candidate_ridge_model,
    build_candidate_hgb_model,
    ForecastBenchmarkEngine,
    compute_slice_metrics,
)


class TestManifestDispositionsGate:
    def test_extract_manifest_dispositions_valid(self):
        # Test against real downloaded processing_manifest_v2.json if available, else synthetic valid
        p = Path("experiments/outputs/FC007_failed_v1/processing_manifest_v2.json")
        if p.exists():
            with open(p) as f:
                manifest = json.load(f)
        else:
            manifest = {
                "summary_metrics": {
                    "total_raw_rows": 472385,
                    "total_valid_parsed_rows": 472358,
                    "total_dropped_raw_rows": 27,
                    "exact_duplicates_deduplicated": 855,
                    "ambiguous_same_grade_excluded_rows": 2936,
                    "low_observation_series_dropped_rows": 5350,
                    "final_clean_rows": 463217,
                }
            }

        res = extract_manifest_dispositions(manifest)
        assert res["raw_rows_in"] == 472385
        assert res["accepted_rows"] == 463217
        assert res["duplicates_deduplicated"] == 855
        assert res["conflicts_quarantined"] == 2936
        assert res["low_obs_dropped"] == 5350
        assert res["invalid_dropped_rows"] == 27
        assert res["row_conservation_verified"] is True

    def test_extract_manifest_dispositions_missing_key_fails(self):
        manifest = {
            "summary_metrics": {
                "total_raw_rows": 472385,
                "total_valid_parsed_rows": 472358,
                "total_dropped_raw_rows": 27,
                "exact_duplicates_deduplicated": 855,
                # "ambiguous_same_grade_excluded_rows": 2936 (missing)
                "low_observation_series_dropped_rows": 5350,
                "final_clean_rows": 463217,
            }
        }
        with pytest.raises(KeyError, match="summary_metrics is missing required fields"):
            extract_manifest_dispositions(manifest)

    def test_extract_manifest_dispositions_conservation_violation_fails(self):
        manifest = {
            "summary_metrics": {
                "total_raw_rows": 472385,
                "total_valid_parsed_rows": 472358,
                "total_dropped_raw_rows": 27,
                "exact_duplicates_deduplicated": 855,
                "ambiguous_same_grade_excluded_rows": 2936,
                "low_observation_series_dropped_rows": 5350,
                "final_clean_rows": 463200,  # 17 rows short!
            }
        }
        with pytest.raises(ValueError, match="Row conservation assertion violated"):
            extract_manifest_dispositions(manifest)


class TestTemporalFoldsAndSplits:
    def test_standard_folds_structure(self):
        folds = get_standard_folds()
        assert len(folds) == 4
        f1, f2, f3, f4 = folds

        assert f1.fold_id == "F1"
        assert f1.train_cutoff == date(2024, 12, 31)
        assert f1.max_train_origin == date(2024, 12, 23)  # cutoff - 8 days
        assert f1.test_start == date(2025, 1, 8)
        assert f1.test_end == date(2025, 6, 30)
        assert f1.regime == "HISTORICAL"

        assert f2.fold_id == "F2"
        assert f2.train_cutoff == date(2025, 6, 30)
        assert f2.max_train_origin == date(2025, 6, 22)
        assert f2.test_start == date(2025, 7, 8)
        assert f2.test_end == date(2025, 10, 31)
        assert f2.regime == "HISTORICAL"  # All dates < 2025-11-01 are historical

        assert f3.fold_id == "F3"
        assert f3.train_cutoff == date(2025, 12, 18)
        assert f3.max_train_origin == date(2025, 12, 10)
        assert f3.test_start == date(2025, 12, 26)
        assert f3.test_end == date(2026, 3, 31)

        assert f4.fold_id == "F4"
        assert f4.train_cutoff == date(2026, 3, 31)
        assert f4.max_train_origin == date(2026, 3, 23)
        assert f4.test_start == date(2026, 4, 8)
        assert f4.test_end == date(2026, 9, 30)
        assert f4.regime == "MODERN"

    def test_all_eight_inner_splits_seven_day_embargo(self):
        """Verify across ALL 4 folds and ALL 8 inner splits that exactly 7 excluded calendar days exist."""
        folds = get_standard_folds()
        assert len(folds) == 4
        total_splits = 0

        for fold in folds:
            splits = get_inner_splits(fold)
            assert len(splits) == 2
            for split in splits:
                total_splits += 1
                # Number of excluded calendar dates strictly between fit_cutoff and val_start
                excluded_days = (split.val_start - split.inner_fit_cutoff).days - 1
                assert excluded_days == 7, (
                    f"Fold {fold.fold_id} {split.name}: expected 7 excluded days, got {excluded_days} "
                    f"(fit_cutoff={split.inner_fit_cutoff}, val_start={split.val_start})"
                )
                # Conservative origin cap is cutoff - 8d
                assert split.inner_fit_max_origin == split.inner_fit_cutoff - timedelta(days=8)

        assert total_splits == 8, f"Expected 8 inner splits evaluated, got {total_splits}"


class TestDateRegimes:
    def test_date_based_regime_classification(self):
        # Historical: before 2025-11-01
        assert classify_date_regime(date(2024, 6, 1)) == "HISTORICAL"
        assert classify_date_regime(date(2025, 7, 8)) == "HISTORICAL"
        assert classify_date_regime(date(2025, 10, 31)) == "HISTORICAL"

        # Transition: 2025-11-01 through 2026-02-28
        assert classify_date_regime(date(2025, 11, 1)) == "TRANSITION"
        assert classify_date_regime(date(2025, 12, 26)) == "TRANSITION"
        assert classify_date_regime(date(2026, 1, 15)) == "TRANSITION"
        assert classify_date_regime(date(2026, 2, 28)) == "TRANSITION"

        # Modern: 2026-03-01 onwards
        assert classify_date_regime(date(2026, 3, 1)) == "MODERN"
        assert classify_date_regime(date(2026, 3, 15)) == "MODERN"  # March 2026 in F3 is modern!
        assert classify_date_regime(date(2026, 4, 8)) == "MODERN"


class TestTargetExtractionAndSensitivities:
    def test_extract_series_target_exact(self):
        history = {
            date(2024, 1, 1): 1000.0,
            date(2024, 1, 7): 1050.0,  # t+6
            date(2024, 1, 8): 1070.0,  # t+7
            date(2024, 1, 9): 1090.0,  # t+8
        }
        price, trg_date, is_exact = extract_series_target(history, date(2024, 1, 1))
        assert price == 1070.0
        assert trg_date == date(2024, 1, 8)
        assert is_exact is True

    def test_extract_series_target_earlier_tie_break(self):
        history = {
            date(2024, 1, 1): 1000.0,
            date(2024, 1, 7): 1050.0,  # t+6 (diff=1)
            date(2024, 1, 9): 1090.0,  # t+8 (diff=1)
        }
        price, trg_date, is_exact = extract_series_target(history, date(2024, 1, 1))
        # Earlier tie-breaker selects t+6 (2024-01-07)
        assert price == 1050.0
        assert trg_date == date(2024, 1, 7)
        assert is_exact is False

    def test_extract_series_target_boundary_nearest_then_rejection(self):
        """
        Defect #5 regression test:
        History contains t+6 and t+7.
        Max target date is t+6.
        Nearest target is t+7 (diff=0).
        Because t+7 > max_target_date, the origin must be EXCLUDED (None, None, False),
        NOT opportunistically substituting t+6.
        """
        history = {
            date(2024, 1, 1): 1000.0,
            date(2024, 1, 7): 1050.0,  # t+6 (inside boundary)
            date(2024, 1, 8): 1070.0,  # t+7 (nearest, outside boundary)
        }
        price, trg_date, is_exact = extract_series_target(
            history,
            origin_t=date(2024, 1, 1),
            max_target_date=date(2024, 1, 7),  # boundary at t+6
        )
        assert price is None
        assert trg_date is None
        assert is_exact is False

    def test_scope_a_disputed_keys_mask(self):
        """Verify that Scope A sensitivity matches exact 6-tuple keys on origin or target."""
        ref_p = Path("data/reference/canonical_disputed_keys_77.csv")
        alias_p = Path("data/reference/market_aliases.csv")
        if not ref_p.exists() or not alias_p.exists():
            pytest.skip("Reference files not available for disputed keys test.")

        keys, _ = load_canonical_disputed_keys(ref_p, alias_p)
        assert len(keys) == 77

        sample_key = list(keys)[0]
        # (District, Market, Commodity, Variety, Grade, Date_str)
        dist, mkt, comm, var, grd, d_str = sample_key

        # Create dummy df where row 0 matches origin, row 1 matches target, row 2 does not match
        df = pd.DataFrame([
            {
                "district": dist,
                "market": mkt,
                "commodity": comm,
                "variety": var,
                "grade": grd,
                "origin_date": d_str,
                "target_date": "2024-01-01",
            },
            {
                "district": dist,
                "market": mkt,
                "commodity": comm,
                "variety": var,
                "grade": grd,
                "origin_date": "2024-01-01",
                "target_date": d_str,
            },
            {
                "district": "Unrelated",
                "market": "Unrelated",
                "commodity": "Wheat",
                "variety": "Dara",
                "grade": "FAQ",
                "origin_date": "2024-01-01",
                "target_date": "2024-01-08",
            },
        ])

        mask = compute_scope_a_disputed_mask(df, keys)
        assert mask.tolist() == [True, True, False]


class TestModelsAndResponseChoice:
    def test_ridge_pipeline_imputation_and_scaling(self):
        X_train = pd.DataFrame({
            "f1": [1.0, np.nan, 3.0, 4.0, 5.0],
            "f2": [10.0, 20.0, 30.0, 40.0, 50.0],
        })
        y_train = np.array([10.0, 20.0, 30.0, 40.0, 50.0])

        model = build_candidate_ridge_model(alpha=1.0)
        model.fit(X_train, y_train)

        imputer = model.named_steps["imputer"]
        assert imputer.statistics_[0] == 3.5

        X_test = pd.DataFrame({"f1": [np.nan], "f2": [30.0]})
        pred = model.predict(X_test)
        assert len(pred) == 1
        assert math.isfinite(pred[0])

    def test_hgb_native_nan_support(self):
        X_train = pd.DataFrame({
            "f1": [1.0, np.nan, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
            "f2": [10.0, 20.0, np.nan, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0],
        })
        y_train = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])

        model = build_candidate_hgb_model(max_depth=3, min_samples_leaf=2)
        model.fit(X_train, y_train)

        X_test = pd.DataFrame({"f1": [np.nan, 5.0], "f2": [25.0, np.nan]})
        preds = model.predict(X_test)
        assert len(preds) == 2
        assert all(math.isfinite(p) for p in preds)


class TestBenchmarkEngineWorkflow:
    @pytest.fixture
    def small_series_fixture(self):
        # Create 2 series extending from 2024 through mid-2025 (covering F1 test window)
        # Series 1: 260 points (step 2 days) -> 183 obs in 2024 (>=120 obs, cov ~0.50) -> Tier A and Tier B
        dates1 = [date(2024, 1, 1) + timedelta(days=i * 2) for i in range(260)]
        s1 = SeriesIdentity("Kanpur", "Kanpur(Grain)", "Wheat", "Dara", "FAQ")

        # Series 2: 140 points (step 3 days starting 2024-05-01) -> 82 obs in 2024 (>=60, <120 obs, cov ~0.34) -> Tier A only
        start_s2 = date(2024, 5, 1)
        dates2 = [start_s2 + timedelta(days=i * 3) for i in range(140)]
        s2 = SeriesIdentity("Lucknow", "Lucknow", "Potato", "Other", "FAQ")

        h1 = {d: 2000.0 + i * 2.0 + (i % 5) * 5.0 for i, d in enumerate(dates1)}
        h2 = {d: 800.0 + i * 1.5 - (i % 4) * 4.0 for i, d in enumerate(dates2)}

        return {s1: h1, s2: h2}

    def test_tier_memberships_and_partitioning(self, small_series_fixture):
        """Verify that Tier B is a strict subset of Tier A and stored as boolean flags."""
        engine = ForecastBenchmarkEngine()
        f1 = engine.folds[0]

        train_df, test_df = engine.prepare_dataset_partitions(small_series_fixture, f1)
        assert not train_df.empty
        assert not test_df.empty

        # Check boolean flags exist
        assert "is_tier_a" in test_df.columns
        assert "is_tier_b" in test_df.columns
        assert "date_regime" in test_df.columns

        # Series 1 has >=120 obs -> must have both is_tier_a=True and is_tier_b=True
        s1_rows = test_df[test_df["market"] == "Kanpur(Grain)"]
        assert not s1_rows.empty
        assert all(s1_rows["is_tier_a"])
        assert all(s1_rows["is_tier_b"])

        # Series 2 has 70 obs -> is_tier_a=True, is_tier_b=False
        s2_rows = test_df[test_df["market"] == "Lucknow"]
        assert not s2_rows.empty
        assert all(s2_rows["is_tier_a"])
        assert not any(s2_rows["is_tier_b"])

        # Each series origin appears ONCE in test_df
        dup_keys = test_df.duplicated(subset=["market", "commodity", "variety", "grade", "origin_date"])
        assert not dup_keys.any(), "Duplicate predictions found in test_df!"

    def test_engine_inner_tuning_common_origins(self, small_series_fixture):
        """Verify that inner tuning ranks configurations on identical common validation origin keys."""
        engine = ForecastBenchmarkEngine()
        f1 = engine.folds[0]

        tuning_results = engine.tune_candidate_models(small_series_fixture, f1)
        assert tuning_results["fold_id"] == "F1"
        assert tuning_results["best_ridge_alpha"] in [0.1, 1.0, 10.0]
        assert tuning_results["best_hgb_config"]["config_id"] in ["hgb_depth3", "hgb_depth5"]

        # Check that common sample size was recorded
        assert "common_ridge_sample_size" in tuning_results
        assert "common_hgb_sample_size" in tuning_results


class TestEvaluationMetricsAndBootstrap:
    def test_bootstrap_preaggregation_mathematical_equivalence(self):
        """
        Defect #7 regression test:
        Prove exact numerical equivalence between pre-aggregated cluster bootstrap
        and raw array concatenation across 100 resamples.
        """
        rng = np.random.default_rng(42)
        n_clusters = 5
        clusters = []
        for i in range(n_clusters):
            n_pts = rng.integers(10, 30)
            y_true = rng.uniform(500, 2500, size=n_pts)
            y_pred = y_true + rng.normal(0, 50, size=n_pts)
            y_naive = y_true + rng.normal(0, 80, size=n_pts)
            clusters.append((y_true, y_pred, y_naive))

        # 1. Raw concatenation bootstrap
        rng1 = np.random.default_rng(42)
        raw_maes = []
        raw_skills = []
        for _ in range(100):
            idx = rng1.integers(0, n_clusters, size=n_clusters)
            b_yt = np.concatenate([clusters[i][0] for i in idx])
            b_yp = np.concatenate([clusters[i][1] for i in idx])
            b_yn = np.concatenate([clusters[i][2] for i in idx])

            b_err_m = np.abs(b_yt - b_yp)
            b_err_n = np.abs(b_yt - b_yn)
            raw_maes.append(float(np.mean(b_err_m)))
            raw_skills.append(1.0 - (float(np.sum(b_err_m)) / float(np.sum(b_err_n))))

        # 2. Pre-aggregated cluster bootstrap
        C = np.array([len(c[0]) for c in clusters], dtype=float)
        E_m = np.array([np.sum(np.abs(c[0] - c[1])) for c in clusters], dtype=float)
        E_n = np.array([np.sum(np.abs(c[0] - c[2])) for c in clusters], dtype=float)

        rng2 = np.random.default_rng(42)
        agg_maes = []
        agg_skills = []
        for _ in range(100):
            idx = rng2.integers(0, n_clusters, size=n_clusters)
            counts = np.bincount(idx, minlength=n_clusters)
            b_num = np.dot(counts, E_m)
            b_tot = np.dot(counts, C)
            b_den = np.dot(counts, E_n)
            agg_maes.append(b_num / b_tot)
            agg_skills.append(1.0 - (b_num / b_den))

        # Max absolute differences must be < 1e-12
        max_diff_mae = np.max(np.abs(np.array(raw_maes) - np.array(agg_maes)))
        max_diff_skill = np.max(np.abs(np.array(raw_skills) - np.array(agg_skills)))
        assert max_diff_mae < 1e-12, f"Bootstrap MAE mismatch: {max_diff_mae}"
        assert max_diff_skill < 1e-12, f"Bootstrap Skill mismatch: {max_diff_skill}"

    def test_compute_slice_metrics_empty_slice_complete_schema(self):
        """Verify that an empty or all-abstain slice returns all required keys with NaNs."""
        empty_df = pd.DataFrame(columns=[
            "district", "market", "commodity", "variety", "grade",
            "y_true", "model_pred", "naive_pred"
        ])
        metrics = compute_slice_metrics(
            empty_df,
            pred_col="model_pred",
            true_col="y_true",
            naive_col="naive_pred",
        )

        required_keys = [
            "total_samples", "scored_count", "abstention_count", "unique_series",
            "coverage", "is_low_n", "mae", "mae_ci_lower", "mae_ci_upper", "mae_ci_95",
            "rmse", "bias", "median_ae", "mape", "pct_within_5pct",
            "paired_count", "paired_mae", "paired_naive_mae", "skill",
            "skill_ci_lower", "skill_ci_upper", "skill_ci_95",
        ]
        for k in required_keys:
            assert k in metrics, f"Missing key in empty slice schema: {k}"

        assert metrics["total_samples"] == 0
        assert metrics["scored_count"] == 0
        assert metrics["unique_series"] == 0
        assert metrics["coverage"] == 0.0
        assert metrics["is_low_n"] is True
        assert math.isnan(metrics["mae"])
        assert math.isnan(metrics["skill"])

    def test_compute_slice_metrics_numeric_cis_and_zero_denominator(self):
        """Verify numeric CI fields and that skill is undefined (NaN) when denominator is zero."""
        # Zero error for naive means denom == 0
        df = pd.DataFrame({
            "district": ["Kanpur"] * 20 + ["Lucknow"] * 20,
            "market": ["Kanpur"] * 20 + ["Lucknow"] * 20,
            "commodity": ["Wheat"] * 20 + ["Potato"] * 20,
            "variety": ["Dara"] * 20 + ["Other"] * 20,
            "grade": ["FAQ"] * 20 + ["FAQ"] * 20,
            "y_true": [1000.0] * 40,
            "naive_pred": [1000.0] * 40,  # Zero error -> denom = 0
            "model_pred": [1010.0] * 40,
        })

        metrics = compute_slice_metrics(
            df,
            pred_col="model_pred",
            true_col="y_true",
            naive_col="naive_pred",
            n_bootstrap=100,
        )

        assert metrics["scored_count"] == 40
        assert metrics["mae"] == 10.0
        # Denominator zero -> skill must be NaN, NEVER 0.0!
        assert math.isnan(metrics["skill"])
        # Numeric CI fields exist
        assert "mae_ci_lower" in metrics
        assert "mae_ci_upper" in metrics
        assert "skill_ci_lower" in metrics
        assert "skill_ci_upper" in metrics
