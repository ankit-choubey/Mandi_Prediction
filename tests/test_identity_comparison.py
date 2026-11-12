"""
Unit tests for narrow shared identity comparison helpers (src/identity_comparison.py).

Tests manifest metric extraction with row conservation, Excel reclassification
precedence and disjoint disposition conservation, causal train-only eligibility
reconstruction, and future mutation invariance on synthetic fixtures.
"""

from typing import Dict, Any
import numpy as np
import pandas as pd
import pytest

from src.identity_comparison import (
    extract_manifest_dispositions,
    compare_panel_dispositions,
    classify_excel_against_panel,
    evaluate_causal_train_eligibility_sensitivity,
    verify_future_mutation_invariance
)


class TestManifestExtractionAndConservation:
    """Tests for extract_manifest_dispositions fail-closed checks and row conservation."""

    @pytest.fixture
    def valid_manifest(self) -> Dict[str, Any]:
        return {
            "summary_metrics": {
                "total_raw_rows": 472385,
                "total_valid_parsed_rows": 472358,
                "total_dropped_raw_rows": 27,
                "exact_duplicates_deduplicated": 855,
                "ambiguous_same_grade_excluded_rows": 2936,
                "low_observation_series_dropped_rows": 5350,
                "final_clean_rows": 463217
            }
        }

    def test_extract_manifest_dispositions_success(self, valid_manifest):
        """Dispositions are successfully extracted and conservation holds: 463217+855+2936+5350+27 == 472385."""
        res = extract_manifest_dispositions(valid_manifest)
        assert res["raw_rows_in"] == 472385
        assert res["valid_parsed_rows"] == 472358
        assert res["invalid_dropped_rows"] == 27
        assert res["duplicates_deduplicated"] == 855
        assert res["conflicts_quarantined"] == 2936
        assert res["low_obs_dropped"] == 5350
        assert res["accepted_rows"] == 463217
        assert res["row_conservation_verified"] is True

    def test_extract_manifest_dispositions_missing_section_fails(self):
        """Missing summary_metrics section raises KeyError."""
        with pytest.raises(KeyError, match="summary_metrics"):
            extract_manifest_dispositions({"raw_rows_in": 100})

    def test_extract_manifest_dispositions_missing_field_fails(self, valid_manifest):
        """Missing individual required field in summary_metrics raises KeyError."""
        del valid_manifest["summary_metrics"]["final_clean_rows"]
        with pytest.raises(KeyError, match="missing required fields"):
            extract_manifest_dispositions(valid_manifest)

    def test_extract_manifest_dispositions_conservation_violation_fails(self, valid_manifest):
        """Violated row conservation identity raises ValueError."""
        valid_manifest["summary_metrics"]["final_clean_rows"] = 460000  # Altered!
        with pytest.raises(ValueError, match="Row conservation assertion violated"):
            extract_manifest_dispositions(valid_manifest)


class TestComparePanelDispositions:
    """Tests for compare_panel_dispositions side-by-side comparison."""

    def test_compare_panel_dispositions(self):
        m1 = {
            "summary_metrics": {
                "total_raw_rows": 1000,
                "total_valid_parsed_rows": 990,
                "total_dropped_raw_rows": 10,
                "exact_duplicates_deduplicated": 20,
                "ambiguous_same_grade_excluded_rows": 30,
                "low_observation_series_dropped_rows": 40,
                "final_clean_rows": 900
            }
        }
        m2 = {
            "summary_metrics": {
                "total_raw_rows": 1000,
                "total_valid_parsed_rows": 990,
                "total_dropped_raw_rows": 10,
                "exact_duplicates_deduplicated": 20,
                "ambiguous_same_grade_excluded_rows": 30,
                "low_observation_series_dropped_rows": 20,
                "final_clean_rows": 920
            }
        }
        df_v2 = pd.DataFrame({
            "District": ["Lucknow"] * 900,
            "Market": ["Lucknow"] * 900,
            "series_id": ["s1"] * 900
        })
        df_v21 = pd.DataFrame({
            "District": ["Lucknow"] * 920,
            "Market": ["Lucknow"] * 920,
            "series_id": ["s1"] * 920
        })

        comp = compare_panel_dispositions(m1, m2, df_v2, df_v21)
        assert comp["overall_delta"]["accepted_delta"] == 20
        assert comp["overall_delta"]["low_obs_delta"] == -20
        assert len(comp["district_comparison"]) == 5


class TestClassifyExcelAgainstPanel:
    """Tests for classify_excel_against_panel precedence and category conservation."""

    @pytest.fixture
    def excel_fixture(self) -> pd.DataFrame:
        return pd.DataFrame([
            # 1. Exact match
            {"District": "Ghaziabad", "Market": "Ghaziabad", "Commodity": "Potato", "Variety": "Desi", "Grade": "FAQ", "Arrival_Date": "2025-01-10", "Modal_Price": 1200.0},
            # 2. Different price match
            {"District": "Ghaziabad", "Market": "Hapur", "Commodity": "Potato", "Variety": "Desi", "Grade": "FAQ", "Arrival_Date": "2025-01-10", "Modal_Price": 1200.0},
            # 3. Quarantined Strategy 2 conflict
            {"District": "Lucknow", "Market": "Lucknow", "Commodity": "Potato", "Variety": "Desi", "Grade": "FAQ", "Arrival_Date": "2025-01-12", "Modal_Price": 1500.0},
            # 4. Low-obs dropped
            {"District": "Unnao", "Market": "Purwa", "Commodity": "Tomato", "Variety": "Desi", "Grade": "FAQ", "Arrival_Date": "2025-01-15", "Modal_Price": 800.0},
            # 5. Spelling unmapped (market not in district)
            {"District": "Jhansi", "Market": "UnknownMarketX", "Commodity": "Wheat", "Variety": "Dara", "Grade": "FAQ", "Arrival_Date": "2025-01-10", "Modal_Price": 2200.0},
            # 6. Absent from raw (known market, but date absent from raw)
            {"District": "Jhansi", "Market": "Moth", "Commodity": "Wheat", "Variety": "Dara", "Grade": "FAQ", "Arrival_Date": "2025-01-20", "Modal_Price": 2250.0},
        ])

    @pytest.fixture
    def panel_fixture(self) -> pd.DataFrame:
        return pd.DataFrame([
            # Row 1 in panel with exact price (1200.0)
            {"District": "Ghaziabad", "Market": "Ghaziabad", "Commodity": "Potato", "Variety": "Desi", "Grade": "FAQ", "Arrival_Date": "2025-01-10", "Modal_Price": 1200.0},
            # Row 2 in panel with differing price (1250.0 vs 1200.0)
            {"District": "Ghaziabad", "Market": "Hapur", "Commodity": "Potato", "Variety": "Desi", "Grade": "FAQ", "Arrival_Date": "2025-01-10", "Modal_Price": 1250.0},
        ])

    @pytest.fixture
    def raw_fixture(self) -> pd.DataFrame:
        return pd.DataFrame([
            {"District": "Jhansi", "Market": "Moth", "Commodity": "Wheat", "Variety": "Dara", "Grade": "FAQ", "Arrival_Date": "2025-01-01", "Modal_Price": 2200.0},
            {"District": "Jhansi", "Market": "Jhansi", "Commodity": "Wheat", "Variety": "Dara", "Grade": "FAQ", "Arrival_Date": "2025-01-01", "Modal_Price": 2200.0},
        ])

    def test_classify_excel_precedence_and_conservation(self, excel_fixture, panel_fixture, raw_fixture):
        """Tests that Excel rows are partitioned into disjoint categories with conservation."""
        quarantined_keys = {
            ("lucknow", "lucknow", "potato", "desi", "faq", "2025-01-12")
        }
        low_obs_keys = {
            ("unnao", "purwa", "tomato", "desi", "faq", "2025-01-15")
        }

        res = classify_excel_against_panel(
            df_excel=excel_fixture,
            df_panel=panel_fixture,
            df_raw=raw_fixture,
            quarantined_keys=quarantined_keys,
            low_obs_keys=low_obs_keys
        )

        assert res["total_excel_rows"] == 6
        assert res["matched_exact"] == 1
        assert res["matched_different"] == 1
        assert res["categories"]["quarantined_strategy2"] == 1
        assert res["categories"]["low_obs_dropped"] == 1
        assert res["categories"]["spelling_unmapped"] == 1
        assert res["categories"]["absent_from_raw"] == 1
        assert res["categories"]["other"] == 0
        assert res["category_conservation_check"] is True

        # Check per-row classifications
        clf_list = list(res["classifications_df"]["classification"])
        expected = [
            "matched_exact",
            "matched_different",
            "quarantined_strategy2",
            "low_obs_dropped",
            "spelling_unmapped",
            "absent_from_raw"
        ]
        assert clf_list == expected


class TestCausalEligibilityAndMutationInvariance:
    """Tests for causal train-only series eligibility and future mutation invariance."""

    @pytest.fixture
    def synthetic_history(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        # Create 100 daily observations for Series A (2025-01-01 to 2025-04-10)
        # Create 10 daily observations for Series B (2025-01-01 to 2025-01-10)
        dates_a = pd.date_range("2025-01-01", periods=100, freq="D").strftime("%Y-%m-%d")
        df_a = pd.DataFrame({
            "Arrival_Date": dates_a,
            "District": "Ghaziabad",
            "Market": "Ghaziabad",
            "Commodity": "Potato",
            "Variety": "Desi",
            "Grade": "FAQ",
            "Modal_Price": 1200.0
        })

        dates_b = pd.date_range("2025-01-01", periods=10, freq="D").strftime("%Y-%m-%d")
        df_b = pd.DataFrame({
            "Arrival_Date": dates_b,
            "District": "Ghaziabad",
            "Market": "Muradnagar",
            "Commodity": "Tomato",
            "Variety": "Desi",
            "Grade": "FAQ",
            "Modal_Price": 800.0
        })

        df_raw = pd.concat([df_a, df_b], ignore_index=True)

        alias_df = pd.DataFrame([
            {
                "district": "Ghaziabad",
                "market_raw": "Ghaziabad",
                "market_canonical": "Ghaziabad",
                "rule": "Identity",
                "evidence": "anchor",
                "first_date": "2021-09-01",
                "last_date": "2025-11-04",
                "overlap_days": 0,
                "price_agreement": None,
                "status": "ACCEPTED",
                "evidence_known_date": "2021-09-01",
                "assumed_known_date": "2021-09-01",
                "knowledge_provenance": "STRUCTURAL_IDENTITY_ANCHOR"
            },
            {
                "district": "Ghaziabad",
                "market_raw": "Muradnagar",
                "market_canonical": "Muradnagar",
                "rule": "Identity",
                "evidence": "anchor",
                "first_date": "2021-09-01",
                "last_date": "2025-11-04",
                "overlap_days": 0,
                "price_agreement": None,
                "status": "ACCEPTED",
                "evidence_known_date": "2021-09-01",
                "assumed_known_date": "2021-09-01",
                "knowledge_provenance": "STRUCTURAL_IDENTITY_ANCHOR"
            }
        ])

        return df_raw, alias_df

    def test_causal_train_eligibility_cutoffs(self, synthetic_history):
        """Tests that N_train >= 60 correctly selects Tier A series and invariant holds."""
        df_raw, alias_df = synthetic_history
        cutoffs = {
            "F1": "2025-01-31",  # 31 days of Series A: N_train=31 < 60 -> Tier A = 0
            "F2": "2025-03-15"   # 74 days of Series A: N_train=74 >= 60 -> Tier A = 1
        }

        res = evaluate_causal_train_eligibility_sensitivity(
            df_raw=df_raw,
            alias_df=alias_df,
            cutoffs=cutoffs,
            min_train_records=60
        )

        assert res["cutoffs"]["F1"]["tier_a_series_count"] == 0
        assert res["cutoffs"]["F2"]["tier_a_series_count"] == 1
        assert res["cutoffs"]["F2"]["tier_a_observations"] == 74
        assert res["cutoffs"]["F1"]["subset_invariant_holds"] is True
        assert res["cutoffs"]["F2"]["subset_invariant_holds"] is True

    def test_verify_future_mutation_invariance(self, synthetic_history):
        """Mutations dated strictly after cutoff do not alter training identities or counts."""
        df_raw, alias_df = synthetic_history
        is_invariant = verify_future_mutation_invariance(
            df_raw=df_raw,
            alias_df=alias_df,
            cutoff_date="2025-02-15"
        )
        assert is_invariant is True
