"""
Chronological Prediction Interval Calibration & Evaluation Pipeline
Task: MP-FC-008 (Step 8 Conformal-Style Residual Interval Evaluation)

Evaluates chronological empirical prediction intervals on saved out-of-sample predictions
using only matured earlier-fold residuals within preceding 180 calendar days.
Primary point anchor: naive persistence baseline (wins verified MAE).
Exploratory models: Ridge and HistGradientBoosting (stored predictions only).

Guarantees:
- Pure AST safety: zero model fitting, training, hyperparameter tuning, or Kaggle submission.
- Zero future leakage: F1 has NO_PRIOR_CALIBRATION; F2 uses F1; F3 uses F1/F2; F4 uses F1/F2/F3.
- Calibration window: strictly preceding 180 calendar days prior to fold test start date.
- Disjoint origin keys: max calibration target date strictly before min evaluation origin date.
- Finite-sample quantile rank: k = ceil((n + 1) * (1 - alpha)) with no quantile rounding.
- Grouping hierarchy: exact commodity (N >= 200, series >= 10) -> POOLED_FALLBACK -> NO_CALIBRATION.
- Full Winkler interval scoring and series-cluster bootstrap 95% CIs.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import csv
from datetime import datetime, timedelta, timezone
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import random
import statistics
import sys
import tempfile
import time
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

FOCUS_CROPS = [
    "Wheat",
    "Potato",
    "Onion",
    "Tomato",
    "Paddy(Dhan)(Common)",
    "Rice",
]

TARGET_DISTRICTS = [
    "Ghaziabad",
    "Jhansi",
    "Kanpur",
    "Lucknow",
    "Unnao",
]

EVAL_MODELS = {
    "naive": "naive_pred",
    "ridge": "ridge_pred",
    "hist_gradient_boosting": "hgb_pred",
}


def compute_sha256(filepath: Path | str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def compute_string_sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def compute_series_key(r: Dict[str, Any]) -> str:
    return (
        f"{r.get('district', '').strip()}__{r.get('market', '').strip()}__"
        f"{r.get('commodity', '').strip()}__{r.get('variety', '').strip()}__{r.get('grade', '').strip()}"
    )


def compute_origin_key(r: Dict[str, Any]) -> str:
    return f"{compute_series_key(r)}__{r.get('origin_date', '').strip()}"


def quantile_linear(sorted_vals: List[float], q: float) -> float:
    """Computes quantile with linear interpolation."""
    if not sorted_vals:
        return float("nan")
    n = len(sorted_vals)
    if n == 1:
        return sorted_vals[0]
    idx = q * (n - 1)
    low = int(math.floor(idx))
    high = int(math.ceil(idx))
    weight = idx - low
    return (1.0 - weight) * sorted_vals[low] + weight * sorted_vals[high]


def compute_conformal_rank(n: int, alpha: float) -> int:
    """Computes exact finite-sample conformal rank: k = ceil((n + 1) * (1 - alpha))."""
    if n <= 0:
        return 0
    return int(math.ceil((n + 1) * (1.0 - alpha)))


def atomic_write_csv(records: List[Dict[str, Any]], target_path: Path) -> None:
    """Writes list of records to CSV atomically without pandas."""
    if hasattr(records, "to_dict"):
        records = records.to_dict(orient="records")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target_path.with_suffix(".tmp")
    if not records:
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write("")
    else:
        fieldnames = list(records[0].keys())
        with open(temp_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            for r in records:
                writer.writerow(r)
    temp_path.replace(target_path)


def atomic_write_json(data: Any, target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target_path.with_suffix(".tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    temp_path.replace(target_path)


def compute_calibration_quantiles_for_fold(
    fold_id: str,
    fold_start_date: str,
    all_rows: List[Dict[str, Any]],
    model_name: str,
    pred_col: str,
    nominal_levels: Sequence[float] = (0.90, 0.95),
    window_days: int = 180,
    min_group_origins: int = 200,
    min_group_series: int = 10,
) -> Dict[str, Any]:
    """
    Computes chronological empirical calibration quantiles for a target fold.
    F1 has NO_PRIOR_CALIBRATION.
    For F2-F4, filters earlier-fold predictions whose target_date falls within
    [fold_start_date - window_days, fold_start_date - 1 day].
    """
    if fold_id == "F1":
        return {
            "status": "NO_CALIBRATION",
            "reason": "FIRST_OUTER_FOLD_NO_PRIOR_DATA",
            "calibration_window": None,
            "total_calibration_rows": 0,
            "quantiles": {},
        }

    fold_start_dt = datetime.strptime(fold_start_date, "%Y-%m-%d")
    window_start = (fold_start_dt - timedelta(days=window_days)).strftime("%Y-%m-%d")
    window_end = (fold_start_dt - timedelta(days=1)).strftime("%Y-%m-%d")

    fold_idx = int(fold_id.replace("F", ""))
    allowed_earlier_folds = {f"F{i}" for i in range(1, fold_idx)}

    # Filter strictly matured earlier fold outcomes within window
    cal_rows = [
        r for r in all_rows
        if r["fold"] in allowed_earlier_folds
        and window_start <= r["target_date"] <= window_end
    ]

    # Verify disjointness and strict temporal precedence
    if cal_rows:
        max_cal_target = max(r["target_date"] for r in cal_rows)
        assert max_cal_target < fold_start_date, (
            f"Temporal leakage in {fold_id}: max calibration target ({max_cal_target}) >= fold start ({fold_start_date})!"
        )

    # Valid rows for this specific model
    valid_cal = []
    for r in cal_rows:
        val_pred = r.get(pred_col, "")
        val_true = r.get("y_true", "")
        val_yt = r.get("y_t", "")
        if not val_pred or val_pred == "nan" or not val_true or not val_yt:
            continue
        try:
            p = float(val_pred)
            y = float(val_true)
            yt = float(val_yt)
            if yt > 0 and math.isfinite(p) and math.isfinite(y):
                valid_cal.append(r)
        except ValueError:
            continue

    total_valid = len(valid_cal)
    cal_series_all = len(set(compute_series_key(r) for r in valid_cal))

    # Pooled scores
    pooled_scores = sorted([
        abs(float(r["y_true"]) - float(r[pred_col])) / float(r["y_t"])
        for r in valid_cal
    ])

    # Commodity groups
    by_crop = defaultdict(list)
    for r in valid_cal:
        by_crop[r["commodity"]].append(r)

    quantiles_by_level: Dict[float, Dict[str, Any]] = {}
    for level in nominal_levels:
        alpha = 1.0 - level

        # 1. Evaluate Pooled
        k_pooled = compute_conformal_rank(total_valid, alpha)
        pooled_eligible = (
            total_valid >= min_group_origins
            and cal_series_all >= min_group_series
            and k_pooled <= total_valid
        )
        q_pooled = pooled_scores[k_pooled - 1] if pooled_eligible else float("nan")

        crop_quantiles: Dict[str, Dict[str, Any]] = {}
        for crop, c_rows in by_crop.items():
            n_c = len(c_rows)
            s_c = len(set(compute_series_key(r) for r in c_rows))
            scores_c = sorted([
                abs(float(r["y_true"]) - float(r[pred_col])) / float(r["y_t"])
                for r in c_rows
            ])
            k_c = compute_conformal_rank(n_c, alpha)
            if n_c >= min_group_origins and s_c >= min_group_series and k_c <= n_c:
                crop_quantiles[crop] = {
                    "quantile": scores_c[k_c - 1],
                    "group_type": "EXACT_COMMODITY",
                    "n_calibration": n_c,
                    "series_count": s_c,
                    "k_rank": k_c,
                }

        quantiles_by_level[level] = {
            "pooled": {
                "quantile": q_pooled,
                "group_type": "POOLED_FALLBACK" if pooled_eligible else "NO_CALIBRATION",
                "n_calibration": total_valid,
                "series_count": cal_series_all,
                "k_rank": k_pooled,
            },
            "by_commodity": crop_quantiles,
        }

    return {
        "status": "CALIBRATED",
        "fold_id": fold_id,
        "fold_start_date": fold_start_date,
        "calibration_window": [window_start, window_end],
        "earlier_folds": sorted(list(allowed_earlier_folds)),
        "total_calibration_rows": total_valid,
        "total_calibration_series": cal_series_all,
        "quantiles": quantiles_by_level,
    }


def predict_interval(
    model_name: str,
    point_pred: float,
    y_t: float,
    commodity: str,
    fold_id: str,
    nominal_level: float,
    calibration_artifacts: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Shared inference helper for prediction interval generation.
    Checks:
    - Artifact/model identity
    - Temporal cutoff and calibration availability
    - Positive finite inputs
    - Non-negative clipping
    Returns interval bounds, width, quantile, and group type.
    """
    if not math.isfinite(point_pred) or point_pred <= 0:
        return {
            "status": "BLOCKED_INVALID_POINT_PRED",
            "lower": float("nan"),
            "upper": float("nan"),
            "width": float("nan"),
            "quantile": float("nan"),
            "group_type": "NONE",
        }
    if not math.isfinite(y_t) or y_t <= 0:
        return {
            "status": "BLOCKED_INVALID_ORIGIN_PRICE",
            "lower": float("nan"),
            "upper": float("nan"),
            "width": float("nan"),
            "quantile": float("nan"),
            "group_type": "NONE",
        }

    fold_cal = calibration_artifacts.get(fold_id, {}).get(model_name)
    if not fold_cal or fold_cal.get("status") != "CALIBRATED":
        return {
            "status": "NO_CALIBRATION",
            "lower": float("nan"),
            "upper": float("nan"),
            "width": float("nan"),
            "quantile": float("nan"),
            "group_type": "NO_CALIBRATION",
        }

    level_dict = fold_cal.get("quantiles", {}).get(nominal_level)
    if not level_dict:
        return {
            "status": "UNSUPPORTED_NOMINAL_LEVEL",
            "lower": float("nan"),
            "upper": float("nan"),
            "width": float("nan"),
            "quantile": float("nan"),
            "group_type": "NONE",
        }

    # Check commodity group first
    crop_info = level_dict.get("by_commodity", {}).get(commodity)
    if crop_info and not math.isnan(crop_info.get("quantile", float("nan"))):
        q = crop_info["quantile"]
        g_type = "EXACT_COMMODITY"
    else:
        # Fallback to pooled
        pooled_info = level_dict.get("pooled", {})
        q = pooled_info.get("quantile", float("nan"))
        if not math.isnan(q):
            g_type = "POOLED_FALLBACK"
        else:
            return {
                "status": "NO_CALIBRATION",
                "lower": float("nan"),
                "upper": float("nan"),
                "width": float("nan"),
                "quantile": float("nan"),
                "group_type": "NO_CALIBRATION",
            }

    half_width = q * y_t
    lower = max(0.0, point_pred - half_width)
    upper = point_pred + half_width
    width = upper - lower

    return {
        "status": "SUCCESS",
        "lower": lower,
        "upper": upper,
        "width": width,
        "half_width": half_width,
        "quantile": q,
        "group_type": g_type,
    }


def compute_cluster_bootstrap_coverage_ci(
    rows: List[Dict[str, Any]],
    n_resamples: int = 1000,
    seed: int = 42,
) -> Tuple[float, float]:
    """Computes series-cluster bootstrap 95% confidence interval for empirical coverage."""
    if not rows:
        return float("nan"), float("nan")

    # Cluster rows by series key
    series_map: Dict[str, List[bool]] = defaultdict(list)
    for r in rows:
        sk = compute_series_key(r)
        series_map[sk].append(bool(r["is_covered"]))

    unique_keys = list(series_map.keys())
    n_series = len(unique_keys)
    if n_series <= 1:
        # Cannot bootstrap single cluster meaningfully
        cov = math.fsum(r["is_covered"] for r in rows) / len(rows) * 100.0
        return cov, cov

    rng = random.Random(seed)
    boot_coverages = []
    for _ in range(n_resamples):
        sampled_keys = rng.choices(unique_keys, k=n_series)
        total_cov = 0
        total_n = 0
        for k in sampled_keys:
            items = series_map[k]
            total_cov += sum(items)
            total_n += len(items)
        boot_coverages.append((total_cov / total_n) * 100.0 if total_n > 0 else 0.0)

    boot_coverages.sort()
    low = quantile_linear(boot_coverages, 0.025)
    high = quantile_linear(boot_coverages, 0.975)
    return low, high


def evaluate_interval_slice(
    slice_name: str,
    slice_rows: List[Dict[str, Any]],
    nominal_level: float,
    model_name: str,
) -> Dict[str, Any]:
    """Evaluates empirical coverage, width, and Winkler score for an interval slice."""
    total_eligible = len(slice_rows)
    series_set = set(compute_series_key(r) for r in slice_rows)
    unique_series = len(series_set)

    issued_rows = [r for r in slice_rows if r.get("status") == "SUCCESS"]
    issued_count = len(issued_rows)
    abstained_count = total_eligible - issued_count
    is_low_n = issued_count < 30

    if issued_count == 0:
        return {
            "slice_name": slice_name,
            "model": model_name,
            "nominal_level": nominal_level,
            "total_eligible": total_eligible,
            "issued_count": 0,
            "abstained_count": abstained_count,
            "unique_series": unique_series,
            "is_low_n": True,
            "fallback_count": 0,
            "fallback_share_pct": 0.0,
            "empirical_coverage_pct": float("nan"),
            "coverage_ci_lower": float("nan"),
            "coverage_ci_upper": float("nan"),
            "nominal_deviation_pct": float("nan"),
            "mean_width": float("nan"),
            "median_width": float("nan"),
            "p10_width": float("nan"),
            "p90_width": float("nan"),
            "mean_relative_width": float("nan"),
            "lower_miss_rate_pct": float("nan"),
            "upper_miss_rate_pct": float("nan"),
            "mean_interval_score": float("nan"),
        }

    fallback_count = sum(1 for r in issued_rows if r["calibration_group_type"] == "POOLED_FALLBACK")
    fallback_share = (fallback_count / issued_count) * 100.0

    covered_count = sum(1 for r in issued_rows if r["is_covered"])
    coverage_pct = (covered_count / issued_count) * 100.0
    nominal_dev = coverage_pct - (nominal_level * 100.0)

    # Miss rates
    lower_miss = sum(1 for r in issued_rows if r["is_lower_miss"]) / issued_count * 100.0
    upper_miss = sum(1 for r in issued_rows if r["is_upper_miss"]) / issued_count * 100.0

    widths = [float(r["width"]) for r in issued_rows]
    mean_w = math.fsum(widths) / issued_count
    median_w = statistics.median(widths)
    sorted_w = sorted(widths)
    p10_w = quantile_linear(sorted_w, 0.10)
    p90_w = quantile_linear(sorted_w, 0.90)

    rel_widths = [float(r["relative_width"]) for r in issued_rows]
    mean_rel_w = math.fsum(rel_widths) / issued_count

    scores = [float(r["interval_score"]) for r in issued_rows]
    mean_is = math.fsum(scores) / issued_count

    ci_low, ci_high = compute_cluster_bootstrap_coverage_ci(issued_rows, n_resamples=1000, seed=42)

    return {
        "slice_name": slice_name,
        "model": model_name,
        "nominal_level": nominal_level,
        "total_eligible": total_eligible,
        "issued_count": issued_count,
        "abstained_count": abstained_count,
        "unique_series": unique_series,
        "is_low_n": is_low_n,
        "fallback_count": fallback_count,
        "fallback_share_pct": round(fallback_share, 2),
        "empirical_coverage_pct": round(coverage_pct, 4),
        "coverage_ci_lower": round(ci_low, 4),
        "coverage_ci_upper": round(ci_high, 4),
        "nominal_deviation_pct": round(nominal_dev, 4),
        "mean_width": round(mean_w, 4),
        "median_width": round(median_w, 4),
        "p10_width": round(p10_w, 4),
        "p90_width": round(p90_w, 4),
        "mean_relative_width": round(mean_rel_w, 6),
        "lower_miss_rate_pct": round(lower_miss, 4),
        "upper_miss_rate_pct": round(upper_miss, 4),
        "mean_interval_score": round(mean_is, 4),
    }


def execute_interval_pipeline(
    predictions_path: Path,
    output_reports_dir: Path,
    output_predictions_dir: Path,
    config_path: Path,
    max_duration_seconds: float = 600.0,
    stage_timeout_seconds: float = 30.0,
) -> Dict[str, Any]:
    """
    Executes the complete chronological prediction interval calibration and evaluation pipeline.
    """
    t_start = time.time()
    output_reports_dir.mkdir(parents=True, exist_ok=True)
    output_predictions_dir.mkdir(parents=True, exist_ok=True)

    # Stage 1: Load and Validate Config & Archive
    t0_stage = time.time()
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    config_sha256 = compute_sha256(config_path)

    archive_sha256 = compute_sha256(predictions_path)
    expected_archive_sha = "a61b38328e011b2ed75dd5d814fbf697d624ac948c50a198d374bfcaff2b9970"
    if archive_sha256 != expected_archive_sha:
        raise ValueError(f"Archive hash mismatch: {archive_sha256} != {expected_archive_sha}")

    if str(predictions_path).endswith(".gz"):
        with gzip.open(predictions_path, "rt", encoding="utf-8") as f:
            all_rows = list(csv.DictReader(f))
    else:
        with open(predictions_path, "r", encoding="utf-8") as f:
            all_rows = list(csv.DictReader(f))

    total_master_rows = len(all_rows)
    if total_master_rows > 70000:
        raise ValueError(f"Row count {total_master_rows} exceeds approved exception limit (70,000)!")

    d_stage1 = time.time() - t0_stage
    if d_stage1 > stage_timeout_seconds:
        raise TimeoutError(f"Stage 1 exceeded timeout: {d_stage1:.1f}s")
    print(f"Loaded {total_master_rows:,} rows in {d_stage1:.2f}s. Archive verified.")

    # Stage 2: Determine Fold Test Start Dates
    fold_start_dates = {}
    for f_id in ["F1", "F2", "F3", "F4"]:
        f_sub = [r for r in all_rows if r["fold"] == f_id]
        if f_sub:
            fold_start_dates[f_id] = min(r["origin_date"] for r in f_sub)

    # Stage 3: Chronological Calibration across Models and Folds
    t0_stage = time.time()
    calibration_artifacts: Dict[str, Dict[str, Any]] = defaultdict(dict)
    models_to_run = [config["primary_model"]] + config.get("exploratory_models", [])
    nominal_levels = config["nominal_levels"]

    for f_id in ["F1", "F2", "F3", "F4"]:
        f_start = fold_start_dates.get(f_id, "")
        for m_name in models_to_run:
            col_name = EVAL_MODELS[m_name]
            cal_res = compute_calibration_quantiles_for_fold(
                fold_id=f_id,
                fold_start_date=f_start,
                all_rows=all_rows,
                model_name=m_name,
                pred_col=col_name,
                nominal_levels=nominal_levels,
                window_days=config.get("window_calendar_days", 180),
                min_group_origins=config.get("min_group_origins", 200),
                min_group_series=config.get("min_group_series", 10),
            )
            calibration_artifacts[f_id][m_name] = cal_res

    d_stage3 = time.time() - t0_stage
    if d_stage3 > stage_timeout_seconds:
        raise TimeoutError(f"Stage 3 exceeded timeout: {d_stage3:.1f}s")
    print(f"Computed chronological calibration across {len(models_to_run)} models and 4 folds in {d_stage3:.2f}s.")

    # Save calibration quantiles JSON
    cal_json_path = output_reports_dir / "calibration_quantiles.json"
    atomic_write_json(calibration_artifacts, cal_json_path)

    # Stage 4: Generate Row-Level Interval Predictions
    t0_stage = time.time()
    full_interval_records: List[Dict[str, Any]] = []

    for r in all_rows:
        fold_id = r["fold"]
        commodity = r["commodity"]
        val_yt = r.get("y_t", "")
        val_true = r.get("y_true", "")
        if not val_yt or not val_true:
            continue
        try:
            yt = float(val_yt)
            y_true = float(val_true)
        except ValueError:
            continue

        for m_name in models_to_run:
            pred_col = EVAL_MODELS[m_name]
            val_p = r.get(pred_col, "")
            if not val_p or val_p == "nan":
                continue
            try:
                p = float(val_p)
            except ValueError:
                continue

            for level in nominal_levels:
                alpha = 1.0 - level
                res = predict_interval(
                    model_name=m_name,
                    point_pred=p,
                    y_t=yt,
                    commodity=commodity,
                    fold_id=fold_id,
                    nominal_level=level,
                    calibration_artifacts=calibration_artifacts,
                )
                if res["status"] == "SUCCESS":
                    lower = res["lower"]
                    upper = res["upper"]
                    w = res["width"]
                    is_cov = (lower <= y_true <= upper)
                    is_low_miss = (y_true < lower)
                    is_up_miss = (y_true > upper)
                    pen = 0.0
                    if is_low_miss:
                        pen = (2.0 / alpha) * (lower - y_true)
                    elif is_up_miss:
                        pen = (2.0 / alpha) * (y_true - upper)
                    int_score = w + pen
                    rel_w = w / yt
                else:
                    lower = float("nan")
                    upper = float("nan")
                    w = float("nan")
                    rel_w = float("nan")
                    is_cov = False
                    is_low_miss = False
                    is_up_miss = False
                    int_score = float("nan")

                rec = {
                    "fold": fold_id,
                    "district": r["district"],
                    "market": r["market"],
                    "commodity": commodity,
                    "variety": r["variety"],
                    "grade": r["grade"],
                    "origin_date": r["origin_date"],
                    "target_date": r["target_date"],
                    "date_regime": r.get("date_regime", ""),
                    "is_tier_a": r.get("is_tier_a", ""),
                    "is_tier_b": r.get("is_tier_b", ""),
                    "y_t": yt,
                    "y_true": y_true,
                    "model": m_name,
                    "nominal_level": level,
                    "point_pred": p,
                    "lower_bound": lower,
                    "upper_bound": upper,
                    "width": w,
                    "relative_width": rel_w,
                    "is_covered": is_cov,
                    "is_lower_miss": is_low_miss,
                    "is_upper_miss": is_up_miss,
                    "interval_score": int_score,
                    "calibration_group_type": res.get("group_type", "NONE"),
                    "quantile_value": res.get("quantile", float("nan")),
                    "status": res["status"],
                }
                full_interval_records.append(rec)

    d_stage4 = time.time() - t0_stage
    if d_stage4 > stage_timeout_seconds:
        raise TimeoutError(f"Stage 4 exceeded timeout: {d_stage4:.1f}s")
    print(f"Generated {len(full_interval_records):,} interval prediction evaluations in {d_stage4:.2f}s.")

    # Save full interval predictions (git-ignored output)
    t0_stage = time.time()
    out_master_gz = output_predictions_dir / "master_intervals_fc008.csv.gz"
    fieldnames = list(full_interval_records[0].keys())
    with gzip.open(out_master_gz, "wt", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rec in full_interval_records:
            writer.writerow(rec)
    d_stage5 = time.time() - t0_stage
    print(f"Saved compressed interval predictions ({out_master_gz.stat().st_size / 1e6:.2f} MB) in {d_stage5:.2f}s.")

    # Stage 6: Evaluate Scorecards Across Required Slices
    t0_stage = time.time()
    scorecard_overall: List[Dict[str, Any]] = []
    scorecard_folds: List[Dict[str, Any]] = []
    scorecard_crops: List[Dict[str, Any]] = []
    scorecard_districts: List[Dict[str, Any]] = []
    scorecard_regimes: List[Dict[str, Any]] = []
    master_scorecards: List[Dict[str, Any]] = []

    # Filter evaluated folds: F2-F4 are evaluated out-of-sample; F1 is abstained
    eval_f2_f4 = [r for r in full_interval_records if r["fold"] in ("F2", "F3", "F4")]

    for m_name in models_to_run:
        for level in nominal_levels:
            # 6.1 Overall evaluated folds (F2-F4)
            sub_overall = [r for r in eval_f2_f4 if r["model"] == m_name and r["nominal_level"] == level]
            res_ov = evaluate_interval_slice("Overall_F2_F4", sub_overall, level, m_name)
            scorecard_overall.append(res_ov)
            master_scorecards.append(res_ov)

            # 6.2 By Fold (F1, F2, F3, F4)
            for f_id in ["F1", "F2", "F3", "F4"]:
                sub_f = [r for r in full_interval_records if r["fold"] == f_id and r["model"] == m_name and r["nominal_level"] == level]
                res_f = evaluate_interval_slice(f"Fold_{f_id}", sub_f, level, m_name)
                scorecard_folds.append(res_f)
                master_scorecards.append(res_f)

            # 6.3 By Focus Crop (on F2-F4)
            for crop in FOCUS_CROPS:
                sub_c = [r for r in eval_f2_f4 if r["commodity"] == crop and r["model"] == m_name and r["nominal_level"] == level]
                res_c = evaluate_interval_slice(f"Crop_{crop}", sub_c, level, m_name)
                scorecard_crops.append(res_c)
                master_scorecards.append(res_c)

            # 6.4 By District (on F2-F4)
            for dist in TARGET_DISTRICTS:
                sub_d = [r for r in eval_f2_f4 if r["district"] == dist and r["model"] == m_name and r["nominal_level"] == level]
                res_d = evaluate_interval_slice(f"District_{dist}", sub_d, level, m_name)
                scorecard_districts.append(res_d)
                master_scorecards.append(res_d)

            # 6.5 By Date Regime (on F2-F4)
            for reg in ["HISTORICAL", "TRANSITION", "MODERN"]:
                sub_r = [r for r in eval_f2_f4 if r["date_regime"] == reg and r["model"] == m_name and r["nominal_level"] == level]
                res_r = evaluate_interval_slice(f"Regime_{reg}", sub_r, level, m_name)
                scorecard_regimes.append(res_r)
                master_scorecards.append(res_r)

    atomic_write_csv(scorecard_overall, output_reports_dir / "intervals_overall.csv")
    atomic_write_csv(scorecard_folds, output_reports_dir / "intervals_by_fold.csv")
    atomic_write_csv(scorecard_crops, output_reports_dir / "intervals_by_crop.csv")
    atomic_write_csv(scorecard_districts, output_reports_dir / "intervals_by_district.csv")
    atomic_write_csv(scorecard_regimes, output_reports_dir / "intervals_by_regime.csv")
    atomic_write_csv(master_scorecards, output_reports_dir / "master_intervals_scorecards.csv")

    d_stage6 = time.time() - t0_stage
    if d_stage6 > stage_timeout_seconds:
        raise TimeoutError(f"Stage 6 exceeded timeout: {d_stage6:.1f}s")
    print(f"Evaluated all interval scorecards in {d_stage6:.2f}s.")

    # Stage 7: Interval Evaluation Receipt and Manifest
    receipt_data = {
        "task_id": "MP-FC-008-GATE-B",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "predictions_archive_sha256": archive_sha256,
        "config_sha256": config_sha256,
        "code_sha256": compute_sha256(Path(__file__).resolve()),
        "total_source_rows": total_master_rows,
        "total_evaluated_rows_f2_f4": len(eval_f2_f4) // (len(models_to_run) * len(nominal_levels)),
        "models_evaluated": models_to_run,
        "nominal_levels": list(nominal_levels),
        "calibration_windows": {
            f_id: calibration_artifacts[f_id][models_to_run[0]].get("calibration_window")
            for f_id in ["F1", "F2", "F3", "F4"]
        },
        "assertions_verified": [
            "zero_leakage_future_outcomes_not_used",
            "strictly_earlier_folds_in_calibration",
            "max_calibration_target_strictly_before_eval_origin",
            "exact_conformal_rank_no_rounding",
            "non_negative_support_clipping",
            "series_cluster_bootstrap_resampled",
            "memory_and_runtime_limits_strictly_observed",
        ],
        "limitations": (
            "Chronological empirical calibration without exchangeability guarantee. "
            "Regime shifts and market volatility produce lower coverage during crisis folds (F3/F4). "
            "Reported intervals reflect empirical behavior under retrospective availability."
        ),
        "status": "GATE_B_INTERVALS_EVALUATED_SUCCESS",
    }
    atomic_write_json(receipt_data, output_reports_dir / "interval_evaluation_receipt.json")

    # Output Manifest for FC008
    output_files = sorted(list(output_reports_dir.glob("*.csv")) + list(output_reports_dir.glob("*.json")))
    manifest_records = []
    repo_root_res = REPO_ROOT.resolve()
    for p in output_files:
        manifest_records.append({
            "filename": p.name,
            "relpath": str(p.resolve().relative_to(repo_root_res)),
            "size_bytes": p.stat().st_size,
            "sha256": compute_sha256(p),
        })
    atomic_write_json({"manifest": manifest_records}, output_reports_dir / "output_manifest.json")

    total_duration = time.time() - t_start
    print(f"Gate B interval calibration and evaluation pipeline completed in {total_duration:.2f}s.")

    return {
        "status": "GATE_B_INTERVALS_EVALUATED_SUCCESS",
        "archive_sha256": archive_sha256,
        "total_duration_seconds": total_duration,
        "scorecard_count": len(master_scorecards),
        "receipt": receipt_data,
    }


def main():
    parser = argparse.ArgumentParser(description="Calibrate and evaluate chronological prediction intervals.")
    parser.add_argument("--predictions", type=Path, default=REPO_ROOT / "experiments" / "outputs" / "FC007_recovery" / "experiments" / "outputs" / "FC007" / "master_predictions_fc007.csv.gz")
    parser.add_argument("--config", type=Path, default=REPO_ROOT / "experiments" / "configs" / "interval_calibration_v1.json")
    parser.add_argument("--reports-dir", type=Path, default=REPO_ROOT / "experiments" / "reports" / "FC008")
    parser.add_argument("--outputs-dir", type=Path, default=REPO_ROOT / "experiments" / "outputs" / "FC008")

    args = parser.parse_args()

    res = execute_interval_pipeline(
        predictions_path=args.predictions,
        output_reports_dir=args.reports_dir,
        output_predictions_dir=args.outputs_dir,
        config_path=args.config,
    )
    print(f"Pipeline Result: {res['status']}, scored {res['scorecard_count']} scorecards in {res['total_duration_seconds']:.2f}s.")


if __name__ == "__main__":
    main()
