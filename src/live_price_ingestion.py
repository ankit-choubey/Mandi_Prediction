"""
Live Price Ingestion Client & Snapshot Engine
APMC Mandi Market Intelligence System
Tasks: MP-SRC-004 & MP-SRC-004B (Steps 3–5)

Core Capabilities:
1. Truthful source provenance tracking via explicit DataMode:
   - LIVE_FETCH: authenticated real-network harvest via official data.gov.in API.
   - HISTORICAL_REPLAY: replay of previously captured verified snapshots.
   - TEST_FIXTURE: isolated regression test fixtures (never sets live verified flags).
   - SYNTHETIC_SIMULATION: reserved mode requiring explicit prior owner approval.
2. Standard library transport (urllib.request) with bounded chunked streaming (stops <= 10MB).
3. Secret-safe parameter/URL sanitization and body echo detection/redaction.
4. Conflict Safety: quarantines ALL members of any natural-key conflict group (order-invariant).
5. Honest price bounds: missing min/max prices are preserved as missing/quarantined;
   modal price substitution is strictly forbidden.
6. Scope enforcement: 5 authorized districts (Ghaziabad, Jhansi, Kanpur, Lucknow, Unnao).
   Kanpur Dehat subdivision ambiguity explicitly quarantined.
7. Missing grade normalized to SOURCE_NOT_PROVIDED, never silently FAQ.
8. Collision-safe immutable persistence (microsecond run IDs, exclusive 'x' writes for both
   page receipts and run receipts).
9. Atomic last_success pointer updated strictly on complete real-live campaigns.
10. Decoupled capability tracking (Price Display vs Forecasting vs Economics Advisory).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import os
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple, Union
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
import urllib.request

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

DEFAULT_LIVE_SNAPSHOTS_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "live_snapshots",
)

DEFAULT_FIXTURE_SNAPSHOTS_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "fixture_snapshots",
)

DEFAULT_FILE_IMPORT_SNAPSHOTS_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "imported_snapshots",
)

APPROVED_DISTRICTS = ("Ghaziabad", "Jhansi", "Kanpur", "Lucknow", "Unnao")
APPROVED_STATE = "Uttar Pradesh"

MAX_HTTP_REQUESTS_BUDGET = 50
MAX_RECORDS_BUDGET = 25000
MAX_IMPORT_RECORDS_BUDGET = 50000
MAX_RESPONSE_BYTES = 10 * 1024 * 1024  # 10 MB
STREAM_CHUNK_BYTES = 64 * 1024        # 64 KB
PER_REQUEST_TIMEOUT_SECONDS = 10.0
PER_DISTRICT_TIMEOUT_SECONDS = 30.0
MAX_RETRIES_PER_PAGE = 2

PUBLISHED_PRICE_UNIT = "Rs./Quintal"
GRADE_NOT_PROVIDED = "SOURCE_NOT_PROVIDED"

IST_TIMEZONE = timezone(timedelta(hours=5, minutes=30))


# =============================================================================
# ENUMS & DATA MODELS
# =============================================================================

class DataMode(str, Enum):
    LIVE_FETCH = "LIVE_FETCH"
    HISTORICAL_REPLAY = "HISTORICAL_REPLAY"
    TEST_FIXTURE = "TEST_FIXTURE"
    FILE_IMPORT = "FILE_IMPORT"
    SYNTHETIC_SIMULATION = "SYNTHETIC_SIMULATION"  # Reserved: requires prior owner approval


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
    data_mode: DataMode = DataMode.LIVE_FETCH
    is_synthetic: bool = False
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
        d["data_mode"] = self.data_mode.value
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
    data_mode: DataMode = DataMode.LIVE_FETCH
    is_synthetic: bool = False
    records: List[Dict[str, Any]] = field(default_factory=list)
    error_message: Optional[str] = None
    sanitized_credential_detected: bool = False
    source_file_path: Optional[str] = None
    source_file_sha256: Optional[str] = None
    source_file_bytes: Optional[int] = None
    source_url_declared: str = "UNKNOWN"
    retrieval_time_declared: str = "UNKNOWN"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["completeness_state"] = self.completeness_state.value
        d["data_mode"] = self.data_mode.value
        return d


@dataclass
class DistrictIngestionResult:
    district: str
    completeness_state: CompletenessState
    data_mode: DataMode = DataMode.LIVE_FETCH
    is_synthetic: bool = False
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
            "data_mode": self.data_mode.value,
            "is_synthetic": self.is_synthetic,
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
    data_mode: DataMode = DataMode.LIVE_FETCH
    is_synthetic: bool = False
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
    source_files: List[Dict[str, Any]] = field(default_factory=list)

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
            "data_mode": self.data_mode.value,
            "is_synthetic": self.is_synthetic,
            "total_http_requests": self.total_http_requests,
            "total_records_fetched": self.total_records_fetched,
            "total_records_accepted": self.total_records_accepted,
            "total_records_quarantined": self.total_records_quarantined,
            "total_records_duplicate": self.total_records_duplicate,
            "snapshot_directory": self.snapshot_directory,
            "is_live_verified": self.is_live_verified,
            "is_blocked": self.is_blocked,
            "blocked_reason": self.blocked_reason,
            "source_files": self.source_files,
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
# HTTP TRANSPORT INTERFACES & BOUNDED STREAMING
# =============================================================================

class HttpTransport:
    """Base HTTP transport interface for dependency injection."""

    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: float = PER_REQUEST_TIMEOUT_SECONDS,
        max_bytes: int = MAX_RESPONSE_BYTES,
    ) -> Tuple[int, str, Dict[str, str]]:
        raise NotImplementedError


class UrllibHttpTransport(HttpTransport):
    """
    Production-grade HTTP transport using Python standard library (urllib.request).
    Streams chunks bounded to max_bytes <= 10MB to prevent memory exhaustion.
    Strictly sanitizes error strings and URLs.
    """

    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: float = PER_REQUEST_TIMEOUT_SECONDS,
        max_bytes: int = MAX_RESPONSE_BYTES,
    ) -> Tuple[int, str, Dict[str, str]]:
        query_str = urlencode(params or {}) if params else ""
        req_url = f"{url}?{query_str}" if query_str else url
        sanitized_req_url = sanitize_url(req_url)

        req = urllib.request.Request(
            req_url,
            headers={
                "User-Agent": "MandiPriceIntelligence/1.0",
                "Accept": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                status_code = response.status
                headers = dict(response.headers)

                # Bounded streaming read
                chunks = []
                total_bytes = 0
                while True:
                    chunk = response.read(STREAM_CHUNK_BYTES)
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    if total_bytes > max_bytes:
                        raise ValueError(f"Response exceeded maximum allowed size ({max_bytes} bytes).")
                    chunks.append(chunk)

                body_bytes = b"".join(chunks)
                body_text = body_bytes.decode("utf-8", errors="replace")
                return status_code, body_text, headers

        except HTTPError as http_err:
            sanitized_err_url = sanitize_url(http_err.filename or sanitized_req_url)
            err_headers = dict(http_err.headers) if http_err.headers else {}
            # Read error body bounded
            try:
                err_body = http_err.read(min(STREAM_CHUNK_BYTES, 65536)).decode("utf-8", errors="replace")
            except Exception:
                err_body = ""
            return http_err.code, err_body, err_headers

        except URLError as url_err:
            sanitized_reason = sanitize_url(str(url_err.reason))
            raise RuntimeError(f"Network error accessing {sanitized_req_url}: {sanitized_reason}") from None
        except Exception as exc:
            sanitized_exc = sanitize_url(str(exc))
            raise RuntimeError(f"HTTP GET failed for {sanitized_req_url}: {sanitized_exc}") from None


class RequestsHttpTransport(HttpTransport):
    """Supported dependency transport using requests with bounded streaming."""

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
        max_bytes: int = MAX_RESPONSE_BYTES,
    ) -> Tuple[int, str, Dict[str, str]]:
        if self._requests is None:
            raise RuntimeError("requests library is not installed. Use UrllibHttpTransport.")

        sanitized_req_url = sanitize_url(url)
        try:
            with self._requests.get(url, params=params, timeout=timeout, stream=True) as resp:
                status_code = resp.status_code
                headers = dict(resp.headers)

                chunks = []
                total_bytes = 0
                for chunk in resp.iter_content(chunk_size=STREAM_CHUNK_BYTES):
                    if not chunk:
                        continue
                    total_bytes += len(chunk)
                    if total_bytes > max_bytes:
                        raise ValueError(f"Response exceeded maximum allowed size ({max_bytes} bytes).")
                    chunks.append(chunk)

                body_bytes = b"".join(chunks)
                body_text = body_bytes.decode(resp.encoding or "utf-8", errors="replace")
                return status_code, body_text, headers

        except Exception as exc:
            sanitized_exc_msg = sanitize_url(str(exc))
            raise RuntimeError(f"HTTP GET failed for {sanitized_req_url}: {sanitized_exc_msg}") from None


class MockHttpTransport(HttpTransport):
    """
    Mock HTTP transport for testing without network access.
    Explicitly designated for TEST_FIXTURE provenance.
    """

    def __init__(self, response_map: Optional[Dict[Tuple[str, int], Tuple[int, str, Dict[str, str]]]] = None):
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
        max_bytes: int = MAX_RESPONSE_BYTES,
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
    Client for fetching, validating, and persisting daily APMC mandi market prices.
    Enforces explicit DataMode provenance, order-invariant conflict safety, honest
    price bounds, and collision-safe immutable persistence.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        transport: Optional[HttpTransport] = None,
        data_mode: Optional[DataMode] = None,
        contract: Optional[Dict[str, Any]] = None,
        alias_mapping: Optional[Dict[Tuple[str, str], Dict[str, Any]]] = None,
        reference_date: Optional[date] = None,
        snapshots_root: Optional[str] = None,
    ):
        self.api_key = api_key or load_api_key()
        self.contract = contract or load_contract()
        self.alias_mapping = alias_mapping if alias_mapping is not None else load_alias_mapping()
        self.ref_date = reference_date or datetime.now(IST_TIMEZONE).date()

        # Determine transport & provenance mode
        if transport is not None:
            self.transport = transport
            if isinstance(transport, MockHttpTransport):
                # Mock transport defaults to TEST_FIXTURE
                self.data_mode = data_mode or DataMode.TEST_FIXTURE
                if self.data_mode == DataMode.LIVE_FETCH:
                    raise ValueError(
                        "Provenance mismatch: LIVE_FETCH mode cannot be used with MockHttpTransport."
                    )
            else:
                self.data_mode = data_mode or DataMode.LIVE_FETCH
        else:
            # Default to standard library UrllibHttpTransport for production
            self.transport = UrllibHttpTransport()
            self.data_mode = data_mode or DataMode.LIVE_FETCH

        # Namespace separation: test fixtures and file imports must never write to live snapshots root
        if snapshots_root:
            self.snapshots_root = snapshots_root
        elif self.data_mode == DataMode.TEST_FIXTURE:
            self.snapshots_root = DEFAULT_FIXTURE_SNAPSHOTS_ROOT
        elif self.data_mode == DataMode.FILE_IMPORT:
            self.snapshots_root = DEFAULT_FILE_IMPORT_SNAPSHOTS_ROOT
        else:
            self.snapshots_root = DEFAULT_LIVE_SNAPSHOTS_ROOT

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

        # Grade normalization: missing grade is explicitly SOURCE_NOT_PROVIDED, never silently FAQ
        if grade_raw is None or str(grade_raw).strip() == "":
            grade_norm = GRADE_NOT_PROVIDED
            grade_raw_str = ""
        else:
            grade_raw_str = str(grade_raw).strip()
            grade_norm = grade_raw_str

        base_kwargs = {
            "state": state,
            "district": dist,
            "market_raw": market,
            "commodity": commodity,
            "variety": variety,
            "grade_raw": grade_raw_str,
            "grade_normalized": grade_norm,
            "arrival_date_raw": arrival_date_raw,
            "min_price_raw": min_p_raw,
            "max_price_raw": max_p_raw,
            "modal_price_raw": modal_p_raw,
            "retrieval_timestamp_utc": retrieval_utc,
            "display_timestamp_ist": display_ist,
            "source_resource_id": self.resource_id,
            "source_endpoint": self.endpoint_url,
            "data_mode": self.data_mode,
            "is_synthetic": (self.data_mode == DataMode.SYNTHETIC_SIMULATION),
        }

        # 1. Required fields presence check
        if not (dist and market and commodity and arrival_date_raw and modal_p_raw is not None):
            return RawPriceRecord(
                **base_kwargs,
                arrival_date_parsed=None,
                min_price=None,
                max_price=None,
                modal_price=None,
                market_canonical=None,
                market_alias_status="UNKNOWN",
                disposition=RecordDisposition.MISSING_REQUIRED_FIELDS,
                disposition_reason="One or more mandatory fields are missing from API payload.",
            )

        # 2. Scope & Subdivision Check (Kanpur vs Kanpur Dehat)
        if dist.lower() == "kanpur dehat":
            return RawPriceRecord(
                **base_kwargs,
                arrival_date_parsed=None,
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
            )

        if dist.lower() != requested_district.lower() or dist not in APPROVED_DISTRICTS:
            return RawPriceRecord(
                **base_kwargs,
                arrival_date_parsed=None,
                min_price=None,
                max_price=None,
                modal_price=None,
                market_canonical=None,
                market_alias_status="OUT_OF_SCOPE",
                disposition=RecordDisposition.OUT_OF_SCOPE_DISTRICT,
                disposition_reason=f"District '{dist}' does not match requested scope '{requested_district}'.",
            )

        # 3. Date validation
        parsed_d = parse_observation_date(arrival_date_raw)
        if parsed_d is None:
            return RawPriceRecord(
                **base_kwargs,
                arrival_date_parsed=None,
                min_price=None,
                max_price=None,
                modal_price=None,
                market_canonical=None,
                market_alias_status="UNKNOWN",
                disposition=RecordDisposition.MALFORMED_DATE,
                disposition_reason=f"Arrival date '{arrival_date_raw}' could not be parsed into valid calendar date.",
            )

        if parsed_d > self.ref_date:
            return RawPriceRecord(
                **base_kwargs,
                arrival_date_parsed=parsed_d.isoformat(),
                min_price=None,
                max_price=None,
                modal_price=None,
                market_canonical=None,
                market_alias_status="UNKNOWN",
                disposition=RecordDisposition.FUTURE_DATED,
                disposition_reason=f"Arrival date {parsed_d} is in the future relative to reference {self.ref_date}.",
            )

        # 4. Honest Price Bounds & Required Price Check (NO MODAL SUBSTITUTION)
        # Check if min_price or max_price are missing
        if min_p_raw is None or str(min_p_raw).strip() == "" or max_p_raw is None or str(max_p_raw).strip() == "":
            return RawPriceRecord(
                **base_kwargs,
                arrival_date_parsed=parsed_d.isoformat(),
                min_price=None,
                max_price=None,
                modal_price=None,
                market_canonical=None,
                market_alias_status="UNKNOWN",
                disposition=RecordDisposition.MISSING_REQUIRED_FIELDS,
                disposition_reason="Mandatory price bounds (min_price or max_price) missing. Modal substitution is strictly forbidden.",
            )

        try:
            p_modal = float(modal_p_raw)
            p_min = float(min_p_raw)
            p_max = float(max_p_raw)
        except (ValueError, TypeError):
            return RawPriceRecord(
                **base_kwargs,
                arrival_date_parsed=parsed_d.isoformat(),
                min_price=None,
                max_price=None,
                modal_price=None,
                market_canonical=None,
                market_alias_status="UNKNOWN",
                disposition=RecordDisposition.INVALID_PRICE_BOUNDS,
                disposition_reason="One or more price fields cannot be converted to float.",
            )

        # Non-finite or non-positive check
        for p_val in (p_min, p_modal, p_max):
            if math.isnan(p_val) or math.isinf(p_val) or p_val <= 0.0:
                return RawPriceRecord(
                    **base_kwargs,
                    arrival_date_parsed=parsed_d.isoformat(),
                    min_price=p_min if not (math.isnan(p_min) or math.isinf(p_min)) else None,
                    max_price=p_max if not (math.isnan(p_max) or math.isinf(p_max)) else None,
                    modal_price=p_modal if not (math.isnan(p_modal) or math.isinf(p_modal)) else None,
                    market_canonical=None,
                    market_alias_status="UNKNOWN",
                    disposition=RecordDisposition.INVALID_PRICE_BOUNDS,
                    disposition_reason=f"Prices must be positive finite floats; received ({p_min}, {p_modal}, {p_max}).",
                )

        if not (0.0 < p_min <= p_modal <= p_max):
            return RawPriceRecord(
                **base_kwargs,
                arrival_date_parsed=parsed_d.isoformat(),
                min_price=p_min,
                max_price=p_max,
                modal_price=p_modal,
                market_canonical=None,
                market_alias_status="UNKNOWN",
                disposition=RecordDisposition.INVALID_PRICE_BOUNDS,
                disposition_reason=f"Violates price bounds: 0 < Min ({p_min}) <= Modal ({p_modal}) <= Max ({p_max}).",
            )

        # 5. Market Alias Policy Lookup
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
            canonical_name = market
            alias_status = "REVIEW"
            disposition = RecordDisposition.UNKNOWN_MARKET_REVIEW
            reason = f"Market '{market}' in {dist} not found in reference alias register. Quarantined for review."

        return RawPriceRecord(
            **base_kwargs,
            arrival_date_parsed=parsed_d.isoformat(),
            min_price=p_min,
            max_price=p_max,
            modal_price=p_modal,
            market_canonical=canonical_name,
            market_alias_status=alias_status,
            disposition=disposition,
            disposition_reason=reason,
        )

    def write_snapshot_page(
        self,
        run_id_utc: str,
        district: str,
        page_receipt: PageReceipt,
    ) -> str:
        """
        Store receipt under <snapshots_root>/<run_id_utc>/<district>/page_<offset:05d>.json.
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
        with open(target_file, "x", encoding="utf-8") as f:
            json.dump(receipt_dict, f, indent=2)

        return target_file

    def _recompute_date_range(self, accepted_records: List[RawPriceRecord]) -> Tuple[Optional[str], Optional[str]]:
        """Recompute oldest and newest observation date strictly from current accepted records."""
        if not accepted_records:
            return None, None
        dates = [r.arrival_date_parsed for r in accepted_records if r.arrival_date_parsed]
        if not dates:
            return None, None
        return min(dates), max(dates)

    def fetch_district_batch(
        self,
        district: str,
        run_id_utc: str,
        requests_tracker: List[int],
    ) -> DistrictIngestionResult:
        """
        Execute bounded pagination loop for a single district.
        Enforces order-invariant conflict resolution: when prices diverge for any natural key,
        ALL records for that natural key are quarantined.
        """
        dist_start_time = time.monotonic()
        result = DistrictIngestionResult(
            district=district,
            completeness_state=CompletenessState.COMPLETE,
            data_mode=self.data_mode,
            is_synthetic=(self.data_mode == DataMode.SYNTHETIC_SIMULATION),
        )

        offset = 0
        limit = 1000
        seen_page_hashes: Set[str] = set()

        # Natural key registries for order-invariant conflict safety
        accepted_registry: Dict[Tuple[str, str, str, str, str, str], List[RawPriceRecord]] = {}
        conflicted_keys: Set[Tuple[str, str, str, str, str, str]] = set()

        while True:
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

            while retries_remaining >= 0:
                requests_tracker[0] += 1
                try:
                    status_code, body_text, headers = self.transport.get(
                        self.endpoint_url,
                        params=params,
                        timeout=self.timeout_per_request,
                        max_bytes=MAX_RESPONSE_BYTES,
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

                break

            req_end_utc = datetime.now(timezone.utc).isoformat()
            now_ist_str = datetime.now(IST_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S IST")

            sanitized_body, echo_detected = redact_credential_echo(body_text, self.api_key)
            content_sha = hashlib.sha256(sanitized_body.encode("utf-8")).hexdigest()

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

            if "error" in payload or "status" in payload and payload.get("status") == "error":
                err_msg = payload.get("error") or payload.get("message") or "Unknown API error"
                result.completeness_state = CompletenessState.FAILED
                result.errors.append(f"Source API returned error payload: {err_msg}")
                return result

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
                    result.completeness_state = CompletenessState.PARTIAL
                    result.warnings.append(
                        f"Unstable source total: changed from {result.source_reported_total} to {reported_total} at offset {offset}."
                    )

            if content_sha in seen_page_hashes and len(raw_records) > 0:
                result.completeness_state = CompletenessState.FAILED
                result.errors.append(
                    f"Repeated page detected: content hash {content_sha[:12]} reappeared at offset {offset}. Aborting."
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
                data_mode=self.data_mode,
                is_synthetic=(self.data_mode == DataMode.SYNTHETIC_SIMULATION),
                records=raw_records,
                sanitized_credential_detected=echo_detected,
            )

            try:
                self.write_snapshot_page(run_id_utc, district, receipt)
            except Exception as write_err:
                result.completeness_state = CompletenessState.FAILED
                result.errors.append(f"Snapshot persistence failure: {str(write_err)}")
                return result

            result.page_receipts.append(receipt)
            result.total_pages_fetched += 1
            result.records_fetched += fetched_count

            # Process and validate records with Order-Invariant Conflict Safety
            for raw_row in raw_records:
                result.records_parsed += 1
                rec = self.parse_and_validate_record(
                    raw_row=raw_row,
                    requested_district=district,
                    retrieval_utc=req_start_utc,
                    display_ist=now_ist_str,
                )

                if rec.disposition == RecordDisposition.ACCEPTED:
                    nat_key = rec.natural_key()

                    if nat_key in conflicted_keys:
                        # Key was already identified as conflicted: quarantine incoming record immediately
                        rec.disposition = RecordDisposition.CONFLICTING_QUOTE
                        rec.disposition_reason = "Unresolved divergent prices observed for this natural key in batch."
                        result.records_quarantined += 1
                        result.quarantined_records.append(rec)
                        result.disposition_counts[RecordDisposition.CONFLICTING_QUOTE.value] = (
                            result.disposition_counts.get(RecordDisposition.CONFLICTING_QUOTE.value, 0) + 1
                        )

                    elif nat_key in accepted_registry:
                        prev_list = accepted_registry[nat_key]
                        anchor_rec = prev_list[0]

                        if anchor_rec.price_tuple() == rec.price_tuple():
                            # Exact duplicate of accepted record
                            rec.disposition = RecordDisposition.EXACT_DUPLICATE
                            rec.disposition_reason = "Identical observation already accepted in this batch."
                            result.records_duplicate += 1
                            result.duplicate_records.append(rec)
                            result.disposition_counts[RecordDisposition.EXACT_DUPLICATE.value] = (
                                result.disposition_counts.get(RecordDisposition.EXACT_DUPLICATE.value, 0) + 1
                            )
                            prev_list.append(rec)

                        else:
                            # DIVERGENT PRICES DETECTED: Quarantine ALL records for this key
                            conflicted_keys.add(nat_key)

                            # 1. Quarantine incoming record
                            rec.disposition = RecordDisposition.CONFLICTING_QUOTE
                            rec.disposition_reason = (
                                f"Divergent price quote for natural key: existing {anchor_rec.price_tuple()} vs incoming {rec.price_tuple()}."
                            )
                            result.records_quarantined += 1
                            result.quarantined_records.append(rec)
                            result.disposition_counts[RecordDisposition.CONFLICTING_QUOTE.value] = (
                                result.disposition_counts.get(RecordDisposition.CONFLICTING_QUOTE.value, 0) + 1
                            )

                            # 2. Retroactively quarantine ALL previously accepted / duplicate records for this key
                            for prev_rec in prev_list:
                                if prev_rec in result.accepted_records:
                                    result.accepted_records.remove(prev_rec)
                                    result.records_accepted -= 1
                                    result.disposition_counts[RecordDisposition.ACCEPTED.value] -= 1
                                elif prev_rec in result.duplicate_records:
                                    result.duplicate_records.remove(prev_rec)
                                    result.records_duplicate -= 1
                                    result.disposition_counts[RecordDisposition.EXACT_DUPLICATE.value] -= 1

                                prev_rec.disposition = RecordDisposition.CONFLICTING_QUOTE
                                prev_rec.disposition_reason = (
                                    f"Retroactively quarantined: conflicting price quote {rec.price_tuple()} appeared in batch."
                                )
                                result.records_quarantined += 1
                                result.quarantined_records.append(prev_rec)
                                result.disposition_counts[RecordDisposition.CONFLICTING_QUOTE.value] = (
                                    result.disposition_counts.get(RecordDisposition.CONFLICTING_QUOTE.value, 0) + 1
                                )

                            del accepted_registry[nat_key]

                    else:
                        # First observation for this key: provisionally accept
                        accepted_registry[nat_key] = [rec]
                        result.records_accepted += 1
                        result.accepted_records.append(rec)
                        result.disposition_counts[RecordDisposition.ACCEPTED.value] = (
                            result.disposition_counts.get(RecordDisposition.ACCEPTED.value, 0) + 1
                        )

                elif rec.disposition == RecordDisposition.EXACT_DUPLICATE:
                    result.records_duplicate += 1
                    result.duplicate_records.append(rec)
                    disp_key = rec.disposition.value
                    result.disposition_counts[disp_key] = result.disposition_counts.get(disp_key, 0) + 1
                else:
                    result.records_quarantined += 1
                    result.quarantined_records.append(rec)
                    disp_key = rec.disposition.value
                    result.disposition_counts[disp_key] = result.disposition_counts.get(disp_key, 0) + 1

            if fetched_count == 0:
                break

            offset += fetched_count
            if reported_total is not None and offset >= reported_total:
                break

        # Recompute honest observation date range strictly from remaining accepted records
        old_d, new_d = self._recompute_date_range(result.accepted_records)
        result.oldest_observation_date = old_d
        result.newest_observation_date = new_d

        if result.records_fetched == 0:
            result.completeness_state = CompletenessState.EMPTY

        return result

    def execute_campaign(
        self,
        districts: Optional[Sequence[str]] = None,
        run_id_utc: Optional[str] = None,
    ) -> IngestionCampaignResult:
        """
        Execute bounded ingestion campaign.
        Enforces strict provenance: only real network runs on LIVE_FETCH mode can set
        is_live_verified=True or advance the persistent last_success pointer.
        """
        target_districts = list(districts or APPROVED_DISTRICTS)
        # Microsecond timestamp ensures collision safety across rapid executions
        run_id = run_id_utc or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
        exec_start_utc = datetime.now(timezone.utc).isoformat()
        exec_start_ist = datetime.now(IST_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S IST")

        campaign = IngestionCampaignResult(
            run_id_utc=run_id,
            execution_timestamp_utc=exec_start_utc,
            execution_timestamp_ist=exec_start_ist,
            overall_operational_state=OperationalState.UNINITIALIZED,
            data_mode=self.data_mode,
            is_synthetic=(self.data_mode == DataMode.SYNTHETIC_SIMULATION),
            snapshot_directory=os.path.join(self.snapshots_root, run_id),
            capabilities={
                "price_display_permitted": False,
                "forecast_eligible": False,
                "economics_eligible": False,
                "active_advice_permitted": False,
                "data_mode": self.data_mode.value,
                "is_synthetic": (self.data_mode == DataMode.SYNTHETIC_SIMULATION),
            },
        )

        # Preflight credentials check for LIVE_FETCH mode
        if self.data_mode == DataMode.LIVE_FETCH and not self.is_credentials_available():
            campaign.is_blocked = True
            campaign.blocked_reason = (
                "KEY_MISSING: OGD_API_KEY is not configured in environment or local .env. "
                "LIVE VERIFICATION BLOCKED awaiting local key configuration."
            )
            campaign.overall_operational_state = OperationalState.UNINITIALIZED
            for dist in target_districts:
                campaign.district_results[dist] = DistrictIngestionResult(
                    district=dist,
                    completeness_state=CompletenessState.BLOCKED,
                    data_mode=self.data_mode,
                    errors=["Credentials blocked: OGD_API_KEY missing."],
                )
            self._write_run_receipt(campaign)
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

        # CRITICAL PROVENANCE RULE: Only real LIVE_FETCH runs can set is_live_verified=True
        if self.data_mode == DataMode.LIVE_FETCH and campaign.overall_operational_state in (
            OperationalState.SUCCESS, OperationalState.UNCHANGED
        ):
            campaign.is_live_verified = True
        else:
            campaign.is_live_verified = False

        # Capabilities
        has_accepted = campaign.total_records_accepted > 0
        campaign.capabilities = {
            "price_display_permitted": has_accepted,
            "forecast_eligible": False,  # Blocked until approved model release
            "economics_eligible": False,  # Blocked until empirical cost quotes verified
            "active_advice_permitted": False,  # Blocked per safety gate policy
            "data_mode": self.data_mode.value,
            "is_synthetic": (self.data_mode == DataMode.SYNTHETIC_SIMULATION),
            "is_live_verified": campaign.is_live_verified,
        }

        # Persist run receipt exclusively
        self._write_run_receipt(campaign)

        # Update persistent last_success pointer ONLY on complete real LIVE_FETCH success
        if campaign.is_live_verified:
            self._update_last_success_pointer(campaign)

        return campaign

    def execute_file_import(
        self,
        file_path: Union[str, Sequence[str]],
        district: Optional[str] = None,
        run_id_utc: Optional[str] = None,
        source_url: str = "UNKNOWN",
        retrieval_timestamp_utc: str = "UNKNOWN",
    ) -> IngestionCampaignResult:
        """
        Execute deterministic dataset file import from local CSV/Excel APMC file(s).
        Enforces:
        - <= 10MB per file and <= 50,000 rows limit
        - Explicit FILE_IMPORT provenance (is_live_verified=False, never advances live-success index)
        - Order-invariant conflict resolution (all divergent quotes quarantined)
        - Honest price bounds (missing min/max preserved/quarantined, NO modal substitution)
        - Collision-safe immutable snapshot storage and exclusive run receipt writing
        """
        import csv

        if isinstance(file_path, (str, bytes, os.PathLike)):
            file_paths = [str(file_path)]
        else:
            file_paths = [str(p) for p in file_path]

        run_id = run_id_utc or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
        exec_start_utc = datetime.now(timezone.utc).isoformat()
        exec_start_ist = datetime.now(IST_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S IST")

        campaign = IngestionCampaignResult(
            run_id_utc=run_id,
            execution_timestamp_utc=exec_start_utc,
            execution_timestamp_ist=exec_start_ist,
            overall_operational_state=OperationalState.UNINITIALIZED,
            data_mode=DataMode.FILE_IMPORT,
            is_synthetic=False,
            snapshot_directory=os.path.join(self.snapshots_root, run_id),
            capabilities={
                "price_display_permitted": False,
                "forecast_eligible": False,
                "economics_eligible": False,
                "active_advice_permitted": False,
                "data_mode": DataMode.FILE_IMPORT.value,
                "is_synthetic": False,
                "is_live_verified": False,
                "is_import_verified": True,
            },
        )

        all_file_metadata = []
        raw_rows_by_district: Dict[str, List[Tuple[Dict[str, Any], str, str, int]]] = {}

        for f_path in file_paths:
            if not os.path.exists(f_path):
                raise FileNotFoundError(f"Import file not found: {f_path}")

            file_bytes = os.path.getsize(f_path)
            if file_bytes > MAX_RESPONSE_BYTES:
                raise ValueError(
                    f"File '{os.path.basename(f_path)}' size ({file_bytes} bytes) exceeds "
                    f"maximum allowed local processing limit ({MAX_RESPONSE_BYTES} bytes = 10MB)."
                )

            with open(f_path, "rb") as bf:
                file_sha = hashlib.sha256(bf.read()).hexdigest()

            file_meta = {
                "file_path": f_path,
                "file_name": os.path.basename(f_path),
                "file_bytes": file_bytes,
                "file_sha256": file_sha,
                "source_url_declared": source_url,
                "retrieval_timestamp_declared": retrieval_timestamp_utc,
            }
            all_file_metadata.append(file_meta)

            row_count = 0
            with open(f_path, "r", encoding="utf-8", errors="replace") as cf:
                reader = csv.DictReader(cf)
                for row in reader:
                    row_count += 1
                    if row_count > MAX_IMPORT_RECORDS_BUDGET:
                        raise ValueError(
                            f"File '{os.path.basename(f_path)}' row count exceeds maximum allowed "
                            f"local processing limit ({MAX_IMPORT_RECORDS_BUDGET} rows = 50,000)."
                        )
                    d_val = str(extract_field(row, ["district", "District"]) or "").strip()
                    if district and district.lower() != "all" and d_val.lower() != district.lower():
                        continue
                    raw_rows_by_district.setdefault(d_val, []).append((row, f_path, file_sha, file_bytes))

        campaign.source_files = all_file_metadata

        if not raw_rows_by_district:
            campaign.overall_operational_state = OperationalState.EMPTY
            self._write_run_receipt(campaign)
            return campaign

        for dist_name, row_tuples in raw_rows_by_district.items():
            dist_res = DistrictIngestionResult(
                district=dist_name,
                completeness_state=CompletenessState.COMPLETE,
                data_mode=DataMode.FILE_IMPORT,
                is_synthetic=False,
            )

            accepted_registry: Dict[Tuple[str, str, str, str, str, str], List[RawPriceRecord]] = {}
            conflicted_keys: Set[Tuple[str, str, str, str, str, str]] = set()
            raw_records_for_receipt: List[Dict[str, Any]] = []

            for raw_row, src_file, src_sha, src_bytes in row_tuples:
                dist_res.records_fetched += 1
                dist_res.records_parsed += 1
                raw_records_for_receipt.append(raw_row)

                rec = self.parse_and_validate_record(
                    raw_row=raw_row,
                    requested_district=dist_name,
                    retrieval_utc=retrieval_timestamp_utc,
                    display_ist="UNKNOWN",
                )
                rec.data_mode = DataMode.FILE_IMPORT
                rec.is_synthetic = False

                if rec.disposition == RecordDisposition.ACCEPTED:
                    nat_key = rec.natural_key()

                    if nat_key in conflicted_keys:
                        rec.disposition = RecordDisposition.CONFLICTING_QUOTE
                        rec.disposition_reason = "Unresolved divergent prices observed for this natural key in imported dataset."
                        dist_res.records_quarantined += 1
                        dist_res.quarantined_records.append(rec)
                        dist_res.disposition_counts[RecordDisposition.CONFLICTING_QUOTE.value] = (
                            dist_res.disposition_counts.get(RecordDisposition.CONFLICTING_QUOTE.value, 0) + 1
                        )
                    elif nat_key in accepted_registry:
                        prev_list = accepted_registry[nat_key]
                        anchor_rec = prev_list[0]

                        if anchor_rec.price_tuple() == rec.price_tuple():
                            rec.disposition = RecordDisposition.EXACT_DUPLICATE
                            rec.disposition_reason = "Identical observation already accepted in this dataset import."
                            dist_res.records_duplicate += 1
                            dist_res.duplicate_records.append(rec)
                            dist_res.disposition_counts[RecordDisposition.EXACT_DUPLICATE.value] = (
                                dist_res.disposition_counts.get(RecordDisposition.EXACT_DUPLICATE.value, 0) + 1
                            )
                            prev_list.append(rec)
                        else:
                            conflicted_keys.add(nat_key)
                            rec.disposition = RecordDisposition.CONFLICTING_QUOTE
                            rec.disposition_reason = (
                                f"Divergent price quote for natural key: existing {anchor_rec.price_tuple()} vs incoming {rec.price_tuple()}."
                            )
                            dist_res.records_quarantined += 1
                            dist_res.quarantined_records.append(rec)
                            dist_res.disposition_counts[RecordDisposition.CONFLICTING_QUOTE.value] = (
                                dist_res.disposition_counts.get(RecordDisposition.CONFLICTING_QUOTE.value, 0) + 1
                            )

                            for prev_rec in prev_list:
                                if prev_rec in dist_res.accepted_records:
                                    dist_res.accepted_records.remove(prev_rec)
                                    dist_res.records_accepted -= 1
                                    dist_res.disposition_counts[RecordDisposition.ACCEPTED.value] -= 1
                                elif prev_rec in dist_res.duplicate_records:
                                    dist_res.duplicate_records.remove(prev_rec)
                                    dist_res.records_duplicate -= 1
                                    dist_res.disposition_counts[RecordDisposition.EXACT_DUPLICATE.value] -= 1

                                prev_rec.disposition = RecordDisposition.CONFLICTING_QUOTE
                                prev_rec.disposition_reason = (
                                    f"Retroactively quarantined: conflicting price quote {rec.price_tuple()} appeared in imported file."
                                )
                                dist_res.records_quarantined += 1
                                dist_res.quarantined_records.append(prev_rec)
                                dist_res.disposition_counts[RecordDisposition.CONFLICTING_QUOTE.value] = (
                                    dist_res.disposition_counts.get(RecordDisposition.CONFLICTING_QUOTE.value, 0) + 1
                                )

                            del accepted_registry[nat_key]
                    else:
                        accepted_registry[nat_key] = [rec]
                        dist_res.records_accepted += 1
                        dist_res.accepted_records.append(rec)
                        dist_res.disposition_counts[RecordDisposition.ACCEPTED.value] = (
                            dist_res.disposition_counts.get(RecordDisposition.ACCEPTED.value, 0) + 1
                        )
                elif rec.disposition == RecordDisposition.EXACT_DUPLICATE:
                    dist_res.records_duplicate += 1
                    dist_res.duplicate_records.append(rec)
                    disp_key = rec.disposition.value
                    dist_res.disposition_counts[disp_key] = dist_res.disposition_counts.get(disp_key, 0) + 1
                else:
                    dist_res.records_quarantined += 1
                    dist_res.quarantined_records.append(rec)
                    disp_key = rec.disposition.value
                    dist_res.disposition_counts[disp_key] = dist_res.disposition_counts.get(disp_key, 0) + 1

            old_d, new_d = self._recompute_date_range(dist_res.accepted_records)
            dist_res.oldest_observation_date = old_d
            dist_res.newest_observation_date = new_d
            if dist_res.records_fetched == 0:
                dist_res.completeness_state = CompletenessState.EMPTY

            primary_file_sha = all_file_metadata[0]["file_sha256"] if all_file_metadata else ""
            primary_file_path = all_file_metadata[0]["file_path"] if all_file_metadata else ""
            primary_file_bytes = all_file_metadata[0]["file_bytes"] if all_file_metadata else 0

            receipt = PageReceipt(
                page_offset=0,
                page_limit=dist_res.records_fetched,
                retrieval_start_utc=exec_start_utc,
                retrieval_end_utc=exec_start_utc,
                http_status=200,
                source_total=dist_res.records_fetched,
                fetched_count=dist_res.records_fetched,
                content_sha256=primary_file_sha,
                completeness_state=dist_res.completeness_state,
                sanitized_params={"import_source": primary_file_path, "district": dist_name},
                endpoint_sanitized=f"file://{primary_file_path}",
                data_mode=DataMode.FILE_IMPORT,
                is_synthetic=False,
                records=raw_records_for_receipt,
                source_file_path=primary_file_path,
                source_file_sha256=primary_file_sha,
                source_file_bytes=primary_file_bytes,
                source_url_declared=source_url,
                retrieval_time_declared=retrieval_timestamp_utc,
            )
            self.write_snapshot_page(run_id, dist_name, receipt)
            dist_res.page_receipts.append(receipt)
            dist_res.total_pages_fetched = 1

            campaign.district_results[dist_name] = dist_res
            campaign.total_records_fetched += dist_res.records_fetched
            campaign.total_records_accepted += dist_res.records_accepted
            campaign.total_records_quarantined += dist_res.records_quarantined
            campaign.total_records_duplicate += dist_res.records_duplicate

        if campaign.total_records_quarantined > 0:
            campaign.overall_operational_state = OperationalState.QUARANTINED
        elif campaign.total_records_accepted == 0:
            campaign.overall_operational_state = OperationalState.EMPTY
        else:
            campaign.overall_operational_state = OperationalState.SUCCESS

        campaign.is_live_verified = False
        has_accepted = campaign.total_records_accepted > 0
        campaign.capabilities = {
            "price_display_permitted": has_accepted,
            "forecast_eligible": False,
            "economics_eligible": False,
            "active_advice_permitted": False,
            "data_mode": DataMode.FILE_IMPORT.value,
            "is_synthetic": False,
            "is_live_verified": False,
            "is_import_verified": True,
        }

        self._write_run_receipt(campaign)
        return campaign

    def _write_run_receipt(self, campaign: IngestionCampaignResult) -> None:
        """Write run-level receipt in snapshot root with exclusive creation."""
        run_dir = os.path.join(self.snapshots_root, campaign.run_id_utc)
        os.makedirs(run_dir, exist_ok=True)
        receipt_path = os.path.join(run_dir, "run_receipt.json")
        try:
            with open(receipt_path, "x", encoding="utf-8") as f:
                json.dump(campaign.to_dict(), f, indent=2)
        except FileExistsError:
            raise FileExistsError(f"Run receipt collision: '{receipt_path}' already exists.")

    def _update_last_success_pointer(self, campaign: IngestionCampaignResult) -> None:
        """
        Atomically persist pointer to last successful live campaign.
        Strictly called ONLY when campaign.is_live_verified is True.
        """
        pointer_path = os.path.join(self.snapshots_root, "last_successful_campaign.json")
        payload = {
            "run_id_utc": campaign.run_id_utc,
            "execution_timestamp_utc": campaign.execution_timestamp_utc,
            "execution_timestamp_ist": campaign.execution_timestamp_ist,
            "total_records_accepted": campaign.total_records_accepted,
            "districts": list(campaign.district_results.keys()),
            "receipt_path": os.path.join(campaign.run_id_utc, "run_receipt.json"),
        }
        temp_path = f"{pointer_path}.tmp_{os.getpid()}"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        os.replace(temp_path, pointer_path)


# =============================================================================
# PERSISTENT FALLBACK & SNAPSHOT LOADERS
# =============================================================================

def load_prior_validated_snapshot(
    snapshots_root: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Load prior validated successful snapshot as labeled fallback.
    Preserves original trade and retrieval timestamps.
    Returns None if no validated snapshot exists.
    """
    root = snapshots_root or DEFAULT_LIVE_SNAPSHOTS_ROOT
    pointer_path = os.path.join(root, "last_successful_campaign.json")
    if not os.path.exists(pointer_path):
        return None

    try:
        with open(pointer_path, "r", encoding="utf-8") as f:
            pointer = json.load(f)
        rel_receipt = pointer.get("receipt_path")
        if not rel_receipt:
            return None
        full_receipt_path = os.path.join(root, rel_receipt)
        if not os.path.exists(full_receipt_path):
            return None
        with open(full_receipt_path, "r", encoding="utf-8") as f:
            campaign_data = json.load(f)
        return campaign_data
    except Exception:
        return None


# =============================================================================
# TRUST & HEALTH STATUS INTEGRATION ADAPTER
# =============================================================================

def build_health_report_from_ingestion(
    campaign: IngestionCampaignResult,
    reference_date: Optional[date] = None,
    prior_validated_snapshot: Optional[Dict[str, Any]] = None,
) -> HealthReport:
    """
    Adapter converting IngestionCampaignResult into a canonical HealthReport.
    Enforces honest data_mode, provenance labels, and fallback provenance.
    """
    ref_d = reference_date or datetime.now(IST_TIMEZONE).date()
    engine = HealthStatusEngine(current_ref_date=ref_d)

    newest_obs: Optional[str] = None
    for res in campaign.district_results.values():
        if res.newest_observation_date:
            if newest_obs is None or res.newest_observation_date > newest_obs:
                newest_obs = res.newest_observation_date

    # If current run is blocked/failed but prior snapshot exists, use fallback metadata
    is_fallback = False
    fetch_utc = None
    fetch_local = None

    if campaign.is_live_verified:
        fetch_utc = campaign.execution_timestamp_utc
        fetch_local = campaign.execution_timestamp_ist
    elif prior_validated_snapshot:
        is_fallback = True
        fetch_utc = prior_validated_snapshot.get("execution_timestamp_utc")
        fetch_local = prior_validated_snapshot.get("execution_timestamp_ist")
        # If no new observations, use prior newest observation
        if not newest_obs:
            for dist_info in prior_validated_snapshot.get("district_results", {}).values():
                d_obs = dist_info.get("newest_observation_date")
                if d_obs and (newest_obs is None or d_obs > newest_obs):
                    newest_obs = d_obs

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
        last_successful_fetch_utc=fetch_utc,
        snapshot_sha256=None,
    )

    warnings: List[str] = []
    errors: List[str] = []

    if campaign.data_mode == DataMode.TEST_FIXTURE:
        warnings.append("PROVENANCE: TEST_FIXTURE run using offline fixtures; NOT a live verified market data feed.")
    elif campaign.data_mode == DataMode.HISTORICAL_REPLAY:
        warnings.append("PROVENANCE: HISTORICAL_REPLAY using preserved past observations.")
    elif campaign.data_mode == DataMode.FILE_IMPORT:
        warnings.append("PROVENANCE: FILE_IMPORT from local APMC dataset archive; NOT an active live network feed.")

    if campaign.is_blocked:
        warnings.append(f"{campaign.blocked_reason}")
    if campaign.overall_operational_state == OperationalState.PARTIAL:
        warnings.append("PARTIAL DATA WARNING: District ingestion was truncated or exceeded budget.")
    if campaign.total_records_quarantined > 0:
        warnings.append(f"{campaign.total_records_quarantined} records quarantined across districts.")

    if is_fallback:
        warnings.append("FALLBACK ACTIVE: Report generated from prior validated offline snapshot.")

    for dist, res in campaign.district_results.items():
        for err in res.errors:
            errors.append(f"[{dist}] {err}")
        for w in res.warnings:
            warnings.append(f"[{dist}] {w}")

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
        last_successful_fetch_utc=fetch_utc,
        last_successful_fetch_local=fetch_local,
        is_source_live=campaign.is_live_verified,
        is_fallback_active=is_fallback,
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
        help="Run offline using existing test fixtures (never sets live verified)",
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
    parser.add_argument(
        "--import-file",
        type=str,
        default=None,
        help="Path to local APMC CSV/Excel file to ingest under FILE_IMPORT provenance",
    )
    parser.add_argument(
        "--source-url",
        type=str,
        default="UNKNOWN",
        help="Declared original source download URL if known (default: UNKNOWN)",
    )
    parser.add_argument(
        "--retrieval-time",
        type=str,
        default="UNKNOWN",
        help="Declared original retrieval timestamp UTC if known (default: UNKNOWN)",
    )

    args = parser.parse_args()

    ref_d = None
    if args.date:
        try:
            ref_d = datetime.strptime(args.date[:10], "%Y-%m-%d").date()
        except ValueError:
            print(f"Error: Invalid date format '{args.date}'. Expected YYYY-MM-DD.", file=sys.stderr)
            return 2

    if args.import_file:
        client = LivePriceIngestionClient(
            data_mode=DataMode.FILE_IMPORT,
            reference_date=ref_d,
            snapshots_root=args.snapshots_dir or DEFAULT_FILE_IMPORT_SNAPSHOTS_ROOT,
        )
        target_dist = None if args.district.lower() == "all" else args.district
        campaign = client.execute_file_import(
            file_path=args.import_file,
            district=target_dist,
            source_url=args.source_url,
            retrieval_timestamp_utc=args.retrieval_time,
        )
    else:
        if args.dry_run:
            # Dry-run uses TEST_FIXTURE data mode and distinct test namespace
            mock_transport = MockHttpTransport()
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
                api_key="TEST_FIXTURE_KEY",
                transport=mock_transport,
                data_mode=DataMode.TEST_FIXTURE,
                reference_date=ref_d,
                snapshots_root=args.snapshots_dir or DEFAULT_FIXTURE_SNAPSHOTS_ROOT,
            )
        else:
            client = LivePriceIngestionClient(
                reference_date=ref_d,
                snapshots_root=args.snapshots_dir or DEFAULT_LIVE_SNAPSHOTS_ROOT,
            )

        target_districts = APPROVED_DISTRICTS if args.district.lower() == "all" else [args.district]
        campaign = client.execute_campaign(districts=target_districts)

    # Check for prior validated fallback if live run failed/blocked
    prior_snapshot = None
    if not campaign.is_live_verified:
        prior_snapshot = load_prior_validated_snapshot(snapshots_root=client.snapshots_root)

    health_rep = build_health_report_from_ingestion(
        campaign,
        reference_date=ref_d,
        prior_validated_snapshot=prior_snapshot,
    )

    if args.json:
        payload = campaign.to_dict()
        payload["health_report"] = health_rep.to_dict()
        print(json.dumps(payload, indent=2))
    else:
        print("=" * 78)
        if campaign.data_mode == DataMode.TEST_FIXTURE:
            print("  [OFFLINE TEST FIXTURE RUN] NOT A LIVE MARKET DATA FEED")
            print("=" * 78)
        elif campaign.data_mode == DataMode.FILE_IMPORT:
            print("  [DATASET FILE IMPORT] PROVENANCE: FILE_IMPORT (OFFICIAL OBSERVED ARCHIVE)")
            print("=" * 78)
        else:
            print("     APMC MANDI LIVE PRICE INGESTION & DATA TRUST REPORT")
            print("=" * 78)
        print(f"Run ID (UTC)         : {campaign.run_id_utc}")
        print(f"Execution Time (IST) : {campaign.execution_timestamp_ist}")
        print(f"Data Mode            : [{campaign.data_mode.value}] (is_synthetic: {campaign.is_synthetic})")
        print(f"Operational State    : [{campaign.overall_operational_state.value}]")
        print(f"Live Verified        : {'YES' if campaign.is_live_verified else 'NO (DATASET IMPORT / FIXTURE / KEY_MISSING)'}")
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
            print(f"  • {cap:<28}: {val}")
        print("=" * 78)

    if campaign.is_blocked:
        return 2
    if campaign.overall_operational_state in (
        OperationalState.SUCCESS,
        OperationalState.UNCHANGED,
        OperationalState.QUARANTINED,
    ):
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
