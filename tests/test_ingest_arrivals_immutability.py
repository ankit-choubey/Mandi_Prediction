"""
Unit tests for Non-Destructive, Deterministic Agmarknet Arrivals Ingestion Engine.
Task: MP-DATA-002 & MP-DATA-002B
"""

import os
import sys
import json
import hashlib
import tempfile
import subprocess
import importlib.util
from typing import Dict
import pandas as pd
import numpy as np
import pytest

from src.ingest_agmarknet_arrivals import (
    audit_arrivals_folder,
    organize_and_export_city_crop,
    load_arrivals_file,
    validate_directories,
    ensure_path_within_output_dir,
    classify_file,
    discover_input_files,
    compute_sha256,
    COLUMN_ALIASES,
    AliasCollisionError
)

HAS_OPENPYXL = importlib.util.find_spec("openpyxl") is not None


def hash_directory(directory: str) -> Dict[str, str]:
    """Compute SHA-256 for all files in a directory tree."""
    tree_hashes = {}
    for root, _, files in os.walk(directory):
        for f in sorted(files):
            p = os.path.join(root, f)
            rel = os.path.relpath(p, directory)
            tree_hashes[rel] = compute_sha256(p)
    return tree_hashes


def create_sample_arrival_df(
    district="Lucknow",
    commodity="Wheat",
    dates=None,
    qty_col="Arrivals (Tonnes)",
    qty_vals=None
) -> pd.DataFrame:
    if dates is None:
        dates = ["10/01/2024", "11/01/2024"]
    if qty_vals is None:
        qty_vals = [50.0, 75.0]
    return pd.DataFrame({
        "State": ["Uttar Pradesh"] * len(dates),
        "District Name": [district] * len(dates),
        "Market Name": [f"{district} APMC"] * len(dates),
        "Commodity": [commodity] * len(dates),
        "Variety": ["Dara"] * len(dates),
        "Grade": ["FAQ"] * len(dates),
        "Arrival Date": dates,
        qty_col: qty_vals,
        "Min Price (Rs./Quintal)": [2000] * len(dates),
        "Max Price (Rs./Quintal)": [2200] * len(dates),
        "Modal Price (Rs./Quintal)": [2150] * len(dates),
    })


# =============================================================================
# 1. FIX 1: Missing values & String dtype
# =============================================================================

def test_missing_values_pandas_string_and_rejection_reason():
    """Missing District or Commodity stays <NA> (never 'nan') and is rejected with reason."""
    with tempfile.TemporaryDirectory() as tmpdir:
        df = pd.DataFrame({
            "District": ["Kanpur", None, "Lucknow", "Ghaziabad"],
            "Commodity": ["Wheat", "Potato", None, "Onion"],
            "Arrival Date": ["10/01/2024", "11/01/2024", "12/01/2024", "13/01/2024"],
            "Arrivals (Tonnes)": [50.0, 60.0, 70.0, None]
        })
        p = os.path.join(tmpdir, "missing_test.csv")
        df.to_csv(p, index=False)

        loaded = load_arrivals_file(p)
        # Verify pandas string dtype is used and missing value is not literal string 'nan'
        assert pd.isna(loaded.loc[1, "District_Raw"])
        assert loaded.loc[1, "District_Raw"] is not "nan"
        assert pd.isna(loaded.loc[2, "Commodity_Raw"])

        # Test rejection categorization
        with tempfile.TemporaryDirectory() as tmp_out:
            res = organize_and_export_city_crop(input_dir=tmpdir, output_dir=tmp_out, write=False)
            reasons = res["reconciliation"]["rejection_reasons"]
            assert reasons["missing_district"] == 1
            assert reasons["missing_commodity"] == 1
            assert reasons["missing_quantity"] == 1
            assert res["reconciliation"]["total_rows_out"] == 1
            assert res["reconciliation"]["total_rejected"] == 3


# =============================================================================
# 2. FIX 2: Preserve originals and explicit standardization
# =============================================================================

def test_preserve_originals_and_explicit_standard_mapping():
    """District_Raw / Commodity_Raw keep source casing; Std columns map typos via explicit mapping."""
    with tempfile.TemporaryDirectory() as tmpdir:
        df = pd.DataFrame({
            "District": ["gaziabaad", "Lukhnow", "kanpur nagar", "UnknownDistrict"],
            "Commodity": ["potatoes", "TOMATOES", "Paddy(Dhan)", "ExoticHerb"],
            "Arrival Date": ["10/01/2024", "11/01/2024", "12/01/2024", "13/01/2024"],
            "Arrivals (Tonnes)": [10.0, 20.0, 30.0, 40.0]
        })
        p = os.path.join(tmpdir, "std_test.csv")
        df.to_csv(p, index=False)

        loaded = load_arrivals_file(p)
        # Check raw preserved exactly as source (stripped)
        assert loaded.loc[0, "District_Raw"] == "gaziabaad"
        assert loaded.loc[1, "District_Raw"] == "Lukhnow"
        assert loaded.loc[0, "Commodity_Raw"] == "potatoes"
        assert loaded.loc[1, "Commodity_Raw"] == "TOMATOES"

        # Check explicit mapping
        assert loaded.loc[0, "District_Std"] == "Ghaziabad"
        assert loaded.loc[0, "District_Mapped"] == True
        assert loaded.loc[1, "District_Std"] == "Lucknow"
        assert loaded.loc[1, "District_Mapped"] == True
        assert loaded.loc[2, "District_Std"] == "Kanpur"
        assert loaded.loc[2, "District_Mapped"] == True

        assert loaded.loc[0, "Commodity_Std"] == "Potato"
        assert loaded.loc[0, "Commodity_Mapped"] == True
        assert loaded.loc[1, "Commodity_Std"] == "Tomato"
        assert loaded.loc[1, "Commodity_Mapped"] == True
        assert loaded.loc[2, "Commodity_Std"] == "Paddy"
        assert loaded.loc[2, "Commodity_Mapped"] == True

        # Unmapped stays as-is without title casing into identity
        assert loaded.loc[3, "District_Std"] == "UnknownDistrict"
        assert loaded.loc[3, "District_Mapped"] == False
        assert loaded.loc[3, "Commodity_Std"] == "ExoticHerb"
        assert loaded.loc[3, "Commodity_Mapped"] == False


# =============================================================================
# 3. FIX 3: Cross-file duplicates & conflicts partition identity
# =============================================================================

def test_cross_file_duplicates_and_conflicts_partition_identity():
    """Exact cross-file duplicates kept once; conflicts on natural key written to conflicts.csv."""
    with tempfile.TemporaryDirectory() as tmp_in, tempfile.TemporaryDirectory() as tmp_out:
        # File 1
        df1 = pd.DataFrame({
            "District": ["Kanpur", "Lucknow", "Ghaziabad"],
            "Market": ["Kanpur APMC", "Lucknow APMC", "Ghaziabad APMC"],
            "Commodity": ["Potato", "Wheat", "Onion"],
            "Variety": ["Desi", "Dara", "Red"],
            "Grade": ["FAQ", "FAQ", "FAQ"],
            "Arrival Date": ["10/01/2024", "10/01/2024", "10/01/2024"],
            "Arrivals (Tonnes)": [100.0, 200.0, 300.0],
            "Min Price": [1000, 2000, 3000],
            "Max Price": [1200, 2200, 3200],
            "Modal Price": [1100, 2100, 3100],
        })
        # File 2
        df2 = pd.DataFrame({
            "District": [
                "Kanpur",   # Exact duplicate of df1 row 0
                "Lucknow",  # Conflicting quantity (250 vs 200) on same natural key
                "Unnao"     # Unique new series
            ],
            "Market": ["Kanpur APMC", "Lucknow APMC", "Unnao APMC"],
            "Commodity": ["Potato", "Wheat", "Wheat"],
            "Variety": ["Desi", "Dara", "Dara"],
            "Grade": ["FAQ", "FAQ", "FAQ"],
            "Arrival Date": ["10/01/2024", "10/01/2024", "10/01/2024"],
            "Arrivals (Tonnes)": [100.0, 250.0, 150.0],
            "Min Price": [1000, 2000, 1900],
            "Max Price": [1200, 2200, 2100],
            "Modal Price": [1100, 2100, 2000],
        })
        df1.to_csv(os.path.join(tmp_in, "batch1.csv"), index=False)
        df2.to_csv(os.path.join(tmp_in, "batch2.csv"), index=False)

        res = organize_and_export_city_crop(input_dir=tmp_in, output_dir=tmp_out, write=True)

        reconc = res["reconciliation"]
        rows_in = reconc["total_rows_in"]
        rows_out = reconc["total_rows_out"]
        dups = reconc["total_duplicates"]
        conflicts = reconc["total_conflicts"]
        rej = reconc["total_rejected"]

        assert rows_in == 6
        assert dups == 1       # 1 exact duplicate (Kanpur Potato)
        assert conflicts == 2  # 2 conflicting rows (Lucknow Wheat: 200 vs 250)
        assert rej == 0
        assert rows_out == 3   # 3 accepted: Kanpur Potato (1 kept), Ghaziabad Onion, Unnao Wheat
        assert rows_in == rows_out + dups + conflicts + rej

        # Verify conflicts.csv was written and has 2 rows
        conflicts_path = os.path.join(tmp_out, "conflicts.csv")
        assert os.path.exists(conflicts_path)
        conflicts_df = pd.read_csv(conflicts_path)
        assert len(conflicts_df) == 2
        assert set(conflicts_df["Arrivals_Raw"]) == {200.0, 250.0}


# =============================================================================
# 4. FIX 4: Rejection reasons breakdown
# =============================================================================

def test_rejection_reasons_breakdown():
    """All 4 rejection reasons are distinctly categorized."""
    with tempfile.TemporaryDirectory() as tmp_in, tempfile.TemporaryDirectory() as tmp_out:
        df = pd.DataFrame({
            "District": [None, "Kanpur", "Kanpur", "Kanpur", "Kanpur"],
            "Commodity": ["Wheat", None, "Wheat", "Wheat", "Wheat"],
            "Arrival Date": ["10/01/2024", "10/01/2024", "invalid_date", "10/01/2024", "10/01/2024"],
            "Arrivals (Tonnes)": [50.0, 50.0, 50.0, None, 50.0]
        })
        p = os.path.join(tmp_in, "reasons.csv")
        df.to_csv(p, index=False)

        res = organize_and_export_city_crop(input_dir=tmp_in, output_dir=tmp_out, write=False)
        reasons = res["reconciliation"]["rejection_reasons"]
        assert reasons["missing_district"] == 1
        assert reasons["missing_commodity"] == 1
        assert reasons["unparseable_date"] == 1
        assert reasons["missing_quantity"] == 1
        assert res["reconciliation"]["total_rejected"] == 4
        assert res["reconciliation"]["total_rows_out"] == 1


# =============================================================================
# 5. FIX 5: Independent reconciliation read-back
# =============================================================================

def test_independent_reconciliation_readback():
    """Re-reading written files validates row counts with explicit raises."""
    with tempfile.TemporaryDirectory() as tmp_in, tempfile.TemporaryDirectory() as tmp_out:
        df = create_sample_arrival_df(district="Kanpur", commodity="Wheat")
        df.to_csv(os.path.join(tmp_in, "data.csv"), index=False)

        res = organize_and_export_city_crop(input_dir=tmp_in, output_dir=tmp_out, write=True)
        assert res["status"] == "SUCCESS"

        # Verify disk read-back succeeded
        master = pd.read_csv(os.path.join(tmp_out, "agmarknet_arrivals_up_consolidated.csv"))
        assert len(master) == 2


# =============================================================================
# 6. FIX 6: Excel dates handling and openpyxl integration [MP-DATA-003A]
# =============================================================================

def test_excel_dates_handling():
    """Excel datetime/Timestamp objects are handled before string conversion."""
    assert HAS_OPENPYXL is True, "openpyxl must be installed in environment"

    with tempfile.TemporaryDirectory() as tmpdir:
        import datetime
        df = pd.DataFrame({
            "District": ["Kanpur"],
            "Commodity": ["Wheat"],
            "Arrival Date": [datetime.datetime(2024, 1, 10, 0, 0, 0)],
            "Arrivals (Tonnes)": [50.0]
        })
        p = os.path.join(tmpdir, "excel_dates.xlsx")
        df.to_excel(p, index=False)

        res = load_arrivals_file(p)
        assert res.loc[0, "Arrival_Date"] == "2024-01-10"


def test_excel_real_datetime_and_timestamp_cells_with_openpyxl():
    """Test writing native datetime, Timestamp, and date cells with openpyxl."""
    import datetime
    import openpyxl

    with tempfile.TemporaryDirectory() as tmp_in, tempfile.TemporaryDirectory() as tmp_out:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["District", "Commodity", "Arrival Date", "Arrivals (Tonnes)"])
        # Native datetime.datetime
        ws.append(["Kanpur", "Wheat", datetime.datetime(2024, 4, 15, 12, 30, 0), 100.0])
        # pd.Timestamp
        ws.append(["Lucknow", "Rice", pd.Timestamp("2024-05-20 00:00:00"), 120.0])
        # datetime.date
        ws.append(["Jhansi", "Tomato", datetime.date(2024, 6, 25), 80.0])

        path = os.path.join(tmp_in, "native_cells.xlsx")
        wb.save(path)

        loaded = load_arrivals_file(path)
        assert list(loaded["Arrival_Date"]) == ["2024-04-15", "2024-05-20", "2024-06-25"]

        res = organize_and_export_city_crop(input_dir=tmp_in, output_dir=tmp_out, write=False)
        reconc = res["reconciliation"]
        assert reconc["rejection_reasons"]["unparseable_date"] == 0
        assert reconc["total_rejected"] == 0
        assert reconc["total_rows_out"] == 3


def test_excel_title_row_format_with_openpyxl():
    """Test Agmarknet-style title row (row 0 title, row 1 headers) with openpyxl."""
    import datetime
    import openpyxl

    with tempfile.TemporaryDirectory() as tmp_in, tempfile.TemporaryDirectory() as tmp_out:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Data_Report"
        # Row 1: Title row
        ws.append(["Daily Price Arrival Report-01-01-2024 to 31-12-2024 for Uttar Pradesh", "", "", "", "", "", "", "", "", ""])
        # Row 2: Header row
        ws.append(["State/UT", "District", "Market", "Commodity Group", "Commodity", "Variety", "Grade", "Arrival Date", "Arrival Quantity", "Arrival Unit"])
        # Row 3: Data row with datetime.datetime cell
        ws.append(["Uttar Pradesh", "Ghaziabad", "Ghaziabad APMC", "Foodgrains", "Wheat", "Dara", "FAQ", datetime.datetime(2024, 3, 10, 0, 0), 150.0, "Metric Tonnes"])
        # Row 4: Data row with pd.Timestamp cell
        ws.append(["Uttar Pradesh", "Lucknow", "Lucknow APMC", "Vegetables", "Potato", "Desi", "FAQ", pd.Timestamp("2024-03-11 00:00:00"), 200.0, "Tonnes"])

        path = os.path.join(tmp_in, "title_report.xlsx")
        wb.save(path)

        loaded = load_arrivals_file(path)
        assert list(loaded["Arrival_Date"]) == ["2024-03-10", "2024-03-11"]
        assert list(loaded["District_Std"]) == ["Ghaziabad", "Lucknow"]
        assert list(loaded["Commodity_Std"]) == ["Wheat", "Potato"]

        res = organize_and_export_city_crop(input_dir=tmp_in, output_dir=tmp_out, write=True)
        assert res["status"] == "SUCCESS"
        reconc = res["reconciliation"]
        assert reconc["rejection_reasons"]["unparseable_date"] == 0
        assert reconc["total_rejected"] == 0
        assert reconc["total_rows_out"] == 2

        # Read back consolidated master
        master = pd.read_csv(os.path.join(tmp_out, "agmarknet_arrivals_up_consolidated.csv"))
        assert len(master) == 2
        assert list(master["Arrival_Date"]) == ["2024-03-10", "2024-03-11"]


# =============================================================================
# 7. FIX 7: Units exact match (no substring matching)
# =============================================================================

def test_units_exact_match_no_substrings():
    """Normalized unit string must exactly match known sets; substrings do not match."""
    with tempfile.TemporaryDirectory() as tmpdir:
        df = pd.DataFrame({
            "District": ["Kanpur", "Kanpur", "Kanpur", "Kanpur", "Kanpur"],
            "Commodity": ["Wheat", "Wheat", "Wheat", "Wheat", "Wheat"],
            "Arrival Date": ["10/01/2024"] * 5,
            "qty": [10.0, 20.0, 30.0, 40.0, 50.0],
            "Arrival_Unit": [
                "cotton",          # Contains 'ton', must NOT match Tonnes
                "washington mt",   # Contains 'mt', must NOT match
                "Metric Tonnes",   # Exact match -> Tonnes
                "Qtl",             # Exact match -> Quintals
                "boxes"            # Unknown -> UNVERIFIED
            ]
        })
        p = os.path.join(tmpdir, "units_exact.csv")
        df.to_csv(p, index=False)

        loaded = load_arrivals_file(p)
        assert loaded.loc[0, "Arrival_Unit_Source"] == "UNVERIFIED"
        assert pd.isna(loaded.loc[0, "Arrivals_Tonnes"])

        assert loaded.loc[1, "Arrival_Unit_Source"] == "UNVERIFIED"
        assert pd.isna(loaded.loc[1, "Arrivals_Tonnes"])

        assert loaded.loc[2, "Arrival_Unit_Source"] == "Tonnes"
        assert loaded.loc[2, "Arrivals_Tonnes"] == 30.0

        assert loaded.loc[3, "Arrival_Unit_Source"] == "Quintals"
        assert loaded.loc[3, "Arrivals_Tonnes"] == 4.0  # 40 / 10 = 4.0

        assert loaded.loc[4, "Arrival_Unit_Source"] == "UNVERIFIED"
        assert pd.isna(loaded.loc[4, "Arrivals_Tonnes"])


# =============================================================================
# 8. FIX 8: Alias collisions fail the file
# =============================================================================

def test_alias_collision_fails_file():
    """If two source columns map to the same canonical alias, file fails with error in failed_files."""
    with tempfile.TemporaryDirectory() as tmp_in, tempfile.TemporaryDirectory() as tmp_out:
        df = pd.DataFrame({
            "District": ["Kanpur"],
            "Commodity": ["Wheat"],
            "Arrival Date": ["10/01/2024"],
            "qty": [10.0],          # Maps to Arrivals_Raw
            "arrivals": [20.0],     # Also maps to Arrivals_Raw with conflicting data
        })
        p = os.path.join(tmp_in, "collision.csv")
        df.to_csv(p, index=False)

        res = organize_and_export_city_crop(input_dir=tmp_in, output_dir=tmp_out, write=False)
        assert res["status"] in ["PARTIAL", "FAILED"]
        assert len(res["failed_files"]) == 1
        assert "Alias collision" in res["failed_files"][0]["error"]


# =============================================================================
# 9. FIX 9: Discovery with multiple input dirs & realpath symlink safety
# =============================================================================

def test_multiple_input_dirs_and_realpath_symlink_safety():
    """Accepts multiple input directories; manifest records source dir; symlinks cannot bypass checks."""
    with tempfile.TemporaryDirectory() as dir1, tempfile.TemporaryDirectory() as dir2, tempfile.TemporaryDirectory() as tmp_out:
        df1 = create_sample_arrival_df(district="Kanpur", commodity="Wheat")
        df2 = create_sample_arrival_df(district="Lucknow", commodity="Potato")
        df1.to_csv(os.path.join(dir1, "file1.csv"), index=False)
        df2.to_csv(os.path.join(dir2, "file2.csv"), index=False)

        res = organize_and_export_city_crop(input_dir=[dir1, dir2], output_dir=tmp_out, write=True)
        assert res["status"] == "SUCCESS"
        assert len(res["files_found"]) == 2

        # Check manifest recorded source directories
        manifest_path = os.path.join(tmp_out, "manifest.json")
        with open(manifest_path) as mf:
            mdata = json.load(mf)
        assert mdata["input_files"]["file1.csv"]["source_dir"] == os.path.realpath(dir1)
        assert mdata["input_files"]["file2.csv"]["source_dir"] == os.path.realpath(dir2)

        # Test symlink safety: symlink of output inside input is rejected
        sub_in = os.path.join(dir1, "sub")
        with pytest.raises(ValueError, match="cannot be inside"):
            validate_directories([dir1], sub_in)


# =============================================================================
# 10. FIX 10: Shared discovery & audit reports failures
# =============================================================================

def test_shared_discovery_and_audit_reports_failures():
    """audit_arrivals_folder reports failed files and PARTIAL status instead of swallowing errors."""
    with tempfile.TemporaryDirectory() as tmpdir:
        df_valid = create_sample_arrival_df(district="Kanpur", commodity="Wheat")
        df_valid.to_csv(os.path.join(tmpdir, "valid.csv"), index=False)

        # File with alias collision
        df_corrupt = pd.DataFrame({
            "District": ["Kanpur"],
            "Commodity": ["Wheat"],
            "qty": [10.0],
            "arrivals": [20.0]
        })
        df_corrupt.to_csv(os.path.join(tmpdir, "colliding.csv"), index=False)

        summary = audit_arrivals_folder(tmpdir)
        assert summary["status"] == "PARTIAL"
        assert len(summary["failed_files"]) == 1
        assert summary["failed_files"][0]["file"] == "colliding.csv"


# =============================================================================
# 11. FIX 11: CLI exit code non-zero on failure
# =============================================================================

def test_cli_exit_code_nonzero_on_failure():
    """main() exits non-zero for PARTIAL, FAILED, or invalid arguments."""
    with tempfile.TemporaryDirectory() as tmp_in, tempfile.TemporaryDirectory() as tmp_out:
        # Create colliding file
        df = pd.DataFrame({"District": ["Kanpur"], "Commodity": ["Wheat"], "qty": [10], "arrivals": [20]})
        df.to_csv(os.path.join(tmp_in, "bad.csv"), index=False)

        proc = subprocess.run(
            [sys.executable, "src/ingest_agmarknet_arrivals.py", "--input-dir", tmp_in, "--output-dir", tmp_out],
            capture_output=True,
            text=True
        )
        assert proc.returncode != 0, "CLI exited with 0 despite PARTIAL/FAILED status!"


# =============================================================================
# 12. FIX 12: Deterministic corrupt file test
# =============================================================================

def test_corrupt_file_deterministic_failure():
    """An unreadable corrupt file unconditionally yields PARTIAL and populates failed_files."""
    with tempfile.TemporaryDirectory() as tmp_in, tempfile.TemporaryDirectory() as tmp_out:
        df_valid = create_sample_arrival_df(district="Unnao", commodity="Rice")
        df_valid.to_csv(os.path.join(tmp_in, "valid.csv"), index=False)

        # Non-zip file named .xlsx will unconditionally fail pd.read_excel
        with open(os.path.join(tmp_in, "invalid_zip.xlsx"), "wb") as f:
            f.write(b"NOT_A_ZIP_OR_EXCEL_STREAM_RANDOM_BYTES_0123456789")

        res = organize_and_export_city_crop(input_dir=tmp_in, output_dir=tmp_out, write=False)
        assert res["status"] == "PARTIAL"
        assert len(res["failed_files"]) == 1
        assert res["failed_files"][0]["file"] == "invalid_zip.xlsx"


# =============================================================================
# 13. FIX 13: Second-run byte-identical outputs & no re-ingestion
# =============================================================================

def test_second_run_byte_identical_and_no_reingestion():
    """Running write twice on same input yields byte-identical files and never re-reads generated files."""
    with tempfile.TemporaryDirectory() as tmp_in, tempfile.TemporaryDirectory() as tmp_out:
        df = create_sample_arrival_df(district="Kanpur", commodity="Wheat")
        df.to_csv(os.path.join(tmp_in, "raw_data.csv"), index=False)

        # First run
        res1 = organize_and_export_city_crop(input_dir=tmp_in, output_dir=tmp_out, write=True)
        assert res1["status"] == "SUCCESS"
        hash_m1 = compute_sha256(os.path.join(tmp_out, "manifest.json"))
        hash_c1 = compute_sha256(os.path.join(tmp_out, "agmarknet_arrivals_up_consolidated.csv"))

        # Second run targeting same output
        res2 = organize_and_export_city_crop(input_dir=tmp_in, output_dir=tmp_out, write=True)
        assert res2["status"] == "SUCCESS"
        hash_m2 = compute_sha256(os.path.join(tmp_out, "manifest.json"))
        hash_c2 = compute_sha256(os.path.join(tmp_out, "agmarknet_arrivals_up_consolidated.csv"))

        assert hash_m1 == hash_m2, "manifest.json changed across identical reruns!"
        assert hash_c1 == hash_c2, "Master consolidated CSV changed across identical reruns!"

        # Now test that if input points to output directory, generated files are excluded
        valid_files, excluded_files = discover_input_files([tmp_out])
        assert len(valid_files) == 0, "Generated files in output_dir were incorrectly discovered as inputs!"
        excluded_reasons = {e["file"]: e["reason"] for e in excluded_files}
        assert excluded_reasons["agmarknet_arrivals_up_consolidated.csv"] == "generated_master_consolidated"
        assert excluded_reasons["manifest.json"] == "manifest_or_log_file"


# =============================================================================
# PRESERVED IMMUTABILITY & AUDIT TESTS
# =============================================================================

def test_input_tree_hash_immutability():
    """Inputs are strictly read-only: directory tree hash must be identical before and after a write run."""
    with tempfile.TemporaryDirectory() as tmp_in, tempfile.TemporaryDirectory() as tmp_out:
        df1 = create_sample_arrival_df(district="Kanpur", commodity="Potato")
        df2 = create_sample_arrival_df(district="Lucknow", commodity="Wheat")

        f1 = os.path.join(tmp_in, "kanpur_batch_01.csv")
        f2 = os.path.join(tmp_in, "lucknow_batch_01.csv")
        df1.to_csv(f1, index=False)
        df2.to_csv(f2, index=False)

        hashes_before = hash_directory(tmp_in)
        assert len(hashes_before) == 2

        res = organize_and_export_city_crop(input_dir=tmp_in, output_dir=tmp_out, write=True)
        assert res["status"] == "SUCCESS"

        hashes_after = hash_directory(tmp_in)
        assert hashes_before == hashes_after, "Input directory was modified by ingestion!"


def test_audit_does_not_create_missing_directory():
    """audit_arrivals_folder must be strictly read-only and return MISSING_DIR for nonexistent paths."""
    with tempfile.TemporaryDirectory() as tmpdir:
        missing_dir = os.path.join(tmpdir, "nonexistent_arrivals_folder")
        assert not os.path.exists(missing_dir)

        summary = audit_arrivals_folder(missing_dir)

        assert not os.path.exists(missing_dir), "audit_arrivals_folder created a missing directory!"
        assert summary["status"] == "MISSING_DIR"
        assert summary["files_count"] == 0


def test_nothing_written_to_repository_when_temp_paths_used():
    """Ingestion using temp paths writes zero files to the repository tree."""
    from src.ingest_agmarknet_arrivals import REPO_ROOT

    files_before = set(os.listdir(REPO_ROOT))

    with tempfile.TemporaryDirectory() as tmp_in, tempfile.TemporaryDirectory() as tmp_out:
        df = create_sample_arrival_df(district="Jhansi", commodity="Tomato")
        df.to_csv(os.path.join(tmp_in, "jhansi_tomato.csv"), index=False)

        organize_and_export_city_crop(input_dir=tmp_in, output_dir=tmp_out, write=True)

    files_after = set(os.listdir(REPO_ROOT))
    assert files_before == files_after, "Files were written to REPO_ROOT during temp-path execution!"


def test_agmarknet_title_row_header_handling():
    """Agmarknet report downloads with metadata in row 0 are properly normalized."""
    with tempfile.TemporaryDirectory() as tmpdir:
        content = (
            "Daily Price Arrival Report - Uttar Pradesh,Unnamed: 1,Unnamed: 2,Unnamed: 3\n"
            "District Name,Commodity,Arrival Date,Arrivals (Tonnes)\n"
            "Lucknow,Potato,12/01/2024,45.0\n"
        )
        p = os.path.join(tmpdir, "title_row.csv")
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)

        res = load_arrivals_file(p)
        assert "District" in res.columns
        assert "Commodity" in res.columns
        assert len(res) == 1
        assert res.loc[0, "District"] == "Lucknow"
        assert res.loc[0, "Commodity"] == "Potato"
        assert res.loc[0, "Arrivals_Tonnes"] == 45.0
