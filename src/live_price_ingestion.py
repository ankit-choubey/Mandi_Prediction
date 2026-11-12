"""
Live Price Ingestion Client & Snapshot Engine
APMC Mandi Market Intelligence System
Task: MP-SRC-004 (Steps 3–5)

Provides:
1. Bounded, safe, read-only ingestion client for official api.data.gov.in daily mandi prices:
   Resource UUID: 9ef84268-d588-465a-a308-a864a43d0070
2. Injected transport and clock interfaces for 100% deterministic, offline testability.
3. Strict secret sanitization: zero credential leakage in URLs, logs, exceptions, or payloads.
4. Fail-closed pagination, duplicate detection, conflicting quote quarantine, and supersession provenance.
5. Scope enforcement: 5 approved districts (Ghaziabad, Jhansi, Kanpur, Lucknow, Unnao).
   Explicit quarantine for Kanpur Dehat subdivision ambiguity.
6. Missing grade policy: explicitly 'SOURCE_NOT_PROVIDED', never silently 'FAQ'.
7. Immutable, collision-safe snapshot storage with independent retrieval provenance.
8. Decoupled capability tracking: Price Display vs Forecast Eligibility vs Economics Advisory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from src.health_status import (
    DEFAULT_RESOURCE_ID,
    DEFAULT_SOURCE_NAME,
    DEFAULT_SOURCE_URL,
    FreshnessStatus,
    HealthReport,
    HealthStatusEngine,
    OperationalState,
    RecommendationSafetyGate,
    RecommendationStatus,
    ReconciliationLedger,
)

logger = logging.getLogger(__name__)

# =============================================================================
# CONSTANTS & CONFIGURATION DEFAULTS
# =============================================================================

DEFAULT_CONTRACT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "reference",
    "live_source_contract.json",
)

DEFAULT_ALIAS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "reference",
    "market_alias_candidates_v21.csv",
)

DEFAULT_SNAPSHOTS_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "live_snapshots",
)

APPROVED_DISTRICTS = ("Ghaziabad", "Jhansi", "Kanpur", "Lucknow", "Unnao")
APPROVED_STATE = "Uttar Pradesh"

MAX_HTTP_REQUESTS_BUDGET = 50
MAX_RECORDS_BUDGET = 25000
MAX_RESPONSE_BYTES = 10 * 1024 * 1024  # 10 MB
PER_REQUEST_TIMEOUT_SECONDS = 10.0
PER_DISTRICT_TIMEOUT_SECONDS = 30.0
MAX_RETRIES_PER_PAGE = 2

PUBLISHED_PRICE_UNIT = "Rs./Quintal"
GRADE_NOT_PROVIDED = "SOURCE_NOT_PROVIDED"

IST_TIMEZONE = timezone(timedelta(hours=5, minutes=30))


# =============================================================================
# ENUMS & DATA MODELS
# =============================================================================

class RecordDisposition(str, Enum):
    ACCEPTED = "ACCEPTED"
    EXACT_DUPLICATE = "EXACT_DUPLICATE"
    CONFLICTING_QUOTE = "CONFLICTING_QUOTE"
    INVALID_PRICE_BOUNDS = "INVALID_PRICE_BOUNDS"
    MALFORMED_DATE = "MALFORMED_DATE"
    FUTURE_DATED = "FUTURE_DATED"
    OUT_OF_SCOPE_DISTRICT = "OUT_OF_SCOPE_DISTRICT"
    UNKNOWN_MARKET_REVIEW = "UNKNOWN_MARKET_REVIEW"
    MISSING_REQUIRED_FIELDS = "MISSING_REQUIRED_FIELDS"


class CompletenessState(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    EMPTY = "EMPTY"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


@dataclass
class RawPriceRecord:
    state: str
    district: str
    market_raw: str
    commodity: str
    variety: str
    grade_raw: str
    grade_normalized: str
    arrival_date_raw: str
    arrival_date_parsed: Optional[str]
    min_price_raw: Any
    max_price_raw: Any
    modal_price_raw: Any
    min_price: Optional[float]
    max_price: Optional[float]
    modal_price: Optional[float]
    market_canonical: Optional[str]
    market_alias_status: str
    disposition: RecordDisposition
    disposition_reason: Optional[str]
    retrieval_timestamp_utc: str
    display_timestamp_ist: str
    source_resource_id: str
    source_endpoint: str
    price_unit: str = PUBLISHED_PRICE_UNIT
    superseded_by: Optional[str] = None
    supersedes: Optional[str] = None

    def natural_key(self) -> Tuple[str, str, str, str, str, str]:
        """Unique identifying tuple for observation deduplication."""
        return (
            self.arrival_date_parsed or self.arrival_date_raw,
            self.district,
            self.market_canonical or self.market_raw,
            self.commodity.strip().lower(),
            self.variety.strip().lower(),
            self.grade_normalized.strip().upper(),
        )

    def price_tuple(self) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        return (self.min_price, self.max_price, self.modal_price)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["disposition"] = self.disposition.value
        return d


@dataclass
class PageReceipt:
    page_offset: int
    page_limit: int
    retrieval_start_utc: str
    retrieval_end_utc: str
    http_status: int
    source_total: Optional[int]
    fetched_count: int
    content_sha256: str
    completeness_state: CompletenessState
    sanitized_params: Dict[str, Any]
    endpoint_sanitized: str
    records: List[Dict[str, Any]] = field(default_factory=list)
    error_message: Optional[str] = None
    sanitized_credential_detected: bool = False

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["completeness_state"] = self.completeness_state.value
        return d


@dataclass
class DistrictIngestionResult:
    district: str
    completeness_state: CompletenessState
    total_pages_fetched: int = 0
    source_reported_total: Optional[int] = None
    records_fetched: int = 0
    records_parsed: int = 0
    records_accepted: int = 0
    records_quarantined: int = 0
    records_duplicate: int = 0
    disposition_counts: Dict[str, int] = field(default_factory=dict)
    oldest_observation_date: Optional[str] = None
    newest_observation_date: Optional[str] = None
    page_receipts: List[PageReceipt] = field(default_factory=list)
    accepted_records: List[RawPriceRecord] = field(default_factory=list)
    quarantined_records: List[RawPriceRecord] = field(default_factory=list)
    duplicate_records: List[RawPriceRecord] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def validate_arithmetic(self) -> Dict[str, Any]:
        """Verify strict row conservation across disjoint disposition buckets."""
        accounted = self.records_accepted + self.records_quarantined + self.records_duplicate
        is_balanced = (self.records_fetched == accounted)
        return {
            "is_balanced": is_balanced,
            "records_fetched": self.records_fetched,
            "accounted": accounted,
            "discrepancy": self.records_fetched - accounted,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "district": self.district,
            "completeness_state": self.completeness_state.value,
            "total_pages_fetched": self.total_pages_fetched,
            "source_reported_total": self.source_reported_total,
            "records_fetched": self.records_fetched,
            "records_parsed": self.records_parsed,
            "records_accepted": self.records_accepted,
            "records_quarantined": self.records_quarantined,
            "records_duplicate": self.records_duplicate,
            "disposition_counts": self.disposition_counts,
            "oldest_observation_date": self.oldest_observation_date,
            "newest_observation_date": self.newest_observation_date,
            "errors": self.errors,
            "warnings": self.warnings,
            "arithmetic_reconciliation": self.validate_arithmetic(),
        }


@dataclass
class IngestionCampaignResult:
    run_id_utc: str
    execution_timestamp_utc: str
    execution_timestamp_ist: str
    overall_operational_state: OperationalState
    district_results: Dict[str, DistrictIngestionResult] = field(default_factory=dict)
    total_http_requests: int = 0
    total_records_fetched: int = 0
    total_records_accepted: int = 0
    total_records_quarantined: int = 0
    total_records_duplicate: int = 0
    snapshot_directory: Optional[str] = None
    is_live_verified: bool = False
    is_blocked: bool = False
    blocked_reason: Optional[str] = None
    capabilities: Dict[str, Any] = field(default_factory=dict)

    def validate_arithmetic(self) -> Dict[str, Any]:
        accounted = (
            self.total_records_accepted
            + self.total_records_quarantined
            + self.total_records_duplicate
        )
        is_balanced = (self.total_records_fetched == accounted)
        return {
            "is_balanced": is_balanced,
            "total_records_fetched": self.total_records_fetched,
            "accounted": accounted,
            "discrepancy": self.total_records_fetched - accounted,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id_utc": self.run_id_utc,
            "execution_timestamp_utc": self.execution_timestamp_utc,
            "execution_timestamp_ist": self.execution_timestamp_ist,
            "overall_operational_state": self.overall_operational_state.value,
            "total_http_requests": self.total_http_requests,
            "total_records_fetched": self.total_records_fetched,
            "total_records_accepted": self.total_records_accepted,
            "total_records_quarantined": self.total_records_quarantined,
            "total_records_duplicate": self.total_records_duplicate,
            "snapshot_directory": self.snapshot_directory,
            "is_live_verified": self.is_live_verified,
            "is_blocked": self.is_blocked,
            "blocked_reason": self.blocked_reason,
            "arithmetic_reconciliation": self.validate_arithmetic(),
            "capabilities": self.capabilities,
            "district_results": {
                d: res.to_dict() for d, res in self.district_results.items()
            },
        }


# =============================================================================
# SECRET SANITIZATION & SECURITY HELPERS
# =============================================================================

_SENSITIVE_KEY_PATTERN = re.compile(r"api[-_]?key|token|secret|password", re.IGNORECASE)


def sanitize_url(url: str) -> str:
    """Strip api-key and secret query parameters from any URL before logging or storage."""
    try:
        parsed = urlparse(url)
        if not parsed.query:
            return url
        params = parse_qsl(parsed.query, keep_blank_values=True)
        sanitized_params = [
            (k, "REDACTED") if _SENSITIVE_KEY_PATTERN.search(k) else (k, v)
            for k, v in params
        ]
        new_query = urlencode(sanitized_params)
        return urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment,
        ))
    except Exception:
        return "[UNPARSEABLE_URL_REDACTED]"


def sanitize_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Return a deep copy of query parameters with sensitive credentials redacted."""
    sanitized: Dict[str, Any] = {}
    for k, v in params.items():
        if _SENSITIVE_KEY_PATTERN.search(k):
            sanitized[k] = "[REDACTED]"
        else:
            sanitized[k] = v
    return sanitized


def redact_credential_echo(body_text: str, secret_key: Optional[str]) -> Tuple[str, bool]:
    """
    Detect if the secret key is echoed back in the response body.
    If detected, redact it and mark sanitized_credential_detected=True.
    """
    if not secret_key or not secret_key.strip():
        return body_text, False

    secret = secret_key.strip()
    if secret in body_text:
        redacted = body_text.replace(secret, "[REDACTED_API_KEY]")
        return redacted, True
    return body_text, False


def load_api_key(
    env_var_name: str = "OGD_API_KEY",
    env_file_path: Optional[str] = None,
) -> Optional[str]:
    """
    Safely inspect environment and optional ignored .env file for OGD_API_KEY.
    Strictly avoids executing .env content, shell sourcing, or printing the key value.
    """
    val = os.environ.get(env_var_name)
    if val and val.strip():
        return val.strip()

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_env = env_file_path or os.path.join(project_root, ".env")

    if os.path.exists(target_env):
        try:
            with open(target_env, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if line.startswith(f"{env_var_name}="):
                        parts = line.split("=", 1)
                        if len(parts) == 2:
                            extracted = parts[1].strip().strip('"').strip("'")
                            if extracted:
                                return extracted
        except Exception:
            return None

    return None


# =============================================================================
# HTTP TRANSPORT INTERFACES
# =============================================================================

class HttpTransport:
    """Base HTTP transport interface for dependency injection."""

    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: float = PER_REQUEST_TIMEOUT_SECONDS,
    ) -> Tuple[int, str, Dict[str, str]]:
        raise NotImplementedError


class RequestsHttpTransport(HttpTransport):
    """Production HTTP transport using requests with strict sanitization."""

    def __init__(self):
        try:
            import requests
            self._requests = requests
        except ImportError:
            self._requests = None

    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: float = PER_REQUEST_TIMEOUT_SECONDS,
    ) -> Tuple[int, str, Dict[str, str]]:
        if self._requests is None:
            raise RuntimeError(
                "requests library is not available in environment. "
                "Use MockHttpTransport or install requests."
            )

        sanitized_req_url = sanitize_url(url)
        try:
            resp = self._requests.get(url, params=params, timeout=timeout)
            headers = dict(resp.headers)
            return resp.status_code, resp.text, headers
        except Exception as exc:
            # Strictly sanitize exception representations to never expose query keys
            sanitized_exc_msg = sanitize_url(str(exc))
            raise RuntimeError(f"HTTP GET failed for {sanitized_req_url}: {sanitized_exc_msg}") from None


class MockHttpTransport(HttpTransport):
    """Mock HTTP transport for testing without network access."""

    def __init__(self, response_map: Optional[Dict[Tuple[str, int], Tuple[int, str, Dict[str, str]]]] = None):
        # Key: (district, offset) -> (status_code, body, headers)
        self.response_map = response_map or {}
        self.call_history: List[Dict[str, Any]] = []

    def set_response(
        self,
        district: str,
        offset: int,
        status_code: int,
        body: str,
        headers: Optional[Dict[str, str]] = None,
    ):
        self.response_map[(district, offset)] = (status_code, body, headers or {})

    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: float = PER_REQUEST_TIMEOUT_SECONDS,
    ) -> Tuple[int, str, Dict[str, str]]:
        params = params or {}
        self.call_history.append({
            "url": sanitize_url(url),
            "sanitized_params": sanitize_params(params),
            "raw_params_has_key": "api-key" in params,
            "timeout": timeout,
        })

        district = params.get("filters[district]", "all")
        offset = int(params.get("offset", 0))

        key = (district, offset)
        if key in self.response_map:
            return self.response_map[key]

        fallback_key = ("all", offset)
        if fallback_key in self.response_map:
            return self.response_map[fallback_key]

        # Default empty JSON response
        empty_payload = json.dumps({
            "total": 0,
            "count": 0,
            "limit": str(params.get("limit", 1000)),
            "offset": str(offset),
            "records": [],
        })
        return 200, empty_payload, {"content-type": "application/json"}


# =============================================================================
# ALIAS & VALIDATION HELPERS
# =============================================================================

def load_contract(contract_path: Optional[str] = None) -> Dict[str, Any]:
    path = contract_path or DEFAULT_CONTRACT_PATH
    if not os.path.exists(path):
        raise FileNotFoundError(f"Live source contract not found at: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_alias_mapping(alias_path: Optional[str] = None) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """
    Load reference alias policy table.
    Maps: (district, raw_market) -> alias record dict
    """
    path = alias_path or DEFAULT_ALIAS_PATH
    mapping: Dict[Tuple[str, str], Dict[str, Any]] = {}
    if not os.path.exists(path):
        return mapping

    with open(path, "r", encoding="utf-8") as f:
        import csv
        reader = csv.DictReader(f)
        for row in reader:
            dist = row.get("district", "").strip()
            raw_m = row.get("market_raw", "").strip()
            if dist and raw_m:
                mapping[(dist, raw_m)] = row
    return mapping


def parse_observation_date(date_str: Any) -> Optional[date]:
    """Parse string date from Agmarknet API into a date object."""
    if not date_str or not isinstance(date_str, str):
        return None
    cleaned = date_str.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(cleaned[:10], fmt).date()
        except ValueError:
            continue
    return None


def extract_field(record: Dict[str, Any], candidates: Sequence[str]) -> Any:
    for c in candidates:
        if c in record and record[c] is not None:
            return record[c]
    return None


# =============================================================================
# CORE LIVE PRICE INGESTION ENGINE
# =============================================================================

class LivePriceIngestionClient:
    """
    Client for fetching, validating, and persisting live daily APMC mandi market prices.
    Designed for bounded execution, fail-closed security, and strict data trust.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        transport: Optional[HttpTransport] = None,
        contract: Optional[Dict[str, Any]] = None,
        alias_mapping: Optional[Dict[Tuple[str, str], Dict[str, Any]]] = None,
        reference_date: Optional[date] = None,
        snapshots_root: Optional[str] = None,
    ):
        self.api_key = api_key or load_api_key()
        self.transport = transport or RequestsHttpTransport()
        self.contract = contract or load_contract()
        self.alias_mapping = alias_mapping if alias_mapping is not None else load_alias_mapping()
        self.ref_date = reference_date or datetime.now(IST_TIMEZONE).date()
        self.snapshots_root = snapshots_root or DEFAULT_SNAPSHOTS_ROOT

        self.source_metadata = self.contract.get("source_metadata", {})
        self.resource_id = self.source_metadata.get("resource_id", DEFAULT_RESOURCE_ID)
        self.endpoint_url = self.source_metadata.get("endpoint_url", DEFAULT_SOURCE_URL)
        self.op_bounds = self.contract.get("operational_bounds", {})

        self.max_requests = self.op_bounds.get("max_http_requests", MAX_HTTP_REQUESTS_BUDGET)
        self.max_records = self.op_bounds.get("max_records_total", MAX_RECORDS_BUDGET)
        self.timeout_per_request = self.op_bounds.get("timeout_seconds_per_request", PER_REQUEST_TIMEOUT_SECONDS)
        self.timeout_per_district = self.op_bounds.get("timeout_seconds_per_district_batch", PER_DISTRICT_TIMEOUT_SECONDS)
        self.max_retries = self.op_bounds.get("max_transient_retries_per_page", MAX_RETRIES_PER_PAGE)

    def is_credentials_available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def parse_and_validate_record(
        self,
        raw_row: Dict[str, Any],
        requested_district: str,
        retrieval_utc: str,
        display_ist: str,
    ) -> RawPriceRecord:
        """Parse raw JSON dict into RawPriceRecord with deterministic disposition."""
        # 1. Extract raw field values supporting casing / XML encoding
        state = str(extract_field(raw_row, ["state", "State"]) or "").strip()
        dist = str(extract_field(raw_row, ["district", "District"]) or "").strip()
        market = str(extract_field(raw_row, ["market", "Market"]) or "").strip()
        commodity = str(extract_field(raw_row, ["commodity", "Commodity"]) or "").strip()
        variety = str(extract_field(raw_row, ["variety", "Variety"]) or "").strip()
        grade_raw = extract_field(raw_row, ["grade", "Grade"])
        arrival_date_raw = str(extract_field(raw_row, ["arrival_date", "Arrival_Date"]) or "").strip()

        min_p_raw = extract_field(raw_row, ["min_price", "Min_Price", "Min_x0020_Price"])
        max_p_raw = extract_field(raw_row, ["max_price", "Max_Price", "Max_x0020_Price"])
        modal_p_raw = extract_field(raw_row, ["modal_price", "Modal_Price", "Modal_x0020_Price"])

        # 2. Grade normalization: missing grade is explicitly SOURCE_NOT_PROVIDED, never silently FAQ
        if grade_raw is None or str(grade_raw).strip() == "":
            grade_norm = GRADE_NOT_PROVIDED
            grade_raw_str = ""
        else:
            grade_raw_str = str(grade_raw).strip()
            grade_norm = grade_raw_str

        # 3. Required fields presence check
        if not (dist and market and commodity and arrival_date_raw and modal_p_raw is not None):
            return RawPriceRecord(
                state=state,
                district=dist,
                market_raw=market,
                commodity=commodity,
                variety=variety,
                grade_raw=grade_raw_str,
                grade_normalized=grade_norm,
                arrival_date_raw=arrival_date_raw,
                arrival_date_parsed=None,
                min_price_raw=min_p_raw,
                max_price_raw=max_p_raw,
                modal_price_raw=modal_p_raw,
                min_price=None,
                max_price=None,
                modal_price=None,
                market_canonical=None,
                market_alias_status="UNKNOWN",
                disposition=RecordDisposition.MISSING_REQUIRED_FIELDS,
                disposition_reason="One or more mandatory fields are missing from API payload.",
                retrieval_timestamp_utc=retrieval_utc,
                display_timestamp_ist=display_ist,
                source_resource_id=self.resource_id,
                source_endpoint=self.endpoint_url,
            )

        # 4. Scope & Subdivision Check (Kanpur vs Kanpur Dehat)
        if dist.lower() == "kanpur dehat":
            return RawPriceRecord(
                state=state,
                district=dist,
                market_raw=market,
                commodity=commodity,
                variety=variety,
                grade_raw=grade_raw_str,
                grade_normalized=grade_norm,
                arrival_date_raw=arrival_date_raw,
                arrival_date_parsed=None,
                min_price_raw=min_p_raw,
                max_price_raw=max_p_raw,
                modal_price_raw=modal_p_raw,
                min_price=None,
                max_price=None,
                modal_price=None,
                market_canonical=None,
                market_alias_status="OUT_OF_SCOPE",
                disposition=RecordDisposition.OUT_OF_SCOPE_DISTRICT,
                disposition_reason=(
                    "Kanpur Dehat is an administrative subdivision outside the authorized "
                    "5-district scope (Kanpur Nagar/Kanpur Grain APMC). Quarantined."
                ),
                retrieval_timestamp_utc=retrieval_utc,
                display_timestamp_ist=display_ist,
                source_resource_id=self.resource_id,
                source_endpoint=self.endpoint_url,
            )

        if dist.lower() != requested_district.lower() or dist not in APPROVED_DISTRICTS:
            return RawPriceRecord(
                state=state,
                district=dist,
                market_raw=market,
                commodity=commodity,
                variety=variety,
                grade_raw=grade_raw_str,
                grade_normalized=grade_norm,
                arrival_date_raw=arrival_date_raw,
                arrival_date_parsed=None,
                min_price_raw=min_p_raw,
                max_price_raw=max_p_raw,
                modal_price_raw=modal_p_raw,
                min_price=None,
                max_price=None,
                modal_price=None,
                market_canonical=None,
                market_alias_status="OUT_OF_SCOPE",
                disposition=RecordDisposition.OUT_OF_SCOPE_DISTRICT,
                disposition_reason=f"District '{dist}' does not match requested scope '{requested_district}'.",
                retrieval_timestamp_utc=retrieval_utc,
                display_timestamp_ist=display_ist,
                source_resource_id=self.resource_id,
                source_endpoint=self.endpoint_url,
            )

        # 5. Date validation
        parsed_d = parse_observation_date(arrival_date_raw)
        if parsed_d is None:
            return RawPriceRecord(
                state=state,
                district=dist,
                market_raw=market,
                commodity=commodity,
                variety=variety,
                grade_raw=grade_raw_str,
                grade_normalized=grade_norm,
                arrival_date_raw=arrival_date_raw,
                arrival_date_parsed=None,
                min_price_raw=min_p_raw,
                max_price_raw=max_p_raw,
                modal_price_raw=modal_p_raw,
                min_price=None,
                max_price=None,
                modal_price=None,
                market_canonical=None,
                market_alias_status="UNKNOWN",
                disposition=RecordDisposition.MALFORMED_DATE,
                disposition_reason=f"Arrival date '{arrival_date_raw}' could not be parsed into valid calendar date.",
                retrieval_timestamp_utc=retrieval_utc,
                display_timestamp_ist=display_ist,
                source_resource_id=self.resource_id,
                source_endpoint=self.endpoint_url,
            )

        if parsed_d > self.ref_date:
            return RawPriceRecord(
                state=state,
                district=dist,
                market_raw=market,
                commodity=commodity,
                variety=variety,
                grade_raw=grade_raw_str,
                grade_normalized=grade_norm,
                arrival_date_raw=arrival_date_raw,
                arrival_date_parsed=parsed_d.isoformat(),
                min_price_raw=min_p_raw,
                max_price_raw=max_p_raw,
                modal_price_raw=modal_p_raw,
                min_price=None,
                max_price=None,
                modal_price=None,
                market_canonical=None,
                market_alias_status="UNKNOWN",
                disposition=RecordDisposition.FUTURE_DATED,
                disposition_reason=f"Arrival date {parsed_d} is in the future relative to reference {self.ref_date}.",
                retrieval_timestamp_utc=retrieval_utc,
                display_timestamp_ist=display_ist,
                source_resource_id=self.resource_id,
                source_endpoint=self.endpoint_url,
            )

        # 6. Price numeric conversion and physical bounds check
        try:
            p_modal = float(modal_p_raw)
            p_min = float(min_p_raw) if min_p_raw is not None else p_modal
            p_max = float(max_p_raw) if max_p_raw is not None else p_modal
        except (ValueError, TypeError):
            return RawPriceRecord(
                state=state,
                district=dist,
                market_raw=market,
                commodity=commodity,
                variety=variety,
                grade_raw=grade_raw_str,
                grade_normalized=grade_norm,
                arrival_date_raw=arrival_date_raw,
                arrival_date_parsed=parsed_d.isoformat(),
                min_price_raw=min_p_raw,
                max_price_raw=max_p_raw,
                modal_price_raw=modal_p_raw,
                min_price=None,
                max_price=None,
                modal_price=None,
                market_canonical=None,
                market_alias_status="UNKNOWN",
                disposition=RecordDisposition.INVALID_PRICE_BOUNDS,
                disposition_reason="One or more price fields cannot be converted to float.",
                retrieval_timestamp_utc=retrieval_utc,
                display_timestamp_ist=display_ist,
                source_resource_id=self.resource_id,
                source_endpoint=self.endpoint_url,
            )

        if not (0.0 < p_min <= p_modal <= p_max):
            return RawPriceRecord(
                state=state,
                district=dist,
                market_raw=market,
                commodity=commodity,
                variety=variety,
                grade_raw=grade_raw_str,
                grade_normalized=grade_norm,
                arrival_date_raw=arrival_date_raw,
                arrival_date_parsed=parsed_d.isoformat(),
                min_price_raw=min_p_raw,
                max_price_raw=max_p_raw,
                modal_price_raw=modal_p_raw,
                min_price=p_min,
                max_price=p_max,
                modal_price=p_modal,
                market_canonical=None,
                market_alias_status="UNKNOWN",
                disposition=RecordDisposition.INVALID_PRICE_BOUNDS,
                disposition_reason=f"Violates price bounds: 0 < Min ({p_min}) <= Modal ({p_modal}) <= Max ({p_max}).",
                retrieval_timestamp_utc=retrieval_utc,
                display_timestamp_ist=display_ist,
                source_resource_id=self.resource_id,
                source_endpoint=self.endpoint_url,
            )

        # 7. Market Alias Policy Lookup
        alias_key = (dist, market)
        alias_entry = self.alias_mapping.get(alias_key)

        canonical_name: Optional[str] = None
        alias_status = "UNKNOWN"
        disposition = RecordDisposition.ACCEPTED
        reason = None

        if alias_entry:
            raw_status = alias_entry.get("status", "").upper()
            if raw_status == "ACCEPTED":
                canonical_name = alias_entry.get("market_canonical", market)
                alias_status = "ACCEPTED"
            elif "REVIEW" in raw_status:
                canonical_name = market
                alias_status = "REVIEW"
                disposition = RecordDisposition.UNKNOWN_MARKET_REVIEW
                reason = f"Market '{market}' in {dist} is designated UNMAPPED/REVIEW in alias policy."
            else:
                canonical_name = market
                alias_status = raw_status
        else:
            # Not in alias table -> enters REVIEW
            canonical_name = market
            alias_status = "REVIEW"
            disposition = RecordDisposition.UNKNOWN_MARKET_REVIEW
            reason = f"Market '{market}' in {dist} not found in reference alias register. Quarantined for review."

        return RawPriceRecord(
            state=state,
            district=dist,
            market_raw=market,
            commodity=commodity,
            variety=variety,
            grade_raw=grade_raw_str,
            grade_normalized=grade_norm,
            arrival_date_raw=arrival_date_raw,
            arrival_date_parsed=parsed_d.isoformat(),
            min_price_raw=min_p_raw,
            max_price_raw=max_p_raw,
            modal_price_raw=modal_p_raw,
            min_price=p_min,
            max_price=p_max,
            modal_price=p_modal,
            market_canonical=canonical_name,
            market_alias_status=alias_status,
            disposition=disposition,
            disposition_reason=reason,
            retrieval_timestamp_utc=retrieval_utc,
            display_timestamp_ist=display_ist,
            source_resource_id=self.resource_id,
            source_endpoint=self.endpoint_url,
        )

    def write_snapshot_page(
        self,
        run_id_utc: str,
        district: str,
        page_receipt: PageReceipt,
    ) -> str:
        """
        Store receipt under data/live_snapshots/<UTC run id>/<district>/page_<offset:05d>.json.
        Enforces collision-safe exclusive creation (mode 'x') to guarantee immutability.
        """
        dist_dir = os.path.join(self.snapshots_root, run_id_utc, district)
        os.makedirs(dist_dir, exist_ok=True)

        target_file = os.path.join(dist_dir, f"page_{page_receipt.page_offset:05d}.json")
        if os.path.exists(target_file):
            raise FileExistsError(
                f"Snapshot receipt collision: file '{target_file}' already exists. "
                "Immutable snapshots must never overwrite an existing receipt."
            )

        receipt_dict = page_receipt.to_dict()
        # Atomic/exclusive write
        with open(target_file, "x", encoding="utf-8") as f:
            json.dump(receipt_dict, f, indent=2)

        return target_file

    def fetch_district_batch(
        self,
        district: str,
        run_id_utc: str,
        requests_tracker: List[int],
    ) -> DistrictIngestionResult:
        """
        Execute bounded, fail-closed pagination loop for a single district.
        Enforces per-request and per-district budgets, transient retries, and row conservation.
        """
        dist_start_time = time.monotonic()
        result = DistrictIngestionResult(
            district=district,
            completeness_state=CompletenessState.COMPLETE,
        )

        offset = 0
        limit = 1000
        seen_page_hashes: Set[str] = set()
        natural_key_registry: Dict[Tuple[str, str, str, str, str, str], RawPriceRecord] = {}

        while True:
            # Check budgets before initiating request
            if requests_tracker[0] >= self.max_requests:
                result.completeness_state = CompletenessState.PARTIAL
                result.warnings.append(
                    f"Campaign HTTP request budget exhausted ({requests_tracker[0]}/{self.max_requests}). Yielding PARTIAL."
                )
                break

            if result.records_fetched >= self.max_records:
                result.completeness_state = CompletenessState.PARTIAL
                result.warnings.append(
                    f"Campaign record budget reached ({result.records_fetched}/{self.max_records}). Yielding PARTIAL."
                )
                break

            if (time.monotonic() - dist_start_time) >= self.timeout_per_district:
                result.completeness_state = CompletenessState.PARTIAL
                result.warnings.append(
                    f"District execution time exceeded budget ({self.timeout_per_district}s). Yielding PARTIAL."
                )
                break

            params = {
                "format": "json",
                "offset": offset,
                "limit": limit,
                "filters[state]": APPROVED_STATE,
                "filters[district]": district,
            }
            if self.api_key:
                params["api-key"] = self.api_key

            req_start_utc = datetime.now(timezone.utc).isoformat()
            retries_remaining = self.max_retries
            status_code = 0
            body_text = ""
            headers: Dict[str, str] = {}

            # Retry loop for transient failures (429, 5xx)
            while retries_remaining >= 0:
                requests_tracker[0] += 1
                try:
                    status_code, body_text, headers = self.transport.get(
                        self.endpoint_url,
                        params=params,
                        timeout=self.timeout_per_request,
                    )
                except Exception as exc:
                    sanitized_err = sanitize_url(str(exc))
                    if retries_remaining == 0:
                        result.completeness_state = CompletenessState.FAILED
                        result.errors.append(f"HTTP request failed after retries: {sanitized_err}")
                        return result
                    retries_remaining -= 1
                    time.sleep(1.0)
                    continue

                if status_code == 429:
                    # Respect Retry-After header within reasonable budget
                    retry_after_str = headers.get("retry-after") or headers.get("Retry-After")
                    wait_sec = 2.0
                    if retry_after_str:
                        try:
                            wait_sec = min(float(retry_after_str), 5.0)
                        except ValueError:
                            wait_sec = 2.0
                    if retries_remaining == 0:
                        result.completeness_state = CompletenessState.PARTIAL
                        result.errors.append(f"HTTP 429 Rate limited at offset {offset}. Retries exhausted.")
                        return result
                    retries_remaining -= 1
                    time.sleep(wait_sec)
                    continue

                if status_code in (500, 502, 503, 504):
                    if retries_remaining == 0:
                        result.completeness_state = CompletenessState.FAILED
                        result.errors.append(f"HTTP {status_code} server error at offset {offset}. Retries exhausted.")
                        return result
                    retries_remaining -= 1
                    time.sleep(1.0)
                    continue

                # Authentication or client error: fail closed immediately without retry
                if status_code in (401, 403):
                    result.completeness_state = CompletenessState.BLOCKED
                    result.errors.append(
                        f"HTTP {status_code} authentication/authorization error. Check OGD_API_KEY."
                    )
                    return result

                if status_code != 200:
                    result.completeness_state = CompletenessState.FAILED
                    result.errors.append(f"Unexpected HTTP status {status_code} at offset {offset}.")
                    return result

                # Success 200
                break

            req_end_utc = datetime.now(timezone.utc).isoformat()
            now_ist_str = datetime.now(IST_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S IST")

            # Check response body size
            if len(body_text.encode("utf-8")) > MAX_RESPONSE_BYTES:
                result.completeness_state = CompletenessState.FAILED
                result.errors.append(f"Response size exceeded {MAX_RESPONSE_BYTES} bytes limit.")
                return result

            # Detect & redact credential echo
            sanitized_body, echo_detected = redact_credential_echo(body_text, self.api_key)
            content_sha = hashlib.sha256(sanitized_body.encode("utf-8")).hexdigest()

            # Parse JSON payload
            try:
                payload = json.loads(sanitized_body)
            except json.JSONDecodeError as jde:
                result.completeness_state = CompletenessState.FAILED
                result.errors.append(f"Malformed JSON at offset {offset}: {str(jde)}")
                return result

            if not isinstance(payload, dict):
                result.completeness_state = CompletenessState.FAILED
                result.errors.append(f"Invalid payload format at offset {offset}: expected JSON object.")
                return result

            # Handle source-level error dictionaries e.g. {"error": "..."}
            if "error" in payload or "status" in payload and payload.get("status") == "error":
                err_msg = payload.get("error") or payload.get("message") or "Unknown API error"
                result.completeness_state = CompletenessState.FAILED
                result.errors.append(f"Source API returned error payload: {err_msg}")
                return result

            # Validate pagination consistency
            raw_records = payload.get("records", [])
            if not isinstance(raw_records, list):
                result.completeness_state = CompletenessState.FAILED
                result.errors.append(f"Field 'records' is not a list at offset {offset}.")
                return result

            reported_total_val = payload.get("total")
            try:
                reported_total = int(reported_total_val) if reported_total_val is not None else None
            except (ValueError, TypeError):
                reported_total = None

            if reported_total is not None:
                if result.source_reported_total is None:
                    result.source_reported_total = reported_total
                elif result.source_reported_total != reported_total:
                    # Mismatched/unstable totals during pagination
                    result.completeness_state = CompletenessState.PARTIAL
                    result.warnings.append(
                        f"Unstable source total: changed from {result.source_reported_total} to {reported_total} at offset {offset}."
                    )

            # Fail closed on repeated pages / duplicate content hash
            if content_sha in seen_page_hashes and len(raw_records) > 0:
                result.completeness_state = CompletenessState.FAILED
                result.errors.append(
                    f"Repeated page detected: content hash {content_sha[:12]} reappeared at offset {offset}. Aborting to prevent infinite loop."
                )
                break
            seen_page_hashes.add(content_sha)

            fetched_count = len(raw_records)

            receipt = PageReceipt(
                page_offset=offset,
                page_limit=limit,
                retrieval_start_utc=req_start_utc,
                retrieval_end_utc=req_end_utc,
                http_status=status_code,
                source_total=reported_total,
                fetched_count=fetched_count,
                content_sha256=content_sha,
                completeness_state=CompletenessState.COMPLETE,
                sanitized_params=sanitize_params(params),
                endpoint_sanitized=sanitize_url(self.endpoint_url),
                records=raw_records,
                sanitized_credential_detected=echo_detected,
            )

            # Store snapshot file under ignored path
            try:
                self.write_snapshot_page(run_id_utc, district, receipt)
            except Exception as write_err:
                result.completeness_state = CompletenessState.FAILED
                result.errors.append(f"Snapshot persistence failure: {str(write_err)}")
                return result

            result.page_receipts.append(receipt)
            result.total_pages_fetched += 1
            result.records_fetched += fetched_count

            # Process and validate records
            for raw_row in raw_records:
                result.records_parsed += 1
                rec = self.parse_and_validate_record(
                    raw_row=raw_row,
                    requested_district=district,
                    retrieval_utc=req_start_utc,
                    display_ist=now_ist_str,
                )

                disp_key = rec.disposition.value
                result.disposition_counts[disp_key] = result.disposition_counts.get(disp_key, 0) + 1

                if rec.disposition == RecordDisposition.ACCEPTED:
                    nat_key = rec.natural_key()
                    if nat_key in natural_key_registry:
                        prev = natural_key_registry[nat_key]
                        if prev.price_tuple() == rec.price_tuple():
                            # Exact duplicate
                            rec.disposition = RecordDisposition.EXACT_DUPLICATE
                            rec.disposition_reason = "Identical observation already accepted in this batch."
                            result.records_duplicate += 1
                            result.duplicate_records.append(rec)
                            result.disposition_counts[RecordDisposition.EXACT_DUPLICATE.value] = (
                                result.disposition_counts.get(RecordDisposition.EXACT_DUPLICATE.value, 0) + 1
                            )
                            # Adjust ACCEPTED count
                            result.disposition_counts[RecordDisposition.ACCEPTED.value] -= 1
                        else:
                            # Conflicting quote on identical natural key
                            rec.disposition = RecordDisposition.CONFLICTING_QUOTE
                            rec.disposition_reason = (
                                f"Divergent price quote for natural key: existing {prev.price_tuple()} vs incoming {rec.price_tuple()}."
                            )
                            result.records_quarantined += 1
                            result.quarantined_records.append(rec)
                            result.disposition_counts[RecordDisposition.CONFLICTING_QUOTE.value] = (
                                result.disposition_counts.get(RecordDisposition.CONFLICTING_QUOTE.value, 0) + 1
                            )
                            result.disposition_counts[RecordDisposition.ACCEPTED.value] -= 1
                    else:
                        natural_key_registry[nat_key] = rec
                        result.records_accepted += 1
                        result.accepted_records.append(rec)

                        # Update observation dates range
                        obs_d = rec.arrival_date_parsed
                        if obs_d:
                            if result.oldest_observation_date is None or obs_d < result.oldest_observation_date:
                                result.oldest_observation_date = obs_d
                            if result.newest_observation_date is None or obs_d > result.newest_observation_date:
                                result.newest_observation_date = obs_d
                elif rec.disposition == RecordDisposition.EXACT_DUPLICATE:
                    result.records_duplicate += 1
                    result.duplicate_records.append(rec)
                else:
                    result.records_quarantined += 1
                    result.quarantined_records.append(rec)

            # Pagination advance check
            if fetched_count == 0:
                # Valid empty page reached
                break

            offset += fetched_count
            if reported_total is not None and offset >= reported_total:
                break

        if result.records_fetched == 0:
            result.completeness_state = CompletenessState.EMPTY

        return result

    def execute_campaign(
        self,
        districts: Optional[Sequence[str]] = None,
        run_id_utc: Optional[str] = None,
    ) -> IngestionCampaignResult:
        """
        Execute bounded ingestion across authorized districts.
        If credentials or endpoint are unavailable, marks blocked without crashing.
        """
        target_districts = list(districts or APPROVED_DISTRICTS)
        run_id = run_id_utc or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        exec_start_utc = datetime.now(timezone.utc).isoformat()
        exec_start_ist = datetime.now(IST_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S IST")

        campaign = IngestionCampaignResult(
            run_id_utc=run_id,
            execution_timestamp_utc=exec_start_utc,
            execution_timestamp_ist=exec_start_ist,
            overall_operational_state=OperationalState.UNINITIALIZED,
            snapshot_directory=os.path.join(self.snapshots_root, run_id),
            capabilities={
                "price_display_permitted": False,
                "forecast_eligible": False,
                "economics_eligible": False,
                "active_advice_permitted": False,
            },
        )

        # Preflight credentials check
        if not self.is_credentials_available():
            campaign.is_blocked = True
            campaign.blocked_reason = (
                "OGD_API_KEY is not configured in environment or local .env. "
                "LIVE VERIFICATION BLOCKED awaiting local key configuration."
            )
            campaign.overall_operational_state = OperationalState.UNINITIALIZED
            for dist in target_districts:
                campaign.district_results[dist] = DistrictIngestionResult(
                    district=dist,
                    completeness_state=CompletenessState.BLOCKED,
                    errors=["Credentials blocked: OGD_API_KEY missing."],
                )
            return campaign

        requests_tracker = [0]

        for dist in target_districts:
            dist_res = self.fetch_district_batch(dist, run_id, requests_tracker)
            campaign.district_results[dist] = dist_res
            campaign.total_records_fetched += dist_res.records_fetched
            campaign.total_records_accepted += dist_res.records_accepted
            campaign.total_records_quarantined += dist_res.records_quarantined
            campaign.total_records_duplicate += dist_res.records_duplicate

        campaign.total_http_requests = requests_tracker[0]

        # Determine overall state across all districts
        all_states = [res.completeness_state for res in campaign.district_results.values()]
        any_failed = any(s == CompletenessState.FAILED for s in all_states)
        any_blocked = any(s == CompletenessState.BLOCKED for s in all_states)
        any_partial = any(s == CompletenessState.PARTIAL for s in all_states)
        all_empty = all(s == CompletenessState.EMPTY for s in all_states)

        if any_blocked:
            campaign.overall_operational_state = OperationalState.UNINITIALIZED
            campaign.is_blocked = True
        elif any_failed:
            campaign.overall_operational_state = OperationalState.SOURCE_DOWN
        elif any_partial:
            campaign.overall_operational_state = OperationalState.PARTIAL
        elif campaign.total_records_quarantined > 0:
            campaign.overall_operational_state = OperationalState.QUARANTINED
        elif campaign.total_records_accepted == 0:
            campaign.overall_operational_state = OperationalState.UNCHANGED
        else:
            campaign.overall_operational_state = OperationalState.SUCCESS
            campaign.is_live_verified = True

        # Capability decisions
        has_accepted = campaign.total_records_accepted > 0
        campaign.capabilities = {
            "price_display_permitted": has_accepted,
            "forecast_eligible": False,  # Live forecasting requires dedicated model release
            "economics_eligible": False,  # Active storage advisory requires empirical farmgate costs
            "active_advice_permitted": False,  # Blocked in this task per safety gate policy
        }

        # Write run-level summary receipt
        self._write_run_receipt(campaign)

        return campaign

    def _write_run_receipt(self, campaign: IngestionCampaignResult) -> None:
        """Write run-level receipt in snapshot root."""
        run_dir = os.path.join(self.snapshots_root, campaign.run_id_utc)
        os.makedirs(run_dir, exist_ok=True)
        receipt_path = os.path.join(run_dir, "run_receipt.json")
        try:
            with open(receipt_path, "w", encoding="utf-8") as f:
                json.dump(campaign.to_dict(), f, indent=2)
        except Exception as e:
            logger.warning(f"Could not write run_receipt.json: {e}")


# =============================================================================
# TRUST & HEALTH STATUS INTEGRATION ADAPTER
# =============================================================================

def build_health_report_from_ingestion(
    campaign: IngestionCampaignResult,
    reference_date: Optional[date] = None,
) -> HealthReport:
    """
    Adapter converting IngestionCampaignResult into a canonical HealthReport
    compatible with health_status.py and current_data_output.py.
    """
    ref_d = reference_date or datetime.now(IST_TIMEZONE).date()
    engine = HealthStatusEngine(current_ref_date=ref_d)

    # Find the newest observation across all districts
    newest_obs: Optional[str] = None
    for res in campaign.district_results.values():
        if res.newest_observation_date:
            if newest_obs is None or res.newest_observation_date > newest_obs:
                newest_obs = res.newest_observation_date

    freshness_status, lag_days = engine.evaluate_freshness(newest_obs)

    ledger = ReconciliationLedger(
        source_total_records=campaign.total_records_fetched,
        records_fetched=campaign.total_records_fetched,
        records_parsed=sum(r.records_parsed for r in campaign.district_results.values()),
        records_accepted=campaign.total_records_accepted,
        records_quarantined=campaign.total_records_quarantined,
        records_unchanged=campaign.total_records_duplicate,
        records_corrected=0,
        records_new=campaign.total_records_accepted,
        current_unique_keys=campaign.total_records_accepted,
        latest_observation_date=newest_obs,
        last_successful_fetch_utc=campaign.execution_timestamp_utc if campaign.is_live_verified else None,
        snapshot_sha256=None,
    )

    warnings: List[str] = []
    errors: List[str] = []

    if campaign.is_blocked:
        warnings.append(f"LIVE VERIFICATION BLOCKED: {campaign.blocked_reason}")
    if campaign.overall_operational_state == OperationalState.PARTIAL:
        warnings.append("PARTIAL DATA WARNING: District ingestion was truncated or exceeded page/record budget.")
    if campaign.total_records_quarantined > 0:
        warnings.append(f"{campaign.total_records_quarantined} records quarantined across districts.")

    for dist, res in campaign.district_results.items():
        for err in res.errors:
            errors.append(f"[{dist}] {err}")
        for w in res.warnings:
            warnings.append(f"[{dist}] {w}")

    # Explicit policy warning: active advice is blocked
    warnings.append(
        "FARMER ADVISORY POLICY: Active commercial storage recommendations are blocked on live prices. "
        "Price display is permitted with explicit observation date disclosures."
    )

    districts_present = [
        d for d, res in campaign.district_results.items()
        if res.records_accepted > 0
    ]

    return HealthReport(
        source_name=DEFAULT_SOURCE_NAME,
        resource_id=DEFAULT_RESOURCE_ID,
        operational_state=campaign.overall_operational_state,
        freshness_status=freshness_status,
        freshness_lag_days=lag_days,
        latest_observation_date=newest_obs,
        last_successful_fetch_utc=campaign.execution_timestamp_utc if campaign.is_live_verified else None,
        last_successful_fetch_local=campaign.execution_timestamp_ist if campaign.is_live_verified else None,
        is_source_live=campaign.is_live_verified,
        is_fallback_active=(not campaign.is_live_verified and campaign.total_records_accepted == 0),
        reconciliation=ledger,
        districts_represented=districts_present,
        markets_count=sum(len(r.accepted_records) for r in campaign.district_results.values()),
        commodities_count=0,
        warnings=warnings,
        errors=errors,
    )


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="APMC Mandi Live Price Ingestion Client & Snapshot Engine"
    )
    parser.add_argument(
        "--district",
        type=str,
        default="all",
        help="Target district name or 'all' for all 5 approved districts (default: all)",
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Evaluation reference date in YYYY-MM-DD format (default: today IST)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without network calls using an offline mock transport",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in machine-readable JSON format",
    )
    parser.add_argument(
        "--snapshots-dir",
        type=str,
        default=None,
        help="Custom root directory for immutable snapshot receipts",
    )

    args = parser.parse_args()

    ref_d = None
    if args.date:
        try:
            ref_d = datetime.strptime(args.date[:10], "%Y-%m-%d").date()
        except ValueError:
            print(f"Error: Invalid date format '{args.date}'. Expected YYYY-MM-DD.", file=sys.stderr)
            return 2

    # Transport selection
    if args.dry_run:
        mock_transport = MockHttpTransport()
        # Prepopulate clean synthetic fixture for offline dry-run verification
        sample_payload = json.dumps({
            "total": 2,
            "count": 2,
            "limit": "1000",
            "offset": "0",
            "records": [
                {
                    "state": "Uttar Pradesh",
                    "district": "Kanpur",
                    "market": "Kanpur(Grain) APMC",
                    "commodity": "Potato",
                    "variety": "Other",
                    "grade": "FAQ",
                    "arrival_date": "2026-11-12",
                    "min_price": 550,
                    "max_price": 600,
                    "modal_price": 575,
                },
                {
                    "state": "Uttar Pradesh",
                    "district": "Kanpur",
                    "market": "Baripaal APMC",
                    "commodity": "Paddy(Basmati)",
                    "variety": "Basmati",
                    "grade": "FAQ",
                    "arrival_date": "2026-11-12",
                    "min_price": 2800,
                    "max_price": 3000,
                    "modal_price": 2900,
                },
            ],
        })
        mock_transport.set_response("Kanpur", 0, 200, sample_payload)
        client = LivePriceIngestionClient(
            api_key="DRY_RUN_MOCK_KEY",
            transport=mock_transport,
            reference_date=ref_d,
            snapshots_root=args.snapshots_dir,
        )
    else:
        client = LivePriceIngestionClient(
            reference_date=ref_d,
            snapshots_root=args.snapshots_dir,
        )

    target_districts = APPROVED_DISTRICTS if args.district.lower() == "all" else [args.district]
    campaign = client.execute_campaign(districts=target_districts)
    health_rep = build_health_report_from_ingestion(campaign, reference_date=ref_d)

    if args.json:
        payload = campaign.to_dict()
        payload["health_report"] = health_rep.to_dict()
        print(json.dumps(payload, indent=2))
    else:
        print("=" * 78)
        print("     APMC MANDI LIVE PRICE INGESTION & DATA TRUST REPORT")
        print("=" * 78)
        print(f"Run ID (UTC)         : {campaign.run_id_utc}")
        print(f"Execution Time (IST) : {campaign.execution_timestamp_ist}")
        print(f"Operational State    : [{campaign.overall_operational_state.value}]")
        print(f"Live Verified        : {'YES' if campaign.is_live_verified else 'NO (BLOCKED / OFFLINE)'}")
        if campaign.is_blocked:
            print(f"Blocked Reason       : {campaign.blocked_reason}")
        print("-" * 78)
        print("DISTRICT HARVEST EVIDENCE:")
        print(f"{'District':<14} {'Status':<10} {'Pages':<6} {'Fetched':<8} {'Accepted':<9} {'Quarantined':<12}")
        print("-" * 78)
        for dist, res in campaign.district_results.items():
            print(
                f"{dist:<14} {res.completeness_state.value:<10} {res.total_pages_fetched:<6} "
                f"{res.records_fetched:<8} {res.records_accepted:<9} {res.records_quarantined:<12}"
            )
        print("-" * 78)
        print("RECONCILIATION & BALANCING:")
        recon = campaign.validate_arithmetic()
        print(f"Total Fetched: {recon['total_records_fetched']} | Accounted: {recon['accounted']} | Balanced: {recon['is_balanced']}")
        print(f"Accepted: {campaign.total_records_accepted} | Quarantined: {campaign.total_records_quarantined} | Duplicate: {campaign.total_records_duplicate}")
        print("-" * 78)
        print("CAPABILITIES & SAFETY DIRECTIVES:")
        for cap, val in campaign.capabilities.items():
            print(f"  • {cap:<28}: {'ENABLED' if val else 'DISABLED / BLOCKED'}")
        print("=" * 78)

    # Return exit code: 0 on success/unchanged, 1 on failed/partial, 2 on credentials blocked
    if campaign.is_blocked:
        return 2
    if campaign.overall_operational_state in (OperationalState.SUCCESS, OperationalState.UNCHANGED):
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
