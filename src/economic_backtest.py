"""
Economic Backtest and Policy Evaluation Engine
APMC Mandi Market Intelligence System - Phase 4

Executes leakage-safe chronological backtesting of 5 sell-versus-store policies:
  A. Always Sell Immediately (Baseline)
  B. Always Store for 7 Days
  C. Simple Price-Trend Policy (Information available at T)
  D. Model-Signal Policy (LightGBM/GB Classifier signal at T)
  E. Oracle Hindsight Benchmark (Theoretical Upper Bound)

Evaluates performance across Conservative, Central, and Optimistic scenarios
on both Validation and Exploratory Historical Test partitions.
"""

import os
import sys
import numpy as np
import pandas as pd
from typing import Dict, List, Any

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.economic_model import (
    EconomicParameters,
    get_default_scenarios,
    generate_sensitivity_matrix,
    generate_sensitivity_matrix_with_quality_discount,
    evaluate_sell_vs_store,
    calculate_break_even_future_price,
    calculate_incremental_benefit_per_quintal,
)
from src.data_loader import load_and_clean_mandi_data
from src.feature_engineering import build_features_and_target, FEATURE_COLUMNS
from src.evaluate import chronological_split
from sklearn.ensemble import GradientBoostingClassifier


def train_baseline_classifier_for_economic_policy(train_df: pd.DataFrame, val_df: pd.DataFrame):
    """
    Train a gradient boosting classifier strictly on the Training partition
    without access to validation or exploratory test data.
    """
    # Feature matrix and targets
    X_train = train_df[FEATURE_COLUMNS].fillna(0.0)
    y_train = train_df['Target_Class']

    clf = GradientBoostingClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.05,
        random_state=42
    )
    clf.fit(X_train, y_train)
    return clf


def run_economic_backtest(
    data_df: pd.DataFrame,
    predictions: np.ndarray,
    scenario: EconomicParameters,
    quantity_per_decision: float = 10.0
) -> Dict[str, Any]:
    """
    Evaluate all 5 decision policies on a given dataset partition under a specific scenario.

    Reports:
      - Unconditional mean incremental return per eligible quintal (SELL decisions contribute 0.0)
      - Mean incremental gain per 10-quintal eligible decision
      - Conditional mean incremental return per stored quintal (only over STORE decisions)
      - Mean incremental gain per 10-quintal stored decision
      - Aggregate net incremental gain across all eligible decisions (each 10 quintals)
      - Storage win rate (percentage of stored decisions where incremental benefit > 0)
    """
    n = len(data_df)
    p_t = data_df['Modal_Price'].values
    p_t7 = data_df['Modal_Price_T7'].values
    # 7-day momentum at T
    p_change_7d = data_df['Price_Change_7d'].fillna(0.0).values

    # Storage benefit per quintal for storing (canonical formula strictly shared with economic_model)
    delta_r_per_qtl = calculate_incremental_benefit_per_quintal(p_t, p_t7, scenario)
    actual_store_won = delta_r_per_qtl > 0.0

    # Required percentage increase to break even for each row (canonical formula)
    be_res = calculate_break_even_future_price(p_t, scenario)
    req_pct_increase = be_res["required_percentage_increase"]

    # Policy Decisions (1 = STORE, 0 = SELL):
    # A. Always Sell
    dec_always_sell = np.zeros(n, dtype=int)

    # B. Always Store
    dec_always_store = np.ones(n, dtype=int)

    # C. Trend Policy: Store if recent 7-day momentum is positive and exceeds break-even threshold
    dec_trend = (p_change_7d > req_pct_increase).astype(int)

    # D. Model-Signal Policy: Store if model predicts Favorable (class 2)
    dec_model = (predictions == 2).astype(int)

    # E. Oracle Hindsight Benchmark (Upper Bound)
    dec_oracle = actual_store_won.astype(int)

    policies = {
        "Always Sell": dec_always_sell,
        "Always Store": dec_always_store,
        "Trend Momentum (T)": dec_trend,
        "Model Signal (T)": dec_model,
        "Oracle Benchmark (Upper Bound)": dec_oracle
    }

    policy_results = {}
    for pol_name, dec in policies.items():
        n_stored = int(np.sum(dec))
        pct_stored = (n_stored / n) * 100.0 if n > 0 else 0.0

        # Unconditional return per eligible quintal (SELL decisions contribute 0.0)
        # Denominator: n (Eligible_Decisions)
        realized_delta_per_qtl = dec * delta_r_per_qtl
        mean_return_eligible_qtl = float(np.mean(realized_delta_per_qtl)) if n > 0 else 0.0
        mean_gain_10qtl_eligible = mean_return_eligible_qtl * quantity_per_decision

        # Conditional return per stored quintal (calculated strictly over STORE decisions)
        # Denominator: n_stored (Times_Stored)
        stored_outcomes = delta_r_per_qtl[dec == 1]
        if n_stored > 0:
            mean_return_stored_qtl = float(np.mean(stored_outcomes))
            mean_gain_10qtl_stored = mean_return_stored_qtl * quantity_per_decision
            success_rate = (np.sum(stored_outcomes > 0.0) / n_stored) * 100.0
            p05_stored = float(np.percentile(stored_outcomes, 5))
            min_stored = float(np.min(stored_outcomes))
        else:
            mean_return_stored_qtl = 0.0
            mean_gain_10qtl_stored = 0.0
            success_rate = 0.0
            p05_stored = 0.0
            min_stored = 0.0

        # Aggregate net incremental gain across all eligible decisions (each 10 quintals)
        # Formula: sum(dec * delta_r_per_qtl * 10) == n * mean_gain_10qtl_eligible
        aggregate_net_gain_10qtl_all = float(np.sum(realized_delta_per_qtl * quantity_per_decision))

        policy_results[pol_name] = {
            "decisions_evaluated": n,
            "times_stored": n_stored,
            "percent_stored": round(pct_stored, 2),
            "storage_win_rate_percent": round(success_rate, 2),
            "mean_incremental_return_rupees_per_eligible_qtl": round(mean_return_eligible_qtl, 2),
            "mean_incremental_gain_rupees_10qtl_per_eligible_decision": round(mean_gain_10qtl_eligible, 2),
            "mean_incremental_return_rupees_per_stored_qtl": round(mean_return_stored_qtl, 2),
            "mean_incremental_gain_rupees_10qtl_per_stored_decision": round(mean_gain_10qtl_stored, 2),
            "aggregate_net_incremental_gain_rupees_10qtl_all_decisions": round(aggregate_net_gain_10qtl_all, 2),
            "worst_case_per_quintal_rupees": round(min_stored, 2),
            "5th_percentile_per_quintal_rupees": round(p05_stored, 2)
        }

    return policy_results


def run_full_economic_study(output_dir: str = "backing/phase_04"):
    """
    Run complete Phase 4 economic decision support analysis across scenarios and partitions.
    """
    print("\n" + "=" * 80)
    print("APMC MANDI MARKET INTELLIGENCE SYSTEM: PHASE 4 ECONOMIC VALIDATION")
    print("Sell-versus-Store Decision Support Layer")
    print("=" * 80 + "\n")

    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, "outputs"), exist_ok=True)

    # 1. Generate Sensitivity Matrices
    print("[1/5] Generating Theoretical Sensitivity Matrices...")
    sensitivity_records = generate_sensitivity_matrix()
    sens_df = pd.DataFrame(sensitivity_records)
    sens_path = os.path.join(output_dir, "economic_sensitivity.csv")
    sens_df.to_csv(sens_path, index=False)
    print(f"  -> Saved {len(sens_df)} baseline sensitivity records (d_q=0.0) to {sens_path}")

    sens_dq_records = generate_sensitivity_matrix_with_quality_discount()
    sens_dq_df = pd.DataFrame(sens_dq_records)
    sens_dq_path = os.path.join(output_dir, "economic_sensitivity_quality_discount.csv")
    sens_dq_df.to_csv(sens_dq_path, index=False)
    print(f"  -> Saved {len(sens_dq_df)} quality-discount sensitivity records to {sens_dq_path}")

    # 2. Ingest Data and Build Features
    print("\n[2/5] Ingesting Mandi Dataset & Engineering Features...")
    clean_df = load_and_clean_mandi_data(data_dir=PROJECT_ROOT, min_series_records=20)
    feature_df = build_features_and_target(clean_df, threshold_pct=2.5)

    # 3. Partition Chronologically with Embargo Buffers
    print("\n[3/5] Partitioning Chronologically with 8-Day Embargo Buffers...")
    train_df, val_df, test_df = chronological_split(
        feature_df, train_ratio=0.70, val_ratio=0.15, horizon_days=7
    )
    print(f"  -> Train partition: {len(train_df):,} records ({train_df['Arrival_Date'].min().strftime('%Y-%m-%d')} to {train_df['Arrival_Date'].max().strftime('%Y-%m-%d')})")
    print(f"  -> Validation partition: {len(val_df):,} records ({val_df['Arrival_Date'].min().strftime('%Y-%m-%d')} to {val_df['Arrival_Date'].max().strftime('%Y-%m-%d')})")
    print(f"  -> Exploratory Test partition: {len(test_df):,} records ({test_df['Arrival_Date'].min().strftime('%Y-%m-%d')} to {test_df['Arrival_Date'].max().strftime('%Y-%m-%d')})")

    # 4. Train Validated Classifier on Train Partition Only
    print("\n[4/5] Training Baseline Classifier on Training Partition Only...")
    clf = train_baseline_classifier_for_economic_policy(train_df, val_df)

    # Generate predictions strictly out-of-sample
    val_X = val_df[FEATURE_COLUMNS].fillna(0.0)
    val_preds = clf.predict(val_X)

    test_X = test_df[FEATURE_COLUMNS].fillna(0.0)
    test_preds = clf.predict(test_X)

    # 5. Execute Economic Backtest across Scenarios
    print("\n[5/5] Executing Policy Comparisons Across Scenarios...")
    scenarios = get_default_scenarios()
    comparison_records = []

    partitions = {
        "VALIDATION": (val_df, val_preds),
        "EXPLORATORY_TEST": (test_df, test_preds)
    }

    for part_name, (df_part, part_preds) in partitions.items():
        for sc_name, sc_params in scenarios.items():
            res = run_economic_backtest(df_part, part_preds, sc_params)
            for pol_name, stats in res.items():
                record = {
                    "Partition": part_name,
                    "Scenario": sc_name,
                    "Policy": pol_name,
                    "Eligible_Decisions": stats["decisions_evaluated"],
                    "Times_Stored": stats["times_stored"],
                    "Percent_Stored": stats["percent_stored"],
                    "Storage_Win_Rate_Percent": stats["storage_win_rate_percent"],
                    "Mean_Incremental_Return_Rupees_Per_Eligible_Qtl": stats["mean_incremental_return_rupees_per_eligible_qtl"],
                    "Mean_Incremental_Gain_Rupees_10Qtl_Per_Eligible_Decision": stats["mean_incremental_gain_rupees_10qtl_per_eligible_decision"],
                    "Mean_Incremental_Return_Rupees_Per_Stored_Qtl": stats["mean_incremental_return_rupees_per_stored_qtl"],
                    "Mean_Incremental_Gain_Rupees_10Qtl_Per_Stored_Decision": stats["mean_incremental_gain_rupees_10qtl_per_stored_decision"],
                    "Aggregate_Net_Incremental_Gain_Rupees_10Qtl_All_Decisions": stats["aggregate_net_incremental_gain_rupees_10qtl_all_decisions"],
                    "Worst_Case_Per_Qtl_Rupees": stats["worst_case_per_quintal_rupees"],
                    "P05_Per_Qtl_Rupees": stats["5th_percentile_per_quintal_rupees"]
                }
                comparison_records.append(record)

    comp_df = pd.DataFrame(comparison_records)
    comp_path = os.path.join(output_dir, "strategy_comparison.csv")
    comp_df.to_csv(comp_path, index=False)
    print(f"  -> Saved strategy comparison table to {comp_path}")

    # Commodity-level breakdown on Exploratory Test under Central scenario
    central_scenario = scenarios["Central"]
    comm_records = []
    top_commodities = ["Wheat", "Potato", "Onion", "Tomato", "Rice"]
    for comm in top_commodities:
        sub_test = test_df[test_df['Commodity'] == comm]
        if len(sub_test) == 0:
            continue
        # Match test_preds indexing
        test_df_reset = test_df.reset_index(drop=True)
        sub_mask = (test_df_reset['Commodity'] == comm).values
        sub_preds = test_preds[sub_mask]
        sub_res = run_economic_backtest(sub_test, sub_preds, central_scenario)

        for pol_name, stats in sub_res.items():
            comm_records.append({
                "Commodity": comm,
                "Policy": pol_name,
                "Sample_Count": stats["decisions_evaluated"],
                "Times_Stored": stats["times_stored"],
                "Storage_Win_Rate_Percent": stats["storage_win_rate_percent"],
                "Mean_Incremental_Return_Rupees_Per_Eligible_Qtl": stats["mean_incremental_return_rupees_per_eligible_qtl"],
                "Mean_Incremental_Return_Rupees_Per_Stored_Qtl": stats["mean_incremental_return_rupees_per_stored_qtl"],
                "P05_Per_Qtl_Rupees": stats["5th_percentile_per_quintal_rupees"]
            })
    comm_df = pd.DataFrame(comm_records)
    comm_path = os.path.join(output_dir, "commodity_economic_breakdown.csv")
    comm_df.to_csv(comm_path, index=False)
    print(f"  -> Saved commodity breakdown to {comm_path}")

    print("\n>>> Phase 4 Economic Backtest Execution Completed Successfully! <<<\n")
    return comp_df, sens_df, comm_df


if __name__ == "__main__":
    run_full_economic_study()
