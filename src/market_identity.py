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


# =============================================================================
# Candidate Policy v2.1 Engine Extensions
# =============================================================================

CANDIDATE_ALIAS_COLUMNS_V21: List[str] = MARKET_ALIAS_COLUMNS + [
    "evidence_known_date"
]


def evaluate_alias_evidence_v21(
    district_1: str,
    name_1: str,
    first_date_1: str,
    last_date_1: str,
    district_2: str,
    name_2: str,
    first_date_2: str,
    last_date_2: str,
    overlapping_records_df: Optional[pd.DataFrame] = None,
    max_migration_gap_days: int = 14,
    max_migration_overlap_days: int = 7,
    min_concordance_keys: int = 5,
    min_price_agreement: float = 0.95
) -> Tuple[bool, Dict[str, Any]]:
    """
    Evaluates whether two raw market names satisfy Candidate Policy v2.1.

    Candidate v2.1 introduces strict, defensive criteria:
      1. Missing Field Check: Rejects empty/null district or market names.
      2. Malformed Date Check: Rejects unparseable dates or inverted date ranges
         (first_date > last_date).
      3. Strict District Match: Rejects cross-district candidate pairs.
      4. Exact Normalized Name Match: Requires identical base token strings.
         Phonetic variations (e.g. Baripaal vs Varipaal) are rejected for automatic
         aliasing without official gazette verification.
      5. Candidate Rule A (Bounded Chronological Migration):
         - Requires near-contiguous transition: gap_days <= max_migration_gap_days
           (default 14 calendar days). Unbounded hiatus (e.g. Purwa 205d gap) fails.
         - Overlap during migration must be bounded: overlap_days <= max_migration_overlap_days
           (default 7 days).
         - If overlapping records exist during migration, exact price agreement
           must be >= min_price_agreement.
      6. Candidate Rule B (Concordance Overlap):
         - Applied when overlap_days > max_migration_overlap_days.
         - Requires a minimum sample of overlapping natural keys:
           len(overlapping_records_df) >= min_concordance_keys (default 5 keys).
         - Requires exact-price agreement >= min_price_agreement (default 95.0%).

    Returns:
        (is_accepted: bool, evidence_dict: dict)
    """
    # 1. Missing field check
    d1 = str(district_1).strip().lower() if district_1 is not None else ""
    d2 = str(district_2).strip().lower() if district_2 is not None else ""
    n1 = str(name_1).strip() if name_1 is not None else ""
    n2 = str(name_2).strip() if name_2 is not None else ""

    if not d1 or not d2 or not n1 or not n2:
        return False, {
            "status": "UNMAPPED/REVIEW",
            "rule": "Failed (missing required identity field)",
            "evidence": "One or more required identity fields (district, names) are empty or null.",
            "overlap_days": 0,
            "price_agreement": None
        }

    # 2. Date parsing and malformed date check
    try:
        dt1_start = pd.to_datetime(first_date_1)
        dt1_end = pd.to_datetime(last_date_1)
        dt2_start = pd.to_datetime(first_date_2)
        dt2_end = pd.to_datetime(last_date_2)
    except Exception as e:
        return False, {
            "status": "UNMAPPED/REVIEW",
            "rule": "Failed (unparseable date)",
            "evidence": f"Date parsing failed: {e}",
            "overlap_days": 0,
            "price_agreement": None
        }

    if dt1_start > dt1_end or dt2_start > dt2_end:
        return False, {
            "status": "UNMAPPED/REVIEW",
            "rule": "Failed (inverted date range: first_date > last_date)",
            "evidence": f"Inverted range detected: [{first_date_1} > {last_date_1}] or [{first_date_2} > {last_date_2}]",
            "overlap_days": 0,
            "price_agreement": None
        }

    # 3. District check
    if d1 != d2:
        return False, {
            "status": "UNMAPPED/REVIEW",
            "rule": "Failed (different districts)",
            "evidence": f"District mismatch: '{district_1}' vs '{district_2}'",
            "overlap_days": 0,
            "price_agreement": None
        }

    # 4. Normalised name check
    norm_1 = normalize_market_name(n1)
    norm_2 = normalize_market_name(n2)
    if norm_1 != norm_2 or not norm_1:
        return False, {
            "status": "UNMAPPED/REVIEW",
            "rule": "Failed (normalised names mismatch)",
            "evidence": f"Normalized mismatch: '{norm_1}' vs '{norm_2}'",
            "overlap_days": 0,
            "price_agreement": None
        }

    # Order intervals by start date (older vs newer)
    if dt1_start <= dt2_start:
        older_start, older_end = dt1_start, dt1_end
        newer_start, newer_end = dt2_start, dt2_end
    else:
        older_start, older_end = dt2_start, dt2_end
        newer_start, newer_end = dt1_start, dt1_end

    overlap_start = max(older_start, newer_start)
    overlap_end = min(older_end, newer_end)

    if overlap_end >= overlap_start:
        overlap_days = int((overlap_end - overlap_start).days) + 1
        gap_days = -overlap_days
    else:
        overlap_days = 0
        gap_days = int((newer_start - older_end).days)

    price_agreement: Optional[float] = None

    # Calculate price agreement if overlap dataframe is provided
    total_matches = 0
    exact_matches = 0
    if overlapping_records_df is not None and not overlapping_records_df.empty:
        total_matches = len(overlapping_records_df)
        if "price_1" in overlapping_records_df.columns and "price_2" in overlapping_records_df.columns:
            exact_matches = int((overlapping_records_df["price_1"] == overlapping_records_df["price_2"]).sum())
            price_agreement = round(float(exact_matches / total_matches), 4) if total_matches > 0 else 0.0

    # Evaluation: Case A - Migration / Near-Contiguous handover
    if overlap_days <= max_migration_overlap_days:
        if gap_days > max_migration_gap_days:
            return False, {
                "status": "UNMAPPED/REVIEW",
                "rule": f"Candidate Rule A Failed (hiatus={gap_days}d > {max_migration_gap_days}d limit)",
                "evidence": f"Unbounded hiatus: {gap_days} days gap between older end ({older_end.strftime('%Y-%m-%d')}) and newer start ({newer_start.strftime('%Y-%m-%d')}). 0 overlap keys.",
                "overlap_days": overlap_days,
                "price_agreement": price_agreement
            }

        # If there are overlapping records during the short handover, verify concordance
        if total_matches > 0 and price_agreement is not None:
            if price_agreement < min_price_agreement:
                return False, {
                    "status": "UNMAPPED/REVIEW",
                    "rule": f"Failed Candidate Rule A (handover price divergence < {min_price_agreement:.0%})",
                    "evidence": f"overlap_days={overlap_days} <= {max_migration_overlap_days}; price_agreement={price_agreement:.4f} < {min_price_agreement} ({exact_matches}/{total_matches})",
                    "overlap_days": overlap_days,
                    "price_agreement": price_agreement
                }

        evidence_str = (
            f"gap_days={gap_days} <= {max_migration_gap_days}; "
            f"overlap_days={overlap_days} <= {max_migration_overlap_days} (verified chronological migration)"
        )
        if total_matches > 0 and price_agreement is not None:
            evidence_str += f"; price_agreement={price_agreement:.4f} ({exact_matches}/{total_matches})"

        return True, {
            "status": "ACCEPTED",
            "rule": "Candidate Rule A (verified migration handover)",
            "evidence": evidence_str,
            "overlap_days": overlap_days,
            "price_agreement": price_agreement
        }

    # Evaluation: Case B - Extended Co-existence / Concordance Overlap
    else:
        if total_matches < min_concordance_keys:
            return False, {
                "status": "UNMAPPED/REVIEW",
                "rule": f"Failed Candidate Rule B (insufficient overlapping keys: {total_matches} < {min_concordance_keys})",
                "evidence": f"overlap_days={overlap_days} > {max_migration_overlap_days}; overlapping keys count {total_matches} below required minimum of {min_concordance_keys}",
                "overlap_days": overlap_days,
                "price_agreement": price_agreement
            }

        if price_agreement is not None and price_agreement >= min_price_agreement:
            return True, {
                "status": "ACCEPTED",
                "rule": f"Candidate Rule B (overlapping concordance >= {min_price_agreement:.0%})",
                "evidence": f"overlap_days={overlap_days} > {max_migration_overlap_days}; price_agreement={price_agreement:.4f} >= {min_price_agreement} ({exact_matches}/{total_matches})",
                "overlap_days": overlap_days,
                "price_agreement": price_agreement
            }
        else:
            agreement_val = price_agreement if price_agreement is not None else 0.0
            return False, {
                "status": "UNMAPPED/REVIEW",
                "rule": f"Failed Candidate Rule B (price agreement {agreement_val:.2%} < {min_price_agreement:.0%})",
                "evidence": f"overlap_days={overlap_days} > {max_migration_overlap_days}; price_agreement={agreement_val:.4f} < {min_price_agreement} ({exact_matches}/{total_matches})",
                "overlap_days": overlap_days,
                "price_agreement": price_agreement
            }


def validate_alias_table(alias_df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Performs comprehensive defensive validation of an alias table:
      1. Schema compliance: All MARKET_ALIAS_COLUMNS must be present.
      2. Non-empty identities: district, market_raw, market_canonical must be populated.
      3. Inverted date check: first_date <= last_date for valid date strings.
      4. Duplicate conflicting mappings: The same (district, market_raw) must NOT
         map to multiple distinct market_canonical values with status ACCEPTED.
      5. Cycle detection: A -> B and B -> A or cyclic alias chains.

    Returns:
        (is_valid: bool, issues: List[str])
    """
    issues: List[str] = []

    # 1. Schema check
    missing_cols = [c for c in MARKET_ALIAS_COLUMNS if c not in alias_df.columns]
    if missing_cols:
        issues.append(f"Missing required columns: {missing_cols}")
        return False, issues

    # 2. Non-empty identities
    for col in ["district", "market_raw", "market_canonical", "status"]:
        null_count = int(alias_df[col].isna().sum())
        empty_count = int((alias_df[col].astype(str).str.strip() == "").sum())
        if null_count > 0 or empty_count > 0:
            issues.append(f"Column '{col}' has {null_count} nulls and {empty_count} empty strings")

    # 3. Inverted dates
    for idx, row in alias_df.iterrows():
        fd, ld = str(row["first_date"]).strip(), str(row["last_date"]).strip()
        if fd and ld and fd != "nan" and ld != "nan":
            try:
                if pd.to_datetime(fd) > pd.to_datetime(ld):
                    issues.append(f"Row {idx}: Inverted date range [{fd} > {ld}] for {row['market_raw']}")
            except Exception:
                pass

    # 4. Duplicate conflicting mappings
    accepted_df = alias_df[alias_df["status"].astype(str).str.upper() == "ACCEPTED"]
    mapping_groups = accepted_df.groupby([
        accepted_df["district"].astype(str).str.strip().str.lower(),
        accepted_df["market_raw"].astype(str).str.strip().str.lower()
    ])
    for (d, raw_m), group in mapping_groups:
        canonical_targets = set(group["market_canonical"].astype(str).str.strip().str.lower())
        if len(canonical_targets) > 1:
            issues.append(
                f"Conflicting duplicate mapping: ({d}, {raw_m}) maps to multiple canonical targets: {canonical_targets}"
            )

    # 5. Cycle detection
    # Graph of accepted non-identity mappings: raw -> canonical
    adj: Dict[Tuple[str, str], Tuple[str, str]] = {}
    for _, row in accepted_df.iterrows():
        dist_key = row["district"].strip().lower()
        raw_key = row["market_raw"].strip().lower()
        can_key = row["market_canonical"].strip().lower()
        if raw_key != can_key:
            adj[(dist_key, raw_key)] = (dist_key, can_key)

    for start_node in adj:
        visited = set()
        curr = start_node
        while curr in adj:
            if curr in visited:
                issues.append(f"Cycle detected in alias mapping starting at {start_node}: cycle node {curr}")
                break
            visited.add(curr)
            curr = adj[curr]

    is_valid = len(issues) == 0
    return is_valid, issues


def build_causal_alias_mapping(
    alias_df: pd.DataFrame,
    as_of_date: Optional[Union[str, pd.Timestamp]] = None
) -> Dict[Tuple[str, str], str]:
    """
    Builds an alias lookup mapping respecting information availability as of cutoff date.

    If `as_of_date` is provided:
      - Only alias mappings whose evidence was known on or before `as_of_date`
        (using `evidence_known_date` if present, else `first_date`) are applied.
      - Any alias whose evidence became available strictly after `as_of_date`
        is omitted, preventing lookahead bias in historical benchmark folds.

    Returns:
        (district_lower, market_raw_lower) -> market_canonical
    """
    mapping: Dict[Tuple[str, str], str] = {}
    accepted_df = alias_df[alias_df["status"].astype(str).str.upper() == "ACCEPTED"]

    as_of_dt = pd.to_datetime(as_of_date) if as_of_date is not None else None

    for _, row in accepted_df.iterrows():
        dist_key = str(row["district"]).strip().lower()
        raw_key = str(row["market_raw"]).strip().lower()
        can_target = str(row["market_canonical"]).strip()

        # Check information availability
        if as_of_dt is not None:
            known_date_col = "evidence_known_date" if "evidence_known_date" in row and pd.notna(row["evidence_known_date"]) else "first_date"
            date_val = str(row.get(known_date_col, "")).strip()
            if date_val and date_val != "nan":
                try:
                    known_dt = pd.to_datetime(date_val)
                    if known_dt > as_of_dt:
                        # Evidence was NOT available by cutoff date; withhold mapping
                        continue
                except Exception:
                    pass

        mapping[(dist_key, raw_key)] = can_target

    return mapping


def apply_market_canonicalization_v21(
    df: pd.DataFrame,
    alias_source: Union[pd.DataFrame, Dict[Tuple[str, str], str], str, Path],
    district_col: str = "District",
    market_col: str = "Market",
    raw_market_col: str = "Market_Raw",
    as_of_date: Optional[Union[str, pd.Timestamp]] = None
) -> pd.DataFrame:
    """
    Applies Candidate v2.1 market canonicalization supporting causal cutoff filters:
      1. Preserves original market name in `raw_market_col` (e.g. 'Market_Raw').
      2. Maps `market_col` to `market_canonical` using accepted aliases.
      3. If `as_of_date` is set, withholds mappings whose evidence was unknown at cutoff.
      4. If unmapped, assigns original name and preserves status.

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
        mapping = build_causal_alias_mapping(alias_source, as_of_date=as_of_date)
    else:
        alias_df = load_market_aliases(alias_source)
        mapping = build_causal_alias_mapping(alias_df, as_of_date=as_of_date)

    # 3. Canonicalize Market column
    def _map_row(row):
        dist = str(row[district_col]).strip().lower()
        raw_mkt = str(row[raw_market_col]).strip().lower()
        return mapping.get((dist, raw_mkt), row[raw_market_col])

    out_df[market_col] = out_df.apply(_map_row, axis=1)
    return out_df
