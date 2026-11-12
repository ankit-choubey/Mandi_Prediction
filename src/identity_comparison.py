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
import numpy as np
import pandas as pd

from src.market_identity import (
    build_causal_alias_mapping,
    apply_market_canonicalization_v21,
    validate_alias_table,
    normalize_market_name
)


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
    df_raw: Optional[pd.DataFrame] = None,
    quarantined_keys: Optional[Set[Tuple]] = None,
    low_obs_keys: Optional[Set[Tuple]] = None
) -> Dict[str, Any]:
    """
    Reclassifies in-window Excel rows against clean panel data and raw source data
    using a strict, mutually exclusive precedence order:

      1. matched_exact: Natural key matches panel row and modal price matches exactly.
      2. matched_different: Natural key matches panel row, but modal price differs.
      3. quarantined_strategy2: Not in panel; dropped due to Strategy 2 conflict.
      4. low_obs_dropped: Not in panel; dropped due to < 20 observations floor.
      5. absent_from_raw: Natural key not present in raw source dataset.
      6. spelling_unmapped: Market name does not normalize to any known district market.
      7. other: Remaining unmatched rows.

    Returns:
        Dict containing category counts, conservation assertion, and per-row classification DataFrame.
    """
    if df_excel.empty:
        return {
            "total_excel_rows": 0,
            "matched_exact": 0,
            "matched_different": 0,
            "unmatched_total": 0,
            "categories": {
                "low_obs_dropped": 0,
                "other": 0,
                "quarantined_strategy2": 0,
                "absent_from_raw": 0,
                "spelling_unmapped": 0
            },
            "category_conservation_check": True,
            "classifications_df": pd.DataFrame()
        }

    # Normalize Excel key columns
    df_ex = df_excel.copy()
    df_ex["Arrival_Date_str"] = pd.to_datetime(df_ex["Arrival_Date"]).dt.strftime("%Y-%m-%d")
    df_ex["District_norm"] = df_ex["District"].astype(str).str.strip().str.lower()
    df_ex["Market_norm"] = df_ex["Market"].apply(normalize_market_name)
    df_ex["Commodity_norm"] = df_ex["Commodity"].astype(str).str.strip().str.lower()
    df_ex["Variety_norm"] = df_ex["Variety"].astype(str).str.strip().str.lower() if "Variety" in df_ex.columns else "default"
    df_ex["Grade_norm"] = df_ex["Grade"].astype(str).str.strip().str.lower() if "Grade" in df_ex.columns else "faq"

    # Index panel rows by canonical natural key
    df_pan = df_panel.copy()
    df_pan["Arrival_Date_str"] = pd.to_datetime(df_pan["Arrival_Date"]).dt.strftime("%Y-%m-%d")
    df_pan["District_norm"] = df_pan["District"].astype(str).str.strip().str.lower()
    df_pan["Market_norm"] = df_pan["Market"].apply(normalize_market_name)
    df_pan["Commodity_norm"] = df_pan["Commodity"].astype(str).str.strip().str.lower()
    df_pan["Variety_norm"] = df_pan["Variety"].astype(str).str.strip().str.lower() if "Variety" in df_pan.columns else "default"
    df_pan["Grade_norm"] = df_pan["Grade"].astype(str).str.strip().str.lower() if "Grade" in df_pan.columns else "faq"

    # Map natural key -> modal price in panel
    panel_map: Dict[Tuple, float] = {}
    for _, r in df_pan.iterrows():
        k = (r["District_norm"], r["Market_norm"], r["Commodity_norm"], r["Variety_norm"], r["Grade_norm"], r["Arrival_Date_str"])
        try:
            panel_map[k] = float(r["Modal_Price"])
        except Exception:
            panel_map[k] = 0.0

    # Index raw dataset if provided
    raw_keys: Set[Tuple] = set()
    raw_markets_by_district: Dict[str, Set[str]] = {}
    if df_raw is not None and not df_raw.empty:
        df_r = df_raw.copy()
        df_r["Arrival_Date_str"] = pd.to_datetime(df_r["Arrival_Date"]).dt.strftime("%Y-%m-%d")
        df_r["District_norm"] = df_r["District"].astype(str).str.strip().str.lower()
        df_r["Market_norm"] = df_r["Market"].apply(normalize_market_name)
        df_r["Commodity_norm"] = df_r["Commodity"].astype(str).str.strip().str.lower()
        df_r["Variety_norm"] = df_r["Variety"].astype(str).str.strip().str.lower() if "Variety" in df_r.columns else "default"
        df_r["Grade_norm"] = df_r["Grade"].astype(str).str.strip().str.lower() if "Grade" in df_r.columns else "faq"

        for _, r in df_r.iterrows():
            k = (r["District_norm"], r["Market_norm"], r["Commodity_norm"], r["Variety_norm"], r["Grade_norm"], r["Arrival_Date_str"])
            raw_keys.add(k)
            d = r["District_norm"]
            if d not in raw_markets_by_district:
                raw_markets_by_district[d] = set()
            raw_markets_by_district[d].add(r["Market_norm"])

    q_keys = quarantined_keys or set()
    lo_keys = low_obs_keys or set()

    classifications: List[str] = []
    matched_exact_count = 0
    matched_different_count = 0

    categories = {
        "low_obs_dropped": 0,
        "other": 0,
        "quarantined_strategy2": 0,
        "absent_from_raw": 0,
        "spelling_unmapped": 0
    }

    for _, r in df_ex.iterrows():
        k = (r["District_norm"], r["Market_norm"], r["Commodity_norm"], r["Variety_norm"], r["Grade_norm"], r["Arrival_Date_str"])
        ex_modal = float(r["Modal_Price"]) if pd.notna(r.get("Modal_Price")) else None

        # 1. Match against panel
        if k in panel_map:
            pan_modal = panel_map[k]
            if ex_modal is not None and abs(ex_modal - pan_modal) < 1e-4:
                classifications.append("matched_exact")
                matched_exact_count += 1
            else:
                classifications.append("matched_different")
                matched_different_count += 1
            continue

        # 2. Check quarantined Strategy 2 conflicts
        if k in q_keys:
            classifications.append("quarantined_strategy2")
            categories["quarantined_strategy2"] += 1
            continue

        # 3. Check low-observation dropped series
        if k in lo_keys:
            classifications.append("low_obs_dropped")
            categories["low_obs_dropped"] += 1
            continue

        # 4. Check raw presence / spelling unmapped / absent from raw
        if df_raw is not None:
            dist_known_markets = raw_markets_by_district.get(r["District_norm"], set())
            if r["Market_norm"] not in dist_known_markets:
                classifications.append("spelling_unmapped")
                categories["spelling_unmapped"] += 1
            elif k not in raw_keys:
                classifications.append("absent_from_raw")
                categories["absent_from_raw"] += 1
            else:
                classifications.append("other")
                categories["other"] += 1
        else:
            classifications.append("other")
            categories["other"] += 1

    df_ex["classification"] = classifications
    total_excel = len(df_ex)
    unmatched_total = sum(categories.values())

    conservation_ok = (
        matched_exact_count + matched_different_count + unmatched_total == total_excel
    )

    return {
        "total_excel_rows": total_excel,
        "matched_exact": matched_exact_count,
        "matched_different": matched_different_count,
        "unmatched_total": unmatched_total,
        "categories": categories,
        "category_conservation_check": conservation_ok,
        "classifications_df": df_ex
    }


def evaluate_causal_train_eligibility_sensitivity(
    df_raw: pd.DataFrame,
    alias_df: pd.DataFrame,
    cutoffs: Dict[str, str],
    evidence_mode: str = "verified",
    min_train_records: int = 60,
    min_series_records: int = 20
) -> Dict[str, Any]:
    """
    Evaluates causal train-only series eligibility (Tier A: N_train >= 60)
    reconstructed BEFORE the full-history (<20) floor across declared cutoffs.

    Parameters:
        df_raw: Raw Agmarknet arrivals dataset before series filtering.
        alias_df: Market alias table (legacy or candidate).
        cutoffs: Dict of {fold_name: cutoff_date_str}.
        evidence_mode: 'verified', 'assumed', or 'retrospective'.
        min_train_records: Minimum training observations for Tier A (default 60).
        min_series_records: Low-observation floor applied to full panel (default 20).

    Returns:
        Structured dictionary with Tier A series counts, total training observations,
        and mathematical subset assertions across all cutoffs.
    """
    df = df_raw.copy()
    df["Arrival_Date_dt"] = pd.to_datetime(df["Arrival_Date"])

    results_by_cutoff: Dict[str, Any] = {}

    for fold_name, cutoff_str in cutoffs.items():
        cutoff_dt = pd.to_datetime(cutoff_str)

        # 1. As-of alias mapping at cutoff
        mapping = build_causal_alias_mapping(alias_df, as_of_date=cutoff_str, evidence_mode=evidence_mode)

        # 2. Canonicalize Market using as-of mapping
        def _get_mkt(r):
            d = str(r["District"]).strip().lower()
            m = str(r.get("Market_Raw", r["Market"])).strip().lower()
            return mapping.get((d, m), r.get("Market_Raw", r["Market"]))

        df_cutoff = df.copy()
        df_cutoff["Market_Canonical"] = df_cutoff.apply(_get_mkt, axis=1)

        # Build series ID before filtering
        grade_val = df_cutoff["Grade"].astype(str).str.strip().str.lower() if "Grade" in df_cutoff.columns else "faq"
        df_cutoff["series_id"] = (
            df_cutoff["District"].astype(str).str.strip().str.lower() + "_" +
            df_cutoff["Market_Canonical"].astype(str).str.strip().str.lower() + "_" +
            df_cutoff["Commodity"].astype(str).str.strip().str.lower() + "_" +
            df_cutoff["Variety"].astype(str).str.strip().str.lower() + "_" +
            grade_val
        )

        # 3. Deduplicate exact duplicates within training slice
        df_train = df_cutoff[df_cutoff["Arrival_Date_dt"] <= cutoff_dt].copy()
        dedup_subset = ["Arrival_Date_dt", "District", "Market_Canonical", "Commodity", "Variety"]
        if "Grade" in df_train.columns:
            dedup_subset.append("Grade")
        df_train_dedup = df_train.drop_duplicates(subset=dedup_subset).copy()

        # 4. Count training observations per series
        train_counts = df_train_dedup.groupby("series_id").size()

        # 5. Full history counts holding this identity fixed
        df_full_dedup = df_cutoff.drop_duplicates(subset=dedup_subset).copy()
        full_counts = df_full_dedup.groupby("series_id").size()

        tier_a_series = train_counts[train_counts >= min_train_records]
        n_tier_a_series = len(tier_a_series)
        n_tier_a_obs = int(tier_a_series.sum())

        # Mathematical subset check: Holding identity fixed, N_full >= N_train
        # Therefore, any series with N_train >= 60 MUST have N_full >= 60 >= 20.
        violation_series = []
        for s_id, n_tr in tier_a_series.items():
            n_fl = full_counts.get(s_id, 0)
            if n_fl < min_series_records:
                violation_series.append((s_id, n_tr, n_fl))

        # Test forward target availability in test window (e.g. within 180 days after cutoff)
        df_test = df_cutoff[(df_cutoff["Arrival_Date_dt"] > cutoff_dt) &
                            (df_cutoff["Arrival_Date_dt"] <= cutoff_dt + pd.Timedelta(days=180))]
        test_series_set = set(df_test["series_id"].unique())
        tier_a_with_forward_data = len(set(tier_a_series.index).intersection(test_series_set))

        results_by_cutoff[fold_name] = {
            "cutoff_date": cutoff_str,
            "evidence_mode": evidence_mode,
            "active_aliases_count": len(mapping),
            "total_training_observations": int(len(df_train_dedup)),
            "tier_a_series_count": n_tier_a_series,
            "tier_a_observations": n_tier_a_obs,
            "tier_a_with_forward_data": tier_a_with_forward_data,
            "mathematical_subset_violations": len(violation_series),
            "subset_invariant_holds": len(violation_series) == 0
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
    do NOT alter training series identities, observation counts, or Tier A eligibility.

    Returns:
        True if bit-level invariant holds under mutation.
    """
    # 1. Baseline training view
    base_res = evaluate_causal_train_eligibility_sensitivity(
        df_raw=df_raw,
        alias_df=alias_df,
        cutoffs={"fold": cutoff_date},
        evidence_mode=evidence_mode
    )

    # 2. Mutate future data strictly after cutoff
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

    mut_res = evaluate_causal_train_eligibility_sensitivity(
        df_raw=df_mut,
        alias_df=alias_df,
        cutoffs={"fold": cutoff_date},
        evidence_mode=evidence_mode
    )

    # Compare baseline vs mutated
    b_fold = base_res["cutoffs"]["fold"]
    m_fold = mut_res["cutoffs"]["fold"]

    is_identical = (
        b_fold["active_aliases_count"] == m_fold["active_aliases_count"] and
        b_fold["total_training_observations"] == m_fold["total_training_observations"] and
        b_fold["tier_a_series_count"] == m_fold["tier_a_series_count"] and
        b_fold["tier_a_observations"] == m_fold["tier_a_observations"]
    )

    return is_identical
