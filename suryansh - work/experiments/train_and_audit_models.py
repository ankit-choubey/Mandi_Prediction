"""
Self-Contained Training, Feature Evaluation, and Parameter Matrix Audit
APMC Mandi Market Intelligence System
Investigator: Suryansh
"""

import os
import sys
import time
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

from datetime import timedelta
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import (
    RandomForestClassifier,
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    VotingClassifier
)
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
    log_loss
)

WORKSPACE_ROOT = "/Users/kumarsuryansh/Desktop/Temporary/suryansh - work"
DATA_DIR = "/Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction/data/raw"
OUTPUT_DIR = os.path.join(WORKSPACE_ROOT, "reports", "phase_03_classification_protocol")
FIGURES_DIR = os.path.join(WORKSPACE_ROOT, "figures")
LOGS_DIR = os.path.join(WORKSPACE_ROOT, "logs")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(FIGURES_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# -----------------------------------------------------------------------------
# 1. DATA INGESTION & CLEANING (Strategy 2)
# -----------------------------------------------------------------------------
def load_data():
    csv_files = sorted([os.path.join(DATA_DIR, f) for f in os.listdir(DATA_DIR) if f.endswith('.csv')])
    print(f"[DataLoader] Ingesting {len(csv_files)} raw district files...")
    dfs = [pd.read_csv(f) for f in csv_files]
    df = pd.concat(dfs, ignore_index=True)
    raw_count = len(df)
    
    # Standardize district naming
    district_clean_map = {'Gaziabaad': 'Ghaziabad', 'Lukhnow': 'Lucknow'}
    df['District'] = df['District'].replace(district_clean_map)
    
    # Grade handling
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
    
    # Filter min records
    series_counts = df.groupby('series_id').size()
    valid_series = series_counts[series_counts >= 20].index
    filtered_df = df[df['series_id'].isin(valid_series)].copy()
    filtered_df.reset_index(drop=True, inplace=True)
    print(f"[DataLoader] Raw rows: {raw_count:,} | Clean rows: {len(filtered_df):,} across {filtered_df['series_id'].nunique():,} series.")
    return filtered_df

# -----------------------------------------------------------------------------
# 2. FEATURE ENGINEERING & TARGET FORMULATION
# -----------------------------------------------------------------------------
NEIGHBORING_DISTRICTS = {
    'Lucknow': ['Unnao', 'Kanpur'],
    'Kanpur': ['Unnao', 'Lucknow'],
    'Unnao': ['Kanpur', 'Lucknow'],
    'Ghaziabad': ['Gaziabaad'],
    'Jhansi': ['Jhansi']
}

FEATURE_COLUMNS = [
    'Modal_Price', 'Min_Price', 'Max_Price', 'Price_Intraday_Spread', 'Price_Intraday_Spread_Ratio',
    'Lag_Price_1', 'Lag_Price_3', 'Lag_Price_7', 'Price_Change_1d', 'Price_Change_3d', 'Price_Change_7d',
    'Roll_Mean_Price_3', 'Roll_Mean_Price_7', 'Roll_Std_Price_7', 'Price_to_RollMean3_Ratio', 'Price_to_RollMean7_Ratio',
    'Month', 'DayOfWeek', 'DayOfMonth', 'Quarter', 'Season',
    'District_Commodity_MeanPrice', 'District_Commodity_MandiCount', 'Mandi_vs_District_Ratio',
    'Neighbor_Commodity_MeanPrice', 'Price_Diff_Target_vs_Neighbor', 'Price_Ratio_Target_vs_Neighbor'
]

def engineer_features_and_target(df):
    print("[FeatureEngineering] Constructing 27 features and exact T+7 target...")
    df = df.copy()
    
    # 1. Intraday spread
    df['Price_Intraday_Spread'] = df['Max_Price'] - df['Min_Price']
    df['Price_Intraday_Spread_Ratio'] = df['Price_Intraday_Spread'] / (df['Modal_Price'] + 1e-5)
    
    # 2. Exact calendar lags (T-1, T-3, T-7)
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
    
    # 3. Rolling stats & causal volatility
    grouped = df.groupby('series_id')
    df['Roll_Mean_Price_3'] = grouped['Modal_Price'].transform(lambda s: s.rolling(window=3, min_periods=1).mean())
    df['Roll_Mean_Price_7'] = grouped['Modal_Price'].transform(lambda s: s.rolling(window=7, min_periods=1).mean())
    df['Roll_Std_Price_7'] = grouped['Modal_Price'].transform(lambda s: s.rolling(window=7, min_periods=3).std())
    df['Price_to_RollMean3_Ratio'] = df['Modal_Price'] / (df['Roll_Mean_Price_3'] + 1e-5)
    df['Price_to_RollMean7_Ratio'] = df['Modal_Price'] / (df['Roll_Mean_Price_7'] + 1e-5)
    
    # 4. Seasonality
    df['Month'] = df['Arrival_Date'].dt.month
    df['DayOfWeek'] = df['Arrival_Date'].dt.dayofweek
    df['DayOfMonth'] = df['Arrival_Date'].dt.day
    df['Quarter'] = df['Arrival_Date'].dt.quarter
    
    def get_season(m):
        return 1 if m in [7, 8, 9, 10] else (2 if m in [11, 12, 1, 2, 3] else 3)
    df['Season'] = df['Month'].apply(get_season)
    
    # 5. District aggregations
    district_agg = df.groupby(['District', 'Commodity', 'Arrival_Date'])['Modal_Price'].agg(
        District_Commodity_MeanPrice='mean',
        District_Commodity_MandiCount='count'
    ).reset_index()
    df = pd.merge(df, district_agg, on=['District', 'Commodity', 'Arrival_Date'], how='left')
    df['Mandi_vs_District_Ratio'] = df['Modal_Price'] / (df['District_Commodity_MeanPrice'] + 1e-5)
    
    # 6. Spatial Neighbor Intelligence
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
    
    # 7. Exact Calendar T+7 Target Matching
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
    print(f"[FeatureEngineering] Valid paired records: {len(matched):,}")
    return matched

# -----------------------------------------------------------------------------
# 3. CHRONOLOGICAL PARTITIONING WITH EMBARGO
# -----------------------------------------------------------------------------
def split_data(df, horizon_days=7):
    sorted_df = df.sort_values('Arrival_Date').reset_index(drop=True)
    dates = sorted_df['Arrival_Date'].drop_duplicates().sort_values().reset_index(drop=True)
    
    n_dates = len(dates)
    train_end_idx = int(n_dates * 0.70)
    val_end_idx = int(n_dates * 0.85)
    
    train_cutoff = dates.iloc[train_end_idx]
    val_cutoff = dates.iloc[val_end_idx]
    
    train_embargo_cutoff = train_cutoff - pd.Timedelta(days=horizon_days + 1)
    val_embargo_cutoff = val_cutoff - pd.Timedelta(days=horizon_days + 1)
    
    train_df = sorted_df[sorted_df['Arrival_Date'] <= train_embargo_cutoff].copy()
    val_df = sorted_df[(sorted_df['Arrival_Date'] >= train_cutoff) & (sorted_df['Arrival_Date'] <= val_embargo_cutoff)].copy()
    test_df = sorted_df[sorted_df['Arrival_Date'] >= val_cutoff].copy()
    
    print(f"[Split] Train: {len(train_df):,} | Val: {len(val_df):,} | Test: {len(test_df):,}")
    return train_df, val_df, test_df

# -----------------------------------------------------------------------------
# 4. MODEL SUITE & HYPERPARAMETER MATRIX
# -----------------------------------------------------------------------------
MODEL_CONFIGS = {
    'Decision Tree': {
        'model': DecisionTreeClassifier(max_depth=8, min_samples_leaf=20, class_weight='balanced', random_state=42),
        'params': {'max_depth': 8, 'min_samples_leaf': 20, 'class_weight': 'balanced', 'random_state': 42}
    },
    'Random Forest': {
        'model': RandomForestClassifier(n_estimators=100, max_depth=12, min_samples_leaf=15, class_weight='balanced', n_jobs=-1, random_state=42),
        'params': {'n_estimators': 100, 'max_depth': 12, 'min_samples_leaf': 15, 'class_weight': 'balanced', 'random_state': 42}
    },
    'Extra Trees': {
        'model': ExtraTreesClassifier(n_estimators=100, max_depth=12, min_samples_leaf=15, class_weight='balanced', n_jobs=-1, random_state=42),
        'params': {'n_estimators': 100, 'max_depth': 12, 'min_samples_leaf': 15, 'class_weight': 'balanced', 'random_state': 42}
    },
    'Gradient Boosting': {
        'model': GradientBoostingClassifier(n_estimators=100, max_depth=5, learning_rate=0.1, random_state=42),
        'params': {'n_estimators': 100, 'max_depth': 5, 'learning_rate': 0.1, 'random_state': 42}
    },
    'Soft-Voting Ensemble': {
        'model': VotingClassifier(
            estimators=[
                ('gb', GradientBoostingClassifier(n_estimators=80, max_depth=4, learning_rate=0.1, random_state=42)),
                ('rf', RandomForestClassifier(n_estimators=80, max_depth=10, min_samples_leaf=15, class_weight='balanced', n_jobs=-1, random_state=42)),
                ('et', ExtraTreesClassifier(n_estimators=80, max_depth=10, min_samples_leaf=15, class_weight='balanced', n_jobs=-1, random_state=42))
            ],
            voting='soft'
        ),
        'params': {'voting': 'soft', 'weights': 'equal [GB(80,d4), RF(80,d10), ET(80,d10)]'}
    }
}

# -----------------------------------------------------------------------------
# 5. EXECUTION & EVALUATION
# -----------------------------------------------------------------------------
def run_live_pipeline():
    start_time = time.time()
    raw_df = load_data()
    dataset = engineer_features_and_target(raw_df)
    train_df, val_df, test_df = split_data(dataset)
    
    X_train = train_df[FEATURE_COLUMNS]
    y_train = train_df['Target_Class']
    X_val = val_df[FEATURE_COLUMNS]
    y_val = val_df['Target_Class']
    X_test = test_df[FEATURE_COLUMNS]
    y_test = test_df['Target_Class']
    
    # Save parameter matrix
    param_records = []
    for name, cfg in MODEL_CONFIGS.items():
        param_records.append({
            'Model_Name': name,
            'Preprocessing': 'SimpleImputer(strategy=median)',
            'Hyperparameters': str(cfg['params'])
        })
    pd.DataFrame(param_records).to_csv(os.path.join(OUTPUT_DIR, "live_model_parameter_matrix.csv"), index=False)
    
    # Train models
    fitted_pipelines = {}
    val_macro_f1s = {}
    print("\n" + "=" * 80)
    print("STAGE 1: TRAINING & VALIDATION CANDIDATE SELECTION")
    print("=" * 80)
    for name, cfg in MODEL_CONFIGS.items():
        print(f"Training {name} on {len(X_train):,} training records...")
        t0 = time.time()
        pipe = Pipeline([
            ('imputer', SimpleImputer(strategy='median')),
            ('classifier', cfg['model'])
        ])
        pipe.fit(X_train, y_train)
        fitted_pipelines[name] = pipe
        t_fit = time.time() - t0
        
        y_val_pred = pipe.predict(X_val)
        val_acc = accuracy_score(y_val, y_val_pred)
        val_f1 = f1_score(y_val, y_val_pred, average='macro', zero_division=0)
        val_macro_f1s[name] = val_f1
        print(f"  --> {name}: Fitted in {t_fit:.1f}s | Val Acc: {val_acc*100:.2f}% | Val Macro F1: {val_f1:.4f}")
        
    best_model_name = max(val_macro_f1s, key=val_macro_f1s.get)
    print(f"\nPRIMARY CANDIDATE SELECTED ON VALIDATION MACRO F1: '{best_model_name}' ({val_macro_f1s[best_model_name]:.4f})")
    
    # Feature Importances from RF and GB
    rf_pipe = fitted_pipelines['Random Forest']
    rf_importances = rf_pipe.named_steps['classifier'].feature_importances_
    gb_pipe = fitted_pipelines['Gradient Boosting']
    gb_importances = gb_pipe.named_steps['classifier'].feature_importances_
    
    fi_df = pd.DataFrame({
        'Feature_Name': FEATURE_COLUMNS,
        'Random_Forest_MDI': rf_importances,
        'Gradient_Boosting_MDI': gb_importances,
        'Average_Importance': (rf_importances + gb_importances) / 2
    }).sort_values(by='Average_Importance', ascending=False).reset_index(drop=True)
    fi_df['Rank'] = np.arange(1, len(fi_df) + 1)
    fi_df.to_csv(os.path.join(OUTPUT_DIR, "live_feature_importance_matrix.csv"), index=False)
    
    # Plot Feature Importance
    plt.figure(figsize=(10, 8), dpi=200)
    plt.barh(fi_df['Feature_Name'].iloc[::-1], fi_df['Average_Importance'].iloc[::-1], color='#1f77b4')
    plt.title('Feature Importance (Mean of RF and GB MDI)', fontsize=12, weight='bold')
    plt.xlabel('Importance Score')
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURES_DIR, "live_feature_importance_ranking.png"))
    plt.close()
    
    # STAGE 2: TEST EVALUATION ACROSS ALL CROPS AND THE 4 APPROVED CROPS
    print("\n" + "=" * 80)
    print("STAGE 2: EVALUATION ON HELD-OUT TEST PARTITION (OVERALL & PER-CROP)")
    print("=" * 80)
    
    performance_records = []
    primary_pipe = fitted_pipelines[best_model_name]
    
    test_df_copy = test_df.copy()
    test_df_copy['Predicted_Class'] = primary_pipe.predict(X_test)
    probs = primary_pipe.predict_proba(X_test)
    test_df_copy['Prob_Unfav'] = probs[:, 0]
    test_df_copy['Prob_Norm'] = probs[:, 1]
    test_df_copy['Prob_Fav'] = probs[:, 2]
    
    subgroups = [("ALL_CROPS", test_df_copy)] + [
        (crop, test_df_copy[test_df_copy['Commodity'] == crop])
        for crop in ["Potato", "Onion", "Tomato", "Wheat"]
    ]
    
    for sub_name, sub_df in subgroups:
        y_true = sub_df['Target_Class'].values
        y_pred = sub_df['Predicted_Class'].values
        
        maj_class = pd.Series(y_true).mode()[0]
        maj_acc = (y_true == maj_class).mean() * 100
        acc = accuracy_score(y_true, y_pred) * 100
        bal_acc = balanced_accuracy_score(y_true, y_pred) * 100
        f1_macro = f1_score(y_true, y_pred, average='macro', zero_division=0)
        f1_weighted = f1_score(y_true, y_pred, average='weighted', zero_division=0)
        
        p_class = precision_score(y_true, y_pred, average=None, labels=[0, 1, 2], zero_division=0)
        r_class = recall_score(y_true, y_pred, average=None, labels=[0, 1, 2], zero_division=0)
        f1_class = f1_score(y_true, y_pred, average=None, labels=[0, 1, 2], zero_division=0)
        supp = np.bincount(y_true, minlength=3)
        
        # Log loss
        p_matrix = sub_df[['Prob_Unfav', 'Prob_Norm', 'Prob_Fav']].values
        p_matrix = np.clip(p_matrix, 1e-15, 1 - 1e-15)
        p_matrix = p_matrix / p_matrix.sum(axis=1, keepdims=True)
        ll = log_loss(y_true, p_matrix, labels=[0, 1, 2])
        
        cm = confusion_matrix(y_true, y_pred, labels=[0, 1, 2])
        
        performance_records.append({
            'Model': best_model_name,
            'Subgroup': sub_name,
            'N_Test_Obs': len(sub_df),
            'Majority_Baseline_Acc': round(maj_acc, 2),
            'Model_Test_Acc': round(acc, 2),
            'Accuracy_Lift': round(acc - maj_acc, 2),
            'Balanced_Accuracy': round(bal_acc, 2),
            'Macro_F1': round(f1_macro, 4),
            'Weighted_F1': round(f1_weighted, 4),
            'Log_Loss': round(ll, 4),
            'Supp_Unfav': supp[0], 'Supp_Norm': supp[1], 'Supp_Fav': supp[2],
            'Prec_Unfav': round(p_class[0], 4), 'Prec_Norm': round(p_class[1], 4), 'Prec_Fav': round(p_class[2], 4),
            'Rec_Unfav': round(r_class[0], 4), 'Rec_Norm': round(r_class[1], 4), 'Rec_Fav': round(r_class[2], 4),
            'F1_Unfav': round(f1_class[0], 4), 'F1_Norm': round(f1_class[1], 4), 'F1_Fav': round(f1_class[2], 4),
            'CM_00': cm[0, 0], 'CM_01': cm[0, 1], 'CM_02': cm[0, 2],
            'CM_10': cm[1, 0], 'CM_11': cm[1, 1], 'CM_12': cm[1, 2],
            'CM_20': cm[2, 0], 'CM_21': cm[2, 1], 'CM_22': cm[2, 2]
        })
        
        # Save confusion matrix plot
        plt.figure(figsize=(5, 4), dpi=200)
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                    xticklabels=['Unfav', 'Normal', 'Fav'], yticklabels=['Unfav', 'Normal', 'Fav'])
        plt.title(f'CM: {best_model_name} on {sub_name}')
        plt.xlabel('Predicted Condition')
        plt.ylabel('True Condition')
        plt.tight_layout()
        plt.savefig(os.path.join(FIGURES_DIR, f"live_cm_{sub_name.lower()}.png"))
        plt.close()
        
    perf_df = pd.DataFrame(performance_records)
    perf_df.to_csv(os.path.join(OUTPUT_DIR, "live_baseline_performance_matrix.csv"), index=False)
    
    elapsed = time.time() - start_time
    print(f"\n[Execution Completed] Full training and evaluation pipeline executed in {elapsed:.1f}s.")
    return perf_df, fi_df

if __name__ == "__main__":
    p_df, f_df = run_live_pipeline()
    print("\nLIVE TEST BENCHMARK RESULTS:")
    print(p_df[['Subgroup', 'N_Test_Obs', 'Majority_Baseline_Acc', 'Model_Test_Acc', 'Accuracy_Lift', 'Balanced_Accuracy', 'Macro_F1']].to_string(index=False))
    print("\nTOP 10 FINAL FEATURES BY IMPORTANCE:")
    print(f_df[['Rank', 'Feature_Name', 'Average_Importance']].head(10).to_string(index=False))
