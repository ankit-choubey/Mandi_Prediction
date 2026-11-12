"""
Identity Comparison and Forensic Reclassification Engine.

Provides testable, shared helper functions for:
1. Pipeline manifest nested metric extraction and row conservation assertions.
2. Disjoint, mutually exclusive reclassification of in-window Excel records
   against cleaned panels and raw arrivals.
3. Causal train-only eligibility and forward target availability sensitivity
   reconstructed BEFORE the full-history low-observation floor.
4. Future mutation invariance verification.
"""

from typing import Any, Dict, List, Optional, Set, Tuple, Union
import hashlib
import numpy as np
import pandas as pd

from src.market_identity import (
    build_causal_alias_mapping,
    apply_market_canonicalization_v21,
    validate_alias_table,
    normalize_market_name
)
from src.baselines import (
    check_serving_recency,
    extract_target_vectorized,
    evaluate_series_train_eligibility
)

# Standard declared fold definitions across the benchmark
DEFAULT_FOLD_BOUNDS: Dict[str, Dict[str, str]] = {
    "F1": {"train_end": "2024-12-31", "test_start": "2025-01-08", "test_end": "2025-06-30"},
    "F2": {"train_end": "2025-06-30", "test_start": "2025-07-08", "test_end": "2025-10-31"},
    "F3": {"train_end": "2025-12-18", "test_start": "2025-12-26", "test_end": "2026-03-31"},
    "F4": {"train_end": "2026-03-31", "test_start": "2026-04-08", "test_end": "2026-09-30"}
}

FOCUS_CROPS = ["Wheat", "Potato", "Onion", "Tomato", "Paddy(Dhan)(Common)", "Rice"]


def extract_manifest_dispositions(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts disposition metrics from a pipeline manifest dictionary without
    measurement fallback constants.

    Enforces fail-closed schema checks and strict row conservation:
      accepted_rows + duplicates_deduplicated + conflicts_quarantined +
      low_obs_dropped + invalid_dropped_rows == total_raw_rows

    Raises:
        KeyError: If required manifest or summary_metrics fields are missing.
        ValueError: If row conservation identity is violated.
    """
    if "summary_metrics" not in manifest:
        raise KeyError("Manifest is missing required top-level section: 'summary_metrics'")

    sm = manifest["summary_metrics"]
    required_keys = [
        "total_raw_rows",
        "total_valid_parsed_rows",
        "total_dropped_raw_rows",
        "exact_duplicates_deduplicated",
        "ambiguous_same_grade_excluded_rows",
        "low_observation_series_dropped_rows",
        "final_clean_rows"
    ]
    missing = [k for k in required_keys if k not in sm]
    if missing:
        raise KeyError(f"summary_metrics is missing required fields: {missing}")

    raw_rows_in = int(sm["total_raw_rows"])
    valid_parsed_rows = int(sm["total_valid_parsed_rows"])
    invalid_dropped = int(sm["total_dropped_raw_rows"])
    duplicates = int(sm["exact_duplicates_deduplicated"])
    conflicts = int(sm["ambiguous_same_grade_excluded_rows"])
    low_obs = int(sm["low_observation_series_dropped_rows"])
    accepted = int(sm["final_clean_rows"])

    # Disjoint partition conservation check:
    # accepted + duplicates + conflicts + low_obs + invalid == raw_rows_in
    sum_dispositions = accepted + duplicates + conflicts + low_obs + invalid_dropped
    if sum_dispositions != raw_rows_in:
        raise ValueError(
            f"Row conservation assertion violated: "
            f"accepted ({accepted}) + dups ({duplicates}) + conflicts ({conflicts}) + "
            f"low_obs ({low_obs}) + invalid ({invalid_dropped}) = {sum_dispositions} != raw_in ({raw_rows_in})"
        )

    # Valid parsed conservation check:
    # accepted + duplicates + conflicts + low_obs == valid_parsed_rows
    sum_valid_dispositions = accepted + duplicates + conflicts + low_obs
    if sum_valid_dispositions != valid_parsed_rows:
        raise ValueError(
            f"Valid parsed row conservation violated: "
            f"accepted ({accepted}) + dups ({duplicates}) + conflicts ({conflicts}) + "
            f"low_obs ({low_obs}) = {sum_valid_dispositions} != valid_parsed ({valid_parsed_rows})"
        )

    return {
        "raw_rows_in": raw_rows_in,
        "valid_parsed_rows": valid_parsed_rows,
        "invalid_dropped_rows": invalid_dropped,
        "duplicates_deduplicated": duplicates,
        "conflicts_quarantined": conflicts,
        "low_obs_dropped": low_obs,
        "accepted_rows": accepted,
        "row_conservation_verified": True
    }


def compare_panel_dispositions(
    v2_manifest: Dict[str, Any],
    v21_manifest: Dict[str, Any],
    df_v2: pd.DataFrame,
    df_v21: pd.DataFrame
) -> Dict[str, Any]:
    """
    Compares panel v2 and candidate panel v2.1 dispositions, series counts,
    and district-level totals using actual manifest fields and panel DataFrames.
    """
    m_v2 = extract_manifest_dispositions(v2_manifest)
    m_v21 = extract_manifest_dispositions(v21_manifest)

    districts = ["Ghaziabad", "Jhansi", "Kanpur", "Lucknow", "Unnao"]
    district_rows = []

    s_col_v2 = "series_id" if "series_id" in df_v2.columns else "Series_ID"
    s_col_v21 = "series_id" if "series_id" in df_v21.columns else "Series_ID"

    for d in districts:
        sub2 = df_v2[df_v2["District"].astype(str).str.strip().str.lower() == d.lower()]
        sub21 = df_v21[df_v21["District"].astype(str).str.strip().str.lower() == d.lower()]

        rows_v2 = len(sub2)
        rows_v21 = len(sub21)
        series_v2 = int(sub2[s_col_v2].nunique()) if rows_v2 > 0 else 0
        series_v21 = int(sub21[s_col_v21].nunique()) if rows_v21 > 0 else 0

        district_rows.append({
            "district": d,
            "rows_v2": rows_v2,
            "rows_v21": rows_v21,
            "row_delta": rows_v21 - rows_v2,
            "series_v2": series_v2,
            "series_v21": series_v21,
            "series_delta": series_v21 - series_v2
        })

    df_district_comp = pd.DataFrame(district_rows)

    overall_delta = {
        "raw_in_delta": m_v21["raw_rows_in"] - m_v2["raw_rows_in"],
        "duplicates_delta": m_v21["duplicates_deduplicated"] - m_v2["duplicates_deduplicated"],
        "conflicts_delta": m_v21["conflicts_quarantined"] - m_v2["conflicts_quarantined"],
        "low_obs_delta": m_v21["low_obs_dropped"] - m_v2["low_obs_dropped"],
        "accepted_delta": m_v21["accepted_rows"] - m_v2["accepted_rows"],
        "total_series_v2": int(df_v2[s_col_v2].nunique()),
        "total_series_v21": int(df_v21[s_col_v21].nunique()),
        "total_series_delta": int(df_v21[s_col_v21].nunique()) - int(df_v2[s_col_v2].nunique())
    }

    return {
        "v2_dispositions": m_v2,
        "v21_dispositions": m_v21,
        "overall_delta": overall_delta,
        "district_comparison": df_district_comp
    }


def classify_excel_against_panel(
    df_excel: pd.DataFrame,
    df_panel: pd.DataFrame,
    alias_mapping: Optional[Dict[Tuple[str, str], str]] = None,
    review_markets: Optional[Set[Tuple[str, str]]] = None,
    raw_valid_df: Optional[pd.DataFrame] = None,
    quarantined_keys: Optional[Set[Tuple]] = None,
    low_obs_keys: Optional[Set[Tuple]] = None,
    raw_keys: Optional[Set[Tuple]] = None,
    known_markets_by_district: Optional[Dict[str, Set[str]]] = None,
    price_tolerance: float = 1e-4,
    strict_panel_integrity: bool = True
) -> Dict[str, Any]:
    """
    Reclassifies in-window Excel rows against clean panel data and raw source data
    using a strict, mutually exclusive precedence order without normalizing away
    market distinctions:

      1. invalid: Missing date, unparseable date, or nonfinite/non-positive price.
      2. matched_exact: Natural key matches panel row and |modal_excel - modal_panel| == 0.0 (or <= tolerance).
      3. matched_different: Natural key matches panel row, but |modal_excel - modal_panel| > tolerance.
      4. conflicting: Not in panel; dropped due to Strategy 2 price conflict in raw data.
      5. low_obs: Not in panel; dropped due to series having < 20 observations in full history.
      6. absent: Not in panel; market recognized in district, but natural key absent from raw data.
      7. spelling-review: Market is unmapped, under review, or unrecognized in district.
      8. other: Remaining unmatched rows.

    Parameters:
        df_excel: In-window Excel observations.
        df_panel: Validated panel DataFrame.
        alias_mapping: Dict mapping (district_lower, market_raw_lower) -> canonical_market_str.
        review_markets: Set of (district_lower, market_raw_lower) under REVIEW/UNMAPPED.
        raw_valid_df: Pre-canonicalization cleaned source rows.
        quarantined_keys: Set of canonical 6-part tuples quarantined in pipeline.
        low_obs_keys: Set of canonical 6-part tuples in series dropped by <20 floor.
        raw_keys: Set of canonical 6-part tuples present in raw dataset.
        known_markets_by_district: Dict of district_lower -> set of market names recognized.
        price_tolerance: Maximum numeric difference for price equivalence (default 1e-4).
        strict_panel_integrity: If True, fails closed on duplicate conflicting panel keys or invalid prices.
    """
    if df_excel.empty:
        empty_df = pd.DataFrame()
        return {
            "total_excel_rows": 0,
            "matched_exact": 0,
            "matched_different": 0,
            "invalid": 0,
            "conflicting": 0,
            "low_obs": 0,
            "absent": 0,
            "spelling_review": 0,
            "other": 0,
            "unmatched_total": 0,
            "categories": {
                "matched_exact": 0,
                "matched_different": 0,
                "invalid": 0,
                "conflicting": 0,
                "low_obs": 0,
                "absent": 0,
                "spelling-review": 0,
                "other": 0,
                # Backwards compatible alias keys
                "quarantined_strategy2": 0,
                "low_obs_dropped": 0,
                "absent_from_raw": 0,
                "spelling_unmapped": 0
            },
            "category_conservation_check": True,
            "classifications_df": empty_df
        }

    # Index panel rows by canonical 6-part natural key
    df_pan = df_panel.copy()
    panel_map: Dict[Tuple, float] = {}

    for idx, r in df_pan.iterrows():
        d = str(r["District"]).strip().lower()
        m = str(r["Market"]).strip().lower()
        c = str(r["Commodity"]).strip().lower()
        v = str(r.get("Variety", "Default")).strip().lower()
        g = str(r.get("Grade", "FAQ")).strip().lower()
        try:
            dt_str = pd.to_datetime(r["Arrival_Date"]).strftime("%Y-%m-%d")
        except Exception:
            dt_str = str(r["Arrival_Date"]).strip()

        k = (d, m, c, v, g, dt_str)

        raw_price = r.get("Modal_Price")
        try:
            p_val = float(raw_price)
        except (ValueError, TypeError):
            if strict_panel_integrity:
                raise ValueError(f"Invalid non-numeric price in panel at row {idx}, key {k}: {raw_price}")
            p_val = -1.0

        if not np.isfinite(p_val) or p_val <= 0:
            if strict_panel_integrity:
                raise ValueError(f"Invalid nonfinite or non-positive price in panel at row {idx}, key {k}: {p_val}")

        if k in panel_map:
            prev_p = panel_map[k]
            if abs(prev_p - p_val) > price_tolerance:
                if strict_panel_integrity:
                    raise ValueError(
                        f"Duplicate conflicting panel key {k} with divergent prices: {prev_p} vs {p_val}"
                    )
        panel_map[k] = p_val

    # Derive raw keys and known markets if raw_valid_df is supplied
    r_keys = set(raw_keys) if raw_keys is not None else set()
    dist_known_markets: Dict[str, Set[str]] = (
        {k: set(v) for k, v in known_markets_by_district.items()}
        if known_markets_by_district is not None else {}
    )

    if raw_valid_df is not None and not raw_valid_df.empty:
        for _, r in raw_valid_df.iterrows():
            d = str(r["District"]).strip().lower()
            m_raw = str(r.get("Market_Raw", r["Market"])).strip().lower()
            dist_known_markets.setdefault(d, set()).add(m_raw)

            # Map market if alias_mapping is active
            if alias_mapping and (d, m_raw) in alias_mapping:
                m_can = alias_mapping[(d, m_raw)].strip().lower()
            else:
                m_can = m_raw
            dist_known_markets[d].add(m_can)

            c = str(r["Commodity"]).strip().lower()
            v = str(r.get("Variety", "Default")).strip().lower()
            g = str(r.get("Grade", "FAQ")).strip().lower()
            try:
                dt_str = pd.to_datetime(r["Arrival_Date"]).strftime("%Y-%m-%d")
            except Exception:
                dt_str = str(r["Arrival_Date"]).strip()

            r_keys.add((d, m_can, c, v, g, dt_str))

    q_keys = quarantined_keys or set()
    lo_keys = low_obs_keys or set()
    rev_markets = review_markets or set()

    df_ex = df_excel.copy()
    classifications: List[str] = []
    modal_diffs: List[Optional[float]] = []
    suggested_norm: List[str] = []

    matched_exact_count = 0
    matched_diff_count = 0
    invalid_count = 0
    conflicting_count = 0
    low_obs_count = 0
    absent_count = 0
    spelling_review_count = 0
    other_count = 0

    for _, r in df_ex.iterrows():
        d_raw = str(r["District"]).strip()
        d_lower = d_raw.lower()

        m_raw = str(r["Market"]).strip()
        m_raw_lower = m_raw.lower()

        # Audit/suggested normalized name only (never used to silently equate identities)
        suggested_norm.append(normalize_market_name(m_raw))

        # Check explicit alias mapping
        if alias_mapping and (d_lower, m_raw_lower) in alias_mapping:
            m_canonical = alias_mapping[(d_lower, m_raw_lower)].strip()
        else:
            m_canonical = m_raw
        m_can_lower = m_canonical.lower()

        c_raw = str(r["Commodity"]).strip()
        c_lower = c_raw.lower()

        v_raw = str(r.get("Variety", "Default")).strip()
        v_lower = v_raw.lower()

        g_raw = str(r.get("Grade", "FAQ")).strip()
        g_lower = g_raw.lower()

        # 1. Date & Price Validity Check
        try:
            arr_dt = pd.to_datetime(r["Arrival_Date"])
            if pd.isna(arr_dt):
                raise ValueError("NaT date")
            dt_str = arr_dt.strftime("%Y-%m-%d")
        except Exception:
            classifications.append("invalid")
            modal_diffs.append(None)
            invalid_count += 1
            continue

        raw_p = r.get("Modal_Price")
        try:
            p_ex = float(raw_p)
            if not np.isfinite(p_ex) or p_ex <= 0:
                raise ValueError("Non-positive or non-finite price")
        except (ValueError, TypeError):
            classifications.append("invalid")
            modal_diffs.append(None)
            invalid_count += 1
            continue

        # 6-part canonical natural key
        k = (d_lower, m_can_lower, c_lower, v_lower, g_lower, dt_str)

        # 2. Check Match Against Panel
        if k in panel_map:
            p_pan = panel_map[k]
            diff = abs(p_ex - p_pan)
            modal_diffs.append(diff)
            if diff <= price_tolerance:
                classifications.append("matched_exact")
                matched_exact_count += 1
            else:
                classifications.append("matched_different")
                matched_diff_count += 1
            continue

        modal_diffs.append(None)

        # 3. Check Quarantined Strategy 2 Conflicts
        if k in q_keys:
            classifications.append("conflicting")
            conflicting_count += 1
            continue

        # 4. Check Low-Observation Floor Dropped Keys
        if k in lo_keys:
            classifications.append("low_obs")
            low_obs_count += 1
            continue

        # 5. Check Review Policy / Spelling Unmapped
        is_review_pair = (d_lower, m_raw_lower) in rev_markets
        known_in_dist = dist_known_markets.get(d_lower, set())
        mkt_unrecognized = bool(
            known_in_dist and
            (m_raw_lower not in known_in_dist) and
            (m_can_lower not in known_in_dist)
        )

        if is_review_pair or mkt_unrecognized:
            classifications.append("spelling-review")
            spelling_review_count += 1
            continue

        # 6. Check Raw Presence vs Absence
        if r_keys:
            if k in r_keys:
                classifications.append("other")
                other_count += 1
            else:
                classifications.append("absent")
                absent_count += 1
        else:
            classifications.append("other")
            other_count += 1

    df_ex["classification"] = classifications
    df_ex["modal_difference"] = modal_diffs
    df_ex["price_tolerance"] = price_tolerance
    df_ex["suggested_normalized_market"] = suggested_norm

    total_excel = len(df_ex)
    unmatched_total = (
        invalid_count + conflicting_count + low_obs_count +
        absent_count + spelling_review_count + other_count
    )

    conservation_ok = (
        matched_exact_count + matched_diff_count + unmatched_total == total_excel
    )
    if not conservation_ok:
        raise ValueError(
            f"Excel reclassification conservation violated: "
            f"matched_exact ({matched_exact_count}) + matched_diff ({matched_diff_count}) + "
            f"unmatched ({unmatched_total}) != total ({total_excel})"
        )

    return {
        "total_excel_rows": total_excel,
        "matched_exact": matched_exact_count,
        "matched_different": matched_diff_count,
        "invalid": invalid_count,
        "conflicting": conflicting_count,
        "low_obs": low_obs_count,
        "absent": absent_count,
        "spelling_review": spelling_review_count,
        "other": other_count,
        "unmatched_total": unmatched_total,
        "categories": {
            "matched_exact": matched_exact_count,
            "matched_different": matched_diff_count,
            "invalid": invalid_count,
            "conflicting": conflicting_count,
            "low_obs": low_obs_count,
            "absent": absent_count,
            "spelling-review": spelling_review_count,
            "other": other_count,
            # Backwards compatible alias keys
            "quarantined_strategy2": conflicting_count,
            "low_obs_dropped": low_obs_count,
            "absent_from_raw": absent_count,
            "spelling_unmapped": spelling_review_count
        },
        "category_conservation_check": conservation_ok,
        "classifications_df": df_ex
    }


def reconstruct_cutoff_fold(
    df_raw: pd.DataFrame,
    alias_df: pd.DataFrame,
    train_end: str,
    test_start: Optional[str] = None,
    test_end: Optional[str] = None,
    evidence_mode: str = "verified",
    min_train_records: int = 60,
    min_coverage: float = 0.30,
    tier_b_min_records: int = 120,
    min_series_records: int = 20
) -> Dict[str, Any]:
    """
    Reconstructs an as-of training slice and test window for a single fold cutoff
    directly from pre-canonicalization raw arrivals.

    Applies:
    1. As-of causal alias mapping (verified, assumed, or retrospective).
    2. Strategy 2 duplicate exclusion / conflict quarantine.
    3. Exact duplicate deduplication.
    4. Series eligibility:
       - Tier A: >= 60 records AND coverage >= 0.30
       - Tier B: >= 120 records AND coverage >= 0.30
    5. Serving recency and target availability in test window.
    """
    df = df_raw.copy()
    train_end_dt = pd.to_datetime(train_end)

    # 1. Build As-Of Alias Mapping
    mapping = build_causal_alias_mapping(alias_df, as_of_date=train_end, evidence_mode=evidence_mode)

    # 2. Slice Training Rows
    df["Arrival_Date_dt"] = pd.to_datetime(df["Arrival_Date"])
    df_train = df[df["Arrival_Date_dt"] <= train_end_dt].copy()

    # 3. Canonicalize Market using As-Of Mapping
    def _get_mkt(r):
        d = str(r["District"]).strip().lower()
        m_raw = str(r.get("Market_Raw", r["Market"])).strip().lower()
        return mapping.get((d, m_raw), r.get("Market_Raw", r["Market"]))

    df_train["Market_Canonical"] = df_train.apply(_get_mkt, axis=1)

    key_cols = ["District", "Market_Canonical", "Commodity", "Variety", "Grade", "Arrival_Date_dt"]
    series_cols = ["District", "Market_Canonical", "Commodity", "Variety", "Grade"]

    # 4. Strategy 2 Ambiguous Conflict Detection
    has_min_max = ("Min_Price" in df_train.columns) and ("Max_Price" in df_train.columns)
    if has_min_max:
        dup_groups = df_train.groupby(key_cols).agg(
            n_rows=("Modal_Price", "count"),
            modal_nunique=("Modal_Price", "nunique"),
            min_nunique=("Min_Price", "nunique"),
            max_nunique=("Max_Price", "nunique")
        )
        ambiguous_keys = set(dup_groups[
            (dup_groups["n_rows"] > 1) &
            ((dup_groups["modal_nunique"] > 1) | (dup_groups["min_nunique"] > 1) | (dup_groups["max_nunique"] > 1))
        ].index)
    else:
        dup_groups = df_train.groupby(key_cols).agg(
            n_rows=("Modal_Price", "count"),
            modal_nunique=("Modal_Price", "nunique")
        )
        ambiguous_keys = set(dup_groups[
            (dup_groups["n_rows"] > 1) & (dup_groups["modal_nunique"] > 1)
        ].index)

    is_ambiguous = df_train.set_index(key_cols).index.isin(ambiguous_keys)
    conflicts_quarantined = int(is_ambiguous.sum())
    df_noconflict = df_train[~is_ambiguous].copy()

    # 5. Exact Duplicate Deduplication
    pre_dedup = len(df_noconflict)
    df_clean = df_noconflict.drop_duplicates(subset=key_cols, keep="first").copy()
    duplicates_deduplicated = pre_dedup - len(df_clean)

    # Sort deterministically
    df_clean.sort_values(
        by=["Arrival_Date_dt", "District", "Market_Canonical", "Commodity", "Variety", "Grade", "Modal_Price"],
        inplace=True
    )
    df_clean.reset_index(drop=True, inplace=True)

    # Deterministic training row hash
    train_hash_input = df_clean[key_cols + ["Modal_Price"]].to_csv(index=False).encode("utf-8")
    train_hash = hashlib.sha256(train_hash_input).hexdigest()

    # 6. Evaluate Train Eligibility per Series
    df_clean["series_tuple"] = list(zip(
        df_clean["District"].astype(str).str.strip(),
        df_clean["Market_Canonical"].astype(str).str.strip(),
        df_clean["Commodity"].astype(str).str.strip(),
        df_clean["Variety"].astype(str).str.strip(),
        df_clean["Grade"].astype(str).str.strip()
    ))

    tier_a_series: Set[Tuple] = set()
    tier_b_series: Set[Tuple] = set()
    series_obs_counts: Dict[Tuple, int] = {}

    for s_tuple, s_group in df_clean.groupby("series_tuple"):
        s_dts = s_group["Arrival_Date_dt"].values
        # Use pure baselines helper
        is_a, is_b = evaluate_series_train_eligibility(
            dates_dt=s_dts,
            train_end_dt=train_end_dt,
            min_obs=min_train_records,
            min_cov=min_coverage,
            tier_b_min_obs=tier_b_min_records
        )
        if is_a:
            tier_a_series.add(s_tuple)
        if is_b:
            tier_b_series.add(s_tuple)
        series_obs_counts[s_tuple] = len(s_group)

    tier_a_hash = hashlib.sha256(str(sorted(list(tier_a_series))).encode("utf-8")).hexdigest()

    # Mathematical subset check: check against full panel floor (min_series_records)
    # Series with N_train >= 60 must have N_full >= 60 >= 20 holding identity fixed.
    df_full = df.copy()
    df_full["Market_Canonical"] = df_full.apply(_get_mkt, axis=1)
    df_full_noconflict = df_full[~df_full.set_index(key_cols).index.isin(ambiguous_keys)].copy()
    df_full_dedup = df_full_noconflict.drop_duplicates(subset=key_cols, keep="first").copy()
    df_full_dedup["series_tuple"] = list(zip(
        df_full_dedup["District"].astype(str).str.strip(),
        df_full_dedup["Market_Canonical"].astype(str).str.strip(),
        df_full_dedup["Commodity"].astype(str).str.strip(),
        df_full_dedup["Variety"].astype(str).str.strip(),
        df_full_dedup["Grade"].astype(str).str.strip()
    ))
    full_counts = df_full_dedup.groupby("series_tuple").size()

    subset_violations = []
    for s_tuple in tier_a_series:
        n_fl = full_counts.get(s_tuple, 0)
        if n_fl < min_series_records:
            subset_violations.append((s_tuple, series_obs_counts.get(s_tuple, 0), n_fl))

    # 7. Serving Eligibility & Target Availability in Test Window
    test_eval = {
        "test_window_available": False,
        "n_origins_total": 0,
        "n_origins_serving_eligible": 0,
        "n_origins_target_available": 0,
        "by_crop": {}
    }

    if test_start is not None and test_end is not None:
        test_start_dt = pd.to_datetime(test_start)
        test_end_dt = pd.to_datetime(test_end)

        df_test = df[(df["Arrival_Date_dt"] >= test_start_dt) & (df["Arrival_Date_dt"] <= test_end_dt)].copy()
        df_test["Market_Canonical"] = df_test.apply(_get_mkt, axis=1)

        # Remove ambiguous quotes and duplicates within test slice
        is_test_ambig = df_test.set_index(key_cols).index.isin(ambiguous_keys)
        df_test_clean = df_test[~is_test_ambig].drop_duplicates(subset=key_cols, keep="first").copy()
        df_test_clean["series_tuple"] = list(zip(
            df_test_clean["District"].astype(str).str.strip(),
            df_test_clean["Market_Canonical"].astype(str).str.strip(),
            df_test_clean["Commodity"].astype(str).str.strip(),
            df_test_clean["Variety"].astype(str).str.strip(),
            df_test_clean["Grade"].astype(str).str.strip()
        ))

        # Combined history for serving recency and forward target lookup
        df_combined = pd.concat([df_clean, df_test_clean], ignore_index=True)
        df_combined.sort_values(by=["series_tuple", "Arrival_Date_dt"], inplace=True)
        df_combined.reset_index(drop=True, inplace=True)

        n_origins_total = 0
        n_origins_serving = 0
        n_origins_target = 0
        crop_stats: Dict[str, Dict[str, int]] = {}

        for crop in FOCUS_CROPS:
            crop_stats[crop] = {"tier_a_series": 0, "origins": 0, "serving_eligible": 0, "target_available": 0}

        for s_tuple in tier_a_series:
            crop_name = s_tuple[2]
            if crop_name in crop_stats:
                crop_stats[crop_name]["tier_a_series"] += 1

            sub_series = df_combined[df_combined["series_tuple"] == s_tuple]
            s_dts = sub_series["Arrival_Date_dt"].values
            s_prices = sub_series["Modal_Price"].values

            # Origins are observed dates in [test_start, test_end]
            test_obs_dts = sub_series[
                (sub_series["Arrival_Date_dt"] >= test_start_dt) &
                (sub_series["Arrival_Date_dt"] <= test_end_dt)
            ]["Arrival_Date_dt"].values

            for t_val in test_obs_dts:
                n_origins_total += 1
                if crop_name in crop_stats:
                    crop_stats[crop_name]["origins"] += 1

                # Serving recency check
                is_serving = check_serving_recency(s_dts, t_val, window_days=30, min_obs=3)
                if is_serving:
                    n_origins_serving += 1
                    if crop_name in crop_stats:
                        crop_stats[crop_name]["serving_eligible"] += 1

                    # Target extraction
                    tgt_res = extract_target_vectorized(
                        dates_dt=s_dts,
                        prices=s_prices,
                        origin_dt=t_val,
                        test_end_dt=test_end_dt,
                        horizon_days=7,
                        window_min=6,
                        window_max=8
                    )
                    if tgt_res["has_target"] and not tgt_res.get("is_after_fold_end", False):
                        n_origins_target += 1
                        if crop_name in crop_stats:
                            crop_stats[crop_name]["target_available"] += 1

        test_eval = {
            "test_window_available": True,
            "test_start": test_start,
            "test_end": test_end,
            "n_origins_total": n_origins_total,
            "n_origins_serving_eligible": n_origins_serving,
            "n_origins_target_available": n_origins_target,
            "by_crop": crop_stats
        }

    return {
        "train_end": train_end,
        "evidence_mode": evidence_mode,
        "active_aliases_count": len(mapping),
        "total_training_observations": int(len(df_clean)),
        "conflicts_quarantined": conflicts_quarantined,
        "ambiguous_keys_count": len(ambiguous_keys),
        "ambiguous_keys": ambiguous_keys,
        "duplicates_deduplicated": duplicates_deduplicated,
        "train_hash": train_hash,
        "tier_a_series_count": len(tier_a_series),
        "tier_a_series_set": tier_a_series,
        "tier_a_hash": tier_a_hash,
        "tier_b_series_count": len(tier_b_series),
        "tier_b_series_set": tier_b_series,
        "subset_violations_count": len(subset_violations),
        "subset_invariant_holds": len(subset_violations) == 0,
        "test_eval": test_eval
    }


def evaluate_causal_train_eligibility_sensitivity(
    df_raw: pd.DataFrame,
    alias_df: pd.DataFrame,
    cutoffs: Dict[str, Union[str, Dict[str, str]]],
    evidence_mode: str = "verified",
    min_train_records: int = 60,
    min_coverage: float = 0.30,
    tier_b_min_records: int = 120,
    min_series_records: int = 20
) -> Dict[str, Any]:
    """
    Evaluates causal train-only series eligibility and forward target availability
    reconstructed BEFORE the full-history floor across declared cutoffs.
    """
    results_by_cutoff: Dict[str, Any] = {}

    for fold_name, cutoff_val in cutoffs.items():
        if isinstance(cutoff_val, dict):
            t_end = cutoff_val["train_end"]
            t_start = cutoff_val.get("test_start")
            t_end_test = cutoff_val.get("test_end")
        else:
            t_end = str(cutoff_val)
            # Check default fold bounds
            if fold_name in DEFAULT_FOLD_BOUNDS:
                t_start = DEFAULT_FOLD_BOUNDS[fold_name]["test_start"]
                t_end_test = DEFAULT_FOLD_BOUNDS[fold_name]["test_end"]
            else:
                t_start = None
                t_end_test = None

        fold_res = reconstruct_cutoff_fold(
            df_raw=df_raw,
            alias_df=alias_df,
            train_end=t_end,
            test_start=t_start,
            test_end=t_end_test,
            evidence_mode=evidence_mode,
            min_train_records=min_train_records,
            min_coverage=min_coverage,
            tier_b_min_records=tier_b_min_records,
            min_series_records=min_series_records
        )

        # Structure for backwards compatibility with earlier summary consumers
        results_by_cutoff[fold_name] = {
            "cutoff_date": t_end,
            "evidence_mode": evidence_mode,
            "active_aliases_count": fold_res["active_aliases_count"],
            "total_training_observations": fold_res["total_training_observations"],
            "conflicts_quarantined": fold_res["conflicts_quarantined"],
            "duplicates_deduplicated": fold_res["duplicates_deduplicated"],
            "train_hash": fold_res["train_hash"],
            "tier_a_series_count": fold_res["tier_a_series_count"],
            "tier_a_series_set": fold_res["tier_a_series_set"],
            "tier_a_hash": fold_res["tier_a_hash"],
            "tier_b_series_count": fold_res["tier_b_series_count"],
            "tier_b_series_set": fold_res["tier_b_series_set"],
            "mathematical_subset_violations": fold_res["subset_violations_count"],
            "subset_invariant_holds": fold_res["subset_invariant_holds"],
            "test_eval": fold_res["test_eval"]
        }

    return {
        "evidence_mode": evidence_mode,
        "cutoffs": results_by_cutoff
    }


def verify_future_mutation_invariance(
    df_raw: pd.DataFrame,
    alias_df: pd.DataFrame,
    cutoff_date: str,
    evidence_mode: str = "verified"
) -> bool:
    """
    Verifies that future rows and value mutations dated strictly after cutoff_date
    do NOT alter training series identities, observation counts, prices, conflict
    dispositions, eligible-series sets, or training hashes.

    Returns:
        True if bit-level invariant holds under mutation.
    """
    # 1. Baseline training reconstruction
    base_res = reconstruct_cutoff_fold(
        df_raw=df_raw,
        alias_df=alias_df,
        train_end=cutoff_date,
        evidence_mode=evidence_mode
    )

    # 2. Mutate future data strictly after cutoff_date
    df_mut = df_raw.copy()
    cutoff_dt = pd.to_datetime(cutoff_date)
    future_mask = pd.to_datetime(df_mut["Arrival_Date"]) > cutoff_dt

    if future_mask.any():
        # Mutate prices, market names, and add duplicate rows in the future
        df_mut.loc[future_mask, "Modal_Price"] = 99999.0
        if "Market" in df_mut.columns:
            df_mut.loc[future_mask, "Market"] = df_mut.loc[future_mask, "Market"] + "_MUTATED"
    else:
        # If no future rows exist, inject synthetic future rows
        sample_row = df_raw.iloc[0].copy()
        sample_row["Arrival_Date"] = (cutoff_dt + pd.Timedelta(days=10)).strftime("%Y-%m-%d")
        sample_row["Modal_Price"] = 99999.0
        df_mut = pd.concat([df_mut, pd.DataFrame([sample_row])], ignore_index=True)

    # Inject an adversarial future conflicting quote: two rows with same natural key on future date
    future_dt_str = (cutoff_dt + pd.Timedelta(days=15)).strftime("%Y-%m-%d")
    adversarial_row1 = df_raw.iloc[0].copy()
    adversarial_row1["Arrival_Date"] = future_dt_str
    adversarial_row1["Modal_Price"] = 1111.0
    adversarial_row2 = df_raw.iloc[0].copy()
    adversarial_row2["Arrival_Date"] = future_dt_str
    adversarial_row2["Modal_Price"] = 8888.0

    df_mut = pd.concat([df_mut, pd.DataFrame([adversarial_row1, adversarial_row2])], ignore_index=True)

    # 3. Reconstruct mutated dataset at same cutoff
    mut_res = reconstruct_cutoff_fold(
        df_raw=df_mut,
        alias_df=alias_df,
        train_end=cutoff_date,
        evidence_mode=evidence_mode
    )

    # Strict multi-attribute bit-level assertions
    is_identical = (
        base_res["train_hash"] == mut_res["train_hash"] and
        base_res["tier_a_hash"] == mut_res["tier_a_hash"] and
        base_res["tier_a_series_set"] == mut_res["tier_a_series_set"] and
        base_res["tier_b_series_set"] == mut_res["tier_b_series_set"] and
        base_res["conflicts_quarantined"] == mut_res["conflicts_quarantined"] and
        base_res["duplicates_deduplicated"] == mut_res["duplicates_deduplicated"] and
        base_res["total_training_observations"] == mut_res["total_training_observations"] and
        base_res["active_aliases_count"] == mut_res["active_aliases_count"]
    )

    return is_identical

