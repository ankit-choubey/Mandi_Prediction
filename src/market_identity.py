"""
Market Identity Normalization and Evidence-Based Canonicalization Engine.

Provides deterministic, pure functions for APMC mandi market name normalization,
evidence-based alias evaluation, alias table management, and DataFrame
canonicalization without external I/O side effects.
"""

import os
import re
import string
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import pandas as pd


# Required schema for data/reference/market_aliases.csv
MARKET_ALIAS_COLUMNS: List[str] = [
    "district",
    "market_raw",
    "market_canonical",
    "rule",
    "evidence",
    "first_date",
    "last_date",
    "overlap_days",
    "price_agreement",
    "status"
]


def normalize_market_name(name: Optional[str]) -> str:
    """
    Normalizes a market name into a canonical token string:
    - Lowercase
    - Strip punctuation (replace punctuation marks with whitespace)
    - Collapse multiple whitespace characters into a single space
    - Remove trailing 'apmc' word
    - Strip leading/trailing whitespace
    
    Examples:
        'Ghaziabad APMC' -> 'ghaziabad'
        'Kanpur(Grain) APMC' -> 'kanpur grain'
        'Jhansi (Grain)' -> 'jhansi grain'
        'Hapur' -> 'hapur'
    """
    if not isinstance(name, str):
        return ""
    
    # 1. Lowercase
    s = name.strip().lower()
    if not s:
        return ""
    
    # 2. Strip punctuation (replace with spaces so 'Kanpur(Grain)' -> 'kanpur grain')
    s = re.sub(r"[" + re.escape(string.punctuation) + r"]", " ", s)
    
    # 3. Collapse multiple whitespace
    s = re.sub(r"\s+", " ", s).strip()
    
    # 4. Remove trailing 'apmc' word boundary
    s = re.sub(r"\bapmc$", "", s).strip()
    
    # 5. Final whitespace collapse
    s = re.sub(r"\s+", " ", s).strip()
    
    return s


def evaluate_alias_evidence(
    district_1: str,
    name_1: str,
    first_date_1: str,
    last_date_1: str,
    district_2: str,
    name_2: str,
    first_date_2: str,
    last_date_2: str,
    overlapping_records_df: Optional[pd.DataFrame] = None
) -> Tuple[bool, Dict[str, Any]]:
    """
    Evaluates whether two raw market names satisfy the strict Evidence Rule:
    
    Accept a pair ONLY if ALL of the following hold:
      1. Same district: district_1.lower() == district_2.lower()
      2. The normalised names are identical:
         normalize_market_name(name_1) == normalize_market_name(name_2)
      3. AND either:
         (a) the two raw names' date ranges overlap by <= 5 calendar days, OR
         (b) on overlapping (commodity, variety, grade, date) rows, the
             exact-price agreement is >= 95%.
             
    Returns:
        (is_accepted: bool, evidence_dict: dict)
    """
    # 1. District check
    d1 = str(district_1).strip().lower()
    d2 = str(district_2).strip().lower()
    same_district = (d1 == d2) and bool(d1)
    
    # 2. Normalised name check
    norm_1 = normalize_market_name(name_1)
    norm_2 = normalize_market_name(name_2)
    same_norm = (norm_1 == norm_2) and bool(norm_1)
    
    # 3. Date range overlap calculation
    dt1_start = pd.to_datetime(first_date_1)
    dt1_end = pd.to_datetime(last_date_1)
    dt2_start = pd.to_datetime(first_date_2)
    dt2_end = pd.to_datetime(last_date_2)
    
    overlap_start = max(dt1_start, dt2_start)
    overlap_end = min(dt1_end, dt2_end)
    
    if overlap_end >= overlap_start:
        overlap_days = int((overlap_end - overlap_start).days) + 1
    else:
        overlap_days = 0
        
    price_agreement: Optional[float] = None
    rule_passed: Optional[str] = None
    evidence_str = ""
    status = "UNMAPPED/REVIEW"
    
    if not same_district:
        return False, {
            "status": "UNMAPPED/REVIEW",
            "rule": "Failed (different districts)",
            "evidence": f"District mismatch: '{district_1}' vs '{district_2}'",
            "overlap_days": overlap_days,
            "price_agreement": None
        }
        
    if not same_norm:
        return False, {
            "status": "UNMAPPED/REVIEW",
            "rule": "Failed (normalised names mismatch)",
            "evidence": f"Normalized mismatch: '{norm_1}' vs '{norm_2}'",
            "overlap_days": overlap_days,
            "price_agreement": None
        }
        
    # Condition (a): Overlap <= 5 days (e.g. chronological transition)
    if overlap_days <= 5:
        rule_passed = "Rule A (chronological transition, overlap <= 5d)"
        status = "ACCEPTED"
        evidence_str = f"overlap_days={overlap_days} <= 5 (chronological migration)"
    else:
        # Condition (b): Price agreement on overlapping records
        if overlapping_records_df is not None and not overlapping_records_df.empty:
            total_matches = len(overlapping_records_df)
            exact_matches = int((overlapping_records_df["price_1"] == overlapping_records_df["price_2"]).sum())
            price_agreement = round(float(exact_matches / total_matches), 4) if total_matches > 0 else 0.0
            
            if price_agreement >= 0.95:
                rule_passed = "Rule B (overlapping concordance >= 95%)"
                status = "ACCEPTED"
                evidence_str = f"overlap_days={overlap_days} > 5; price_agreement={price_agreement:.4f} >= 0.95 ({exact_matches}/{total_matches})"
            else:
                rule_passed = "Failed Rule B (price agreement < 95%)"
                status = "UNMAPPED/REVIEW"
                evidence_str = f"overlap_days={overlap_days} > 5; price_agreement={price_agreement:.4f} < 0.95 ({exact_matches}/{total_matches})"
        else:
            rule_passed = "Failed Rule B (no overlap price records)"
            status = "UNMAPPED/REVIEW"
            evidence_str = f"overlap_days={overlap_days} > 5; missing overlapping price data for verification"
            
    is_accepted = (status == "ACCEPTED")
    return is_accepted, {
        "status": status,
        "rule": rule_passed,
        "evidence": evidence_str,
        "overlap_days": overlap_days,
        "price_agreement": price_agreement
    }


def load_market_aliases(csv_path: Union[str, Path]) -> pd.DataFrame:
    """
    Loads and validates the market alias reference table from CSV.
    Ensures all required columns are present and strips whitespace.
    """
    path_obj = Path(csv_path)
    if not path_obj.exists():
        raise FileNotFoundError(f"Market aliases reference file not found: {path_obj}")
        
    df = pd.read_csv(path_obj)
    missing_cols = [c for c in MARKET_ALIAS_COLUMNS if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Market aliases CSV is missing required columns: {missing_cols}")
        
    # Clean whitespace on string columns
    for c in ["district", "market_raw", "market_canonical", "rule", "status"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()
            
    return df


def build_alias_mapping(alias_df: pd.DataFrame) -> Dict[Tuple[str, str], str]:
    """
    Builds a lookup mapping from accepted market aliases:
        (district_lower, raw_market_lower) -> canonical_market_name
    Only records with status == 'ACCEPTED' are included.
    """
    mapping: Dict[Tuple[str, str], str] = {}
    accepted_df = alias_df[alias_df["status"].str.upper() == "ACCEPTED"]
    
    for _, row in accepted_df.iterrows():
        key = (row["district"].strip().lower(), row["market_raw"].strip().lower())
        mapping[key] = row["market_canonical"].strip()
        
    return mapping


def apply_market_canonicalization(
    df: pd.DataFrame,
    alias_source: Union[pd.DataFrame, Dict[Tuple[str, str], str], str, Path],
    district_col: str = "District",
    market_col: str = "Market",
    raw_market_col: str = "Market_Raw"
) -> pd.DataFrame:
    """
    Applies evidence-based market canonicalization to a DataFrame:
    1. Preserves original market name in `raw_market_col` (e.g. 'Market_Raw').
    2. Maps `market_col` to `market_canonical` using the accepted alias mapping.
    3. If no accepted alias is found, leaves `market_col` identical to `raw_market_col`.
    
    Pure function: returns a new DataFrame copy.
    """
    out_df = df.copy()
    
    # 1. Preserve original name
    if raw_market_col not in out_df.columns:
        out_df[raw_market_col] = out_df[market_col]
        
    # 2. Resolve mapping
    if isinstance(alias_source, dict):
        mapping = alias_source
    elif isinstance(alias_source, pd.DataFrame):
        mapping = build_alias_mapping(alias_source)
    else:
        alias_df = load_market_aliases(alias_source)
        mapping = build_alias_mapping(alias_df)
        
    # 3. Canonicalize Market column
    def _map_row(row):
        dist = str(row[district_col]).strip().lower()
        raw_mkt = str(row[raw_market_col]).strip().lower()
        return mapping.get((dist, raw_mkt), row[raw_market_col])
        
    out_df[market_col] = out_df.apply(_map_row, axis=1)
    return out_df

