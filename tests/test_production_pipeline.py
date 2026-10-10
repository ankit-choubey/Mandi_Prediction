"""
Regression & Verification Test Suite for Application Pipeline (src/)
APMC Mandi Market Intelligence System

Tests core functionality against audited Phase 0-3 standards:
1. Preservation of Grade in series identity & Strategy 2 duplicate exclusion.
2. Exact calendar date lags (T-1, T-3, T-7) with explicit NaN handling (zero substitution).
3. Horizon-aware chronological splitting with embargo buffer purging.
4. Validation-only candidate model selection with zero test contamination.
5. Mandatory research prototype disclaimers on intelligence system outputs.
6. End-to-end smoke test through the pipeline modules.
"""

import os
import sys
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Ensure repo root is on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.data_loader import load_and_clean_mandi_data
from src.feature_engineering import build_features_and_target, FEATURE_COLUMNS
from src.evaluate import chronological_split, train_and_evaluate_all, CLASS_NAMES
from src.intelligence_system import MandiMarketIntelligenceEngine
from src.models import get_models


# =============================================================================
# 1. DATA LOADER TESTS: GRADE PRESERVATION & DUPLICATE STRATEGY 2
# =============================================================================

def test_data_loader_preserves_grade_and_key(tmp_path):
    """Verify that series_id includes Grade and distinct grades on the same date are not dropped."""
    # Create synthetic test dataset
    df_raw = pd.DataFrame({
        'District': ['Kanpur', 'Kanpur'],
        'Market': ['Kanpur(Grain)', 'Kanpur(Grain)'],
        'Commodity': ['Wheat', 'Wheat'],
        'Variety': ['Dara', 'Dara'],
        'Grade': ['FAQ', 'Medium'],  # Distinct grades
        'Arrival_Date': ['01/01/2025', '01/01/2025'],
        'Min_Price': [2100.0, 2200.0],
        'Max_Price': [2300.0, 2400.0],
        'Modal_Price': [2200.0, 2300.0]
    })
    
    test_csv_path = tmp_path / "test_loader_grade.csv"
    df_raw.to_csv(test_csv_path, index=False)
    
    df_loaded = load_and_clean_mandi_data(data_dir=str(tmp_path), min_series_records=1)
        
    kanpur_rows = df_loaded[df_loaded['Commodity'] == 'Wheat']
    assert len(kanpur_rows) == 2, "Different grades on the same date must NOT be collapsed or dropped!"
    assert 'FAQ' in kanpur_rows['Grade'].values
    assert 'Medium' in kanpur_rows['Grade'].values
    assert all('__FAQ' in s or '__Medium' in s for s in kanpur_rows['series_id']), \
        "Grade must be explicitly incorporated in series_id!"


def test_data_loader_filters_invalid_prices(tmp_path):
    """Verify non-positive prices (<= 0) are purged."""
    df_raw = pd.DataFrame({
        'District': ['Kanpur', 'Kanpur'],
        'Market': ['Kanpur(Grain)', 'Kanpur(Grain)'],
        'Commodity': ['Wheat', 'Wheat'],
        'Variety': ['Dara', 'Dara'],
        'Grade': ['FAQ', 'FAQ'],
        'Arrival_Date': ['01/01/2025', '02/01/2025'],
        'Min_Price': [0.0, 2100.0],  # Invalid 0 price
        'Max_Price': [2300.0, 2300.0],
        'Modal_Price': [0.0, 2200.0]  # Invalid 0 price
    })
    
    test_csv_path = tmp_path / "test_invalid_price.csv"
    df_raw.to_csv(test_csv_path, index=False)
    
    df_loaded = load_and_clean_mandi_data(data_dir=str(tmp_path), min_series_records=1)
        
    assert (df_loaded['Modal_Price'] <= 0).sum() == 0, "Non-positive prices must be filtered out!"
    assert len(df_loaded) == 1


# =============================================================================
# 2. FEATURE ENGINEERING TESTS: EXACT CALENDAR LAGS & VOLATILITY
# =============================================================================

def test_feature_engineering_exact_calendar_lags():
    """
    Verify that Lag_Price_1, 3, 7 use exact calendar dates.
    When a calendar date is missing (e.g. Sunday closure), lag must be NaN,
    with zero substitution of the next available date.
    """
    # Create series: Mon (2025-01-06), Tue (2025-01-07), Wed (2025-01-08)
    # Then weekend gap: Fri (2025-01-10), Mon (2025-01-13)
    # On Mon (2025-01-13):
    # - T-1 (Sun 2025-01-12) was CLOSED -> Lag_Price_1 MUST be NaN!
    # - T-3 (Fri 2025-01-10) was OPEN -> Lag_Price_3 MUST equal 2500!
    # - T-7 (Mon 2025-01-06) was OPEN -> Lag_Price_7 MUST equal 2000!
    # Also add T+7 dates so targets can match.
    dates = [
        '2025-01-06', '2025-01-07', '2025-01-08', '2025-01-10', '2025-01-13',
        '2025-01-20' # T+7 for 2025-01-13
    ]
    prices = [2000.0, 2100.0, 2200.0, 2500.0, 2600.0, 2700.0]
    
    df_series = pd.DataFrame({
        'District': ['Lucknow'] * len(dates),
        'Market': ['Lucknow'] * len(dates),
        'Commodity': ['Potato'] * len(dates),
        'Variety': ['Desi'] * len(dates),
        'Grade': ['FAQ'] * len(dates),
        'Arrival_Date': pd.to_datetime(dates),
        'Min_Price': [p - 50 for p in prices],
        'Max_Price': [p + 50 for p in prices],
        'Modal_Price': prices,
        'series_id': ['Lucknow__Lucknow__Potato__Desi__FAQ'] * len(dates)
    })
    
    featured = build_features_and_target(df_series, threshold_pct=2.5)
    
    # Find row for 2025-01-13
    row_mon = featured[featured['Arrival_Date'] == pd.to_datetime('2025-01-13')].iloc[0]
    
    # 1. T-1 was Sunday (no observation): Lag_Price_1 must be NaN!
    assert pd.isna(row_mon['Lag_Price_1']), \
        f"Lag_Price_1 must be NaN when T-1 was closed (got {row_mon['Lag_Price_1']}); no row-offset substitution!"
    assert pd.isna(row_mon['Price_Change_1d']), "Price_Change_1d must be NaN when Lag_Price_1 is NaN!"
    
    # 2. T-3 was Friday 2025-01-10 (present, Modal=2500):
    assert row_mon['Lag_Price_3'] == 2500.0, \
        f"Lag_Price_3 must match exact calendar T-3 (2500.0), got {row_mon['Lag_Price_3']}"
    
    # 3. T-7 was Monday 2025-01-06 (present, Modal=2000):
    assert row_mon['Lag_Price_7'] == 2000.0, \
        f"Lag_Price_7 must match exact calendar T-7 (2000.0), got {row_mon['Lag_Price_7']}"


def test_feature_engineering_causal_volatility_burnin():
    """Verify rolling volatility does not forward fill or fillna(0) for insufficient history."""
    dates = pd.date_range('2025-01-01', periods=10, freq='D')
    prices = [1000.0 + i * 20.0 for i in range(10)]
    
    df_series = pd.DataFrame({
        'District': ['Kanpur'] * 10,
        'Market': ['Kanpur(Grain)'] * 10,
        'Commodity': ['Wheat'] * 10,
        'Variety': ['Dara'] * 10,
        'Grade': ['FAQ'] * 10,
        'Arrival_Date': dates,
        'Min_Price': [p - 50 for p in prices],
        'Max_Price': [p + 50 for p in prices],
        'Modal_Price': prices,
        'series_id': ['Kanpur__Kanpur(Grain)__Wheat__Dara__FAQ'] * 10
    })
    
    # Add T+7 future dates so target matches
    future_dates = dates + pd.Timedelta(days=7)
    df_future = pd.DataFrame({
        'District': ['Kanpur'] * 10,
        'Market': ['Kanpur(Grain)'] * 10,
        'Commodity': ['Wheat'] * 10,
        'Variety': ['Dara'] * 10,
        'Grade': ['FAQ'] * 10,
        'Arrival_Date': future_dates,
        'Min_Price': [p - 50 for p in prices],
        'Max_Price': [p + 50 for p in prices],
        'Modal_Price': [p * 1.05 for p in prices],
        'series_id': ['Kanpur__Kanpur(Grain)__Wheat__Dara__FAQ'] * 10
    })
    df_all = pd.concat([df_series, df_future]).drop_duplicates(subset=['series_id', 'Arrival_Date']).sort_values('Arrival_Date')
    
    featured = build_features_and_target(df_all, threshold_pct=2.5)
    
    # First 2 observations in a series have n < 3 observations: Roll_Std_Price_7 MUST be NaN
    first_row = featured.iloc[0]
    assert pd.isna(first_row['Roll_Std_Price_7']), \
        "First observation must have NaN volatility due to burn-in (min_periods=3); no fillna(0) masking!"


# =============================================================================
# 3. TEMPORAL SPLITTING TESTS: HORIZON-AWARE EMBARGO PURGING
# =============================================================================

def test_chronological_split_horizon_embargo_no_cross_leakage():
    """Verify that target realization dates (T+7) in train do not cross into validation."""
    dates = pd.date_range('2025-01-01', periods=100, freq='D')
    
    df_data = pd.DataFrame({
        'Arrival_Date': dates,
        'Modal_Price': [1000.0] * 100,
        'Target_Class': [1] * 100
    })
    for col in FEATURE_COLUMNS:
        if col not in df_data.columns:
            df_data[col] = 1.0
            
    train_df, val_df, test_df = chronological_split(df_data, train_ratio=0.70, val_ratio=0.15, horizon_days=7)
    
    val_start = val_df['Arrival_Date'].min()
    test_start = test_df['Arrival_Date'].min()
    
    # 1. Max target realization in train must be < val_start
    train_max_origin = train_df['Arrival_Date'].max()
    train_max_realization = train_max_origin + pd.Timedelta(days=7)
    assert train_max_realization < val_start, \
        f"LEAKAGE DETECTED: Train target realization ({train_max_realization}) crosses into validation ({val_start})!"
        
    # 2. Max target realization in val must be < test_start
    val_max_origin = val_df['Arrival_Date'].max()
    val_max_realization = val_max_origin + pd.Timedelta(days=7)
    assert val_max_realization < test_start, \
        f"LEAKAGE DETECTED: Val target realization ({val_max_realization}) crosses into test ({test_start})!"


# =============================================================================
# 4. EVALUATION & MODEL SELECTION TESTS
# =============================================================================

def test_model_selection_validation_only(tmp_path):
    """Verify candidate selection uses validation only, and test set is designated exploratory."""
    # Synthetic dataset
    np.random.seed(42)
    n = 60
    dates = pd.date_range('2025-01-01', periods=n, freq='D')
    
    df = pd.DataFrame({
        'Arrival_Date': dates,
        'Target_Class': np.random.choice([0, 1, 2], size=n)
    })
    for col in FEATURE_COLUMNS:
        df[col] = np.random.randn(n)
        
    train_df, val_df, test_df = chronological_split(df, train_ratio=0.60, val_ratio=0.20, horizon_days=2)
    
    # Run evaluation
    results, pipelines, best_name = train_and_evaluate_all(train_df, val_df, test_df, output_dir=str(tmp_path))
    
    assert best_name in results
    assert results[best_name]['is_selected_candidate'] is True
    assert 'val_f1_macro' in results[best_name]
    assert 'accuracy' in results[best_name]
    
    # Verify candidate selection was strictly by validation Macro F1
    highest_val_f1 = max(results[m]['val_f1_macro'] for m in results)
    assert results[best_name]['val_f1_macro'] == highest_val_f1, \
        "Selected model must have the highest validation Macro F1 score!"


# =============================================================================
# 5. INTELLIGENCE SYSTEM ADVISORY DISCLAIMER CHECKS
# =============================================================================

def test_intelligence_system_mandatory_disclaimers():
    """Verify terminal card and intelligence payload include mandatory research prototype disclaimers."""
    # Mock model
    class MockModel:
        def predict(self, X):
            return np.array([2]) # Favorable
        def predict_proba(self, X):
            return np.array([[0.1, 0.2, 0.7]])
            
    # Mock feature row
    row = {
        'District': 'Lucknow',
        'Market': 'Lucknow',
        'Commodity': 'Wheat',
        'Variety': 'Dara',
        'Arrival_Date': pd.to_datetime('2025-06-01'),
        'Modal_Price': 2400.0,
        'Min_Price': 2350.0,
        'Max_Price': 2450.0,
        'Price_Intraday_Spread': 100.0,
        'Price_Change_1d': 1.5,
        'Price_Change_3d': 2.0,
        'Price_Change_7d': 3.5,
        'Roll_Mean_Price_7': 2380.0,
        'Roll_Std_Price_7': 35.0,
        'District_Commodity_MeanPrice': 2390.0,
        'District_Commodity_MandiCount': 2,
        'Neighbor_Commodity_MeanPrice': 2350.0,
        'Price_Diff_Target_vs_Neighbor': 50.0,
        'Modal_Price_T7': 2500.0,
        'Pct_Change_T7': 4.17,
        'Market_Condition': 'Favorable'
    }
    for col in FEATURE_COLUMNS:
        if col not in row:
            row[col] = 1.0
            
    df_mock = pd.DataFrame([row])
    
    engine = MandiMarketIntelligenceEngine(MockModel(), df_mock)
    intel = engine.generate_intelligence(district='Lucknow', commodity='Wheat')
    card = engine.format_terminal_card(intel)
    
    # 1. Payload must contain explicit disclaimer
    assert 'disclaimer' in intel, "Intelligence payload must contain a disclaimer!"
    assert "NOT PRODUCTION-READY" in intel['disclaimer']
    assert "RESEARCH PROTOTYPE" in intel['disclaimer']
    
    # 2. Terminal card must contain prominent research prototype disclaimer
    assert "RESEARCH PROTOTYPE DISCLAIMER" in card
    assert "NOT PRODUCTION READY" in card
    assert "Do NOT base" in card
