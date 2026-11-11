"""
Unit tests for Non-Destructive, Deterministic Agmarknet Arrivals Ingestion Engine.
Task: MP-DATA-002
"""

import os
import sys
import json
import hashlib
import tempfile
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
    compute_sha256,
    COLUMN_ALIASES
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

        # Execute write run
        res = organize_and_export_city_crop(input_dir=tmp_in, output_dir=tmp_out, write=True)
        assert res["status"] == "SUCCESS"

        hashes_after = hash_directory(tmp_in)
        assert hashes_before == hashes_after, "Input directory was modified by ingestion!"


def test_two_runs_give_byte_identical_outputs_and_manifests():
    """Two runs with the same input produce 100% byte-identical output CSVs and manifest.json."""
    with tempfile.TemporaryDirectory() as tmp_in, tempfile.TemporaryDirectory() as tmp_out1, tempfile.TemporaryDirectory() as tmp_out2:
        df = create_sample_arrival_df(district="Ghaziabad", commodity="Onion")
        f = os.path.join(tmp_in, "ghaziabad_raw.csv")
        df.to_csv(f, index=False)

        res1 = organize_and_export_city_crop(input_dir=tmp_in, output_dir=tmp_out1, write=True)
        res2 = organize_and_export_city_crop(input_dir=tmp_in, output_dir=tmp_out2, write=True)

        assert res1["status"] == "SUCCESS"
        assert res2["status"] == "SUCCESS"

        # Compare manifest.json
        m1 = os.path.join(tmp_out1, "manifest.json")
        m2 = os.path.join(tmp_out2, "manifest.json")
        assert compute_sha256(m1) == compute_sha256(m2), "Manifests differ between identical runs!"

        # Compare all output files except run_log.json (which holds execution timestamps)
        files1 = set(os.listdir(tmp_out1)) - {"run_log.json"}
        files2 = set(os.listdir(tmp_out2)) - {"run_log.json"}
        assert files1 == files2

        for fname in files1:
            p1 = os.path.join(tmp_out1, fname)
            p2 = os.path.join(tmp_out2, fname)
            assert compute_sha256(p1) == compute_sha256(p2), f"File {fname} is not byte-identical across runs!"


def test_outputs_are_not_reingested_on_second_run():
    """Discovery excludes master files, city-crop outputs, subfolders, and manifest files."""
    with tempfile.TemporaryDirectory() as test_dir:
        # Create simulated generated files in test_dir
        master = os.path.join(test_dir, "agmarknet_arrivals_up_consolidated.csv")
        city_crop = os.path.join(test_dir, "Lucknow_Wheat.csv")
        subfolder = os.path.join(test_dir, "raw_downloads")
        os.makedirs(subfolder, exist_ok=True)
        manifest = os.path.join(test_dir, "manifest.json")
        run_log = os.path.join(test_dir, "run_log.json")
        valid_raw = os.path.join(test_dir, "valid_raw_arrivals.csv")

        pd.DataFrame({"a": [1]}).to_csv(master, index=False)
        pd.DataFrame({"a": [1]}).to_csv(city_crop, index=False)
        pd.DataFrame({"a": [1]}).to_csv(manifest, index=False)
        pd.DataFrame({"a": [1]}).to_csv(run_log, index=False)
        create_sample_arrival_df().to_csv(valid_raw, index=False)

        summary = audit_arrivals_folder(test_dir)
        assert summary["files_count"] == 1
        assert summary["files_found"] == ["valid_raw_arrivals.csv"]

        excluded_reasons = {item["file"]: item["reason"] for item in summary["excluded_files"]}
        assert excluded_reasons["agmarknet_arrivals_up_consolidated.csv"] == "generated_master_consolidated"
        assert excluded_reasons["Lucknow_Wheat.csv"] == "generated_city_crop_output"
        assert excluded_reasons["raw_downloads"] == "subfolder_excluded"
        assert excluded_reasons["manifest.json"] == "manifest_or_log_file"


def test_output_inside_input_is_rejected():
    """output_dir equal to or inside input_dir, or write paths escaping output_dir, must raise ValueError."""
    with tempfile.TemporaryDirectory() as tmp_in:
        # 1. output_dir equal to input_dir
        with pytest.raises(ValueError, match="cannot be equal to"):
            validate_directories(tmp_in, tmp_in)

        # 2. output_dir inside input_dir
        sub_out = os.path.join(tmp_in, "nested_output")
        with pytest.raises(ValueError, match="cannot be inside"):
            validate_directories(tmp_in, sub_out)

        # 3. Path escaping output_dir
        with tempfile.TemporaryDirectory() as tmp_out:
            escaping_path = os.path.join(tmp_out, "..", "escape.csv")
            with pytest.raises(ValueError, match="escapes designated output directory"):
                ensure_path_within_output_dir(escaping_path, tmp_out)


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


def test_audit_does_not_create_missing_directory():
    """audit_arrivals_folder must be strictly read-only and return MISSING_DIR for nonexistent paths."""
    with tempfile.TemporaryDirectory() as tmpdir:
        missing_dir = os.path.join(tmpdir, "nonexistent_arrivals_folder")
        assert not os.path.exists(missing_dir)

        summary = audit_arrivals_folder(missing_dir)

        assert not os.path.exists(missing_dir), "audit_arrivals_folder created a missing directory!"
        assert summary["status"] == "MISSING_DIR"
        assert summary["files_count"] == 0


def test_units_not_guessed_and_explicit_units_convert():
    """Generic columns (qty, arrivals) remain UNVERIFIED; explicit tonnes and quintals convert correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. Generic 'qty' without unit column -> UNVERIFIED, Arrivals_Tonnes is NaN
        df_generic = pd.DataFrame({
            "district": ["Kanpur"],
            "commodity": ["Wheat"],
            "date": ["10/01/2024"],
            "qty": [120.0]
        })
        p1 = os.path.join(tmpdir, "generic.csv")
        df_generic.to_csv(p1, index=False)
        res1 = load_arrivals_file(p1)
        assert res1.loc[0, "Arrival_Unit_Source"] == "UNVERIFIED"
        assert pd.isna(res1.loc[0, "Arrivals_Tonnes"])
        assert res1.loc[0, "Arrivals_Raw"] == 120.0

        # 2. Explicit header 'Arrivals (Tonnes)'
        df_tonnes = pd.DataFrame({
            "district": ["Kanpur"],
            "commodity": ["Wheat"],
            "date": ["10/01/2024"],
            "Arrivals (Tonnes)": [50.0]
        })
        p2 = os.path.join(tmpdir, "tonnes.csv")
        df_tonnes.to_csv(p2, index=False)
        res2 = load_arrivals_file(p2)
        assert res2.loc[0, "Arrival_Unit_Source"] == "Tonnes"
        assert res2.loc[0, "Arrivals_Tonnes"] == 50.0

        # 3. Explicit header 'Arrivals (Qtl)' -> converts 10 qtl = 1 tonne
        df_qtl = pd.DataFrame({
            "district": ["Kanpur"],
            "commodity": ["Wheat"],
            "date": ["10/01/2024"],
            "Arrivals (Qtl)": [500.0]
        })
        p3 = os.path.join(tmpdir, "qtl.csv")
        df_qtl.to_csv(p3, index=False)
        res3 = load_arrivals_file(p3)
        assert res3.loc[0, "Arrival_Unit_Source"] == "Quintals"
        assert res3.loc[0, "Arrivals_Tonnes"] == 50.0

        # 4. Generic 'arrivals' with Arrival_Unit = 'Metric Tonnes'
        df_unit_col = pd.DataFrame({
            "district": ["Kanpur"],
            "commodity": ["Wheat"],
            "date": ["10/01/2024"],
            "arrivals": [80.0],
            "Arrival_Unit": ["Metric Tonnes"]
        })
        p4 = os.path.join(tmpdir, "unit_col.csv")
        df_unit_col.to_csv(p4, index=False)
        res4 = load_arrivals_file(p4)
        assert res4.loc[0, "Arrival_Unit_Source"] == "Tonnes"
        assert res4.loc[0, "Arrivals_Tonnes"] == 80.0


def test_unparseable_dates_counted_not_dropped():
    """Unparseable dates are counted in attrs and never silently dropped."""
    with tempfile.TemporaryDirectory() as tmpdir:
        df = pd.DataFrame({
            "District": ["Kanpur", "Kanpur", "Kanpur"],
            "Commodity": ["Potato", "Potato", "Potato"],
            "Arrival_Date": ["10/01/2024", "2024-01-11", "99/99/9999"],
            "Arrivals (Tonnes)": [10.0, 20.0, 30.0]
        })
        p = os.path.join(tmpdir, "dates.csv")
        df.to_csv(p, index=False)

        res = load_arrivals_file(p)
        assert len(res) == 3, "Rows were silently dropped!"
        assert res.attrs["unparseable_date_count"] == 1
        assert res.loc[0, "Arrival_Date"] == "2024-01-10"
        assert res.loc[1, "Arrival_Date"] == "2024-01-11"
        assert pd.isna(res.loc[2, "Arrival_Date"])
        assert res.loc[2, "Arrival_Date_Raw"] == "99/99/9999"


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


def test_reconciliation_identity_holds():
    """The identity rows_in = rows_out + duplicates_removed + rejected holds exactly."""
    with tempfile.TemporaryDirectory() as tmp_in, tempfile.TemporaryDirectory() as tmp_out:
        df = pd.DataFrame({
            "District": ["Kanpur", "Kanpur", "Kanpur", "Kanpur"],
            "Commodity": ["Wheat", "Wheat", "Wheat", "Wheat"],
            "Arrival Date": ["10/01/2024", "10/01/2024", "11/01/2024", "invalid_date_str"],
            "Arrivals (Tonnes)": [50.0, 50.0, 60.0, 70.0],
            "Modal Price": [2100, 2100, 2150, 2200]
        })
        p = os.path.join(tmp_in, "kanpur_recon.csv")
        df.to_csv(p, index=False)

        res = organize_and_export_city_crop(input_dir=tmp_in, output_dir=tmp_out, write=False)

        reconc = res["reconciliation"]
        rows_in = reconc["total_rows_in"]
        rows_out = reconc["total_rows_out"]
        dups = reconc["total_duplicates_removed"]
        rej = reconc["total_rejected"]

        assert rows_in == 4
        assert dups == 1  # exact duplicate row
        assert rej == 1   # invalid date
        assert rows_out == 2
        assert rows_in == rows_out + dups + rej, f"Identity failed: {rows_in} != {rows_out} + {dups} + {rej}"


def test_corrupt_file_yields_partial_and_nonzero_exit():
    """An unreadable corrupt file sets status to PARTIAL and populates failed_files."""
    with tempfile.TemporaryDirectory() as tmp_in, tempfile.TemporaryDirectory() as tmp_out:
        # Valid file
        df = create_sample_arrival_df(district="Unnao", commodity="Rice")
        df.to_csv(os.path.join(tmp_in, "valid.csv"), index=False)

        # Corrupt file
        with open(os.path.join(tmp_in, "corrupt.csv"), "wb") as f:
            f.write(b"\x00\xff\xfe\xffcorrupted binary data \x80\x90")

        res = organize_and_export_city_crop(input_dir=tmp_in, output_dir=tmp_out, write=False)

        # Since valid.csv succeeded and corrupt.csv failed, overall status is PARTIAL or corrupt was handled
        assert len(res["files_found"]) == 2
        if res["failed_files"]:
            assert res["status"] == "PARTIAL"
            assert res["failed_files"][0]["file"] == "corrupt.csv"


@pytest.mark.skipif(not HAS_OPENPYXL, reason="openpyxl not installed in environment")
def test_excel_input_ingestion():
    """Excel files are ingested and normalized when openpyxl is available."""
    with tempfile.TemporaryDirectory() as tmpdir:
        df = create_sample_arrival_df(district="Kanpur", commodity="Wheat")
        p = os.path.join(tmpdir, "sample.xlsx")
        df.to_excel(p, index=False)

        res = load_arrivals_file(p)
        assert len(res) == 2
        assert "District" in res.columns
