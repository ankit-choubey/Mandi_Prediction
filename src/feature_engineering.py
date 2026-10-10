"""
Feature Engineering & Target Generation Module
APMC Mandi Market Intelligence System
Strictly prevents lookahead leakage. All features at row T use data <= T.
Target is computed from exact T+7 calendar day observation.
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
from datetime import timedelta
from src.data_loader import NEIGHBORING_DISTRICTS

def get_indian_agri_season(month):
    """
    Kharif: July to October (7 - 10)
    Rabi: October/November to March (11, 12, 1, 2, 3)
    Zaid (Summer): April to June (4, 5, 6)
    """
    if month in [7, 8, 9, 10]:
        return 1 # Kharif
    elif month in [11, 12, 1, 2, 3]:
        return 2 # Rabi
    else:
        return 3 # Zaid

def build_features_and_target(df, threshold_pct=2.5):
    print("[FeatureEngineering] Starting feature engineering and target construction...")
    df = df.copy()
    
    # ---------------------------------------------------------
    # 1. Base Intraday Spread Features at T
    # ---------------------------------------------------------
    df['Price_Intraday_Spread'] = df['Max_Price'] - df['Min_Price']
    df['Price_Intraday_Spread_Ratio'] = df['Price_Intraday_Spread'] / (df['Modal_Price'] + 1e-5)
    
    # ---------------------------------------------------------
    # 2. Historical Exact-Calendar Lags & Rolling Features per Series
    # ---------------------------------------------------------
    # Enforce exact calendar date joins for T-1, T-3, T-7.
    # Missing dates (e.g. Sunday closure) yield explicit NaN (no next-available substitution).
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
    
    # Recent price changes (momentum) strictly relative to exact calendar lags
    df['Price_Change_1d'] = ((df['Modal_Price'] - df['Lag_Price_1']) / df['Lag_Price_1']) * 100
    df['Price_Change_3d'] = ((df['Modal_Price'] - df['Lag_Price_3']) / df['Lag_Price_3']) * 100
    df['Price_Change_7d'] = ((df['Modal_Price'] - df['Lag_Price_7']) / df['Lag_Price_7']) * 100
    
    # Rolling averages and volatility (strictly causal, up to date T)
    grouped = df.groupby('series_id')
    df['Roll_Mean_Price_3'] = grouped['Modal_Price'].transform(lambda s: s.rolling(window=3, min_periods=1).mean())
    df['Roll_Mean_Price_7'] = grouped['Modal_Price'].transform(lambda s: s.rolling(window=7, min_periods=1).mean())
    # Causal volatility with explicit burn-in (min_periods=3). Preserves NaN for insufficient history (no bfill, no fillna(0))
    df['Roll_Std_Price_7'] = grouped['Modal_Price'].transform(lambda s: s.rolling(window=7, min_periods=3).std())
    
    # Ratio of current price to rolling moving averages
    df['Price_to_RollMean3_Ratio'] = df['Modal_Price'] / (df['Roll_Mean_Price_3'] + 1e-5)
    df['Price_to_RollMean7_Ratio'] = df['Modal_Price'] / (df['Roll_Mean_Price_7'] + 1e-5)
    
    # ---------------------------------------------------------
    # 3. Calendar & Seasonal Features
    # ---------------------------------------------------------
    df['Month'] = df['Arrival_Date'].dt.month
    df['DayOfWeek'] = df['Arrival_Date'].dt.dayofweek
    df['DayOfMonth'] = df['Arrival_Date'].dt.day
    df['Quarter'] = df['Arrival_Date'].dt.quarter
    df['Season'] = df['Month'].apply(get_indian_agri_season)
    
    # ---------------------------------------------------------
    # 4. District-Level Aggregations at Time T
    # ---------------------------------------------------------
    # Average commodity price across all mandis in the same district on the same date T
    district_agg = df.groupby(['District', 'Commodity', 'Arrival_Date'])['Modal_Price'].agg(
        District_Commodity_MeanPrice='mean',
        District_Commodity_MandiCount='count'
    ).reset_index()
    
    df = pd.merge(df, district_agg, on=['District', 'Commodity', 'Arrival_Date'], how='left')
    df['Mandi_vs_District_Ratio'] = df['Modal_Price'] / (df['District_Commodity_MeanPrice'] + 1e-5)
    
    # ---------------------------------------------------------
    # 5. Neighbouring-Mandi Intelligence Signals at Time T
    # ---------------------------------------------------------
    # For each commodity and date, compute average prices in neighboring districts
    neighbor_records = []
    # Pre-aggregate commodity prices by district and date
    dist_comm_date = df.groupby(['District', 'Commodity', 'Arrival_Date'])['Modal_Price'].mean().reset_index()
    
    # Build lookup dictionary: (District, Commodity, Arrival_Date) -> mean price
    dist_price_map = dist_comm_date.set_index(['District', 'Commodity', 'Arrival_Date'])['Modal_Price'].to_dict()
    
    def compute_neighbor_price(row):
        target_dist = row['District']
        comm = row['Commodity']
        date = row['Arrival_Date']
        neighbors = NEIGHBORING_DISTRICTS.get(target_dist, [])
        prices = [dist_price_map.get((n_dist, comm, date)) for n_dist in neighbors if (n_dist, comm, date) in dist_price_map]
        prices = [p for p in prices if p is not None]
        if prices:
            return np.mean(prices)
        return row['Modal_Price'] # Fallback to target price if no neighbor reported that commodity on date
    
    # Vectorized / efficient calculation:
    neighbor_pairs = []
    for dist, neighbors in NEIGHBORING_DISTRICTS.items():
        for n_dist in neighbors:
            if n_dist != dist:
                neighbor_pairs.append({'District': dist, 'Neighbor_District': n_dist})
    
    if neighbor_pairs:
        pairs_df = pd.DataFrame(neighbor_pairs)
        # Merge pairs with district commodity date prices of neighbors
        merged_n = pd.merge(
            pairs_df,
            dist_comm_date.rename(columns={'District': 'Neighbor_District', 'Modal_Price': 'Neighbor_Modal_Price'}),
            on='Neighbor_District'
        )
        neighbor_summary = merged_n.groupby(['District', 'Commodity', 'Arrival_Date'])['Neighbor_Modal_Price'].mean().reset_index()
        df = pd.merge(df, neighbor_summary, on=['District', 'Commodity', 'Arrival_Date'], how='left')
        df['Neighbor_Commodity_MeanPrice'] = df['Neighbor_Modal_Price'].fillna(df['District_Commodity_MeanPrice'])
        df.drop(columns=['Neighbor_Modal_Price'], inplace=True)
    else:
        df['Neighbor_Commodity_MeanPrice'] = df['District_Commodity_MeanPrice']
    
    df['Price_Diff_Target_vs_Neighbor'] = df['Modal_Price'] - df['Neighbor_Commodity_MeanPrice']
    df['Price_Ratio_Target_vs_Neighbor'] = df['Modal_Price'] / (df['Neighbor_Commodity_MeanPrice'] + 1e-5)
    
    # ---------------------------------------------------------
    # 6. Classification Target Construction (Exact T+7 Matching)
    # ---------------------------------------------------------
    # Target is strictly constructed from future observation at T + 7 calendar days
    t7_lookup = df[['series_id', 'Arrival_Date', 'Modal_Price', 'Min_Price', 'Max_Price']].copy()
    df['Target_Date'] = df['Arrival_Date'] + timedelta(days=7)
    
    matched = pd.merge(
        df,
        t7_lookup,
        left_on=['series_id', 'Target_Date'],
        right_on=['series_id', 'Arrival_Date'],
        suffixes=('', '_T7'),
        how='inner'
    )
    
    matched['Price_Change_T7'] = matched['Modal_Price_T7'] - matched['Modal_Price']
    matched['Pct_Change_T7'] = (matched['Price_Change_T7'] / (matched['Modal_Price'] + 1e-5)) * 100
    
    # Assign discrete 3-class target strictly following DEC-015:
    # Favorable: Price increase > +threshold_pct
    # Normal: Price fluctuation within [-threshold_pct, +threshold_pct]
    # Unfavorable: Price drop < -threshold_pct
    conditions = [
        matched['Pct_Change_T7'] > threshold_pct,
        matched['Pct_Change_T7'] < -threshold_pct
    ]
    choices = ['Favorable', 'Unfavorable']
    matched['Market_Condition'] = np.select(conditions, choices, default='Normal')
    
    # Numeric code mapping for standard scikit-learn models:
    # 0: Unfavorable, 1: Normal, 2: Favorable
    label_map = {'Unfavorable': 0, 'Normal': 1, 'Favorable': 2}
    matched['Target_Class'] = matched['Market_Condition'].map(label_map)
    
    print(f"[FeatureEngineering] Built dataset of {len(matched):,} records with valid T+7 targets.")
    print(f"[FeatureEngineering] Class distribution:\n{matched['Market_Condition'].value_counts(normalize=True)*100}")
    
    return matched

FEATURE_COLUMNS = [
    'Modal_Price',
    'Min_Price',
    'Max_Price',
    'Price_Intraday_Spread',
    'Price_Intraday_Spread_Ratio',
    'Lag_Price_1',
    'Lag_Price_3',
    'Lag_Price_7',
    'Price_Change_1d',
    'Price_Change_3d',
    'Price_Change_7d',
    'Roll_Mean_Price_3',
    'Roll_Mean_Price_7',
    'Roll_Std_Price_7',
    'Price_to_RollMean3_Ratio',
    'Price_to_RollMean7_Ratio',
    'Month',
    'DayOfWeek',
    'DayOfMonth',
    'Quarter',
    'Season',
    'District_Commodity_MeanPrice',
    'District_Commodity_MandiCount',
    'Mandi_vs_District_Ratio',
    'Neighbor_Commodity_MeanPrice',
    'Price_Diff_Target_vs_Neighbor',
    'Price_Ratio_Target_vs_Neighbor'
]

if __name__ == "__main__":
    from src.data_loader import load_and_clean_mandi_data
    df = load_and_clean_mandi_data()
    dataset = build_features_and_target(df)
    print("Features ready:", len(FEATURE_COLUMNS))
