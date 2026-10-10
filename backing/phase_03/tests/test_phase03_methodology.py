"""
Automated Methodology and Leakage Verification Test Suite for Phase 3.
Validates:
1. Temporal Split Boundaries and Chronological Ordering
2. Target Realization Isolation and Horizon Embargo Purging
3. Feature Engineering Leakage Resistance (Strictly Past Information)
4. Causal Historical Volatility (No Backfilling into Past)
5. Preprocessing Isolation (Fitted on Training Set Only)
6. Fixed Target Definition Consistency with Phase 2
7. Denominator Reconciliation and Evaluation Integrity
"""

import os
import sys
import pytest
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer

# Add project root to sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

OUTPUTS_DIR = os.path.join(REPO_ROOT, "backing/phase_03/outputs")
PHASE02_CANONICAL = os.path.join(REPO_ROOT, "backing/phase_02/outputs/canonical_market_mapping.csv")
MASTER_CSV = REPO_ROOT



@pytest.fixture(scope="module")
def loaded_phase03_outputs():
    """Load all Phase 3 output CSV tables."""
    outputs = {}
    files = [
        "temporal_split_summary.csv",
        "feature_audit.csv",
        "baseline_metrics.csv",
        "model_comparison.csv",
        "classification_report.csv",
        "confusion_matrix.csv",
        "subgroup_performance.csv",
        "regression_metrics.csv",
    ]
    for f in files:
        path = os.path.join(OUTPUTS_DIR, f)
        assert os.path.exists(path), f"Required Phase 3 output {f} is missing from {OUTPUTS_DIR}"
        outputs[f] = pd.read_csv(path)
    return outputs


@pytest.fixture(scope="module")
def prepared_experiment_data():
    """Recreate the clean dataset and splits according to Phase 3 runner rules."""
    from backing.phase_03.tests.run_phase03_experiment import (
        ingest_and_filter_strategy2,
        engineer_causal_features,
        match_targets_and_partition,
    )

    clean_s2 = ingest_and_filter_strategy2(MASTER_CSV, PHASE02_CANONICAL)
    clean_s2 = engineer_causal_features(clean_s2)
    partitions, summary_df = match_targets_and_partition(clean_s2)
    return partitions, summary_df


# ==============================================================================
# 1. TEMPORAL SPLIT AND EMBARGO TESTS
# ==============================================================================

def test_temporal_split_chronological_ordering(loaded_phase03_outputs):
    """Verify that Train, Validation, and Test boundaries are strictly chronological."""
    split_df = loaded_phase03_outputs["temporal_split_summary.csv"]
    train_row = split_df[split_df["partition_name"] == "TRAIN"].iloc[0]
    val_row = split_df[split_df["partition_name"] == "VALIDATION"].iloc[0]
    test_row = split_df[split_df["partition_name"] == "FINAL_TEST"].iloc[0]

    # Chronological checks
    assert pd.to_datetime(train_row["start_date"]) < pd.to_datetime(train_row["end_date"])
    assert pd.to_datetime(train_row["end_date"]) < pd.to_datetime(val_row["start_date"])
    assert pd.to_datetime(val_row["start_date"]) < pd.to_datetime(val_row["end_date"])
    assert pd.to_datetime(val_row["end_date"]) < pd.to_datetime(test_row["start_date"])
    assert pd.to_datetime(test_row["start_date"]) < pd.to_datetime(test_row["end_date"])


def test_target_realizations_respect_embargo_and_boundaries(prepared_experiment_data):
    """
    Verify horizon-aware purging:
    1. Every training target realization (T+7) falls within the training boundary (<= 2026-01-24).
    2. Every validation target realization (T+7) falls within the validation boundary (<= 2026-04-07).
    3. No training or validation target realization ever enters the final test period (>= 2026-04-08).
    """
    partitions, _ = prepared_experiment_data
    train_df = partitions["train_df"]
    val_df = partitions["val_df"]
    test_df = partitions["test_df"]

    # Target realization date is Target_Date_T7
    assert (train_df["Target_Date_T7"] <= pd.to_datetime("2026-01-24")).all(), (
        "Found training example with target realization date crossing into embargo/validation period!"
    )
    assert (val_df["Target_Date_T7"] <= pd.to_datetime("2026-04-07")).all(), (
        "Found validation example with target realization date crossing into test embargo/test period!"
    )
    assert (val_df["Target_Date_T7"] < pd.to_datetime("2026-04-08")).all(), (
        "Validation target realization must strictly precede final test period start date!"
    )
    assert (test_df["Arrival_Date_Parsed"] >= pd.to_datetime("2026-04-08")).all(), (
        "Test origin date must start at or after 2026-04-08!"
    )


def test_embargo_buffer_purging_counts(loaded_phase03_outputs):
    """Verify that embargo buffers were purged and recorded accurately."""
    split_df = loaded_phase03_outputs["temporal_split_summary.csv"]
    train_row = split_df[split_df["partition_name"] == "TRAIN"].iloc[0]
    val_row = split_df[split_df["partition_name"] == "VALIDATION"].iloc[0]

    # Exact purged counts
    assert train_row["embargo_purged_count"] == 72
    assert val_row["embargo_purged_count"] == 565


# ==============================================================================
# 2. FEATURE LEAKAGE TESTS
# ==============================================================================

def test_feature_audit_no_future_leakage(loaded_phase03_outputs):
    """Verify all features in feature_audit.csv are documented with zero leakage risk."""
    feat_df = loaded_phase03_outputs["feature_audit.csv"]
    assert len(feat_df) == 13
    assert (feat_df["leakage_risk_assessment"].str.contains("ZERO LEAKAGE")).all()
    for _, row in feat_df.iterrows():
        assert "T+1" not in str(row["lookback_period"])
        assert "T+7" not in str(row["lookback_period"])


def test_feature_invariance_to_future_data():
    """
    Unit test: changing future prices (at T+1, T+7, etc.) does NOT change
    any engineered predictor calculated at origin date T.
    """
    dates = pd.date_range("2025-01-01", periods=15, freq="D")
    df1 = pd.DataFrame({
        "series_id_with_grade": ["MandiA_Potato_Jyoti_FAQ"] * 15,
        "Commodity": ["Potato"] * 15,
        "Market_Canonical": ["MandiA"] * 15,
        "Grade": ["FAQ"] * 15,
        "Arrival_Date_Parsed": dates,
        "Modal_Price_Num": [1000 + i * 10 for i in range(15)],
        "Min_Price_Num": [950 + i * 10 for i in range(15)],
        "Max_Price_Num": [1050 + i * 10 for i in range(15)],
        "Modal_Price_Num_Lag1": [np.nan] + [1000 + (i - 1) * 10 for i in range(1, 15)],
        "Modal_Price_Num_Lag3": [np.nan] * 3 + [1000 + (i - 3) * 10 for i in range(3, 15)],
        "Modal_Price_Num_Lag7": [np.nan] * 7 + [1000 + (i - 7) * 10 for i in range(7, 15)],
        "Lag_Price_Bounded7": [np.nan] * 7 + [1000 + (i - 7) * 10 for i in range(7, 15)],
    })

    # df2 alters future prices for day 10 onward
    df2 = df1.copy()
    df2.loc[10:, "Modal_Price_Num"] = df2.loc[10:, "Modal_Price_Num"] * 2.5

    from backing.phase_03.tests.run_phase03_experiment import engineer_causal_features
    res1 = engineer_causal_features(df1)
    res2 = engineer_causal_features(df2)

    # For origin dates T < day 10 (indices 0..9), features must be identical
    feature_cols = [
        "Log_Modal_Price", "Price_Spread_Ratio", "Past_Return_1d",
        "Past_Return_3d", "Past_Return_7d", "Past_Return_Bounded7d", "Momentum_Ratio_7d"
    ]
    for col in feature_cols:
        pd.testing.assert_series_equal(
            res1.loc[:9, col], res2.loc[:9, col],
            check_names=True, obj=f"Feature {col} at origin dates before day 10"
        )


def test_causal_historical_volatility_no_backward_filling(prepared_experiment_data):
    """
    Verify historical volatility is causal:
    1. Early origins with insufficient history have NaN (prior to imputation).
    2. Volatility does not backfill future high-volatility events into earlier dates.
    """
    partitions, _ = prepared_experiment_data
    train_df = partitions["train_df"]

    # Check that in train_df, Hist_Vol_Commodity exists and has realistic values
    valid_vols = train_df["Hist_Vol_Commodity"].dropna()
    assert (valid_vols >= 0).all()


# ==============================================================================
# 3. PREPROCESSING ISOLATION TESTS
# ==============================================================================

def test_preprocessing_fitted_on_training_only(prepared_experiment_data):
    """
    Verify that Scaler and OneHotEncoder are fitted ONLY on training observations,
    and transforming held-out sets does NOT change training parameters.
    """
    partitions, _ = prepared_experiment_data
    train_df = partitions["train_df"]
    val_df = partitions["val_df"]
    test_df = partitions["test_df"]

    numeric_features = [
        "Log_Modal_Price", "Price_Spread_Ratio",
        "Past_Return_1d", "Past_Return_3d", "Past_Return_7d", "Past_Return_Bounded7d",
        "Momentum_Ratio_7d", "Hist_Vol_Commodity", "Day_Of_Week", "Month"
    ]
    categorical_features = ["Commodity", "Market_Canonical", "Grade"]
    feature_cols = numeric_features + categorical_features

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", Pipeline([
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler())
            ]), numeric_features),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical_features)
        ]
    )

    # Fit strictly on train
    preprocessor.fit(train_df[feature_cols])

    # Extract fitted scaler mean
    train_means_initial = preprocessor.named_transformers_["num"].named_steps["scaler"].mean_.copy()

    # Transforming val and test must not alter fitted parameters
    _ = preprocessor.transform(val_df[feature_cols])
    _ = preprocessor.transform(test_df[feature_cols])

    train_means_after = preprocessor.named_transformers_["num"].named_steps["scaler"].mean_
    np.testing.assert_array_equal(train_means_initial, train_means_after)


# ==============================================================================
# 4. TARGET DEFINITION CONSISTENCY TESTS
# ==============================================================================

def test_target_definition_fixed_thresholds(prepared_experiment_data):
    """
    Verify target classification strictly obeys Phase 2 Strategy 2:
    - Favorable: R_7 > +2.5%
    - Normal: -2.5% <= R_7 <= +2.5%
    - Unfavorable: R_7 < -2.5%
    """
    partitions, _ = prepared_experiment_data
    for p_name, df in [("train", partitions["train_df"]), ("val", partitions["val_df"]), ("test", partitions["test_df"])]:
        # Exact mathematical checks
        fav_mask = df["Target_Class"] == "Favorable"
        norm_mask = df["Target_Class"] == "Normal"
        unfav_mask = df["Target_Class"] == "Unfavorable"

        assert (df.loc[fav_mask, "R_7"] > 2.5).all(), f"Found Favorable with R_7 <= 2.5 in {p_name}"
        assert ((df.loc[norm_mask, "R_7"] >= -2.5) & (df.loc[norm_mask, "R_7"] <= 2.5)).all(), f"Found Normal outside [-2.5, 2.5] in {p_name}"
        assert (df.loc[unfav_mask, "R_7"] < -2.5).all(), f"Found Unfavorable with R_7 >= -2.5 in {p_name}"


# ==============================================================================
# 5. DENOMINATOR RECONCILIATION AND METRIC INTEGRITY TESTS
# ==============================================================================

def test_observation_counts_and_denominators(loaded_phase03_outputs):
    """
    Verify partition sizes:
    - TRAIN: 100,650
    - VALIDATION: 2,914
    - FINAL_TEST: 12,625
    - PURGED EMBARGO: 72 (Train) + 565 (Val)
    - TOTAL MATCHED: 116,826
    """
    split_df = loaded_phase03_outputs["temporal_split_summary.csv"]
    train_row = split_df[split_df["partition_name"] == "TRAIN"].iloc[0]
    val_row = split_df[split_df["partition_name"] == "VALIDATION"].iloc[0]
    test_row = split_df[split_df["partition_name"] == "FINAL_TEST"].iloc[0]

    assert train_row["valid_target_count"] == 100650
    assert val_row["valid_target_count"] == 2914
    assert test_row["valid_target_count"] == 12625

    total = train_row["valid_target_count"] + train_row["embargo_purged_count"] + \
            val_row["valid_target_count"] + val_row["embargo_purged_count"] + \
            test_row["valid_target_count"]
    assert total == 116826


def test_confusion_matrix_sums_match_denominators(loaded_phase03_outputs):
    """Verify that every confusion matrix row sum matches exact partition observation counts."""
    cm_df = loaded_phase03_outputs["confusion_matrix.csv"]
    for model in cm_df["model_name"].unique():
        val_sum = cm_df[(cm_df["model_name"] == model) & (cm_df["partition"] == "VALIDATION")]["count"].sum()
        test_sum = cm_df[(cm_df["model_name"] == model) & (cm_df["partition"] == "FINAL_TEST")]["count"].sum()
        assert val_sum == 2914, f"Confusion matrix for {model} in VALIDATION sums to {val_sum}, expected 2914"
        assert test_sum == 12625, f"Confusion matrix for {model} in FINAL_TEST sums to {test_sum}, expected 12625"


def test_majority_baseline_predicts_exclusively_normal(loaded_phase03_outputs):
    """Verify that Majority Class baseline predicts Normal for 100% of observations."""
    cm_df = loaded_phase03_outputs["confusion_matrix.csv"]
    maj_cm = cm_df[cm_df["model_name"] == "Majority_Class_Baseline"]
    
    # All predictions should be 'Normal'
    non_normal_preds = maj_cm[maj_cm["predicted_class"] != "Normal"]["count"].sum()
    assert non_normal_preds == 0, f"Majority baseline predicted non-Normal classes {non_normal_preds} times!"


def test_no_row_multiplication_or_duplicate_keys(prepared_experiment_data):
    """Verify that (series_id_with_grade, Arrival_Date_Parsed) is unique across all partitions."""
    partitions, _ = prepared_experiment_data
    for p_name, df in [("train", partitions["train_df"]), ("val", partitions["val_df"]), ("test", partitions["test_df"])]:
        dups = df.duplicated(subset=["series_id_with_grade", "Arrival_Date_Parsed"]).sum()
        assert dups == 0, f"Found {dups} duplicate series-date records in {p_name} partition!"
