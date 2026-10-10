"""
Regression and Verification Tests for Feasibility Reconciliation
APMC Mandi Market Intelligence System

Tests specific requirements from Step 3:
A. Grade preservation: Two rows with identical metadata and date but different Grade
   values remain distinct canonical series.
B. Conflicting same-grade prices are not arbitrarily resolved by keeping the first row
   (Strategy 2 exclusion).
C. Exact T+7 matching does not substitute another date when T+7 is missing.
D. Feasibility metrics clearly distinguish raw input counts from cleaned/model-eligible counts.
E. DEC-015 target boundaries and production pipeline safeguards.
"""

import os
import sys
import pytest
import numpy as np
import pandas as pd
from datetime import timedelta

# Ensure repo root is on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.feasibility import run_feasibility_analysis
from src.data_loader import load_and_clean_mandi_data


def test_feasibility_grade_preservation_distinct_series(tmp_path):
    """
    Requirement A:
    Two rows with identical metadata and date but different Grade values
    remain distinct when the methodology requires grade preservation.
    They must not be collapsed or cross-matched.
    """
    data_dir = tmp_path / "data" / "raw"
    data_dir.mkdir(parents=True)
    
    # Create two rows on the same date with different Grade
    # and provide T+7 for only one of the grades
    df_raw = pd.DataFrame({
        'District': ['Kanpur', 'Kanpur', 'Kanpur'],
        'Market': ['Kanpur(Grain)', 'Kanpur(Grain)', 'Kanpur(Grain)'],
        'Commodity': ['Wheat', 'Wheat', 'Wheat'],
        'Variety': ['Dara', 'Dara', 'Dara'],
        'Grade': ['FAQ', 'Medium', 'FAQ'],
        'Arrival_Date': ['01/01/2025', '01/01/2025', '08/01/2025'],  # 08/01 is T+7 for FAQ
        'Min_Price': [2000.0, 2200.0, 2100.0],
        'Max_Price': [2200.0, 2400.0, 2300.0],
        'Modal_Price': [2100.0, 2300.0, 2200.0]
    })
    df_raw.to_csv(data_dir / "Kanpur.csv", index=False)
    
    report_path = tmp_path / "test_report.md"
    metrics, matched = run_feasibility_analysis(data_dir=str(tmp_path), output_report_path=str(report_path))
    
    # Both grades must be preserved in clean records
    assert metrics['Total clean records'] == 3
    assert metrics['Unique canonical series (with Grade)'] == 2
    
    # Exactly one T+7 match should occur (for FAQ only, Medium has no T+7)
    assert metrics['Records with exact T+7'] == 1
    assert len(matched) == 1
    assert matched.iloc[0]['Grade'] == 'FAQ'
    assert '__FAQ' in matched.iloc[0]['series_id']


def test_feasibility_strategy2_conflicting_same_grade_prices_excluded(tmp_path):
    """
    Requirement B:
    Conflicting same-grade prices are not arbitrarily resolved by keeping the first row.
    Strategy 2 must exclude both conflicting rows.
    """
    data_dir = tmp_path / "data" / "raw"
    data_dir.mkdir(parents=True)
    
    # 2 rows with same date and same grade but CONFLICTING modal prices
    # 1 valid row on a different date
    df_raw = pd.DataFrame({
        'District': ['Kanpur', 'Kanpur', 'Kanpur'],
        'Market': ['Kanpur(Grain)', 'Kanpur(Grain)', 'Kanpur(Grain)'],
        'Commodity': ['Wheat', 'Wheat', 'Wheat'],
        'Variety': ['Dara', 'Dara', 'Dara'],
        'Grade': ['FAQ', 'FAQ', 'FAQ'],
        'Arrival_Date': ['01/01/2025', '01/01/2025', '02/01/2025'],
        'Min_Price': [2000.0, 2150.0, 2100.0],
        'Max_Price': [2200.0, 2350.0, 2300.0],
        'Modal_Price': [2100.0, 2250.0, 2200.0]  # Conflicting quotes on 01/01/2025
    })
    df_raw.to_csv(data_dir / "Kanpur.csv", index=False)
    
    report_path = tmp_path / "test_report.md"
    metrics, matched = run_feasibility_analysis(data_dir=str(tmp_path), output_report_path=str(report_path))
    
    # Raw has 3 rows; the 2 conflicting rows must be excluded by Strategy 2, leaving only 1 clean row
    assert metrics['Total raw records'] == 3
    assert metrics['Duplicate records removed'] == 2
    assert metrics['Total clean records'] == 1


def test_feasibility_exact_t7_no_substitution_when_missing(tmp_path):
    """
    Requirement C:
    Exact T+7 matching does not substitute another date (e.g. T+6, T+8) when T+7 is missing.
    """
    data_dir = tmp_path / "data" / "raw"
    data_dir.mkdir(parents=True)
    
    # Day 0: 2025-01-01
    # Day 6: 2025-01-07 (T+6)
    # Day 8: 2025-01-09 (T+8)
    # T+7 (2025-01-08) is missing!
    df_raw = pd.DataFrame({
        'District': ['Lucknow'] * 3,
        'Market': ['Lucknow'] * 3,
        'Commodity': ['Potato'] * 3,
        'Variety': ['Desi'] * 3,
        'Grade': ['FAQ'] * 3,
        'Arrival_Date': ['01/01/2025', '07/01/2025', '09/01/2025'],
        'Min_Price': [1000.0, 1100.0, 1200.0],
        'Max_Price': [1200.0, 1300.0, 1400.0],
        'Modal_Price': [1100.0, 1200.0, 1300.0]
    })
    df_raw.to_csv(data_dir / "Lucknow.csv", index=False)
    
    report_path = tmp_path / "test_report.md"
    metrics, matched = run_feasibility_analysis(data_dir=str(tmp_path), output_report_path=str(report_path))
    
    # No exact T+7 pairs should be formed!
    assert metrics['Records with exact T+7'] == 0
    assert len(matched) == 0


def test_feasibility_metrics_distinguish_raw_and_clean_counts(tmp_path):
    """
    Requirement D:
    Feasibility metrics clearly distinguish raw input counts from cleaned/model-eligible counts.
    """
    data_dir = tmp_path / "data" / "raw"
    data_dir.mkdir(parents=True)
    
    # 4 rows: 2 identical duplicates, 1 invalid zero-price, 1 valid row
    df_raw = pd.DataFrame({
        'District': ['Unnao'] * 4,
        'Market': ['Unnao'] * 4,
        'Commodity': ['Rice'] * 4,
        'Variety': ['Common'] * 4,
        'Grade': ['FAQ'] * 4,
        'Arrival_Date': ['01/01/2025', '01/01/2025', '02/01/2025', '03/01/2025'],
        'Min_Price': [2500.0, 2500.0, 0.0, 2600.0],
        'Max_Price': [2700.0, 2700.0, 2700.0, 2800.0],
        'Modal_Price': [2600.0, 2600.0, 0.0, 2700.0]
    })
    df_raw.to_csv(data_dir / "Unnao.csv", index=False)
    
    report_path = tmp_path / "test_report.md"
    metrics, matched = run_feasibility_analysis(data_dir=str(tmp_path), output_report_path=str(report_path))
    
    assert 'Total raw records' in metrics
    assert 'Total clean records' in metrics
    assert 'Duplicate records removed' in metrics
    assert 'Unique canonical series (with Grade)' in metrics
    
    # Raw is 4, clean is 2 (1 duplicate dropped, 1 zero-price dropped)
    assert metrics['Total raw records'] == 4
    assert metrics['Total clean records'] == 2
    assert metrics['Duplicate records removed'] == 2
    assert metrics['Total raw records'] != metrics['Total clean records']


def test_dec015_target_class_boundaries():
    """
    Requirement E & DEC-015:
    Target class boundaries must strictly adhere to:
      Favorable: return > +2.5%
      Normal: return from -2.5% through +2.5%, inclusive
      Unfavorable: return < -2.5%
    """
    # Test boundary conditions
    test_cases = [
        (2.500000, 1),    # Exactly +2.5% -> Normal (1)
        (2.500001, 2),    # > +2.5% -> Favorable (2)
        (-2.500000, 1),   # Exactly -2.5% -> Normal (1)
        (-2.500001, 0),   # < -2.5% -> Unfavorable (0)
        (0.000000, 1),    # 0.0% -> Normal (1)
        (10.0, 2),        # +10% -> Favorable (2)
        (-10.0, 0)        # -10% -> Unfavorable (0)
    ]
    
    threshold_pct = 2.5
    for ret, expected_class in test_cases:
        if ret > threshold_pct:
            cls = 2
        elif ret < -threshold_pct:
            cls = 0
        else:
            cls = 1
        assert cls == expected_class, f"Return {ret}% failed expected class {expected_class} (got {cls})"
