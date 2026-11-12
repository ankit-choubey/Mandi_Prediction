"""
Unit tests for narrow shared identity comparison helpers (src/identity_comparison.py).

Tests manifest metric extraction with row conservation, Excel reclassification
precedence and disjoint disposition conservation, causal train-only eligibility
reconstruction, and future mutation invariance on synthetic fixtures.
"""

from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd
import pytest

from src.identity_comparison import (
    extract_manifest_dispositions,
    compare_panel_dispositions,
    classify_excel_against_panel,
    reconstruct_cutoff_fold,
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
    """Tests for classify_excel_against_panel precedence, alias policy, and conservation."""

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
            raw_valid_df=raw_fixture,
            quarantined_keys=quarantined_keys,
            low_obs_keys=low_obs_keys,
            known_markets_by_district={"jhansi": {"moth", "jhansi"}}
        )

        assert res["total_excel_rows"] == 6
        assert res["matched_exact"] == 1
        assert res["matched_different"] == 1
        assert res["conflicting"] == 1
        assert res["low_obs"] == 1
        assert res["spelling_review"] == 1
        assert res["absent"] == 1
        assert res["other"] == 0
        assert res["category_conservation_check"] is True

        # Check per-row classifications
        clf_list = list(res["classifications_df"]["classification"])
        expected = [
            "matched_exact",
            "matched_different",
            "conflicting",
            "low_obs",
            "spelling-review",
            "absent"
        ]
        assert clf_list == expected

    def test_purwa_unmatched_under_review_and_matched_under_accepted(self):
        """Purwa vs Purwa APMC is unmatched under REVIEW policy and matched ONLY when an explicit accepted mapping exists."""
        df_ex = pd.DataFrame([{
            "District": "Unnao", "Market": "Purwa APMC", "Commodity": "Wheat",
            "Variety": "Dara", "Grade": "FAQ", "Arrival_Date": "2025-02-01", "Modal_Price": 2100.0
        }])
        df_pan = pd.DataFrame([{
            "District": "Unnao", "Market": "Purwa", "Commodity": "Wheat",
            "Variety": "Dara", "Grade": "FAQ", "Arrival_Date": "2025-02-01", "Modal_Price": 2100.0
        }])

        # 1. Under REVIEW policy (no accepted alias, review_markets contains the pair)
        res_review = classify_excel_against_panel(
            df_excel=df_ex,
            df_panel=df_pan,
            alias_mapping={},  # Not in accepted aliases!
            review_markets={("unnao", "purwa apmc")},
            known_markets_by_district={"unnao": {"purwa"}}
        )
        assert res_review["matched_exact"] == 0
        assert res_review["spelling_review"] == 1
        assert res_review["classifications_df"].iloc[0]["classification"] == "spelling-review"

        # 2. Under ACCEPTED policy (explicit accepted mapping provided)
        res_accepted = classify_excel_against_panel(
            df_excel=df_ex,
            df_panel=df_pan,
            alias_mapping={("unnao", "purwa apmc"): "Purwa"},
            review_markets=set(),
            known_markets_by_district={"unnao": {"purwa"}}
        )
        assert res_accepted["matched_exact"] == 1
        assert res_accepted["classifications_df"].iloc[0]["classification"] == "matched_exact"

    def test_baripaal_and_varipaal_remain_separate(self):
        """Baripaal APMC vs Varipaal remain distinct unless an explicit alias is declared."""
        df_ex = pd.DataFrame([{
            "District": "Kanpur", "Market": "Varipaal", "Commodity": "Potato",
            "Variety": "Desi", "Grade": "FAQ", "Arrival_Date": "2025-03-01", "Modal_Price": 1000.0
        }])
        df_pan = pd.DataFrame([{
            "District": "Kanpur", "Market": "Baripaal APMC", "Commodity": "Potato",
            "Variety": "Desi", "Grade": "FAQ", "Arrival_Date": "2025-03-01", "Modal_Price": 1000.0
        }])

        res = classify_excel_against_panel(
            df_excel=df_ex,
            df_panel=df_pan,
            alias_mapping={},  # Kept separate under candidate policy
            review_markets={("kanpur", "varipaal")},
            known_markets_by_district={"kanpur": {"baripaal apmc"}}
        )
        assert res["matched_exact"] == 0
        assert res["spelling_review"] == 1

    def test_accepted_jhansi_mapping(self):
        """Accepted Jhansi mapping maps Jhansi (Grain) APMC to Jhansi (Grain)."""
        df_ex = pd.DataFrame([{
            "District": "Jhansi", "Market": "Jhansi (Grain) APMC", "Commodity": "Wheat",
            "Variety": "Dara", "Grade": "FAQ", "Arrival_Date": "2025-04-01", "Modal_Price": 2300.0
        }])
        df_pan = pd.DataFrame([{
            "District": "Jhansi", "Market": "Jhansi (Grain)", "Commodity": "Wheat",
            "Variety": "Dara", "Grade": "FAQ", "Arrival_Date": "2025-04-01", "Modal_Price": 2300.0
        }])

        res = classify_excel_against_panel(
            df_excel=df_ex,
            df_panel=df_pan,
            alias_mapping={("jhansi", "jhansi (grain) apmc"): "Jhansi (Grain)"}
        )
        assert res["matched_exact"] == 1

    def test_grade_and_variety_remain_distinct(self):
        """Differing Variety or Grade prevents false match on natural key."""
        df_ex = pd.DataFrame([{
            "District": "Ghaziabad", "Market": "Ghaziabad", "Commodity": "Wheat",
            "Variety": "Dara", "Grade": "FAQ", "Arrival_Date": "2025-01-10", "Modal_Price": 2200.0
        }])
        # Panel has same date and market, but different variety
        df_pan = pd.DataFrame([{
            "District": "Ghaziabad", "Market": "Ghaziabad", "Commodity": "Wheat",
            "Variety": "Desi", "Grade": "FAQ", "Arrival_Date": "2025-01-10", "Modal_Price": 2200.0
        }])

        res = classify_excel_against_panel(df_excel=df_ex, df_panel=df_pan)
        assert res["matched_exact"] == 0
        assert res["classifications_df"].iloc[0]["classification"] == "other"

    def test_conflicting_duplicate_panel_keys_fail_closed(self):
        """Duplicate panel rows for the same natural key with conflicting prices raise ValueError."""
        df_pan_conflicting = pd.DataFrame([
            {"District": "Ghaziabad", "Market": "Ghaziabad", "Commodity": "Potato", "Variety": "Desi", "Grade": "FAQ", "Arrival_Date": "2025-01-10", "Modal_Price": 1200.0},
            {"District": "Ghaziabad", "Market": "Ghaziabad", "Commodity": "Potato", "Variety": "Desi", "Grade": "FAQ", "Arrival_Date": "2025-01-10", "Modal_Price": 1300.0},
        ])
        df_ex = pd.DataFrame([
            {"District": "Ghaziabad", "Market": "Ghaziabad", "Commodity": "Potato", "Variety": "Desi", "Grade": "FAQ", "Arrival_Date": "2025-01-10", "Modal_Price": 1200.0}
        ])

        with pytest.raises(ValueError, match="Duplicate conflicting panel key"):
            classify_excel_against_panel(df_excel=df_ex, df_panel=df_pan_conflicting, strict_panel_integrity=True)

    def test_invalid_prices_fail_closed_or_classify_invalid(self):
        """Non-positive or nonfinite prices in Excel are classified as invalid; invalid panel price fails closed."""
        df_ex = pd.DataFrame([
            {"District": "Ghaziabad", "Market": "Ghaziabad", "Commodity": "Potato", "Variety": "Desi", "Grade": "FAQ", "Arrival_Date": "2025-01-10", "Modal_Price": -50.0},
            {"District": "Ghaziabad", "Market": "Ghaziabad", "Commodity": "Potato", "Variety": "Desi", "Grade": "FAQ", "Arrival_Date": "2025-01-11", "Modal_Price": np.nan},
        ])
        df_pan = pd.DataFrame([
            {"District": "Ghaziabad", "Market": "Ghaziabad", "Commodity": "Potato", "Variety": "Desi", "Grade": "FAQ", "Arrival_Date": "2025-01-10", "Modal_Price": 1200.0}
        ])

        res = classify_excel_against_panel(df_excel=df_ex, df_panel=df_pan)
        assert res["invalid"] == 2
        assert res["matched_exact"] == 0

        # Non-positive price in panel raises ValueError under strict_panel_integrity
        df_pan_bad = pd.DataFrame([
            {"District": "Ghaziabad", "Market": "Ghaziabad", "Commodity": "Potato", "Variety": "Desi", "Grade": "FAQ", "Arrival_Date": "2025-01-10", "Modal_Price": -10.0}
        ])
        with pytest.raises(ValueError, match="Invalid nonfinite or non-positive price in panel"):
            classify_excel_against_panel(df_excel=df_ex, df_panel=df_pan_bad, strict_panel_integrity=True)


class TestCausalEligibilityAndCutoffReconstruction:
    """Tests for causal train-only series eligibility, coverage, fold boundaries, and mutation invariance."""

    @pytest.fixture
    def alias_df(self) -> pd.DataFrame:
        return pd.DataFrame([
            {
                "district": "Ghaziabad", "market_raw": "Ghaziabad", "market_canonical": "Ghaziabad",
                "rule": "Identity", "evidence": "anchor", "first_date": "2021-09-01", "last_date": "2025-11-04",
                "overlap_days": 0, "price_agreement": None, "status": "ACCEPTED",
                "evidence_known_date": "2021-09-01", "assumed_known_date": "2021-09-01",
                "knowledge_provenance": "STRUCTURAL_IDENTITY_ANCHOR"
            },
            {
                "district": "Ghaziabad", "market_raw": "Muradnagar", "market_canonical": "Muradnagar",
                "rule": "Identity", "evidence": "anchor", "first_date": "2021-09-01", "last_date": "2025-11-04",
                "overlap_days": 0, "price_agreement": None, "status": "ACCEPTED",
                "evidence_known_date": "2021-09-01", "assumed_known_date": "2021-09-01",
                "knowledge_provenance": "STRUCTURAL_IDENTITY_ANCHOR"
            }
        ])

    def test_sparse_60_obs_twenty_days_apart_fails_tier_a(self, alias_df):
        """Sparse 60 observations twenty days apart spans 1180 days (cov ~0.05 < 0.30) and MUST fail Tier A."""
        # 60 observations spaced every 20 days: span = 59 * 20 + 1 = 1181 days. Coverage = 60 / 1181 = 0.0508 < 0.30
        sparse_dates = [pd.Timestamp("2021-09-01") + pd.Timedelta(days=20 * i) for i in range(60)]
        df_sparse = pd.DataFrame({
            "Arrival_Date": [d.strftime("%Y-%m-%d") for d in sparse_dates],
            "District": "Ghaziabad", "Market": "Ghaziabad", "Commodity": "Wheat",
            "Variety": "Dara", "Grade": "FAQ", "Modal_Price": 2200.0
        })

        res = reconstruct_cutoff_fold(
            df_raw=df_sparse,
            alias_df=alias_df,
            train_end="2024-12-31",
            min_train_records=60,
            min_coverage=0.30
        )
        assert res["total_training_observations"] == 60
        assert res["tier_a_series_count"] == 0  # Fails due to coverage < 0.30!
        assert len(res["tier_a_series_set"]) == 0

    def test_dense_60_obs_passes_tier_a_and_120_passes_tier_b(self, alias_df):
        """60 dense consecutive observations pass Tier A (cov 1.0 >= 0.30); >=120 dense pass Tier B."""
        # 130 consecutive daily observations: span = 130 days, coverage = 1.0 >= 0.30
        dense_dates = pd.date_range("2024-01-01", periods=130, freq="D").strftime("%Y-%m-%d")
        df_dense = pd.DataFrame({
            "Arrival_Date": dense_dates,
            "District": "Ghaziabad", "Market": "Ghaziabad", "Commodity": "Wheat",
            "Variety": "Dara", "Grade": "FAQ", "Modal_Price": 2200.0
        })

        # Test at 60 obs (train_end = 2024-03-01: 61 days)
        res_60 = reconstruct_cutoff_fold(
            df_raw=df_dense,
            alias_df=alias_df,
            train_end="2024-03-01",
            min_train_records=60,
            min_coverage=0.30,
            tier_b_min_records=120
        )
        assert res_60["tier_a_series_count"] == 1
        assert res_60["tier_b_series_count"] == 0  # 61 < 120

        # Test at 130 obs (train_end = 2024-05-15: 130 days)
        res_120 = reconstruct_cutoff_fold(
            df_raw=df_dense,
            alias_df=alias_df,
            train_end="2024-05-15",
            min_train_records=60,
            min_coverage=0.30,
            tier_b_min_records=120
        )
        assert res_120["tier_a_series_count"] == 1
        assert res_120["tier_b_series_count"] == 1  # 130 >= 120

    def test_conflicting_quotes_quarantined_and_duplicates_deduplicated(self, alias_df):
        """Strategy 2 quarantines ALL rows for conflicting keys and drops exact duplicate quotes."""
        rows = [
            # Exact duplicates: two identical quotes on 2024-01-01
            {"Arrival_Date": "2024-01-01", "District": "Ghaziabad", "Market": "Ghaziabad", "Commodity": "Wheat", "Variety": "Dara", "Grade": "FAQ", "Modal_Price": 2000.0, "Min_Price": 1900.0, "Max_Price": 2100.0},
            {"Arrival_Date": "2024-01-01", "District": "Ghaziabad", "Market": "Ghaziabad", "Commodity": "Wheat", "Variety": "Dara", "Grade": "FAQ", "Modal_Price": 2000.0, "Min_Price": 1900.0, "Max_Price": 2100.0},
            # Conflicting quotes: two divergent quotes on 2024-01-02
            {"Arrival_Date": "2024-01-02", "District": "Ghaziabad", "Market": "Ghaziabad", "Commodity": "Wheat", "Variety": "Dara", "Grade": "FAQ", "Modal_Price": 2000.0, "Min_Price": 1900.0, "Max_Price": 2100.0},
            {"Arrival_Date": "2024-01-02", "District": "Ghaziabad", "Market": "Ghaziabad", "Commodity": "Wheat", "Variety": "Dara", "Grade": "FAQ", "Modal_Price": 2500.0, "Min_Price": 2400.0, "Max_Price": 2600.0},
            # Normal single quote on 2024-01-03
            {"Arrival_Date": "2024-01-03", "District": "Ghaziabad", "Market": "Ghaziabad", "Commodity": "Wheat", "Variety": "Dara", "Grade": "FAQ", "Modal_Price": 2050.0, "Min_Price": 1950.0, "Max_Price": 2150.0},
        ]
        df_test = pd.DataFrame(rows)

        res = reconstruct_cutoff_fold(
            df_raw=df_test,
            alias_df=alias_df,
            train_end="2024-01-05"
        )
        # Total in: 5 rows
        # Conflicting: 2 rows (both on 2024-01-02 quarantined)
        # Remaining: 3 rows (2 from 2024-01-01, 1 from 2024-01-03)
        # Duplicates deduplicated: 1 row dropped from 2024-01-01
        # Final clean: 2 rows
        assert res["conflicts_quarantined"] == 2
        assert res["duplicates_deduplicated"] == 1
        assert res["total_training_observations"] == 2

    def test_verify_future_mutation_invariance(self, alias_df):
        """Mutations dated strictly after cutoff do not alter training identities, counts, prices, or hashes."""
        dates = pd.date_range("2024-01-01", periods=100, freq="D").strftime("%Y-%m-%d")
        df_raw = pd.DataFrame({
            "Arrival_Date": dates,
            "District": "Ghaziabad", "Market": "Ghaziabad", "Commodity": "Wheat",
            "Variety": "Dara", "Grade": "FAQ", "Modal_Price": 2100.0
        })

        is_invariant = verify_future_mutation_invariance(
            df_raw=df_raw,
            alias_df=alias_df,
            cutoff_date="2024-02-15"
        )
        assert is_invariant is True

    def test_unavailable_evidence_withholding(self):
        """Candidate alias with evidence_known_date in the future is withheld under verified mode."""
        alias_df = pd.DataFrame([{
            "district": "Ghaziabad", "market_raw": "OldMarket", "market_canonical": "CanonicalMarket",
            "rule": "Rule A", "evidence": "migration", "first_date": "2021-09-01", "last_date": "2025-06-01",
            "overlap_days": 0, "price_agreement": None, "status": "ACCEPTED",
            "evidence_known_date": "2025-06-01",  # Known on 2025-06-01
            "assumed_known_date": "2025-01-01",
            "knowledge_provenance": "EMPIRICAL_DISCOVERY"
        }])

        df_raw = pd.DataFrame([{
            "Arrival_Date": "2025-02-01", "District": "Ghaziabad", "Market": "OldMarket",
            "Commodity": "Wheat", "Variety": "Dara", "Grade": "FAQ", "Modal_Price": 2100.0
        }])

        # At cutoff 2025-03-31:
        # 1. Under 'verified' mode: evidence_known_date (2025-06-01) > cutoff -> withholds alias!
        res_ver = reconstruct_cutoff_fold(
            df_raw=df_raw,
            alias_df=alias_df,
            train_end="2025-03-31",
            evidence_mode="verified"
        )
        assert res_ver["active_aliases_count"] == 0

        # 2. Under 'assumed' mode: assumed_known_date (2025-01-01) <= cutoff -> active!
        res_assumed = reconstruct_cutoff_fold(
            df_raw=df_raw,
            alias_df=alias_df,
            train_end="2025-03-31",
            evidence_mode="assumed"
        )
        assert res_assumed["active_aliases_count"] == 1

        # 3. Under 'retrospective' mode: always active!
        res_retro = reconstruct_cutoff_fold(
            df_raw=df_raw,
            alias_df=alias_df,
            train_end="2025-03-31",
            evidence_mode="retrospective"
        )
        assert res_retro["active_aliases_count"] == 1

        # 4. At cutoff 2025-06-30 under 'verified' mode: evidence_known_date <= cutoff -> active!
        res_ver_late = reconstruct_cutoff_fold(
            df_raw=df_raw,
            alias_df=alias_df,
            train_end="2025-06-30",
            evidence_mode="verified"
        )
        assert res_ver_late["active_aliases_count"] == 1

    def test_all_four_fold_boundaries(self, alias_df):
        """Evaluates causal reconstruction across all four standard benchmark folds F1, F2, F3, F4."""
        # Daily series from 2024-01-01 through 2026-09-30 (1004 days)
        dates = pd.date_range("2024-01-01", "2026-09-30", freq="D").strftime("%Y-%m-%d")
        df_multi_year = pd.DataFrame({
            "Arrival_Date": dates,
            "District": "Ghaziabad", "Market": "Ghaziabad", "Commodity": "Wheat",
            "Variety": "Dara", "Grade": "FAQ", "Modal_Price": 2200.0
        })

        from src.identity_comparison import DEFAULT_FOLD_BOUNDS
        res = evaluate_causal_train_eligibility_sensitivity(
            df_raw=df_multi_year,
            alias_df=alias_df,
            cutoffs=DEFAULT_FOLD_BOUNDS,
            min_train_records=60,
            min_coverage=0.30
        )

        for fold in ["F1", "F2", "F3", "F4"]:
            assert fold in res["cutoffs"]
            f_res = res["cutoffs"][fold]
            assert f_res["tier_a_series_count"] == 1
            assert f_res["subset_invariant_holds"] is True
            assert f_res["test_eval"]["test_window_available"] is True
            assert f_res["test_eval"]["n_origins_total"] > 0
            assert f_res["test_eval"]["n_origins_serving_eligible"] > 0
            assert f_res["test_eval"]["n_origins_target_available"] > 0

    def test_workbook_title_row_and_schema(self, tmp_path):
        """Verifies ingestion of Agmarknet Excel file with title row and raw date/unit schema."""
        import openpyxl
        from src.ingest_agmarknet_arrivals import load_arrivals_file

        wb = openpyxl.Workbook()
        ws = wb.active
        # Row 1: Title row
        ws.append(["Daily Price Arrival Report-07-11-2025 to 06-11-2026 for Uttar Pradesh"] + [""] * 13)
        # Row 2: Standard header row
        ws.append([
            "State/UT", "District", "Market", "Commodity Group", "Commodity", "Variety", "Grade",
            "Min Price", "Max Price", "Modal Price", "Price Unit", "Arrival Quantity", "Arrival Unit", "Arrival Date"
        ])
        # Row 3: Data row
        ws.append([
            "Uttar Pradesh", "Ghaziabad", "Ghaziabad", "Foodgrains", "Wheat", "Dara", "FAQ",
            2100, 2300, 2200, "Rs./Quintal", 50, "Metric Tonnes", "15/01/2026"
        ])
        xlsx_path = tmp_path / "test_agmarknet_report.xlsx"
        wb.save(xlsx_path)

        df_loaded = load_arrivals_file(str(xlsx_path))
        assert len(df_loaded) == 1
        assert df_loaded["District"].iloc[0] == "Ghaziabad"
        assert df_loaded["Market"].iloc[0] == "Ghaziabad"
        assert df_loaded["Commodity"].iloc[0] == "Wheat"
        assert df_loaded["Price_Unit"].iloc[0] == "Rs./Quintal"
        assert df_loaded["Arrival_Date"].iloc[0] == "2026-01-15"
        assert float(df_loaded["Modal_Price"].iloc[0]) == 2200.0


