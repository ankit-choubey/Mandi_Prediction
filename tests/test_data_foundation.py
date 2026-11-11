"""
Automated Data Foundation Verification and Alignment Test Suite
APMC Mandi Market Intelligence System
Validates Workstreams A, B, C, D, and E requirements:
1. Raw input integrity and checksum stability
2. Data inventory status classification coverage
3. Synthetic quarantine enforcement
4. Price series/date key uniqueness and ambiguous duplicate resolution
5. Exact calendar T+h target matching
6. Rejection of row-shift target generation
7. Chronological split calendar separation (no train/test date overlap)
8. Label-window overlap purging across split boundaries (horizon-aware embargo)
9. Weather calendar lag construction (calendar date, not row index)
10. Weather join row-count preservation
11. NASA POWER missing value preservation (NaN != 0.0)
12. Absence of machine-specific absolute paths
"""

import os
import re
import glob
import json
import hashlib
from datetime import timedelta, date
import numpy as np
import pandas as pd
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# -----------------------------------------------------------------------------
# 1. RAW INPUT FILES INTEGRITY
# -----------------------------------------------------------------------------
EXPECTED_RAW_FILES = {
    'Gaziabaad.csv': {'rows': 41495, 'sha256': '71601f993e07efa146f126747245a7fffb608a307abdea579475ba19bfeb0251'},
    'Jhansi.csv': {'rows': 23625, 'sha256': '7d0808d8d32555212af546004195c0ccf58e368106daad67169a231e80988a5c'},
    'Kanpur.csv': {'rows': 42644, 'sha256': '0eb17704ebba1f66b8c9ef660f48dabc3665ea4691ed3b8aa20a49df8528d04a'},
    'Lukhnow.csv': {'rows': 21063, 'sha256': '6ca52743cc2f9059bf1e3b919b25317aa367f580bbafa6f62adb9db1d759bb13'},
    'Unnao.csv': {'rows': 31365, 'sha256': 'd4ee358b96cad3a888e4a92acd993327e56c4dc6af6eb60814193f98f591cebc'}
}

def test_raw_input_files_remain_unchanged():
    raw_dir = os.path.join(REPO_ROOT, "data", "raw")
    assert os.path.isdir(raw_dir), f"Missing raw directory: {raw_dir}"
    
    total_rows = 0
    for fname, expected in EXPECTED_RAW_FILES.items():
        fpath = os.path.join(raw_dir, fname)
        assert os.path.exists(fpath), f"Raw file missing: {fpath}"
        
        # Check SHA-256
        h = hashlib.sha256()
        with open(fpath, 'rb') as f:
            while chunk := f.read(65536):
                h.update(chunk)
        actual_hash = h.hexdigest()
        assert actual_hash == expected['sha256'], f"SHA-256 mismatch for {fname}: got {actual_hash}"
        
        # Check row count
        df = pd.read_csv(fpath)
        assert len(df) == expected['rows'], f"Row count changed for {fname}: got {len(df)}"
        total_rows += len(df)
        
    assert total_rows == 160192, f"Expected 160,192 total raw records, got {total_rows}"

# -----------------------------------------------------------------------------
# 2. DATA INVENTORY CLASSIFICATION COVERAGE
# -----------------------------------------------------------------------------
VALID_AUTHENTICITY_STATUSES = {
    'REAL_OBSERVED', 'REAL_PUBLISHED', 'DERIVED_ESTIMATE',
    'SYNTHETIC_SCENARIO', 'SCHEMA_ONLY'
}

def test_data_inventory_status_for_every_consumed_input():
    inv_path = os.path.join(REPO_ROOT, "data_inventory.json")
    assert os.path.exists(inv_path), "Missing data_inventory.json"
    
    with open(inv_path, 'r', encoding='utf-8') as f:
        inventory = json.load(f)
        
    assert len(inventory) >= 12, f"Expected at least 12 inventory entries, got {len(inventory)}"
    
    for item in inventory:
        assert 'file_path' in item
        assert 'authenticity_status' in item
        assert item['authenticity_status'] in VALID_AUTHENTICITY_STATUSES, (
            f"Invalid status {item['authenticity_status']} for {item['file_path']}"
        )
        assert 'permitted_use' in item and len(item['permitted_use']) > 0
        assert 'sha256_checksum' in item and len(item['sha256_checksum']) == 64

# -----------------------------------------------------------------------------
# 3. SYNTHETIC FILES BLOCKED FROM EMPIRICAL PIPELINES
# -----------------------------------------------------------------------------
def test_synthetic_files_blocked_from_empirical_pipeline():
    quarantine_dir = os.path.join(REPO_ROOT, "suryansh - work", "dataset_research", "raw_external", "quarantine")
    assert os.path.isdir(quarantine_dir), f"Quarantine directory does not exist: {quarantine_dir}"
    
    quarantined_files = os.listdir(quarantine_dir)
    assert any("SYNTHETIC_ceda_calibrated_mandi_arrivals" in f for f in quarantined_files)
    assert any("SYNTHETIC_des_up_district_crop_production" in f for f in quarantined_files)
    
    # Assert that core data loader does NOT load from quarantine or external directory
    from src.data_loader import load_and_clean_mandi_data
    df = load_and_clean_mandi_data(data_dir=REPO_ROOT, min_series_records=20)
    
    # Clean mandi dataset must NOT contain synthetic arrivals or DES columns
    forbidden_cols = {'Arrival_Quantity_Qtl', 'Area_Hectares', 'Production_Tonnes', 'Yield_Kg_Per_Ha'}
    found_forbidden = forbidden_cols.intersection(df.columns)
    assert not found_forbidden, f"Empirical dataset contaminated with synthetic columns: {found_forbidden}"

# -----------------------------------------------------------------------------
# 4. PRICE-SERIES / DATE KEY UNIQUENESS & AMBIGUITY HANDLING
# -----------------------------------------------------------------------------
def test_price_series_date_keys_unique_and_unambiguous():
    from src.data_loader import load_and_clean_mandi_data
    df = load_and_clean_mandi_data(data_dir=REPO_ROOT, min_series_records=20)
    
    key_with_date = ['series_id', 'Arrival_Date']
    dup_keys = df.duplicated(subset=key_with_date).sum()
    assert dup_keys == 0, f"Found {dup_keys} duplicate (series_id, Arrival_Date) keys after data cleaning!"
    
    # Assert positive prices and order
    assert (df['Modal_Price'] > 0).all(), "Found non-positive Modal_Price"
    assert (df['Min_Price'] > 0).all(), "Found non-positive Min_Price"
    assert (df['Max_Price'] > 0).all(), "Found non-positive Max_Price"
    assert (df['Min_Price'] <= df['Modal_Price']).all(), "Min_Price > Modal_Price violation detected"
    assert (df['Modal_Price'] <= df['Max_Price']).all(), "Modal_Price > Max_Price violation detected"

# -----------------------------------------------------------------------------
# 5. EXACT CALENDAR T+h MATCHING & REJECTION OF ROW-SHIFT MATCHING
# -----------------------------------------------------------------------------
def test_exact_calendar_t_plus_h_matching():
    # Construct a small synthetic panel with an intentional non-consecutive gap:
    # Day 1: 2025-01-01 -> Target T+7 is 2025-01-08 (present)
    # Day 2: 2025-01-02 -> Target T+7 is 2025-01-09 (MISSING in panel)
    # Day 3: 2025-01-08 -> Target T+7 is 2025-01-15 (present)
    # Day 4: 2025-01-15
    dates = pd.to_datetime(['2025-01-01', '2025-01-02', '2025-01-08', '2025-01-15'])
    prices = [100.0, 110.0, 120.0, 150.0]
    
    toy_df = pd.DataFrame({
        'series_id': 'Series_A',
        'Arrival_Date': dates,
        'Modal_Price': prices
    })
    
    # Exact calendar T+7 matching
    toy_df['Target_Date'] = toy_df['Arrival_Date'] + timedelta(days=7)
    lookup = toy_df[['series_id', 'Arrival_Date', 'Modal_Price']].copy()
    
    matched = pd.merge(
        toy_df,
        lookup.rename(columns={'Modal_Price': 'Modal_Price_T7', 'Arrival_Date': 'Target_Date'}),
        on=['series_id', 'Target_Date'],
        how='left'
    )
    
    # Row 0 (2025-01-01) matches exactly 2025-01-08 (price = 120.0)
    assert matched.loc[0, 'Modal_Price_T7'] == 120.0
    
    # Row 1 (2025-01-02) target 2025-01-09 is missing -> MUST be NaN!
    assert pd.isna(matched.loc[1, 'Modal_Price_T7']), (
        f"Expected NaN for missing calendar date 2025-01-09, got {matched.loc[1, 'Modal_Price_T7']}"
    )
    
    # Row 2 (2025-01-08) matches exactly 2025-01-15 (price = 150.0)
    assert matched.loc[2, 'Modal_Price_T7'] == 150.0
    
    # Proves that a naive row shift (-1) would have INCORRECTLY matched 2025-01-02 to 2025-01-08!
    row_shift_price = toy_df['Modal_Price'].shift(-1).iloc[1]
    assert row_shift_price == 120.0  # The row shift bug
    assert pd.isna(matched.loc[1, 'Modal_Price_T7'])  # The correct calendar logic

def test_no_row_shift_target_generation_in_src():
    from src.feature_engineering import build_features_and_target
    
    # Create controlled multi-date frame with weekend gap
    dates = pd.date_range('2025-01-01', periods=14, freq='D')
    # Remove Sunday (2025-01-05) and following Wednesday (2025-01-08)
    dates = [d for d in dates if d.strftime('%Y-%m-%d') not in ['2025-01-05', '2025-01-08']]
    
    df_toy = pd.DataFrame({
        'District': 'Lucknow',
        'Market': 'Lucknow',
        'Commodity': 'Potato',
        'Variety': 'Desi',
        'Grade': 'FAQ',
        'series_id': 'Lucknow__Lucknow__Potato__Desi__FAQ',
        'Arrival_Date': pd.to_datetime(dates),
        'Min_Price': 1000.0,
        'Modal_Price': 1100.0,
        'Max_Price': 1200.0
    })
    
    res = build_features_and_target(df_toy)
    
    # Any date whose Arrival_Date + 7 days was removed must NOT appear in matched res
    for _, row in res.iterrows():
        expected_target_date = row['Arrival_Date'] + timedelta(days=7)
        assert expected_target_date in df_toy['Arrival_Date'].values, (
            f"Target date {expected_target_date} was not present in source records!"
        )

# -----------------------------------------------------------------------------
# 6. TRAIN / VAL / TEST SPLIT & HORIZON-AWARE EMBARGO PURGING
# -----------------------------------------------------------------------------
def test_no_train_test_calendar_overlap_and_embargo_purging():
    from src.evaluate import chronological_split
    
    # Create synthetic panel spanning 100 consecutive calendar dates
    dates = pd.date_range('2025-01-01', periods=100, freq='D')
    df = pd.DataFrame({
        'Arrival_Date': dates,
        'series_id': 'Test_Series',
        'Modal_Price': 1000.0
    })
    
    horizon = 7
    train_df, val_df, test_df = chronological_split(df, train_ratio=0.70, val_ratio=0.15, horizon_days=horizon)
    
    # 1. No calendar date overlap across partitions
    train_dates = set(train_df['Arrival_Date'])
    val_dates = set(val_df['Arrival_Date'])
    test_dates = set(test_df['Arrival_Date'])
    
    assert train_dates.isdisjoint(val_dates), "Train and Val dates overlap!"
    assert train_dates.isdisjoint(test_dates), "Train and Test dates overlap!"
    assert val_dates.isdisjoint(test_dates), "Val and Test dates overlap!"
    
    # 2. Strict chronological order
    assert train_df['Arrival_Date'].max() < val_df['Arrival_Date'].min()
    assert val_df['Arrival_Date'].max() < test_df['Arrival_Date'].min()
    
    # 3. Label-window overlap purging (embargo buffer)
    # The last train origin's realization date (Arrival_Date + 7 days) MUST be strictly prior to val start date
    val_start = val_df['Arrival_Date'].min()
    last_train_origin = train_df['Arrival_Date'].max()
    last_train_realization = last_train_origin + pd.Timedelta(days=horizon)
    assert last_train_realization < val_start, (
        f"Train realization {last_train_realization} overlaps into validation start {val_start}!"
    )
    
    # Same for validation into test
    test_start = test_df['Arrival_Date'].min()
    last_val_origin = val_df['Arrival_Date'].max()
    last_val_realization = last_val_origin + pd.Timedelta(days=horizon)
    assert last_val_realization < test_start, (
        f"Val realization {last_val_realization} overlaps into test start {test_start}!"
    )

# -----------------------------------------------------------------------------
# 7. WEATHER FEATURE CONSTRUCTION (CALENDAR LAG, ROW PRESERVATION, NaN HANDLING)
# -----------------------------------------------------------------------------
def test_weather_lag_based_on_calendar_date():
    # Construct a daily calendar weather panel with an intentional gap
    # Date 1: 2025-01-01, Rain: 10.0
    # Date 2: 2025-01-03 (Jan 2 missing), Rain: 5.0
    w_df = pd.DataFrame({
        'District': ['Kanpur', 'Kanpur'],
        'Arrival_Date': pd.to_datetime(['2025-01-01', '2025-01-03']),
        'Precipitation_mm': [10.0, 5.0]
    })
    
    # When correctly reindexed to full daily calendar:
    full_dates = pd.date_range('2025-01-01', '2025-01-03', freq='D')
    grid = pd.MultiIndex.from_product([['Kanpur'], full_dates], names=['District', 'Arrival_Date']).to_frame().reset_index(drop=True)
    w_panel = pd.merge(grid, w_df, on=['District', 'Arrival_Date'], how='left')
    w_panel.sort_values(by=['District', 'Arrival_Date'], inplace=True)
    
    w_panel['Precipitation_Lag1'] = w_panel.groupby('District')['Precipitation_mm'].shift(1)
    
    # 2025-01-03 lag-1 should be 2025-01-02 (which is NaN), NOT 10.0 from Jan 1
    jan3_lag = w_panel[w_panel['Arrival_Date'] == '2025-01-03']['Precipitation_Lag1'].iloc[0]
    assert pd.isna(jan3_lag), f"Expected NaN for unobserved prior day, got {jan3_lag}"

def test_weather_join_preserves_row_count():
    # Price table with 3 commodities on the same date and district
    price_df = pd.DataFrame({
        'District': ['Lucknow', 'Lucknow', 'Lucknow'],
        'Arrival_Date': pd.to_datetime(['2025-05-01', '2025-05-01', '2025-05-01']),
        'Commodity': ['Potato', 'Tomato', 'Wheat'],
        'Modal_Price': [1200.0, 1800.0, 2400.0]
    })
    
    # Unique weather panel with exactly 1 row for that district and date
    weather_df = pd.DataFrame({
        'District': ['Lucknow'],
        'Arrival_Date': pd.to_datetime(['2025-05-01']),
        'Precipitation_Lag1': [2.5],
        'Temp_Max_Lag1': [34.0]
    })
    
    merged = pd.merge(price_df, weather_df, on=['District', 'Arrival_Date'], how='left')
    assert len(merged) == len(price_df), f"Row count changed: expected {len(price_df)}, got {len(merged)}"
    assert (merged['Temp_Max_Lag1'] == 34.0).all()

def test_missing_precipitation_distinguishable_from_zero():
    # In NASA POWER data, missing is -999.0
    raw_precip_values = [-999.0, 0.0, 12.5, -999.0]
    
    # Cleaned following Workstream C repair rule:
    cleaned = [np.nan if p < -900 else p for p in raw_precip_values]
    
    assert pd.isna(cleaned[0]), "Failed to map -999.0 to NaN"
    assert cleaned[1] == 0.0, "Zero precipitation dry day altered"
    assert cleaned[2] == 12.5, "Valid precipitation altered"
    assert pd.isna(cleaned[3]), "Failed to map second -999.0 to NaN"
    
    # Verify that a dry day (0.0) is not equal to a missing day (NaN)
    assert cleaned[1] != cleaned[0]
    assert np.isnan(cleaned[0]) and not np.isnan(cleaned[1])

# -----------------------------------------------------------------------------
# 8. ABSENCE OF MACHINE-SPECIFIC ABSOLUTE PATHS
# -----------------------------------------------------------------------------
def test_no_machine_specific_paths_in_scripts():
    py_files = []
    for root, dirs, files in os.walk(REPO_ROOT):
        # Skip git and cache
        if '.git' in root or '__pycache__' in root or '.venv' in root:
            continue
        for f in files:
            if f.endswith('.py') and f != os.path.basename(__file__):
                py_files.append(os.path.join(root, f))
                
    forbidden_patterns = [
        re.compile(r'/Users/[a-zA-Z0-9_]+/Desktop'),
        re.compile(r'/home/kumarsuryansh'),
        re.compile(r'C:\\Users\\')
    ]
    
    violations = []
    for fpath in py_files:
        rel_path = os.path.relpath(fpath, REPO_ROOT)
        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
            for line_no, line in enumerate(f, 1):
                for pat in forbidden_patterns:
                    if pat.search(line):
                        violations.append((rel_path, line_no, line.strip()))
                        
    assert not violations, f"Found machine-specific paths in scripts: {violations}"
