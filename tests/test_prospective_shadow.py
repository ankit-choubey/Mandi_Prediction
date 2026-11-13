"""
Unit tests for Step 13 Prospective Shadow Validation Registry and CLI.
Validates protocol invariants, idempotency, hash-chaining, freshness gating,
tie-breaking logic, and scorecard calculation.
"""

from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import pytest
import tempfile

from src.prospective_shadow import (
    ProspectiveShadowRegistry,
    ShadowRecord,
    compute_file_sha256,
    compute_dict_hash,
)


@pytest.fixture
def temp_registry_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_snapshot_file(temp_registry_dir):
    p = temp_registry_dir / "sample_snapshot.json"
    data = {
        "index_version": "1.0.0",
        "generated_at_utc": "2026-11-12T10:00:00Z",
        "composite_source_sha256": "3d3bc047440186eed49a8764eb28387a99e7293cdc9b62f1d30290b855fedb11",
        "series": {
            "lucknow_banthara_wheat": {
                "series_id": "up_lucknow_banthara_wheat_dara_faq",
                "district": "Lucknow",
                "market_canonical": "Banthara",
                "commodity": "Wheat",
                "variety": "Dara",
                "grade": "FAQ",
                "latest_observation_date": "2026-11-12",
                "modal_price": 2721.0,
                "min_price": 2670.0,
                "max_price": 2750.0,
                "units": "INR/quintal",
                "price_display_permitted": True,
            },
            "kanpur_baripaal_paddy": {
                "series_id": "up_kanpur_baripaal_paddy_common_faq",
                "district": "Kanpur",
                "market_canonical": "Baripaal",
                "commodity": "Paddy(Common)",
                "variety": "Common",
                "grade": "FAQ",
                "latest_observation_date": "2026-11-12",
                "modal_price": 2100.0,
                "units": "INR/quintal",
                "price_display_permitted": False,
            },
            "out_of_scope_crop": {
                "series_id": "up_lucknow_fish",
                "district": "Lucknow",
                "market_canonical": "Lucknow",
                "commodity": "Fish",
                "variety": "Fresh",
                "grade": "FAQ",
                "latest_observation_date": "2026-11-12",
                "modal_price": 15000.0,
                "price_display_permitted": True,
            },
        },
    }
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return p


class TestProspectiveShadowRegistry:

    def test_init_registry_creates_files_and_preserves_on_second_init(self, temp_registry_dir):
        reg = ProspectiveShadowRegistry(registry_dir=temp_registry_dir)
        res1 = reg.init_registry()
        assert res1["status"] == "INITIALIZED"
        assert (temp_registry_dir / "registry_meta.json").exists()
        assert (temp_registry_dir / "forward_forecast_log.jsonl").exists()

        # Second init without force preserves existing
        res2 = reg.init_registry(force=False)
        assert res2["status"] == "EXISTING_REGISTRY_PRESERVED"
        assert res2["config_hash"] == res1["config_hash"]

    def test_validate_snapshot_bounds_and_structure(self, temp_registry_dir, sample_snapshot_file):
        reg = ProspectiveShadowRegistry(registry_dir=temp_registry_dir)
        val = reg.validate_snapshot(sample_snapshot_file)
        assert val["total_series_rows"] == 3
        assert val["valid_series_count"] == 3
        assert val["accepted_eligible_count"] == 2
        assert val["review_withheld_count"] == 1
        assert "Lucknow" in val["districts_covered"]
        assert "Wheat" in val["commodities_covered"]

    def test_freshness_policy_fresh_vs_stale(self, temp_registry_dir, sample_snapshot_file):
        reg = ProspectiveShadowRegistry(registry_dir=temp_registry_dir)

        # Case 1: Fresh observation (same day, delta=0)
        res_fresh = reg.issue_shadow_records(
            sample_snapshot_file,
            dry_run=True,
            simulated_current_date_ist=date(2026, 11, 12),
        )
        assert res_fresh["issued_point_forecasts"] == 1
        assert res_fresh["abstained_stale"] == 0
        assert res_fresh["abstained_review"] == 1
        assert res_fresh["abstained_out_of_scope"] == 1

        # Case 2: Stale observation (3 days old, delta=3)
        res_stale = reg.issue_shadow_records(
            sample_snapshot_file,
            dry_run=True,
            simulated_current_date_ist=date(2026, 11, 15),
        )
        assert res_stale["issued_point_forecasts"] == 0
        assert res_stale["abstained_stale"] == 1
        assert res_stale["abstained_review"] == 1

    def test_issuance_idempotency_and_hash_chaining(self, temp_registry_dir, sample_snapshot_file):
        reg = ProspectiveShadowRegistry(registry_dir=temp_registry_dir)

        # First run writes records
        res1 = reg.issue_shadow_records(
            sample_snapshot_file,
            dry_run=False,
            simulated_current_date_ist=date(2026, 11, 12),
        )
        assert res1["status"] == "SUCCESS_ISSUED"
        assert res1["total_new_appended"] == 2

        # Second run skips identical duplicates
        res2 = reg.issue_shadow_records(
            sample_snapshot_file,
            dry_run=False,
            simulated_current_date_ist=date(2026, 11, 12),
        )
        assert res2["skipped_existing_duplicates"] == 2
        assert res2["total_new_appended"] == 0

        # Verify hash chaining
        log_file = temp_registry_dir / "forward_forecast_log.jsonl"
        records = []
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                records.append(json.loads(line))

        assert len(records) == 2
        assert records[0]["prev_record_hash"] == "0" * 64
        assert records[1]["prev_record_hash"] == records[0]["record_hash"]
        assert len(records[0]["record_hash"]) == 64
        assert len(records[1]["record_hash"]) == 64

    def test_outcome_matching_window_and_tie_breaks(self, temp_registry_dir, sample_snapshot_file):
        reg = ProspectiveShadowRegistry(registry_dir=temp_registry_dir)
        # Issue forecast with origin 2026-11-12 -> target expected 2026-11-19 (window 11-18 to 11-20)
        reg.issue_shadow_records(
            sample_snapshot_file,
            dry_run=False,
            simulated_current_date_ist=date(2026, 11, 12),
        )

        outcomes_file = temp_registry_dir / "outcomes.json"

        # Create outcomes containing Day 6 (11-18) and Day 7 (11-19)
        outcomes_data = {
            "series": [
                {
                    "series_id": "up_lucknow_banthara_wheat_dara_faq",
                    "observation_date": "2026-11-18",
                    "modal_price": 2750.0,
                },
                {
                    "series_id": "up_lucknow_banthara_wheat_dara_faq",
                    "observation_date": "2026-11-19",
                    "modal_price": 2780.0,
                },
            ]
        }
        with open(outcomes_file, "w", encoding="utf-8") as f:
            json.dump(outcomes_data, f)

        reg.import_outcomes(outcomes_file)

        # Before window closes (e.g. simulated date 2026-11-19): provisional pending close
        m_prov = reg.match_outcomes(dry_run=True, simulated_current_date_ist=date(2026, 11, 19))
        assert m_prov["provisional_matches"] == 1
        assert m_prov["matured_matches"] == 0

        # After window closes (simulated date 2026-11-22 > 11-20): matured match
        m_mat = reg.match_outcomes(dry_run=False, simulated_current_date_ist=date(2026, 11, 22))
        assert m_mat["matured_matches"] == 1

        # Check matched record picked exact Day 7 (2780.0) over Day 6 (2750.0)
        matches_log = temp_registry_dir / "forward_matches.jsonl"
        with open(matches_log, "r", encoding="utf-8") as f:
            match = json.loads(f.readline())

        assert match["matched_observation_date"] == "2026-11-19"
        assert match["observed_modal_price"] == 2780.0
        assert match["point_forecast"] == 2721.0
        assert match["absolute_error"] == 59.0
        assert match["match_status"] == "MATURED_MATCH"

    def test_scorecard_empty_vs_evaluated(self, temp_registry_dir, sample_snapshot_file):
        reg = ProspectiveShadowRegistry(registry_dir=temp_registry_dir)

        # Empty registry scorecard
        sc_empty = reg.generate_scorecard()
        assert sc_empty["scorecard_status"] == "EMPIRICAL_PENDING"
        assert sc_empty["matured_matches_count"] == 0
        assert sc_empty["metrics"]["primary_mae_inr"] is None
        assert sc_empty["advisory_status"] == "BLOCKED"

        # Issue and match a single outcome
        reg.issue_shadow_records(sample_snapshot_file, dry_run=False, simulated_current_date_ist=date(2026, 11, 12))
        outcomes_file = temp_registry_dir / "outcomes.json"
        with open(outcomes_file, "w", encoding="utf-8") as f:
            json.dump({
                "series": [{
                    "series_id": "up_lucknow_banthara_wheat_dara_faq",
                    "observation_date": "2026-11-19",
                    "modal_price": 2750.0,
                }]
            }, f)
        reg.import_outcomes(outcomes_file)
        reg.match_outcomes(dry_run=False, simulated_current_date_ist=date(2026, 11, 22))

        sc_eval = reg.generate_scorecard()
        assert sc_eval["scorecard_status"] == "ENGINEERING_COMPLETE_EMPIRICAL_EVALUATED"
        assert sc_eval["matured_matches_count"] == 1
        assert sc_eval["is_low_n"] is True
        assert sc_eval["metrics"]["primary_mae_inr"] == 29.0
        assert sc_eval["metrics"]["rmse_inr"] == 29.0
        assert sc_eval["metrics"]["mean_bias_inr"] == 29.0
        assert sc_eval["advisory_status"] == "BLOCKED"
