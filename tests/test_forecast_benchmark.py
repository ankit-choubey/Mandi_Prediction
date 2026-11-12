"""
Unit tests for APMC Mandi Price Forecasting Benchmark Engine
Task: MP-FC-007
"""

from datetime import date, timedelta
import math
import numpy as np
import pandas as pd
import pytest
from sklearn.pipeline import Pipeline

from src.forecast_features import SeriesIdentity, FEATURE_COLUMNS
from src.forecast_benchmark import (
    TemporalFold,
    InnerSplit,
    get_standard_folds,
    get_inner_splits,
    extract_series_target,
    build_candidate_ridge_model,
    build_candidate_hgb_model,
    ForecastBenchmarkEngine,
    compute_slice_metrics,
)


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
        assert f2.regime == "TRANSITION"

        assert f3.fold_id == "F3"
        assert f3.train_cutoff == date(2025, 12, 18)
        assert f3.max_train_origin == date(2025, 12, 10)
        assert f3.test_start == date(2025, 12, 26)
        assert f3.test_end == date(2026, 3, 31)
        assert f3.regime == "TRANSITION"

        assert f4.fold_id == "F4"
        assert f4.train_cutoff == date(2026, 3, 31)
        assert f4.max_train_origin == date(2026, 3, 23)
        assert f4.test_start == date(2026, 4, 8)
        assert f4.test_end == date(2026, 9, 30)
        assert f4.regime == "MODERN"

    def test_inner_splits_generation(self):
        fold = TemporalFold(
            fold_id="F1",
            train_cutoff=date(2024, 12, 31),
            test_start=date(2025, 1, 8),
            test_end=date(2025, 6, 30),
            embargo_days=7,
        )
        splits = get_inner_splits(fold)
        assert len(splits) == 2
        s1, s2 = splits

        # Split 1: val window [T-119d, T-60d]
        assert s1.val_start == date(2024, 12, 31) - timedelta(days=119)
        assert s1.val_end == date(2024, 12, 31) - timedelta(days=60)
        assert s1.inner_fit_cutoff == date(2024, 12, 31) - timedelta(days=120)
        assert s1.inner_fit_max_origin == s1.inner_fit_cutoff - timedelta(days=8)

        # Split 2: val window [T-59d, T]
        assert s2.val_start == date(2024, 12, 31) - timedelta(days=59)
        assert s2.val_end == date(2024, 12, 31)
        assert s2.inner_fit_cutoff == date(2024, 12, 31) - timedelta(days=60)
        assert s2.inner_fit_max_origin == s2.inner_fit_cutoff - timedelta(days=8)


class TestTargetExtraction:
    def test_extract_series_target_exact(self):
        # t = 2024-01-01 -> t+7 = 2024-01-08
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
        # t = 2024-01-01 -> t+7 = 2024-01-08 is missing, but t+6 and t+8 exist (both diff=1)
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

    def test_extract_series_target_max_date_enforcement(self):
        # Target t+7 is past max_target_date (train cutoff) -> must not leak!
        history = {
            date(2024, 1, 1): 1000.0,
            date(2024, 1, 8): 1070.0,
        }
        price, trg_date, is_exact = extract_series_target(
            history,
            date(2024, 1, 1),
            max_target_date=date(2024, 1, 7),  # cutoff before t+7
        )
        assert price is None
        assert trg_date is None
        assert is_exact is False


class TestModelsAndResponseChoice:
    def test_ridge_pipeline_imputation_and_scaling(self):
        # Build small X with missing values in train
        X_train = pd.DataFrame({
            "f1": [1.0, np.nan, 3.0, 4.0, 5.0],
            "f2": [10.0, 20.0, 30.0, 40.0, 50.0],
        })
        y_train = np.array([10.0, 20.0, 30.0, 40.0, 50.0])

        model = build_candidate_ridge_model(alpha=1.0)
        model.fit(X_train, y_train)

        # Check that median imputer fitted value is 3.5 (median of [1, 3, 4, 5])
        imputer = model.named_steps["imputer"]
        assert imputer.statistics_[0] == 3.5

        # Predict on test row with missing value
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
        # Create 2 series with enough history for Tier A eligibility (>=60 obs, >=0.30 cov)
        # Covering 2024-01-01 through mid-2025 (e.g. 260 steps * 2 days = 520 days)
        dates = [date(2024, 1, 1) + timedelta(days=i * 2) for i in range(260)]
        s1 = SeriesIdentity("Kanpur", "Kanpur(Grain)", "Wheat", "Dara", "FAQ")
        s2 = SeriesIdentity("Lucknow", "Lucknow", "Potato", "Other", "FAQ")

        # Linear trend plus small wave
        h1 = {d: 2000.0 + i * 2.0 + (i % 5) * 10.0 for i, d in enumerate(dates)}
        h2 = {d: 800.0 + i * 1.5 - (i % 4) * 8.0 for i, d in enumerate(dates)}

        return {s1: h1, s2: h2}

    def test_engine_partition_and_run(self, small_series_fixture):
        engine = ForecastBenchmarkEngine()
        f1 = engine.folds[0]  # F1: train <= 2024-12-31, test 2025-01-08..2025-06-30

        train_df, test_df = engine.prepare_dataset_partitions(small_series_fixture, f1)

        assert not train_df.empty
        assert not test_df.empty

        # Check label maturity in training partition
        assert all(train_df["target_date"] <= f1.train_cutoff)
        assert all(train_df["origin_date"] <= f1.max_train_origin)

        # Check outer test partition
        assert all(f1.test_start <= d <= f1.test_end for d in test_df["origin_date"])
        assert all(d <= f1.test_end for d in test_df["target_date"])

        # Check audited baselines exist in test_df
        assert "naive_pred" in test_df.columns
        assert "ma_pred" in test_df.columns
        assert "seasonal_pred" in test_df.columns
        assert "drift_pred" in test_df.columns

        # Train and predict
        pred_df, models = engine.train_and_predict_outer(
            train_df,
            test_df,
            ridge_alpha=1.0,
            hgb_config={"max_depth": 3, "min_samples_leaf": 5, "learning_rate": 0.05, "max_iter": 50},
        )

        assert "ridge_pred" in pred_df.columns
        assert "hgb_pred" in pred_df.columns
        assert models["fitted"] is True

        # Nonpositive reconstructed forecast check
        # If delta makes y_hat <= 0, must be marked NON_POSITIVE_RECONSTRUCTED_FORECAST
        assert all(
            reason in ("SCORED", "NON_POSITIVE_RECONSTRUCTED_FORECAST")
            for reason in pred_df["ridge_abstention"]
        )

    def test_engine_inner_tuning(self, small_series_fixture):
        engine = ForecastBenchmarkEngine()
        f1 = engine.folds[0]

        tuning_results = engine.tune_candidate_models(small_series_fixture, f1)
        assert tuning_results["fold_id"] == "F1"
        assert tuning_results["best_ridge_alpha"] in [0.1, 1.0, 10.0]
        assert tuning_results["best_hgb_config"]["config_id"] in ["hgb_depth3", "hgb_depth5"]


class TestEvaluationMetricsAndBootstrap:
    def test_compute_slice_metrics_perfect_predictions(self):
        df = pd.DataFrame({
            "district": ["Kanpur"] * 20 + ["Lucknow"] * 20,
            "market": ["Kanpur"] * 20 + ["Lucknow"] * 20,
            "commodity": ["Wheat"] * 20 + ["Potato"] * 20,
            "variety": ["Dara"] * 20 + ["Other"] * 20,
            "grade": ["FAQ"] * 20 + ["FAQ"] * 20,
            "y_true": [2000.0 + i for i in range(40)],
            "naive_pred": [1990.0 + i for i in range(40)],  # Naive has error 10.0
            "model_pred": [2000.0 + i for i in range(40)],  # Model has error 0.0 (perfect)
        })

        metrics = compute_slice_metrics(
            df,
            pred_col="model_pred",
            true_col="y_true",
            naive_col="naive_pred",
            n_bootstrap=100,
            seed=42,
        )

        assert metrics["scored_count"] == 40
        assert metrics["mae"] == 0.0
        assert metrics["rmse"] == 0.0
        assert metrics["bias"] == 0.0
        assert metrics["median_ae"] == 0.0
        assert metrics["mape"] == 0.0
        assert metrics["pct_within_5pct"] == 100.0

        # Skill = 1 - (0 / 400) = 1.0
        assert metrics["skill"] == 1.0
        assert metrics["paired_naive_mae"] == 10.0

        # LOW-N flag is True because scored_count 40 < 200
        assert metrics["is_low_n"] is True

    def test_compute_slice_metrics_abstention_handling(self):
        df = pd.DataFrame({
            "district": ["Kanpur", "Kanpur"],
            "market": ["Kanpur", "Kanpur"],
            "commodity": ["Wheat", "Wheat"],
            "variety": ["Dara", "Dara"],
            "grade": ["FAQ", "FAQ"],
            "y_true": [2000.0, 2100.0],
            "naive_pred": [1990.0, 2090.0],
            "model_pred": [np.nan, np.nan],  # All abstained
        })

        metrics = compute_slice_metrics(
            df,
            pred_col="model_pred",
            true_col="y_true",
            naive_col="naive_pred",
            n_bootstrap=0,
        )

        assert metrics["scored_count"] == 0
        assert math.isnan(metrics["mae"])
        assert math.isnan(metrics["skill"])
        assert metrics["is_low_n"] is True
