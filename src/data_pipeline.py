"""
Mandi Data Loading & Normalization Pipeline
APMC Mandi Market Intelligence System

This module implements a production-grade, reproducible data-loading pipeline
for multi-year APMC mandi datasets (including 5-year historical series).

Features:
- Multi-format source ingestion (CSV, TSV, and optional Excel).
- Non-destructive processing: preserves raw source files intact.
- Explicit schema standardization and case-insensitive column aliasing.
- Robust date parsing across diverse date representations.
- Strict numeric normalization for price metrics (cleaning currency symbols, commas).
- Complete edge-case safety: handles missing files, empty files, malformed rows,
  invalid dates, missing columns, and zero-row states safely.
- Grade-preserving series identity and Strategy 2 duplicate exclusion.
- Comprehensive processing manifest generation with cryptographic SHA-256
  checksums, UTC execution timestamps, row accounting, and schema metadata.
- Full CLI interface with configurable arguments.
"""

import os
import sys
import glob
import json
import hashlib
import logging
import argparse
from datetime import datetime, timezone
from typing import List, Dict, Tuple, Optional, Any, Set
import pandas as pd
import numpy as np

# Configure module logging
logger = logging.getLogger("mandi_data_pipeline")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


# =============================================================================
# 1. CONSTANTS, SCHEMAS & NORMALIZATION MAPS
# =============================================================================

SCHEMA_VERSION = "1.0.0"

# Mandatory columns required for econometric and market modeling
REQUIRED_COLUMNS = [
    "Arrival_Date",
    "District",
    "Market",
    "Commodity",
    "Variety",
    "Modal_Price",
    "Min_Price",
    "Max_Price"
]

# Optional columns that are imputed or retained if present
OPTIONAL_COLUMNS = [
    "Grade",
    "Commodity_Code",
    "State"
]

# Canonical ordering of output columns
CANONICAL_COLUMNS = [
    "Arrival_Date",
    "District",
    "Market",
    "Commodity",
    "Variety",
    "Grade",
    "Min_Price",
    "Max_Price",
    "Modal_Price",
    "Commodity_Code",
    "State",
    "series_id"
]

# Mapping dictionary for case-insensitive and alias resolution
COLUMN_ALIASES: Dict[str, str] = {
    # Arrival Date
    "arrival_date": "Arrival_Date",
    "arrival date": "Arrival_Date",
    "arrivaldate": "Arrival_Date",
    "date": "Arrival_Date",
    "arrival-date": "Arrival_Date",
    "reported_date": "Arrival_Date",
    
    # Commodity
    "commodity": "Commodity",
    "crop": "Commodity",
    "commodity_name": "Commodity",
    "crop_name": "Commodity",
    
    # Commodity Code
    "commodity_code": "Commodity_Code",
    "commodity code": "Commodity_Code",
    "commoditycode": "Commodity_Code",
    "crop_code": "Commodity_Code",
    
    # District
    "district": "District",
    "dist": "District",
    "district_name": "District",
    
    # Market
    "market": "Market",
    "mandi": "Market",
    "market_name": "Market",
    "apmc": "Market",
    
    # Grade
    "grade": "Grade",
    "quality_grade": "Grade",
    
    # Prices
    "min_price": "Min_Price",
    "min price": "Min_Price",
    "minimum_price": "Min_Price",
    "minimum price": "Min_Price",
    "minprice": "Min_Price",
    
    "max_price": "Max_Price",
    "max price": "Max_Price",
    "maximum_price": "Max_Price",
    "maximum price": "Max_Price",
    "maxprice": "Max_Price",
    
    "modal_price": "Modal_Price",
    "modal price": "Modal_Price",
    "modalprice": "Modal_Price",
    "modal": "Modal_Price",
    
    # State
    "state": "State",
    "state_name": "State",
    
    # Variety
    "variety": "Variety",
    "cultivar": "Variety"
}

# Standardized district spelling map (resolving historical typos)
DISTRICT_NORMALIZATION: Dict[str, str] = {
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

# Supported date formats for deterministic parsing
DATE_FORMATS = [
    "%d/%m/%Y",
    "%Y-%m-%d",
    "%d-%m-%Y",
    "%m/%d/%Y",
    "%Y/%m/%d",
    "%d.%m.%Y"
]

# Core target crops evaluated in the Mandi_Prediction econometric engine
TARGET_CROPS = {"Potato", "Onion", "Tomato", "Wheat"}


# =============================================================================
# 2. CUSTOM EXCEPTION HIERARCHY
# =============================================================================

class DataPipelineError(Exception):
    """Base exception for all mandi data pipeline errors."""
    pass


class MissingSourceFilesError(DataPipelineError):
    """Raised when the specified source directory or files cannot be located."""
    pass


class MissingColumnsError(DataPipelineError):
    """Raised when raw files lack mandatory canonical columns."""
    pass


class EmptyDatasetError(DataPipelineError):
    """Raised when no valid observations survive parsing and cleaning."""
    pass


class UnsupportedFileFormatError(DataPipelineError):
    """Raised when an unsupported file extension is encountered."""
    pass


# =============================================================================
# 3. HELPER UTILITIES
# =============================================================================

def compute_file_sha256(filepath: str, chunk_size: int = 65536) -> str:
    """
    Computes cryptographic SHA-256 hex digest of a file in streaming chunks
    to avoid memory exhaustion on large datasets.
    """
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def normalize_price_series(series: pd.Series) -> pd.Series:
    """
    Normalizes numeric price series by stripping currency prefixes (₹, Rs),
    commas, whitespace, and coercing unparseable characters to NaN.
    """
    if series.empty:
        return pd.Series(dtype=float)
    
    # If already numeric
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")
    
    # Clean string representations
    cleaned = (
        series.astype(str)
        .str.replace("₹", "", regex=False)
        .str.replace("Rs.", "", regex=False)
        .str.replace("Rs", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
    )
    return pd.to_numeric(cleaned, errors="coerce")


def parse_arrival_dates(series: pd.Series) -> pd.Series:
    """
    Parses date series across standard agricultural reporting date formats.
    Returns datetime series with unparseable entries coerced to NaT.
    """
    if series.empty:
        return pd.to_datetime(pd.Series(dtype="datetime64[ns]"))
    
    # First attempt canonical %d/%m/%Y
    dt = pd.to_datetime(series, format="%d/%m/%Y", errors="coerce")
    
    # For any remaining NaT values, try fallback formats
    missing_mask = dt.isna() & series.notna()
    if missing_mask.any():
        for fmt in ["%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%Y/%m/%d"]:
            attempt = pd.to_datetime(series[missing_mask], format=fmt, errors="coerce")
            dt.update(attempt[attempt.notna()])
            missing_mask = dt.isna() & series.notna()
            if not missing_mask.any():
                break
                
    # Final generic parser attempt for remaining tricky records
    if missing_mask.any():
        dt.update(pd.to_datetime(series[missing_mask], errors="coerce"))
        
    return dt


# =============================================================================
# 4. CORE DATA PIPELINE ENGINE
# =============================================================================

class MandiDataPipeline:
    """
    End-to-end data ingestion, validation, normalization, deduplication,
    and manifest generation engine for multi-year APMC mandi datasets.
    """
    
    def __init__(
        self,
        input_dir: str = "5 year dataset",
        output_dir: str = "data/processed",
        output_filename: str = "mandi_5year_processed.csv",
        manifest_filename: str = "processing_manifest.json",
        min_series_records: int = 20,
        exclude_ambiguous_same_grade: bool = True,
        target_crops_only: bool = False,
        date_format: str = "%Y-%m-%d",
        schema_version: str = SCHEMA_VERSION
    ):
        self.input_dir = os.path.abspath(input_dir) if input_dir else ""
        self.output_dir = os.path.abspath(output_dir) if output_dir else ""
        self.output_filename = output_filename
        self.manifest_filename = manifest_filename
        self.min_series_records = min_series_records
        self.exclude_ambiguous_same_grade = exclude_ambiguous_same_grade
        self.target_crops_only = target_crops_only
        self.date_format = date_format
        self.schema_version = schema_version
        
        self.logger = logger
        
    def find_source_files(self, explicit_files: Optional[List[str]] = None) -> List[str]:
        """
        Discovers raw source files (CSV and Excel) in the configured input directory
        or validates explicit file paths.
        """
        if explicit_files:
            found_files = []
            for f in explicit_files:
                abs_f = os.path.abspath(f)
                if not os.path.exists(abs_f):
                    raise MissingSourceFilesError(f"Specified source file not found: {abs_f}")
                found_files.append(abs_f)
            return sorted(found_files)
            
        if not self.input_dir or not os.path.isdir(self.input_dir):
            raise MissingSourceFilesError(f"Input directory does not exist: {self.input_dir}")
            
        patterns = ["*.csv", "*.CSV", "*.xlsx", "*.XLSX", "*.xls", "*.XLS"]
        files: List[str] = []
        for p in patterns:
            files.extend(glob.glob(os.path.join(self.input_dir, p)))
            
        files = sorted(list(set(files)))
        if not files:
            raise MissingSourceFilesError(f"No CSV or Excel source files found in: {self.input_dir}")
            
        return files

    def read_raw_file(self, filepath: str) -> pd.DataFrame:
        """
        Reads a raw tabular file (CSV or Excel) safely in read-only mode.
        Handles zero-byte and empty files cleanly.
        """
        if not os.path.exists(filepath):
            raise MissingSourceFilesError(f"File not found: {filepath}")
            
        file_size = os.path.getsize(filepath)
        if file_size == 0:
            self.logger.warning(f"File {os.path.basename(filepath)} is completely empty (0 bytes).")
            return pd.DataFrame()
            
        ext = os.path.splitext(filepath)[1].lower()
        if ext in [".csv", ".tsv", ".txt"]:
            try:
                # Try standard comma CSV
                df = pd.read_csv(filepath, low_memory=False)
            except Exception as e:
                # Attempt with fallback separator if comma parsing fails
                try:
                    df = pd.read_csv(filepath, sep=None, engine="python")
                except Exception as inner_e:
                    raise DataPipelineError(f"Failed to parse CSV file {filepath}: {str(inner_e)}") from e
            return df
        elif ext in [".xlsx", ".xls"]:
            try:
                df = pd.read_excel(filepath)
                return df
            except ImportError as ie:
                raise UnsupportedFileFormatError(
                    f"Excel support requires 'openpyxl' (for .xlsx) or 'xlrd' (for .xls). "
                    f"Please install dependencies or provide CSV files. Error: {str(ie)}"
                ) from ie
            except Exception as e:
                raise DataPipelineError(f"Failed to parse Excel file {filepath}: {str(e)}") from e
        else:
            raise UnsupportedFileFormatError(f"Unsupported file format '{ext}' for file {filepath}")

    def standardize_column_names(self, df: pd.DataFrame, filepath: str) -> pd.DataFrame:
        """
        Standardizes column headers using case-insensitive mapping and alias resolution.
        Verifies presence of mandatory columns.
        """
        if df.empty:
            return df
            
        rename_map = {}
        for col in df.columns:
            clean_col = str(col).strip().lower()
            if clean_col in COLUMN_ALIASES:
                rename_map[col] = COLUMN_ALIASES[clean_col]
            else:
                # Normalize underscore/spaces
                clean_col_norm = clean_col.replace(" ", "_").replace("-", "_")
                if clean_col_norm in COLUMN_ALIASES:
                    rename_map[col] = COLUMN_ALIASES[clean_col_norm]
                    
        df = df.rename(columns=rename_map)
        
        # Verify required columns
        missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing_cols:
            raise MissingColumnsError(
                f"File '{os.path.basename(filepath)}' is missing mandatory columns: {missing_cols}. "
                f"Found columns: {list(df.columns)}"
            )
            
        return df

    def clean_single_file(self, filepath: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Loads, standardizes, validates, and cleans an individual source file.
        Returns cleaned DataFrame along with detailed file-level manifest audit metadata.
        """
        file_name = os.path.basename(filepath)
        file_size = os.path.getsize(filepath)
        file_sha256 = compute_file_sha256(filepath) if file_size > 0 else ""
        
        audit_meta: Dict[str, Any] = {
            "file_name": file_name,
            "source_path": filepath,
            "size_bytes": file_size,
            "sha256": file_sha256,
            "raw_row_count": 0,
            "valid_row_count": 0,
            "dropped_row_count": 0,
            "dropped_reasons": {
                "missing_dates": 0,
                "missing_prices": 0,
                "non_positive_prices": 0,
                "missing_series_metadata": 0
            }
        }
        
        if file_size == 0:
            return pd.DataFrame(), audit_meta
            
        df = self.read_raw_file(filepath)
        if df.empty:
            return pd.DataFrame(), audit_meta
            
        raw_count = len(df)
        audit_meta["raw_row_count"] = raw_count
        
        # Standardize column headers
        df = self.standardize_column_names(df, filepath)
        
        # Provide defaults for optional columns if absent
        if "Grade" not in df.columns:
            df["Grade"] = "FAQ"
        else:
            df["Grade"] = df["Grade"].fillna("FAQ").astype(str).str.strip()
            df["Grade"] = df["Grade"].replace({"": "FAQ", "nan": "FAQ", "None": "FAQ", "NAN": "FAQ"})
            
        if "State" not in df.columns:
            df["State"] = "Uttar Pradesh"
        else:
            df["State"] = df["State"].fillna("Uttar Pradesh").astype(str).str.strip()
            df["State"] = df["State"].replace({"": "Uttar Pradesh", "nan": "Uttar Pradesh", "None": "Uttar Pradesh"})
            
        if "Commodity_Code" not in df.columns:
            df["Commodity_Code"] = 0
        else:
            df["Commodity_Code"] = pd.to_numeric(df["Commodity_Code"], errors="coerce").fillna(0).astype(int)
            
        # Clean string text fields
        text_cols = ["District", "Market", "Commodity", "Variety"]
        for col in text_cols:
            df[col] = df[col].astype(str).str.strip()
            
        # Standardize District naming
        district_lower = df["District"].str.lower()
        df["District"] = district_lower.map(DISTRICT_NORMALIZATION).fillna(df["District"])
        
        # Parse Dates
        parsed_dates = parse_arrival_dates(df["Arrival_Date"])
        invalid_dates = parsed_dates.isna()
        audit_meta["dropped_reasons"]["missing_dates"] = int(invalid_dates.sum())
        df["Arrival_Date_Parsed"] = parsed_dates
        
        # Normalize Prices
        for p in ["Modal_Price", "Min_Price", "Max_Price"]:
            df[p] = normalize_price_series(df[p])
            
        missing_prices = df["Modal_Price"].isna() | df["Min_Price"].isna() | df["Max_Price"].isna()
        audit_meta["dropped_reasons"]["missing_prices"] = int(missing_prices.sum())
        
        non_positive_prices = (df["Modal_Price"] <= 0) | (df["Min_Price"] <= 0) | (df["Max_Price"] <= 0)
        audit_meta["dropped_reasons"]["non_positive_prices"] = int(non_positive_prices.sum())
        
        # Check text columns for nulls / empty placeholders
        missing_metadata = False
        for col in text_cols:
            missing_metadata = missing_metadata | df[col].isna() | (df[col] == "") | (df[col] == "nan")
        audit_meta["dropped_reasons"]["missing_series_metadata"] = int(missing_metadata.sum())
        
        # Valid filter mask
        valid_mask = (
            ~invalid_dates &
            ~missing_prices &
            ~non_positive_prices &
            ~missing_metadata
        )
        
        clean_df = df[valid_mask].copy()
        clean_df["Arrival_Date"] = clean_df["Arrival_Date_Parsed"]
        clean_df.drop(columns=["Arrival_Date_Parsed"], inplace=True)
        
        # Record source file name for traceability
        clean_df["Source_File"] = file_name
        
        valid_count = len(clean_df)
        audit_meta["valid_row_count"] = valid_count
        audit_meta["dropped_row_count"] = raw_count - valid_count
        
        return clean_df, audit_meta

    def process(self, source_files: Optional[List[str]] = None) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Executes end-to-end ingestion across all source files, performs multi-file
        concatenation, duplicate resolution (Strategy 2), canonical series_id generation,
        and aggregates manifest accounting metrics.
        """
        start_utc = datetime.now(timezone.utc)
        self.logger.info(f"Starting MandiDataPipeline execution (UTC: {start_utc.isoformat()})...")
        
        files = self.find_source_files(source_files)
        self.logger.info(f"Discovered {len(files)} source files in: {self.input_dir if not source_files else 'explicit list'}")
        
        cleaned_dfs: List[pd.DataFrame] = []
        file_audits: List[Dict[str, Any]] = []
        
        total_raw = 0
        total_valid = 0
        total_dropped = 0
        
        for filepath in files:
            self.logger.info(f"Processing source file: {os.path.basename(filepath)}...")
            df_clean, audit = self.clean_single_file(filepath)
            file_audits.append(audit)
            total_raw += audit["raw_row_count"]
            total_valid += audit["valid_row_count"]
            total_dropped += audit["dropped_row_count"]
            
            if not df_clean.empty:
                cleaned_dfs.append(df_clean)
                
        if not cleaned_dfs:
            raise EmptyDatasetError(
                f"No valid observations were loaded from {len(files)} source files. "
                f"Total raw rows inspected: {total_raw}, dropped: {total_dropped}."
            )
            
        merged_df = pd.concat(cleaned_dfs, ignore_index=True)
        post_merge_count = len(merged_df)
        
        # Apply target crop filter if requested
        if self.target_crops_only:
            crop_mask = merged_df["Commodity"].isin(TARGET_CROPS)
            merged_df = merged_df[crop_mask].copy()
            self.logger.info(f"Target crop filter applied ({TARGET_CROPS}): retained {len(merged_df):,} rows.")
            
        if merged_df.empty:
            raise EmptyDatasetError("Dataset is empty after applying target crop filter.")
            
        # Series key definition including Grade (Grade-preserving series identity)
        series_cols = ["District", "Market", "Commodity", "Variety", "Grade"]
        key_grade_date = series_cols + ["Arrival_Date"]
        
        # Strategy 2 duplicate exclusion: remove ambiguous same-grade conflicting price quotes on same date
        ambiguous_rows_excluded = 0
        ambiguous_dates_count = 0
        if self.exclude_ambiguous_same_grade:
            dup_groups = merged_df.groupby(key_grade_date).agg(
                n_rows=("Modal_Price", "count"),
                modal_nunique=("Modal_Price", "nunique"),
                min_nunique=("Min_Price", "nunique"),
                max_nunique=("Max_Price", "nunique")
            )
            ambiguous_keys = dup_groups[
                (dup_groups["n_rows"] > 1) &
                ((dup_groups["modal_nunique"] > 1) | (dup_groups["min_nunique"] > 1) | (dup_groups["max_nunique"] > 1))
            ].index
            
            if not ambiguous_keys.empty:
                is_ambiguous = merged_df.set_index(key_grade_date).index.isin(ambiguous_keys)
                ambiguous_rows_excluded = int(is_ambiguous.sum())
                ambiguous_dates_count = len(ambiguous_keys)
                merged_df = merged_df[~is_ambiguous].copy()
                self.logger.info(
                    f"Strategy 2: Excluded {ambiguous_rows_excluded:,} ambiguous conflicting rows "
                    f"across {ambiguous_dates_count:,} dates."
                )
                
        # Deduplicate exact matching quotes (keep first row)
        pre_dedup = len(merged_df)
        merged_df = merged_df.drop_duplicates(subset=key_grade_date, keep="first").copy()
        exact_duplicates_dropped = pre_dedup - len(merged_df)
        
        # Construct canonical series_id
        merged_df["series_id"] = merged_df[series_cols].astype(str).agg("__".join, axis=1)
        
        # Filter series with fewer than min_series_records
        filtered_series_dropped_rows = 0
        if self.min_series_records > 0:
            series_counts = merged_df.groupby("series_id").size()
            valid_series = series_counts[series_counts >= self.min_series_records].index
            pre_series_filter = len(merged_df)
            merged_df = merged_df[merged_df["series_id"].isin(valid_series)].copy()
            filtered_series_dropped_rows = pre_series_filter - len(merged_df)
            self.logger.info(
                f"Series observation filter (>= {self.min_series_records} obs): retained {len(merged_df):,} rows "
                f"across {merged_df['series_id'].nunique():,} unique series."
            )
            
        # Chronological sorting strictly by series_id and Arrival_Date
        merged_df.sort_values(by=["series_id", "Arrival_Date"], inplace=True)
        merged_df.reset_index(drop=True, inplace=True)
        
        # Format Arrival_Date for output
        min_date_str = merged_df["Arrival_Date"].min().strftime("%Y-%m-%d")
        max_date_str = merged_df["Arrival_Date"].max().strftime("%Y-%m-%d")
        
        # Enforce canonical column order
        for col in CANONICAL_COLUMNS:
            if col not in merged_df.columns:
                merged_df[col] = None
        final_df = merged_df[CANONICAL_COLUMNS].copy()
        
        end_utc = datetime.now(timezone.utc)
        processing_duration_sec = (end_utc - start_utc).total_seconds()
        
        # Assemble Manifest
        manifest: Dict[str, Any] = {
            "schema_version": self.schema_version,
            "pipeline_name": "MandiDataPipeline",
            "execution_timestamp_utc": end_utc.isoformat(),
            "duration_seconds": round(processing_duration_sec, 3),
            "configuration": {
                "input_dir": self.input_dir,
                "output_dir": self.output_dir,
                "output_filename": self.output_filename,
                "manifest_filename": self.manifest_filename,
                "min_series_records": self.min_series_records,
                "exclude_ambiguous_same_grade": self.exclude_ambiguous_same_grade,
                "target_crops_only": self.target_crops_only,
                "date_format": self.date_format
            },
            "source_files_audit": file_audits,
            "summary_metrics": {
                "total_source_files": len(files),
                "total_raw_rows": total_raw,
                "total_valid_parsed_rows": total_valid,
                "total_dropped_raw_rows": total_dropped,
                "ambiguous_same_grade_excluded_rows": ambiguous_rows_excluded,
                "exact_duplicates_deduplicated": exact_duplicates_dropped,
                "low_observation_series_dropped_rows": filtered_series_dropped_rows,
                "final_clean_rows": len(final_df),
                "unique_series_count": int(final_df["series_id"].nunique()),
                "unique_districts": sorted(final_df["District"].unique().tolist()),
                "unique_markets_count": int(final_df["Market"].nunique()),
                "unique_commodities_count": int(final_df["Commodity"].nunique()),
                "date_range": {
                    "earliest_arrival_date": min_date_str,
                    "latest_arrival_date": max_date_str,
                    "total_calendar_days_spanned": (
                        merged_df["Arrival_Date"].max() - merged_df["Arrival_Date"].min()
                    ).days + 1
                }
            },
            "schema_columns": {
                col: str(final_df[col].dtype) for col in final_df.columns
            },
            "output_artifacts": []
        }
        
        self.logger.info(
            f"Pipeline complete! Raw rows: {total_raw:,} -> Final clean rows: {len(final_df):,} "
            f"across {final_df['series_id'].nunique():,} series. Spans {min_date_str} to {max_date_str}."
        )
        
        return final_df, manifest

    def save(
        self,
        df: pd.DataFrame,
        manifest: Dict[str, Any],
        output_path: Optional[str] = None,
        manifest_path: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Saves the processed dataset to CSV and the manifest metadata to JSON.
        Computes SHA-256 digests and file sizes for the output artifacts.
        """
        if not output_path:
            os.makedirs(self.output_dir, exist_ok=True)
            output_path = os.path.join(self.output_dir, self.output_filename)
        else:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            
        if not manifest_path:
            os.makedirs(self.output_dir, exist_ok=True)
            manifest_path = os.path.join(self.output_dir, self.manifest_filename)
        else:
            os.makedirs(os.path.dirname(os.path.abspath(manifest_path)), exist_ok=True)
            
        # Format Arrival_Date for serialization
        save_df = df.copy()
        if pd.api.types.is_datetime64_any_dtype(save_df["Arrival_Date"]):
            save_df["Arrival_Date"] = save_df["Arrival_Date"].dt.strftime(self.date_format)
            
        # Write CSV dataset
        self.logger.info(f"Saving processed dataset to: {output_path}...")
        save_df.to_csv(output_path, index=False)
        
        output_size = os.path.getsize(output_path)
        output_sha256 = compute_file_sha256(output_path)
        
        manifest["output_artifacts"] = [
            {
                "artifact_type": "processed_dataset_csv",
                "file_name": os.path.basename(output_path),
                "file_path": os.path.abspath(output_path),
                "size_bytes": output_size,
                "sha256": output_sha256,
                "row_count": len(save_df)
            }
        ]
        
        # Write JSON Manifest
        self.logger.info(f"Saving processing manifest to: {manifest_path}...")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
            
        manifest_size = os.path.getsize(manifest_path)
        manifest_sha256 = compute_file_sha256(manifest_path)
        
        manifest["output_artifacts"].append({
            "artifact_type": "processing_manifest_json",
            "file_name": os.path.basename(manifest_path),
            "file_path": os.path.abspath(manifest_path),
            "size_bytes": manifest_size,
            "sha256": manifest_sha256,
            "row_count": None
        })
        
        # Re-write manifest with its own entry included
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
            
        self.logger.info(f"Artifacts successfully written! (Dataset: {output_size:,} bytes | Manifest: {manifest_size:,} bytes)")
        return output_path, manifest_path

    def run(self, source_files: Optional[List[str]] = None) -> Tuple[pd.DataFrame, Dict[str, Any], str, str]:
        """
        Convenience wrapper executing both process() and save().
        """
        df, manifest = self.process(source_files)
        out_csv, out_manifest = self.save(df, manifest)
        return df, manifest, out_csv, out_manifest


# =============================================================================
# 5. CONVENIENCE FUNCTION FOR DIRECT IMPORT
# =============================================================================

def process_5year_mandi_dataset(
    input_dir: str = "5 year dataset",
    output_dir: str = "data/processed",
    output_filename: str = "mandi_5year_processed.csv",
    min_series_records: int = 20,
    target_crops_only: bool = False
) -> Tuple[pd.DataFrame, Dict[str, Any], str, str]:
    """
    Standard high-level entry point to process the 5-year APMC dataset.
    """
    pipeline = MandiDataPipeline(
        input_dir=input_dir,
        output_dir=output_dir,
        output_filename=output_filename,
        min_series_records=min_series_records,
        target_crops_only=target_crops_only
    )
    return pipeline.run()


# =============================================================================
# 6. COMMAND-LINE ENTRY POINT
# =============================================================================

def build_parser() -> argparse.ArgumentParser:
    """Constructs the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Mandi Data Pipeline: Ingest, clean, normalize, and manifest APMC mandi datasets.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        default="5 year dataset",
        help="Path to directory containing raw CSV or Excel mandi files."
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/processed",
        help="Directory where processed dataset and manifest will be written."
    )
    parser.add_argument(
        "--output-filename",
        type=str,
        default="mandi_5year_processed.csv",
        help="Filename for the processed CSV dataset."
    )
    parser.add_argument(
        "--manifest-filename",
        type=str,
        default="processing_manifest.json",
        help="Filename for the processing manifest JSON."
    )
    parser.add_argument(
        "--min-series-records",
        type=int,
        default=20,
        help="Minimum number of observations required to retain a price series."
    )
    parser.add_argument(
        "--target-crops-only",
        action="store_true",
        help="If set, retains only target crops (Potato, Onion, Tomato, Wheat)."
    )
    parser.add_argument(
        "--date-format",
        type=str,
        default="%Y-%m-%d",
        help="Date format for serialized output CSV (e.g., '%%Y-%%m-%%d' or '%%d/%%m/%%Y')."
    )
    parser.add_argument(
        "--no-exclude-ambiguous",
        action="store_true",
        help="Disable Strategy 2 exclusion of ambiguous same-grade conflicting quotes."
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable detailed debug logging."
    )
    return parser


def main():
    """Command-line entry point."""
    parser = build_parser()
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        
    print("=" * 80)
    print("APMC MANDI 5-YEAR DATA PROCESSING PIPELINE")
    print(f"Input Directory:  {args.input_dir}")
    print(f"Output Directory: {args.output_dir}")
    print(f"Target Crops:     {'Yes (Potato, Onion, Tomato, Wheat)' if args.target_crops_only else 'All commodities'}")
    print(f"Ambiguity Filter: {'Disabled' if args.no_exclude_ambiguous else 'Enabled (Strategy 2)'}")
    print("=" * 80)
    
    try:
        pipeline = MandiDataPipeline(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            output_filename=args.output_filename,
            manifest_filename=args.manifest_filename,
            min_series_records=args.min_series_records,
            exclude_ambiguous_same_grade=not args.no_exclude_ambiguous,
            target_crops_only=args.target_crops_only,
            date_format=args.date_format
        )
        df, manifest, out_csv, out_manifest = pipeline.run()
        
        print("\n" + "=" * 80)
        print("PIPELINE PROCESSING SUMMARY:")
        print(f"  Source Files Processed:  {manifest['summary_metrics']['total_source_files']}")
        print(f"  Total Raw Rows Read:     {manifest['summary_metrics']['total_raw_rows']:,}")
        print(f"  Total Valid Rows Parsed: {manifest['summary_metrics']['total_valid_parsed_rows']:,}")
        print(f"  Raw Rows Dropped:        {manifest['summary_metrics']['total_dropped_raw_rows']:,}")
        print(f"  Ambiguous Rows Excluded: {manifest['summary_metrics']['ambiguous_same_grade_excluded_rows']:,}")
        print(f"  Exact Duplicates Dropped:{manifest['summary_metrics']['exact_duplicates_deduplicated']:,}")
        print(f"  Final Clean Observations:{manifest['summary_metrics']['final_clean_rows']:,}")
        print(f"  Unique Series Retained:  {manifest['summary_metrics']['unique_series_count']:,}")
        print(f"  Temporal Date Coverage:  {manifest['summary_metrics']['date_range']['earliest_arrival_date']} to {manifest['summary_metrics']['date_range']['latest_arrival_date']} ({manifest['summary_metrics']['date_range']['total_calendar_days_spanned']:,} days)")
        print(f"  Districts Covered:       {', '.join(manifest['summary_metrics']['unique_districts'])}")
        print(f"  Output CSV Dataset:      {out_csv} ({os.path.getsize(out_csv):,} bytes)")
        print(f"  Output Manifest JSON:    {out_manifest} ({os.path.getsize(out_manifest):,} bytes)")
        print("=" * 80)
        print("SUCCESS: Mandi 5-year data processing pipeline completed successfully.\n")
        return 0
    except DataPipelineError as e:
        logger.error(f"Pipeline Execution Failed: {str(e)}")
        print(f"\nERROR: {str(e)}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.exception(f"Unexpected Fatal Error: {str(e)}")
        print(f"\nFATAL ERROR: {str(e)}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
