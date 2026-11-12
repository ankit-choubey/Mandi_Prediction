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
    normalize_nominal_level,
    build_output_manifest,
    create_calibration_envelope,
    validate_and_load_calibration_envelope,
    compute_semantic_json_sha256,
    get_peak_rss_mb,
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

    def test_normalize_nominal_level(self):
        """Verify nominal level normalizer handles floats, strings, and percentages."""
        assert normalize_nominal_level(0.90) == (0.90, "0.90")
        assert normalize_nominal_level(0.9) == (0.90, "0.90")
        assert normalize_nominal_level("0.90") == (0.90, "0.90")
        assert normalize_nominal_level("0.9") == (0.90, "0.90")
        assert normalize_nominal_level("90%") == (0.90, "0.90")
        assert normalize_nominal_level(90) == (0.90, "0.90")

        assert normalize_nominal_level(0.95) == (0.95, "0.95")
        assert normalize_nominal_level("0.95") == (0.95, "0.95")
        assert normalize_nominal_level("95%") == (0.95, "0.95")
        assert normalize_nominal_level(95) == (0.95, "0.95")

        with pytest.raises(ValueError, match="Unsupported nominal level"):
            normalize_nominal_level(0.80)
        with pytest.raises(ValueError, match="Unsupported nominal level"):
            normalize_nominal_level("0.99")
        with pytest.raises(ValueError, match="Invalid nominal level"):
            normalize_nominal_level("invalid_level")

    def test_predict_interval_json_reload_roundtrip(self):
        """
        Verify saved JSON calibration artifacts reload and evaluate without UNSUPPORTED_NOMINAL_LEVEL.
        Tests 90% and 95%, exact commodity and pooled fallback, and all calibrated folds.
        Compares pre-export and post-load bounds numerically to machine precision.
        """
        cal_path = Path("experiments/reports/FC008/calibration_quantiles.json")
        assert cal_path.exists(), "FC008 calibration_quantiles.json missing!"
        with open(cal_path, "r", encoding="utf-8") as f:
            cal_json = json.load(f)

        envelope_path = Path("experiments/reports/FC008/calibration_envelope_v1.json")
        assert envelope_path.exists(), "FC008 calibration_envelope_v1.json missing!"
        envelope = validate_and_load_calibration_envelope(envelope_path)

        # F1 produces NO_CALIBRATION
        res_f1 = predict_interval("naive", 2000.0, 2000.0, "Wheat", "F1", 0.90, cal_json)
        assert res_f1["status"] == "NO_CALIBRATION"
        assert res_f1["operational_advisory_allowed"] is False

        # Test cases across folds, commodities, models, and levels
        test_cases = [
            ("F2", "Wheat", "naive", 0.90, 2150.0, 2100.0, "EXACT_COMMODITY"),
            ("F2", "Wheat", "naive", "0.90", 2150.0, 2100.0, "EXACT_COMMODITY"),
            ("F2", "Wheat", "naive", 0.95, 2150.0, 2100.0, "EXACT_COMMODITY"),
            ("F2", "Potato", "ridge", "0.95", 1450.0, 1400.0, "EXACT_COMMODITY"),
            ("F2", "ExoticCrop", "hist_gradient_boosting", 0.90, 1800.0, 1750.0, "POOLED_FALLBACK"),
            ("F3", "Wheat", "naive", 0.90, 2200.0, 2150.0, "EXACT_COMMODITY"),
            ("F3", "Potato", "naive", 0.95, 1300.0, 1250.0, "EXACT_COMMODITY"),
            ("F4", "Wheat", "naive", 0.90, 2300.0, 2250.0, "EXACT_COMMODITY"),
            ("F4", "Rice", "naive", 0.95, 2600.0, 2550.0, "EXACT_COMMODITY"),
        ]

        for fold, crop, model, level, p, yt, exp_group in test_cases:
            res_raw = predict_interval(model, p, yt, crop, fold, level, cal_json)
            res_env = predict_interval(model, p, yt, crop, fold, level, envelope)

            assert res_raw["status"] == "SUCCESS", f"Failed for {fold} {crop} {model} {level}: {res_raw}"
            assert res_env["status"] == "SUCCESS"
            assert res_raw["group_type"] == exp_group
            assert res_env["group_type"] == exp_group

            # Strict numerical equivalence between raw JSON quantiles and envelope
            assert abs(res_raw["lower"] - res_env["lower"]) < 1e-9
            assert abs(res_raw["upper"] - res_env["upper"]) < 1e-9
            assert abs(res_raw["quantile"] - res_env["quantile"]) < 1e-9
            assert abs(res_raw["width"] - res_env["width"]) < 1e-9
            assert res_raw["operational_advisory_allowed"] is False
            assert res_env["operational_advisory_allowed"] is False

    def test_predict_interval_boundary_validations(self):
        """Verify fail-safe behavior for invalid models, units, horizons, dates, and nonfinite values."""
        cal_path = Path("experiments/reports/FC008/calibration_quantiles.json")
        with open(cal_path, "r", encoding="utf-8") as f:
            cal = json.load(f)

        # Invalid model
        res_m = predict_interval("unsupported_model", 2000.0, 2000.0, "Wheat", "F2", 0.90, cal)
        assert res_m["status"] == "UNSUPPORTED_MODEL"

        # Invalid units
        res_u = predict_interval("naive", 2000.0, 2000.0, "Wheat", "F2", 0.90, cal, units="USD")
        assert res_u["status"] == "UNSUPPORTED_UNITS"

        # Invalid horizon
        res_h = predict_interval("naive", 2000.0, 2000.0, "Wheat", "F2", 0.90, cal, horizon_days=30)
        assert res_h["status"] == "UNSUPPORTED_HORIZON"

        # Nonfinite point prediction
        res_nan = predict_interval("naive", float("nan"), 2000.0, "Wheat", "F2", 0.90, cal)
        assert res_nan["status"] == "BLOCKED_INVALID_POINT_PRED"

        # Negative origin price
        res_neg = predict_interval("naive", 2000.0, -100.0, "Wheat", "F2", 0.90, cal)
        assert res_neg["status"] == "BLOCKED_INVALID_ORIGIN_PRICE"

        # Origin date outside validity scope
        res_date = predict_interval("naive", 2000.0, 2000.0, "Wheat", "F2", 0.90, cal, origin_date="2026-08-01")
        assert res_date["status"] == "ORIGIN_DATE_OUTSIDE_VALIDITY_SCOPE"

        # Origin date inside validity scope
        res_date_ok = predict_interval("naive", 2000.0, 2000.0, "Wheat", "F2", 0.90, cal, origin_date="2025-08-01")
        assert res_date_ok["status"] == "SUCCESS"


class TestEnvelopeAndManifestIntegrity:
    def test_calibration_envelope_validation_rules(self):
        """Verify envelope validation rejects corrupted, unordered, negative quantiles, or bad metadata."""
        envelope_path = Path("experiments/reports/FC008/calibration_envelope_v1.json")
        envelope = validate_and_load_calibration_envelope(envelope_path)
        assert envelope["artifact_type"] == "CALIBRATION_ENVELOPE"
        assert envelope["status"] == "RESEARCH_ONLY"
        assert envelope["operational_advisory_allowed"] is False

        # Test unordered quantiles detection: q90 > q95
        import copy
        bad_env = copy.deepcopy(envelope)
        k90 = "0.9" if "0.9" in bad_env["quantiles"]["F2"]["naive"]["quantiles"] else "0.90"
        k95 = "0.95" if "0.95" in bad_env["quantiles"]["F2"]["naive"]["quantiles"] else 0.95
        bad_env["quantiles"]["F2"]["naive"]["quantiles"][k90]["pooled"]["quantile"] = 0.50
        bad_env["quantiles"]["F2"]["naive"]["quantiles"][k95]["pooled"]["quantile"] = 0.10
        with pytest.raises(ValueError, match="Quantile ordering violation"):
            validate_and_load_calibration_envelope(bad_env)

        # Test negative quantile detection
        bad_env2 = copy.deepcopy(envelope)
        bad_env2["quantiles"]["F2"]["naive"]["quantiles"][k90]["pooled"]["quantile"] = -0.05
        with pytest.raises(ValueError, match="Invalid pooled quantile"):
            validate_and_load_calibration_envelope(bad_env2)

        # Test wrong artifact type
        bad_env3 = copy.deepcopy(envelope)
        bad_env3["artifact_type"] = "WRONG_TYPE"
        with pytest.raises(ValueError, match="Invalid artifact_type"):
            validate_and_load_calibration_envelope(bad_env3)

        # Test source archive mismatch
        with pytest.raises(ValueError, match="Source archive SHA-256 mismatch"):
            validate_and_load_calibration_envelope(envelope, expected_source_sha256="wrong_hash")

    def test_manifest_self_exclusion_and_idempotency(self):
        """Verify output manifest excludes itself and temporary files, and repeated generation is idempotent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            # Create sample payload files
            (tmp / "file1.csv").write_text("a,b\n1,2\n", encoding="utf-8")
            (tmp / "file2.json").write_text('{"key": "value"}', encoding="utf-8")
            (tmp / "temp_file.tmp").write_text("temporary data", encoding="utf-8")

            # First manifest generation
            m1 = build_output_manifest(tmp, source_archive_sha256="dummy_sha")
            m1_path = tmp / "output_manifest.json"
            atomic_write_json(m1, m1_path)

            m1_filenames = [e["filename"] for e in m1["manifest"]]
            assert "file1.csv" in m1_filenames
            assert "file2.json" in m1_filenames
            assert "output_manifest.json" not in m1_filenames
            assert "temp_file.tmp" not in m1_filenames
            assert len(m1["manifest"]) == 2

            # Second manifest generation in populated directory with existing output_manifest.json
            m2 = build_output_manifest(tmp, source_archive_sha256="dummy_sha")
            m2_filenames = [e["filename"] for e in m2["manifest"]]
            assert "output_manifest.json" not in m2_filenames
            assert m1 == m2, "Manifest generation is not idempotent!"

    def test_semantic_config_equivalence(self):
        """Verify semantic config equivalence between working file and original run receipt."""
        cfg_path = Path("experiments/configs/interval_calibration_v1.json")
        semantic_sha = compute_semantic_json_sha256(cfg_path)
        expected_semantic = "7ddfa98408ff55bd6ec843c292247176f17851973cbaa8f47d6057b563005ac2"
        assert semantic_sha == expected_semantic

    def test_peak_rss_mb_measurement(self):
        """Verify cross-platform peak RSS reporting returns a positive float."""
        rss = get_peak_rss_mb()
        assert isinstance(rss, float)
        assert rss > 0.0
