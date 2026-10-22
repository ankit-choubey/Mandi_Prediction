"""
Comprehensive Feature Selection, Testing, and Validation Pipeline
APMC Mandi Market Intelligence System
Investigator: Suryansh

Performs 5 statistical and ML tests across candidate external & market features:
1. Mutual Information (mutual_info_classif)
2. ANOVA F-statistic (f_classif)
3. Random Forest Mean Decrease in Impurity (MDI)
4. Gradient Boosting MDI
5. Directional Pearson Correlation with 7-day Return

Ranks all candidates to select the BEST EXTRA 12 FEATURES.
Validates the Enhanced Model (27 Baseline + 12 Extra = 39 Features) against the Baseline.
"""

import os
import sys
import time
import ssl
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import timedelta

from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.feature_selection import mutual_info_classif, f_classif
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    log_loss
)

WORKSPACE_ROOT = "/Users/kumarsuryansh/Desktop/Temporary/suryansh - work"
DATA_DIR = "/Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction/data/raw"
WEATHER_CSV = os.path.join(WORKSPACE_ROOT, "dataset_research", "raw_external", "nasa_power_weather_up_2024_2026.csv")
RESULTS_DIR = os.path.join(WORKSPACE_ROOT, "results", "feature_selection")
FIGURES_DIR = os.path.join(WORKSPACE_ROOT, "figures")
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(FIGURES_DIR, exist_ok=True)

# -----------------------------------------------------------------------------
# 1. LOAD MANDI PRICE DATA + WEATHER DATA
# -----------------------------------------------------------------------------
def load_all_data():
    csv_files = sorted([os.path.join(DATA_DIR, f) for f in os.listdir(DATA_DIR) if f.endswith('.csv')])
    print(f"[DataLoader] Ingesting {len(csv_files)} raw district files...")
    dfs = [pd.read_csv(f) for f in csv_files]
    df = pd.concat(dfs, ignore_index=True)
    
    district_clean_map = {'Gaziabaad': 'Ghaziabad', 'Lukhnow': 'Lucknow'}
    df['District'] = df['District'].replace(district_clean_map)
    
    if 'Grade' in df.columns:
        df['Grade'] = df['Grade'].fillna('FAQ').astype(str).str.strip()
        df['Grade'] = df['Grade'].replace({'': 'FAQ', 'nan': 'FAQ', 'None': 'FAQ'})
    else:
        df['Grade'] = 'FAQ'
        
    df['Arrival_Date'] = pd.to_datetime(df['Arrival_Date'], format='%d/%m/%Y', errors='coerce')
    for p in ['Modal_Price', 'Min_Price', 'Max_Price']:
        df[p] = pd.to_numeric(df[p], errors='coerce')
        
    series_cols = ['District', 'Market', 'Commodity', 'Variety', 'Grade']
    df = df.dropna(subset=['Arrival_Date', 'Modal_Price', 'Min_Price', 'Max_Price'] + series_cols).copy()
    df = df[(df['Modal_Price'] > 0) & (df['Min_Price'] > 0) & (df['Max_Price'] > 0)].copy()
    
    # Strategy 2 duplicate exclusion
    key_grade = series_cols + ['Arrival_Date']
    dup_groups = df.groupby(key_grade).agg(
        n_rows=('Modal_Price', 'count'),
        modal_nunique=('Modal_Price', 'nunique'),
        min_nunique=('Min_Price', 'nunique'),
        max_nunique=('Max_Price', 'nunique')
    )
    ambiguous_keys = dup_groups[
        (dup_groups['n_rows'] > 1) & 
        ((dup_groups['modal_nunique'] > 1) | (dup_groups['min_nunique'] > 1) | (dup_groups['max_nunique'] > 1))
    ].index
    
    is_ambiguous = df.set_index(key_grade).index.isin(ambiguous_keys)
    df = df[~is_ambiguous].copy()
    df = df.drop_duplicates(subset=key_grade, keep='first').copy()
    
    df['series_id'] = df[series_cols].astype(str).agg('__'.join, axis=1)
    df.sort_values(by=['series_id', 'Arrival_Date'], inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    series_counts = df.groupby('series_id').size()
    valid_series = series_counts[series_counts >= 20].index
    clean_df = df[df['series_id'].isin(valid_series)].copy()
    clean_df.reset_index(drop=True, inplace=True)
    print(f"[DataLoader] Clean records: {len(clean_df):,} across {clean_df['series_id'].nunique():,} series.")
    
    # Load Weather Data
    print(f"[DataLoader] Ingesting NASA POWER weather data from {WEATHER_CSV}...")
    w_df = pd.read_csv(WEATHER_CSV)
    w_df['Arrival_Date'] = pd.to_datetime(w_df['Arrival_Date'])
    
    # Merge weather deterministically on District and Arrival_Date
    merged_df = pd.merge(clean_df, w_df, on=['District', 'Arrival_Date'], how='left')
    print(f"[DataLoader] Merged dataset: {len(merged_df):,} records with weather signals.")
    return merged_df

# -----------------------------------------------------------------------------
# 2. FEATURE ENGINEERING (ORIGINAL 27 + 16 CANDIDATE EXTRA FEATURES)
# -----------------------------------------------------------------------------
NEIGHBORING_DISTRICTS = {
    'Lucknow': ['Unnao', 'Kanpur'],
    'Kanpur': ['Unnao', 'Lucknow'],
    'Unnao': ['Kanpur', 'Lucknow'],
    'Ghaziabad': ['Gaziabaad'],
    'Jhansi': ['Jhansi']
}

ORIGINAL_27_FEATURES = [
    'Modal_Price', 'Min_Price', 'Max_Price', 'Price_Intraday_Spread', 'Price_Intraday_Spread_Ratio',
    'Lag_Price_1', 'Lag_Price_3', 'Lag_Price_7', 'Price_Change_1d', 'Price_Change_3d', 'Price_Change_7d',
    'Roll_Mean_Price_3', 'Roll_Mean_Price_7', 'Roll_Std_Price_7', 'Price_to_RollMean3_Ratio', 'Price_to_RollMean7_Ratio',
    'Month', 'DayOfWeek', 'DayOfMonth', 'Quarter', 'Season',
    'District_Commodity_MeanPrice', 'District_Commodity_MandiCount', 'Mandi_vs_District_Ratio',
    'Neighbor_Commodity_MeanPrice', 'Price_Diff_Target_vs_Neighbor', 'Price_Ratio_Target_vs_Neighbor'
]

def engineer_all_features(df):
    print("[FeatureEngineering] Constructing original 27 features + 16 candidate extra features...")
    df = df.copy()
    
    # --- 1. Original Intraday Spreads ---
    df['Price_Intraday_Spread'] = df['Max_Price'] - df['Min_Price']
    df['Price_Intraday_Spread_Ratio'] = df['Price_Intraday_Spread'] / (df['Modal_Price'] + 1e-5)
    
    # --- 2. Calendar Lags ---
    lag_lookup = df[['series_id', 'Arrival_Date', 'Modal_Price']].drop_duplicates().copy()
    for k in [1, 3, 7]:
        df[f'_Lag_Date_{k}'] = df['Arrival_Date'] - timedelta(days=k)
        df = pd.merge(
            df,
            lag_lookup.rename(columns={'Modal_Price': f'Lag_Price_{k}', 'Arrival_Date': f'_Lag_Date_{k}'}),
            on=['series_id', f'_Lag_Date_{k}'],
            how='left'
        )
        df.drop(columns=[f'_Lag_Date_{k}'], inplace=True)
        
    df['Price_Change_1d'] = ((df['Modal_Price'] - df['Lag_Price_1']) / df['Lag_Price_1']) * 100
    df['Price_Change_3d'] = ((df['Modal_Price'] - df['Lag_Price_3']) / df['Lag_Price_3']) * 100
    df['Price_Change_7d'] = ((df['Modal_Price'] - df['Lag_Price_7']) / df['Lag_Price_7']) * 100
    
    # --- 3. Rolling Stats ---
    grouped = df.groupby('series_id')
    df['Roll_Mean_Price_3'] = grouped['Modal_Price'].transform(lambda s: s.rolling(window=3, min_periods=1).mean())
    df['Roll_Mean_Price_7'] = grouped['Modal_Price'].transform(lambda s: s.rolling(window=7, min_periods=1).mean())
    df['Roll_Std_Price_7'] = grouped['Modal_Price'].transform(lambda s: s.rolling(window=7, min_periods=3).std())
    df['Price_to_RollMean3_Ratio'] = df['Modal_Price'] / (df['Roll_Mean_Price_3'] + 1e-5)
    df['Price_to_RollMean7_Ratio'] = df['Modal_Price'] / (df['Roll_Mean_Price_7'] + 1e-5)
    
    # --- 4. Seasonality ---
    df['Month'] = df['Arrival_Date'].dt.month
    df['DayOfWeek'] = df['Arrival_Date'].dt.dayofweek
    df['DayOfMonth'] = df['Arrival_Date'].dt.day
    df['Quarter'] = df['Arrival_Date'].dt.quarter
    df['Season'] = df['Month'].apply(lambda m: 1 if m in [7, 8, 9, 10] else (2 if m in [11, 12, 1, 2, 3] else 3))
    
    # --- 5. District & Spatial Intelligence ---
    dist_agg = df.groupby(['District', 'Commodity', 'Arrival_Date'])['Modal_Price'].agg(
        District_Commodity_MeanPrice='mean',
        District_Commodity_MandiCount='count'
    ).reset_index()
    df = pd.merge(df, dist_agg, on=['District', 'Commodity', 'Arrival_Date'], how='left')
    df['Mandi_vs_District_Ratio'] = df['Modal_Price'] / (df['District_Commodity_MeanPrice'] + 1e-5)
    
    dist_comm_date = df.groupby(['District', 'Commodity', 'Arrival_Date'])['Modal_Price'].mean().reset_index()
    neighbor_pairs = []
    for dist, neighbors in NEIGHBORING_DISTRICTS.items():
        for n_dist in neighbors:
            if n_dist != dist:
                neighbor_pairs.append({'District': dist, 'Neighbor_District': n_dist})
    pairs_df = pd.DataFrame(neighbor_pairs)
    merged_n = pd.merge(
        pairs_df,
        dist_comm_date.rename(columns={'District': 'Neighbor_District', 'Modal_Price': 'Neighbor_Modal_Price'}),
        on='Neighbor_District'
    )
    neighbor_summary = merged_n.groupby(['District', 'Commodity', 'Arrival_Date'])['Neighbor_Modal_Price'].mean().reset_index()
    df = pd.merge(df, neighbor_summary, on=['District', 'Commodity', 'Arrival_Date'], how='left')
    df['Neighbor_Commodity_MeanPrice'] = df['Neighbor_Modal_Price'].fillna(df['District_Commodity_MeanPrice'])
    df.drop(columns=['Neighbor_Modal_Price'], inplace=True)
    df['Price_Diff_Target_vs_Neighbor'] = df['Modal_Price'] - df['Neighbor_Commodity_MeanPrice']
    df['Price_Ratio_Target_vs_Neighbor'] = df['Modal_Price'] / (df['Neighbor_Commodity_MeanPrice'] + 1e-5)
    
    # =========================================================================
    # CANDIDATE EXTRA FEATURES (16 CANDIDATES)
    # =========================================================================
    # 1. Weather Signals (NASA POWER - Causal Lagged to T-1 and T-3)
    df['Precipitation_Lag1'] = df.groupby('District')['Precipitation_mm'].shift(1)
    df['Precipitation_Sum_3d'] = df.groupby('District')['Precipitation_mm'].transform(lambda s: s.shift(1).rolling(3, min_periods=1).sum())
    df['Precipitation_Sum_7d'] = df.groupby('District')['Precipitation_mm'].transform(lambda s: s.shift(1).rolling(7, min_periods=1).sum())
    df['Extreme_Rain_Flag'] = (df['Precipitation_Sum_3d'] > 20.0).astype(int)
    
    df['Temp_Max_Lag1'] = df.groupby('District')['Temp_Max_C'].shift(1)
    df['Temp_Max_RollMean3'] = df.groupby('District')['Temp_Max_C'].transform(lambda s: s.shift(1).rolling(3, min_periods=1).mean())
    df['Temp_Diurnal_Range'] = df['Temp_Max_C'] - df['Temp_Min_C']
    df['Relative_Humidity_Mean7'] = df.groupby('District')['Relative_Humidity_Pct'].transform(lambda s: s.shift(1).rolling(7, min_periods=1).mean())
    
    # 2. Advanced Dynamic Price & Market Breadth Signals
    df['Price_Acceleration_7d'] = df['Price_Change_3d'] - df['Price_Change_7d']
    df['Intraday_Volatility_RollMean7'] = grouped['Price_Intraday_Spread_Ratio'].transform(lambda s: s.rolling(7, min_periods=1).mean())
    df['Rolling_Price_ZScore_7d'] = (df['Modal_Price'] - df['Roll_Mean_Price_7']) / (df['Roll_Std_Price_7'] + 1e-5)
    
    roll_max_7 = grouped['Modal_Price'].transform(lambda s: s.rolling(7, min_periods=1).max())
    roll_min_7 = grouped['Modal_Price'].transform(lambda s: s.rolling(7, min_periods=1).min())
    df['Rolling_Max_Min_Spread_7d'] = (roll_max_7 - roll_min_7) / (df['Modal_Price'] + 1e-5)
    
    df['Price_to_Min_Ratio'] = df['Modal_Price'] / (df['Min_Price'] + 1e-5)
    df['District_Price_Dispersion'] = df.groupby(['District', 'Commodity', 'Arrival_Date'])['Modal_Price'].transform('std').fillna(0.0)
    
    # 3. Market Trading Breadth Lag
    df['_mandi_breadth'] = df.groupby(['District', 'Commodity', 'Arrival_Date'])['Market'].transform('nunique')
    df['Market_Trading_Breadth_Lag1'] = df.groupby('series_id')['_mandi_breadth'].shift(1).fillna(1.0).astype(float)
    df.drop(columns=['_mandi_breadth'], inplace=True)
    
    # 4. Variety Relative Price Premium
    comm_mean = df.groupby(['Commodity', 'Arrival_Date'])['Modal_Price'].transform('mean')
    df['Variety_Price_Premium'] = df['Modal_Price'] - comm_mean
    
    # --- Exact Calendar T+7 Target Matching ---
    t7_lookup = df[['series_id', 'Arrival_Date', 'Modal_Price']].copy()
    df['Target_Date'] = df['Arrival_Date'] + timedelta(days=7)
    matched = pd.merge(
        df,
        t7_lookup,
        left_on=['series_id', 'Target_Date'],
        right_on=['series_id', 'Arrival_Date'],
        suffixes=('', '_T7'),
        how='inner'
    )
    
    matched['Return_7d'] = ((matched['Modal_Price_T7'] - matched['Modal_Price']) / (matched['Modal_Price'] + 1e-5)) * 100
    matched['Target_Class'] = np.select(
        [matched['Return_7d'] > 2.5, matched['Return_7d'] < -2.5],
        [2, 0],
        default=1
    )
    print(f"[FeatureEngineering] Paired T+7 labeled records: {len(matched):,}")
    return matched

CANDIDATE_EXTRA_FEATURES = [
    'Precipitation_Lag1',
    'Precipitation_Sum_3d',
    'Precipitation_Sum_7d',
    'Extreme_Rain_Flag',
    'Temp_Max_Lag1',
    'Temp_Max_RollMean3',
    'Temp_Diurnal_Range',
    'Relative_Humidity_Mean7',
    'Price_Acceleration_7d',
    'Intraday_Volatility_RollMean7',
    'Rolling_Price_ZScore_7d',
    'Rolling_Max_Min_Spread_7d',
    'Price_to_Min_Ratio',
    'District_Price_Dispersion',
    'Market_Trading_Breadth_Lag1',
    'Variety_Price_Premium'
]

# -----------------------------------------------------------------------------
# 3. SPLIT DATA (CHRONOLOGICAL 70-15-15 WITH 8-DAY EMBARGO)
# -----------------------------------------------------------------------------
def split_data(df, horizon_days=7):
    sorted_df = df.sort_values('Arrival_Date').reset_index(drop=True)
    dates = sorted_df['Arrival_Date'].drop_duplicates().sort_values().reset_index(drop=True)
    n_dates = len(dates)
    train_end = dates.iloc[int(n_dates * 0.70)]
    val_end = dates.iloc[int(n_dates * 0.85)]
    
    train_embargo = train_end - pd.Timedelta(days=horizon_days + 1)
    val_embargo = val_end - pd.Timedelta(days=horizon_days + 1)
    
    train_df = sorted_df[sorted_df['Arrival_Date'] <= train_embargo].copy()
    val_df = sorted_df[(sorted_df['Arrival_Date'] >= train_end) & (sorted_df['Arrival_Date'] <= val_embargo)].copy()
    test_df = sorted_df[sorted_df['Arrival_Date'] >= val_end].copy()
    print(f"[Split] Train: {len(train_df):,} | Val: {len(val_df):,} | Test: {len(test_df):,}")
    return train_df, val_df, test_df

# -----------------------------------------------------------------------------
# 4. PERFORM ALL 5 FEATURE SELECTION TESTS
# -----------------------------------------------------------------------------
def evaluate_and_select_features(train_df):
    print("\n" + "=" * 80)
    print("STAGE 1: COMPREHENSIVE STATISTICAL & ML FEATURE SELECTION TESTS (ON TRAINING SET)")
    print("=" * 80)
    
    X_train_raw = train_df[CANDIDATE_EXTRA_FEATURES]
    y_train = train_df['Target_Class']
    y_return = train_df['Return_7d']
    
    # Impute medians for test computation
    imputer = SimpleImputer(strategy='median')
    X_train_imp = pd.DataFrame(imputer.fit_transform(X_train_raw), columns=CANDIDATE_EXTRA_FEATURES)
    
    # Test 1: ANOVA F-statistic
    print("[Test 1/5] Running ANOVA F-test (f_classif)...")
    f_scores, f_pvals = f_classif(X_train_imp, y_train)
    
    # Test 2: Mutual Information (subsample 20k rows for efficiency)
    print("[Test 2/5] Running Mutual Information test (mutual_info_classif)...")
    np.random.seed(42)
    sample_idx = np.random.choice(len(X_train_imp), size=min(20000, len(X_train_imp)), replace=False)
    mi_scores = mutual_info_classif(X_train_imp.iloc[sample_idx], y_train.iloc[sample_idx], random_state=42)
    
    # Test 3: Random Forest MDI
    print("[Test 3/5] Fitting Random Forest to extract MDI...")
    rf = RandomForestClassifier(n_estimators=60, max_depth=10, min_samples_leaf=15, n_jobs=-1, random_state=42)
    rf.fit(X_train_imp, y_train)
    rf_mdi = rf.feature_importances_
    
    # Test 4: Gradient Boosting MDI
    print("[Test 4/5] Fitting Gradient Boosting to extract MDI...")
    gb = GradientBoostingClassifier(n_estimators=60, max_depth=4, learning_rate=0.1, random_state=42)
    gb.fit(X_train_imp, y_train)
    gb_mdi = gb.feature_importances_
    
    # Test 5: Absolute Pearson Correlation with Return_7d
    print("[Test 5/5] Computing Pearson Correlation with 7-day Return...")
    corr_scores = [abs(X_train_imp[col].corr(y_return)) for col in CANDIDATE_EXTRA_FEATURES]
    
    # Compile Results
    results_df = pd.DataFrame({
        'Feature_Name': CANDIDATE_EXTRA_FEATURES,
        'ANOVA_F_Score': f_scores,
        'Mutual_Info_Score': mi_scores,
        'Random_Forest_MDI': rf_mdi,
        'Gradient_Boosting_MDI': gb_mdi,
        'Pearson_Abs_Corr': corr_scores
    })
    
    # Compute relative ranks (1 = highest / best)
    for metric in ['ANOVA_F_Score', 'Mutual_Info_Score', 'Random_Forest_MDI', 'Gradient_Boosting_MDI', 'Pearson_Abs_Corr']:
        results_df[f'{metric}_Rank'] = results_df[metric].rank(ascending=False)
        
    results_df['Composite_Rank_Sum'] = (
        results_df['ANOVA_F_Score_Rank'] +
        results_df['Mutual_Info_Score_Rank'] +
        results_df['Random_Forest_MDI_Rank'] +
        results_df['Gradient_Boosting_MDI_Rank'] +
        results_df['Pearson_Abs_Corr_Rank']
    )
    
    results_df.sort_values(by='Composite_Rank_Sum', inplace=True)
    results_df.reset_index(drop=True, inplace=True)
    results_df['Final_Selection_Rank'] = np.arange(1, len(results_df) + 1)
    
    results_csv = os.path.join(RESULTS_DIR, "candidate_feature_selection_tests.csv")
    results_df.to_csv(results_csv, index=False)
    print(f"\n[Feature Selection Complete] Test results saved to {results_csv}")
    
    top_12_features = results_df['Feature_Name'].iloc[:12].tolist()
    print("\n" + "=" * 80)
    print("FINAL SELECTION: TOP 12 BEST EXTRA FEATURES")
    print("=" * 80)
    for i, col in enumerate(top_12_features, 1):
        score = results_df.loc[results_df['Feature_Name'] == col, 'Composite_Rank_Sum'].values[0]
        print(f"  Rank {i:2d}: {col:<30} (Rank Sum Score: {score:.1f})")
        
    return results_df, top_12_features

# -----------------------------------------------------------------------------
# 5. VALIDATION: BENCHMARK BASELINE (27) VS ENHANCED MODEL (27 + 12 = 39)
# -----------------------------------------------------------------------------
def benchmark_models(train_df, val_df, test_df, top_12_features):
    print("\n" + "=" * 80)
    print("STAGE 2: VALIDATING ENHANCED MODEL (39 FEATURES) VS BASELINE (27 FEATURES)")
    print("=" * 80)
    
    feature_sets = {
        'Baseline_27_Features': ORIGINAL_27_FEATURES,
        'Enhanced_39_Features': ORIGINAL_27_FEATURES + top_12_features
    }
    
    benchmarks = []
    crop_benchmarks = []
    
    for fset_name, fcols in feature_sets.items():
        print(f"\n--- Training {fset_name} ({len(fcols)} features) ---")
        pipe = Pipeline([
            ('imputer', SimpleImputer(strategy='median')),
            ('classifier', GradientBoostingClassifier(n_estimators=100, max_depth=5, learning_rate=0.1, random_state=42))
        ])
        
        t0 = time.time()
        pipe.fit(train_df[fcols], train_df['Target_Class'])
        fit_time = time.time() - t0
        
        # Validation score
        val_preds = pipe.predict(val_df[fcols])
        val_acc = accuracy_score(val_df['Target_Class'], val_preds) * 100
        val_bal_acc = balanced_accuracy_score(val_df['Target_Class'], val_preds) * 100
        val_macro_f1 = f1_score(val_df['Target_Class'], val_preds, average='macro', zero_division=0)
        
        # Test evaluation
        test_df_copy = test_df.copy()
        test_df_copy['Pred'] = pipe.predict(test_df[fcols])
        probs = pipe.predict_proba(test_df[fcols])
        test_df_copy['Prob_0'] = probs[:, 0]
        test_df_copy['Prob_1'] = probs[:, 1]
        test_df_copy['Prob_2'] = probs[:, 2]
        
        # Overall Test Metrics
        y_true = test_df_copy['Target_Class'].values
        y_pred = test_df_copy['Pred'].values
        maj_acc = (y_true == pd.Series(y_true).mode()[0]).mean() * 100
        acc = accuracy_score(y_true, y_pred) * 100
        bal_acc = balanced_accuracy_score(y_true, y_pred) * 100
        macro_f1 = f1_score(y_true, y_pred, average='macro', zero_division=0)
        weighted_f1 = f1_score(y_true, y_pred, average='weighted', zero_division=0)
        
        benchmarks.append({
            'Model_Configuration': fset_name,
            'Num_Features': len(fcols),
            'Fit_Time_Sec': round(fit_time, 1),
            'Val_Accuracy': round(val_acc, 2),
            'Val_Balanced_Acc': round(val_bal_acc, 2),
            'Val_Macro_F1': round(val_macro_f1, 4),
            'Test_Majority_Baseline_Acc': round(maj_acc, 2),
            'Test_Accuracy': round(acc, 2),
            'Test_Accuracy_Lift': round(acc - maj_acc, 2),
            'Test_Balanced_Accuracy': round(bal_acc, 2),
            'Test_Macro_F1': round(macro_f1, 4),
            'Test_Weighted_F1': round(weighted_f1, 4)
        })
        
        # Per-Crop Breakdown
        for crop in ['Potato', 'Onion', 'Tomato', 'Wheat']:
            c_df = test_df_copy[test_df_copy['Commodity'] == crop]
            cy_true = c_df['Target_Class'].values
            cy_pred = c_df['Pred'].values
            c_maj = (cy_true == pd.Series(cy_true).mode()[0]).mean() * 100
            c_acc = accuracy_score(cy_true, cy_pred) * 100
            c_bal = balanced_accuracy_score(cy_true, cy_pred) * 100
            c_f1 = f1_score(cy_true, cy_pred, average='macro', zero_division=0)
            
            p_cls = precision_score(cy_true, cy_pred, average=None, labels=[0, 1, 2], zero_division=0)
            r_cls = recall_score(cy_true, cy_pred, average=None, labels=[0, 1, 2], zero_division=0)
            
            crop_benchmarks.append({
                'Configuration': fset_name,
                'Crop': crop,
                'N_Obs': len(c_df),
                'Majority_Acc': round(c_maj, 2),
                'Test_Acc': round(c_acc, 2),
                'Lift': round(c_acc - c_maj, 2),
                'Balanced_Acc': round(c_bal, 2),
                'Macro_F1': round(c_f1, 4),
                'Prec_Unfav': round(p_cls[0], 4),
                'Prec_Fav': round(p_cls[2], 4),
                'Rec_Unfav': round(r_cls[0], 4),
                'Rec_Fav': round(r_cls[2], 4)
            })
            
    b_df = pd.DataFrame(benchmarks)
    cb_df = pd.DataFrame(crop_benchmarks)
    
    b_df.to_csv(os.path.join(RESULTS_DIR, "feature_ablation_overall_comparison.csv"), index=False)
    cb_df.to_csv(os.path.join(RESULTS_DIR, "feature_ablation_crop_comparison.csv"), index=False)
    
    print("\nOVERALL BENCHMARK COMPARISON:")
    print(b_df[['Model_Configuration', 'Num_Features', 'Test_Majority_Baseline_Acc', 'Test_Accuracy', 'Test_Accuracy_Lift', 'Test_Balanced_Accuracy', 'Test_Macro_F1']].to_string(index=False))
    
    print("\nCROP-LEVEL COMPARISON:")
    print(cb_df[['Configuration', 'Crop', 'N_Obs', 'Majority_Acc', 'Test_Acc', 'Lift', 'Balanced_Acc', 'Macro_F1']].to_string(index=False))
    return b_df, cb_df

def main():
    start_time = time.time()
    dataset = load_all_data()
    featured_df = engineer_all_features(dataset)
    train_df, val_df, test_df = split_data(featured_df)
    
    results_df, top_12 = evaluate_and_select_features(train_df)
    b_df, cb_df = benchmark_models(train_df, val_df, test_df, top_12)
    
    elapsed = time.time() - start_time
    print(f"\n[Complete Pipeline Executed] Finished all tests & validations in {elapsed:.1f}s.")

if __name__ == "__main__":
    main()
