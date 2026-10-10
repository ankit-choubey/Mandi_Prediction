"""
Phase 3: Leakage-Safe Baseline Modeling and Temporal Evaluation.

This script executes the complete Phase 3 baseline modeling experiment:
1. Ingests raw mandi price series and applies Phase 2 Strategy 2 clean dataset rules
   (dropping ambiguous same-grade series-date duplicates, preserving Grade and canonical markets).
2. Generates strictly causal features available at origin date T (T-1, T-3, T-7, Bounded T-7 lags,
   causal historical volatility per commodity with min_periods=10 and zero future backfilling).
3. Constructs exact T+7 calendar-matched forward price return targets R_7.
4. Partitions data chronologically with horizon-aware embargo purging:
   - Train: Origin <= 2026-01-17 (Target Realization <= 2026-01-24)
   - Train Embargo: Origins 2026-01-18 to 2026-01-24 (Purged)
   - Validation: Origins 2026-01-25 to 2026-03-31 (Target Realization <= 2026-04-07)
   - Val Embargo: Origins 2026-04-01 to 2026-04-07 (Purged)
   - Final Test: Origins 2026-04-08 to 2026-08-25 (Untouched Holdout)
5. Fits preprocessing (imputation, scaling, one-hot encoding) strictly on the Training set.
6. Evaluates:
   - Baselines: Majority Class, Historical Class Frequency, Momentum Rule, Persistence.
   - Interpretable ML: Logistic Regression, Decision Tree, Random Forest, LightGBM.
   - Secondary Regression: Zero-Return Persistence, Mean-Return Baseline, Ridge, LightGBM.
7. Produces all required audit CSVs, execution logs, and metric comparisons.
"""

import os
import sys
import glob
import logging
import warnings
from datetime import timedelta
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, f1_score,
    precision_recall_fscore_support, confusion_matrix,
    mean_absolute_error, root_mean_squared_error
)
import lightgbm as lgb

DEFAULT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))


def classify_fixed_threshold(r):
    """
    Phase 2 Agreed Convention:
    Favorable: return > +2.5%
    Normal: -2.5% <= return <= +2.5%
    Unfavorable: return < -2.5%
    """
    if pd.isna(r):
        return np.nan
    if r > 2.5:
        return 'Favorable'
    elif r < -2.5:
        return 'Unfavorable'
    else:
        return 'Normal'


def ingest_and_filter_strategy2(master_csv_path_or_root, canonical_mapping_path=None):
    """
    Ingests mandi data and applies Phase 2 Strategy 2:
    - Normalizes District names.
    - Applies approved canonical market mappings.
    - Excludes ambiguous same-grade series-date duplicates (Categories B and C).
    - Drops exact duplicate rows (Category A).
    - Preserves separate Grade dimensions.
    """
    if os.path.isdir(master_csv_path_or_root):
        raw_files = sorted(glob.glob(os.path.join(master_csv_path_or_root, "data", "raw", "*.csv")))
        dfs = [pd.read_csv(f) for f in raw_files]
        raw_df = pd.concat(dfs, ignore_index=True)
    elif os.path.isfile(master_csv_path_or_root):
        raw_df = pd.read_csv(master_csv_path_or_root)
    else:
        raise FileNotFoundError(f"Cannot find input data at {master_csv_path_or_root}")

    if canonical_mapping_path is None:
        canonical_mapping_path = os.path.join(
            DEFAULT_ROOT, "backing", "phase_02", "outputs", "canonical_market_mapping.csv"
        )

    raw_df['Arrival_Date_Parsed'] = pd.to_datetime(raw_df['Arrival_Date'], format='%d/%m/%Y', errors='coerce')
    if raw_df['Arrival_Date_Parsed'].isna().sum() > len(raw_df) * 0.5:
        raw_df['Arrival_Date_Parsed'] = pd.to_datetime(raw_df['Arrival_Date'], errors='coerce')

    raw_df['Modal_Price_Num'] = pd.to_numeric(raw_df['Modal_Price'], errors='coerce')
    raw_df['Min_Price_Num'] = pd.to_numeric(raw_df['Min_Price'], errors='coerce')
    raw_df['Max_Price_Num'] = pd.to_numeric(raw_df['Max_Price'], errors='coerce')

    raw_df['District'] = raw_df['District'].astype(str).str.strip()
    raw_df['District_Normalized'] = raw_df['District'].replace({'Gaziabaad': 'Ghaziabad', 'Lukhnow': 'Lucknow'})
    raw_df['Market'] = raw_df['Market'].astype(str).str.strip()
    raw_df['Commodity'] = raw_df['Commodity'].astype(str).str.strip()
    raw_df['Variety'] = raw_df['Variety'].astype(str).str.strip()
    raw_df['Grade'] = raw_df['Grade'].astype(str).str.strip()

    # Apply canonical market mapping safeguards from Phase 2
    can_df = pd.read_csv(canonical_mapping_path)
    approved_mappings = can_df[can_df['mapping_status'] == 'APPROVED']
    can_map = dict(zip(approved_mappings['raw_market_name'], approved_mappings['proposed_canonical_name']))
    raw_df['Market_Canonical'] = raw_df['Market'].map(lambda m: can_map.get(m, m))

    # Apply Strategy 2: Exclude ambiguous same-grade series-date groups
    key_grade = ['District_Normalized', 'Market', 'Commodity', 'Variety', 'Grade', 'Arrival_Date_Parsed']
    g_grade = raw_df.groupby(key_grade).agg(
        n_rows=('Modal_Price_Num', 'count'),
        modal_nunique=('Modal_Price_Num', 'nunique'),
        min_nunique=('Min_Price_Num', 'nunique'),
        max_nunique=('Max_Price_Num', 'nunique')
    )
    dups_grade = g_grade[g_grade['n_rows'] > 1]
    cat_b = dups_grade[dups_grade['modal_nunique'] > 1]
    cat_c = dups_grade[(dups_grade['modal_nunique'] == 1) & ((dups_grade['min_nunique'] > 1) | (dups_grade['max_nunique'] > 1))]
    ambiguous_keys = set(cat_b.index).union(set(cat_c.index))

    clean_s2 = raw_df[~raw_df.set_index(key_grade).index.isin(ambiguous_keys)].drop_duplicates(subset=key_grade).copy()

    clean_s2['series_id_with_grade'] = (
        clean_s2['District_Normalized'] + "__" +
        clean_s2['Market'] + "__" +
        clean_s2['Commodity'] + "__" +
        clean_s2['Variety'] + "__" +
        clean_s2['Grade']
    )
    clean_s2.sort_values(by=['series_id_with_grade', 'Arrival_Date_Parsed'], inplace=True)
    clean_s2.reset_index(drop=True, inplace=True)
    return clean_s2


def engineer_causal_features(df):
    """
    Computes strictly causal features available at prediction origin date T.
    No future data (T+1 or later) is ever used.
    """
    clean_s2 = df.copy()
    if 'Arrival_Date_Parsed' not in clean_s2.columns or not pd.api.types.is_datetime64_any_dtype(clean_s2['Arrival_Date_Parsed']):
        clean_s2['Arrival_Date_Parsed'] = pd.to_datetime(clean_s2['Arrival_Date_Parsed'])

    if 'series_id_with_grade' not in clean_s2.columns:
        clean_s2['series_id_with_grade'] = (
            clean_s2['District'].astype(str) + "__" +
            clean_s2['Market'].astype(str) + "__" +
            clean_s2['Commodity'].astype(str) + "__" +
            clean_s2['Variety'].astype(str) + "__" +
            clean_s2['Grade'].astype(str)
        )

    # Check if lags already present; if not, merge them
    needed_lags = [1, 3, 7, 8, 9]
    missing_lags = [k for k in needed_lags if f'Modal_Price_Num_Lag{k}' not in clean_s2.columns]

    if missing_lags:
        lookup_table = clean_s2[['series_id_with_grade', 'Arrival_Date_Parsed', 'Modal_Price_Num']].drop_duplicates()
        for k in missing_lags:
            clean_s2[f'Lag_Date_{k}'] = clean_s2['Arrival_Date_Parsed'] - timedelta(days=k)
            clean_s2 = pd.merge(
                clean_s2,
                lookup_table,
                left_on=['series_id_with_grade', f'Lag_Date_{k}'],
                right_on=['series_id_with_grade', 'Arrival_Date_Parsed'],
                suffixes=('', f'_Lag{k}'),
                how='left'
            )
            if f'Lag_Date_{k}' in clean_s2.columns:
                clean_s2.drop(columns=[f'Lag_Date_{k}'], inplace=True)
            if f'Arrival_Date_Parsed_Lag{k}' in clean_s2.columns:
                clean_s2.drop(columns=[f'Arrival_Date_Parsed_Lag{k}'], inplace=True)

    if 'Lag_Price_Bounded7' not in clean_s2.columns:
        clean_s2['Lag_Price_Bounded7'] = (
            clean_s2['Modal_Price_Num_Lag7']
            .combine_first(clean_s2.get('Modal_Price_Num_Lag8', pd.Series(np.nan, index=clean_s2.index)))
            .combine_first(clean_s2.get('Modal_Price_Num_Lag9', pd.Series(np.nan, index=clean_s2.index)))
        )

    # Predictor transformations:
    clean_s2['Log_Modal_Price'] = np.log(clean_s2['Modal_Price_Num'].clip(lower=1.0))
    clean_s2['Price_Spread_Ratio'] = (clean_s2['Max_Price_Num'] - clean_s2['Min_Price_Num']) / clean_s2['Modal_Price_Num'].clip(lower=1.0)
    clean_s2['Past_Return_1d'] = (((clean_s2['Modal_Price_Num'] - clean_s2['Modal_Price_Num_Lag1']) / clean_s2['Modal_Price_Num_Lag1'].clip(lower=1.0)) * 100.0).clip(-100.0, 300.0)
    clean_s2['Past_Return_3d'] = (((clean_s2['Modal_Price_Num'] - clean_s2['Modal_Price_Num_Lag3']) / clean_s2['Modal_Price_Num_Lag3'].clip(lower=1.0)) * 100.0).clip(-100.0, 300.0)
    clean_s2['Past_Return_7d'] = (((clean_s2['Modal_Price_Num'] - clean_s2['Modal_Price_Num_Lag7']) / clean_s2['Modal_Price_Num_Lag7'].clip(lower=1.0)) * 100.0).clip(-100.0, 300.0)
    clean_s2['Past_Return_Bounded7d'] = (((clean_s2['Modal_Price_Num'] - clean_s2['Lag_Price_Bounded7']) / clean_s2['Lag_Price_Bounded7'].clip(lower=1.0)) * 100.0).clip(-100.0, 300.0)
    clean_s2['Momentum_Ratio_7d'] = (clean_s2['Modal_Price_Num'] / clean_s2['Lag_Price_Bounded7'].clip(lower=1.0)).clip(0.1, 5.0)

    # Causal Historical Volatility per Commodity (min_periods=10, NO bfill)
    comm_daily = clean_s2.groupby(['Commodity', 'Arrival_Date_Parsed'])['Modal_Price_Num'].mean().reset_index()
    comm_daily.sort_values(by=['Commodity', 'Arrival_Date_Parsed'], inplace=True)
    comm_daily['daily_return'] = comm_daily.groupby('Commodity')['Modal_Price_Num'].pct_change() * 100.0
    comm_daily['hist_vol_T'] = comm_daily.groupby('Commodity')['daily_return'].transform(
        lambda s: s.expanding(min_periods=10).std()
    )
    comm_daily['hist_vol_T'] = comm_daily.groupby('Commodity')['hist_vol_T'].ffill()
    vol_lookup = comm_daily.set_index(['Commodity', 'Arrival_Date_Parsed'])['hist_vol_T'].to_dict()
    clean_s2['Hist_Vol_Commodity'] = [vol_lookup.get((c, d), np.nan) for c, d in zip(clean_s2['Commodity'], clean_s2['Arrival_Date_Parsed'])]

    # Calendar Seasonality
    clean_s2['Day_Of_Week'] = clean_s2['Arrival_Date_Parsed'].dt.dayofweek
    clean_s2['Month'] = clean_s2['Arrival_Date_Parsed'].dt.month

    return clean_s2


def match_targets_and_partition(clean_s2):
    """
    Matches exact T+7 calendar-day targets and partitions chronologically with horizon embargo.
    """
    clean_s2['Target_Date_T7'] = clean_s2['Arrival_Date_Parsed'] + timedelta(days=7)
    lookup_table = clean_s2[['series_id_with_grade', 'Arrival_Date_Parsed', 'Modal_Price_Num']].drop_duplicates()

    m_target = pd.merge(
        clean_s2,
        lookup_table,
        left_on=['series_id_with_grade', 'Target_Date_T7'],
        right_on=['series_id_with_grade', 'Arrival_Date_Parsed'],
        suffixes=('', '_Target7'),
        how='inner'
    )
    valid_targets = m_target[(m_target['Modal_Price_Num'] > 0) & (m_target['Modal_Price_Num_Target7'] > 0)].copy()
    valid_targets['R_7'] = ((valid_targets['Modal_Price_Num_Target7'] - valid_targets['Modal_Price_Num']) / valid_targets['Modal_Price_Num']) * 100.0
    valid_targets['Target_Class'] = valid_targets['R_7'].apply(classify_fixed_threshold)

    # Horizon-aware partitions:
    train_mask = valid_targets['Arrival_Date_Parsed'] <= pd.to_datetime('2026-01-17')
    train_embargo_mask = (valid_targets['Arrival_Date_Parsed'] > pd.to_datetime('2026-01-17')) & (valid_targets['Arrival_Date_Parsed'] <= pd.to_datetime('2026-01-24'))

    val_mask = (valid_targets['Arrival_Date_Parsed'] >= pd.to_datetime('2026-01-25')) & (valid_targets['Arrival_Date_Parsed'] <= pd.to_datetime('2026-03-31'))
    val_embargo_mask = (valid_targets['Arrival_Date_Parsed'] > pd.to_datetime('2026-03-31')) & (valid_targets['Arrival_Date_Parsed'] <= pd.to_datetime('2026-04-07'))

    test_mask = (valid_targets['Arrival_Date_Parsed'] >= pd.to_datetime('2026-04-08')) & (valid_targets['Arrival_Date_Parsed'] <= pd.to_datetime('2026-08-25'))

    train_df = valid_targets[train_mask].copy()
    val_df = valid_targets[val_mask].copy()
    test_df = valid_targets[test_mask].copy()

    n_train = len(train_df)
    n_train_embargo = int(train_embargo_mask.sum())
    n_val = len(val_df)
    n_val_embargo = int(val_embargo_mask.sum())
    n_test = len(test_df)

    split_summary_rows = [
        {
            'partition_name': 'TRAIN',
            'start_date': '2024-09-01',
            'end_date': '2026-01-17',
            'target_realization_start': '2024-09-08',
            'target_realization_end': '2026-01-24',
            'eligible_origins': int((clean_s2['Arrival_Date_Parsed'] <= pd.to_datetime('2026-01-17')).sum()),
            'valid_target_count': n_train,
            'normal_count': int((train_df['Target_Class'] == 'Normal').sum()),
            'normal_pct': round((train_df['Target_Class'] == 'Normal').mean() * 100, 2),
            'favorable_count': int((train_df['Target_Class'] == 'Favorable').sum()),
            'favorable_pct': round((train_df['Target_Class'] == 'Favorable').mean() * 100, 2),
            'unfavorable_count': int((train_df['Target_Class'] == 'Unfavorable').sum()),
            'unfavorable_pct': round((train_df['Target_Class'] == 'Unfavorable').mean() * 100, 2),
            'boundary_truncated_count': 0,
            'embargo_purged_count': n_train_embargo
        },
        {
            'partition_name': 'VALIDATION',
            'start_date': '2026-01-25',
            'end_date': '2026-03-31',
            'target_realization_start': '2026-02-01',
            'target_realization_end': '2026-04-07',
            'eligible_origins': int(((clean_s2['Arrival_Date_Parsed'] >= pd.to_datetime('2026-01-25')) & (clean_s2['Arrival_Date_Parsed'] <= pd.to_datetime('2026-03-31'))).sum()),
            'valid_target_count': n_val,
            'normal_count': int((val_df['Target_Class'] == 'Normal').sum()),
            'normal_pct': round((val_df['Target_Class'] == 'Normal').mean() * 100, 2),
            'favorable_count': int((val_df['Target_Class'] == 'Favorable').sum()),
            'favorable_pct': round((val_df['Target_Class'] == 'Favorable').mean() * 100, 2),
            'unfavorable_count': int((val_df['Target_Class'] == 'Unfavorable').sum()),
            'unfavorable_pct': round((val_df['Target_Class'] == 'Unfavorable').mean() * 100, 2),
            'boundary_truncated_count': 0,
            'embargo_purged_count': n_val_embargo
        },
        {
            'partition_name': 'FINAL_TEST',
            'start_date': '2026-04-08',
            'end_date': '2026-08-25',
            'target_realization_start': '2026-04-15',
            'target_realization_end': '2026-09-01',
            'eligible_origins': int(((clean_s2['Arrival_Date_Parsed'] >= pd.to_datetime('2026-04-08')) & (clean_s2['Arrival_Date_Parsed'] <= pd.to_datetime('2026-08-25'))).sum()),
            'valid_target_count': n_test,
            'normal_count': int((test_df['Target_Class'] == 'Normal').sum()),
            'normal_pct': round((test_df['Target_Class'] == 'Normal').mean() * 100, 2),
            'favorable_count': int((test_df['Target_Class'] == 'Favorable').sum()),
            'favorable_pct': round((test_df['Target_Class'] == 'Favorable').mean() * 100, 2),
            'unfavorable_count': int((test_df['Target_Class'] == 'Unfavorable').sum()),
            'unfavorable_pct': round((test_df['Target_Class'] == 'Unfavorable').mean() * 100, 2),
            'boundary_truncated_count': int((clean_s2['Arrival_Date_Parsed'] > pd.to_datetime('2026-08-25')).sum()),
            'embargo_purged_count': 0
        }
    ]

    partitions = {
        'train_df': train_df,
        'val_df': val_df,
        'test_df': test_df,
        'train_embargo_mask': train_embargo_mask,
        'val_embargo_mask': val_embargo_mask,
        'valid_targets': valid_targets
    }
    return partitions, pd.DataFrame(split_summary_rows)


def run_experiment(repo_root=None):
    if repo_root is None:
        repo_root = os.environ.get("MANDI_REPO_ROOT", DEFAULT_ROOT)
    ROOT_DIR = os.path.abspath(repo_root)

    CAN_PATH = os.path.join(ROOT_DIR, "backing", "phase_02", "outputs", "canonical_market_mapping.csv")
    OUT_DIR = os.path.join(ROOT_DIR, "backing", "phase_03", "outputs")
    LOG_DIR = os.path.join(ROOT_DIR, "backing", "phase_03", "logs")
    EVID_DIR = os.path.join(ROOT_DIR, "backing", "phase_03", "evidence")
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(EVID_DIR, exist_ok=True)

    log_file = os.path.join(LOG_DIR, "phase03_execution.log")

    logger = logging.getLogger("Phase03BaselineModeling")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    if logger.hasHandlers():
        logger.handlers.clear()

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(formatter)
    logger.addHandler(sh)

    fh = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    logger.info("================================================================================")
    logger.info("STARTING PHASE 3 LEAKAGE-SAFE BASELINE MODELING EXPERIMENT")
    logger.info(f"Repository Root: {ROOT_DIR}")
    logger.info(f"Target Output Directory: {OUT_DIR}")
    logger.info(f"Execution Log: {log_file}")
    logger.info("================================================================================")

    # 1. Ingest Raw Master Data & Apply Strategy 2 Clean Dataset
    clean_s2 = ingest_and_filter_strategy2(ROOT_DIR, CAN_PATH)
    logger.info(f"Retained {len(clean_s2):,} clean records under Strategy 2.")

    # 2. Compute Causal Predictors Available Strictly at Origin Date T
    logger.info("Computing strictly past-only lag features and predictors...")
    clean_s2 = engineer_causal_features(clean_s2)

    # Feature audit records
    feature_audit_rows = [
        {
            'feature_name': 'Log_Modal_Price',
            'mathematical_definition': 'ln(Modal_Price_Num)',
            'source_columns': 'Modal_Price_Num',
            'lookback_period': 'Current origin date T',
            'availability_time': 'At origin date T (published close of trading)',
            'missing_handling': 'No missing values in raw master data',
            'leakage_risk_assessment': 'ZERO LEAKAGE: Log transform of current observed price'
        },
        {
            'feature_name': 'Price_Spread_Ratio',
            'mathematical_definition': '(Max_Price_Num - Min_Price_Num) / Modal_Price_Num',
            'source_columns': 'Max_Price_Num, Min_Price_Num, Modal_Price_Num',
            'lookback_period': 'Current origin date T',
            'availability_time': 'At origin date T (published close of trading)',
            'missing_handling': 'No missing values in raw master data',
            'leakage_risk_assessment': 'ZERO LEAKAGE: Captures intraday dispersion strictly at T'
        },
        {
            'feature_name': 'Past_Return_1d',
            'mathematical_definition': '((P_T - P_{T-1}) / P_{T-1}) * 100',
            'source_columns': 'Modal_Price_Num, Modal_Price_Num_Lag1',
            'lookback_period': 'Exact T - 1 calendar day',
            'availability_time': 'At origin date T',
            'missing_handling': 'Imputed with median of training partition (27.0% missing due to closures)',
            'leakage_risk_assessment': 'ZERO LEAKAGE: Strictly past calendar date T-1'
        },
        {
            'feature_name': 'Past_Return_3d',
            'mathematical_definition': '((P_T - P_{T-3}) / P_{T-3}) * 100',
            'source_columns': 'Modal_Price_Num, Modal_Price_Num_Lag3',
            'lookback_period': 'Exact T - 3 calendar days',
            'availability_time': 'At origin date T',
            'missing_handling': 'Imputed with median of training partition (30.1% missing)',
            'leakage_risk_assessment': 'ZERO LEAKAGE: Strictly past calendar date T-3'
        },
        {
            'feature_name': 'Past_Return_7d',
            'mathematical_definition': '((P_T - P_{T-7}) / P_{T-7}) * 100',
            'source_columns': 'Modal_Price_Num, Modal_Price_Num_Lag7',
            'lookback_period': 'Exact T - 7 calendar days',
            'availability_time': 'At origin date T',
            'missing_handling': 'Imputed with median of training partition (25.8% missing)',
            'leakage_risk_assessment': 'ZERO LEAKAGE: Strictly past calendar date T-7'
        },
        {
            'feature_name': 'Past_Return_Bounded7d',
            'mathematical_definition': '((P_T - P_{Bounded7}) / P_{Bounded7}) * 100',
            'source_columns': 'Modal_Price_Num, Lag_Price_Bounded7 (T-7 fallback T-8 fallback T-9)',
            'lookback_period': 'T - 7 to T - 9 calendar days',
            'availability_time': 'At origin date T',
            'missing_handling': 'Imputed with median of training partition (12.9% missing)',
            'leakage_risk_assessment': 'ZERO LEAKAGE: Strictly past calendar dates <= 9 days old'
        },
        {
            'feature_name': 'Momentum_Ratio_7d',
            'mathematical_definition': 'P_T / P_{Bounded7}',
            'source_columns': 'Modal_Price_Num, Lag_Price_Bounded7',
            'lookback_period': 'T - 7 to T - 9 calendar days',
            'availability_time': 'At origin date T',
            'missing_handling': 'Imputed with median of training partition (12.9% missing)',
            'leakage_risk_assessment': 'ZERO LEAKAGE: Normalized price momentum ratio'
        },
        {
            'feature_name': 'Hist_Vol_Commodity',
            'mathematical_definition': 'Expanding standard deviation of daily commodity returns up to date T (min_periods=10)',
            'source_columns': 'Modal_Price_Num, Arrival_Date_Parsed, Commodity',
            'lookback_period': 'All dates <= origin date T',
            'availability_time': 'At origin date T',
            'missing_handling': 'Imputed with median of training partition for early burn-in origins',
            'leakage_risk_assessment': 'ZERO LEAKAGE: Phase 2 causal rule; zero future backward-filling'
        },
        {
            'feature_name': 'Day_Of_Week',
            'mathematical_definition': 'Integer day of week (0=Monday, ..., 6=Sunday)',
            'source_columns': 'Arrival_Date_Parsed',
            'lookback_period': 'Current origin date T',
            'availability_time': 'At origin date T',
            'missing_handling': 'Deterministic calendar feature (0 missing)',
            'leakage_risk_assessment': 'ZERO LEAKAGE: Exogenous calendar property'
        },
        {
            'feature_name': 'Month',
            'mathematical_definition': 'Integer month of year (1=Jan, ..., 12=Dec)',
            'source_columns': 'Arrival_Date_Parsed',
            'lookback_period': 'Current origin date T',
            'availability_time': 'At origin date T',
            'missing_handling': 'Deterministic calendar feature (0 missing)',
            'leakage_risk_assessment': 'ZERO LEAKAGE: Exogenous calendar seasonality property'
        },
        {
            'feature_name': 'Commodity',
            'mathematical_definition': 'Commercial commodity string (e.g., Potato, Onion, Wheat)',
            'source_columns': 'Commodity',
            'lookback_period': 'Static series attribute',
            'availability_time': 'At origin date T',
            'missing_handling': 'One-hot encoded (unseen categories ignored in test)',
            'leakage_risk_assessment': 'ZERO LEAKAGE: Static series metadata'
        },
        {
            'feature_name': 'Market_Canonical',
            'mathematical_definition': 'Approved unified canonical mandi name',
            'source_columns': 'Market, canonical_market_mapping.csv',
            'lookback_period': 'Static series attribute',
            'availability_time': 'At origin date T',
            'missing_handling': 'One-hot encoded',
            'leakage_risk_assessment': 'ZERO LEAKAGE: Static market yard identifier'
        },
        {
            'feature_name': 'Grade',
            'mathematical_definition': 'Commercial quality grade (FAQ, Medium, Non-FAQ, etc.)',
            'source_columns': 'Grade',
            'lookback_period': 'Static series attribute',
            'availability_time': 'At origin date T',
            'missing_handling': 'One-hot encoded',
            'leakage_risk_assessment': 'ZERO LEAKAGE: Physical commodity trade specification'
        }
    ]
    pd.DataFrame(feature_audit_rows).to_csv(os.path.join(OUT_DIR, "feature_audit.csv"), index=False)
    logger.info(f"Saved {os.path.join(OUT_DIR, 'feature_audit.csv')} successfully.")

    # 3. Match Exact T+7 Calendar-Day Targets and Apply Horizon Embargo
    logger.info("Matching exact T+7 calendar-day targets and partitioning chronologically...")
    partitions, split_summary_df = match_targets_and_partition(clean_s2)
    split_summary_df.to_csv(os.path.join(OUT_DIR, "temporal_split_summary.csv"), index=False)
    logger.info(f"Saved {os.path.join(OUT_DIR, 'temporal_split_summary.csv')} successfully.")

    train_df = partitions['train_df']
    val_df = partitions['val_df']
    test_df = partitions['test_df']
    n_train = len(train_df)
    n_val = len(val_df)
    n_test = len(test_df)

    logger.info(f"Partition counts: Train={n_train:,}, Val={n_val:,}, Test={n_test:,}")

    # 4. Strict Training-Only Preprocessing Pipeline
    numeric_features = [
        'Log_Modal_Price', 'Price_Spread_Ratio',
        'Past_Return_1d', 'Past_Return_3d', 'Past_Return_7d', 'Past_Return_Bounded7d',
        'Momentum_Ratio_7d', 'Hist_Vol_Commodity', 'Day_Of_Week', 'Month'
    ]
    categorical_features = ['Commodity', 'Market_Canonical', 'Grade']
    feature_cols = numeric_features + categorical_features

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', Pipeline([
                ('imputer', SimpleImputer(strategy='median')),
                ('scaler', StandardScaler())
            ]), numeric_features),
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_features)
        ]
    )

    logger.info("Fitting preprocessing pipeline strictly on Train partition...")
    X_train = preprocessor.fit_transform(train_df[feature_cols])
    y_train = train_df['Target_Class'].values
    y_train_reg = train_df['R_7'].values

    X_val = preprocessor.transform(val_df[feature_cols])
    y_val = val_df['Target_Class'].values
    y_val_reg = val_df['R_7'].values

    X_test = preprocessor.transform(test_df[feature_cols])
    y_test = test_df['Target_Class'].values
    y_test_reg = test_df['R_7'].values

    classes = ['Favorable', 'Normal', 'Unfavorable']

    # 5. Baseline Evaluation
    logger.info("Evaluating Phase 3 Baselines (A, B, C, D)...")
    train_class_counts = train_df['Target_Class'].value_counts()
    majority_class = train_class_counts.index[0]  # Normal
    majority_prob = train_class_counts / n_train

    # Baseline A: Majority Class Predictor
    pred_maj_val = np.array([majority_class] * n_val)
    pred_maj_test = np.array([majority_class] * n_test)

    # Baseline B: Historical Class Frequency Predictor
    rng = np.random.RandomState(42)
    freq_classes = majority_prob.index.tolist()
    freq_probs = majority_prob.values.tolist()
    pred_freq_val = rng.choice(freq_classes, size=n_val, p=freq_probs)
    pred_freq_test = rng.choice(freq_classes, size=n_test, p=freq_probs)

    # Baseline C: Simple Historical Momentum Rule
    def momentum_predict(ret_val):
        if pd.isna(ret_val):
            return majority_class
        if ret_val > 2.5:
            return 'Favorable'
        elif ret_val < -2.5:
            return 'Unfavorable'
        else:
            return 'Normal'

    pred_mom_val = val_df['Past_Return_Bounded7d'].apply(momentum_predict).values
    pred_mom_test = test_df['Past_Return_Bounded7d'].apply(momentum_predict).values

    # Baseline D: Persistence (No-Change Benchmark) -> Predicts Normal
    pred_pers_val = np.array(['Normal'] * n_val)
    pred_pers_test = np.array(['Normal'] * n_test)

    baselines = {
        'Majority_Class_Baseline': {
            'val_pred': pred_maj_val,
            'test_pred': pred_maj_test,
            'desc': f'Always predicts training majority class ({majority_class})'
        },
        'Historical_Frequency_Baseline': {
            'val_pred': pred_freq_val,
            'test_pred': pred_freq_test,
            'desc': f'Sampled according to training empirical class distribution (seed=42)'
        },
        'Historical_Momentum_Rule': {
            'val_pred': pred_mom_val,
            'test_pred': pred_mom_test,
            'desc': 'Extrapolates past 7-day price momentum direction (Favorable if >2.5%, Unfavorable if <-2.5%, else Normal)'
        },
        'Persistence_NoChange_Benchmark': {
            'val_pred': pred_pers_val,
            'test_pred': pred_pers_test,
            'desc': 'Assumes wholesale price stickiness persistence (0% change = Normal class)'
        }
    }

    baseline_metric_rows = []
    for b_name, b_info in baselines.items():
        for p_name, y_true, y_p in [('VALIDATION', y_val, b_info['val_pred']), ('FINAL_TEST', y_test, b_info['test_pred'])]:
            acc = round(accuracy_score(y_true, y_p) * 100, 2)
            bacc = round(balanced_accuracy_score(y_true, y_p) * 100, 2)
            f1 = round(f1_score(y_true, y_p, average='macro', zero_division=0), 4)
            baseline_metric_rows.append({
                'baseline_name': b_name,
                'partition': p_name,
                'observation_count': len(y_true),
                'accuracy': acc,
                'balanced_accuracy': bacc,
                'macro_f1': f1,
                'description': b_info['desc']
            })
    pd.DataFrame(baseline_metric_rows).to_csv(os.path.join(OUT_DIR, "baseline_metrics.csv"), index=False)
    logger.info(f"Saved {os.path.join(OUT_DIR, 'baseline_metrics.csv')} successfully.")

    # 6. Candidate Machine Learning Models
    logger.info("Training candidate machine learning models on training partition...")
    models = {
        'Logistic Regression': (
            LogisticRegression(max_iter=1000, random_state=42),
            'Multinomial Logistic Regression with L2 regularization (C=1.0, max_iter=1000)'
        ),
        'Decision Tree': (
            DecisionTreeClassifier(max_depth=5, min_samples_leaf=50, random_state=42),
            'Decision Tree with constrained depth (max_depth=5, min_samples_leaf=50)'
        ),
        'Random Forest': (
            RandomForestClassifier(n_estimators=100, max_depth=8, min_samples_leaf=20, random_state=42, n_jobs=-1),
            'Random Forest Ensemble (n_estimators=100, max_depth=8, min_samples_leaf=20)'
        ),
        'LightGBM': (
            lgb.LGBMClassifier(n_estimators=100, max_depth=5, learning_rate=0.05, min_child_samples=50, random_state=42, verbose=-1),
            'Gradient Boosted Decision Trees via LightGBM (100 trees, max_depth=5, lr=0.05)'
        )
    }

    test_maj_acc = round((y_test == majority_class).mean() * 100, 2)
    test_maj_macro_f1 = round(f1_score(y_test, [majority_class]*n_test, average='macro', zero_division=0), 4)

    model_comp_rows = []
    class_report_rows = []
    confusion_rows = []
    fitted_models = {}

    for m_name, (clf, config_str) in models.items():
        logger.info(f"Fitting {m_name}...")
        warning_msg = "None"
        with warnings.catch_warnings(record=True) as caught_warnings:
            warnings.simplefilter("always")
            clf.fit(X_train, y_train)
            if len(caught_warnings) > 0:
                warning_msg = f"{len(caught_warnings)} warnings (e.g. {caught_warnings[0].category.__name__})"
        
        fitted_models[m_name] = clf

        val_pred = clf.predict(X_val)
        test_pred = clf.predict(X_test)

        val_acc = round(accuracy_score(y_val, val_pred) * 100, 2)
        val_bacc = round(balanced_accuracy_score(y_val, val_pred) * 100, 2)
        val_f1 = round(f1_score(y_val, val_pred, average='macro', zero_division=0), 4)

        test_acc = round(accuracy_score(y_test, test_pred) * 100, 2)
        test_bacc = round(balanced_accuracy_score(y_test, test_pred) * 100, 2)
        test_f1 = round(f1_score(y_test, test_pred, average='macro', zero_division=0), 4)

        acc_delta = round(test_acc - test_maj_acc, 2)
        f1_delta = round(test_f1 - test_maj_macro_f1, 4)

        model_comp_rows.append({
            'model_name': m_name,
            'model_type': 'CLASSIFICATION',
            'validation_accuracy': val_acc,
            'validation_balanced_accuracy': val_bacc,
            'validation_macro_f1': val_f1,
            'test_accuracy': test_acc,
            'test_balanced_accuracy': test_bacc,
            'test_macro_f1': test_f1,
            'test_acc_delta_vs_majority': f"{'+' if acc_delta > 0 else ''}{acc_delta}%",
            'test_macro_f1_delta_vs_majority': f"{'+' if f1_delta > 0 else ''}{f1_delta}",
            'training_configuration': config_str,
            'convergence_and_warnings': warning_msg
        })

        for p_name, y_true, y_p in [('VALIDATION', y_val, val_pred), ('FINAL_TEST', y_test, test_pred)]:
            prec, rec, f1_vals, supp = precision_recall_fscore_support(y_true, y_p, labels=classes, zero_division=0)
            for c_label, p_v, r_v, f_v, s_v in zip(classes, prec, rec, f1_vals, supp):
                class_report_rows.append({
                    'model_name': m_name,
                    'partition': p_name,
                    'class_label': c_label,
                    'precision': round(p_v, 4),
                    'recall': round(r_v, 4),
                    'f1_score': round(f_v, 4),
                    'support': int(s_v)
                })

            cm = confusion_matrix(y_true, y_p, labels=classes)
            for i, act_c in enumerate(classes):
                for j, pred_c in enumerate(classes):
                    confusion_rows.append({
                        'model_name': m_name,
                        'partition': p_name,
                        'actual_class': act_c,
                        'predicted_class': pred_c,
                        'count': int(cm[i, j])
                    })

    for b_name, b_info in baselines.items():
        for p_name, y_true, y_p in [('VALIDATION', y_val, b_info['val_pred']), ('FINAL_TEST', y_test, b_info['test_pred'])]:
            cm = confusion_matrix(y_true, y_p, labels=classes)
            for i, act_c in enumerate(classes):
                for j, pred_c in enumerate(classes):
                    confusion_rows.append({
                        'model_name': b_name,
                        'partition': p_name,
                        'actual_class': act_c,
                        'predicted_class': pred_c,
                        'count': int(cm[i, j])
                    })

    pd.DataFrame(model_comp_rows).to_csv(os.path.join(OUT_DIR, "model_comparison.csv"), index=False)
    pd.DataFrame(class_report_rows).to_csv(os.path.join(OUT_DIR, "classification_report.csv"), index=False)
    pd.DataFrame(confusion_rows).to_csv(os.path.join(OUT_DIR, "confusion_matrix.csv"), index=False)
    logger.info("Saved model_comparison.csv, classification_report.csv, and confusion_matrix.csv successfully.")

    # 7. Subgroup Performance
    logger.info("Evaluating subgroup performance by major commodities and markets...")
    subgroup_rows = []
    top_commodities = train_df['Commodity'].value_counts().head(5).index.tolist()
    top_markets = train_df['Market_Canonical'].value_counts().head(5).index.tolist()

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for subgroup_type, col_name, item_list in [('COMMODITY', 'Commodity', top_commodities), ('MARKET', 'Market_Canonical', top_markets)]:
            for item in item_list:
                for p_name, p_df, X_p, y_p_all in [('VALIDATION', val_df, X_val, y_val), ('FINAL_TEST', test_df, X_test, y_test)]:
                    mask = (p_df[col_name] == item).values
                    obs_count = int(mask.sum())
                    if obs_count < 30:
                        subgroup_rows.append({
                            'subgroup_type': subgroup_type,
                            'subgroup_name': item,
                            'partition': p_name,
                            'model_name': 'ALL_MODELS',
                            'observation_count': obs_count,
                            'accuracy': np.nan,
                            'macro_f1': np.nan,
                            'reliability_warning': f'INSUFFICIENT EVIDENCE: only {obs_count} samples (<30 threshold)'
                        })
                        continue

                    y_sub_true = y_p_all[mask]
                    X_sub = X_p[mask]
                    for m_name, clf in fitted_models.items():
                        y_sub_pred = clf.predict(X_sub)
                        acc = round(accuracy_score(y_sub_true, y_sub_pred) * 100, 2)
                        f1 = round(f1_score(y_sub_true, y_sub_pred, average='macro', zero_division=0), 4)
                        subgroup_rows.append({
                            'subgroup_type': subgroup_type,
                            'subgroup_name': item,
                            'partition': p_name,
                            'model_name': m_name,
                            'observation_count': obs_count,
                            'accuracy': acc,
                            'macro_f1': f1,
                            'reliability_warning': 'ADEQUATE EVIDENCE' if obs_count >= 100 else 'CAUTION: Small subgroup sample size'
                        })

    pd.DataFrame(subgroup_rows).to_csv(os.path.join(OUT_DIR, "subgroup_performance.csv"), index=False)
    logger.info(f"Saved {os.path.join(OUT_DIR, 'subgroup_performance.csv')} successfully.")

    # 8. Secondary Regression Task
    logger.info("Evaluating secondary continuous return regression task...")
    mean_train_ret = float(y_train_reg.mean())

    reg_models = {
        'Zero_Return_Persistence_Benchmark': {
            'val_pred': np.zeros_like(y_val_reg),
            'test_pred': np.zeros_like(y_test_reg),
            'desc': 'Assumes 0.0% price change over 7 days (wholesale stickiness persistence)'
        },
        'Mean_Return_Baseline': {
            'val_pred': np.full_like(y_val_reg, mean_train_ret),
            'test_pred': np.full_like(y_test_reg, mean_train_ret),
            'desc': f'Predicts historical mean training return ({mean_train_ret:.3f}%)'
        }
    }

    # Train Ridge Regressor with LSQR solver
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ridge = Ridge(alpha=10.0, solver='lsqr', random_state=42)
        ridge.fit(X_train, y_train_reg)
        reg_models['Ridge_Regression'] = {
            'val_pred': ridge.predict(X_val),
            'test_pred': ridge.predict(X_test),
            'desc': 'Linear L2-regularized Ridge Regression (alpha=10.0)'
        }

        # Train LightGBM Regressor
        lgb_r = lgb.LGBMRegressor(n_estimators=100, max_depth=5, learning_rate=0.05, min_child_samples=50, random_state=42, verbose=-1)
        lgb_r.fit(X_train, y_train_reg)
        reg_models['LightGBM_Regressor'] = {
            'val_pred': lgb_r.predict(X_val),
            'test_pred': lgb_r.predict(X_test),
            'desc': 'LightGBM Regressor (100 trees, max_depth=5, lr=0.05)'
        }

    base_zero_val_mae = mean_absolute_error(y_val_reg, np.zeros_like(y_val_reg))
    base_zero_val_rmse = root_mean_squared_error(y_val_reg, np.zeros_like(y_val_reg))
    base_zero_test_mae = mean_absolute_error(y_test_reg, np.zeros_like(y_test_reg))
    base_zero_test_rmse = root_mean_squared_error(y_test_reg, np.zeros_like(y_test_reg))

    reg_metric_rows = []
    for r_name, r_info in reg_models.items():
        for p_name, y_true_r, y_pred_r, b_mae, b_rmse in [
            ('VALIDATION', y_val_reg, r_info['val_pred'], base_zero_val_mae, base_zero_val_rmse),
            ('FINAL_TEST', y_test_reg, r_info['test_pred'], base_zero_test_mae, base_zero_test_rmse)
        ]:
            mae = round(float(mean_absolute_error(y_true_r, y_pred_r)), 4)
            rmse = round(float(root_mean_squared_error(y_true_r, y_pred_r)), 4)
            dir_correct = round(float(((y_true_r * y_pred_r) > 0).mean() * 100), 2)
            mae_delta = round(mae - b_mae, 4)
            rmse_delta = round(rmse - b_rmse, 4)
            reg_metric_rows.append({
                'model_name': r_name,
                'partition': p_name,
                'observation_count': len(y_true_r),
                'mae': mae,
                'rmse': rmse,
                'directional_accuracy_pct': dir_correct,
                'baseline_mae_delta': f"{'+' if mae_delta > 0 else ''}{mae_delta}",
                'baseline_rmse_delta': f"{'+' if rmse_delta > 0 else ''}{rmse_delta}",
                'model_configuration': r_info['desc']
            })

    pd.DataFrame(reg_metric_rows).to_csv(os.path.join(OUT_DIR, "regression_metrics.csv"), index=False)
    logger.info(f"Saved {os.path.join(OUT_DIR, 'regression_metrics.csv')} successfully.")
    logger.info("================================================================================")
    logger.info("PHASE 3 EXPERIMENT EXECUTION COMPLETED SUCCESSFULLY")
    logger.info("================================================================================")
    return True


if __name__ == "__main__":
    cli_repo = None
    for i, arg in enumerate(sys.argv):
        if arg == "--repo-root" and i + 1 < len(sys.argv):
            cli_repo = sys.argv[i + 1]
    run_experiment(cli_repo)
