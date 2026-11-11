"""
AGMARKNET Daily Price & Arrival Report Ingestion Engine
APMC Mandi Market Intelligence System
Author: Track D / Data Operations

Deterministic, non-destructive, and immutable arrivals ingestion engine.
Enforces strict separation of input_dir and output_dir, immutability of raw inputs,
explicit unit resolution, deterministic CSV export with SHA-256 manifests,
and strict row reconciliation accounting.

Required Behaviors:
1. Inputs are read-only: never move, delete, rename, or modify input files.
2. Strict directory separation: output_dir default data/interim/arrivals/; rejects
   output_dir inside or equal to input_dir; rejects writes escaping output_dir.
3. No hidden global write paths: all paths derive from function arguments.
4. Input discovery excludes generated master consolidated files, {District}_{Commodity}.csv
   outputs, and subfolders (e.g. raw_downloads/).
5. Dry-run is default; writes require explicit flag.
6. audit_arrivals_folder is strictly read-only; missing directory returns MISSING_DIR.
7. Units: generic columns (qty, arrivals) are kept in Arrivals_Raw and marked UNVERIFIED
   without guessing tonnes. Arrivals_Tonnes produced only when explicit.
8. Dates: strict explicit formats only; unparseable dates counted, never silently dropped.
9. Deduplication & Reconciliation identity:
   rows_in = rows_out + duplicates_removed + rejected
10. Determinism: sorted inputs, stable row sort, SHA-256 manifests, separate run log.
11. Failures: corrupt files recorded in failed_files, status PARTIAL/FAILED, CLI exit non-zero.
"""

import os
import sys
import json
import hashlib
import logging
import argparse
from datetime import datetime, timezone
from typing import List, Dict, Tuple, Optional, Any
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
logger = logging.getLogger("agmarknet_ingest")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_INPUT_DIR = os.path.join(REPO_ROOT, "data", "raw", "arrivals", "historical")
DEFAULT_OUTPUT_DIR = os.path.join(REPO_ROOT, "data", "interim", "arrivals")
ARRIVALS_DIR = DEFAULT_INPUT_DIR

TARGET_DISTRICTS = ["Ghaziabad", "Jhansi", "Kanpur", "Lucknow", "Unnao"]
TARGET_CROPS = ["Potato", "Onion", "Tomato", "Wheat", "Rice", "Paddy"]

EXPLICIT_DATE_FORMATS = ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"]

COLUMN_ALIASES = {
    "state": "State",
    "state/ut": "State",
    "district name": "District",
    "district": "District",
    "market name": "Market",
    "market": "Market",
    "commodity group": "Commodity_Group",
    "commodity": "Commodity",
    "variety": "Variety",
    "grade": "Grade",
    "arrival date": "Arrival_Date",
    "reported date": "Arrival_Date",
    "date": "Arrival_Date",
    "arrival unit": "Arrival_Unit",
    "unit": "Arrival_Unit",
    "min price (rs./quintal)": "Min_Price",
    "min price": "Min_Price",
    "max price (rs./quintal)": "Max_Price",
    "max price": "Max_Price",
    "modal price (rs./quintal)": "Modal_Price",
    "modal price": "Modal_Price",
    "price unit": "Price_Unit",
    # CEDA Agmarknet portal aliases
    "t": "Arrival_Date",
    "cmdty": "Commodity",
    "district_name": "District",
    "state_name": "State",
    "market_name": "Market",
    "qty": "Arrivals_Raw",
    "arrivals": "Arrivals_Raw",
    "arrival quantity": "Arrivals_Raw",
    "p_min": "Min_Price",
    "p_max": "Max_Price",
    "p_modal": "Modal_Price"
}


def compute_sha256(filepath: str) -> str:
    """Compute the SHA-256 hexadecimal digest of a file in binary mode."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def validate_directories(input_dir: str, output_dir: str) -> Tuple[str, str]:
    """
    Validates that input_dir and output_dir are distinct and output_dir
    is not equal to or contained within input_dir.
    """
    abs_input = os.path.abspath(input_dir)
    abs_output = os.path.abspath(output_dir)

    if abs_input == abs_output:
        raise ValueError(
            f"output_dir ({abs_output}) cannot be equal to input_dir ({abs_input})"
        )

    try:
        common = os.path.commonpath([abs_input, abs_output])
    except ValueError:
        common = None

    if common == abs_input:
        raise ValueError(
            f"output_dir ({abs_output}) cannot be inside input_dir ({abs_input})"
        )

    return abs_input, abs_output


def ensure_path_within_output_dir(target_path: str, output_dir: str) -> str:
    """Rejects any write path that falls outside designated output directory."""
    abs_target = os.path.abspath(target_path)
    abs_output = os.path.abspath(output_dir)
    try:
        common = os.path.commonpath([abs_output, abs_target])
    except ValueError:
        common = None

    if common != abs_output:
        raise ValueError(
            f"Write path ({abs_target}) escapes designated output directory ({abs_output})"
        )
    return abs_target


def classify_file(filename: str, parent_dir: str) -> Tuple[bool, str]:
    """
    Determines whether a file in parent_dir is a valid raw input or an excluded file.
    Returns (is_valid_input, reason).
    """
    full_path = os.path.join(parent_dir, filename)

    if os.path.isdir(full_path):
        return False, "subfolder_excluded"

    if filename.startswith("."):
        return False, "hidden_or_system_file"

    if filename in ["manifest.json", "run_log.json", "checksums.sha256", "existing_file_inventory.csv"]:
        return False, "manifest_or_log_file"

    # Master consolidated files
    if (
        filename.startswith("agmarknet_arrivals_up_")
        or filename.startswith("master_consolidated")
        or filename in ["consolidated_arrivals.csv", "agmarknet_arrivals_up_consolidated.csv"]
    ):
        return False, "generated_master_consolidated"

    # Generated city-crop outputs: {District}_{Commodity}.csv
    if filename.endswith(".csv"):
        stem = filename[:-4]
        parts = stem.split("_")
        if len(parts) == 2:
            p0 = parts[0].strip()
            p1 = parts[1].strip()
            # Match BOTH district in target districts AND crop in target crops
            is_dist = p0 in TARGET_DISTRICTS or any(p0.lower() == d.lower() for d in TARGET_DISTRICTS)
            is_crop = p1 in TARGET_CROPS or any(p1.lower() == c.lower() for c in TARGET_CROPS)
            if is_dist and is_crop:
                return False, "generated_city_crop_output"

    if not filename.lower().endswith((".csv", ".xlsx", ".xls")):
        return False, "unsupported_file_extension"

    return True, "valid_raw_input"


def parse_explicit_dates(date_series: pd.Series) -> Tuple[pd.Series, pd.Series, int]:
    """
    Parses dates using strict explicit formats only.
    Formats tried: %d/%m/%Y, %d-%m-%Y, %Y-%m-%d.
    Does NOT guess day/month order.
    Returns (raw_dates_series, parsed_iso_series, unparseable_count).
    """
    raw_dates = date_series.astype(str).str.strip()
    clean_mask = date_series.notna() & (~raw_dates.isin(["nan", "<NA>", "None", "", "NaT"]))

    parsed = pd.Series(pd.NaT, index=date_series.index)
    for fmt in EXPLICIT_DATE_FORMATS:
        mask = clean_mask & parsed.isna()
        if not mask.any():
            break
        parsed[mask] = pd.to_datetime(raw_dates[mask], format=fmt, errors="coerce")

    unparseable_mask = clean_mask & parsed.isna()
    unparseable_count = int(unparseable_mask.sum())

    iso_dates = pd.Series(None, index=date_series.index, dtype=object)
    valid_mask = parsed.notna()
    iso_dates[valid_mask] = parsed[valid_mask].dt.strftime("%Y-%m-%d")

    return raw_dates, iso_dates, unparseable_count


def load_arrivals_file(file_path: str) -> pd.DataFrame:
    """
    Load and normalize an Agmarknet arrivals file (CSV or Excel).
    Inputs are read-only: this function never modifies or writes to the input file.
    Resolves units explicitly:
      - Raw value kept in Arrivals_Raw
      - Unit source recorded in Arrival_Unit_Source ('Tonnes', 'Quintals', or 'UNVERIFIED')
      - Arrivals_Tonnes populated only when unit is explicit (1 tonne = 10 quintals);
        left empty (NaN) when generic/unverified.
      - Explicit date parsing with unparseable count tracked in df.attrs.
    """
    if file_path.lower().endswith(".csv"):
        df = pd.read_csv(file_path, low_memory=False)
    elif file_path.lower().endswith((".xlsx", ".xls")):
        try:
            df = pd.read_excel(file_path)
        except Exception as e:
            raise RuntimeError(f"Failed to read Excel file {file_path}: {e}")
    else:
        raise ValueError(f"Unsupported file format: {file_path}")

    # Detect if row 0 has headers (common in Agmarknet report downloads)
    if any("unnamed" in str(c).lower() or "daily price arrival" in str(c).lower() for c in df.columns[:2]):
        if any("district" in str(v).lower() for v in df.iloc[0].values):
            df.columns = [str(x).strip() for x in df.iloc[0].values]
            df = df.iloc[1:].reset_index(drop=True)

    # Detect original arrival quantity column and unit hint before alias mapping
    orig_arrival_col = None
    unit_hint = "UNVERIFIED"

    for c in df.columns:
        c_clean = str(c).strip().lower()
        if any(token in c_clean for token in ["arrivals (tonnes)", "arrivals(in tonnes)", "arrivals (tonne)", "arrivals_tonnes"]):
            orig_arrival_col = c
            unit_hint = "Tonnes"
            break
        elif any(token in c_clean for token in ["arrivals (qtl)", "arrivals (in qtl)", "arrivals (quintal)", "arrivals_qtl"]):
            orig_arrival_col = c
            unit_hint = "Quintals"
            break
        elif any(token in c_clean for token in ["arrival quantity", "arrivals", "qty"]):
            orig_arrival_col = c
            unit_hint = "GENERIC"
            break

    # Standardize column names via aliases
    normalized_cols = {c: COLUMN_ALIASES.get(str(c).strip().lower(), str(c).strip()) for c in df.columns}
    df.rename(columns=normalized_cols, inplace=True)

    # Standardize District and Commodity naming
    if "District" in df.columns:
        df["District"] = df["District"].astype(str).str.strip().str.title()
    if "Commodity" in df.columns:
        df["Commodity"] = df["Commodity"].astype(str).str.strip().str.title()

    # Unit Resolution
    if orig_arrival_col is not None:
        raw_vals = pd.to_numeric(df[normalized_cols[orig_arrival_col]], errors="coerce")
        df["Arrivals_Raw"] = raw_vals

        if unit_hint == "Tonnes":
            df["Arrival_Unit_Source"] = "Tonnes"
            df["Arrivals_Tonnes"] = raw_vals
        elif unit_hint == "Quintals":
            df["Arrival_Unit_Source"] = "Quintals"
            df["Arrivals_Tonnes"] = raw_vals / 10.0
        else:
            # Generic quantity: inspect Arrival_Unit column if present
            if "Arrival_Unit" in df.columns:
                unit_series = df["Arrival_Unit"].astype(str).str.strip().str.lower()
                is_tonne = unit_series.apply(lambda u: any(w in u for w in ["tonne", "ton", "mt", "metric tonnes"]))
                is_qtl = unit_series.apply(lambda u: any(w in u for w in ["quintal", "qtl"]))

                unit_source = pd.Series("UNVERIFIED", index=df.index, dtype=object)
                unit_source[is_tonne] = "Tonnes"
                unit_source[is_qtl] = "Quintals"
                df["Arrival_Unit_Source"] = unit_source

                tonnes_vals = pd.Series(np.nan, index=df.index, dtype=float)
                tonnes_vals[is_tonne] = raw_vals[is_tonne]
                tonnes_vals[is_qtl] = raw_vals[is_qtl] / 10.0
                df["Arrivals_Tonnes"] = tonnes_vals
            else:
                df["Arrival_Unit_Source"] = "UNVERIFIED"
                df["Arrivals_Tonnes"] = np.nan
    else:
        df["Arrivals_Raw"] = np.nan
        df["Arrival_Unit_Source"] = "UNVERIFIED"
        df["Arrivals_Tonnes"] = np.nan

    # Date Resolution
    unparseable_dates = 0
    if "Arrival_Date" in df.columns:
        raw_dates, iso_dates, unparseable_dates = parse_explicit_dates(df["Arrival_Date"])
        df["Arrival_Date_Raw"] = raw_dates
        df["Arrival_Date"] = iso_dates
    else:
        df["Arrival_Date_Raw"] = ""
        df["Arrival_Date"] = None

    df.attrs["unparseable_date_count"] = unparseable_dates
    return df


def audit_arrivals_folder(folder_path: str = DEFAULT_INPUT_DIR) -> Dict[str, Any]:
    """
    Strictly read-only inspection of folder_path.
    Never creates directories (no makedirs) and never modifies files.
    If folder does not exist, returns status MISSING_DIR.
    """
    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        return {
            "folder_path": folder_path,
            "status": "MISSING_DIR",
            "files_count": 0,
            "files_found": [],
            "excluded_files": [],
            "total_records": 0,
            "districts_covered": [],
            "commodities_covered": [],
            "date_min": None,
            "date_max": None,
            "unparseable_date_count": 0,
            "unit_status_counts": {},
            "duplicates_count": 0,
            "reconciliation": {}
        }

    all_entries = sorted(os.listdir(folder_path))
    data_files = []
    excluded_files = []

    for entry in all_entries:
        is_valid, reason = classify_file(entry, folder_path)
        if is_valid:
            data_files.append(entry)
        else:
            excluded_files.append({"file": entry, "reason": reason})

    summary = {
        "folder_path": folder_path,
        "status": "EMPTY" if not data_files else "POPULATED",
        "files_count": len(data_files),
        "files_found": data_files,
        "excluded_files": excluded_files,
        "districts_covered": [],
        "commodities_covered": [],
        "total_records": 0,
        "date_min": None,
        "date_max": None,
        "unparseable_date_count": 0,
        "unit_status_counts": {"Tonnes": 0, "Quintals": 0, "UNVERIFIED": 0},
        "duplicates_count": 0,
        "reconciliation": {}
    }

    if not data_files:
        return summary

    total_rows = 0
    total_unparseable = 0
    total_duplicates = 0
    valid_dates = []
    districts_set = set()
    commodities_set = set()
    unit_counts = {"Tonnes": 0, "Quintals": 0, "UNVERIFIED": 0}

    for fname in data_files:
        full_path = os.path.join(folder_path, fname)
        try:
            df = load_arrivals_file(full_path)
            total_rows += len(df)
            total_unparseable += df.attrs.get("unparseable_date_count", 0)

            # Duplicates in raw file
            dups = int(df.duplicated().sum())
            total_duplicates += dups

            if "District" in df.columns:
                for d in df["District"].dropna().unique():
                    if str(d).strip():
                        districts_set.add(str(d).strip())
            if "Commodity" in df.columns:
                for c in df["Commodity"].dropna().unique():
                    if str(c).strip():
                        commodities_set.add(str(c).strip())

            if "Arrival_Date" in df.columns:
                dates = df["Arrival_Date"].dropna().tolist()
                valid_dates.extend([d for d in dates if str(d).strip()])

            if "Arrival_Unit_Source" in df.columns:
                counts = df["Arrival_Unit_Source"].value_counts().to_dict()
                for k, v in counts.items():
                    unit_counts[k] = unit_counts.get(k, 0) + v
        except Exception as e:
            logger.error(f"Error reading {fname}: {e}")

    summary["total_records"] = total_rows
    summary["districts_covered"] = sorted(list(districts_set))
    summary["commodities_covered"] = sorted(list(commodities_set))
    summary["unparseable_date_count"] = total_unparseable
    summary["duplicates_count"] = total_duplicates
    summary["unit_status_counts"] = unit_counts

    if valid_dates:
        summary["date_min"] = min(valid_dates)
        summary["date_max"] = max(valid_dates)

    return summary


def organize_and_export_city_crop(
    input_dir: str = DEFAULT_INPUT_DIR,
    output_dir: Optional[str] = None,
    write: bool = False
) -> Dict[str, Any]:
    """
    Ingests and reconciles Agmarknet arrivals.
    
    Guarantees:
    - Inputs are strictly read-only (zero moves, deletes, renames).
    - output_dir is validated to be distinct from and not inside input_dir.
    - Default write=False (dry-run). Writes require write=True.
    - Reconciles rows_in = rows_out + duplicates_removed + rejected.
    - Deterministic output: sorted inputs, stable row sort, SHA-256 manifests.
    - Timestamps written strictly to run_log.json, never in hashed outputs or manifest.json.
    - Corrupt files recorded in failed_files, status set to PARTIAL/FAILED.
    """
    if output_dir is None:
        output_dir = DEFAULT_OUTPUT_DIR

    abs_input, abs_output = validate_directories(input_dir, output_dir)

    if not os.path.exists(abs_input) or not os.path.isdir(abs_input):
        raise FileNotFoundError(f"Input directory does not exist: {abs_input}")

    all_entries = sorted(os.listdir(abs_input))
    data_files = []
    excluded_files = []

    for entry in all_entries:
        is_valid, reason = classify_file(entry, abs_input)
        if is_valid:
            data_files.append(entry)
        else:
            excluded_files.append({"file": entry, "reason": reason})

    if not data_files:
        logger.warning(f"No valid data files to process in {abs_input}.")
        return {
            "status": "EMPTY",
            "input_dir": abs_input,
            "output_dir": abs_output,
            "files_found": [],
            "excluded_files": excluded_files,
            "failed_files": [],
            "reconciliation": {
                "total_rows_in": 0,
                "total_rows_out": 0,
                "total_duplicates_removed": 0,
                "total_rejected": 0,
            },
            "exported_files": []
        }

    loaded_dfs = []
    failed_files = []
    file_reconciliations = []

    total_rows_in = 0
    total_duplicates = 0
    total_rejected = 0

    for fname in data_files:
        fpath = os.path.join(abs_input, fname)
        try:
            df = load_arrivals_file(fpath)
            rows_in = len(df)
            total_rows_in += rows_in

            # Deduplication on raw loaded file
            unique_df = df.drop_duplicates()
            duplicates_removed = rows_in - len(unique_df)
            total_duplicates += duplicates_removed

            # Rejected rows: missing critical keys (District, Commodity, or unparseable Arrival_Date)
            rejected_mask = (
                unique_df["Arrival_Date"].isna()
                | unique_df["District"].isna()
                | unique_df["Commodity"].isna()
                | (unique_df["District"].astype(str).str.strip() == "")
                | (unique_df["Commodity"].astype(str).str.strip() == "")
            )
            rejected_count = int(rejected_mask.sum())
            total_rejected += rejected_count

            accepted_df = unique_df[~rejected_mask].copy()
            rows_out = len(accepted_df)

            # Assert mathematical identity per file
            assert rows_in == rows_out + duplicates_removed + rejected_count, (
                f"Reconciliation identity violated in {fname}: "
                f"{rows_in} != {rows_out} + {duplicates_removed} + {rejected_count}"
            )

            file_reconciliations.append({
                "file": fname,
                "sha256": compute_sha256(fpath),
                "rows_in": rows_in,
                "rows_out": rows_out,
                "duplicates_removed": duplicates_removed,
                "rejected": rejected_count,
            })

            if not accepted_df.empty:
                loaded_dfs.append(accepted_df)

        except Exception as e:
            logger.error(f"Failed to process file {fname}: {e}")
            failed_files.append({"file": fname, "error": str(e)})

    # Determine overall status
    if failed_files and loaded_dfs:
        overall_status = "PARTIAL"
    elif failed_files and not loaded_dfs:
        overall_status = "FAILED"
    else:
        overall_status = "SUCCESS"

    if not loaded_dfs:
        return {
            "status": overall_status,
            "input_dir": abs_input,
            "output_dir": abs_output,
            "files_found": data_files,
            "excluded_files": excluded_files,
            "failed_files": failed_files,
            "reconciliation": {
                "total_rows_in": total_rows_in,
                "total_rows_out": 0,
                "total_duplicates_removed": total_duplicates,
                "total_rejected": total_rejected,
            },
            "exported_files": []
        }

    # Combine accepted records
    combined = pd.concat(loaded_dfs, ignore_index=True)

    # Sort columns for deterministic CSV export
    sort_cols = [c for c in ["District", "Commodity", "Market", "Arrival_Date", "Variety", "Grade"] if c in combined.columns]
    if sort_cols:
        combined = combined.sort_values(by=sort_cols).reset_index(drop=True)

    total_rows_out = len(combined)

    # Enforce total reconciliation identity
    assert total_rows_in == total_rows_out + total_duplicates + total_rejected, (
        f"Total reconciliation identity violated: "
        f"{total_rows_in} != {total_rows_out} + {total_duplicates} + {total_rejected}"
    )

    exported_files = []
    output_manifest_entries = {}

    if write:
        os.makedirs(abs_output, exist_ok=True)

        # 1. Export master consolidated CSV
        master_filename = "agmarknet_arrivals_up_consolidated.csv"
        master_path = ensure_path_within_output_dir(os.path.join(abs_output, master_filename), abs_output)
        combined.to_csv(master_path, index=False, encoding="utf-8", lineterminator="\n")
        master_sha = compute_sha256(master_path)
        output_manifest_entries[master_filename] = master_sha
        exported_files.append((master_filename, len(combined)))
        logger.info(f"Exported master consolidated arrivals: {master_path} ({len(combined):,} rows)")

        # 2. Export individual {District}_{Commodity}.csv files
        if "District" in combined.columns and "Commodity" in combined.columns:
            for (dist, comm), group in combined.groupby(["District", "Commodity"]):
                clean_dist = str(dist).strip().replace(" ", "_")
                clean_comm = str(comm).strip().replace(" ", "_")
                pair_filename = f"{clean_dist}_{clean_comm}.csv"
                pair_path = ensure_path_within_output_dir(os.path.join(abs_output, pair_filename), abs_output)
                
                # Deterministic row sort
                if sort_cols:
                    group = group.sort_values(by=[c for c in sort_cols if c in group.columns]).reset_index(drop=True)
                
                group.to_csv(pair_path, index=False, encoding="utf-8", lineterminator="\n")
                pair_sha = compute_sha256(pair_path)
                output_manifest_entries[pair_filename] = pair_sha
                exported_files.append((pair_filename, len(group)))
                logger.info(f"  • Exported {pair_filename}: {len(group):,} rows")

        # 3. Deterministic manifest (NO timestamps to ensure byte-identical reruns)
        manifest_data = {
            "input_files": {
                f["file"]: f["sha256"] for f in file_reconciliations
            },
            "output_files": output_manifest_entries,
            "reconciliation": {
                "total_rows_in": total_rows_in,
                "total_rows_out": total_rows_out,
                "total_duplicates_removed": total_duplicates,
                "total_rejected": total_rejected,
            }
        }
        manifest_path = ensure_path_within_output_dir(os.path.join(abs_output, "manifest.json"), abs_output)
        with open(manifest_path, "w", encoding="utf-8", newline="\n") as mf:
            json.dump(manifest_data, mf, indent=2, sort_keys=True)
            mf.write("\n")

        # 4. Separate run log (holds timestamps and execution metadata)
        run_log_data = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "status": overall_status,
            "input_dir": abs_input,
            "output_dir": abs_output,
            "files_processed_count": len(file_reconciliations),
            "failed_files": failed_files,
            "excluded_files": excluded_files,
            "reconciliation": {
                "total_rows_in": total_rows_in,
                "total_rows_out": total_rows_out,
                "total_duplicates_removed": total_duplicates,
                "total_rejected": total_rejected,
            }
        }
        run_log_path = ensure_path_within_output_dir(os.path.join(abs_output, "run_log.json"), abs_output)
        with open(run_log_path, "w", encoding="utf-8", newline="\n") as rf:
            json.dump(run_log_data, rf, indent=2, sort_keys=True)
            rf.write("\n")

    return {
        "status": overall_status,
        "input_dir": abs_input,
        "output_dir": abs_output,
        "is_dry_run": not write,
        "files_found": data_files,
        "excluded_files": excluded_files,
        "failed_files": failed_files,
        "reconciliation": {
            "total_rows_in": total_rows_in,
            "total_rows_out": total_rows_out,
            "total_duplicates_removed": total_duplicates,
            "total_rejected": total_rejected,
            "file_details": file_reconciliations,
        },
        "exported_files": exported_files
    }


def main():
    parser = argparse.ArgumentParser(
        description="Deterministic Agmarknet Arrivals Ingestion & Audit Engine"
    )
    parser.add_argument("--input-dir", default=DEFAULT_INPUT_DIR, help="Input directory containing raw arrivals data")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Output directory for interim arrivals")
    parser.add_argument("--write", action="store_true", help="Perform actual writes (default is dry-run)")
    args = parser.parse_args()

    logger.info("Executing Agmarknet Arrivals Audit & Ingestion...")
    audit_summary = audit_arrivals_folder(args.input_dir)
    res = organize_and_export_city_crop(input_dir=args.input_dir, output_dir=args.output_dir, write=args.write)

    print("\n" + "=" * 80)
    print("AGMARKNET ARRIVALS AUDIT & INGESTION REPORT")
    print("=" * 80)
    print(f"Input Directory  : {args.input_dir}")
    print(f"Output Directory : {args.output_dir} (write={args.write})")
    print(f"Audit Status     : {audit_summary['status']}")
    print(f"Ingest Status    : {res['status']}")
    print(f"Files Discovered : {len(res['files_found'])} valid raw input(s)")
    print(f"Files Excluded   : {len(res['excluded_files'])} generated / system file(s)")
    print(f"Files Failed     : {len(res['failed_files'])} unreadable file(s)")
    print("-" * 80)
    print("RECONCILIATION ACCOUNTING:")
    reconc = res["reconciliation"]
    print(f"  • Rows Read (In)     : {reconc['total_rows_in']:,}")
    print(f"  • Rows Exported (Out): {reconc['total_rows_out']:,}")
    print(f"  • Duplicates Removed : {reconc['total_duplicates_removed']:,}")
    print(f"  • Rows Rejected      : {reconc['total_rejected']:,}")
    print(f"  • Identity Verified  : {reconc['total_rows_in']} == {reconc['total_rows_out']} + {reconc['total_duplicates_removed']} + {reconc['total_rejected']}")
    print("-" * 80)
    print(f"Districts Covered: {', '.join(audit_summary['districts_covered']) if audit_summary['districts_covered'] else 'None'}")
    print(f"Crops Covered    : {', '.join(audit_summary['commodities_covered']) if audit_summary['commodities_covered'] else 'None'}")
    if audit_summary.get("date_min"):
        print(f"Timeline Covered : {audit_summary['date_min']} to {audit_summary['date_max']}")
    print(f"Unit Breakdown   : {audit_summary['unit_status_counts']}")
    print(f"Unparseable Dates: {audit_summary['unparseable_date_count']:,}")
    print("=" * 80)

    if res["failed_files"] or res["status"] in ["PARTIAL", "FAILED"]:
        logger.error(f"Execution completed with failures: {res['failed_files']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
