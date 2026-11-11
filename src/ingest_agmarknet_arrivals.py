"""
AGMARKNET Daily Price & Arrival Report Ingestion Engine
APMC Mandi Market Intelligence System
Author: Om Awasthi (Track D / Data Operations)

This script audits, verifies, and standardizes manually downloaded Agmarknet
daily price and arrival report files placed in data/raw/arrivals/historical/.

Expected naming convention in data/raw/arrivals/historical/:
- {District}_{Commodity}.csv or .xlsx (e.g., Kanpur_Potato.csv, Lucknow_Wheat.csv)
- or consolidated files like agmarknet_arrivals_{District}_{Year}.csv
"""

import os
import sys
import glob
import json
import logging
from typing import List, Dict, Tuple, Optional, Any
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
logger = logging.getLogger("agmarknet_ingest")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARRIVALS_DIR = os.path.join(REPO_ROOT, "data", "raw", "arrivals", "historical")

TARGET_DISTRICTS = ["Ghaziabad", "Jhansi", "Kanpur", "Lucknow", "Unnao"]
TARGET_CROPS = ["Potato", "Onion", "Tomato", "Wheat", "Rice", "Paddy"]

# Expected schema aliases from Agmarknet reports
COLUMN_ALIASES = {
    "state": "State",
    "district name": "District",
    "district": "District",
    "market name": "Market",
    "market": "Market",
    "commodity": "Commodity",
    "variety": "Variety",
    "grade": "Grade",
    "arrival date": "Arrival_Date",
    "reported date": "Arrival_Date",
    "date": "Arrival_Date",
    "arrivals (tonnes)": "Arrivals_Tonnes",
    "arrivals(in tonnes)": "Arrivals_Tonnes",
    "arrivals": "Arrivals_Tonnes",
    "arrivals (qtl)": "Arrivals_Qtl",
    "arrivals (in qtl)": "Arrivals_Qtl",
    "min price (rs./quintal)": "Min_Price",
    "min price": "Min_Price",
    "max price (rs./quintal)": "Max_Price",
    "max price": "Max_Price",
    "modal price (rs./quintal)": "Modal_Price",
    "modal price": "Modal_Price"
}


def audit_arrivals_folder(folder_path: str = ARRIVALS_DIR) -> Dict[str, Any]:
    """Inspect data/raw/arrivals/historical/ and report discovered files and rows."""
    os.makedirs(folder_path, exist_ok=True)
    all_files = glob.glob(os.path.join(folder_path, "*.*"))
    data_files = [f for f in all_files if f.lower().endswith((".csv", ".xlsx", ".xls"))]

    logger.info(f"Scanning arrivals directory: {folder_path}")
    logger.info(f"Discovered {len(data_files)} data file(s).")

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
        logger.warning(
            "No arrival files found in data/raw/arrivals/historical/. "
            "Follow instructions to download reports from https://agmarknet.gov.in/daily-price-and-arrival-report."
        )
        return summary

    total_rows = 0
    date_series = []
    districts_set = set()
    commodities_set = set()

    for file_path in data_files:
        try:
            if file_path.endswith(".csv"):
                df = pd.read_csv(file_path, low_memory=False)
            else:
                df = pd.read_excel(file_path)

            # Normalize column names
            normalized_cols = {c: COLUMN_ALIASES.get(str(c).strip().lower(), str(c).strip()) for c in df.columns}
            df.rename(columns=normalized_cols, inplace=True)

            total_rows += len(df)

            if "District" in df.columns:
                for d in df["District"].dropna().unique():
                    districts_set.add(str(d).strip())
            if "Commodity" in df.columns:
                for c in df["Commodity"].dropna().unique():
                    commodities_set.add(str(c).strip())
            if "Arrival_Date" in df.columns:
                parsed_dates = pd.to_datetime(df["Arrival_Date"], errors="coerce")
                valid_dates = parsed_dates.dropna()
                if not valid_dates.empty:
                    date_series.extend(valid_dates)

            logger.info(f"  • {os.path.basename(file_path)}: {len(df):,} rows")

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
    summary = audit_arrivals_folder()
    print("\n" + "=" * 80)
    print("AGMARKNET ARRIVALS REPOSITORY AUDIT SUMMARY")
    print("=" * 80)
    print(f"Directory: {summary['folder_path']}")
    print(f"Status   : {summary['status']}")
    print(f"Files    : {summary['files_count']} file(s)")
    if summary["files_found"]:
        for fn in summary["files_found"]:
            print(f"  - {fn}")
    print(f"Records  : {summary['total_records']:,} rows")
    print(f"Districts: {', '.join(summary['districts_covered']) if summary['districts_covered'] else 'None'}")
    print(f"Crops    : {', '.join(summary['commodities_covered']) if summary['commodities_covered'] else 'None'}")
    if summary["date_min"]:
        print(f"Timeline : {summary['date_min']} to {summary['date_max']}")
    print("=" * 80)


if __name__ == "__main__":
    main()
