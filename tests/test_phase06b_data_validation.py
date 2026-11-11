"""
Phase 06b Automated Verification Test Suite
APMC Mandi Market Intelligence System

Tests and verifies:
1. Complete existence of all required Phase 06b evidence artifacts.
2. Data requirements matrix schema and variable coverage (Market, Production, Weather, Logistics, Storage, Economic).
3. Dataset inventory provenance, official authorities, and licensing.
4. Dataset scorecard tier classifications (REQUIRED, HIGH VALUE, OPTIONAL, NOT SUITABLE).
5. Multi-horizon feasibility metrics (T+1, T+3, T+7, T+14, T+30 match rates and stickiness).
6. Out-of-sample regression benchmark proving zero-return persistence beats ML regression.
7. Cross-district generalization asserting Bundelkhand (Jhansi) transfer failure.
8. Crop storage hurdle rates confirming >85% loss frequency for 7-day holding across grains and perishables.
"""

import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import pytest
import pandas as pd

PHASE_06B_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backing", "phase_06b"))

def test_phase06b_artifacts_exist():
    required_files = [
        "README.md",
        "data_requirements_matrix.csv",
        "dataset_inventory.csv",
        "dataset_scorecard.csv",
        "leakage_and_availability_audit.md",
        "join_compatibility_matrix.csv",
        "crop_storage_profiles.csv",
        "mathematical_method_comparison.md",
        "ablation_plan.md",
        "statistical_testing_plan.md",
        "recommended_data_foundation.md",
        "experiment_results.md",
        "limitations.md",
        "execution_log.txt",
        "multi_horizon_feasibility_summary.csv",
        "classification_threshold_comparison.csv",
        "cross_district_generalization.csv",
        "multi_horizon_regression_benchmark.csv",
        "crop_category_hurdle_rate_analysis.csv"
    ]
    for fname in required_files:
        fpath = os.path.join(PHASE_06B_DIR, fname)
        assert os.path.exists(fpath), f"Missing required Phase 06b artifact: {fname}"
        assert os.path.getsize(fpath) > 0, f"Artifact is empty: {fname}"

def test_phase06b_data_requirements_matrix():
    path = os.path.join(PHASE_06B_DIR, "data_requirements_matrix.csv")
    df = pd.read_csv(path)
    required_cols = [
        "variable", "meaning", "unit", "temporal_frequency", "spatial_level",
        "expected_source", "source_authority", "historical_coverage", "access_method",
        "licence_or_restriction", "availability", "join_key", "likely_lag",
        "leakage_risk", "measurement_reliability", "expected_modelling_value",
        "whether_currently_available", "whether_acquisition_required", "recommended_priority",
        "evidence_or_source_url"
    ]
    for col in required_cols:
        assert col in df.columns, f"Missing column in data_requirements_matrix.csv: {col}"
    assert len(df) >= 30, f"Expected at least 30 candidate variables, got {len(df)}"
    # Check core priority categories
    priorities = df["recommended_priority"].unique()
    assert "CORE" in priorities
    assert "HIGH" in priorities

def test_phase06b_dataset_inventory():
    path = os.path.join(PHASE_06B_DIR, "dataset_inventory.csv")
    df = pd.read_csv(path)
    assert len(df) >= 10, f"Expected at least 10 documented datasets, got {len(df)}"
    assert "dataset_name" in df.columns
    assert "provider" in df.columns
    assert "source_authority" in df.columns
    assert "can_join_current_data" in df.columns

def test_phase06b_dataset_scorecard():
    path = os.path.join(PHASE_06B_DIR, "dataset_scorecard.csv")
    df = pd.read_csv(path)
    assert len(df) >= 12
    tiers = set(df["tier_classification"].unique())
    assert {"REQUIRED", "HIGH VALUE", "OPTIONAL", "NOT SUITABLE"}.issubset(tiers)

def test_phase06b_multi_horizon_feasibility():
    path = os.path.join(PHASE_06B_DIR, "multi_horizon_feasibility_summary.csv")
    df = pd.read_csv(path)
    assert len(df) == 5, f"Expected 5 horizons, got {len(df)}"
    horizons = list(df["horizon"])
    assert horizons == ["T+1", "T+3", "T+7", "T+14", "T+30"]
    # Verify match rates are positive and reasonable
    assert (df["match_rate_eligible_pct"] > 60.0).all()
    # Verify modal stickiness decreases as horizon increases
    stickiness = list(df["sticky_zero_change_pct"])
    assert stickiness[0] > stickiness[1] > stickiness[2] > stickiness[3] > stickiness[4]
    assert stickiness[0] > 30.0, "T+1 stickiness should exceed 30%"

def test_phase06b_regression_persistence_superiority():
    path = os.path.join(PHASE_06B_DIR, "multi_horizon_regression_benchmark.csv")
    df = pd.read_csv(path)
    assert len(df) == 5
    # Mathematically assert that zero-return persistence beats LightGBM across all 5 horizons
    for _, row in df.iterrows():
        assert row["persistence_mae_pct"] < row["lightgbm_mae_pct"], (
            f"Expected persistence MAE ({row['persistence_mae_pct']}%) < LightGBM MAE "
            f"({row['lightgbm_mae_pct']}%) at {row['horizon']}"
        )
        assert row["lightgbm_beats_persistence"] == "NO (Persistence Superior)"

def test_phase06b_cross_district_transfer_audit():
    path = os.path.join(PHASE_06B_DIR, "cross_district_generalization.csv")
    df = pd.read_csv(path)
    assert len(df) == 5
    districts = set(df["held_out_district"])
    assert districts == {"Ghaziabad", "Jhansi", "Kanpur", "Lucknow", "Unnao"}
    # Assert that Jhansi (Bundelkhand) transfer performance drops below baseline
    jhansi_row = df[df["held_out_district"] == "Jhansi"].iloc[0]
    assert jhansi_row["lodo_test_accuracy_pct"] < jhansi_row["test_majority_baseline_acc_pct"]
    assert jhansi_row["generalization_verdict"] == "WEAK / NON-GENERALIZABLE"

def test_phase06b_crop_storage_hurdle_rates():
    path = os.path.join(PHASE_06B_DIR, "crop_category_hurdle_rate_analysis.csv")
    df = pd.read_csv(path)
    assert len(df) == 3
    # Assert that 7-day storage loss frequency exceeds 85% across all crop categories
    for _, row in df.iterrows():
        assert row["loss_frequency_pct"] > 85.0, (
            f"Expected loss frequency > 85% for {row['crop_category']}, got {row['loss_frequency_pct']}%"
        )
        assert "UNVIABLE" in row["economic_viability_verdict"]
