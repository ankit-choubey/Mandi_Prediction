"""
Targeted Data Profiling for Candidate Crops: Potato, Onion, Tomato, Wheat
APMC Mandi Market Intelligence Project
Investigator: Suryansh

Supports both 5-Year Expanded Panel and 2-Year Baseline Datasets.
"""

import os
import sys
import glob
import argparse
import pandas as pd
import numpy as np
from datetime import timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Potential roots
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
WORKSPACE_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))

CANDIDATE_CROPS = ["Potato", "Onion", "Tomato", "Wheat"]


def resolve_data_dir(user_path=None):
    if user_path:
        # Check direct path
        if os.path.isdir(user_path):
            return os.path.abspath(user_path)
        # Check against common anchor directories
        for base in [os.getcwd(), PROJECT_ROOT, WORKSPACE_ROOT, "/kaggle/working/Mandi_Prediction", "/kaggle/working"]:
            p = os.path.join(base, user_path)
            if os.path.isdir(p):
                return os.path.abspath(p)

    # Defaults: prioritize 5 year dataset
    search_dirs = [
        os.path.join(PROJECT_ROOT, "5 year dataset"),
        os.path.join(WORKSPACE_ROOT, "5 year dataset"),
        os.path.join(os.getcwd(), "5 year dataset"),
        "/kaggle/working/Mandi_Prediction/5 year dataset",
        os.path.join(PROJECT_ROOT, "data", "raw"),
        os.path.join(WORKSPACE_ROOT, "data", "raw"),
        os.path.join(os.getcwd(), "data", "raw"),
    ]
    for d in search_dirs:
        if os.path.isdir(d):
            return os.path.abspath(d)
    return user_path or "5 year dataset"


def resolve_output_dir(user_path=None):
    if user_path:
        if os.path.isabs(user_path):
            return user_path
        return os.path.abspath(os.path.join(os.getcwd(), user_path))
    return os.path.join(WORKSPACE_ROOT, "reports", "phase_02_crop_suitability")


def run_candidate_profiling(data_dir=None, output_dir=None, output_suffix="5year"):
    target_data_dir = resolve_data_dir(data_dir)
    target_output_dir = resolve_output_dir(output_dir)
    os.makedirs(target_output_dir, exist_ok=True)
    
    csv_files = sorted(glob.glob(os.path.join(target_data_dir, "*.csv")))
    print(f"Loading raw CSVs from {target_data_dir}...")
    print(f"Found {len(csv_files)} files: {[os.path.basename(f) for f in csv_files]}")
    
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {target_data_dir}")

    dfs = []
    for f in csv_files:
        df_temp = pd.read_csv(f)
        df_temp['Source_File'] = os.path.basename(f)
        dfs.append(df_temp)
    raw_df = pd.concat(dfs, ignore_index=True)
    print(f"Total raw records loaded: {len(raw_df):,}")
    
    # Check column names
    print("Columns present:", list(raw_df.columns))
    has_arrivals = any("arrival" in col.lower() or "volume" in col.lower() or "qty" in col.lower() for col in raw_df.columns)
    print("Arrival quantity field detected:", has_arrivals)

    # Standardize District naming
    district_clean_map = {'Gaziabaad': 'Ghaziabad', 'Lukhnow': 'Lucknow'}
    raw_df['District'] = raw_df['District'].replace(district_clean_map)
    
    # Handle Grade
    if 'Grade' in raw_df.columns:
        raw_df['Grade'] = raw_df['Grade'].fillna('FAQ').astype(str).str.strip()
        raw_df['Grade'] = raw_df['Grade'].replace({'': 'FAQ', 'nan': 'FAQ', 'None': 'FAQ'})
    else:
        raw_df['Grade'] = 'FAQ'

    raw_df['Arrival_Date'] = pd.to_datetime(raw_df['Arrival_Date'], format='%d/%m/%Y', errors='coerce')
    for p in ['Modal_Price', 'Min_Price', 'Max_Price']:
        raw_df[p] = pd.to_numeric(raw_df[p], errors='coerce')

    # Overall dataset metrics
    print("\n--- Overall Dataset Overview ---")
    print(f"Unique Commodities in raw: {raw_df['Commodity'].nunique()}")
    print("Candidate crops present in raw:")
    for crop in CANDIDATE_CROPS:
        cnt = (raw_df['Commodity'] == crop).sum()
        print(f"  - {crop}: {cnt:,} raw rows")

    # Filter to candidate crops
    cand_df = raw_df[raw_df['Commodity'].isin(CANDIDATE_CROPS)].copy()
    
    # Data Quality Checks per crop
    # 1. Price order violations: Min <= Modal <= Max
    cand_df['Price_Order_Valid'] = (cand_df['Min_Price'] <= cand_df['Modal_Price']) & (cand_df['Modal_Price'] <= cand_df['Max_Price'])
    # 2. Non-positive prices
    cand_df['Positive_Price'] = (cand_df['Modal_Price'] > 0) & (cand_df['Min_Price'] > 0) & (cand_df['Max_Price'] > 0)
    
    # Series key
    series_cols = ['District', 'Market', 'Commodity', 'Variety', 'Grade']
    cand_df['series_id'] = cand_df[series_cols].astype(str).agg('__'.join, axis=1)

    # Clean data filtering following Strategy 2 (exclude ambiguous same-grade conflicting quotes)
    key_grade = series_cols + ['Arrival_Date']
    dup_groups = cand_df.groupby(key_grade).agg(
        n_rows=('Modal_Price', 'count'),
        modal_nunique=('Modal_Price', 'nunique'),
        min_nunique=('Min_Price', 'nunique'),
        max_nunique=('Max_Price', 'nunique')
    )
    ambiguous_keys = dup_groups[
        (dup_groups['n_rows'] > 1) & 
        ((dup_groups['modal_nunique'] > 1) | (dup_groups['min_nunique'] > 1) | (dup_groups['max_nunique'] > 1))
    ].index

    cand_df['is_ambiguous'] = cand_df.set_index(key_grade).index.isin(ambiguous_keys)
    
    # Deduplicated clean dataset
    clean_df = cand_df[
        cand_df['Positive_Price'] & 
        (~cand_df['is_ambiguous'])
    ].drop_duplicates(subset=key_grade, keep='first').copy()
    
    clean_df.sort_values(by=['series_id', 'Arrival_Date'], inplace=True)
    clean_df.reset_index(drop=True, inplace=True)

    # Exact calendar T+7 matching
    t7_lookup = clean_df[['series_id', 'Arrival_Date', 'Modal_Price', 'Min_Price', 'Max_Price']].copy()
    clean_df['Target_Date'] = clean_df['Arrival_Date'] + timedelta(days=7)
    
    matched = pd.merge(
        clean_df,
        t7_lookup,
        left_on=['series_id', 'Target_Date'],
        right_on=['series_id', 'Arrival_Date'],
        suffixes=('', '_T7'),
        how='inner'
    )
    
    matched['Return_7d'] = ((matched['Modal_Price_T7'] - matched['Modal_Price']) / matched['Modal_Price']) * 100
    
    # DEC-015 thresholds
    matched['Class_DEC015'] = np.select(
        [matched['Return_7d'] > 2.5, matched['Return_7d'] < -2.5],
        ['Favorable', 'Unfavorable'],
        default='Normal'
    )
    
    # Chronological partition flags
    # Train: <= 2026-01-17
    # Val: 2026-01-25 to 2026-03-31
    # Test: >= 2026-04-08
    matched['Partition'] = 'Embargo'
    matched.loc[matched['Arrival_Date'] <= pd.Timestamp('2026-01-17'), 'Partition'] = 'Train'
    matched.loc[(matched['Arrival_Date'] >= pd.Timestamp('2026-01-25')) & (matched['Arrival_Date'] <= pd.Timestamp('2026-03-31')), 'Partition'] = 'Val'
    matched.loc[matched['Arrival_Date'] >= pd.Timestamp('2026-04-08'), 'Partition'] = 'Exploratory_Test'

    # Now compile metrics per crop
    crop_metrics = []
    
    for crop in CANDIDATE_CROPS:
        raw_crop = cand_df[cand_df['Commodity'] == crop]
        clean_crop = clean_df[clean_df['Commodity'] == crop]
        matched_crop = matched[matched['Commodity'] == crop]
        
        # Date metrics
        min_date = clean_crop['Arrival_Date'].min()
        max_date = clean_crop['Arrival_Date'].max()
        unique_dates = clean_crop['Arrival_Date'].nunique()
        calendar_span_days = (max_date - min_date).days + 1 if pd.notnull(min_date) else 0
        
        # Continuity / Gaps per series
        gaps_list = []
        for s_id, s_df in clean_crop.groupby('series_id'):
            s_dates = s_df['Arrival_Date'].sort_values()
            gaps = (s_dates.diff().dt.days).dropna()
            gaps_list.extend(gaps.tolist())
            
        gaps_series = pd.Series(gaps_list) if gaps_list else pd.Series([np.nan])
        pct_consecutive_1d = (gaps_series == 1).mean() * 100 if len(gaps_series) > 0 else 0
        median_gap = gaps_series.median() if len(gaps_series) > 0 else np.nan
        max_gap = gaps_series.max() if len(gaps_series) > 0 else np.nan
        
        # Districts and Mandis
        districts = sorted(clean_crop['District'].unique())
        n_districts = len(districts)
        mandis = sorted(clean_crop['Market'].unique())
        n_mandis = len(mandis)
        canonical_series = clean_crop['series_id'].nunique()
        
        # Data Quality
        price_order_valid_pct = (raw_crop['Price_Order_Valid']).mean() * 100
        positive_price_pct = (raw_crop['Positive_Price']).mean() * 100
        ambiguous_rows_cnt = raw_crop['is_ambiguous'].sum()
        ambiguous_rows_pct = ambiguous_rows_cnt / len(raw_crop) * 100 if len(raw_crop) > 0 else 0
        
        # T+7 Matching Feasibility
        matched_count = len(matched_crop)
        t7_availability_pct = (matched_count / len(clean_crop) * 100) if len(clean_crop) > 0 else 0
        
        # 7-day return distribution
        ret = matched_crop['Return_7d']
        ret_mean = ret.mean() if len(ret) > 0 else np.nan
        ret_std = ret.std() if len(ret) > 0 else np.nan
        ret_median = ret.median() if len(ret) > 0 else np.nan
        ret_iqr = (ret.quantile(0.75) - ret.quantile(0.25)) if len(ret) > 0 else np.nan
        ret_min = ret.min() if len(ret) > 0 else np.nan
        ret_max = ret.max() if len(ret) > 0 else np.nan
        
        # Class distribution overall
        cls_counts = matched_crop['Class_DEC015'].value_counts(normalize=True) * 100
        pct_norm = cls_counts.get('Normal', 0.0)
        pct_fav = cls_counts.get('Favorable', 0.0)
        pct_unfav = cls_counts.get('Unfavorable', 0.0)
        
        # Partition breakdown
        train_n = (matched_crop['Partition'] == 'Train').sum()
        val_n = (matched_crop['Partition'] == 'Val').sum()
        test_n = (matched_crop['Partition'] == 'Exploratory_Test').sum()
        
        test_part = matched_crop[matched_crop['Partition'] == 'Exploratory_Test']
        test_cls_counts = test_part['Class_DEC015'].value_counts()
        test_norm = test_cls_counts.get('Normal', 0)
        test_fav = test_cls_counts.get('Favorable', 0)
        test_unfav = test_cls_counts.get('Unfavorable', 0)
        
        crop_metrics.append({
            'Crop': crop,
            'Raw_Rows': len(raw_crop),
            'Clean_Rows': len(clean_crop),
            'Price_Order_Valid_Pct': round(price_order_valid_pct, 2),
            'Positive_Price_Pct': round(positive_price_pct, 2),
            'Ambiguous_Conflicting_Rows': ambiguous_rows_cnt,
            'Ambiguous_Conflicting_Pct': round(ambiguous_rows_pct, 2),
            'Canonical_Series_Count': canonical_series,
            'District_Count': n_districts,
            'Districts_List': ", ".join(districts),
            'Market_Count': n_mandis,
            'Min_Date': str(min_date.date()) if pd.notnull(min_date) else None,
            'Max_Date': str(max_date.date()) if pd.notnull(max_date) else None,
            'Unique_Trading_Dates': unique_dates,
            'Calendar_Span_Days': calendar_span_days,
            'Consecutive_1Day_Gaps_Pct': round(pct_consecutive_1d, 2),
            'Median_Gap_Days': median_gap,
            'Max_Gap_Days': max_gap,
            'Matched_T7_Pairs': matched_count,
            'T7_Availability_Pct': round(t7_availability_pct, 2),
            'Return_7d_Mean_Pct': round(ret_mean, 2),
            'Return_7d_Std_Pct': round(ret_std, 2),
            'Return_7d_Median_Pct': round(ret_median, 2),
            'Return_7d_IQR_Pct': round(ret_iqr, 2),
            'Return_7d_Min_Pct': round(ret_min, 2),
            'Return_7d_Max_Pct': round(ret_max, 2),
            'Class_Normal_Pct': round(pct_norm, 2),
            'Class_Favorable_Pct': round(pct_fav, 2),
            'Class_Unfavorable_Pct': round(pct_unfav, 2),
            'Train_Pairs_Count': train_n,
            'Val_Pairs_Count': val_n,
            'Test_Pairs_Count': test_n,
            'Test_Class_Normal_Count': test_norm,
            'Test_Class_Favorable_Count': test_fav,
            'Test_Class_Unfavorable_Count': test_unfav,
        })
        
    metrics_df = pd.DataFrame(crop_metrics)
    csv_out_path = os.path.join(target_output_dir, f"measured_crop_metrics_{output_suffix}.csv")
    metrics_df.to_csv(csv_out_path, index=False)
    print(f"\nSaved {output_suffix} measured metrics to: {csv_out_path}")
    
    # Also update canonical measured_crop_metrics.csv
    canonical_path = os.path.join(target_output_dir, "measured_crop_metrics.csv")
    metrics_df.to_csv(canonical_path, index=False)
    print(f"Updated canonical metrics to: {canonical_path}")
    
    return metrics_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Profile candidate agricultural commodities.")
    parser.add_argument("--data-dir", type=str, default=None, help="Path to raw CSV dataset.")
    parser.add_argument("--output-dir", type=str, default=None, help="Path to reports directory.")
    parser.add_argument("--suffix", type=str, default="5year", help="File suffix for metrics CSV.")
    args = parser.parse_args()
    
    df = run_candidate_profiling(data_dir=args.data_dir, output_dir=args.output_dir, output_suffix=args.suffix)
    print("\nSummary Results:")
    print(df[['Crop', 'Raw_Rows', 'Clean_Rows', 'Canonical_Series_Count', 'Matched_T7_Pairs', 'T7_Availability_Pct', 'Return_7d_Std_Pct', 'Class_Normal_Pct']])
