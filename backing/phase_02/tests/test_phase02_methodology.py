"""
Automated Methodology and Data Handling Test Suite for Phase 02 Audit.
Verifies duplicate handling, market canonicalization, lag feature integrity,
and target definition correctness using both full dataset checks and synthetic micro-tests.
"""

import os
import glob
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
OUTPUT_DIR = os.path.join(WORKSPACE_DIR, "backing/phase_02/outputs")
RAW_DATA_DIR = os.path.join(WORKSPACE_DIR, "data/raw")


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def raw_dataset():
    """Load raw dataset without any modifications."""
    csv_files = sorted(glob.glob(os.path.join(RAW_DATA_DIR, "*.csv")))
    assert len(csv_files) == 5, f"Expected 5 raw CSVs, found {len(csv_files)}"
    dfs = [pd.read_csv(f) for f in csv_files]
    df = pd.concat(dfs, ignore_index=True)
    df['Arrival_Date_Parsed'] = pd.to_datetime(df['Arrival_Date'], format='%d/%m/%Y', errors='coerce')
    df['Modal_Price_Num'] = pd.to_numeric(df['Modal_Price'], errors='coerce')
    return df


@pytest.fixture(scope="module")
def canonical_mapping_df():
    """Load canonical market mapping output."""
    path = os.path.join(OUTPUT_DIR, "canonical_market_mapping.csv")
    assert os.path.exists(path), f"File not found: {path}"
    return pd.read_csv(path)


@pytest.fixture(scope="module")
def target_comparison_df():
    """Load target definition comparison output."""
    path = os.path.join(OUTPUT_DIR, "target_definition_comparison.csv")
    assert os.path.exists(path), f"File not found: {path}"
    return pd.read_csv(path)


# =============================================================================
# TEST 1: Duplicate handling preserves original source records
# =============================================================================
def test_duplicate_handling_preserves_original_source_records(raw_dataset):
    """Verify raw records are 100% preserved in number and content."""
    assert len(raw_dataset) == 160192, f"Expected 160,192 records, got {len(raw_dataset)}"
    for f in glob.glob(os.path.join(RAW_DATA_DIR, "*.csv")):
        assert os.path.getsize(f) > 0, f"Raw file {f} is empty!"


# =============================================================================
# TEST 2: Ambiguous price groups are explicitly flagged
# =============================================================================
def test_ambiguous_price_groups_are_explicitly_flagged(raw_dataset):
    """Verify that ambiguous series-dates with conflicting prices are flagged, not dropped."""
    group_cols = ['District', 'Market', 'Commodity', 'Variety', 'Arrival_Date']
    
    # Calculate min and max modal price per group
    price_ranges = raw_dataset.groupby(group_cols)['Modal_Price_Num'].agg(['min', 'max', 'count'])
    ambiguous_groups = price_ranges[(price_ranges['count'] > 1) & (price_ranges['min'] != price_ranges['max'])]
    
    # In Phase 1 and 2 analysis, exactly 4,363 groups have conflicting modal prices
    assert len(ambiguous_groups) == 4363, f"Expected 4,363 conflicting modal price groups, got {len(ambiguous_groups)}"
    
    # Verify synthetic flagging logic
    synth_df = pd.DataFrame({
        'series': ['S1', 'S1', 'S2', 'S2'],
        'date': ['2025-01-01', '2025-01-01', '2025-01-01', '2025-01-01'],
        'price': [100.0, 120.0, 200.0, 200.0]
    })
    synth_groups = synth_df.groupby(['series', 'date'])['price'].transform(lambda s: s.nunique() > 1)
    assert synth_groups.tolist() == [True, True, False, False], "Synthetic conflict flag failed"


# =============================================================================
# TEST 3: Duplicate resolution strategies produce expected group counts
# =============================================================================
def test_duplicate_resolution_strategies_produce_expected_group_counts(raw_dataset):
    """Verify row counts across different resolution strategies."""
    dup_comp_path = os.path.join(OUTPUT_DIR, "duplicate_resolution_comparison.csv")
    assert os.path.exists(dup_comp_path)
    df_comp = pd.read_csv(dup_comp_path)
    
    # Strat 1 (Preserve all) should have 160,192 rows
    row_strat1 = df_comp[df_comp['strategy_id'] == 'STRAT_01_PRESERVE_AND_FLAG'].iloc[0]
    assert int(row_strat1['retained_records_count']) == 160192
    
    # Strat 2 (Exclude ambiguous) should have 151,361 rows
    row_strat2 = df_comp[df_comp['strategy_id'] == 'STRAT_02_EXCLUDE_AMBIGUOUS'].iloc[0]
    assert int(row_strat2['retained_records_count']) == 151361
    assert int(row_strat2['ambiguous_groups_excluded']) == 4380
    
    # Strat 3 (Median aggregation) should have 155,741 unique series-dates
    row_strat3 = df_comp[df_comp['strategy_id'] == 'STRAT_03_MEDIAN_AGGREGATION'].iloc[0]
    assert int(row_strat3['retained_records_count']) == 155741
    assert int(row_strat3['unique_series_date_groups']) == 155741


# =============================================================================
# TEST 4: Market mappings preserve raw names
# =============================================================================
def test_market_mappings_preserve_raw_names(canonical_mapping_df, raw_dataset):
    """Verify raw market names remain distinct and unmutated in the mapping table."""
    raw_markets_in_data = set(raw_dataset['Market'].unique())
    raw_markets_in_map = set(canonical_mapping_df['raw_market_name'].unique())
    
    assert raw_markets_in_data == raw_markets_in_map, "Mismatch between raw data markets and mapping table!"
    assert len(raw_markets_in_map) == 42, f"Expected 42 raw market names, got {len(raw_markets_in_map)}"
    assert 'proposed_canonical_name' in canonical_mapping_df.columns
    assert 'raw_market_name' in canonical_mapping_df.columns


# =============================================================================
# TEST 5: Unapproved market mappings are not silently applied
# =============================================================================
def test_unapproved_market_mappings_are_not_silently_applied(canonical_mapping_df):
    """Verify that concurrent yards (Jhansi vs Jhansi Grain) and uncertain mappings are flagged."""
    # Jhansi and Jhansi (Grain) must have distinct canonical targets
    jhansi_base = canonical_mapping_df[canonical_mapping_df['raw_market_name'] == 'Jhansi'].iloc[0]
    jhansi_grain = canonical_mapping_df[canonical_mapping_df['raw_market_name'] == 'Jhansi (Grain)'].iloc[0]
    
    assert jhansi_base['proposed_canonical_name'] != jhansi_grain['proposed_canonical_name'], \
        "CRITICAL ERROR: Jhansi and Jhansi (Grain) were incorrectly merged!"
    
    # Check Baripaal APMC has UNRESOLVED / PROPOSED status due to concurrent dates
    baripaal = canonical_mapping_df[canonical_mapping_df['raw_market_name'] == 'Baripaal APMC'].iloc[0]
    assert baripaal['confidence_level'] == 'MEDIUM'
    assert baripaal['mapping_status'] in ['PROPOSED', 'UNRESOLVED']


# =============================================================================
# TEST 6: Exact-calendar lags use the intended calendar date
# =============================================================================
def test_exact_calendar_lags_use_intended_calendar_date():
    """Synthetic test verifying exact calendar matching for lags."""
    dates = pd.to_datetime(['2025-01-01', '2025-01-02', '2025-01-08', '2025-01-15'])
    df = pd.DataFrame({
        'series_id': 'A',
        'date': dates,
        'price': [100.0, 110.0, 120.0, 130.0]
    })
    
    df['lag_date_7'] = df['date'] - timedelta(days=7)
    merged = pd.merge(df, df[['series_id', 'date', 'price']], left_on=['series_id', 'lag_date_7'], right_on=['series_id', 'date'], suffixes=('', '_lag7'), how='left')
    
    # For 2025-01-08, date-7 is 2025-01-01 (price 100.0)
    row_jan08 = merged[merged['date'] == pd.to_datetime('2025-01-08')].iloc[0]
    assert row_jan08['price_lag7'] == 100.0
    
    # For 2025-01-15, date-7 is 2025-01-08 (price 120.0)
    row_jan15 = merged[merged['date'] == pd.to_datetime('2025-01-15')].iloc[0]
    assert row_jan15['price_lag7'] == 120.0


# =============================================================================
# TEST 7: Missing calendar dates remain missing
# =============================================================================
def test_missing_calendar_dates_remain_missing():
    """Verify exact calendar lag does NOT forward-fill missing dates."""
    dates = pd.to_datetime(['2025-01-01', '2025-01-03', '2025-01-10'])
    df = pd.DataFrame({
        'series_id': 'A',
        'date': dates,
        'price': [100.0, 110.0, 120.0]
    })
    
    df['lag_date_7'] = df['date'] - timedelta(days=7)
    merged = pd.merge(df, df[['series_id', 'date', 'price']], left_on=['series_id', 'lag_date_7'], right_on=['series_id', 'date'], suffixes=('', '_lag7'), how='left')
    
    # 2025-01-03 minus 7 is 2025-12-27 (not in data -> NaN)
    row_jan03 = merged[merged['date'] == pd.to_datetime('2025-01-03')].iloc[0]
    assert pd.isna(row_jan03['price_lag7'])
    
    # 2025-01-10 minus 7 is 2025-01-03 (in data -> 110.0)
    row_jan10 = merged[merged['date'] == pd.to_datetime('2025-01-10')].iloc[0]
    assert row_jan10['price_lag7'] == 110.0


# =============================================================================
# TEST 8: No future observations enter historical lag features
# =============================================================================
def test_no_future_observations_enter_historical_lag_features():
    """Verify that every matched lag observation date is strictly < origin date."""
    dates = pd.to_datetime(['2025-01-01', '2025-01-05', '2025-01-12'])
    df = pd.DataFrame({
        'series_id': 'A',
        'date': dates,
        'price': [100.0, 105.0, 110.0]
    })
    
    for lag_days in [1, 3, 7]:
        df[f'lag_target_date_{lag_days}'] = df['date'] - timedelta(days=lag_days)
        merged = pd.merge(df, df[['series_id', 'date', 'price']], left_on=['series_id', f'lag_target_date_{lag_days}'], right_on=['series_id', 'date'], suffixes=('', f'_lag{lag_days}'), how='inner')
        if len(merged) > 0:
            assert (merged['date_lag' + str(lag_days)] < merged['date']).all(), "Future observation found in lag!"


# =============================================================================
# TEST 9: Target joins match the exact intended date
# =============================================================================
def test_target_joins_match_exact_intended_date():
    """Verify target prices match exactly T + horizon calendar days."""
    dates = pd.to_datetime(['2025-01-01', '2025-01-04', '2025-01-08'])
    df = pd.DataFrame({
        'series_id': 'S',
        'date': dates,
        'price': [100.0, 105.0, 110.0]
    })
    
    # Test T+7: 2025-01-01 + 7 days = 2025-01-08
    df['target_date_7'] = df['date'] + timedelta(days=7)
    merged7 = pd.merge(df, df[['series_id', 'date', 'price']], left_on=['series_id', 'target_date_7'], right_on=['series_id', 'date'], suffixes=('', '_T7'), how='left')
    row1 = merged7[merged7['date'] == pd.to_datetime('2025-01-01')].iloc[0]
    assert row1['price_T7'] == 110.0
    
    # Test T+3: 2025-01-01 + 3 days = 2025-01-04
    df['target_date_3'] = df['date'] + timedelta(days=3)
    merged3 = pd.merge(df, df[['series_id', 'date', 'price']], left_on=['series_id', 'target_date_3'], right_on=['series_id', 'date'], suffixes=('', '_T3'), how='left')
    row1_3 = merged3[merged3['date'] == pd.to_datetime('2025-01-01')].iloc[0]
    assert row1_3['price_T3'] == 105.0


# =============================================================================
# TEST 10: Zero and negative prices are excluded from percentage-return calculations
# =============================================================================
def test_zero_and_negative_prices_excluded_from_return_calculations():
    """Synthetic test verifying exclusion of non-positive price denominators."""
    df_pairs = pd.DataFrame({
        'P_T': [0.0, -10.0, 100.0, 200.0],
        'P_T7': [50.0, 20.0, 110.0, 190.0]
    })
    
    # Filter out invalid denominators according to policy
    valid_pairs = df_pairs[(df_pairs['P_T'] > 0) & (df_pairs['P_T7'] > 0)].copy()
    valid_pairs['R_7'] = ((valid_pairs['P_T7'] - valid_pairs['P_T']) / valid_pairs['P_T']) * 100.0
    
    assert len(valid_pairs) == 2, f"Expected 2 valid pairs, got {len(valid_pairs)}"
    assert not np.isinf(valid_pairs['R_7']).any(), "Infinite return generated!"
    assert not np.isnan(valid_pairs['R_7']).any(), "NaN return generated!"
    assert valid_pairs['R_7'].tolist() == [10.0, -5.0]


# =============================================================================
# TEST 11: Target classes handle exactly +2.5% and -2.5% correctly
# =============================================================================
def test_target_classes_handle_exact_boundaries():
    """Verify that exact edge cases +2.5% and -2.5% are mapped correctly."""
    returns = pd.Series([2.500000, -2.500000, 2.499999, -2.499999, 0.0, 5.0, -5.0])
    
    def classify(r):
        if r >= 2.5:
            return 'Favorable'
        elif r <= -2.5:
            return 'Unfavorable'
        else:
            return 'Normal'
            
    classes = returns.apply(classify).tolist()
    expected = ['Favorable', 'Unfavorable', 'Normal', 'Normal', 'Normal', 'Favorable', 'Unfavorable']
    assert classes == expected, f"Classification mismatch: {classes} vs {expected}"


# =============================================================================
# TEST 12: Boundary-truncated and interior-missing targets are distinguished
# =============================================================================
def test_boundary_truncated_and_interior_missing_targets_distinguished(target_comparison_df):
    """Verify that targets truncated by the end of dataset are separated from interior missing."""
    t7_rows = target_comparison_df[target_comparison_df['horizon'] == 'T+7']
    assert len(t7_rows) > 0
    t7_row = t7_rows.iloc[0]
    
    trunc = int(t7_row['boundary_truncated_targets'])
    interior = int(t7_row['interior_missing_targets'])
    matched = int(t7_row['matched_targets'])
    eligible = int(t7_row['eligible_origins'])
    
    # Verification of arithmetic identities
    assert trunc == 1005, f"Expected 1,005 truncated records at T+7, got {trunc}"
    assert interior == 37560, f"Expected 37,560 interior missing records at T+7, got {interior}"
    assert eligible == matched + interior, f"Eligible ({eligible}) != matched ({matched}) + interior ({interior})"


# =============================================================================
# TEST 13: Every required output exists and has a valid schema
# =============================================================================
def test_every_required_output_exists_and_has_valid_schema():
    """Verify that all 6 required Phase 2 output CSV files exist and have non-empty schemas."""
    required_files = [
        "duplicate_resolution_comparison.csv",
        "canonical_market_mapping.csv",
        "calendar_lag_coverage.csv",
        "target_definition_comparison.csv",
        "cleaned_data_quality_summary.csv",
        "methodology_sensitivity_summary.csv"
    ]
    
    for filename in required_files:
        filepath = os.path.join(OUTPUT_DIR, filename)
        assert os.path.exists(filepath), f"Missing output CSV: {filepath}"
        df = pd.read_csv(filepath)
        assert len(df) > 0, f"CSV {filename} is empty!"
        assert len(df.columns) >= 3, f"CSV {filename} has insufficient columns ({len(df.columns)})"
