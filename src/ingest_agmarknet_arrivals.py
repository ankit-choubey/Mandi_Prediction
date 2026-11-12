"""
AGMARKNET Daily Price & Arrival Report Ingestion Engine
APMC Mandi Market Intelligence System
Author: Track D / Data Operations

Deterministic, non-destructive, and immutable arrivals ingestion engine.
Enforces strict separation of input_dirs and output_dir, immutability of raw inputs,
explicit unit resolution, alias collision detection, raw string preservation with explicit standardization,
cross-file exact deduplication and conflict partitioning, independent disk reconciliation,
and deterministic CSV export with SHA-256 manifests.

Required Invariants:
1. Inputs are read-only: never move, delete, rename, or modify input files.
2. Strict directory separation: output_dir default data/interim/arrivals/; rejects
   output_dir inside or equal to any input_dir; rejects writes escaping output_dir.
   Uses os.path.realpath to guard against symlink circumvention.
3. No hidden global write paths: all paths derive from function arguments.
4. Input discovery excludes generated master consolidated files, {District}_{Commodity}.csv
   outputs, conflicts.csv, and subfolders (e.g. raw_downloads/).
5. Dry-run is default; writes require explicit flag.
6. audit_arrivals_folder is strictly read-only; missing directory returns MISSING_DIR;
   reports unreadable files and PARTIAL status without swallowing errors.
7. Units: exact set match against normalized string (no substring matching). Generic/unknown
   units are marked UNVERIFIED with Arrivals_Tonnes empty (NaN).
8. Dates: strict explicit formats; datetime/Timestamp cells handled before string casting;
   unparseable dates counted, never silently dropped.
9. Missing values & Standardization: uses pandas string dtype (no astype(str) turning NaN to 'nan').
   Preserves District_Raw and Commodity_Raw; creates District_Std and Commodity_Std via explicit
   case-insensitive mapping; unmapped values remain as-is with mapped=False.
10. Cross-file deduplication & conflict partitioning:
    rows_in = rows_out + duplicates + conflicts + rejected
11. Independent reconciliation: re-reads disk outputs after write to verify counts with explicit raises.
12. Failures: corrupt or colliding files recorded in failed_files, status PARTIAL/FAILED, CLI exit non-zero.
"""

import os
import sys
import json
import hashlib
import logging
import argparse
from datetime import datetime, timezone, date
from typing import List, Dict, Tuple, Optional, Any, Union
import pandas as pd
import numpy as np

# Reuse DISTRICT_NORMALIZATION from data_pipeline
try:
    from src.data_pipeline import DISTRICT_NORMALIZATION
except ImportError:
    DISTRICT_NORMALIZATION = {
        "gaziabaad": "Ghaziabad",
        "ghaziabad": "Ghaziabad",
        "gaziabad": "Ghaziabad",
        "jhansi": "Jhansi",
        "kanpur": "Kanpur",
        "kanpur nagar": "Kanpur",
        "lukhnow": "Lucknow",
        "lucknow": "Lucknow",
        "unnao": "Unnao"
    }

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
logger = logging.getLogger("agmarknet_ingest")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_INPUT_DIR = os.path.join(REPO_ROOT, "data", "raw", "arrivals", "historical")
DEFAULT_OUTPUT_DIR = os.path.join(REPO_ROOT, "data", "interim", "arrivals")
ARRIVALS_DIR = DEFAULT_INPUT_DIR

TARGET_DISTRICTS = ["Ghaziabad", "Jhansi", "Kanpur", "Lucknow", "Unnao"]
TARGET_CROPS = ["Potato", "Onion", "Tomato", "Wheat", "Rice", "Paddy"]

EXPLICIT_DATE_FORMATS = ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"]

# Explicit commodity spelling normalization
COMMODITY_NORMALIZATION: Dict[str, str] = {
    "potato": "Potato",
    "potatoes": "Potato",
    "onion": "Onion",
    "onions": "Onion",
    "tomato": "Tomato",
    "tomatoes": "Tomato",
    "wheat": "Wheat",
    "rice": "Rice",
    "paddy": "Paddy",
    "paddy(dhan)": "Paddy",
}

# Exact unit sets (no substring matching permitted)
TONNE_UNITS = {"tonne", "tonnes", "ton", "tons", "mt", "metric tonne", "metric tonnes"}
QUINTAL_UNITS = {"quintal", "quintals", "qtl", "qtls"}

# Natural key definition for arrivals series identity
NATURAL_KEY = ["District_Std", "Market", "Commodity_Std", "Variety", "Grade", "Arrival_Date"]

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


class AliasCollisionError(ValueError):
    """Raised when multiple source columns in a file map to the same canonical alias."""
    pass


def compute_sha256(filepath: str) -> str:
    """Compute the SHA-256 hexadecimal digest of a file in binary mode."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def validate_directories(input_dirs: Union[str, List[str]], output_dir: str) -> Tuple[List[str], str]:
    """
    Validates that output_dir is not equal to, inside, or containing any input_dir.
    Resolves symlinks via os.path.realpath.
    """
    if isinstance(input_dirs, str):
        input_dirs = [input_dirs]

    real_inputs = [os.path.realpath(d) for d in input_dirs]
    real_output = os.path.realpath(output_dir)

    for inp in real_inputs:
        if inp == real_output:
            raise ValueError(
                f"output_dir ({real_output}) cannot be equal to input_dir ({inp})"
            )

        try:
            common = os.path.commonpath([inp, real_output])
        except ValueError:
            common = None

        if common == inp:
            raise ValueError(
                f"output_dir ({real_output}) cannot be inside input_dir ({inp})"
            )
        if common == real_output:
            raise ValueError(
                f"input_dir ({inp}) cannot be inside output_dir ({real_output})"
            )

    return real_inputs, real_output


def ensure_path_within_output_dir(target_path: str, output_dir: str) -> str:
    """Rejects any write path that falls outside designated output directory."""
    real_target = os.path.realpath(target_path)
    real_output = os.path.realpath(output_dir)
    try:
        common = os.path.commonpath([real_output, real_target])
    except ValueError:
        common = None

    if common != real_output:
        raise ValueError(
            f"Write path ({real_target}) escapes designated output directory ({real_output})"
        )
    return real_target


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

    if filename in ["manifest.json", "run_log.json", "checksums.sha256", "existing_file_inventory.csv", "conflicts.csv"]:
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
            is_dist = p0 in TARGET_DISTRICTS or any(p0.lower() == d.lower() for d in TARGET_DISTRICTS)
            is_crop = p1 in TARGET_CROPS or any(p1.lower() == c.lower() for c in TARGET_CROPS)
            if is_dist and is_crop:
                return False, "generated_city_crop_output"

    if not filename.lower().endswith((".csv", ".xlsx", ".xls")):
        return False, "unsupported_file_extension"

    return True, "valid_raw_input"


def discover_input_files(input_dirs: Union[str, List[str]]) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """
    Unified discovery across one or multiple input directories.
    Returns (valid_files, excluded_files) where each item has filename, full_path, source_dir.
    """
    if isinstance(input_dirs, str):
        input_dirs = [input_dirs]

    valid_files: List[Dict[str, str]] = []
    excluded_files: List[Dict[str, str]] = []

    for d in input_dirs:
        real_d = os.path.realpath(d)
        if not os.path.exists(real_d) or not os.path.isdir(real_d):
            continue

        entries = sorted(os.listdir(real_d))
        for entry in entries:
            is_valid, reason = classify_file(entry, real_d)
            item = {
                "file": entry,
                "full_path": os.path.join(real_d, entry),
                "source_dir": real_d,
                "reason": reason
            }
            if is_valid:
                valid_files.append(item)
            else:
                excluded_files.append(item)

    # Sort discovered valid files deterministically
    valid_files.sort(key=lambda x: (x["source_dir"], x["file"]))
    return valid_files, excluded_files


def parse_explicit_dates(date_series: pd.Series) -> Tuple[pd.Series, pd.Series, int]:
    """
    Parses dates using strict explicit formats only.
    Handles datetime / Timestamp / date objects directly before any string cast.
    Formats tried for strings: %d/%m/%Y, %d-%m-%Y, %Y-%m-%d.
    Does NOT guess day/month order.
    Returns (raw_dates_series, parsed_iso_series, unparseable_count).
    """
    raw_dates = pd.Series(pd.NA, index=date_series.index, dtype="string")
    iso_dates = pd.Series(pd.NA, index=date_series.index, dtype="string")
    unparseable_count = 0

    for idx, val in date_series.items():
        if pd.isna(val) or val is None or val == "":
            continue

        if isinstance(val, (datetime, pd.Timestamp, date)):
            iso_str = val.strftime("%Y-%m-%d")
            raw_dates.loc[idx] = iso_str
            iso_dates.loc[idx] = iso_str
            continue

        s_val = str(val).strip()
        if s_val.lower() in ["nan", "<na>", "none", "nat", ""]:
            continue

        raw_dates.loc[idx] = s_val
        parsed_iso = None
        for fmt in EXPLICIT_DATE_FORMATS:
            try:
                dt = datetime.strptime(s_val, fmt)
                parsed_iso = dt.strftime("%Y-%m-%d")
                break
            except (ValueError, TypeError):
                continue

        if parsed_iso:
            iso_dates.loc[idx] = parsed_iso
        else:
            unparseable_count += 1

    return raw_dates, iso_dates, unparseable_count


def load_arrivals_file(file_path: str) -> pd.DataFrame:
    """
    Load and normalize an Agmarknet arrivals file (CSV or Excel).
    Inputs are read-only: this function never modifies or writes to the input file.
    
    Guarantees:
    - Never uses astype(str) on District or Commodity; uses pandas string dtype.
    - Preserves District_Raw and Commodity_Raw (stripped only, source casing preserved).
    - Maps District_Std and Commodity_Std using explicit case-insensitive dictionaries.
    - Tracks District_Mapped and Commodity_Mapped flags without title-casing into identity.
    - Detects alias collisions and raises AliasCollisionError.
    - Unit matching is exact against known sets (no substring matching).
    - Explicit date parsing handling datetime/Timestamp cells before string conversion.
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

    # Alias collision detection
    seen_canonical: Dict[str, str] = {}
    normalized_cols: Dict[str, str] = {}
    cols_to_drop = []
    for c in df.columns:
        c_clean = str(c).strip().lower()
        canonical = COLUMN_ALIASES.get(c_clean, str(c).strip())
        if canonical in seen_canonical:
            prev_c = seen_canonical[canonical]
            # If two columns have identical non-empty series (e.g. redundant state & state_name API export), drop duplicate
            if df[c].equals(df[prev_c]):
                logger.warning(
                    f"Source column '{c}' is identical to '{prev_c}' (both map to '{canonical}'); dropping redundant column '{c}'."
                )
                cols_to_drop.append(c)
                continue
            raise AliasCollisionError(
                f"Alias collision in source columns: both '{prev_c}' and '{c}' map to canonical alias '{canonical}'"
            )
        seen_canonical[canonical] = str(c)
        normalized_cols[c] = canonical

    if cols_to_drop:
        df.drop(columns=cols_to_drop, inplace=True)

    # Detect original arrival quantity column and unit hint before alias mapping
    orig_arrival_col = None
    unit_hint = "UNVERIFIED"

    for c in df.columns:
        c_clean = str(c).strip().lower()
        if c_clean in ["arrivals (tonnes)", "arrivals(in tonnes)", "arrivals (tonne)", "arrivals_tonnes"]:
            orig_arrival_col = c
            unit_hint = "Tonnes"
            break
        elif c_clean in ["arrivals (qtl)", "arrivals (in qtl)", "arrivals (quintal)", "arrivals_qtl"]:
            orig_arrival_col = c
            unit_hint = "Quintals"
            break
        elif c_clean in ["arrival quantity", "arrivals", "qty"]:
            orig_arrival_col = c
            unit_hint = "GENERIC"
            break

    df.rename(columns=normalized_cols, inplace=True)

    # Missing values and Standardization: String dtype without astype(str)
    if "District" in df.columns:
        df["District_Raw"] = df["District"].astype("string").str.strip()
    else:
        df["District_Raw"] = pd.Series(pd.NA, index=df.index, dtype="string")

    if "Commodity" in df.columns:
        df["Commodity_Raw"] = df["Commodity"].astype("string").str.strip()
    else:
        df["Commodity_Raw"] = pd.Series(pd.NA, index=df.index, dtype="string")

    def standardize_district(val):
        if pd.isna(val) or val == "":
            return pd.NA, False
        s_val = str(val).strip()
        val_lower = s_val.lower()
        if val_lower in DISTRICT_NORMALIZATION:
            return DISTRICT_NORMALIZATION[val_lower], True
        return s_val, False

    def standardize_commodity(val):
        if pd.isna(val) or val == "":
            return pd.NA, False
        s_val = str(val).strip()
        val_lower = s_val.lower()
        if val_lower in COMMODITY_NORMALIZATION:
            return COMMODITY_NORMALIZATION[val_lower], True
        return s_val, False

    dist_res = [standardize_district(v) for v in df["District_Raw"]]
    df["District_Std"] = pd.Series([r[0] for r in dist_res], index=df.index, dtype="string")
    df["District_Mapped"] = pd.Series([r[1] for r in dist_res], index=df.index, dtype="boolean")

    comm_res = [standardize_commodity(v) for v in df["Commodity_Raw"]]
    df["Commodity_Std"] = pd.Series([r[0] for r in comm_res], index=df.index, dtype="string")
    df["Commodity_Mapped"] = pd.Series([r[1] for r in comm_res], index=df.index, dtype="boolean")

    # Set canonical District and Commodity to standardized values
    df["District"] = df["District_Std"]
    df["Commodity"] = df["Commodity_Std"]

    # Market, Variety, Grade string cleaning
    for col in ["Market", "Variety", "Grade"]:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()
        else:
            df[col] = pd.Series("", index=df.index, dtype="string")

    # Unit Resolution (Exact set membership, no substring matching)
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
            # Generic quantity: exact set match against Arrival_Unit if present
            if "Arrival_Unit" in df.columns:
                def resolve_unit_exact(u_val, q_val):
                    if pd.isna(u_val):
                        return "UNVERIFIED", np.nan
                    norm_u = str(u_val).strip().lower()
                    if norm_u in TONNE_UNITS:
                        return "Tonnes", q_val
                    elif norm_u in QUINTAL_UNITS:
                        return "Quintals", q_val / 10.0 if pd.notna(q_val) else np.nan
                    return "UNVERIFIED", np.nan

                unit_results = [resolve_unit_exact(u, q) for u, q in zip(df["Arrival_Unit"], raw_vals)]
                df["Arrival_Unit_Source"] = pd.Series([r[0] for r in unit_results], index=df.index, dtype="string")
                df["Arrivals_Tonnes"] = pd.Series([r[1] for r in unit_results], index=df.index, dtype="float")
            else:
                df["Arrival_Unit_Source"] = pd.Series("UNVERIFIED", index=df.index, dtype="string")
                df["Arrivals_Tonnes"] = pd.Series(np.nan, index=df.index, dtype="float")
    else:
        df["Arrivals_Raw"] = pd.Series(np.nan, index=df.index, dtype="float")
        df["Arrival_Unit_Source"] = pd.Series("UNVERIFIED", index=df.index, dtype="string")
        df["Arrivals_Tonnes"] = pd.Series(np.nan, index=df.index, dtype="float")

    # Date Resolution
    unparseable_dates = 0
    if "Arrival_Date" in df.columns:
        raw_dates, iso_dates, unparseable_dates = parse_explicit_dates(df["Arrival_Date"])
        df["Arrival_Date_Raw"] = raw_dates
        df["Arrival_Date"] = iso_dates
    else:
        df["Arrival_Date_Raw"] = pd.Series(pd.NA, index=df.index, dtype="string")
        df["Arrival_Date"] = pd.Series(pd.NA, index=df.index, dtype="string")

    df.attrs["unparseable_date_count"] = unparseable_dates
    return df


def classify_row_rejections(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, int], pd.DataFrame]:
    """
    Evaluates rows against required arrival fields.
    Reasons:
      - missing_district: District_Std is NA or empty
      - missing_commodity: Commodity_Std is NA or empty
      - unparseable_date: Arrival_Date is NA or empty
      - missing_quantity: Arrivals_Raw is NA (price-only rows are not arrivals)
    Returns (accepted_df, reject_reasons_dict, rejected_df)
    """
    reasons = []
    for _, row in df.iterrows():
        if pd.isna(row.get("District_Std")) or str(row.get("District_Std")).strip() == "":
            reasons.append("missing_district")
        elif pd.isna(row.get("Commodity_Std")) or str(row.get("Commodity_Std")).strip() == "":
            reasons.append("missing_commodity")
        elif pd.isna(row.get("Arrival_Date")) or str(row.get("Arrival_Date")).strip() == "":
            reasons.append("unparseable_date")
        elif pd.isna(row.get("Arrivals_Raw")):
            reasons.append("missing_quantity")
        else:
            reasons.append("ACCEPTED")

    reasons_series = pd.Series(reasons, index=df.index)
    accepted_mask = reasons_series == "ACCEPTED"
    accepted_df = df[accepted_mask].copy()

    rejected_df = df[~accepted_mask].copy()
    rejected_df["rejection_reason"] = reasons_series[~accepted_mask]

    counts = {
        "missing_district": int((reasons_series == "missing_district").sum()),
        "missing_commodity": int((reasons_series == "missing_commodity").sum()),
        "unparseable_date": int((reasons_series == "unparseable_date").sum()),
        "missing_quantity": int((reasons_series == "missing_quantity").sum()),
    }
    return accepted_df, counts, rejected_df


def audit_arrivals_folder(folder_path: Union[str, List[str]] = DEFAULT_INPUT_DIR) -> Dict[str, Any]:
    """
    Strictly read-only inspection of folder_path.
    Never creates directories and never modifies files.
    If folder does not exist, returns status MISSING_DIR.
    Reports failed files and PARTIAL status without swallowing errors.
    """
    if isinstance(folder_path, str):
        folder_paths = [folder_path]
    else:
        folder_paths = folder_path

    # Check existence
    existing_paths = [p for p in folder_paths if os.path.exists(os.path.realpath(p)) and os.path.isdir(os.path.realpath(p))]
    if not existing_paths:
        return {
            "folder_path": folder_paths[0] if folder_paths else "",
            "status": "MISSING_DIR",
            "files_count": 0,
            "files_found": [],
            "excluded_files": [],
            "failed_files": [],
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

    valid_files, excluded_files = discover_input_files(existing_paths)

    summary = {
        "folder_path": existing_paths[0] if len(existing_paths) == 1 else existing_paths,
        "status": "EMPTY" if not valid_files else "POPULATED",
        "files_count": len(valid_files),
        "files_found": [f["file"] for f in valid_files],
        "excluded_files": excluded_files,
        "failed_files": [],
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

    if not valid_files:
        return summary

    total_rows = 0
    total_unparseable = 0
    total_duplicates = 0
    valid_dates = []
    districts_set = set()
    commodities_set = set()
    unit_counts = {"Tonnes": 0, "Quintals": 0, "UNVERIFIED": 0}
    failed_files = []

    for item in valid_files:
        fpath = item["full_path"]
        fname = item["file"]
        try:
            df = load_arrivals_file(fpath)
            total_rows += len(df)
            total_unparseable += df.attrs.get("unparseable_date_count", 0)
            total_duplicates += int(df.duplicated().sum())

            if "District_Std" in df.columns:
                for d in df["District_Std"].dropna().unique():
                    if str(d).strip():
                        districts_set.add(str(d).strip())
            if "Commodity_Std" in df.columns:
                for c in df["Commodity_Std"].dropna().unique():
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
            logger.error(f"Error auditing {fname}: {e}")
            failed_files.append({"file": fname, "error": str(e)})

    summary["total_records"] = total_rows
    summary["districts_covered"] = sorted(list(districts_set))
    summary["commodities_covered"] = sorted(list(commodities_set))
    summary["unparseable_date_count"] = total_unparseable
    summary["duplicates_count"] = total_duplicates
    summary["unit_status_counts"] = unit_counts
    summary["failed_files"] = failed_files

    if failed_files:
        summary["status"] = "PARTIAL" if total_rows > 0 else "FAILED"

    if valid_dates:
        summary["date_min"] = min(valid_dates)
        summary["date_max"] = max(valid_dates)

    return summary


def organize_and_export_city_crop(
    input_dir: Union[str, List[str]] = DEFAULT_INPUT_DIR,
    output_dir: Optional[str] = None,
    write: bool = False
) -> Dict[str, Any]:
    """
    Ingests, standardizes, deduplicates, and reconciles Agmarknet arrivals.
    
    Guarantees:
    - Inputs are strictly read-only (zero moves, deletes, renames).
    - output_dir is validated to be distinct from and not inside any input_dir.
    - Default write=False (dry-run). Writes require write=True.
    - Preserves District_Raw and Commodity_Raw; maps District_Std and Commodity_Std.
    - Reconciles rows_in = rows_out + duplicates + conflicts + rejected.
    - Exact cross-file duplicates kept once; conflicts partitioned to conflicts.csv.
    - Independent disk read-back verifies file integrity with explicit raises.
    - Deterministic output: sorted inputs, stable row sort, SHA-256 manifests.
    - Timestamps written strictly to run_log.json, never in hashed outputs or manifest.json.
    - Corrupt files or alias collisions recorded in failed_files, status set to PARTIAL/FAILED.
    """
    if output_dir is None:
        output_dir = DEFAULT_OUTPUT_DIR

    real_inputs, real_output = validate_directories(input_dir, output_dir)

    valid_files, excluded_files = discover_input_files(real_inputs)

    if not valid_files:
        logger.warning(f"No valid data files to process in {real_inputs}.")
        return {
            "status": "EMPTY",
            "input_dirs": real_inputs,
            "output_dir": real_output,
            "files_found": [],
            "excluded_files": excluded_files,
            "failed_files": [],
            "reconciliation": {
                "total_rows_in": 0,
                "total_rows_out": 0,
                "total_duplicates": 0,
                "total_conflicts": 0,
                "total_rejected": 0,
                "rejection_reasons": {
                    "missing_district": 0,
                    "missing_commodity": 0,
                    "unparseable_date": 0,
                    "missing_quantity": 0
                }
            },
            "exported_files": []
        }

    loaded_dfs = []
    failed_files = []
    file_reconciliations = []

    total_rows_in = 0
    total_within_file_dups = 0
    total_rejected = 0
    total_rejection_reasons = {
        "missing_district": 0,
        "missing_commodity": 0,
        "unparseable_date": 0,
        "missing_quantity": 0
    }

    for item in valid_files:
        fpath = item["full_path"]
        fname = item["file"]
        sdir = item["source_dir"]
        try:
            df = load_arrivals_file(fpath)
            rows_in = len(df)
            total_rows_in += rows_in

            # Deduplication on raw loaded file
            unique_raw_df = df.drop_duplicates()
            dups_removed = rows_in - len(unique_raw_df)
            total_within_file_dups += dups_removed

            # Classify rejections
            accepted_df, reject_counts, _ = classify_row_rejections(unique_raw_df)
            file_rej = len(unique_raw_df) - len(accepted_df)
            total_rejected += file_rej
            for r_k, r_v in reject_counts.items():
                total_rejection_reasons[r_k] += r_v

            accepted_count = len(accepted_df)

            assert rows_in == accepted_count + dups_removed + file_rej, (
                f"File reconciliation identity violated in {fname}: "
                f"{rows_in} != {accepted_count} + {dups_removed} + {file_rej}"
            )

            file_reconciliations.append({
                "file": fname,
                "source_dir": sdir,
                "sha256": compute_sha256(fpath),
                "rows_in": rows_in,
                "accepted_pre_merge": accepted_count,
                "duplicates_removed": dups_removed,
                "rejected": file_rej,
                "rejection_reasons": reject_counts
            })

            if not accepted_df.empty:
                accepted_df["_source_file"] = fname
                loaded_dfs.append(accepted_df)

        except Exception as e:
            logger.error(f"Failed to process file {fname}: {e}")
            failed_files.append({"file": fname, "error": str(e), "source_dir": sdir})

    # Overall status determination
    if failed_files and loaded_dfs:
        overall_status = "PARTIAL"
    elif failed_files and not loaded_dfs:
        overall_status = "FAILED"
    else:
        overall_status = "SUCCESS"

    if not loaded_dfs:
        return {
            "status": overall_status,
            "input_dirs": real_inputs,
            "output_dir": real_output,
            "files_found": [f["file"] for f in valid_files],
            "excluded_files": excluded_files,
            "failed_files": failed_files,
            "reconciliation": {
                "total_rows_in": total_rows_in,
                "total_rows_out": 0,
                "total_duplicates": total_within_file_dups,
                "total_conflicts": 0,
                "total_rejected": total_rejected,
                "rejection_reasons": total_rejection_reasons
            },
            "exported_files": []
        }

    # Combine accepted records across files
    combined_raw = pd.concat(loaded_dfs, ignore_index=True)

    # Cross-file deduplication and conflict partitioning
    # Group by natural key
    value_cols = [c for c in ["Arrivals_Raw", "Min_Price", "Max_Price", "Modal_Price", "Price_Unit", "Arrival_Unit_Source"] if c in combined_raw.columns]

    final_accepted_rows = []
    conflict_rows = []
    cross_file_duplicates = 0

    # Build natural key string tuple for robust grouping without NA issues
    key_tuples = list(zip(
        combined_raw["District_Std"].fillna("").astype(str),
        combined_raw["Market"].fillna("").astype(str),
        combined_raw["Commodity_Std"].fillna("").astype(str),
        combined_raw["Variety"].fillna("").astype(str),
        combined_raw["Grade"].fillna("").astype(str),
        combined_raw["Arrival_Date"].fillna("").astype(str)
    ))
    combined_raw["_natural_key_tuple"] = key_tuples

    for _, group in combined_raw.groupby("_natural_key_tuple"):
        if len(group) == 1:
            final_accepted_rows.append(group)
        else:
            # Check if all value columns are identical across rows
            unique_values = group[value_cols].drop_duplicates()
            if len(unique_values) == 1:
                # Exact duplicates across files: keep 1, count the rest
                final_accepted_rows.append(group.iloc[[0]])
                cross_file_duplicates += (len(group) - 1)
            else:
                # Conflicting records on same natural key: partition all to conflicts
                conflict_rows.append(group)

    if final_accepted_rows:
        accepted_df_final = pd.concat(final_accepted_rows, ignore_index=True).drop(columns=["_natural_key_tuple"])
    else:
        accepted_df_final = pd.DataFrame(columns=[c for c in combined_raw.columns if c != "_natural_key_tuple"])

    if conflict_rows:
        conflicts_df = pd.concat(conflict_rows, ignore_index=True).drop(columns=["_natural_key_tuple"])
    else:
        conflicts_df = pd.DataFrame(columns=[c for c in combined_raw.columns if c != "_natural_key_tuple"])

    total_duplicates = total_within_file_dups + cross_file_duplicates
    total_conflicts = len(conflicts_df)
    total_rows_out = len(accepted_df_final)

    # Master identity verification
    assert total_rows_in == total_rows_out + total_duplicates + total_conflicts + total_rejected, (
        f"Master reconciliation identity failed: {total_rows_in} != "
        f"{total_rows_out} (out) + {total_duplicates} (dups) + {total_conflicts} (conflicts) + {total_rejected} (rej)"
    )

    # Sort columns for deterministic CSV export
    sort_cols = [c for c in ["District_Std", "Commodity_Std", "Market", "Arrival_Date", "Variety", "Grade"] if c in accepted_df_final.columns]
    if sort_cols and not accepted_df_final.empty:
        accepted_df_final = accepted_df_final.sort_values(by=sort_cols).reset_index(drop=True)

    exported_files = []
    output_manifest_entries = {}

    if write:
        os.makedirs(real_output, exist_ok=True)

        # 1. Export master consolidated CSV
        master_filename = "agmarknet_arrivals_up_consolidated.csv"
        master_path = ensure_path_within_output_dir(os.path.join(real_output, master_filename), real_output)
        clean_master = accepted_df_final.drop(columns=["_source_file"], errors="ignore")
        clean_master.to_csv(master_path, index=False, encoding="utf-8", lineterminator="\n")
        output_manifest_entries[master_filename] = compute_sha256(master_path)
        exported_files.append((master_filename, len(clean_master)))

        # 2. Export individual {District}_{Commodity}.csv files
        pair_paths = []
        if "District_Std" in accepted_df_final.columns and "Commodity_Std" in accepted_df_final.columns:
            for (dist, comm), group in accepted_df_final.groupby(["District_Std", "Commodity_Std"]):
                clean_dist = str(dist).strip().replace(" ", "_")
                clean_comm = str(comm).strip().replace(" ", "_")
                pair_filename = f"{clean_dist}_{clean_comm}.csv"
                pair_path = ensure_path_within_output_dir(os.path.join(real_output, pair_filename), real_output)

                clean_group = group.drop(columns=["_source_file"], errors="ignore")
                if sort_cols:
                    clean_group = clean_group.sort_values(by=[c for c in sort_cols if c in clean_group.columns]).reset_index(drop=True)

                clean_group.to_csv(pair_path, index=False, encoding="utf-8", lineterminator="\n")
                output_manifest_entries[pair_filename] = compute_sha256(pair_path)
                exported_files.append((pair_filename, len(clean_group)))
                pair_paths.append(pair_path)

        # 3. Export conflicts.csv if conflicts exist
        conflicts_filename = "conflicts.csv"
        conflicts_path = ensure_path_within_output_dir(os.path.join(real_output, conflicts_filename), real_output)
        if total_conflicts > 0:
            conflicts_df.to_csv(conflicts_path, index=False, encoding="utf-8", lineterminator="\n")
            output_manifest_entries[conflicts_filename] = compute_sha256(conflicts_path)
            exported_files.append((conflicts_filename, total_conflicts))

        # 4. Independent Reconciliation Check (Re-reading from disk)
        re_read_master = pd.read_csv(master_path, low_memory=False)
        if len(re_read_master) != total_rows_out:
            raise ValueError(
                f"Independent reconciliation failed: master has {len(re_read_master)} rows, expected {total_rows_out}"
            )

        if pair_paths:
            pair_row_sum = sum(len(pd.read_csv(p, low_memory=False)) for p in pair_paths)
            if pair_row_sum != total_rows_out:
                raise ValueError(
                    f"Independent reconciliation failed: city-crop files sum to {pair_row_sum} rows, expected {total_rows_out}"
                )

        if total_conflicts > 0 and os.path.exists(conflicts_path):
            re_read_conflicts = pd.read_csv(conflicts_path, low_memory=False)
            if len(re_read_conflicts) != total_conflicts:
                raise ValueError(
                    f"Independent reconciliation failed: conflicts has {len(re_read_conflicts)} rows, expected {total_conflicts}"
                )

        # 5. Deterministic manifest.json (NO timestamps)
        manifest_data = {
            "input_files": {
                f["file"]: {
                    "sha256": f["sha256"],
                    "source_dir": f["source_dir"]
                } for f in file_reconciliations
            },
            "output_files": output_manifest_entries,
            "reconciliation": {
                "total_rows_in": total_rows_in,
                "total_rows_out": total_rows_out,
                "total_duplicates": total_duplicates,
                "total_conflicts": total_conflicts,
                "total_rejected": total_rejected,
                "rejection_reasons": total_rejection_reasons
            }
        }
        manifest_path = ensure_path_within_output_dir(os.path.join(real_output, "manifest.json"), real_output)
        with open(manifest_path, "w", encoding="utf-8", newline="\n") as mf:
            json.dump(manifest_data, mf, indent=2, sort_keys=True)
            mf.write("\n")

        # 6. Separate run_log.json (records runtime metadata and timestamps)
        run_log_data = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "status": overall_status,
            "input_dirs": real_inputs,
            "output_dir": real_output,
            "files_processed_count": len(file_reconciliations),
            "failed_files": failed_files,
            "excluded_files": excluded_files,
            "reconciliation": {
                "total_rows_in": total_rows_in,
                "total_rows_out": total_rows_out,
                "total_duplicates": total_duplicates,
                "total_conflicts": total_conflicts,
                "total_rejected": total_rejected,
                "rejection_reasons": total_rejection_reasons
            }
        }
        run_log_path = ensure_path_within_output_dir(os.path.join(real_output, "run_log.json"), real_output)
        with open(run_log_path, "w", encoding="utf-8", newline="\n") as rf:
            json.dump(run_log_data, rf, indent=2, sort_keys=True)
            rf.write("\n")

    return {
        "status": overall_status,
        "input_dirs": real_inputs,
        "output_dir": real_output,
        "is_dry_run": not write,
        "files_found": [f["file"] for f in valid_files],
        "excluded_files": excluded_files,
        "failed_files": failed_files,
        "reconciliation": {
            "total_rows_in": total_rows_in,
            "total_rows_out": total_rows_out,
            "total_duplicates": total_duplicates,
            "total_conflicts": total_conflicts,
            "total_rejected": total_rejected,
            "rejection_reasons": total_rejection_reasons,
            "file_details": file_reconciliations,
        },
        "exported_files": exported_files
    }


def main():
    parser = argparse.ArgumentParser(
        description="Deterministic Agmarknet Arrivals Ingestion & Audit Engine"
    )
    parser.add_argument("--input-dir", action="append", default=None, help="Input directory containing raw arrivals data (can be passed multiple times)")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Output directory for interim arrivals")
    parser.add_argument("--write", action="store_true", help="Perform actual writes (default is dry-run)")
    args = parser.parse_args()

    input_dirs = args.input_dir if args.input_dir is not None else [DEFAULT_INPUT_DIR]

    logger.info("Executing Agmarknet Arrivals Audit & Ingestion...")
    audit_summary = audit_arrivals_folder(input_dirs)
    res = organize_and_export_city_crop(input_dir=input_dirs, output_dir=args.output_dir, write=args.write)

    print("\n" + "=" * 80)
    print("AGMARKNET ARRIVALS AUDIT & INGESTION REPORT")
    print("=" * 80)
    print(f"Input Directories: {', '.join(res['input_dirs'])}")
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
    print(f"  • Duplicates Removed : {reconc['total_duplicates']:,}")
    print(f"  • Conflicts Recorded : {reconc['total_conflicts']:,}")
    print(f"  • Rows Rejected      : {reconc['total_rejected']:,}")
    print(f"    - Missing District : {reconc['rejection_reasons']['missing_district']:,}")
    print(f"    - Missing Commodity: {reconc['rejection_reasons']['missing_commodity']:,}")
    print(f"    - Unparseable Date : {reconc['rejection_reasons']['unparseable_date']:,}")
    print(f"    - Missing Quantity : {reconc['rejection_reasons']['missing_quantity']:,}")
    print(f"  • Identity Verified  : {reconc['total_rows_in']} == {reconc['total_rows_out']} + {reconc['total_duplicates']} + {reconc['total_conflicts']} + {reconc['total_rejected']}")
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
