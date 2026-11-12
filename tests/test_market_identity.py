"""
Unit tests for Market Identity Normalization and Evidence-Based Canonicalization Engine.
"""

import os
import tempfile
import pandas as pd
import pytest

from src.market_identity import (
    normalize_market_name,
    evaluate_alias_evidence,
    load_market_aliases,
    build_alias_mapping,
    apply_market_canonicalization,
    MARKET_ALIAS_COLUMNS
)


class TestMarketIdentityNormalization:
    """Tests for pure function normalize_market_name."""

    def test_basic_normalization(self):
        assert normalize_market_name("Ghaziabad APMC") == "ghaziabad"
        assert normalize_market_name("Ghaziabad") == "ghaziabad"
        assert normalize_market_name("Hapur APMC") == "hapur"
        assert normalize_market_name("Hapur") == "hapur"

    def test_punctuation_and_whitespace_collapse(self):
        assert normalize_market_name("Kanpur(Grain) APMC") == "kanpur grain"
        assert normalize_market_name("Kanpur(Grain)") == "kanpur grain"
        assert normalize_market_name("Kanpur  (Grain)  APMC") == "kanpur grain"
        assert normalize_market_name("Jhansi (Grain) APMC") == "jhansi grain"
        assert normalize_market_name("Jhansi Grain APMC") == "jhansi grain"

    def test_empty_and_non_string_inputs(self):
        assert normalize_market_name("") == ""
        assert normalize_market_name(None) == ""
        assert normalize_market_name("   ") == ""
        assert normalize_market_name(123) == ""


class TestEvidenceRuleEvaluation:
    """Tests for evaluate_alias_evidence satisfying MP-DATA-006 rules."""

    def test_suffix_pair_accepted_rule_a(self):
        """Chronological migration with overlap <= 5 days is accepted under Rule A."""
        is_accepted, evidence = evaluate_alias_evidence(
            district_1="Ghaziabad",
            name_1="Ghaziabad",
            first_date_1="2021-09-01",
            last_date_1="2025-11-04",
            district_2="Ghaziabad",
            name_2="Ghaziabad APMC",
            first_date_2="2025-11-06",
            last_date_2="2026-09-30"
        )
        assert is_accepted is True
        assert evidence["status"] == "ACCEPTED"
        assert "Rule A" in evidence["rule"]
        assert evidence["overlap_days"] <= 5

    def test_different_markets_not_merged(self):
        """Never merge different markets even with similar names or same district."""
        # Different normalized names in same district
        is_accepted, evidence = evaluate_alias_evidence(
            district_1="Ghaziabad",
            name_1="Ghaziabad",
            first_date_1="2021-09-01",
            last_date_1="2026-09-30",
            district_2="Ghaziabad",
            name_2="Noida",
            first_date_2="2021-09-01",
            last_date_2="2026-09-30"
        )
        assert is_accepted is False
        assert evidence["status"] == "UNMAPPED/REVIEW"

        # Phonetical variation not normalized identically (Baripaal vs Varipaal)
        is_accepted, evidence = evaluate_alias_evidence(
            district_1="Kanpur",
            name_1="Baripaal APMC",
            first_date_1="2025-11-20",
            last_date_1="2026-09-30",
            district_2="Kanpur",
            name_2="Varipaal APMC",
            first_date_2="2025-11-20",
            last_date_2="2026-09-30"
        )
        assert is_accepted is False
        assert evidence["status"] == "UNMAPPED/REVIEW"

        # Same market name in different districts
        is_accepted, evidence = evaluate_alias_evidence(
            district_1="Jhansi",
            name_1="Moth",
            first_date_1="2021-09-01",
            last_date_1="2026-09-30",
            district_2="Kanpur",
            name_2="Moth APMC",
            first_date_2="2021-09-01",
            last_date_2="2026-09-30"
        )
        assert is_accepted is False
        assert evidence["status"] == "UNMAPPED/REVIEW"

    def test_overlapping_disagreeing_prices_rejected(self):
        """Overlapping period > 5 days with price agreement < 95% is rejected."""
        overlap_df = pd.DataFrame({
            "commodity": ["Potato", "Wheat", "Onion", "Tomato"],
            "date": ["2025-11-01", "2025-11-02", "2025-11-03", "2025-11-04"],
            "price_1": [1000, 2000, 1500, 1800],
            "price_2": [1000, 2500, 1200, 1900]  # Only 1 of 4 matches (25% < 95%)
        })
        is_accepted, evidence = evaluate_alias_evidence(
            district_1="Lucknow",
            name_1="Lucknow",
            first_date_1="2021-09-01",
            last_date_1="2025-11-30",
            district_2="Lucknow",
            name_2="Lucknow APMC",
            first_date_2="2025-11-01",
            last_date_2="2026-09-30",
            overlapping_records_df=overlap_df
        )
        assert is_accepted is False
        assert evidence["status"] == "UNMAPPED/REVIEW"
        assert evidence["price_agreement"] == 0.25
        assert evidence["overlap_days"] > 5

    def test_overlapping_agreeing_prices_accepted_rule_b(self):
        """Overlapping period > 5 days with price agreement >= 95% is accepted under Rule B."""
        overlap_df = pd.DataFrame({
            "commodity": [f"Crop_{i}" for i in range(20)],
            "price_1": [2000] * 20,
            "price_2": [2000] * 19 + [2010]  # 19/20 = 95.0% >= 95%
        })
        is_accepted, evidence = evaluate_alias_evidence(
            district_1="Unnao",
            name_1="Unnao",
            first_date_1="2021-09-01",
            last_date_1="2025-11-30",
            district_2="Unnao",
            name_2="Unnao APMC",
            first_date_2="2025-11-10",
            last_date_2="2026-09-30",
            overlapping_records_df=overlap_df
        )
        assert is_accepted is True
        assert evidence["status"] == "ACCEPTED"
        assert "Rule B" in evidence["rule"]
        assert evidence["price_agreement"] == 0.95


class TestMarketCanonicalizationApplication:
    """Tests for applying aliases and preserving Market_Raw."""

    @pytest.fixture
    def sample_alias_df(self):
        return pd.DataFrame([
            {
                "district": "Ghaziabad",
                "market_raw": "Ghaziabad APMC",
                "market_canonical": "Ghaziabad",
                "rule": "Rule A",
                "evidence": "overlap <= 5",
                "first_date": "2025-11-06",
                "last_date": "2026-09-30",
                "overlap_days": 0,
                "price_agreement": None,
                "status": "ACCEPTED"
            },
            {
                "district": "Ghaziabad",
                "market_raw": "Hapur APMC",
                "market_canonical": "Hapur",
                "rule": "Rule A",
                "evidence": "overlap <= 5",
                "first_date": "2025-11-06",
                "last_date": "2026-09-30",
                "overlap_days": 0,
                "price_agreement": None,
                "status": "ACCEPTED"
            },
            {
                "district": "Kanpur",
                "market_raw": "Baripaal APMC",
                "market_canonical": "Varipaal",
                "rule": "Review Pending",
                "evidence": "Normalized mismatch",
                "first_date": "2025-11-06",
                "last_date": "2026-09-30",
                "overlap_days": 0,
                "price_agreement": None,
                "status": "UNMAPPED/REVIEW"
            }
        ])

    def test_original_name_preserved_as_market_raw(self, sample_alias_df):
        input_df = pd.DataFrame({
            "District": ["Ghaziabad", "Ghaziabad", "Kanpur"],
            "Market": ["Ghaziabad APMC", "Hapur APMC", "Baripaal APMC"],
            "Commodity": ["Wheat", "Potato", "Tomato"],
            "Modal_Price": [2400, 1100, 1500]
        })
        out_df = apply_market_canonicalization(input_df, sample_alias_df)
        
        # Original preserved in Market_Raw
        assert "Market_Raw" in out_df.columns
        assert out_df["Market_Raw"].tolist() == ["Ghaziabad APMC", "Hapur APMC", "Baripaal APMC"]
        
        # Market column canonicalized for ACCEPTED status
        assert out_df["Market"].tolist() == ["Ghaziabad", "Hapur", "Baripaal APMC"]

    def test_deterministic_and_idempotent(self, sample_alias_df):
        input_df = pd.DataFrame({
            "District": ["Ghaziabad", "Ghaziabad"],
            "Market": ["Ghaziabad APMC", "Ghaziabad"],
            "Commodity": ["Wheat", "Wheat"],
            "Modal_Price": [2400, 2400]
        })
        run_1 = apply_market_canonicalization(input_df, sample_alias_df)
        run_2 = apply_market_canonicalization(input_df, sample_alias_df)
        pd.testing.assert_frame_equal(run_1, run_2)

        # Idempotence: applying on output preserves state
        run_3 = apply_market_canonicalization(run_1, sample_alias_df)
        pd.testing.assert_frame_equal(run_1, run_3)

    def test_alias_loader_validates_schema(self, sample_alias_df):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            sample_alias_df.to_csv(f.name, index=False)
            temp_path = f.name
            
        try:
            loaded = load_market_aliases(temp_path)
            assert len(loaded) == 3
            assert list(loaded.columns) == MARKET_ALIAS_COLUMNS
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

