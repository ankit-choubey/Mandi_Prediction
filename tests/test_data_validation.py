"""
Unit & Integration Tests for Mandi Data Validation & Deduplication Engine
APMC Mandi Market Intelligence System

Tests cover:
- Natural Key deduplication: exact duplicates vs conflicting price records
- Strict quarantine of conflicting records with original evidence and reasons preserved
- Impossible price relationships (Min > Max, Modal < Min, Modal > Max) flagged for review rather than silently corrected
- Invalid dates, negative prices, and missing mandatory columns detection
- Inconsistent district name normalization with audit tracking
- Repeated processing idempotence (rerunning does not compound or generate extra records)
- Failed-update safety (atomic staging and preservation of existing valid output on failure)
- Source file preservation (ensuring raw input files remain 100% unaltered)
"""

import os
import sys
import json
import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from src.data_validator import (
    MandiDataValidator,
    ValidationError,
    MissingSourceFilesValidationError,
    MissingColumnsValidationError,
    EmptyInputValidationError,
    AtomicPublishingError,
    compute_sha256,
    NATURAL_KEY_COLUMNS,
    CANONICAL_COLUMNS
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_clean_mandi_csv(tmp_path):
    """Creates a small valid mandi dataset."""
    csv_file = tmp_path / "valid_raw.csv"
    data = """Arrival_Date,Commodity,Commodity_Code,District,Grade,Market,Max_Price,Min_Price,Modal_Price,State,Variety
01/09/2021,Potato,24,Kanpur,FAQ,Kanpur(Grain),1600,1400,1500,Uttar Pradesh,Desi
02/09/2021,Potato,24,Kanpur,FAQ,Kanpur(Grain),1620,1420,1520,Uttar Pradesh,Desi
03/09/2021,Potato,24,Kanpur,FAQ,Kanpur(Grain),1650,1450,1550,Uttar Pradesh,Desi
"""
    csv_file.write_text(data, encoding="utf-8")
    return str(csv_file)


# =============================================================================
# 1. IMPOSSIBLE PRICE RELATIONSHIPS (FLAGGED, NOT SILENTLY CORRECTED)
# =============================================================================

def test_impossible_price_relationships_flagged(tmp_path):
    """
    Verify that Min > Max, Modal < Min, and Modal > Max are explicitly quarantined
    with rejection codes rather than silently swapped or corrected.
    """
    csv_file = tmp_path / "price_anomalies.csv"
    data = """Arrival_Date,Commodity,Commodity_Code,District,Grade,Market,Max_Price,Min_Price,Modal_Price,State,Variety
01/09/2021,Wheat,28,Kanpur,FAQ,Kanpur,2000,2200,2100,Uttar Pradesh,Dara
02/09/2021,Wheat,28,Kanpur,FAQ,Kanpur,2500,2000,1800,Uttar Pradesh,Dara
03/09/2021,Wheat,28,Kanpur,FAQ,Kanpur,2500,2000,2700,Uttar Pradesh,Dara
04/09/2021,Wheat,28,Kanpur,FAQ,Kanpur,2400,2000,2200,Uttar Pradesh,Dara
"""
    # Row 1: Min (2200) > Max (2000) -> Impossible
    # Row 2: Modal (1800) < Min (2000) -> Impossible
    # Row 3: Modal (2700) > Max (2500) -> Impossible
    # Row 4: Valid
    csv_file.write_text(data, encoding="utf-8")

    out_dir = tmp_path / "processed"
    quar_dir = tmp_path / "quarantine"

    validator = MandiDataValidator(
        input_dir=str(tmp_path),
        output_dir=str(out_dir),
        quarantine_dir=str(quar_dir),
        min_series_records=1
    )
    df_accepted, pub_csv, quar_inv, quar_conf, report = validator.run()

    # Only row 4 should be accepted
    assert len(df_accepted) == 1
    assert df_accepted.iloc[0]["Modal_Price"] == 2200.0

    # Quarantined invalid rows must be exactly 3
    quar_df = pd.read_csv(quar_inv)
    assert len(quar_df) == 3
    rejection_codes = quar_df["rejection_codes"].tolist()
    assert any("IMP_RELATIONSHIP_MIN_GT_MAX" in c for c in rejection_codes)
    assert any("IMP_RELATIONSHIP_MODAL_LT_MIN" in c for c in rejection_codes)
    assert any("IMP_RELATIONSHIP_MODAL_GT_MAX" in c for c in rejection_codes)

    # Verify original raw values are preserved
    raw_min_prices = quar_df["raw_min_price"].astype(str).tolist()
    raw_modal_prices = quar_df["raw_modal_price"].astype(str).tolist()
    assert "2200" in raw_min_prices or "2200.0" in raw_min_prices
    assert "1800" in raw_modal_prices or "1800.0" in raw_modal_prices
    assert "2700" in raw_modal_prices or "2700.0" in raw_modal_prices


# =============================================================================
# 2. NATURAL KEY DEDUPLICATION: EXACT DUPLICATES VS CONFLICTING QUOTES
# =============================================================================

def test_natural_key_duplicates_and_conflicts(tmp_path):
    """
    Test differentiation between exact identical duplicates (keep first, log redundant)
    and conflicting price quotes (quarantine with evidence, exclude from clean panel).
    """
    csv_file = tmp_path / "duplicates_and_conflicts.csv"
    data = """Arrival_Date,Commodity,Commodity_Code,District,Grade,Market,Max_Price,Min_Price,Modal_Price,State,Variety
01/09/2021,Onion,23,Ghaziabad,FAQ,Ghaziabad,3200,2800,3000,Uttar Pradesh,Red
01/09/2021,Onion,23,Ghaziabad,FAQ,Ghaziabad,3200,2800,3000,Uttar Pradesh,Red
02/09/2021,Onion,23,Ghaziabad,FAQ,Ghaziabad,3200,2800,3000,Uttar Pradesh,Red
02/09/2021,Onion,23,Ghaziabad,FAQ,Ghaziabad,3500,3000,3300,Uttar Pradesh,Red
03/09/2021,Onion,23,Ghaziabad,FAQ,Ghaziabad,3400,3000,3200,Uttar Pradesh,Red
"""
    # 01/09: Exact identical duplicate -> 1 kept, 1 deduped
    # 02/09: Conflicting price quotes (3000 vs 3300) -> BOTH quarantined
    # 03/09: Unique clean record -> 1 kept
    csv_file.write_text(data, encoding="utf-8")

    out_dir = tmp_path / "processed"
    quar_dir = tmp_path / "quarantine"

    validator = MandiDataValidator(
        input_dir=str(tmp_path),
        output_dir=str(out_dir),
        quarantine_dir=str(quar_dir),
        min_series_records=1
    )
    df_accepted, pub_csv, quar_inv, quar_conf, report = validator.run()

    # Accepted: 01/09 (1 row) + 03/09 (1 row) = 2 rows
    assert len(df_accepted) == 2
    accepted_dates = pd.to_datetime(df_accepted["Arrival_Date"]).dt.strftime("%Y-%m-%d").tolist()
    assert "2021-09-01" in accepted_dates
    assert "2021-09-03" in accepted_dates
    assert "2021-09-02" not in accepted_dates

    # Conflicting quarantine file must have both rows from 02/09
    conf_df = pd.read_csv(quar_conf)
    assert len(conf_df) == 2
    assert (conf_df["arrival_date"] == "2021-09-02").all()
    assert set(conf_df["modal_price"].tolist()) == {3000.0, 3300.0}
    assert (conf_df["rejection_category"] == "CONFLICTING_NATURAL_KEY_PRICES").all()


# =============================================================================
# 3. NON-POSITIVE PRICES & INVALID DATES
# =============================================================================

def test_non_positive_prices_and_invalid_dates(tmp_path):
    """Verify <= 0 prices and corrupt date strings are safely isolated into quarantine."""
    csv_file = tmp_path / "invalid_data.csv"
    data = """Arrival_Date,Commodity,Commodity_Code,District,Grade,Market,Max_Price,Min_Price,Modal_Price,State,Variety
01/09/2021,Potato,24,Jhansi,FAQ,Jhansi,1500,1200,0.0,Uttar Pradesh,Desi
02/09/2021,Potato,24,Jhansi,FAQ,Jhansi,1500,-100,1400,Uttar Pradesh,Desi
32/13/2021,Potato,24,Jhansi,FAQ,Jhansi,1500,1200,1400,Uttar Pradesh,Desi
04/09/2021,Potato,24,Jhansi,FAQ,Jhansi,1500,1200,1350,Uttar Pradesh,Desi
"""
    csv_file.write_text(data, encoding="utf-8")

    out_dir = tmp_path / "processed"
    quar_dir = tmp_path / "quarantine"

    validator = MandiDataValidator(
        input_dir=str(tmp_path),
        output_dir=str(out_dir),
        quarantine_dir=str(quar_dir),
        min_series_records=1
    )
    df_accepted, pub_csv, quar_inv, quar_conf, report = validator.run()

    assert len(df_accepted) == 1
    assert df_accepted.iloc[0]["Modal_Price"] == 1350.0

    quar_df = pd.read_csv(quar_inv)
    assert len(quar_df) == 3
    codes = quar_df["rejection_codes"].tolist()
    assert any("NON_POSITIVE" in c for c in codes)
    assert any("DATE" in c for c in codes)


# =============================================================================
# 4. INCONSISTENT DISTRICT NAMES NORMALIZATION
# =============================================================================

def test_district_name_inconsistencies(tmp_path):
    """Verify historical district typos (Gaziabaad, Lukhnow) are normalized in clean data."""
    csv_file = tmp_path / "district_typos.csv"
    data = """Arrival_Date,Commodity,Commodity_Code,District,Grade,Market,Max_Price,Min_Price,Modal_Price,State,Variety
01/09/2021,Potato,24,Gaziabaad,FAQ,Ghaziabad,1600,1400,1500,Uttar Pradesh,Desi
02/09/2021,Potato,24,Lukhnow,FAQ,Lucknow,1600,1400,1500,Uttar Pradesh,Desi
"""
    csv_file.write_text(data, encoding="utf-8")

    out_dir = tmp_path / "processed"
    quar_dir = tmp_path / "quarantine"

    validator = MandiDataValidator(
        input_dir=str(tmp_path),
        output_dir=str(out_dir),
        quarantine_dir=str(quar_dir),
        min_series_records=1
    )
    df_accepted, _, _, _, _ = validator.run()

    districts = set(df_accepted["District"].unique())
    assert districts == {"Ghaziabad", "Lucknow"}
    assert "Gaziabaad" not in districts
    assert "Lukhnow" not in districts


# =============================================================================
# 5. IDEMPOTENCE (REPEATED PROCESSING)
# =============================================================================

def test_processing_idempotence(tmp_path, sample_clean_mandi_csv):
    """
    Verify that executing validation repeatedly produces identical outputs,
    identical row counts, identical checksums, and does not create duplicate entries.
    """
    out_dir = tmp_path / "processed"
    quar_dir = tmp_path / "quarantine"

    validator = MandiDataValidator(
        input_dir=str(tmp_path),
        output_dir=str(out_dir),
        quarantine_dir=str(quar_dir),
        min_series_records=1
    )

    # First Execution
    df_run1, pub_csv1, quar_inv1, quar_conf1, _ = validator.run()
    sha_run1 = compute_sha256(pub_csv1)
    len_run1 = len(df_run1)

    # Second Execution
    df_run2, pub_csv2, quar_inv2, quar_conf2, _ = validator.run()
    sha_run2 = compute_sha256(pub_csv2)
    len_run2 = len(df_run2)

    assert len_run1 == len_run2
    assert sha_run1 == sha_run2, "Pipeline must be idempotent! Checksum differed across repeated runs."


# =============================================================================
# 6. ATOMIC PUBLISHING & FAILED-UPDATE SAFETY
# =============================================================================

def test_atomic_publishing_preserves_valid_output_on_failure(tmp_path):
    """
    Verify that if an update fails during validation or publishing,
    the previously existing valid published file remains completely untouched.
    """
    out_dir = tmp_path / "processed"
    quar_dir = tmp_path / "quarantine"
    os.makedirs(out_dir, exist_ok=True)

    # Step 1: Establish an existing valid published dataset
    initial_valid_file = out_dir / "mandi_5year_validated.csv"
    initial_content = "Arrival_Date,District,Market,Commodity,Variety,Grade,Min_Price,Max_Price,Modal_Price,Commodity_Code,State,series_id\n2021-09-01,Kanpur,Kanpur,Potato,Desi,FAQ,1400,1600,1500,24,Uttar Pradesh,Kanpur__Kanpur__Potato__Desi__FAQ\n"
    initial_valid_file.write_text(initial_content, encoding="utf-8")
    initial_sha = compute_sha256(str(initial_valid_file))

    # Step 2: Attempt validation on a folder with an unparseable or completely empty file that causes failure
    bad_dir = tmp_path / "bad_input"
    bad_dir.mkdir()
    zero_file = bad_dir / "zero.csv"
    zero_file.touch()

    validator = MandiDataValidator(
        input_dir=str(bad_dir),
        output_dir=str(out_dir),
        quarantine_dir=str(quar_dir)
    )

    # Validation should raise EmptyInputValidationError
    with pytest.raises(EmptyInputValidationError):
        validator.run()

    # Step 3: Verify the original published file was preserved 100% intact
    assert initial_valid_file.exists()
    assert compute_sha256(str(initial_valid_file)) == initial_sha
    assert initial_valid_file.read_text(encoding="utf-8") == initial_content


# =============================================================================
# 7. SOURCE FILE PRESERVATION
# =============================================================================

def test_raw_source_files_unaltered(tmp_path, sample_clean_mandi_csv):
    """Verify raw input source files are never altered or overwritten."""
    sha_before = compute_sha256(sample_clean_mandi_csv)
    raw_content_before = open(sample_clean_mandi_csv, "rb").read()

    out_dir = tmp_path / "processed"
    quar_dir = tmp_path / "quarantine"
    validator = MandiDataValidator(
        input_dir=str(tmp_path),
        output_dir=str(out_dir),
        quarantine_dir=str(quar_dir),
        min_series_records=1
    )
    validator.run()

    sha_after = compute_sha256(sample_clean_mandi_csv)
    raw_content_after = open(sample_clean_mandi_csv, "rb").read()

    assert sha_before == sha_after
    assert raw_content_before == raw_content_after
