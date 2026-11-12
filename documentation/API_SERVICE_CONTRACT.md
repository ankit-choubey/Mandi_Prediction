# APMC Mandi Intelligence System — API Service Contract (v1.0.0)

**Document ID:** `API-CONTRACT-001`
**Milestone:** Step 10 (Dataset-First Backend Architecture)
**Implementation Modules:** `src/service_contracts.py`, `src/service.py`, `src/api.py`, `run_service.py`
**OpenAPI Specification:** [openapi_v1.json](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/documentation/openapi_v1.json)

---

## 1. Architectural Philosophy and Operational Scope

The APMC Mandi Market Intelligence API provides an audited, dataset-first HTTP service layer connecting validated storage artifacts, market price observations, benchmark scorecards, and research economics calculators.

### Critical Safety and Operational Constraints:
1. **Loopback Serving Only (`127.0.0.1`):** The service is designed and configured strictly for local loopback serving. It must NOT be exposed on public interfaces or deployed as an unauthenticated open web service.
2. **Zero Synthetic Generation:** The service serves only observed, imported, or audited historical artifacts. No synthetic operational feeds, fabricated trade rows, or simulated live scenarios are generated.
3. **Fail-Closed Advisory Gating:** Operational advisory status is unconditionally `BLOCKED` (`advisory_permitted = False`). Retrospective models and unverified commercial cost assumptions cannot authorize live farmer recommendations.
4. **Pure Standard Library Runtime:** The WSGI adapter is implemented using pure Python standard-library components (`wsgiref.simple_server`, `urllib.parse`, `json`, `http.client`), eliminating external web framework dependency debt.

---

## 2. Standard Response Envelope and Error Handling

All versioned endpoints return responses wrapped in a uniform, machine-readable envelope with strict non-finite value protection (`allow_nan=False`).

### Response Envelope Schema:
```json
{
  "schema_version": "1.0.0",
  "request_id": "c1f7b8d2-4e92-4f05-8912-3df621a590b4",
  "as_of_utc": "2026-11-13T01:30:00.000000+00:00",
  "status": "SUCCESS",
  "data": { ... },
  "error": null
}
```

### Error Object Schema:
When `status` is `"ERROR"` or `"UNAVAILABLE"`, the `error` object provides stable programmatic reason codes:
```json
{
  "code": "INVALID_ECONOMIC_PARAMETERS",
  "message": "Field 'storage_cost_per_quintal' cannot be less than 0.0, got -10.0",
  "details": null
}
```

### HTTP Status Code Mapping:
- `200 OK`: Request succeeded. Note: Unavailable capabilities (such as `/api/v1/forecast`) return HTTP 200 with envelope `status: "UNAVAILABLE"` and explicit reason codes to allow predictable client handling.
- `400 Bad Request`: Validation failure, non-finite domain error, invalid pagination parameter, or malformed JSON.
- `404 Not Found`: Unknown endpoint route.
- `405 Method Not Allowed`: HTTP verb mismatch (e.g. POST on a GET-only route).
- `413 Payload Too Large`: Request body exceeds maximum allowed limit (1 MB).
- `500 Internal Server Error`: Unhandled server exception. Secret-safe: stack traces and internal paths are never exposed.
- `503 Service Unavailable`: Underlyling storage index or snapshot is missing or unreadable.

---

## 3. Date Policy and Freshness Accounting

The service strictly adheres to the official **India Date Policy**:
- **Reference Timezone:** Asia/Kolkata (`UTC+05:30`).
- **Dynamic Age Computation:** On every request, `age_days` is dynamically calculated as:
  $$\text{age\_days} = (\text{server\_date}_{\text{IST}} - \text{observation\_date}_{\text{IST}}).\text{days}$$
  Stored static `freshness_days` in imported files is treated as stale metadata and never used for freshness decisions.
- **Provenance Preservation:** Imported files retain `data_mode: "FILE_IMPORT"`. Executing an API request at the current time does not convert an imported file record into a `LIVE_FETCH` or live-verified observation.

---

## 4. Versioned Endpoint Reference

### 4.1 Health and Capability Readiness
- **Route:** `GET /api/v1/health`
- **Purpose:** Distinguishes a running process from individual capability readiness.
- **Capabilities Matrix:**
  - `prices`: `AVAILABLE` (if imported index loaded)
  - `history`: `UNAVAILABLE_RESTRICTED` (full-panel raw scans blocked on local runtime)
  - `benchmarks`: `AVAILABLE` (audited scorecards)
  - `forecast`: `UNAVAILABLE` (`NO_APPROVED_SERVING_MODEL_ARTIFACT`)
  - `economics`: `RESEARCH_ONLY` (conditional on user inputs)
  - `active_advice`: `BLOCKED` (prospective validation required)

### 4.2 Market Catalog
- **Route:** `GET /api/v1/catalog`
- **Purpose:** Exposes supported districts, markets, commodities, and varieties.
- **Identity Integrity:**
  - `Rice` and `Paddy(Common)` / `Paddy(Dhan)(Common)` are strictly preserved as distinct commodities.
  - Six declared focus crops are highlighted: `Wheat`, `Potato`, `Onion`, `Tomato`, `Paddy(Common)`, `Rice`.

### 4.3 Latest Price Observations
- **Route:** `GET /api/v1/prices/latest`
- **Query Parameters:**
  - `commodity` (string, optional): Filter by commodity name.
  - `district` (string, optional): Filter by district name.
  - `market` (string, optional): Filter by market name (canonical or raw).
- **Invariants:**
  - Returns ALL matching series records (never arbitrarily discards varieties/grades).
  - Preserves `min_price` and `max_price` as `null` if missing from source (never defaults to `modal_price`).
  - Preserves exact market alias status (e.g. `REVIEW` series never become `ACCEPTED` by default).

### 4.4 Bounded Price History
- **Route:** `GET /api/v1/prices/history`
- **Query Parameters:** `district`, `market`, `commodity`, `start_date`, `end_date`, `page` (default 1), `page_size` (default 20, max 100).
- **Policy:** Fails honest `UNAVAILABLE` (`HISTORY_UNAVAILABLE`) unless an approved historical snapshot is configured. Local runtime limits strictly prohibit ad-hoc 5-year full panel queries.

### 4.5 Model Benchmark Information
- **Route:** `GET /api/v1/models/benchmark`
- **Verified Facts Disclosed:**
  - Naive persistence baseline MAE `106.96` beats HistGradientBoosting (`109.75`) and Ridge (`110.32`).
  - HistGradientBoosting improves RMSE by `5.91%` (`176.62` vs `187.72`) but does not win primary MAE.
  - Overall 90% empirical coverage is `89.95%`, but collapses during crisis regimes: F3 (`75.94%`) and F4 (`72.26%`).

### 4.6 Forecast Gating
- **Route:** `POST /api/v1/forecast`
- **Request Body:** `{"district": "Lucknow", "market": "Lucknow", "commodity": "Wheat", "horizon_days": 7}`
- **Behavior:** Returns `status: "UNAVAILABLE"`, `forecast_status: "FORECAST_UNAVAILABLE"`, and `advisory_action: "BLOCKED"`. Does not deserialize incompatible model weights or train on request.

### 4.7 Research Economics Evaluation
- **Route:** `POST /api/v1/economics/evaluate`
- **Request Body:** `ResearchEconomicRequest` payload (quantity, spot price, optional interval bounds, holding period, and optional `params`).
- **Behaviors:**
  - If `params` is omitted: Returns incomplete holding proceeds (`r_hold = null`, `gain = null`, `p_break_even = null`), `break_even_relation: "INCOMPLETE_PARAMETERS"`, and explicit `missing_cost_inputs`.
  - If `params` is provided: Evaluates canonical accounting, enforces horizon reconciliation, verifies provenance consistency, checks affine bounds ($p_{\text{lower}} \le p_{\text{point}} \le p_{\text{upper}}$), and enforces advisory action `BLOCKED`.
