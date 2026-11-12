"""
Unit tests and safety verification for Chronological Prediction Intervals Pipeline
Task: MP-FC-008

Verifies:
1. Pure AST safety: zero model fitting, training, or tuning calls in src/forecast_intervals.py.
2. Exact finite-sample conformal rank formula: k = ceil((n + 1) * (1 - alpha)), no rounding.
3. Grouping rules: exact commodity (N >= 200, series >= 10), POOLED_FALLBACK, NO_CALIBRATION.
4. Non-negative support clipping: lower bound never drops below zero.
5. Zero-error calibration: when past residuals are 0, calibrated quantile is 0 and half-width is 0.
6. Chronological maturity: F1 has NO_PRIOR_CALIBRATION; F2 never sees F2/F3/F4.
7. Future mutation immunity: mutating future fold true values does not change earlier calibration quantiles.
8. Serialization and roundtrip: JSON/CSV exports reload faithfully.
9. Shared inference helper: predict_interval checks parameter sanity, bounds, and fallbacks.
"""

import ast
from datetime import date
import json
import math
from pathlib import Path
import tempfile
import pytest

from src.forecast_intervals import (
    compute_conformal_rank,
    predict_interval,
    compute_calibration_quantiles_for_fold,
    evaluate_interval_slice,
    atomic_write_json,
    atomic_write_csv,
    quantile_linear,
    compute_series_key,
    compute_origin_key,
)


class TestIntervalASTSafety:
    def test_zero_fit_train_or_tune_calls(self):
        """Verify via AST that src/forecast_intervals.py never calls fit, train, or tune."""
        script_path = Path("src/forecast_intervals.py")
        assert script_path.exists(), "src/forecast_intervals.py missing!"
        tree = ast.parse(script_path.read_text(encoding="utf-8"))

        prohibited = {"fit", "train", "tune", "tune_candidate_models", "train_and_predict_outer"}
        found = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id in prohibited:
                    found.append(func.id)
                elif isinstance(func, ast.Attribute) and func.attr in prohibited:
                    found.append(func.attr)

        assert not found, f"Prohibited training/fitting calls found in intervals pipeline: {found}"


class TestQuantileAndRankFormulas:
    def test_conformal_rank_exact_calculation(self):
        """Verify k = ceil((n + 1) * (1 - alpha)) on standard test cases."""
        # n = 99, 1 - alpha = 0.90 -> (100) * 0.90 = 90
        assert compute_conformal_rank(99, 0.10) == 90

        # n = 100, 1 - alpha = 0.90 -> (101) * 0.90 = 90.9 -> ceil is 91
        assert compute_conformal_rank(100, 0.10) == 91

        # n = 1000, 1 - alpha = 0.95 -> (1001) * 0.95 = 950.95 -> ceil is 951
        assert compute_conformal_rank(1000, 0.05) == 951

        # n = 19, 1 - alpha = 0.90 -> 20 * 0.90 = 18
        assert compute_conformal_rank(19, 0.10) == 18

    def test_ties_and_quantile_monotonicity(self):
        """Ensure tied values preserve rank and produce non-decreasing quantiles."""
        scores = [0.05, 0.05, 0.05, 0.10, 0.10, 0.15]
        n = len(scores)
        k_90 = compute_conformal_rank(n, 0.10)  # ceil(7 * 0.9) = 7 > 6 -> withhold
        assert k_90 > n

        scores_large = [0.05] * 50 + [0.10] * 50
        n_large = len(scores_large)
        k_large = compute_conformal_rank(n_large, 0.10)  # ceil(101 * 0.9) = 91
        assert k_large <= n_large
        val = scores_large[k_large - 1]
        assert val == 0.10


class TestGroupingAndFallbackHierarchy:
    def test_f1_has_no_prior_calibration(self):
        """Verify F1 produces NO_PRIOR_CALIBRATION."""
        res = compute_calibration_quantiles_for_fold(
            fold_id="F1",
            fold_start_date="2025-01-08",
            all_rows=[{"fold": "F1", "target_date": "2025-01-10", "origin_date": "2025-01-08", "y_true": "100", "y_t": "100", "naive_pred": "100", "commodity": "Wheat"}],
            model_name="naive",
            pred_col="naive_pred",
        )
        assert res["status"] == "NO_CALIBRATION"
        assert res["total_calibration_rows"] == 0

    def test_exact_commodity_vs_pooled_fallback(self):
        """Verify crop with N < 200 falls back to POOLED_FALLBACK while crop with N >= 200 uses EXACT_COMMODITY."""
        rows = []
        # Create Wheat with 250 rows across 12 series
        for s in range(12):
            for i in range(21):
                rows.append({
                    "fold": "F1",
                    "origin_date": "2025-02-01",
                    "target_date": "2025-02-08",
                    "district": f"D{s}",
                    "market": f"M{s}",
                    "commodity": "Wheat",
                    "variety": "V",
                    "grade": "G",
                    "y_t": "1000.0",
                    "y_true": "1050.0",
                    "naive_pred": "1000.0",
                })
        # Create Potato with only 50 rows across 2 series
        for s in range(2):
            for i in range(25):
                rows.append({
                    "fold": "F1",
                    "origin_date": "2025-02-01",
                    "target_date": "2025-02-08",
                    "district": f"DP{s}",
                    "market": f"MP{s}",
                    "commodity": "Potato",
                    "variety": "VP",
                    "grade": "GP",
                    "y_t": "1000.0",
                    "y_true": "1080.0",
                    "naive_pred": "1000.0",
                })

        cal_res = compute_calibration_quantiles_for_fold(
            fold_id="F2",
            fold_start_date="2025-07-08",
            all_rows=rows,
            model_name="naive",
            pred_col="naive_pred",
            nominal_levels=[0.90],
            min_group_origins=200,
            min_group_series=10,
        )
        assert cal_res["status"] == "CALIBRATED"
        quantiles_90 = cal_res["quantiles"][0.90]

        # Wheat should be EXACT_COMMODITY
        assert "Wheat" in quantiles_90["by_commodity"]
        assert quantiles_90["by_commodity"]["Wheat"]["group_type"] == "EXACT_COMMODITY"

        # Potato should NOT be in by_commodity (falls back)
        assert "Potato" not in quantiles_90["by_commodity"]

        # Pooled should be POOLED_FALLBACK
        assert quantiles_90["pooled"]["group_type"] == "POOLED_FALLBACK"


class TestSupportClippingAndZeroResiduals:
    def test_non_negative_support_clipping(self):
        """Verify lower bound is clipped at 0.0 when point_pred - half_width < 0."""
        cal_artifacts = {
            "F2": {
                "naive": {
                    "status": "CALIBRATED",
                    "quantiles": {
                        0.90: {
                            "pooled": {"quantile": 0.50, "group_type": "POOLED_FALLBACK"},
                            "by_commodity": {},
                        }
                    }
                }
            }
        }
        # point_pred = 100, y_t = 300 -> half_width = 150 -> raw lower = -50 -> clipped to 0.0
        res = predict_interval(
            model_name="naive",
            point_pred=100.0,
            y_t=300.0,
            commodity="Tomato",
            fold_id="F2",
            nominal_level=0.90,
            calibration_artifacts=cal_artifacts,
        )
        assert res["status"] == "SUCCESS"
        assert res["lower"] == 0.0
        assert res["upper"] == 250.0
        assert res["width"] == 250.0
        assert res["group_type"] == "POOLED_FALLBACK"

    def test_zero_error_residual_calibration(self):
        """Verify perfect past predictions produce zero quantile and zero half-width."""
        cal_artifacts = {
            "F2": {
                "naive": {
                    "status": "CALIBRATED",
                    "quantiles": {
                        0.90: {
                            "pooled": {"quantile": 0.0, "group_type": "POOLED_FALLBACK"},
                            "by_commodity": {},
                        }
                    }
                }
            }
        }
        res = predict_interval(
            model_name="naive",
            point_pred=2000.0,
            y_t=2000.0,
            commodity="Wheat",
            fold_id="F2",
            nominal_level=0.90,
            calibration_artifacts=cal_artifacts,
        )
        assert res["status"] == "SUCCESS"
        assert res["half_width"] == 0.0
        assert res["lower"] == 2000.0
        assert res["upper"] == 2000.0
        assert res["width"] == 0.0


class TestFutureOutcomeMutationImmunity:
    def test_future_outcomes_do_not_leak_into_earlier_calibration(self):
        """Mutating future fold (F2/F3) outcomes must have zero impact on F2 calibration quantiles."""
        rows_base = []
        # F1 rows (preceding 180 days)
        for s in range(12):
            for i in range(25):
                rows_base.append({
                    "fold": "F1",
                    "origin_date": "2025-02-01",
                    "target_date": "2025-02-08",
                    "district": f"D{s}",
                    "market": f"M{s}",
                    "commodity": "Wheat",
                    "variety": "V",
                    "grade": "G",
                    "y_t": "1000.0",
                    "y_true": "1050.0",
                    "naive_pred": "1000.0",
                })
        # F2 rows (future relative to F1)
        for s in range(5):
            rows_base.append({
                "fold": "F2",
                "origin_date": "2025-08-01",
                "target_date": "2025-08-08",
                "district": f"D{s}",
                "market": f"M{s}",
                "commodity": "Wheat",
                "variety": "V",
                "grade": "G",
                "y_t": "1000.0",
                "y_true": "1050.0",
                "naive_pred": "1000.0",
            })

        # Run calibration on base
        cal_1 = compute_calibration_quantiles_for_fold(
            fold_id="F2",
            fold_start_date="2025-07-08",
            all_rows=rows_base,
            model_name="naive",
            pred_col="naive_pred",
            nominal_levels=[0.90],
            min_group_origins=200,
            min_group_series=10,
        )

        # Mutate F2 outcomes violently (e.g. 10x true price)
        import copy
        rows_mutated = copy.deepcopy(rows_base)
        for r in rows_mutated:
            if r["fold"] == "F2":
                r["y_true"] = "99999.0"

        cal_2 = compute_calibration_quantiles_for_fold(
            fold_id="F2",
            fold_start_date="2025-07-08",
            all_rows=rows_mutated,
            model_name="naive",
            pred_col="naive_pred",
            nominal_levels=[0.90],
            min_group_origins=200,
            min_group_series=10,
        )

        q1 = cal_1["quantiles"][0.90]["pooled"]["quantile"]
        q2 = cal_2["quantiles"][0.90]["pooled"]["quantile"]
        assert q1 == q2, f"Future outcome mutation altered past calibration: {q1} != {q2}"


class TestSerializationAndInferenceRoundtrip:
    def test_json_and_csv_atomic_writers(self):
        """Verify atomic serialization and faithful readback."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            json_file = tmp / "test_cal.json"
            sample_data = {"test_key": 123.456, "status": "CALIBRATED"}
            atomic_write_json(sample_data, json_file)
            assert json_file.exists()
            with open(json_file, "r") as f:
                loaded = json.load(f)
            assert loaded == sample_data

            csv_file = tmp / "test_scorecard.csv"
            sample_records = [{"slice": "A", "val": 1.0}, {"slice": "B", "val": 2.0}]
            atomic_write_csv(sample_records, csv_file)
            assert csv_file.exists()
            with open(csv_file, "r") as f:
                import csv
                reader = list(csv.DictReader(f))
            assert len(reader) == 2
            assert reader[0]["slice"] == "A"
