"""
WSGI HTTP API Adapter (MP-APP-001A)
APMC Mandi Intelligence System - Step 10 Dataset-First Backend
Pure Python standard-library WSGI application.
Supports versioned API endpoints, strict JSON validation (allow_nan=False),
secret-safe error handling, and loopback development serving.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from typing import Any, Callable, Dict, List, Optional, Tuple
import urllib.parse
import uuid
from wsgiref.simple_server import make_server

from src.service import MandiMarketService
from src.service_contracts import (
    ServiceEnvelope,
    ServiceError,
    ServiceStatus,
    ForecastServiceRequest,
    dumps_strict_json,
)

MAX_BODY_BYTES = 1024 * 1024  # 1 MB maximum request body


class MandiApiApp:
    """
    Standard-library WSGI Application providing versioned HTTP endpoints:
    - GET  /api/v1/health
    - GET  /api/v1/catalog
    - GET  /api/v1/prices/latest
    - GET  /api/v1/prices/history
    - GET  /api/v1/models/benchmark
    - POST /api/v1/forecast
    - POST /api/v1/economics/evaluate
    """

    def __init__(self, service: Optional[MandiMarketService] = None):
        self.service = service or MandiMarketService()

    def __call__(self, environ: Dict[str, Any], start_response: Callable) -> List[bytes]:
        request_id = str(uuid.uuid4())
        as_of_utc = datetime.now(timezone.utc).isoformat()

        path_info = environ.get("PATH_INFO", "").rstrip("/")
        method = environ.get("REQUEST_METHOD", "GET").upper()

        # Route matching
        try:
            if path_info == "" or path_info == "/api/v1/health":
                return self._handle_health(environ, method, start_response, request_id, as_of_utc)
            elif path_info == "/api/v1/catalog":
                return self._handle_catalog(environ, method, start_response, request_id, as_of_utc)
            elif path_info == "/api/v1/prices/latest":
                return self._handle_latest_prices(environ, method, start_response, request_id, as_of_utc)
            elif path_info == "/api/v1/prices/history":
                return self._handle_price_history(environ, method, start_response, request_id, as_of_utc)
            elif path_info == "/api/v1/models/benchmark":
                return self._handle_benchmarks(environ, method, start_response, request_id, as_of_utc)
            elif path_info == "/api/v1/forecast":
                return self._handle_forecast(environ, method, start_response, request_id, as_of_utc)
            elif path_info == "/api/v1/economics/evaluate":
                return self._handle_economics(environ, method, start_response, request_id, as_of_utc)
            else:
                return self._send_json(
                    start_response,
                    status_code="404 Not Found",
                    payload=ServiceEnvelope(
                        request_id=request_id,
                        as_of_utc=as_of_utc,
                        status=ServiceStatus.ERROR.value,
                        error=ServiceError(
                            code="NOT_FOUND",
                            message=f"Endpoint '{path_info}' does not exist on this server.",
                        ),
                    ),
                )
        except Exception as ex:
            # Secret-safe generic error response: never leak internal stack traces or paths
            return self._send_json(
                start_response,
                status_code="500 Internal Server Error",
                payload=ServiceEnvelope(
                    request_id=request_id,
                    as_of_utc=as_of_utc,
                    status=ServiceStatus.ERROR.value,
                    error=ServiceError(
                        code="INTERNAL_ERROR",
                        message=f"An unexpected internal error occurred: {type(ex).__name__}",
                    ),
                ),
            )

    def _parse_query_params(self, environ: Dict[str, Any]) -> Dict[str, str]:
        qs = environ.get("QUERY_STRING", "")
        parsed = urllib.parse.parse_qs(qs, keep_blank_values=False)
        # Flatten single parameters
        return {k: v[0] for k, v in parsed.items() if v}

    def _read_json_body(self, environ: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            content_length = int(environ.get("CONTENT_LENGTH", 0))
        except (ValueError, TypeError):
            content_length = 0

        if content_length > MAX_BODY_BYTES:
            return None, "PAYLOAD_TOO_LARGE"

        content_type = environ.get("CONTENT_TYPE", "")
        if content_type and not content_type.lower().startswith("application/json"):
            return None, "UNSUPPORTED_MEDIA_TYPE"

        if content_length <= 0:
            return {}, None

        body_stream = environ.get("wsgi.input")
        if body_stream is None:
            return {}, None

        raw_bytes = body_stream.read(content_length)

        def _reject_constant(c):
            raise ValueError(f"Constant '{c}' is not valid JSON number")

        try:
            parsed = json.loads(raw_bytes.decode("utf-8"), parse_constant=_reject_constant)
            if not isinstance(parsed, dict):
                return None, "JSON_ROOT_MUST_BE_OBJECT"
            return parsed, None
        except ValueError as ve:
            if "Constant" in str(ve) or "not valid JSON" in str(ve):
                return None, "INVALID_JSON_NUMBER"
            return None, f"INVALID_JSON: {str(ve)}"
        except Exception as e:
            return None, f"INVALID_JSON: {str(e)}"

    def _send_json(
        self,
        start_response: Callable,
        status_code: str,
        payload: ServiceEnvelope,
    ) -> List[bytes]:
        response_json = dumps_strict_json(payload.to_dict())
        response_bytes = response_json.encode("utf-8")
        headers = [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(response_bytes))),
            ("X-Content-Type-Options", "nosniff"),
        ]
        start_response(status_code, headers)
        return [response_bytes]

    def _handle_health(
        self,
        environ: Dict[str, Any],
        method: str,
        start_response: Callable,
        request_id: str,
        as_of_utc: str,
    ) -> List[bytes]:
        if method != "GET":
            return self._method_not_allowed(start_response, request_id, as_of_utc, "GET")

        health_data = self.service.get_health()
        return self._send_json(
            start_response,
            status_code="200 OK",
            payload=ServiceEnvelope(
                request_id=request_id,
                as_of_utc=as_of_utc,
                status=ServiceStatus.SUCCESS.value,
                data=health_data.to_dict(),
            ),
        )

    def _handle_catalog(
        self,
        environ: Dict[str, Any],
        method: str,
        start_response: Callable,
        request_id: str,
        as_of_utc: str,
    ) -> List[bytes]:
        if method != "GET":
            return self._method_not_allowed(start_response, request_id, as_of_utc, "GET")

        catalog = self.service.get_catalog()
        return self._send_json(
            start_response,
            status_code="200 OK",
            payload=ServiceEnvelope(
                request_id=request_id,
                as_of_utc=as_of_utc,
                status=ServiceStatus.SUCCESS.value,
                data=catalog.to_dict(),
            ),
        )

    def _handle_latest_prices(
        self,
        environ: Dict[str, Any],
        method: str,
        start_response: Callable,
        request_id: str,
        as_of_utc: str,
    ) -> List[bytes]:
        if method != "GET":
            return self._method_not_allowed(start_response, request_id, as_of_utc, "GET")

        params = self._parse_query_params(environ)
        comm = params.get("commodity")
        dist = params.get("district")
        mkt = params.get("market")

        try:
            records = self.service.get_latest_prices(commodity=comm, district=dist, market=mkt)
            return self._send_json(
                start_response,
                status_code="200 OK",
                payload=ServiceEnvelope(
                    request_id=request_id,
                    as_of_utc=as_of_utc,
                    status=ServiceStatus.SUCCESS.value,
                    data={
                        "query": {"commodity": comm, "district": dist, "market": mkt},
                        "total_matching_series": len(records),
                        "series": [r.to_dict() for r in records],
                    },
                ),
            )
        except RuntimeError as e:
            return self._send_json(
                start_response,
                status_code="503 Service Unavailable",
                payload=ServiceEnvelope(
                    request_id=request_id,
                    as_of_utc=as_of_utc,
                    status=ServiceStatus.UNAVAILABLE.value,
                    error=ServiceError(code="PRICE_INDEX_UNAVAILABLE", message=str(e)),
                ),
            )

    def _handle_price_history(
        self,
        environ: Dict[str, Any],
        method: str,
        start_response: Callable,
        request_id: str,
        as_of_utc: str,
    ) -> List[bytes]:
        if method != "GET":
            return self._method_not_allowed(start_response, request_id, as_of_utc, "GET")

        params = self._parse_query_params(environ)
        try:
            page = int(params.get("page", 1))
            page_size = int(params.get("page_size", 20))
        except ValueError:
            return self._send_json(
                start_response,
                status_code="400 Bad Request",
                payload=ServiceEnvelope(
                    request_id=request_id,
                    as_of_utc=as_of_utc,
                    status=ServiceStatus.ERROR.value,
                    error=ServiceError(
                        code="INVALID_PAGINATION_PARAMETERS",
                        message="page and page_size must be valid integers.",
                    ),
                ),
            )

        try:
            res = self.service.get_price_history(
                district=params.get("district"),
                market=params.get("market"),
                commodity=params.get("commodity"),
                start_date=params.get("start_date"),
                end_date=params.get("end_date"),
                page=page,
                page_size=page_size,
            )
            return self._send_json(
                start_response,
                status_code="200 OK",
                payload=ServiceEnvelope(
                    request_id=request_id,
                    as_of_utc=as_of_utc,
                    status=ServiceStatus.UNAVAILABLE.value,
                    data=res,
                ),
            )
        except ValueError as ve:
            return self._send_json(
                start_response,
                status_code="400 Bad Request",
                payload=ServiceEnvelope(
                    request_id=request_id,
                    as_of_utc=as_of_utc,
                    status=ServiceStatus.ERROR.value,
                    error=ServiceError(code="BAD_REQUEST", message=str(ve)),
                ),
            )

    def _handle_benchmarks(
        self,
        environ: Dict[str, Any],
        method: str,
        start_response: Callable,
        request_id: str,
        as_of_utc: str,
    ) -> List[bytes]:
        if method != "GET":
            return self._method_not_allowed(start_response, request_id, as_of_utc, "GET")

        data = self.service.get_benchmark_scorecards()
        return self._send_json(
            start_response,
            status_code="200 OK",
            payload=ServiceEnvelope(
                request_id=request_id,
                as_of_utc=as_of_utc,
                status=ServiceStatus.SUCCESS.value,
                data=data,
            ),
        )

    def _handle_forecast(
        self,
        environ: Dict[str, Any],
        method: str,
        start_response: Callable,
        request_id: str,
        as_of_utc: str,
    ) -> List[bytes]:
        if method != "POST":
            return self._method_not_allowed(start_response, request_id, as_of_utc, "POST")

        body, err = self._read_json_body(environ)
        if err:
            status_code = "415 Unsupported Media Type" if err == "UNSUPPORTED_MEDIA_TYPE" else (
                "413 Payload Too Large" if err == "PAYLOAD_TOO_LARGE" else "400 Bad Request"
            )
            return self._send_json(
                start_response,
                status_code=status_code,
                payload=ServiceEnvelope(
                    request_id=request_id,
                    as_of_utc=as_of_utc,
                    status=ServiceStatus.ERROR.value,
                    error=ServiceError(code=err, message=f"Failed to parse request body: {err}"),
                ),
            )

        # Validate required fields
        required = ["district", "market", "commodity"]
        missing = [f for f in required if not body.get(f)]
        if missing:
            return self._send_json(
                start_response,
                status_code="400 Bad Request",
                payload=ServiceEnvelope(
                    request_id=request_id,
                    as_of_utc=as_of_utc,
                    status=ServiceStatus.ERROR.value,
                    error=ServiceError(
                        code="MISSING_REQUIRED_FIELDS",
                        message=f"Missing required fields: {', '.join(missing)}",
                    ),
                ),
            )

        # Validate horizon_days
        horizon_days = body.get("horizon_days", 7)
        if type(horizon_days) is bool or not isinstance(horizon_days, int) or horizon_days <= 0 or horizon_days > 365:
            return self._send_json(
                start_response,
                status_code="400 Bad Request",
                payload=ServiceEnvelope(
                    request_id=request_id,
                    as_of_utc=as_of_utc,
                    status=ServiceStatus.ERROR.value,
                    error=ServiceError(
                        code="INVALID_HORIZON_DAYS",
                        message=f"horizon_days must be a positive integer between 1 and 365, got {horizon_days}",
                    ),
                ),
            )

        req_obj = ForecastServiceRequest(
            district=body["district"],
            market=body["market"],
            commodity=body["commodity"],
            variety=body.get("variety", "Common"),
            grade=body.get("grade", "FAQ"),
            horizon_days=horizon_days,
        )
        res = self.service.evaluate_forecast(req_obj)
        return self._send_json(
            start_response,
            status_code="200 OK",
            payload=ServiceEnvelope(
                request_id=request_id,
                as_of_utc=as_of_utc,
                status=ServiceStatus.UNAVAILABLE.value,
                data=res.to_dict(),
            ),
        )

    def _handle_economics(
        self,
        environ: Dict[str, Any],
        method: str,
        start_response: Callable,
        request_id: str,
        as_of_utc: str,
    ) -> List[bytes]:
        if method != "POST":
            return self._method_not_allowed(start_response, request_id, as_of_utc, "POST")

        body, err = self._read_json_body(environ)
        if err:
            status_code = "415 Unsupported Media Type" if err == "UNSUPPORTED_MEDIA_TYPE" else (
                "413 Payload Too Large" if err == "PAYLOAD_TOO_LARGE" else "400 Bad Request"
            )
            return self._send_json(
                start_response,
                status_code=status_code,
                payload=ServiceEnvelope(
                    request_id=request_id,
                    as_of_utc=as_of_utc,
                    status=ServiceStatus.ERROR.value,
                    error=ServiceError(code=err, message=f"Failed to parse request body: {err}"),
                ),
            )

        # Validate required fields: quantity_quintals, current_price
        if not body or "quantity_quintals" not in body or "current_price" not in body:
            return self._send_json(
                start_response,
                status_code="400 Bad Request",
                payload=ServiceEnvelope(
                    request_id=request_id,
                    as_of_utc=as_of_utc,
                    status=ServiceStatus.ERROR.value,
                    error=ServiceError(
                        code="MISSING_REQUIRED_FIELDS",
                        message="Missing required fields: 'quantity_quintals' and 'current_price' must be provided.",
                    ),
                ),
            )

        try:
            res_dict = self.service.evaluate_economics(body)
            return self._send_json(
                start_response,
                status_code="200 OK",
                payload=ServiceEnvelope(
                    request_id=request_id,
                    as_of_utc=as_of_utc,
                    status=ServiceStatus.SUCCESS.value,
                    data=res_dict,
                ),
            )
        except (ValueError, TypeError, ZeroDivisionError) as ve:
            return self._send_json(
                start_response,
                status_code="400 Bad Request",
                payload=ServiceEnvelope(
                    request_id=request_id,
                    as_of_utc=as_of_utc,
                    status=ServiceStatus.ERROR.value,
                    error=ServiceError(
                        code="INVALID_ECONOMIC_PARAMETERS",
                        message=str(ve),
                    ),
                ),
            )

    def _method_not_allowed(
        self,
        start_response: Callable,
        request_id: str,
        as_of_utc: str,
        allowed_method: str,
    ) -> List[bytes]:
        return self._send_json(
            start_response,
            status_code="405 Method Not Allowed",
            payload=ServiceEnvelope(
                request_id=request_id,
                as_of_utc=as_of_utc,
                status=ServiceStatus.ERROR.value,
                error=ServiceError(
                    code="METHOD_NOT_ALLOWED",
                    message=f"Only HTTP {allowed_method} is supported on this endpoint.",
                ),
            ),
        )


def create_app(service: Optional[MandiMarketService] = None) -> MandiApiApp:
    return MandiApiApp(service=service)
