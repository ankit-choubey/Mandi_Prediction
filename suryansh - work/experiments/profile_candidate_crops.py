"""
Targeted Data Profiling for Candidate Crops: Potato, Onion, Tomato, Wheat
APMC Mandi Market Intelligence Project
Investigator: Suryansh
"""

import os
import glob
import pandas as pd
import numpy as np
from datetime import timedelta

RAW_DATA_DIR = "/Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction/data/raw"
OUTPUT_DIR = "/Users/kumarsuryansh/Desktop/Temporary/suryansh - work/reports/phase_02_crop_suitability"
CANDIDATE_CROPS = ["Potato", "Onion", "Tomato", "Wheat"]

def run_candidate_profiling():
    csv_files = sorted(glob.glob(os.path.join(RAW_DATA_DIR, "*.csv")))
    print(f"Loading raw CSVs from {RAW_DATA_DIR}...")
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
        varieties = sorted(clean_crop['Variety'].unique())
        n_varieties = len(varieties)
        grades = sorted(clean_crop['Grade'].unique())
        n_grades = len(grades)
        n_series = clean_crop['series_id'].nunique()
        
        # Prices
        prices = clean_crop['Modal_Price']
        p_mean = prices.mean()
        p_std = prices.std()
        p_min = prices.min()
        p_25 = prices.quantile(0.25)
        p_med = prices.median()
        p_75 = prices.quantile(0.75)
        p_max = prices.max()
        
        # Intraday spread
        spread = clean_crop['Max_Price'] - clean_crop['Min_Price']
        spread_ratio = (spread / clean_crop['Modal_Price']) * 100
        mean_spread_pct = spread_ratio.mean()
        
        # Matching & T+7
        raw_rows = len(raw_crop)
        clean_rows = len(clean_crop)
        matched_pairs = len(matched_crop)
        t7_match_rate = (matched_pairs / clean_rows * 100) if clean_rows > 0 else 0
        
        # Target returns & Volatility
        returns = matched_crop['Return_7d']
        r_mean = returns.mean()
        r_std = returns.std()
        r_med = returns.median()
        zero_return_pct = (returns == 0.0).mean() * 100 if len(returns) > 0 else 0
        
        # Class distribution
        class_counts = matched_crop['Class_DEC015'].value_counts()
        n_fav = class_counts.get('Favorable', 0)
        n_norm = class_counts.get('Normal', 0)
        n_unfav = class_counts.get('Unfavorable', 0)
        
        pct_fav = (n_fav / matched_pairs * 100) if matched_pairs > 0 else 0
        pct_norm = (n_norm / matched_pairs * 100) if matched_pairs > 0 else 0
        pct_unfav = (n_unfav / matched_pairs * 100) if matched_pairs > 0 else 0
        
        # Partition breakdown
        train_n = (matched_crop['Partition'] == 'Train').sum()
        val_n = (matched_crop['Partition'] == 'Val').sum()
        test_n = (matched_crop['Partition'] == 'Exploratory_Test').sum()
        
        # Test partition class balance
        test_crop = matched_crop[matched_crop['Partition'] == 'Exploratory_Test']
        test_fav = (test_crop['Class_DEC015'] == 'Favorable').sum()
        test_norm = (test_crop['Class_DEC015'] == 'Normal').sum()
        test_unfav = (test_crop['Class_DEC015'] == 'Unfavorable').sum()

        crop_metrics.append({
            'Crop': crop,
            'Raw_Rows': raw_rows,
            'Clean_Rows': clean_rows,
            'Excluded_Conflicting_Rows': raw_crop['is_ambiguous'].sum(),
            'Price_Order_Violations': (~raw_crop['Price_Order_Valid']).sum(),
            'Non_Positive_Price_Rows': (~raw_crop['Positive_Price']).sum(),
            'Unique_Districts_Count': n_districts,
            'Districts_List': "; ".join(districts),
            'Unique_Markets_Count': n_mandis,
            'Unique_Varieties_Count': n_varieties,
            'Top_Varieties': "; ".join(clean_crop['Variety'].value_counts().head(3).index),
            'Unique_Grades_Count': n_grades,
            'Grades_List': "; ".join(grades),
            'Canonical_Series_Count': n_series,
            'Date_Min': min_date.strftime('%Y-%m-%d') if pd.notnull(min_date) else 'N/A',
            'Date_Max': max_date.strftime('%Y-%m-%d') if pd.notnull(max_date) else 'N/A',
            'Calendar_Span_Days': calendar_span_days,
            'Unique_Dates_Count': unique_dates,
            'Pct_Consecutive_1d_Gaps': round(pct_consecutive_1d, 2),
            'Median_Gap_Days': median_gap,
            'Max_Gap_Days': max_gap,
            'Price_Mean_Rs': round(p_mean, 2),
            'Price_Std_Rs': round(p_std, 2),
            'Price_Min_Rs': round(p_min, 2),
            'Price_Q25_Rs': round(p_25, 2),
            'Price_Median_Rs': round(p_med, 2),
            'Price_Q75_Rs': round(p_75, 2),
            'Price_Max_Rs': round(p_max, 2),
            'Mean_Intraday_Spread_Pct': round(mean_spread_pct, 2),
            'Matched_T7_Pairs': matched_pairs,
            'T7_Availability_Pct': round(t7_match_rate, 2),
            'Return_7d_Mean_Pct': round(r_mean, 2),
            'Return_7d_Std_Pct': round(r_std, 2),
            'Return_7d_Median_Pct': round(r_med, 2),
            'Exact_Zero_Return_Pct': round(zero_return_pct, 2),
            'Class_Normal_Count': n_norm,
            'Class_Normal_Pct': round(pct_norm, 2),
            'Class_Favorable_Count': n_fav,
            'Class_Favorable_Pct': round(pct_fav, 2),
            'Class_Unfavorable_Count': n_unfav,
            'Class_Unfavorable_Pct': round(pct_unfav, 2),
            'Train_Pairs_Count': train_n,
            'Val_Pairs_Count': val_n,
            'Test_Pairs_Count': test_n,
            'Test_Class_Normal_Count': test_norm,
            'Test_Class_Favorable_Count': test_fav,
            'Test_Class_Unfavorable_Count': test_unfav,
        })
        
    metrics_df = pd.DataFrame(crop_metrics)
    csv_out_path = os.path.join(OUTPUT_DIR, "measured_crop_metrics.csv")
    metrics_df.to_csv(csv_out_path, index=False)
    print(f"\nSaved measured metrics to: {csv_out_path}")
    return metrics_df

if __name__ == "__main__":
    df = run_candidate_profiling()
    print("\nSummary Results:")
    print(df[['Crop', 'Raw_Rows', 'Clean_Rows', 'Canonical_Series_Count', 'Matched_T7_Pairs', 'T7_Availability_Pct', 'Return_7d_Std_Pct', 'Class_Normal_Pct']])
