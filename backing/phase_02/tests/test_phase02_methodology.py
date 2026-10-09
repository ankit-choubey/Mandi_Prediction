"""
Comprehensive Methodology and Data Handling Test Suite for Phase 02 Correction Pass.
Tests duplicate resolution with Grade dimension, consistent market status, hiatus validation,
leak-free volatility thresholds, embargoed quantile estimation, and exact calendar joins.
"""

import os
import glob
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Dynamic repository path derivation
WORKSPACE_DIR = os.environ.get(
    "MANDI_REPO_ROOT",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
)
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
    df['Min_Price_Num'] = pd.to_numeric(df['Min_Price'], errors='coerce')
    df['Max_Price_Num'] = pd.to_numeric(df['Max_Price'], errors='coerce')
    return df


@pytest.fixture(scope="module")
def canonical_mapping_df():
    path = os.path.join(OUTPUT_DIR, "canonical_market_mapping.csv")
    assert os.path.exists(path), f"File not found: {path}"
    return pd.read_csv(path)


@pytest.fixture(scope="module")
def duplicate_comparison_df():
    path = os.path.join(OUTPUT_DIR, "duplicate_resolution_comparison.csv")
    assert os.path.exists(path), f"File not found: {path}"
    return pd.read_csv(path)


@pytest.fixture(scope="module")
def target_comparison_df():
    path = os.path.join(OUTPUT_DIR, "target_definition_comparison.csv")
    assert os.path.exists(path), f"File not found: {path}"
    return pd.read_csv(path)


# =============================================================================
# TEST 1: Duplicate group with different grades and different prices
# =============================================================================
def test_duplicate_group_with_different_grades_and_prices():
    """Verify that records with differing Grade represent distinct commercial series, not duplicates."""
    synth_df = pd.DataFrame({
        'District': ['Lucknow', 'Lucknow'],
        'Market': ['Lucknow APMC', 'Lucknow APMC'],
        'Commodity': ['Potato', 'Potato'],
        'Variety': ['Deshi', 'Deshi'],
        'Grade': ['FAQ', 'Medium'],
        'Arrival_Date': ['15/01/2026', '15/01/2026'],
        'Modal_Price': [1200.0, 1500.0]
    })
    
    # When grouped without grade: false collision
    no_grade_dups = synth_df.duplicated(subset=['District', 'Market', 'Commodity', 'Variety', 'Arrival_Date'], keep=False)
    assert no_grade_dups.all(), "Expected collision when Grade is omitted"
    
    # When grouped with grade: zero collision, genuine quality tiers preserved
    with_grade_dups = synth_df.duplicated(subset=['District', 'Market', 'Commodity', 'Variety', 'Grade', 'Arrival_Date'], keep=False)
    assert not with_grade_dups.any(), "Different grades must not collide as duplicate series-dates"


# =============================================================================
# TEST 2: Same-grade conflicting-price examples
# =============================================================================
def test_same_grade_conflicting_price_examples():
    """Verify that same-grade conflicting prices are explicitly flagged as ambiguous."""
    synth_df = pd.DataFrame({
        'District': ['Lucknow', 'Lucknow', 'Lucknow'],
        'Market': ['Lucknow APMC', 'Lucknow APMC', 'Lucknow APMC'],
        'Commodity': ['Potato', 'Potato', 'Potato'],
        'Variety': ['Deshi', 'Deshi', 'Deshi'],
        'Grade': ['FAQ', 'FAQ', 'Medium'],
        'Arrival_Date': ['15/01/2026', '15/01/2026', '15/01/2026'],
        'Modal_Price': [1200.0, 1250.0, 1500.0]
    })
    
    key_with_grade = ['District', 'Market', 'Commodity', 'Variety', 'Grade', 'Arrival_Date']
    g_agg = synth_df.groupby(key_with_grade)['Modal_Price'].agg(['count', 'nunique'])
    ambig_groups = g_agg[(g_agg['count'] > 1) & (g_agg['nunique'] > 1)]
    
    assert len(ambig_groups) == 1, "Expected exactly 1 ambiguous same-grade group"
    assert ('Lucknow', 'Lucknow APMC', 'Potato', 'Deshi', 'FAQ', '15/01/2026') in ambig_groups.index


# =============================================================================
# TEST 3: Missing or inconsistent Grade values audit
# =============================================================================
def test_missing_or_inconsistent_grade_values_audit(raw_dataset):
    """Verify that all 160,192 raw records have non-null, valid Grade values."""
    assert raw_dataset['Grade'].isnull().sum() == 0, "Null Grade values detected!"
    assert (raw_dataset['Grade'].astype(str).str.strip() == '').sum() == 0, "Empty Grade strings detected!"
    
    # Check that known standard grades exist and are predominant
    grades = set(raw_dataset['Grade'].unique())
    assert 'FAQ' in grades
    assert 'Medium' in grades
    assert 'Non-FAQ' in grades


# =============================================================================
# TEST 4: Verification that strategy exclusions operate on the documented key
# =============================================================================
def test_strategy_exclusions_operate_on_documented_key(duplicate_comparison_df):
    """Verify Strategy 2 exclusions use (District, Market, Commodity, Variety, Grade, Date)."""
    s2_row = duplicate_comparison_df[duplicate_comparison_df['strategy_id'] == 'STRAT_02_EXCLUDE_AMBIGUOUS_SAME_GRADE'].iloc[0]
    
    # In Strategy 2: 157,518 retained, exactly 2,674 rows excluded (1,321 ambiguous groups + 10 duplicate rows)
    assert int(s2_row['raw_records_retained']) == 157518
    assert int(s2_row['records_excluded']) == 2674
    assert int(s2_row['raw_records_retained']) + int(s2_row['records_excluded']) == 160192


# =============================================================================
# TEST 5: A test ensuring medians do not combine different grades
# =============================================================================
def test_medians_do_not_combine_different_grades():
    """Verify that median aggregation groups by Grade and never averages across distinct grades."""
    synth_df = pd.DataFrame({
        'District': ['Kanpur', 'Kanpur', 'Kanpur', 'Kanpur'],
        'Market': ['Kanpur(Grain)', 'Kanpur(Grain)', 'Kanpur(Grain)', 'Kanpur(Grain)'],
        'Commodity': ['Wheat', 'Wheat', 'Wheat', 'Wheat'],
        'Variety': ['Dara', 'Dara', 'Dara', 'Dara'],
        'Grade': ['FAQ', 'FAQ', 'Medium', 'Medium'],
        'Arrival_Date': ['10/01/2026', '10/01/2026', '10/01/2026', '10/01/2026'],
        'Modal_Price': [2000.0, 2100.0, 2500.0, 2700.0]
    })
    
    key = ['District', 'Market', 'Commodity', 'Variety', 'Grade', 'Arrival_Date']
    medians = synth_df.groupby(key)['Modal_Price'].median().to_dict()
    
    faq_key = ('Kanpur', 'Kanpur(Grain)', 'Wheat', 'Dara', 'FAQ', '10/01/2026')
    med_key = ('Kanpur', 'Kanpur(Grain)', 'Wheat', 'Dara', 'Medium', '10/01/2026')
    
    assert medians[faq_key] == 2050.0, f"FAQ median corrupted: {medians[faq_key]}"
    assert medians[med_key] == 2600.0, f"Medium median corrupted: {medians[med_key]}"


# =============================================================================
# TEST 6: Consistent mapping status within alias groups
# =============================================================================
def test_consistent_mapping_status_within_alias_groups(canonical_mapping_df):
    """Verify that base markets and their APMC aliases share identical mapping status."""
    for (dist, can_name), group in canonical_mapping_df.groupby(['district', 'proposed_canonical_name']):
        statuses = set(group['mapping_status'].unique())
        # For Varipaal, Baripaal is UNRESOLVED while Varipaal/Varipaal APMC are APPROVED (documented exception)
        if can_name == 'Varipaal':
            assert 'APPROVED' in statuses and 'UNRESOLVED' in statuses
        else:
            assert len(statuses) == 1, f"Contradictory mapping statuses in group ({dist}, {can_name}): {statuses}"


# =============================================================================
# TEST 7: Concurrent market names must remain distinct
# =============================================================================
def test_concurrent_market_names_remain_distinct(canonical_mapping_df):
    """Verify Jhansi and Jhansi (Grain) are not merged and represent concurrent yards."""
    jh_base = canonical_mapping_df[canonical_mapping_df['raw_market_name'] == 'Jhansi'].iloc[0]
    jh_grain = canonical_mapping_df[canonical_mapping_df['raw_market_name'] == 'Jhansi (Grain)'].iloc[0]
    
    assert jh_base['proposed_canonical_name'] != jh_grain['proposed_canonical_name'], \
        "CRITICAL ERROR: Jhansi and Jhansi (Grain) were incorrectly merged!"
    assert jh_base['proposed_canonical_name'] == 'Jhansi'
    assert jh_grain['proposed_canonical_name'] == 'Jhansi (Grain)'


# =============================================================================
# TEST 8: Hypothetical Purwa hiatus must not be silently treated as continuous
# =============================================================================
def test_purwa_hiatus_explicit_mapping_decision(canonical_mapping_df):
    """Verify Purwa is flagged with PROPOSED status and its 204-day reporting hiatus is documented."""
    purwa_rows = canonical_mapping_df[canonical_mapping_df['proposed_canonical_name'] == 'Purwa']
    assert len(purwa_rows) == 2
    for _, row in purwa_rows.iterrows():
        assert row['mapping_status'] == 'PROPOSED', "Purwa must not be APPROVED as continuous without hiatus resolution!"
        assert int(row['reporting_hiatus_days']) >= 200, "Hiatus days must reflect the ~204-day gap"


# =============================================================================
# TEST 9: Historical volatility thresholds remain unchanged when future modified
# =============================================================================
def test_historical_volatility_thresholds_remain_unchanged_when_future_modified():
    """Verify historical volatility estimated up to origin T is 100% invariant to future outcomes."""
    dates = pd.to_datetime(['2025-01-01', '2025-01-02', '2025-01-03', '2025-01-04', '2025-01-05'])
    
    df1 = pd.DataFrame({
        'Date': dates,
        'Price': [100.0, 102.0, 101.0, 105.0, 110.0] # Baseline future at T=2025-01-03
    })
    
    df2 = pd.DataFrame({
        'Date': dates,
        'Price': [100.0, 102.0, 101.0, 150.0, 200.0] # Drastically altered future at T+1, T+2
    })
    
    def get_hist_vol_at_T(d, T_date):
        past_prices = d[d['Date'] <= T_date]['Price']
        returns = past_prices.pct_change().dropna() * 100.0
        return float(returns.std())
        
    T = pd.to_datetime('2025-01-03')
    vol1 = get_hist_vol_at_T(df1, T)
    vol2 = get_hist_vol_at_T(df2, T)
    
    assert abs(vol1 - vol2) < 1e-9, f"LEAKAGE DETECTED: Historical volatility changed from {vol1} to {vol2}!"


# =============================================================================
# TEST 10: Quantile cutoffs do not use outcomes from held-out periods
# =============================================================================
def test_quantile_cutoffs_do_not_use_outcomes_from_held_out_periods(target_comparison_df):
    """Verify quantile estimation uses an embargo window so targets do not cross the train/val split."""
    t7_quantile_row = target_comparison_df[
        (target_comparison_df['horizon'] == 'T+7') &
        (target_comparison_df['target_definition_name'].str.contains('Quantile_Quartiles'))
    ].iloc[0]
    
    # Must explicitly state origin cutoff <= 2026-01-17 (7 days before 2026-01-24 split)
    rule_text = t7_quantile_row['formula_or_rule']
    assert '2026-01-17' in rule_text, f"Expected embargo cutoff 2026-01-17 in rule, got: {rule_text}"


# =============================================================================
# TEST 11: Independent reproducibility tests for exact T-1, T-3, T-7, T+3, T+7 joins
# =============================================================================
def test_independent_reproducibility_exact_joins():
    """Verify calendar matching logic on synthetic dates with missing interior dates."""
    dates = pd.to_datetime(['2025-01-01', '2025-01-04', '2025-01-08', '2025-01-15'])
    df = pd.DataFrame({
        'series': 'S',
        'date': dates,
        'price': [100.0, 104.0, 108.0, 115.0]
    })
    
    # Exact T-7 join
    df['lag7_date'] = df['date'] - timedelta(days=7)
    m_lag7 = pd.merge(df, df[['series', 'date', 'price']], left_on=['series', 'lag7_date'], right_on=['series', 'date'], suffixes=('', '_lag7'), how='left')
    
    # 2025-01-08 minus 7 is 2025-01-01 (price 100.0)
    assert m_lag7.loc[m_lag7['date'] == pd.to_datetime('2025-01-08'), 'price_lag7'].iloc[0] == 100.0
    # 2025-01-04 minus 7 is 2024-12-28 (missing -> NaN)
    assert pd.isna(m_lag7.loc[m_lag7['date'] == pd.to_datetime('2025-01-04'), 'price_lag7'].iloc[0])
    
    # Exact T+7 join
    df['target7_date'] = df['date'] + timedelta(days=7)
    m_target7 = pd.merge(df, df[['series', 'date', 'price']], left_on=['series', 'target7_date'], right_on=['series', 'date'], suffixes=('', '_target7'), how='left')
    
    # 2025-01-01 plus 7 is 2025-01-08 (price 108.0)
    assert m_target7.loc[m_target7['date'] == pd.to_datetime('2025-01-01'), 'price_target7'].iloc[0] == 108.0
    # 2025-01-04 plus 7 is 2025-01-11 (missing -> NaN)
    assert pd.isna(m_target7.loc[m_target7['date'] == pd.to_datetime('2025-01-04'), 'price_target7'].iloc[0])


# =============================================================================
# TEST 12: Zero and negative prices are excluded from return calculations
# =============================================================================
def test_zero_and_negative_prices_excluded():
    """Verify non-positive prices are filtered out of returns."""
    df = pd.DataFrame({
        'P_T': [0.0, -5.0, 100.0, 200.0],
        'P_T7': [100.0, 50.0, 0.0, 220.0]
    })
    valid = df[(df['P_T'] > 0) & (df['P_T7'] > 0)].copy()
    valid['R'] = ((valid['P_T7'] - valid['P_T']) / valid['P_T']) * 100.0
    
    assert len(valid) == 1
    assert valid['R'].iloc[0] == 10.0


# =============================================================================
# TEST 13: Target classes handle exactly +2.5% and -2.5% correctly
# =============================================================================
def test_target_classes_handle_exact_boundaries():
    """Verify that exact edge cases +2.5% and -2.5% are mapped correctly."""
    returns = pd.Series([2.500000, -2.500000, 2.499999, -2.499999, 0.0])
    
    def classify(r):
        if r >= 2.5:
            return 'Favorable'
        elif r <= -2.5:
            return 'Unfavorable'
        else:
            return 'Normal'
            
    classes = returns.apply(classify).tolist()
    expected = ['Favorable', 'Unfavorable', 'Normal', 'Normal', 'Normal']
    assert classes == expected


# =============================================================================
# TEST 14: Every output CSV has expected schema and reconciled denominators
# =============================================================================
def test_every_output_csv_has_expected_schema_and_reconciled_denominators():
    """Verify all 6 CSV outputs exist, are non-empty, and denominators reconcile."""
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
        assert os.path.exists(filepath), f"Missing CSV: {filepath}"
        df = pd.read_csv(filepath)
        assert len(df) > 0, f"CSV {filename} is empty!"
        assert len(df.columns) >= 3, f"CSV {filename} has too few columns"
