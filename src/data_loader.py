"""
Data Loader & Preprocessing Module
APMC Mandi Market Intelligence System
"""

import os
import glob
import pandas as pd
import numpy as np

# Geographic neighbor graph for Uttar Pradesh APMC districts/markets
NEIGHBORING_DISTRICTS = {
    'Lucknow': ['Unnao', 'Kanpur'],
    'Kanpur': ['Unnao', 'Lucknow'],
    'Unnao': ['Kanpur', 'Lucknow'],
    'Ghaziabad': ['Gaziabaad'],  # Contains Noida, Hapur, Muradnagar mandis internally
    'Jhansi': ['Jhansi']         # Regional Bundelkhand hub (Mauranipur, Chirgaon, Baruwasagar)
}

def load_and_clean_mandi_data(data_dir=".", min_series_records=20, exclude_ambiguous_same_grade=True, data_source=None, processed_file=None):
    """
    Loads all APMC mandi CSVs, verifies schema, preserves Grade in series identity,
    filters invalid/non-positive prices, resolves duplicates via Strategy 2 (excluding
    ambiguous same-grade conflicting quotes), sorts chronologically, and filters out
    low-observation series (< min_series_records).
    
    Supports:
    - Default raw 2-year dataset (data/raw/*.csv)
    - 5-year historical dataset (5 year dataset/*.csv via data_source='5_year' or data_dir)
    - Pre-processed dataset (via processed_file='data/processed/mandi_5year_processed.csv')
    """
    if processed_file and os.path.exists(processed_file):
        print(f"[DataLoader] Loading pre-processed mandi dataset from {processed_file}...")
        df_processed = pd.read_csv(processed_file)
        df_processed['Arrival_Date'] = pd.to_datetime(df_processed['Arrival_Date'], errors='coerce')
        return df_processed

    if data_source in ['5_year', '5year', '5_years'] or '5 year' in str(data_dir).lower():
        target_dir = os.path.join(data_dir, "5 year dataset") if not str(data_dir).endswith("5 year dataset") else data_dir
        if not os.path.isdir(target_dir):
            target_dir = os.path.join(".", "5 year dataset")
        csv_files = sorted(glob.glob(os.path.join(target_dir, "*.csv")))
    else:
        csv_files = sorted(glob.glob(os.path.join(data_dir, "data", "raw", "*.csv")))
        if not csv_files:
            csv_files = sorted(glob.glob(os.path.join(data_dir, "*.csv")))
            
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {data_dir} or {os.path.join(data_dir, 'data', 'raw')}")
    
    print(f"[DataLoader] Loading {len(csv_files)} district files...")
    dfs = []
    for f in csv_files:
        df_temp = pd.read_csv(f)
        df_temp['Source_File'] = os.path.basename(f)
        dfs.append(df_temp)
    
    df = pd.concat(dfs, ignore_index=True)
    initial_count = len(df)
    
    # Standardize District naming (e.g. Gaziabaad -> Ghaziabad, Lukhnow -> Lucknow)
    district_clean_map = {
        'Gaziabaad': 'Ghaziabad',
        'Lukhnow': 'Lucknow'
    }
    df['District'] = df['District'].replace(district_clean_map)
    
    # Handle Grade: preserve grade dimension, standardizing null/empty values
    if 'Grade' in df.columns:
        df['Grade'] = df['Grade'].fillna('FAQ').astype(str).str.strip()
        df['Grade'] = df['Grade'].replace({'': 'FAQ', 'nan': 'FAQ', 'None': 'FAQ'})
    else:
        df['Grade'] = 'FAQ'
        
    # Standardize types
    df['Arrival_Date'] = pd.to_datetime(df['Arrival_Date'], format='%d/%m/%Y', errors='coerce')
    for p in ['Modal_Price', 'Min_Price', 'Max_Price']:
        df[p] = pd.to_numeric(df[p], errors='coerce')
    
    # Drop rows with invalid price, non-positive price, or missing metadata
    series_cols = ['District', 'Market', 'Commodity', 'Variety', 'Grade']
    df = df.dropna(subset=['Arrival_Date', 'Modal_Price', 'Min_Price', 'Max_Price'] + series_cols).copy()
    df = df[(df['Modal_Price'] > 0) & (df['Min_Price'] > 0) & (df['Max_Price'] > 0)].copy()
    
    # Duplicate handling on full series key WITH Grade + Arrival_Date
    key_grade = series_cols + ['Arrival_Date']
    
    if exclude_ambiguous_same_grade:
        # Identify duplicate groups
        dup_groups = df.groupby(key_grade).agg(
            n_rows=('Modal_Price', 'count'),
            modal_nunique=('Modal_Price', 'nunique'),
            min_nunique=('Min_Price', 'nunique'),
            max_nunique=('Max_Price', 'nunique')
        )
        # Ambiguous groups: more than 1 row AND differing modal, min, or max prices
        ambiguous_keys = dup_groups[
            (dup_groups['n_rows'] > 1) & 
            ((dup_groups['modal_nunique'] > 1) | (dup_groups['min_nunique'] > 1) | (dup_groups['max_nunique'] > 1))
        ].index
        
        # Exclude ambiguous groups (Strategy 2)
        is_ambiguous = df.set_index(key_grade).index.isin(ambiguous_keys)
        n_ambiguous_rows = int(is_ambiguous.sum())
        df = df[~is_ambiguous].copy()
        print(f"[DataLoader] Strategy 2: Excluded {n_ambiguous_rows:,} ambiguous same-grade conflicting rows across {len(ambiguous_keys):,} dates.")
    
    # Deduplicate exact identical quotes
    df = df.drop_duplicates(subset=key_grade, keep='first').copy()
    
    # Create canonical series_id incorporating Grade
    df['series_id'] = df[series_cols].astype(str).agg('__'.join, axis=1)
    
    # Sort strictly by series and date
    df.sort_values(by=['series_id', 'Arrival_Date'], inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    # Filter out series with fewer than min_series_records
    series_counts = df.groupby('series_id').size()
    valid_series = series_counts[series_counts >= min_series_records].index
    filtered_df = df[df['series_id'].isin(valid_series)].copy()
    filtered_df.reset_index(drop=True, inplace=True)
    
    print(f"[DataLoader] Initial rows: {initial_count:,} | Clean rows: {len(df):,} | Filtered (>= {min_series_records} obs): {len(filtered_df):,}")
    print(f"[DataLoader] Retained series: {filtered_df['series_id'].nunique():,} of {df['series_id'].nunique():,}")
    
    return filtered_df

if __name__ == "__main__":
    df = load_and_clean_mandi_data()
    print("Sample:\n", df.head(3))
