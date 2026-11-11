"""
AGMARKNET Daily Price & Arrival Report Ingestion Engine
APMC Mandi Market Intelligence System
Author: Om Awasthi (Track D / Data Operations)

This script audits, standardizes, and reconciles Agmarknet daily price and
arrival report files placed in data/raw/arrivals/historical/.

Functions:
- load_arrivals_file: Handles title headers and normalizes column names.
- export_city_crop_csvs: Splits consolidated downloads into clean {District}_{Commodity}.csv files.
- audit_arrivals_folder: Produces a complete validation audit report.
"""

import os
import sys
import glob
import logging
import shutil
from typing import List, Dict, Tuple, Optional, Any
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
logger = logging.getLogger("agmarknet_ingest")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARRIVALS_DIR = os.path.join(REPO_ROOT, "data", "raw", "arrivals", "historical")
RAW_DOWNLOADS_DIR = os.path.join(ARRIVALS_DIR, "raw_downloads")

TARGET_DISTRICTS = ["Ghaziabad", "Jhansi", "Kanpur", "Lucknow", "Unnao"]
TARGET_CROPS = ["Potato", "Onion", "Tomato", "Wheat", "Rice", "Paddy"]

# Expected schema aliases from Agmarknet reports
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
    "arrival quantity": "Arrivals_Tonnes",
    "arrivals (tonnes)": "Arrivals_Tonnes",
    "arrivals(in tonnes)": "Arrivals_Tonnes",
    "arrivals": "Arrivals_Tonnes",
    "arrival unit": "Arrival_Unit",
    "arrivals (qtl)": "Arrivals_Qtl",
    "arrivals (in qtl)": "Arrivals_Qtl",
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
    "qty": "Arrivals_Tonnes",
    "p_min": "Min_Price",
    "p_max": "Max_Price",
    "p_modal": "Modal_Price"
}


def load_arrivals_file(file_path: str) -> pd.DataFrame:
    """Load and normalize an Agmarknet arrivals file (CSV or Excel)."""
    if file_path.endswith(".csv"):
        df = pd.read_csv(file_path, low_memory=False)
    else:
        df = pd.read_excel(file_path)

    # Detect if row 0 has headers (common in Agmarknet 2.0 report downloads)
    if any("unnamed" in str(c).lower() or "daily price arrival" in str(c).lower() for c in df.columns[:2]):
        if any("district" in str(v).lower() for v in df.iloc[0].values):
            df.columns = [str(x).strip() for x in df.iloc[0].values]
            df = df.iloc[1:].reset_index(drop=True)

    normalized_cols = {c: COLUMN_ALIASES.get(str(c).strip().lower(), str(c).strip()) for c in df.columns}
    df.rename(columns=normalized_cols, inplace=True)
    return df


def organize_and_export_city_crop(folder_path: str = ARRIVALS_DIR) -> Dict[str, Any]:
    """
    Scans for raw download files in folder_path, consolidates them,
    moves original downloads into raw_downloads/, and writes out
    clean {District}_{Commodity}.csv files and master consolidated CSV.
    """
    all_files = glob.glob(os.path.join(folder_path, "*.*"))
    data_files = [f for f in all_files if f.lower().endswith((".csv", ".xlsx", ".xls"))]

    if not data_files:
        logger.warning("No data files to process for city/crop export.")
        return {}

    os.makedirs(RAW_DOWNLOADS_DIR, exist_ok=True)
    loaded_dfs = []

    for f in data_files:
        try:
            df = load_arrivals_file(f)
            loaded_dfs.append(df)
            # If it's an xlsx download, archive a copy in raw_downloads
            if f.endswith((".xlsx", ".xls")):
                dest_f = os.path.join(RAW_DOWNLOADS_DIR, os.path.basename(f))
                if f != dest_f:
                    shutil.copy2(f, dest_f)
                    os.remove(f)
        except Exception as e:
            logger.error(f"Error processing {f}: {e}")

    if not loaded_dfs:
        return {}

    combined = pd.concat(loaded_dfs, ignore_index=True)
    combined.drop_duplicates(inplace=True)

    # Export master consolidated CSV
    master_path = os.path.join(folder_path, "agmarknet_arrivals_up_2025_2026.csv")
    combined.to_csv(master_path, index=False)
    logger.info(f"Exported master consolidated arrivals: {master_path} ({len(combined):,} rows)")

    # Export individual {District}_{Commodity}.csv files
    exported_files = []
    if "District" in combined.columns and "Commodity" in combined.columns:
        for (dist, comm), group in combined.groupby(["District", "Commodity"]):
            clean_dist = str(dist).strip().replace(" ", "_")
            clean_comm = str(comm).strip().replace(" ", "_")
            pair_filename = f"{clean_dist}_{clean_comm}.csv"
            pair_path = os.path.join(folder_path, pair_filename)
            group.to_csv(pair_path, index=False)
            exported_files.append((pair_filename, len(group)))
            logger.info(f"  • Exported {pair_filename}: {len(group):,} rows")

    return {
        "master_file": master_path,
        "total_records": len(combined),
        "exported_city_crop_count": len(exported_files),
        "files": exported_files
    }


def audit_arrivals_folder(folder_path: str = ARRIVALS_DIR) -> Dict[str, Any]:
    """Inspect folder_path and report discovered files and rows."""
    os.makedirs(folder_path, exist_ok=True)
    all_files = glob.glob(os.path.join(folder_path, "*.csv"))
    # Exclude consolidated master if checking atomic city-crop files
    data_files = [f for f in all_files if not os.path.basename(f).startswith("agmarknet_arrivals_up_")]
    if not data_files:
        # Fallback to any data files including xlsx
        data_files = [f for f in glob.glob(os.path.join(folder_path, "*.*")) if f.lower().endswith((".csv", ".xlsx", ".xls"))]

    summary = {
        "folder_path": folder_path,
        "files_count": len(data_files),
        "files_found": [os.path.basename(f) for f in data_files],
        "districts_covered": [],
        "commodities_covered": [],
        "total_records": 0,
        "date_min": None,
        "date_max": None,
        "status": "EMPTY" if not data_files else "POPULATED"
    }

    if not data_files:
        logger.warning(f"No arrival files found in {folder_path}.")
        return summary

    total_rows = 0
    date_series = []
    districts_set = set()
    commodities_set = set()

    for file_path in data_files:
        try:
            df = load_arrivals_file(file_path)
            total_rows += len(df)

            if "District" in df.columns:
                for d in df["District"].dropna().unique():
                    districts_set.add(str(d).strip())
            if "Commodity" in df.columns:
                for c in df["Commodity"].dropna().unique():
                    commodities_set.add(str(c).strip())
            if "Arrival_Date" in df.columns:
                parsed_dates = pd.to_datetime(df["Arrival_Date"], format="%d-%m-%Y", errors="coerce")
                if parsed_dates.isna().all():
                    parsed_dates = pd.to_datetime(df["Arrival_Date"], errors="coerce")
                valid_dates = parsed_dates.dropna()
                if not valid_dates.empty:
                    date_series.extend(valid_dates)

        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")

    summary["total_records"] = total_rows
    summary["districts_covered"] = sorted(list(districts_set))
    summary["commodities_covered"] = sorted(list(commodities_set))

    if date_series:
        summary["date_min"] = min(date_series).strftime("%Y-%m-%d")
        summary["date_max"] = max(date_series).strftime("%Y-%m-%d")

    return summary


def main():
    logger.info("Executing Agmarknet City-Crop Organization & Audit...")
    res = organize_and_export_city_crop()
    summary = audit_arrivals_folder()

    print("\n" + "=" * 80)
    print("AGMARKNET ARRIVALS REPOSITORY AUDIT SUMMARY")
    print("=" * 80)
    print(f"Directory: {summary['folder_path']}")
    print(f"Status   : {summary['status']}")
    print(f"Files    : {summary['files_count']} individual city-crop file(s)")
    print(f"Records  : {summary['total_records']:,} rows")
    print(f"Districts: {', '.join(summary['districts_covered']) if summary['districts_covered'] else 'None'}")
    print(f"Crops    : {', '.join(summary['commodities_covered']) if summary['commodities_covered'] else 'None'}")
    if summary["date_min"]:
        print(f"Timeline : {summary['date_min']} to {summary['date_max']}")
    print("=" * 80)


if __name__ == "__main__":
    main()
