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

def load_and_clean_mandi_data(data_dir=".", min_series_records=20):
    """
    Loads all APMC mandi CSVs, verifies schema, drops duplicates, sorts chronologically,
    and filters out low-observation series (< min_series_records).
    """
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
    
    # Standardize types
    df['Arrival_Date'] = pd.to_datetime(df['Arrival_Date'], format='%d/%m/%Y', errors='coerce')
    for p in ['Modal_Price', 'Min_Price', 'Max_Price']:
        df[p] = pd.to_numeric(df[p], errors='coerce')
    
    # Drop rows with invalid price or date
    df = df.dropna(subset=['Arrival_Date', 'Modal_Price', 'District', 'Market', 'Commodity', 'Variety']).copy()
    
    # Deduplicate exact (District, Market, Commodity, Variety, Arrival_Date)
    series_cols = ['District', 'Market', 'Commodity', 'Variety']
    df = df.drop_duplicates(subset=series_cols + ['Arrival_Date'], keep='first').copy()
    
    # Create canonical series_id
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
