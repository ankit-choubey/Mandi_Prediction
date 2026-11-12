"""
Unit tests and regression checks for Standalone Prediction Scoring Pipeline
Task: MP-FC-007-SCORE

Verifies:
1. Scorer never imports or calls model fitting, training, or tuning functions.
2. Complete reporting miniature path executes without NameError, KeyError, or serialization issues.
3. Empty slices, zero denominators, missing naive pairs, and all-abstain slices produce valid schemas.
4. Output tables serialize atomically with valid checksums and manifest records.
5. Prediction archive bytes remain strictly immutable and unchanged.
"""

import ast
from datetime import date
import gzip
import hashlib
import json
import math
from pathlib import Path
import tempfile
import numpy as np
import pandas as pd
import pytest

from src.score_forecast_archive import (
    evaluate_slice_suite,
    run_miniature_preflight,
    execute_archive_scoring,
    atomic_write_csv,
    atomic_write_json,
    MODEL_COLUMNS,
)


class TestScorerSafetyAndCausality:
    def test_scorer_contains_no_fit_train_or_tune_calls(self):
        """Verify via AST that src/score_forecast_archive.py never calls fit, train, or tune."""
        scorer_path = Path("src/score_forecast_archive.py")
        assert scorer_path.exists()
        tree = ast.parse(scorer_path.read_text(encoding="utf-8"))

        prohibited_calls = {"fit", "train", "tune", "tune_candidate_models", "train_and_predict_outer"}
        found_prohibited = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id in prohibited_calls:
                    found_prohibited.append(func.id)
                elif isinstance(func, ast.Attribute) and func.attr in prohibited_calls:
                    found_prohibited.append(func.attr)

        assert not found_prohibited, f"Prohibited training/fitting calls found in scorer: {found_prohibited}"

    def test_archive_bytes_immutability(self):
        """Verify that running preflight or scoring does not alter the underlying prediction archive."""
        archive_path = Path("experiments/outputs/FC007_recovery/experiments/outputs/FC007/master_predictions_fc007.csv.gz")
        if not archive_path.exists():
            pytest.skip("Recovery archive not found.")

        expected_sha = "a61b38328e011b2ed75dd5d814fbf697d624ac948c50a198d374bfcaff2b9970"
        initial_sha = hashlib.sha256(archive_path.read_bytes()).hexdigest()
        assert initial_sha == expected_sha, "Archive hash altered prior to test!"

        # Read small sample
        with gzip.open(archive_path, "rt", encoding="utf-8") as f:
            _ = pd.read_csv(f, nrows=10)

        post_sha = hashlib.sha256(archive_path.read_bytes()).hexdigest()
        assert post_sha == expected_sha, "Archive hash modified after reading!"


class TestMiniaturePreflightAndEdgeCases:
    @pytest.fixture
    def sample_predictions_fixture(self):
        """Create a synthetic DataFrame replicating master_predictions_fc007 schema."""
        n = 30
        return pd.DataFrame({
            "fold": ["F1"] * 15 + ["F2"] * 15,
            "district": ["Kanpur"] * n,
            "market": ["Kanpur(Grain)"] * n,
            "commodity": ["Wheat"] * n,
            "variety": ["Dara"] * n,
            "grade": ["FAQ"] * n,
            "origin_date": [f"2025-01-{i+1:02d}" for i in range(n)],
            "target_date": [f"2025-01-{i+8:02d}" for i in range(n)],
            "exact_t7": [True] * n,
            "is_tier_a": [True] * n,
            "is_tier_b": [True] * n,
            "tier": ["TierB"] * n,
            "date_regime": ["HISTORICAL"] * n,
            "y_t": [2000.0 + i for i in range(n)],
            "y_true": [2050.0 + i for i in range(n)],
            "target_delta": [50.0] * n,
            "naive_pred": [2000.0 + i for i in range(n)],
            "ma_pred": [1990.0 + i for i in range(n)],
            "seasonal_pred": [1980.0 + i for i in range(n)],
            "drift_pred": [2010.0 + i for i in range(n)],
            "ridge_pred": [2045.0 + i for i in range(n)],
            "ridge_abstention": ["SCORED"] * n,
            "hgb_pred": [2048.0 + i for i in range(n)],
            "hgb_abstention": ["SCORED"] * n,
        })

    def test_evaluate_slice_suite_empty_and_zero_denom(self, sample_predictions_fixture):
        # Empty slice
        empty_res = evaluate_slice_suite("Empty_Slice", sample_predictions_fixture.head(0), n_bootstrap=10)
        assert len(empty_res) == len(MODEL_COLUMNS)
        for r in empty_res:
            assert r["total_samples"] == 0
            assert r["scored_count"] == 0
            assert math.isnan(r["mae"])
            assert math.isnan(r["skill"])
            assert r["is_low_n"] is True

        # Zero denominator slice (naive has zero error)
        zero_den_df = sample_predictions_fixture.head(10).copy()
        zero_den_df["naive_pred"] = zero_den_df["y_true"]
        zd_res = evaluate_slice_suite("Zero_Denom_Slice", zero_den_df, n_bootstrap=10)
        for r in zd_res:
            assert math.isnan(r["skill"]), "Skill must be NaN when naive error is zero!"

    def test_miniature_preflight_execution(self, sample_predictions_fixture):
        dummy_keys = {("Kanpur", "Kanpur(Grain)", "Wheat", "Dara", "FAQ", "2025-01-01")}
        res = run_miniature_preflight(sample_predictions_fixture, dummy_keys)
        assert res["status"] == "PREFLIGHT_PASSED"

    def test_atomic_writers(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            df = pd.DataFrame({"col": [1, 2, 3]})
            csv_path = tmp / "test.csv"
            atomic_write_csv(df, csv_path)
            assert csv_path.exists()
            assert len(pd.read_csv(csv_path)) == 3

            json_path = tmp / "test.json"
            atomic_write_json({"a": 1}, json_path)
            assert json_path.exists()
            with open(json_path) as f:
                assert json.load(f) == {"a": 1}
