"""
Unit & Integration Tests for Mandi Data Pipeline
APMC Mandi Market Intelligence System

Tests cover:
- Successful loading and explicit schema normalization
- Non-destructive processing (verifying source file checksums remain identical)
- Safe handling of empty files (0 bytes and header-only)
- Safe handling of malformed rows (invalid dates, non-numeric prices, negative prices, missing metadata)
- Detection and error raising for missing mandatory columns
- Detection and error raising for missing source files and directories
- Detection and error raising for empty dataset states
- Manifest generation, UTC timestamping, and exact row count accounting
- Grade-preserving series identity and Strategy 2 duplicate exclusion
- Target crops filtering
- CLI entry point execution and parameter parsing
"""

import os
import sys
import json
import hashlib
import subprocess
import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from src.data_pipeline import (
    MandiDataPipeline,
    DataPipelineError,
    MissingSourceFilesError,
    MissingColumnsError,
    EmptyDatasetError,
    UnsupportedFileFormatError,
    compute_file_sha256,
    normalize_price_series,
    parse_arrival_dates,
    SCHEMA_VERSION,
    CANONICAL_COLUMNS,
    TARGET_CROPS
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_valid_csv(tmp_path):
    """Creates a temporary valid APMC CSV with varied column cases and aliases."""
    csv_file = tmp_path / "Ghaziabad_sample.csv"
    data = """arrival_date,commodity,commodity_code,district,grade,market,max_price,min_price,modal_price,state,variety
01/09/2021,Potato,24,Gaziabaad,FAQ,Ghaziabad,1600,1400,1500,Uttar Pradesh,Desi
02/09/2021,Potato,24,Gaziabaad,FAQ,Ghaziabad,1620,1420,1520,Uttar Pradesh,Desi
03/09/2021,Potato,24,Gaziabaad,Medium,Ghaziabad,1550,1350,1450,Uttar Pradesh,Desi
01/09/2021,Onion,23,Gaziabaad,FAQ,Ghaziabad,3000,2800,2900,Uttar Pradesh,Red
02/09/2021,Onion,23,Gaziabaad,FAQ,Ghaziabad,3100,2900,3000,Uttar Pradesh,Red
"""
    csv_file.write_text(data, encoding="utf-8")
    return str(csv_file)


# =============================================================================
# 1. SUCCESSFUL LOADING & CANONICAL NORMALIZATION
# =============================================================================

def test_successful_loading_and_normalization(tmp_path, sample_valid_csv):
    """Test successful loading, column standardization, date parsing, and price normalization."""
    out_dir = tmp_path / "processed"
    pipeline = MandiDataPipeline(
        input_dir=str(tmp_path),
        output_dir=str(out_dir),
        min_series_records=1,
        date_format="%Y-%m-%d"
    )
    df, manifest, out_csv, out_manifest = pipeline.run()

    # 1. Verify returned DataFrame structure
    assert not df.empty
    assert len(df) == 5
    for col in CANONICAL_COLUMNS:
        assert col in df.columns, f"Missing canonical column: {col}"

    # 2. Verify district normalization (Gaziabaad -> Ghaziabad)
    assert (df["District"] == "Ghaziabad").all()

    # 3. Verify numeric prices
    for p in ["Modal_Price", "Min_Price", "Max_Price"]:
        assert pd.api.types.is_numeric_dtype(df[p])
        assert (df[p] > 0).all()

    # 4. Verify canonical series_id incorporates Grade
    assert all("__FAQ" in s or "__Medium" in s for s in df["series_id"])

    # 5. Verify output files exist and are non-empty
    assert os.path.exists(out_csv)
    assert os.path.exists(out_manifest)
    assert os.path.getsize(out_csv) > 0
    assert os.path.getsize(out_manifest) > 0


# =============================================================================
# 2. SOURCE FILE PRESERVATION (NON-DESTRUCTIVE PROCESSING)
# =============================================================================

def test_source_files_unaltered(tmp_path, sample_valid_csv):
    """Verify that source files are 100% unchanged before and after pipeline execution."""
    sha256_before = compute_file_sha256(sample_valid_csv)
    content_before = open(sample_valid_csv, "rb").read()

    out_dir = tmp_path / "processed"
    pipeline = MandiDataPipeline(
        input_dir=str(tmp_path),
        output_dir=str(out_dir),
        min_series_records=1
    )
    pipeline.run()

    sha256_after = compute_file_sha256(sample_valid_csv)
    content_after = open(sample_valid_csv, "rb").read()

    assert sha256_before == sha256_after, "Source file SHA-256 changed after pipeline run!"
    assert content_before == content_after, "Source file content altered!"


# =============================================================================
# 3. EMPTY FILE HANDLING (0 BYTES & HEADER ONLY)
# =============================================================================

def test_empty_file_handling(tmp_path, sample_valid_csv):
    """Verify pipeline handles 0-byte and header-only empty files gracefully without crashing."""
    # 0-byte file
    zero_byte_file = tmp_path / "zero_byte.csv"
    zero_byte_file.touch()

    # Header-only file
    header_only_file = tmp_path / "header_only.csv"
    header_only_file.write_text("Arrival_Date,District,Market,Commodity,Variety,Modal_Price,Min_Price,Max_Price\n", encoding="utf-8")

    out_dir = tmp_path / "processed"
    pipeline = MandiDataPipeline(
        input_dir=str(tmp_path),
        output_dir=str(out_dir),
        min_series_records=1
    )
    df, manifest, out_csv, out_manifest = pipeline.run()

    # Pipeline should succeed by loading valid data from sample_valid_csv and skipping empty files
    assert len(df) == 5
    audits = {a["file_name"]: a for a in manifest["source_files_audit"]}
    assert "zero_byte.csv" in audits
    assert audits["zero_byte.csv"]["size_bytes"] == 0
    assert audits["zero_byte.csv"]["raw_row_count"] == 0
    assert audits["zero_byte.csv"]["valid_row_count"] == 0

    assert "header_only.csv" in audits
    assert audits["header_only.csv"]["raw_row_count"] == 0
    assert audits["header_only.csv"]["valid_row_count"] == 0


# =============================================================================
# 4. MALFORMED DATA & INVALID DATE / PRICE HANDLING
# =============================================================================

def test_malformed_data_handling(tmp_path):
    """Verify malformed rows (bad dates, text in prices, non-positive prices) are safely isolated."""
    csv_file = tmp_path / "malformed.csv"
    data = """Arrival_Date,Commodity,Commodity_Code,District,Grade,Market,Max_Price,Min_Price,Modal_Price,State,Variety
01/09/2021,Potato,24,Kanpur,FAQ,Kanpur,1600,1400,1500,Uttar Pradesh,Desi
99/99/9999,Potato,24,Kanpur,FAQ,Kanpur,1600,1400,1500,Uttar Pradesh,Desi
02/09/2021,Potato,24,Kanpur,FAQ,Kanpur,INVALID_PRICE,1400,1500,Uttar Pradesh,Desi
03/09/2021,Potato,24,Kanpur,FAQ,Kanpur,1600,-100,1500,Uttar Pradesh,Desi
04/09/2021,Potato,24,Kanpur,FAQ,Kanpur,1600,1400,0.0,Uttar Pradesh,Desi
05/09/2021,,24,Kanpur,FAQ,Kanpur,1600,1400,1500,Uttar Pradesh,Desi
06/09/2021,Potato,24,Kanpur,FAQ,Kanpur,1650,1450,1550,Uttar Pradesh,Desi
"""
    csv_file.write_text(data, encoding="utf-8")

    out_dir = tmp_path / "processed"
    pipeline = MandiDataPipeline(
        input_dir=str(tmp_path),
        output_dir=str(out_dir),
        min_series_records=1
    )
    df, manifest, _, _ = pipeline.run()

    # Out of 7 rows, only rows 1 and 7 are fully valid
    assert len(df) == 2
    audit = manifest["source_files_audit"][0]
    assert audit["raw_row_count"] == 7
    assert audit["valid_row_count"] == 2
    assert audit["dropped_row_count"] == 5

    # Check that individual failure reasons were properly tracked
    reasons = audit["dropped_reasons"]
    assert reasons["missing_dates"] == 1        # 99/99/9999
    assert reasons["missing_prices"] == 1       # INVALID_PRICE
    assert reasons["non_positive_prices"] == 2  # -100 and 0.0
    assert reasons["missing_series_metadata"] == 1 # Empty commodity


# =============================================================================
# 5. MISSING REQUIRED COLUMNS DETECTION
# =============================================================================

def test_missing_required_columns(tmp_path):
    """Verify that MissingColumnsError is raised when mandatory columns are absent."""
    csv_file = tmp_path / "missing_columns.csv"
    # Lacks 'Modal_Price' and 'Arrival_Date'
    data = """District,Market,Commodity,Variety,Min_Price,Max_Price
Kanpur,Kanpur(Grain),Wheat,Dara,2100,2300
"""
    csv_file.write_text(data, encoding="utf-8")

    pipeline = MandiDataPipeline(input_dir=str(tmp_path))
    with pytest.raises(MissingColumnsError) as exc_info:
        pipeline.run()

    error_msg = str(exc_info.value)
    assert "missing mandatory columns" in error_msg
    assert "Arrival_Date" in error_msg or "Modal_Price" in error_msg


# =============================================================================
# 6. MISSING SOURCE FILES & DIRECTORIES
# =============================================================================

def test_missing_source_directory():
    """Verify MissingSourceFilesError is raised when input directory does not exist."""
    pipeline = MandiDataPipeline(input_dir="/non/existent/mandi/path")
    with pytest.raises(MissingSourceFilesError) as exc_info:
        pipeline.run()
    assert "does not exist" in str(exc_info.value)


def test_empty_source_directory(tmp_path):
    """Verify MissingSourceFilesError is raised when directory contains no supported files."""
    empty_dir = tmp_path / "empty_dir"
    empty_dir.mkdir()
    pipeline = MandiDataPipeline(input_dir=str(empty_dir))
    with pytest.raises(MissingSourceFilesError) as exc_info:
        pipeline.run()
    assert "No CSV or Excel source files found" in str(exc_info.value)


# =============================================================================
# 7. EMPTY DATASET STATE DETECTION
# =============================================================================

def test_empty_dataset_error(tmp_path):
    """Verify EmptyDatasetError is raised when all rows are filtered out or empty."""
    # Only 0-byte file
    empty_file = tmp_path / "empty.csv"
    empty_file.touch()

    pipeline = MandiDataPipeline(input_dir=str(tmp_path))
    with pytest.raises(EmptyDatasetError) as exc_info:
        pipeline.run()
    assert "No valid observations were loaded" in str(exc_info.value)


# =============================================================================
# 8. MANIFEST GENERATION & ROW ACCOUNTING AUDIT
# =============================================================================

def test_processing_manifest_generation(tmp_path, sample_valid_csv):
    """Verify manifest fields, UTC timestamp format, SHA-256 hashes, and row accounting."""
    out_dir = tmp_path / "processed"
    pipeline = MandiDataPipeline(
        input_dir=str(tmp_path),
        output_dir=str(out_dir),
        min_series_records=1
    )
    _, manifest, out_csv, out_manifest = pipeline.run()

    # 1. Manifest structure checks
    assert manifest["schema_version"] == SCHEMA_VERSION
    assert manifest["pipeline_name"] == "MandiDataPipeline"

    # 2. Check UTC timestamp format (ISO-8601)
    timestamp = manifest["execution_timestamp_utc"]
    assert timestamp.endswith("+00:00") or timestamp.endswith("Z")
    parsed_ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    assert parsed_ts.tzinfo is not None

    # 3. Summary metrics accounting
    summary = manifest["summary_metrics"]
    assert summary["total_source_files"] == 1
    assert summary["total_raw_rows"] == 5
    assert summary["total_valid_parsed_rows"] == 5
    assert summary["total_dropped_raw_rows"] == 0
    assert summary["final_clean_rows"] == 5
    assert summary["total_raw_rows"] == summary["total_valid_parsed_rows"] + summary["total_dropped_raw_rows"]

    # 4. Output artifacts
    artifacts = {a["artifact_type"]: a for a in manifest["output_artifacts"]}
    assert "processed_dataset_csv" in artifacts
    assert "processing_manifest_json" in artifacts
    assert artifacts["processed_dataset_csv"]["size_bytes"] > 0
    assert len(artifacts["processed_dataset_csv"]["sha256"]) == 64

    # 5. Manifest file on disk is valid JSON
    with open(out_manifest, "r", encoding="utf-8") as f:
        disk_manifest = json.load(f)
    assert disk_manifest["schema_version"] == SCHEMA_VERSION


# =============================================================================
# 9. GRADE PRESERVATION & STRATEGY 2 DUPLICATE EXCLUSION
# =============================================================================

def test_grade_preservation_and_strategy2_duplicates(tmp_path):
    """Verify distinct grades are retained on same date, and conflicting same-grade quotes are dropped."""
    csv_file = tmp_path / "grades_and_dups.csv"
    data = """Arrival_Date,Commodity,Commodity_Code,District,Grade,Market,Max_Price,Min_Price,Modal_Price,State,Variety
01/09/2021,Wheat,28,Kanpur,FAQ,Kanpur,2200,2000,2100,Uttar Pradesh,Dara
01/09/2021,Wheat,28,Kanpur,Medium,Kanpur,2400,2200,2300,Uttar Pradesh,Dara
02/09/2021,Wheat,28,Kanpur,FAQ,Kanpur,2200,2000,2100,Uttar Pradesh,Dara
02/09/2021,Wheat,28,Kanpur,FAQ,Kanpur,2200,2000,2100,Uttar Pradesh,Dara
03/09/2021,Wheat,28,Kanpur,FAQ,Kanpur,2200,2000,2100,Uttar Pradesh,Dara
03/09/2021,Wheat,28,Kanpur,FAQ,Kanpur,2500,2300,2400,Uttar Pradesh,Dara
"""
    csv_file.write_text(data, encoding="utf-8")

    out_dir = tmp_path / "processed"
    pipeline = MandiDataPipeline(
        input_dir=str(tmp_path),
        output_dir=str(out_dir),
        min_series_records=1,
        exclude_ambiguous_same_grade=True
    )
    df, manifest, _, _ = pipeline.run()

    # Analysis of the 6 rows:
    # 01/09: FAQ (2100) and Medium (2300) -> Both must be KEPT (distinct grades).
    # 02/09: FAQ (2100) and FAQ (2100) -> Exact duplicates -> 1 KEPT (first).
    # 03/09: FAQ (2100) and FAQ (2400) -> Conflicting prices -> Strategy 2 EXCLUDES BOTH.
    # Total expected rows = 2 (from 01/09) + 1 (from 02/09) = 3 rows.
    assert len(df) == 3

    dates = pd.to_datetime(df["Arrival_Date"]).dt.strftime("%Y-%m-%d").tolist()
    assert "2021-09-01" in dates
    assert "2021-09-02" in dates
    assert "2021-09-03" not in dates, "Conflicting ambiguous same-grade quotes on 03/09 must be excluded!"

    summary = manifest["summary_metrics"]
    assert summary["ambiguous_same_grade_excluded_rows"] == 2
    assert summary["exact_duplicates_deduplicated"] == 1


# =============================================================================
# 10. TARGET CROPS FILTERING
# =============================================================================

def test_target_crops_filter(tmp_path):
    """Verify target crops filter retains only Potato, Onion, Tomato, Wheat."""
    csv_file = tmp_path / "crops.csv"
    data = """Arrival_Date,Commodity,Commodity_Code,District,Grade,Market,Max_Price,Min_Price,Modal_Price,State,Variety
01/09/2021,Potato,24,Kanpur,FAQ,Kanpur,1600,1400,1500,Uttar Pradesh,Desi
01/09/2021,Onion,23,Kanpur,FAQ,Kanpur,3000,2800,2900,Uttar Pradesh,Red
01/09/2021,Barley (Jau),29,Kanpur,FAQ,Kanpur,2300,2100,2200,Uttar Pradesh,Dara
01/09/2021,Mustard,12,Kanpur,FAQ,Kanpur,5000,4800,4900,Uttar Pradesh,Black
"""
    csv_file.write_text(data, encoding="utf-8")

    pipeline = MandiDataPipeline(
        input_dir=str(tmp_path),
        min_series_records=1,
        target_crops_only=True
    )
    df, _, _, _ = pipeline.run()

    assert len(df) == 2
    assert set(df["Commodity"].unique()) == {"Potato", "Onion"}


# =============================================================================
# 11. CLI INVOCATION TEST
# =============================================================================

def test_cli_help():
    """Verify python -m src.data_pipeline --help exits cleanly with code 0."""
    result = subprocess.run(
        [sys.executable, "-m", "src.data_pipeline", "--help"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "Mandi Data Pipeline" in result.stdout
    assert "--input-dir" in result.stdout
    assert "--output-dir" in result.stdout


def test_cli_execution_on_test_data(tmp_path, sample_valid_csv):
    """Verify end-to-end execution of CLI script on test dataset."""
    out_dir = tmp_path / "cli_processed"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.data_pipeline",
            "--input-dir", str(tmp_path),
            "--output-dir", str(out_dir),
            "--min-series-records", "1"
        ],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "SUCCESS: Mandi 5-year data processing pipeline completed successfully" in result.stdout
    assert os.path.exists(out_dir / "mandi_5year_processed.csv")
    assert os.path.exists(out_dir / "processing_manifest.json")
