"""
APMC Mandi Intelligence System - Step 13 Prospective Shadow Validation
Implements bounded, pure standard-library shadow registry, forecast issuance,
outcome matching, and evaluation scorecards under protocol APMC-PV-2026-V1.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, asdict
from datetime import datetime, date, timezone, timedelta
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple, Union

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = REPO_ROOT / "experiments" / "configs" / "forward_validation_protocol_v1.json"
DEFAULT_REGISTRY_DIR = REPO_ROOT / "data" / "shadow_registry"

IST_TZ = timezone(timedelta(hours=5, minutes=30))


def get_current_ist_date() -> date:
    """Returns current date in Asia/Kolkata timezone (UTC+05:30)."""
    return datetime.now(IST_TZ).date()


def compute_file_sha256(filepath: Union[str, Path]) -> str:
    """Computes SHA-256 checksum of a file in streaming chunks."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def compute_dict_hash(data: Dict[str, Any]) -> str:
    """Deterministic canonical JSON SHA-256 hash."""
    canonical_bytes = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical_bytes).hexdigest()


@dataclass
class ShadowRecord:
    record_id: str
    cohort_id: str
    protocol_version: str
    config_hash: str
    code_version: str
    series_id: str
    canonical_identity: Dict[str, str]
    origin_observation_date: str
    origin_modal_price: Optional[float]
    units: str
    source_index_file_sha256: str
    composite_source_sha256: str
    issuance_timestamp_utc: str
    target_expected_date: str
    target_window_min_date: str
    target_window_max_date: str
    model_id: str
    point_forecast: Optional[float]
    interval_status: str
    status: str
    abstention_reason: Optional[str]
    prev_record_hash: str
    record_hash: str = ""

    def compute_hash(self) -> str:
        d = asdict(self)
        d.pop("record_hash", None)
        canonical_str = json.dumps(d, sort_keys=True, separators=(",", ":"))
        combined = f"{self.prev_record_hash}|{canonical_str}".encode("utf-8")
        return hashlib.sha256(combined).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


@dataclass
class OutcomeRecord:
    outcome_id: str
    series_id: str
    canonical_identity: Dict[str, str]
    observation_date: str
    modal_price: float
    min_price: Optional[float]
    max_price: Optional[float]
    units: str
    source_file_sha256: str
    import_timestamp_utc: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ProspectiveShadowRegistry:
    """
    Manages append-only forward forecast shadow logging, outcome matching,
    and scorecard evaluation with strict resource budgets and idempotency.
    """

    def __init__(
        self,
        registry_dir: Optional[Union[str, Path]] = None,
        config_path: Optional[Union[str, Path]] = None,
    ):
        self.registry_dir = Path(registry_dir) if registry_dir else DEFAULT_REGISTRY_DIR
        self.config_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        self.config = self._load_protocol_config()
        self.config_hash = compute_dict_hash(self.config)

    def _load_protocol_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Protocol configuration not found: {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_log_path(self, filename: str) -> Path:
        return self.registry_dir / filename

    def init_registry(self, force: bool = False) -> Dict[str, Any]:
        """Initializes shadow registry directory and freezes protocol snapshot."""
        if self.registry_dir.exists() and not force:
            meta_file = self.registry_dir / "registry_meta.json"
            if meta_file.exists():
                with open(meta_file, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                return {
                    "status": "EXISTING_REGISTRY_PRESERVED",
                    "registry_dir": str(self.registry_dir),
                    "created_at_utc": existing.get("created_at_utc"),
                    "config_hash": existing.get("config_hash"),
                }

        self.registry_dir.mkdir(parents=True, exist_ok=True)
        now_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        meta = {
            "protocol_id": self.config.get("protocol_id", "APMC-PV-2026-V1"),
            "protocol_version": self.config.get("protocol_version", "1.0.0"),
            "config_hash": self.config_hash,
            "created_at_utc": now_utc,
            "registry_status": "FROZEN_ACTIVE",
            "integrity_mechanism": "LOCAL_SHA256_HASH_CHAIN (Not externally notarized)",
        }
        with open(self.registry_dir / "registry_meta.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        # Initialize empty log files with header comments
        for fname in ["forward_forecast_log.jsonl", "forward_outcomes_log.jsonl", "forward_matches.jsonl"]:
            p = self.registry_dir / fname
            if not p.exists():
                p.touch()

        return {
            "status": "INITIALIZED",
            "registry_dir": str(self.registry_dir),
            "created_at_utc": now_utc,
            "config_hash": self.config_hash,
        }

    def validate_snapshot(self, snapshot_path: Union[str, Path]) -> Dict[str, Any]:
        """Validates snapshot file under strict memory, row, and type bounds."""
        p = Path(snapshot_path)
        if not p.exists():
            raise FileNotFoundError(f"Snapshot file not found: {p}")

        file_size = p.stat().st_size
        if file_size > 10 * 1024 * 1024:
            raise ValueError(f"Snapshot file exceeds 10 MB limit ({file_size} bytes)")

        sha256 = compute_file_sha256(p)

        with open(p, "r", encoding="utf-8") as f:
            payload = json.load(f)

        if not isinstance(payload, dict):
            raise TypeError("Snapshot root must be a JSON object")

        raw_series = payload.get("series")
        if raw_series is None:
            raise ValueError("Snapshot missing required 'series' property")

        if isinstance(raw_series, list):
            series_list = raw_series
        elif isinstance(raw_series, dict):
            series_list = list(raw_series.values())
        else:
            raise TypeError("Snapshot series must be a list or object")

        if len(series_list) > 50000:
            raise ValueError(f"Snapshot exceeds row limit ({len(series_list)} > 50,000)")

        valid_count = 0
        accepted_count = 0
        review_count = 0
        districts = set()
        commodities = set()

        for item in series_list:
            if not isinstance(item, dict):
                continue
            mp = item.get("modal_price")
            if mp is not None and isinstance(mp, (int, float)) and math.isfinite(float(mp)) and float(mp) > 0:
                valid_count += 1
                districts.add(item.get("district", "Unknown"))
                commodities.add(item.get("commodity", "Unknown"))
                if item.get("price_display_permitted", True):
                    accepted_count += 1
                else:
                    review_count += 1

        return {
            "snapshot_path": str(p),
            "file_size_bytes": file_size,
            "file_sha256": sha256,
            "composite_source_sha256": payload.get("composite_source_sha256", "UNKNOWN"),
            "total_series_rows": len(series_list),
            "valid_series_count": valid_count,
            "accepted_eligible_count": accepted_count,
            "review_withheld_count": review_count,
            "districts_covered": sorted(list(districts)),
            "commodities_covered": sorted(list(commodities)),
            "generated_at_utc": payload.get("generated_at_utc"),
        }

    def _get_last_record_hash(self, log_path: Path) -> str:
        """Reads the hash of the last record in a jsonl file for chaining."""
        if not log_path.exists() or log_path.stat().st_size == 0:
            return "0" * 64

        last_line = ""
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    last_line = line.strip()

        if not last_line:
            return "0" * 64

        try:
            rec = json.loads(last_line)
            return rec.get("record_hash", "0" * 64)
        except Exception:
            return "0" * 64

    def issue_shadow_records(
        self,
        snapshot_path: Union[str, Path],
        dry_run: bool = False,
        simulated_current_date_ist: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Processes validated snapshot and issues forward shadow persistence forecasts.
        Strictly enforces the frozen freshness policy and append-only idempotency.
        """
        val_res = self.validate_snapshot(snapshot_path)
        p = Path(snapshot_path)
        with open(p, "r", encoding="utf-8") as f:
            payload = json.load(f)

        raw_series = payload.get("series")
        if isinstance(raw_series, dict):
            series_list = list(raw_series.values())
        else:
            series_list = raw_series

        current_date_ist = simulated_current_date_ist or get_current_ist_date()
        now_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        target_districts = set(self.config.get("cohort", {}).get("target_districts", []))
        declared_crops = set(self.config.get("cohort", {}).get("declared_focus_crops", []))
        nominal_days = self.config.get("horizon_matching", {}).get("nominal_days", 7)
        win_min = self.config.get("horizon_matching", {}).get("window_min_days", 6)
        win_max = self.config.get("horizon_matching", {}).get("window_max_days", 8)
        max_age_days = self.config.get("freshness_policy", {}).get("max_observation_age_days_ist", 1)

        forecast_log = self.get_log_path("forward_forecast_log.jsonl")
        self.init_registry(force=False)

        # Existing record keys to guarantee idempotency
        existing_records: Dict[str, str] = {}
        if forecast_log.exists():
            with open(forecast_log, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            rec = json.loads(line)
                            k = f"{rec.get('series_id')}|{rec.get('origin_observation_date')}|{rec.get('target_expected_date')}"
                            existing_records[k] = rec.get("record_hash", "")
                        except Exception:
                            continue

        issued_records: List[ShadowRecord] = []
        skipped_duplicate_count = 0
        abstained_stale_count = 0
        abstained_review_count = 0
        abstained_scope_count = 0
        issued_point_count = 0

        last_hash = self._get_last_record_hash(forecast_log)

        for s in series_list:
            if not isinstance(s, dict):
                continue

            sid = s.get("series_id") or f"series_{s.get('district')}_{s.get('market')}_{s.get('commodity')}".lower()
            dist = s.get("district", "")
            comm = s.get("commodity", "")
            market = s.get("market_canonical") or s.get("market", "")
            variety = s.get("variety", "")
            grade = s.get("grade", "")
            obs_date_str = s.get("latest_observation_date") or s.get("observation_date", "")
            mp = s.get("modal_price")
            permitted = s.get("capabilities", {}).get(
                "price_display_permitted", s.get("price_display_permitted", True)
            )

            # Target crop & district filter
            if dist not in target_districts or comm not in declared_crops:
                abstained_scope_count += 1
                continue

            # Parse observation date
            try:
                obs_date = datetime.strptime(obs_date_str, "%Y-%m-%d").date()
            except Exception:
                continue

            target_exp = obs_date + timedelta(days=nominal_days)
            target_min = obs_date + timedelta(days=win_min)
            target_max = obs_date + timedelta(days=win_max)

            record_key = f"{sid}|{obs_date_str}|{target_exp.isoformat()}"
            if record_key in existing_records:
                skipped_duplicate_count += 1
                continue

            # Freshness policy check
            age_days_ist = (current_date_ist - obs_date).days
            is_stale = age_days_ist > max_age_days

            rec_id = f"SHD-{obs_date.strftime('%Y%m%d')}-{sid[:12].replace('_', '').upper()}-{len(issued_records)+1:03d}"

            if not permitted:
                status = "ABSTAINED"
                reason = "UNKNOWN_MARKET_IDENTITY_REVIEW"
                point_fc = None
                abstained_review_count += 1
            elif is_stale:
                status = "ABSTAINED"
                reason = f"STALE_OBSERVATION_EXCEEDS_{max_age_days}_DAY (Age: {age_days_ist} days)"
                point_fc = None
                abstained_stale_count += 1
            else:
                status = "ISSUED"
                reason = None
                point_fc = float(mp)
                issued_point_count += 1

            rec = ShadowRecord(
                record_id=rec_id,
                cohort_id=self.config.get("cohort", {}).get("cohort_id", "UP_CANDIDATE_2026_COHORT_A"),
                protocol_version=self.config.get("protocol_version", "1.0.0"),
                config_hash=self.config_hash,
                code_version="git-6af1dbc0",
                series_id=sid,
                canonical_identity={
                    "district": dist,
                    "market": market,
                    "commodity": comm,
                    "variety": variety,
                    "grade": grade,
                },
                origin_observation_date=obs_date_str,
                origin_modal_price=float(mp) if (mp is not None and permitted) else None,
                units=s.get("units", "INR/quintal"),
                source_index_file_sha256=val_res["file_sha256"],
                composite_source_sha256=val_res["composite_source_sha256"],
                issuance_timestamp_utc=now_utc,
                target_expected_date=target_exp.isoformat(),
                target_window_min_date=target_min.isoformat(),
                target_window_max_date=target_max.isoformat(),
                model_id="naive_persistence",
                point_forecast=point_fc,
                interval_status="UNAVAILABLE",
                status=status,
                abstention_reason=reason,
                prev_record_hash=last_hash,
            )
            rec.record_hash = rec.compute_hash()
            last_hash = rec.record_hash
            issued_records.append(rec)

        if not dry_run and issued_records:
            # Atomic append with lock
            with open(forecast_log, "a", encoding="utf-8") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    for r in issued_records:
                        f.write(json.dumps(r.to_dict()) + "\n")
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

        return {
            "status": "DRY_RUN_COMPLETED" if dry_run else "SUCCESS_ISSUED",
            "snapshot_validated": val_res["file_sha256"],
            "current_date_ist": current_date_ist.isoformat(),
            "records_processed": len(issued_records),
            "issued_point_forecasts": issued_point_count,
            "abstained_stale": abstained_stale_count,
            "abstained_review": abstained_review_count,
            "abstained_out_of_scope": abstained_scope_count,
            "skipped_existing_duplicates": skipped_duplicate_count,
            "total_new_appended": 0 if dry_run else len(issued_records),
        }

    def import_outcomes(self, outcomes_path: Union[str, Path], dry_run: bool = False) -> Dict[str, Any]:
        """Imports candidate outcome observations into forward_outcomes_log.jsonl."""
        p = Path(outcomes_path)
        val = self.validate_snapshot(p)

        with open(p, "r", encoding="utf-8") as f:
            payload = json.load(f)

        raw = payload.get("series")
        series_list = list(raw.values()) if isinstance(raw, dict) else raw

        now_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        outcomes_log = self.get_log_path("forward_outcomes_log.jsonl")

        existing_keys = set()
        if outcomes_log.exists():
            with open(outcomes_log, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            r = json.loads(line)
                            existing_keys.add(f"{r.get('series_id')}|{r.get('observation_date')}")
                        except Exception:
                            continue

        new_outcomes: List[Dict[str, Any]] = []
        for s in series_list:
            if not isinstance(s, dict):
                continue
            sid = s.get("series_id") or f"series_{s.get('district')}_{s.get('market')}_{s.get('commodity')}".lower()
            obs_date = s.get("latest_observation_date") or s.get("observation_date")
            mp = s.get("modal_price")
            if not obs_date or mp is None or float(mp) <= 0:
                continue

            k = f"{sid}|{obs_date}"
            if k in existing_keys:
                continue

            rec = OutcomeRecord(
                outcome_id=f"OUT-{obs_date.replace('-', '')}-{sid[:12].replace('_', '').upper()}",
                series_id=sid,
                canonical_identity={
                    "district": s.get("district", ""),
                    "market": s.get("market_canonical") or s.get("market", ""),
                    "commodity": s.get("commodity", ""),
                    "variety": s.get("variety", ""),
                    "grade": s.get("grade", ""),
                },
                observation_date=obs_date,
                modal_price=float(mp),
                min_price=float(s.get("min_price", mp)),
                max_price=float(s.get("max_price", mp)),
                units=s.get("units", "INR/quintal"),
                source_file_sha256=val["file_sha256"],
                import_timestamp_utc=now_utc,
            )
            new_outcomes.append(rec.to_dict())

        if not dry_run and new_outcomes:
            with open(outcomes_log, "a", encoding="utf-8") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    for o in new_outcomes:
                        f.write(json.dumps(o) + "\n")
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

        return {
            "status": "DRY_RUN_COMPLETED" if dry_run else "SUCCESS_IMPORTED",
            "imported_file": str(p),
            "new_outcomes_count": len(new_outcomes),
        }

    def match_outcomes(
        self,
        dry_run: bool = False,
        simulated_current_date_ist: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Matches issued forecasts against observed outcomes according to frozen T+7 window
        and tie-breaking rules. Finalizes matches only after target window closes.
        """
        current_date_ist = simulated_current_date_ist or get_current_ist_date()

        forecast_log = self.get_log_path("forward_forecast_log.jsonl")
        outcomes_log = self.get_log_path("forward_outcomes_log.jsonl")
        matches_log = self.get_log_path("forward_matches.jsonl")

        if not forecast_log.exists():
            return {"status": "NO_FORECASTS_FOUND", "matched_count": 0}

        forecasts: List[Dict[str, Any]] = []
        with open(forecast_log, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    forecasts.append(json.loads(line))

        outcomes_by_series: Dict[str, List[Dict[str, Any]]] = {}
        if outcomes_log.exists():
            with open(outcomes_log, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        o = json.loads(line)
                        sid = o.get("series_id")
                        if sid:
                            outcomes_by_series.setdefault(sid, []).append(o)

        matches: List[Dict[str, Any]] = []
        pending_maturation_count = 0
        window_closed_unmatched_count = 0
        matured_match_count = 0
        provisional_count = 0

        for fc in forecasts:
            if fc.get("status") != "ISSUED" or fc.get("point_forecast") is None:
                continue

            sid = fc["series_id"]
            t_exp_str = fc["target_expected_date"]
            t_min_str = fc["target_window_min_date"]
            t_max_str = fc["target_window_max_date"]

            t_exp = datetime.strptime(t_exp_str, "%Y-%m-%d").date()
            t_min = datetime.strptime(t_min_str, "%Y-%m-%d").date()
            t_max = datetime.strptime(t_max_str, "%Y-%m-%d").date()

            window_closed = current_date_ist > t_max

            candidate_outcomes = outcomes_by_series.get(sid, [])
            # Filter outcomes in [t_min, t_max]
            window_obs = []
            for obs in candidate_outcomes:
                obs_d = datetime.strptime(obs["observation_date"], "%Y-%m-%d").date()
                if t_min <= obs_d <= t_max:
                    window_obs.append((obs_d, obs))

            selected_outcome = None
            if window_obs:
                # Tie-breaking precedence:
                # 1. Exact T+7
                exact = [o for d, o in window_obs if d == t_exp]
                if exact:
                    selected_outcome = exact[0]
                else:
                    # 2. Closest to T+7
                    window_obs.sort(key=lambda item: (abs((item[0] - t_exp).days), item[0]))
                    selected_outcome = window_obs[0][1]

            if window_closed:
                if selected_outcome:
                    match_status = "MATURED_MATCH"
                    matured_match_count += 1
                else:
                    match_status = "WINDOW_CLOSED_UNMATCHED"
                    window_closed_unmatched_count += 1
            else:
                if selected_outcome:
                    match_status = "PROVISIONAL_PENDING_WINDOW_CLOSE"
                    provisional_count += 1
                else:
                    match_status = "PENDING_MATURATION"
                    pending_maturation_count += 1

            if selected_outcome:
                y = float(selected_outcome["modal_price"])
                y_hat = float(fc["point_forecast"])
                abs_err = abs(y - y_hat)
                pct_err = (abs_err / y) * 100.0 if y > 0 else 0.0
                within_5 = pct_err <= 5.0
                obs_d_str = selected_outcome["observation_date"]
            else:
                y = None
                abs_err = None
                pct_err = None
                within_5 = None
                obs_d_str = None

            match_rec = {
                "match_id": f"MTC-{fc['record_id']}",
                "record_id": fc["record_id"],
                "series_id": sid,
                "commodity": fc.get("canonical_identity", {}).get("commodity"),
                "district": fc.get("canonical_identity", {}).get("district"),
                "market": fc.get("canonical_identity", {}).get("market"),
                "origin_date": fc["origin_observation_date"],
                "target_expected_date": t_exp_str,
                "target_window_min": t_min_str,
                "target_window_max": t_max_str,
                "point_forecast": fc["point_forecast"],
                "matched_observation_date": obs_d_str,
                "observed_modal_price": y,
                "absolute_error": abs_err,
                "percentage_error": pct_err,
                "within_5_pct_tolerance": within_5,
                "match_status": match_status,
                "evaluated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            }
            matches.append(match_rec)

        if not dry_run and matches:
            with open(matches_log, "w", encoding="utf-8") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    for m in matches:
                        f.write(json.dumps(m) + "\n")
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

        return {
            "status": "DRY_RUN_COMPLETED" if dry_run else "SUCCESS_MATCHED",
            "current_date_ist": current_date_ist.isoformat(),
            "total_evaluated_forecasts": len(matches),
            "matured_matches": matured_match_count,
            "provisional_matches": provisional_count,
            "pending_maturation": pending_maturation_count,
            "window_closed_unmatched": window_closed_unmatched_count,
        }

    def generate_scorecard(self) -> Dict[str, Any]:
        """
        Generates statistical scorecard over all matured matched forward outcomes.
        Distinguishes matured empirical results from pending horizons.
        """
        matches_log = self.get_log_path("forward_matches.jsonl")
        forecast_log = self.get_log_path("forward_forecast_log.jsonl")

        total_issued = 0
        total_abstained = 0
        if forecast_log.exists():
            with open(forecast_log, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        rec = json.loads(line)
                        if rec.get("status") == "ISSUED":
                            total_issued += 1
                        else:
                            total_abstained += 1

        matured_matches: List[Dict[str, Any]] = []
        pending_count = 0
        unmatched_count = 0

        if matches_log.exists():
            with open(matches_log, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        m = json.loads(line)
                        st = m.get("match_status")
                        if st == "MATURED_MATCH":
                            matured_matches.append(m)
                        elif st in ("PENDING_MATURATION", "PROVISIONAL_PENDING_WINDOW_CLOSE"):
                            pending_count += 1
                        elif st == "WINDOW_CLOSED_UNMATCHED":
                            unmatched_count += 1

        n = len(matured_matches)
        if n == 0:
            return {
                "scorecard_status": "EMPIRICAL_PENDING",
                "message": "Zero matured forward outcomes available. Forward horizons have not yet closed.",
                "total_forecasts_issued": total_issued,
                "total_forecasts_abstained": total_abstained,
                "pending_maturation_count": pending_count,
                "unmatched_closed_count": unmatched_count,
                "matured_matches_count": 0,
                "metrics": {
                    "primary_mae_inr": None,
                    "rmse_inr": None,
                    "mean_bias_inr": None,
                    "mape_pct": None,
                    "within_5_pct_tolerance_pct": None,
                },
                "advisory_status": "BLOCKED",
            }

        # Compute empirical statistics on matured matches
        abs_errors = [m["absolute_error"] for m in matured_matches]
        biases = [m["observed_modal_price"] - m["point_forecast"] for m in matured_matches]
        sq_errors = [b ** 2 for b in biases]
        pct_errors = [m["percentage_error"] for m in matured_matches]
        within_5_count = sum(1 for m in matured_matches if m["within_5_pct_tolerance"])

        mae = sum(abs_errors) / n
        rmse = math.sqrt(sum(sq_errors) / n)
        mean_bias = sum(biases) / n
        mape = sum(pct_errors) / n
        accuracy_5 = (within_5_count / n) * 100.0

        return {
            "scorecard_status": "ENGINEERING_COMPLETE_EMPIRICAL_EVALUATED",
            "protocol_id": self.config.get("protocol_id", "APMC-PV-2026-V1"),
            "cohort_id": self.config.get("cohort", {}).get("cohort_id", "UP_CANDIDATE_2026_COHORT_A"),
            "total_forecasts_issued": total_issued,
            "total_forecasts_abstained": total_abstained,
            "matured_matches_count": n,
            "pending_maturation_count": pending_count,
            "unmatched_closed_count": unmatched_count,
            "is_low_n": n < self.config.get("metrics", {}).get("min_sample_size_low_n_threshold", 30),
            "metrics": {
                "primary_mae_inr": round(mae, 2),
                "rmse_inr": round(rmse, 2),
                "mean_bias_inr": round(mean_bias, 2),
                "mape_pct": round(mape, 2),
                "within_5_pct_tolerance_pct": round(accuracy_5, 2),
            },
            "advisory_status": "BLOCKED",
            "disclaimer": "Empirical forward scores represent point forecast error on matured observations under frozen protocol. Advisory remains strictly blocked.",
        }


def main():
    parser = argparse.ArgumentParser(
        description="APMC Mandi Intelligence System - Step 13 Prospective Shadow Validation CLI"
    )
    parser.add_argument("--registry-dir", default=str(DEFAULT_REGISTRY_DIR), help="Custom registry directory")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Custom protocol config path")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. init
    p_init = subparsers.add_parser("init", help="Initialize or freeze protocol and registry")
    p_init.add_argument("--force", action="store_true", help="Force re-initialization")

    # 2. validate-snapshot
    p_val = subparsers.add_parser("validate-snapshot", help="Validate supplied market snapshot JSON")
    p_val.add_argument("snapshot_path", help="Path to snapshot file")

    # 3. issue
    p_issue = subparsers.add_parser("issue", help="Issue persistence shadow forecasts from snapshot")
    p_issue.add_argument("snapshot_path", help="Path to snapshot file")
    p_issue.add_argument("--dry-run", action="store_true", help="Inspect without appending to registry")
    p_issue.add_argument("--simulated-date", help="Simulate current IST date (YYYY-MM-DD) for backtesting")

    # 4. import-outcomes
    p_imp = subparsers.add_parser("import-outcomes", help="Import candidate outcome observations")
    p_imp.add_argument("outcomes_path", help="Path to outcomes snapshot file")
    p_imp.add_argument("--dry-run", action="store_true", help="Inspect without appending")

    # 5. match
    p_match = subparsers.add_parser("match", help="Match forecasts to outcomes according to T+7 window")
    p_match.add_argument("--dry-run", action="store_true", help="Inspect matches without writing")
    p_match.add_argument("--simulated-date", help="Simulate current IST date (YYYY-MM-DD) for maturation testing")

    # 6. scorecard
    subparsers.add_parser("scorecard", help="Generate performance scorecard over matured outcomes")

    args = parser.parse_args()
    reg = ProspectiveShadowRegistry(registry_dir=args.registry_dir, config_path=args.config)

    if args.command == "init":
        res = reg.init_registry(force=args.force)
        print(json.dumps(res, indent=2))

    elif args.command == "validate-snapshot":
        res = reg.validate_snapshot(args.snapshot_path)
        print(json.dumps(res, indent=2))

    elif args.command == "issue":
        sim_d = datetime.strptime(args.simulated_date, "%Y-%m-%d").date() if args.simulated_date else None
        res = reg.issue_shadow_records(args.snapshot_path, dry_run=args.dry_run, simulated_current_date_ist=sim_d)
        print(json.dumps(res, indent=2))

    elif args.command == "import-outcomes":
        res = reg.import_outcomes(args.outcomes_path, dry_run=args.dry_run)
        print(json.dumps(res, indent=2))

    elif args.command == "match":
        sim_d = datetime.strptime(args.simulated_date, "%Y-%m-%d").date() if args.simulated_date else None
        res = reg.match_outcomes(dry_run=args.dry_run, simulated_current_date_ist=sim_d)
        print(json.dumps(res, indent=2))

    elif args.command == "scorecard":
        res = reg.generate_scorecard()
        print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
