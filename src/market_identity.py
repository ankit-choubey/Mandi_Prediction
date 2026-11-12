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
    "evidence_known_date",
    "assumed_known_date",
    "knowledge_provenance"
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
      2. Malformed Date Check: Rejects unparseable dates, NaT, or inverted date ranges
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
         - If overlapping records exist during migration, verified price columns
           must be present, finite, and exact price agreement must be >= min_price_agreement.
      6. Candidate Rule B (Concordance Overlap):
         - Applied when overlap_days > max_migration_overlap_days.
         - Requires verified price columns ('price_1', 'price_2') with finite numeric data.
         - Requires a minimum sample of unique natural keys:
           unique_keys >= min_concordance_keys (default 5 keys).
         - Requires exact-price agreement >= min_price_agreement (default 95.0%).

    Returns:
        (is_accepted: bool, evidence_dict: dict)
    """
    # 1. Missing field check
    def _is_empty_or_null(v: Any) -> bool:
        if v is None:
            return True
        s = str(v).strip().lower()
        return s in {"", "none", "nan", "null", "<na>"}

    if _is_empty_or_null(district_1) or _is_empty_or_null(district_2) or \
       _is_empty_or_null(name_1) or _is_empty_or_null(name_2):
        return False, {
            "status": "UNMAPPED/REVIEW",
            "rule": "Failed (missing required identity field)",
            "evidence": "One or more required identity fields (district, names) are empty or null.",
            "overlap_days": 0,
            "price_agreement": None
        }

    d1 = str(district_1).strip().lower()
    d2 = str(district_2).strip().lower()
    n1 = str(name_1).strip()
    n2 = str(name_2).strip()

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

    if pd.isna(dt1_start) or pd.isna(dt1_end) or pd.isna(dt2_start) or pd.isna(dt2_end):
        return False, {
            "status": "UNMAPPED/REVIEW",
            "rule": "Failed (NaT date detected)",
            "evidence": f"One or more dates evaluated to NaT: [{first_date_1}, {last_date_1}, {first_date_2}, {last_date_2}]",
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
    has_overlap_df = overlapping_records_df is not None and not overlapping_records_df.empty
    total_unique_keys = 0
    exact_matches = 0

    if has_overlap_df:
        # Check price column presence
        if "price_1" not in overlapping_records_df.columns or "price_2" not in overlapping_records_df.columns:
            return False, {
                "status": "UNMAPPED/REVIEW",
                "rule": "Failed (missing required price columns)",
                "evidence": "Overlapping records provided but missing 'price_1' or 'price_2' column.",
                "overlap_days": overlap_days,
                "price_agreement": None
            }

        # Validate finite numeric prices
        p1 = pd.to_numeric(overlapping_records_df["price_1"], errors="coerce")
        p2 = pd.to_numeric(overlapping_records_df["price_2"], errors="coerce")
        valid_price_mask = p1.notna() & p2.notna()

        if not valid_price_mask.all():
            invalid_cnt = int((~valid_price_mask).sum())
            return False, {
                "status": "UNMAPPED/REVIEW",
                "rule": "Failed (nonfinite or unparseable price values)",
                "evidence": f"Overlapping records contain {invalid_cnt} nonfinite or unparseable price values.",
                "overlap_days": overlap_days,
                "price_agreement": None
            }

        # Count unique natural keys to prevent many-to-many joined row inflation
        key_candidates = ["Arrival_Date", "Commodity", "Variety", "Grade"]
        available_keys = [c for c in key_candidates if c in overlapping_records_df.columns]
        if available_keys:
            # Deduplicate by unique natural key
            dedup_df = overlapping_records_df.drop_duplicates(subset=available_keys).copy()
        else:
            dedup_df = overlapping_records_df.copy()

        total_unique_keys = len(dedup_df)
        p1_dedup = pd.to_numeric(dedup_df["price_1"], errors="coerce")
        p2_dedup = pd.to_numeric(dedup_df["price_2"], errors="coerce")
        exact_matches = int((p1_dedup == p2_dedup).sum())
        price_agreement = round(float(exact_matches / total_unique_keys), 4) if total_unique_keys > 0 else 0.0

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
        if has_overlap_df and total_unique_keys > 0:
            if price_agreement is not None and price_agreement < min_price_agreement:
                return False, {
                    "status": "UNMAPPED/REVIEW",
                    "rule": f"Failed Candidate Rule A (handover price divergence < {min_price_agreement:.0%})",
                    "evidence": f"overlap_days={overlap_days} <= {max_migration_overlap_days}; price_agreement={price_agreement:.4f} < {min_price_agreement} ({exact_matches}/{total_unique_keys})",
                    "overlap_days": overlap_days,
                    "price_agreement": price_agreement
                }

        evidence_str = (
            f"gap_days={gap_days} <= {max_migration_gap_days}; "
            f"overlap_days={overlap_days} <= {max_migration_overlap_days} (verified chronological migration)"
        )
        if has_overlap_df and total_unique_keys > 0 and price_agreement is not None:
            evidence_str += f"; price_agreement={price_agreement:.4f} ({exact_matches}/{total_unique_keys} unique keys)"

        return True, {
            "status": "ACCEPTED",
            "rule": "Candidate Rule A (verified migration handover)",
            "evidence": evidence_str,
            "overlap_days": overlap_days,
            "price_agreement": price_agreement
        }

    # Evaluation: Case B - Extended Co-existence / Concordance Overlap
    else:
        if not has_overlap_df or total_unique_keys < min_concordance_keys:
            return False, {
                "status": "UNMAPPED/REVIEW",
                "rule": f"Failed Candidate Rule B (insufficient overlapping keys: {total_unique_keys} < {min_concordance_keys})",
                "evidence": f"overlap_days={overlap_days} > {max_migration_overlap_days}; unique overlapping keys count {total_unique_keys} below required minimum of {min_concordance_keys}",
                "overlap_days": overlap_days,
                "price_agreement": price_agreement
            }

        if price_agreement is not None and price_agreement >= min_price_agreement:
            return True, {
                "status": "ACCEPTED",
                "rule": f"Candidate Rule B (overlapping concordance >= {min_price_agreement:.0%})",
                "evidence": f"overlap_days={overlap_days} > {max_migration_overlap_days}; price_agreement={price_agreement:.4f} >= {min_price_agreement} ({exact_matches}/{total_unique_keys} unique keys)",
                "overlap_days": overlap_days,
                "price_agreement": price_agreement
            }
        else:
            agreement_val = price_agreement if price_agreement is not None else 0.0
            return False, {
                "status": "UNMAPPED/REVIEW",
                "rule": f"Failed Candidate Rule B (price agreement {agreement_val:.2%} < {min_price_agreement:.0%})",
                "evidence": f"overlap_days={overlap_days} > {max_migration_overlap_days}; price_agreement={agreement_val:.4f} < {min_price_agreement} ({exact_matches}/{total_unique_keys} unique keys)",
                "overlap_days": overlap_days,
                "price_agreement": price_agreement
            }


def validate_alias_table(alias_df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Performs comprehensive defensive, fail-closed validation of an alias table:
      1. Schema compliance: All MARKET_ALIAS_COLUMNS must be present.
      2. Non-empty/non-null identities: district, market_raw, market_canonical, status.
         Rejects pandas NaN, None, empty strings, and string 'nan'/'none'/'null'.
      3. Valid status domain: status must be one of {'ACCEPTED', 'UNMAPPED/REVIEW', 'REJECTED'}.
      4. Strict Date Validation:
         - All date fields present ('first_date', 'last_date', 'evidence_known_date',
           'assumed_known_date') must be parseable dates if non-empty; malformed strings
           or NaT values fail validation.
         - Inverted range check: first_date <= last_date.
      5. Duplicate conflicting mappings: The same (district, market_raw) must NOT
         map to multiple distinct market_canonical values with status ACCEPTED.
      6. Nonterminal mapping chains: A -> B and B -> C (where A != B and B != C)
         with status ACCEPTED are rejected to avoid ambiguous transitive expansion.
      7. Cycle detection: A -> B and B -> A or multi-hop cyclic alias chains.

    Returns:
        (is_valid: bool, issues: List[str])
    """
    issues: List[str] = []

    # 1. Schema check
    missing_cols = [c for c in MARKET_ALIAS_COLUMNS if c not in alias_df.columns]
    if missing_cols:
        issues.append(f"Missing required columns: {missing_cols}")
        return False, issues

    # Helper for null / string-null check
    def _is_null_like(val: Any) -> bool:
        if val is None or pd.isna(val):
            return True
        s = str(val).strip().lower()
        return s in {"", "none", "nan", "null", "<na>"}

    # 2. Non-empty identities & valid status
    valid_statuses = {"ACCEPTED", "UNMAPPED/REVIEW", "REJECTED"}
    for idx, row in alias_df.iterrows():
        for col in ["district", "market_raw", "market_canonical", "status"]:
            if _is_null_like(row.get(col)):
                issues.append(f"Row {idx}: Column '{col}' is null or empty: {repr(row.get(col))}")

        st = str(row.get("status", "")).strip().upper()
        if st and st not in valid_statuses:
            issues.append(f"Row {idx}: Invalid status '{row.get('status')}'. Must be one of {valid_statuses}")

    # 3. Date validity & inverted dates
    date_cols_to_check = [c for c in ["first_date", "last_date", "evidence_known_date", "assumed_known_date"] if c in alias_df.columns]

    for idx, row in alias_df.iterrows():
        parsed_dates = {}
        for col in date_cols_to_check:
            val = row.get(col)
            if not _is_null_like(val):
                try:
                    dt = pd.to_datetime(val)
                    if pd.isna(dt):
                        issues.append(f"Row {idx}: Date field '{col}' evaluated to NaT: {repr(val)}")
                    else:
                        parsed_dates[col] = dt
                except Exception as e:
                    issues.append(f"Row {idx}: Malformed/unparseable date in '{col}': {repr(val)} ({e})")

        # Inverted date check between first_date and last_date
        if "first_date" in parsed_dates and "last_date" in parsed_dates:
            if parsed_dates["first_date"] > parsed_dates["last_date"]:
                issues.append(
                    f"Row {idx}: Inverted date range [{row.get('first_date')} > {row.get('last_date')}] for '{row.get('market_raw')}'"
                )

    # 4. Duplicate conflicting mappings
    status_series = alias_df["status"].astype(str).str.strip().str.upper()
    accepted_df = alias_df[status_series == "ACCEPTED"]

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

    # 5. Nonterminal mapping chains & Cycle detection
    # Map of accepted nonidentity mappings: (district, raw) -> (district, canonical)
    non_identity_edges: Dict[Tuple[str, str], Tuple[str, str]] = {}
    for idx, row in accepted_df.iterrows():
        dist_key = str(row["district"]).strip().lower()
        raw_key = str(row["market_raw"]).strip().lower()
        can_key = str(row["market_canonical"]).strip().lower()
        if raw_key != can_key:
            src = (dist_key, raw_key)
            dst = (dist_key, can_key)
            non_identity_edges[src] = dst

    # Check for nonterminal mapping chains: A -> B and B -> C where A != B and B != C
    for src, dst in non_identity_edges.items():
        if dst in non_identity_edges:
            issues.append(
                f"Nonterminal mapping chain detected: {src} -> {dst} -> {non_identity_edges[dst]}. "
                f"Accepted mappings must be terminal single-hop mappings."
            )

    # Check for cycles
    for start_node in non_identity_edges:
        visited = set()
        curr = start_node
        while curr in non_identity_edges:
            if curr in visited:
                issues.append(f"Cycle detected in alias mapping starting at {start_node}: cycle node {curr}")
                break
            visited.add(curr)
            curr = non_identity_edges[curr]

    is_valid = len(issues) == 0
    return is_valid, issues


def build_causal_alias_mapping(
    alias_df: pd.DataFrame,
    as_of_date: Optional[Union[str, pd.Timestamp]] = None,
    evidence_mode: str = "verified"
) -> Dict[Tuple[str, str], str]:
    """
    Builds an alias lookup mapping respecting information availability as of cutoff date.

    Fail-Closed Validation:
      Validates alias_df before building mapping. Raises ValueError if validation fails.

    Evidence Modes:
      - 'verified' (default, fail-closed): Requires dated publication/retrieval evidence
        in 'evidence_known_date'. If 'as_of_date' is supplied and 'evidence_known_date' is
        missing, empty, unparseable, or strictly after 'as_of_date', nonidentity mappings
        are strictly WITHHELD. NEVER falls back to 'first_date'.
      - 'assumed': Uses 'assumed_known_date' (or 'evidence_known_date' if present) for
        sensitivity analysis of assumed observation handover timings.
      - 'retrospective': Applies all accepted aliases irrespective of cutoff date.

    Returns:
        (district_lower, market_raw_lower) -> market_canonical
    """
    is_valid, issues = validate_alias_table(alias_df)
    if not is_valid:
        raise ValueError(f"Cannot build alias mapping: table failed defensive validation:\n" + "\n".join(issues))

    evidence_mode_clean = str(evidence_mode).strip().lower()
    if evidence_mode_clean not in {"verified", "assumed", "retrospective"}:
        raise ValueError(
            f"Unsupported evidence_mode: '{evidence_mode}'. Must be 'verified', 'assumed', or 'retrospective'."
        )

    mapping: Dict[Tuple[str, str], str] = {}
    status_series = alias_df["status"].astype(str).str.strip().str.upper()
    accepted_df = alias_df[status_series == "ACCEPTED"]

    as_of_dt = pd.to_datetime(as_of_date) if as_of_date is not None else None

    def _is_null_like(val: Any) -> bool:
        if val is None or pd.isna(val):
            return True
        s = str(val).strip().lower()
        return s in {"", "none", "nan", "null", "<na>"}

    for _, row in accepted_df.iterrows():
        dist_key = str(row["district"]).strip().lower()
        raw_key = str(row["market_raw"]).strip().lower()
        can_target = str(row["market_canonical"]).strip()
        can_key = can_target.lower()

        # Identity mappings (canonical anchors) are structural no-ops: always active
        if raw_key == can_key:
            mapping[(dist_key, raw_key)] = can_target
            continue

        # Non-identity alias mapping: check as-of information availability
        if as_of_dt is not None and evidence_mode_clean != "retrospective":
            if evidence_mode_clean == "verified":
                # In verified mode, require evidence_known_date
                val = row.get("evidence_known_date")
                if _is_null_like(val):
                    # Fail-closed: missing verified publication receipt withholds merge
                    continue
                try:
                    known_dt = pd.to_datetime(val)
                    if pd.isna(known_dt) or known_dt > as_of_dt:
                        continue
                except Exception:
                    continue

            elif evidence_mode_clean == "assumed":
                # In assumed mode, look for assumed_known_date, then evidence_known_date
                val = row.get("assumed_known_date")
                if _is_null_like(val):
                    val = row.get("evidence_known_date")
                if _is_null_like(val):
                    continue
                try:
                    known_dt = pd.to_datetime(val)
                    if pd.isna(known_dt) or known_dt > as_of_dt:
                        continue
                except Exception:
                    continue

        mapping[(dist_key, raw_key)] = can_target

    return mapping


def apply_market_canonicalization_v21(
    df: pd.DataFrame,
    alias_source: Union[pd.DataFrame, Dict[Tuple[str, str], str], str, Path],
    district_col: str = "District",
    market_col: str = "Market",
    raw_market_col: str = "Market_Raw",
    as_of_date: Optional[Union[str, pd.Timestamp]] = None,
    evidence_mode: str = "verified"
) -> pd.DataFrame:
    """
    Applies Candidate v2.1 market canonicalization supporting causal cutoff filters:
      1. Preserves original market name in `raw_market_col` (e.g. 'Market_Raw').
      2. Maps `market_col` to `market_canonical` using accepted aliases.
      3. If `as_of_date` is set, withholds nonidentity mappings whose evidence was
         unknown at cutoff under the specified evidence_mode ('verified', 'assumed', 'retrospective').
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
        mapping = build_causal_alias_mapping(alias_source, as_of_date=as_of_date, evidence_mode=evidence_mode)
    else:
        alias_df = load_market_aliases(alias_source)
        mapping = build_causal_alias_mapping(alias_df, as_of_date=as_of_date, evidence_mode=evidence_mode)

    # 3. Canonicalize Market column
    def _map_row(row):
        dist = str(row[district_col]).strip().lower()
        raw_mkt = str(row[raw_market_col]).strip().lower()
        return mapping.get((dist, raw_mkt), row[raw_market_col])

    out_df[market_col] = out_df.apply(_map_row, axis=1)
    return out_df
