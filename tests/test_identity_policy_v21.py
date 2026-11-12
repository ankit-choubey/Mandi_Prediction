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

    def test_validate_alias_table_detects_nonterminal_chains(self):
        """Nonterminal mapping chains A -> B and B -> C are detected and rejected."""
        chain_df = pd.DataFrame([
            {
                "district": "Jhansi",
                "market_raw": "Jhansi Grain APMC",
                "market_canonical": "Jhansi (Grain) APMC",
                "rule": "Rule B",
                "evidence": "concordance",
                "first_date": "2026-01-01",
                "last_date": "2026-01-14",
                "overlap_days": 10,
                "price_agreement": 1.0,
                "status": "ACCEPTED"
            },
            {
                "district": "Jhansi",
                "market_raw": "Jhansi (Grain) APMC",
                "market_canonical": "Jhansi (Grain)",
                "rule": "Rule A",
                "evidence": "migration",
                "first_date": "2025-11-02",
                "last_date": "2026-01-14",
                "overlap_days": 2,
                "price_agreement": 1.0,
                "status": "ACCEPTED"
            }
        ])
        is_valid, issues = validate_alias_table(chain_df)
        assert is_valid is False
        assert any("nonterminal mapping chain" in s.lower() for s in issues)

    def test_validate_alias_table_rejects_malformed_and_nat_dates(self):
        """Malformed date strings and NaT fail validation closed."""
        malformed_df = pd.DataFrame([
            {
                "district": "Ghaziabad",
                "market_raw": "Ghaziabad APMC",
                "market_canonical": "Ghaziabad",
                "rule": "Rule A",
                "evidence": "test",
                "first_date": "2025-11-01",
                "last_date": "not-a-date",  # Malformed date string!
                "overlap_days": 4,
                "price_agreement": 1.0,
                "status": "ACCEPTED"
            }
        ])
        is_valid, issues = validate_alias_table(malformed_df)
        assert is_valid is False
        assert any("malformed" in s.lower() or "unparseable" in s.lower() for s in issues)

    def test_validate_alias_table_rejects_null_and_string_null_identities(self):
        """Rejects pandas NaN, None, empty strings, and string 'nan'/'none'/'null'."""
        for bad_val in [None, float("nan"), "", "nan", "NONE", "null"]:
            bad_id_df = pd.DataFrame([
                {
                    "district": bad_val,
                    "market_raw": "Ghaziabad APMC",
                    "market_canonical": "Ghaziabad",
                    "rule": "Rule A",
                    "evidence": "test",
                    "first_date": "2025-11-01",
                    "last_date": "2026-09-30",
                    "overlap_days": 4,
                    "price_agreement": 1.0,
                    "status": "ACCEPTED"
                }
            ])
            is_valid, issues = validate_alias_table(bad_id_df)
            assert is_valid is False, f"Expected failure for bad_val={repr(bad_val)}"
            assert any("null or empty" in s.lower() for s in issues)

    def test_validate_alias_table_rejects_unknown_status(self):
        """Statuses outside {'ACCEPTED', 'UNMAPPED/REVIEW', 'REJECTED'} fail validation."""
        bad_status_df = pd.DataFrame([
            {
                "district": "Ghaziabad",
                "market_raw": "Ghaziabad APMC",
                "market_canonical": "Ghaziabad",
                "rule": "Rule A",
                "evidence": "test",
                "first_date": "2025-11-01",
                "last_date": "2026-09-30",
                "overlap_days": 4,
                "price_agreement": 1.0,
                "status": "PENDING_APPROVAL"  # Unknown status!
            }
        ])
        is_valid, issues = validate_alias_table(bad_status_df)
        assert is_valid is False
        assert any("invalid status" in s.lower() for s in issues)

    def test_rule_a_rejects_missing_or_nonfinite_prices(self):
        """Overlapping records with missing price columns or nonfinite prices fail Rule A."""
        overlap_no_price = pd.DataFrame({"dummy": [1, 2, 3]})
        is_acc, ev = evaluate_alias_evidence_v21(
            district_1="Ghaziabad",
            name_1="Ghaziabad",
            first_date_1="2021-09-01",
            last_date_1="2025-11-04",
            district_2="Ghaziabad",
            name_2="Ghaziabad APMC",
            first_date_2="2025-11-01",
            last_date_2="2026-09-30",
            overlapping_records_df=overlap_no_price
        )
        assert is_acc is False
        assert "missing required price columns" in ev["rule"].lower()

        overlap_nan_price = pd.DataFrame({"price_1": [2000, float("nan")], "price_2": [2000, 2000]})
        is_acc2, ev2 = evaluate_alias_evidence_v21(
            district_1="Ghaziabad",
            name_1="Ghaziabad",
            first_date_1="2021-09-01",
            last_date_1="2025-11-04",
            district_2="Ghaziabad",
            name_2="Ghaziabad APMC",
            first_date_2="2025-11-01",
            last_date_2="2026-09-30",
            overlapping_records_df=overlap_nan_price
        )
        assert is_acc2 is False
        assert "nonfinite" in ev2["rule"].lower()

    def test_rule_b_deduplicates_unique_natural_keys(self):
        """Rule B deduplicates joined many-to-many records by natural keys."""
        # 20 rows, but all have the exact same natural key
        inflated_df = pd.DataFrame({
            "Arrival_Date": ["2026-01-05"] * 20,
            "Commodity": ["Wheat"] * 20,
            "Variety": ["Dara"] * 20,
            "Grade": ["FAQ"] * 20,
            "price_1": [2200.0] * 20,
            "price_2": [2200.0] * 20
        })
        is_acc, ev = evaluate_alias_evidence_v21(
            district_1="Jhansi",
            name_1="Jhansi (Grain)",
            first_date_1="2024-05-25",
            last_date_1="2026-01-14",
            district_2="Jhansi",
            name_2="Jhansi Grain APMC",
            first_date_2="2026-01-01",
            last_date_2="2026-01-14",
            overlapping_records_df=inflated_df,
            max_migration_overlap_days=7,
            min_concordance_keys=5
        )
        # Deduplicated key count is 1 < 5, so it must fail!
        assert is_acc is False
        assert "insufficient overlapping keys" in ev["rule"].lower()


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
                "evidence_known_date": "2021-09-01",
                "assumed_known_date": "2021-09-01",
                "knowledge_provenance": "STRUCTURAL_IDENTITY_ANCHOR"
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
                "evidence_known_date": "",
                "assumed_known_date": "2025-11-05",
                "knowledge_provenance": "ASSUMED_OBSERVATION_HANDOVER"
            }
        ])

    def test_causal_as_of_withholds_when_evidence_known_date_missing_in_verified_mode(self, candidate_table_fixture):
        """In verified mode, missing evidence_known_date withholds merge (does NOT fall back to first_date)."""
        mapping_f3 = build_causal_alias_mapping(
            candidate_table_fixture, as_of_date="2025-12-18", evidence_mode="verified"
        )
        assert ("ghaziabad", "ghaziabad") in mapping_f3
        # Fail-closed: Ghaziabad APMC has no dated publication receipt, so it is withheld!
        assert ("ghaziabad", "ghaziabad apmc") not in mapping_f3

    def test_causal_as_of_assumed_mode_uses_assumed_known_date(self, candidate_table_fixture):
        """In assumed mode, assumed_known_date (2025-11-05) is evaluated against cutoff."""
        # F2 (2025-06-30): Before assumed handover date -> withheld
        mapping_f2 = build_causal_alias_mapping(
            candidate_table_fixture, as_of_date="2025-06-30", evidence_mode="assumed"
        )
        assert ("ghaziabad", "ghaziabad apmc") not in mapping_f2

        # F3 (2025-12-18): After assumed handover date -> applied
        mapping_f3 = build_causal_alias_mapping(
            candidate_table_fixture, as_of_date="2025-12-18", evidence_mode="assumed"
        )
        assert ("ghaziabad", "ghaziabad apmc") in mapping_f3
        assert mapping_f3[("ghaziabad", "ghaziabad apmc")] == "Ghaziabad"

    def test_build_causal_alias_mapping_raises_value_error_on_invalid_table(self):
        """build_causal_alias_mapping raises ValueError if table fails validation."""
        bad_df = pd.DataFrame([
            {
                "district": "Ghaziabad",
                "market_raw": "Ghaziabad APMC",
                "market_canonical": "Ghaziabad",
                "rule": "Rule A",
                "evidence": "test",
                "first_date": "2025-11-01",
                "last_date": "not-a-date",  # Invalid!
                "overlap_days": 4,
                "price_agreement": 1.0,
                "status": "ACCEPTED"
            }
        ])
        with pytest.raises(ValueError, match="failed defensive validation"):
            build_causal_alias_mapping(bad_df, as_of_date="2025-12-18")

    def test_candidate_v21_reference_file_passes_validation(self):
        """Verified that data/reference/market_alias_candidates_v21.csv passes validate_alias_table."""
        cand_path = Path("data/reference/market_alias_candidates_v21.csv")
        assert cand_path.exists()
        cand_df = pd.read_csv(cand_path)
        is_valid, issues = validate_alias_table(cand_df)
        assert is_valid is True, f"Validation issues found: {issues}"


