"""
Service Contracts and Data Transfer Objects (MP-APP-001A)
APMC Mandi Intelligence System - Step 10 Dataset-First Backend
Defines strict serialization contracts, enums, error models, and standard response envelopes.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime, date, timezone, timedelta
from enum import Enum
import json
import math
from typing import Any, Dict, List, Literal, Optional, Union
import uuid

# India Standard Time offset: UTC+05:30
IST_OFFSET = timezone(timedelta(hours=5, minutes=30))


class ServiceStatus(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    UNAVAILABLE = "UNAVAILABLE"
    ERROR = "ERROR"


class MarketDataMode(str, Enum):
    FILE_IMPORT = "FILE_IMPORT"
    LIVE_FETCH = "LIVE_FETCH"
    SIMULATION = "SIMULATION"


class MarketAliasStatus(str, Enum):
    ACCEPTED = "ACCEPTED"
    REVIEW = "REVIEW"
    UNKNOWN = "UNKNOWN"


def safe_json_serialize(obj: Any) -> Any:
    """Recursively cleans floats, turning NaN/Inf to None, and serializing dataclasses/dates."""
    if obj is None:
        return None
    if isinstance(obj, (bool, str, int)):
        return obj
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, Enum):
        return obj.value
    if hasattr(obj, "to_dict"):
        return safe_json_serialize(obj.to_dict())
    if hasattr(obj, "__dataclass_fields__"):
        return safe_json_serialize(asdict(obj))
    if isinstance(obj, dict):
        return {str(k): safe_json_serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [safe_json_serialize(v) for v in obj]
    return str(obj)


def dumps_strict_json(obj: Any, indent: Optional[int] = None) -> str:
    """Serializes data to strict JSON disallowing raw NaN/Infinity (allow_nan=False)."""
    clean_obj = safe_json_serialize(obj)
    return json.dumps(clean_obj, indent=indent, allow_nan=False)


@dataclass
class ServiceError:
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class ServiceEnvelope:
    schema_version: str = "1.0.0"
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    as_of_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = ServiceStatus.SUCCESS.value
    data: Optional[Any] = None
    error: Optional[ServiceError] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "request_id": self.request_id,
            "as_of_utc": self.as_of_utc,
            "status": self.status,
            "data": self.data,
            "error": self.error.to_dict() if self.error else None,
        }


@dataclass
class ServiceCapability:
    available: bool
    status: str
    reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "available": self.available,
            "status": self.status,
            "reason": self.reason,
            "metadata": self.metadata,
        }


@dataclass
class HealthResponseData:
    process_status: str
    uptime_seconds: float
    server_time_utc: str
    server_time_ist: str
    date_policy_timezone: str
    capabilities: Dict[str, ServiceCapability]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "process_status": self.process_status,
            "uptime_seconds": self.uptime_seconds,
            "server_time_utc": self.server_time_utc,
            "server_time_ist": self.server_time_ist,
            "date_policy_timezone": self.date_policy_timezone,
            "capabilities": {k: v.to_dict() for k, v in self.capabilities.items()},
        }


@dataclass
class PriceSeriesRecord:
    series_id: str
    district: str
    market_canonical: str
    market_raw: str
    commodity: str
    variety: str
    grade: str
    observation_date: str
    age_days: int
    modal_price: float
    min_price: Optional[float]
    max_price: Optional[float]
    price_unit: str
    market_alias_status: str
    status: str
    status_reason: str
    data_mode: str
    import_timestamp_utc: str
    is_live_verified: bool
    is_import_verified: bool
    source_file_hashes: List[str]
    capabilities: Dict[str, bool]

    @property
    def price_display_permitted(self) -> bool:
        return bool(self.capabilities.get("price_display_permitted", False))

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["price_display_permitted"] = self.price_display_permitted
        d["market"] = self.market_canonical
        return d


@dataclass
class CatalogData:
    total_series_count: int
    focus_crops: List[str]
    districts: List[str]
    markets: List[Dict[str, str]]
    commodities: List[str]
    series_inventory: List[Dict[str, Any]]
    commodity_aliases: Optional[Dict[str, str]] = None
    accepted_series_count: int = 0
    review_series_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ForecastServiceRequest:
    district: str
    market: str
    commodity: str
    variety: str = "Common"
    grade: str = "FAQ"
    horizon_days: int = 7

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ForecastServiceResult:
    series_id: str
    horizon_days: int
    point_forecast: Optional[float]
    interval_lower: Optional[float]
    interval_upper: Optional[float]
    nominal_level: float
    forecast_status: str
    reason: str
    advisory_action: str
    advisory_permitted: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
