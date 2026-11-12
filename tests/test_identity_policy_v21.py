"""
Unit tests for Market Identity Candidate Policy v2.1.

Tests conservative gap/overlap rules, defensive validation (inverted dates,
missing fields, duplicate conflicting mappings, cycles), and causal as-of
information availability cutoff filtering.
"""

import pandas as pd
import pytest
from pathlib import Path

from src.market_identity import (
    evaluate_alias_evidence_v21,
    validate_alias_table,
    build_causal_alias_mapping,
    apply_market_canonicalization_v21,
    load_market_aliases,
    MARKET_ALIAS_COLUMNS,
    CANDIDATE_ALIAS_COLUMNS_V21
)


class TestCandidateRuleAAndB:
    """Tests for evaluate_alias_evidence_v21 bounded migration and concordance."""

    def test_candidate_rule_a_bounded_gap_accepted(self):
        """Contiguous handover (gap <= 14d, overlap <= 7d) is accepted under Candidate Rule A."""
        is_accepted, evidence = evaluate_alias_evidence_v21(
            district_1="Ghaziabad",
            name_1="Ghaziabad",
            first_date_1="2021-09-01",
            last_date_1="2025-11-04",
            district_2="Ghaziabad",
            name_2="Ghaziabad APMC",
            first_date_2="2025-11-01",
            last_date_2="2026-09-30"
        )
        assert is_accepted is True
        assert evidence["status"] == "ACCEPTED"
        assert "Candidate Rule A" in evidence["rule"]
        assert evidence["overlap_days"] <= 7

    def test_candidate_rule_a_unbounded_hiatus_rejected(self):
        """Unbounded gap (e.g. Purwa 205-day hiatus) without overlap is rejected under Candidate Rule A."""
        is_accepted, evidence = evaluate_alias_evidence_v21(
            district_1="Unnao",
            name_1="Purwa",
            first_date_1="2021-09-01",
            last_date_1="2025-07-31",
            district_2="Unnao",
            name_2="Purwa APMC",
            first_date_2="2026-02-21",
            last_date_2="2026-09-30"
        )
        assert is_accepted is False
        assert evidence["status"] == "UNMAPPED/REVIEW"
        assert "Candidate Rule A Failed" in evidence["rule"]
        assert "205" in evidence["evidence"]

    def test_candidate_rule_b_insufficient_sample_size_rejected(self):
        """Extended overlap with fewer than min_concordance_keys (e.g. 2 < 5) is rejected."""
        overlap_df = pd.DataFrame({
            "price_1": [2000, 2050],
            "price_2": [2000, 2050]
        })
        is_accepted, evidence = evaluate_alias_evidence_v21(
            district_1="Jhansi",
            name_1="Moth",
            first_date_1="2021-09-01",
            last_date_1="2025-11-30",
            district_2="Jhansi",
            name_2="Moth APMC",
            first_date_2="2025-11-10",
            last_date_2="2026-09-30",
            overlapping_records_df=overlap_df,
            max_migration_overlap_days=7,
            min_concordance_keys=5
        )
        assert is_accepted is False
        assert evidence["status"] == "UNMAPPED/REVIEW"
        assert "insufficient overlapping keys" in evidence["rule"]

    def test_candidate_rule_b_sufficient_concordance_accepted(self):
        """Extended overlap with >= min_concordance_keys and >= 95% match is accepted."""
        overlap_df = pd.DataFrame({
            "price_1": [2000] * 20,
            "price_2": [2000] * 20
        })
        is_accepted, evidence = evaluate_alias_evidence_v21(
            district_1="Jhansi",
            name_1="Jhansi (Grain)",
            first_date_1="2024-05-25",
            last_date_1="2026-01-14",
            district_2="Jhansi",
            name_2="Jhansi Grain APMC",
            first_date_2="2026-01-01",
            last_date_2="2026-01-14",
            overlapping_records_df=overlap_df,
            max_migration_overlap_days=7,
            min_concordance_keys=5,
            min_price_agreement=0.95
        )
        assert is_accepted is True
        assert evidence["status"] == "ACCEPTED"
        assert "Candidate Rule B" in evidence["rule"]
        assert evidence["price_agreement"] == 1.0

    def test_candidate_rule_b_price_divergence_rejected(self):
        """Extended overlap with price agreement < 95% is rejected."""
        overlap_df = pd.DataFrame({
            "price_1": [1000] * 10,
            "price_2": [1000] * 8 + [1200, 1300]  # 80% < 95%
        })
        is_accepted, evidence = evaluate_alias_evidence_v21(
            district_1="Kanpur",
            name_1="Baripaal APMC",
            first_date_1="2025-11-01",
            last_date_1="2026-04-26",
            district_2="Kanpur",
            name_2="Baripaal APMC",
            first_date_2="2026-03-01",
            last_date_2="2026-09-30",
            overlapping_records_df=overlap_df,
            max_migration_overlap_days=7
        )
        assert is_accepted is False
        assert evidence["status"] == "UNMAPPED/REVIEW"
        assert "price agreement" in evidence["rule"]


class TestDefensiveValidation:
    """Tests for rejecting malformed inputs, missing fields, duplicate conflicts, and cycles."""

    def test_inverted_date_ranges_rejected(self):
        """first_date > last_date returns validation failure."""
        is_accepted, evidence = evaluate_alias_evidence_v21(
            district_1="Unnao",
            name_1="Purwa",
            first_date_1="2025-12-01",
            last_date_1="2025-01-01",  # Inverted!
            district_2="Unnao",
            name_2="Purwa APMC",
            first_date_2="2026-01-01",
            last_date_2="2026-09-30"
        )
        assert is_accepted is False
        assert "inverted date range" in evidence["rule"].lower()

    def test_missing_identity_fields_rejected(self):
        """Empty or null district or market names are rejected immediately."""
        is_accepted, evidence = evaluate_alias_evidence_v21(
            district_1="",
            name_1="Ghaziabad",
            first_date_1="2021-09-01",
            last_date_1="2025-11-04",
            district_2="Ghaziabad",
            name_2="Ghaziabad APMC",
            first_date_2="2025-11-01",
            last_date_2="2026-09-30"
        )
        assert is_accepted is False
        assert "missing required identity field" in evidence["rule"].lower()

    def test_validate_alias_table_detects_duplicate_conflicting_mappings(self):
        """The same (district, market_raw) cannot map to two distinct canonical names with ACCEPTED status."""
        bad_df = pd.DataFrame([
            {
                "district": "Kanpur",
                "market_raw": "Baripaal APMC",
                "market_canonical": "Baripaal APMC",
                "rule": "Identity",
                "evidence": "none",
                "first_date": "2026-03-01",
                "last_date": "2026-09-30",
                "overlap_days": 0,
                "price_agreement": None,
                "status": "ACCEPTED"
            },
            {
                "district": "Kanpur",
                "market_raw": "Baripaal APMC",
                "market_canonical": "Varipaal",  # Conflicting second target!
                "rule": "Rule B",
                "evidence": "95%",
                "first_date": "2026-03-01",
                "last_date": "2026-09-30",
                "overlap_days": 52,
                "price_agreement": 0.9567,
                "status": "ACCEPTED"
            }
        ])
        is_valid, issues = validate_alias_table(bad_df)
        assert is_valid is False
        assert any("conflicting duplicate mapping" in s.lower() for s in issues)

    def test_validate_alias_table_detects_cycles(self):
        """Cycles like A -> B and B -> A are detected and flagged."""
        cycle_df = pd.DataFrame([
            {
                "district": "Lucknow",
                "market_raw": "Market_A",
                "market_canonical": "Market_B",
                "rule": "Rule A",
                "evidence": "none",
                "first_date": "2021-09-01",
                "last_date": "2025-11-04",
                "overlap_days": 0,
                "price_agreement": None,
                "status": "ACCEPTED"
            },
            {
                "district": "Lucknow",
                "market_raw": "Market_B",
                "market_canonical": "Market_A",
                "rule": "Rule A",
                "evidence": "none",
                "first_date": "2025-11-01",
                "last_date": "2026-09-30",
                "overlap_days": 0,
                "price_agreement": None,
                "status": "ACCEPTED"
            }
        ])
        is_valid, issues = validate_alias_table(cycle_df)
        assert is_valid is False
        assert any("cycle detected" in s.lower() for s in issues)


class TestCausalInformationCutoff:
    """Tests for causal as-of filtering preventing lookahead bias."""

    @pytest.fixture
    def candidate_table_fixture(self):
        return pd.DataFrame([
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
                "evidence_known_date": "2021-09-01"
            },
            {
                "district": "Ghaziabad",
                "market_raw": "Ghaziabad APMC",
                "market_canonical": "Ghaziabad",
                "rule": "Candidate Rule A",
                "evidence": "handover",
                "first_date": "2025-11-01",
                "last_date": "2026-09-30",
                "overlap_days": 4,
                "price_agreement": 1.0,
                "status": "ACCEPTED",
                "evidence_known_date": "2025-11-05"
            }
        ])

    def test_causal_as_of_withholds_future_alias(self, candidate_table_fixture):
        """As of 2025-06-30 (Fold F2 cutoff), evidence known in Nov 2025 is not applied."""
        mapping_f2 = build_causal_alias_mapping(candidate_table_fixture, as_of_date="2025-06-30")
        assert ("ghaziabad", "ghaziabad") in mapping_f2
        assert ("ghaziabad", "ghaziabad apmc") not in mapping_f2

    def test_causal_as_of_includes_past_alias(self, candidate_table_fixture):
        """As of 2025-12-18 (Fold F3 cutoff), evidence known on 2025-11-05 is applied."""
        mapping_f3 = build_causal_alias_mapping(candidate_table_fixture, as_of_date="2025-12-18")
        assert ("ghaziabad", "ghaziabad") in mapping_f3
        assert ("ghaziabad", "ghaziabad apmc") in mapping_f3
        assert mapping_f3[("ghaziabad", "ghaziabad apmc")] == "Ghaziabad"

    def test_candidate_v21_reference_file_passes_validation(self):
        """Verified that data/reference/market_alias_candidates_v21.csv passes validate_alias_table."""
        cand_path = Path("data/reference/market_alias_candidates_v21.csv")
        assert cand_path.exists()
        cand_df = pd.read_csv(cand_path)
        is_valid, issues = validate_alias_table(cand_df)
        assert is_valid is True, f"Validation issues found: {issues}"
