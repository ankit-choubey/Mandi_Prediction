"""
Phase 1 Data Integrity & Calendar Target Matching Automated Test Suite
Tests exact calendar joins, missingness separation, duplicate date ambiguity,
price ordering anomalies, and target boundary edge cases.
"""

import os
import glob
import pytest
import pandas as pd
import numpy as np
from datetime import timedelta

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
RAW_DIR = os.path.join(ROOT_DIR, "data", "raw")
OUT_DIR = os.path.join(ROOT_DIR, "backing", "phase_01", "outputs")

# Helper to load raw master data
def load_raw_data():
    raw_files = sorted(glob.glob(os.path.join(RAW_DIR, "*.csv")))
    dfs = []
    for f in raw_files:
        df_temp = pd.read_csv(f)
        df_temp['Source_File'] = os.path.basename(f)
        dfs.append(df_temp)
    df = pd.concat(dfs, ignore_index=True)
    df['Arrival_Date_Parsed'] = pd.to_datetime(df['Arrival_Date'], format='%d/%m/%Y', errors='coerce')
    df['Modal_Price_Num'] = pd.to_numeric(df['Modal_Price'], errors='coerce')
    df['Min_Price_Num'] = pd.to_numeric(df['Min_Price'], errors='coerce')
    df['Max_Price_Num'] = pd.to_numeric(df['Max_Price'], errors='coerce')
    series_cols = ['District', 'Market', 'Commodity', 'Variety']
    df['series_id'] = df[series_cols].astype(str).agg('__'.join, axis=1)
    return df

class TestPhase01DataIntegrity:

    @classmethod
    def setup_class(cls):
        cls.df = load_raw_data()
        cls.series_cols = ['District', 'Market', 'Commodity', 'Variety']
        cls.clean_df = cls.df.drop_duplicates(subset=cls.series_cols + ['Arrival_Date_Parsed'], keep='first').copy()
        cls.clean_df.sort_values(by=['series_id', 'Arrival_Date_Parsed'], inplace=True)
        cls.clean_df.reset_index(drop=True, inplace=True)

    def test_total_raw_record_count(self):
        """Verify exact total raw record count across all 5 files is 160,192."""
        assert len(self.df) == 160192, f"Expected 160,192 records, got {len(self.df):,}"

    def test_exact_calendar_t7_matching(self):
        """Verify exact calendar matching at T+7: must match exactly Arrival_Date + 7 days without substitution."""
        t7_lookup = self.clean_df[['series_id', 'Arrival_Date_Parsed', 'Modal_Price_Num']].copy()
        self.clean_df['Target_Date_T7'] = self.clean_df['Arrival_Date_Parsed'] + timedelta(days=7)
        
        matched = pd.merge(
            self.clean_df,
            t7_lookup,
            left_on=['series_id', 'Target_Date_T7'],
            right_on=['series_id', 'Arrival_Date_Parsed'],
            suffixes=('', '_T7'),
            how='inner'
        )
        # Expected exact matches on deduplicated series: 117,176
        assert len(matched) == 117176, f"Expected 117,176 exact T+7 matches, got {len(matched):,}"
        
        # Verify that for every matched row, Target_Date == Arrival_Date_T7
        day_diffs = (matched['Arrival_Date_Parsed_T7'] - matched['Arrival_Date_Parsed']).dt.days
        assert (day_diffs == 7).all(), "Found matched rows with time delta != 7 calendar days!"

    def test_exact_calendar_t3_matching(self):
        """Verify exact calendar matching at T+3: must match exactly Arrival_Date + 3 days."""
        t3_lookup = self.clean_df[['series_id', 'Arrival_Date_Parsed', 'Modal_Price_Num']].copy()
        self.clean_df['Target_Date_T3'] = self.clean_df['Arrival_Date_Parsed'] + timedelta(days=3)
        
        matched_t3 = pd.merge(
            self.clean_df,
            t3_lookup,
            left_on=['series_id', 'Target_Date_T3'],
            right_on=['series_id', 'Arrival_Date_Parsed'],
            suffixes=('', '_T3'),
            how='inner'
        )
        assert len(matched_t3) == 110349, f"Expected 110,349 exact T+3 matches, got {len(matched_t3):,}"
        
        day_diffs_t3 = (matched_t3['Arrival_Date_Parsed_T3'] - matched_t3['Arrival_Date_Parsed']).dt.days
        assert (day_diffs_t3 == 3).all(), "Found matched rows with time delta != 3 calendar days!"

    def test_missing_target_separation_t7(self):
        """Verify separation between boundary-truncated targets and interior missing gaps."""
        max_date = self.clean_df['Arrival_Date_Parsed'].max()
        target_dates = self.clean_df['Arrival_Date_Parsed'] + timedelta(days=7)
        
        is_boundary_trunc = target_dates > max_date
        n_boundary = is_boundary_trunc.sum()
        n_eligible = len(self.clean_df) - n_boundary
        
        # Exact values verified
        assert n_boundary == 1005, f"Expected 1,005 boundary-truncated origins, got {n_boundary}"
        assert n_eligible == 154736, f"Expected 154,736 eligible origins, got {n_eligible}"
        
        # Matches inside eligible set
        t7_lookup = self.clean_df[['series_id', 'Arrival_Date_Parsed', 'Modal_Price_Num']].copy()
        matched = pd.merge(
            self.clean_df[~is_boundary_trunc],
            t7_lookup,
            left_on=['series_id', 'Target_Date_T7'],
            right_on=['series_id', 'Arrival_Date_Parsed'],
            how='inner'
        )
        n_matched = len(matched)
        n_interior_missing = n_eligible - n_matched
        
        assert n_matched == 117176
        assert n_interior_missing == 37560, f"Expected 37,560 interior missing, got {n_interior_missing}"
        assert (n_matched + n_interior_missing + n_boundary) == len(self.clean_df)

    def test_duplicate_date_ambiguity(self):
        """
        Verify that duplicate series-date groups exist and differentiate:
        - 4,363 groups have conflicting Modal prices
        - 17 groups have identical Modal price but conflicting Min/Max spread
        - 13 groups have completely identical Modal, Min, and Max prices
        Total duplicate groups: 4,393
        """
        dupe_grouped = self.df.groupby(self.series_cols + ['Arrival_Date_Parsed'])
        dupe_counts = dupe_grouped.size()
        groups_gt1 = dupe_counts[dupe_counts > 1]
        
        assert len(groups_gt1) == 4393, f"Expected 4,393 duplicate groups, got {len(groups_gt1)}"
        
        modal_conflicts = 0
        any_conflicts = 0
        fully_identical = 0
        
        for name, grp in dupe_grouped:
            if len(grp) > 1:
                modal_diff = grp['Modal_Price_Num'].nunique() > 1
                min_diff = grp['Min_Price_Num'].nunique() > 1
                max_diff = grp['Max_Price_Num'].nunique() > 1
                
                if modal_diff:
                    modal_conflicts += 1
                if modal_diff or min_diff or max_diff:
                    any_conflicts += 1
                else:
                    fully_identical += 1
                    
        assert modal_conflicts == 4363, f"Expected 4,363 modal price conflicts, got {modal_conflicts}"
        assert any_conflicts == 4380, f"Expected 4,380 any price conflicts, got {any_conflicts}"
        assert fully_identical == 13, f"Expected 13 fully identical duplicate groups, got {fully_identical}"
        assert (any_conflicts + fully_identical) == 4393

    def test_price_order_violations_detection(self):
        """Verify detection of exactly 6 price ordering violations (Modal > Max) due to Max_Price=0."""
        valid_prices = self.df.dropna(subset=['Min_Price_Num', 'Modal_Price_Num', 'Max_Price_Num'])
        violations = valid_prices[(valid_prices['Min_Price_Num'] > valid_prices['Modal_Price_Num']) | 
                                  (valid_prices['Modal_Price_Num'] > valid_prices['Max_Price_Num'])]
        
        assert len(violations) == 6, f"Expected exactly 6 price order violations, got {len(violations)}"
        # All 6 must have Max_Price == 0
        assert (violations['Max_Price_Num'] == 0.0).all(), "Not all violations were caused by Max_Price==0"

    def test_target_class_boundaries_and_edge_cases(self):
        """Verify target class boundary conditions at exact +/-2.5% and 0.0%."""
        t7_lookup = self.clean_df[['series_id', 'Arrival_Date_Parsed', 'Modal_Price_Num']].copy()
        matched = pd.merge(
            self.clean_df,
            t7_lookup,
            left_on=['series_id', 'Target_Date_T7'],
            right_on=['series_id', 'Arrival_Date_Parsed'],
            suffixes=('', '_T7'),
            how='inner'
        )
        matched['Pct_Change_T7'] = ((matched['Modal_Price_Num_T7'] - matched['Modal_Price_Num']) / matched['Modal_Price_Num']) * 100
        p = matched['Pct_Change_T7']
        
        # Edge cases
        exact_zeros = (p == 0.0).sum()
        exact_plus_25 = (p == 2.5).sum()
        exact_minus_25 = (p == -2.5).sum()
        
        assert exact_zeros == 20085, f"Expected 20,085 exact zeros, got {exact_zeros}"
        assert exact_plus_25 == 131, f"Expected 131 exact +2.5% matches, got {exact_plus_25}"
        assert exact_minus_25 == 141, f"Expected 141 exact -2.5% matches, got {exact_minus_25}"
        
        # Boundary logic compliance
        favorable = (p >= 2.5).sum()
        unfavorable = (p <= -2.5).sum()
        normal = ((p > -2.5) & (p < 2.5)).sum()
        
        assert (favorable + unfavorable + normal) == len(matched)
        assert favorable == 23118
        assert normal == 67775
        assert unfavorable == 26283

    def test_output_csv_artifacts_exist(self):
        """Verify that all 9 required Phase 1 output CSV files exist and are non-empty."""
        expected_files = [
            "input_inventory.csv",
            "observation_gap_summary.csv",
            "duplicate_groups.csv",
            "data_quality_flags.csv",
            "price_quality_summary.csv",
            "market_mapping_review.csv",
            "exact_target_coverage.csv",
            "target_match_examples.csv",
            "class_distribution.csv"
        ]
        for ef in expected_files:
            fpath = os.path.join(OUT_DIR, ef)
            assert os.path.exists(fpath), f"Required output file {ef} missing from {OUT_DIR}"
            assert os.path.getsize(fpath) > 100, f"File {ef} is empty or suspiciously small"

if __name__ == "__main__":
    pytest.main(["-v", __file__])
