# Live Price Ingestion & Operational Data Trust Runbook

**Repository:** `ankit-choubey/Mandi_Prediction`
**Document ID:** `LIVE_INGESTION_RUNBOOK`
**Established Under Task:** `MP-SRC-004` (Foundations)
**Updated Under Task:** `MP-SRC-004B` (Provenance, Conflict Safety & Dataset-First Default) & `MP-DATA-008` (Latest Index, XLSX Support & Multi-File Provenance)
**Date:** 2026-11-12 IST
**Engine:** `src/live_price_ingestion.py`, `src/current_data_output.py`, `src/forecast_features.py`
**Contract Specification:** `data/reference/live_source_contract.json` (Version 1.2.0), `data/reference/operational_sources.json` (Version 1.0.0)

---

## 1. Overview & Architectural Principles

This runbook documents the operational workflow for dataset file ingestion and live/offline ingestion of daily wholesale mandi prices from the official Government of India Open Government Data (OGD) platform (`data.gov.in`), resource UUID `9ef84268-d588-465a-a308-a864a43d0070` (AGMARKNET Daily Price Arrivals).

### Standing Owner Rule:
> [!IMPORTANT]
> **ZERO SYNTHETIC DATASETS / SIMULATED OPERATIONAL FEEDS:**
> No new synthetic datasets, simulated operational feeds, model-training rows, or storage scenarios may be generated without prior explanation and explicit owner approval. Never replace unavailable live data with fake-now records.

### Core Architectural Guarantees:
1. **Explicit Provenance Modes (`DataMode`):**
   - `LIVE_FETCH`: Authenticated real network harvest. Only mode that can set `is_live_verified=True` or advance `last_successful_campaign.json`.
   - `FILE_IMPORT`: Primary dataset-first operational source from official downloaded APMC raw files (`data/raw/*.csv`). Never claims live verification.
   - `HISTORICAL_REPLAY`: Replay of preserved snapshots preserving original trade and retrieval timestamps.
   - `TEST_FIXTURE`: Offline mock tests. Writes to `data/fixture_snapshots/`. Never claims live verification.
   - `SYNTHETIC_SIMULATION`: Reserved mode requiring explicit owner approval.
2. **Zero Credential Exposure:** API keys are never printed, logged, committed, or embedded in stored receipt URLs or error messages. Echoed keys in response bodies are automatically redacted.
3. **Immutable Snapshot Receipts:** Raw API responses and import receipts are stored under ignored directories (`data/live_snapshots/`, `data/imported_snapshots/`, `data/fixture_snapshots/`) using exclusive writes (`mode 'x'`). No snapshot is ever overwritten or modified.
4. **Order-Invariant Conflict Safety:** When divergent prices appear for the identical natural key, ALL records for that key are quarantined as `CONFLICTING_QUOTE`.
5. **Honest Price Bounds:** Modal substitution ($P_{\min} = P_{\text{modal}}$) is strictly eliminated. Missing min/max bounds remain missing and are quarantined as `MISSING_REQUIRED_FIELDS`. Non-finite bounds (`NaN`, `Inf`) are quarantined as `INVALID_PRICE_BOUNDS`.
6. **Strict Disjoint Accounting:** Every fetched record is accounted for without silent loss:
   $$\text{records\_fetched} = \text{records\_accepted} + \text{records\_duplicate} + \sum \text{records\_quarantined}$$
7. **Decoupled Capabilities:** Fresh price availability alone does not authorize ML forecasting or synthetic-cost farmer advice. Capabilities are strictly segregated:
   - **Price Display:** Enabled for `CURRENT` ($\le 2$d) and `DELAYED` (3–5d) with explicit observation date disclosures.
   - **Forecast Eligibility:** Blocked (requires approved model release).
   - **Economics / Farmer Advisory:** Blocked (commercial storage advice requires empirical farmgate costs, not synthetic parameters).

---

## 2. API Key Configuration & Verification

To execute live price harvests against `data.gov.in`, a developer API key is required from the portal.

### 2.1 Obtaining an API Key
1. Register an account at [data.gov.in](https://data.gov.in/).
2. Navigate to **My Account** -> **API Keys**.
3. Copy your unique 40+ character API token.

### 2.2 Local Configuration (Secret-Safe)
Store the API key in the repository's root `.env` file (which is strictly ignored by Git in `.gitignore`):

```bash
# Add to .env (do NOT commit this file)
OGD_API_KEY=your_actual_api_key_here
```

Alternatively, export the environment variable in your shell session:

```bash
export OGD_API_KEY="your_actual_api_key_here"
```

### 2.3 Safe Presence Check
To verify whether the key is detected without revealing its value:

```bash
python3 -c "
from src.live_price_ingestion import load_api_key
key = load_api_key()
print('OGD_API_KEY detected:', bool(key and key.strip()))
"
```

---

## 3. Manual Execution Workflows

### 3.1 Primary Operational Source: Dataset-First File Import (`FILE_IMPORT`)
Per the repository's dataset-first operational default, official observed APMC raw archives in `data/raw/*.csv`, `.xlsx`, and snapshot files serve as the primary operational source:

```bash
# Ingest using configured operational sources manifest and publish latest index
python3 -m src.live_price_ingestion --import-config data/reference/operational_sources.json

# Ingest single district raw file (.csv or official .xlsx) and publish latest index
python3 -m src.live_price_ingestion --import-file data/raw/Kanpur.csv --district Kanpur --publish-index

# Ingest single district with declared metadata
python3 -m src.live_price_ingestion \
  --import-file data/raw/Kanpur.csv \
  --district Kanpur \
  --source-url "https://agmarknet.gov.in" \
  --retrieval-time "2026-09-01T00:00:00Z"

# Ingest with machine-readable JSON output
python3 -m src.live_price_ingestion --import-file data/raw/Jhansi.csv --json
```

**Dataset Refresh Steps for Operators:**
1. Download official daily/monthly APMC mandi arrivals CSV or Excel (.xlsx) from Agmarknet or data.gov.in for the target district.
2. Verify file size $\le 10$ MB and row count $\le 50,000$ (if file exceeds limits, request remote workflow).
3. Compute SHA-256 and confirm schema headers match `data/reference/live_source_contract.json` or `data/reference/operational_sources.json`.
4. Run `--import-config data/reference/operational_sources.json` or `--import-file` with `--publish-index`.
5. Review the generated `run_receipt.json` under `data/imported_snapshots/<RUN_ID>/` and `data/imported_snapshots/latest_observation_index.json` to confirm row reconciliation and zero unhandled errors.

### 3.1.1 Independent Import Pointer & Latest Observation Index
- **`data/imported_snapshots/last_successful_import.json`**: Updated automatically upon successful file imports with accepted records. Strictly segregated from `last_successful_campaign.json` (which is reserved for authenticated live runs).
- **`data/imported_snapshots/latest_observation_index.json`**: Bounded per-series latest observation registry queried directly by `CurrentDataReporter` to prevent scanning large panel files. Divergent quotes on latest dates are quarantined with explicit disclosure.

### 3.2 Offline Dry-Run (Mock Transport)
Runs the full ingestion pipeline, validation engine, reconciliation arithmetic, and health report formatting without initiating external network calls:

```bash
python3 -m src.live_price_ingestion --dry-run
```

To view machine-readable JSON output:

```bash
python3 -m src.live_price_ingestion --dry-run --json
```

### 3.3 Single District Live Harvest (Requires OGD_API_KEY)
Fetches and validates the daily price batch for one authorized district (e.g. `Kanpur`):

```bash
python3 -m src.live_price_ingestion --district Kanpur
```

### 3.4 Full 5-District Live Campaign (Requires OGD_API_KEY)
Executes a bounded harvest across all five authorized districts (`Ghaziabad`, `Jhansi`, `Kanpur`, `Lucknow`, `Unnao`):

```bash
python3 -m src.live_price_ingestion --district all
```

### 3.5 Custom Reference Date
Specify an explicit evaluation date for backtesting or specific calendar reconciliation:

```bash
python3 -m src.live_price_ingestion --district all --date 2026-11-12
```

### 3.6 CLI Exit Code Contract
- `0`: Ingestion succeeded cleanly (`SUCCESS`, `UNCHANGED`, or `QUARANTINED` under dataset import).
- `1`: Ingestion encountered fatal operational failure (`SOURCE_DOWN` or unhandled error).
- `2`: Ingestion blocked due to missing or invalid credentials (`UNINITIALIZED` / `BLOCKED`).

---

## 4. Operational Freshness & Safety Gate Policies

Observations are evaluated against the current Indian Standard Time (IST) calendar date:

| Freshness Status | Age Threshold | Price Display Policy | Active Farmer Advisory Policy |
| :--- | :--- | :--- | :--- |
| **`CURRENT`** | $\le 2$ calendar days | Displayed with trade date | Permitted if non-conflicting, verified unit, non-review market |
| **`DELAYED`** | $3$ to $5$ calendar days | Displayed with **DELAYED DATA NOTICE** | **WITHHELD / BLOCKED** (storage advice requires CURRENT quotes) |
| **`STALE`** | $> 5$ calendar days | Displayed with **STALE DATA WARNING** | **BLOCKED** (`Insufficient information to recommend storage`) |
| **`FUTURE`** | $< 0$ calendar days | Quarantined / Hidden | **BLOCKED** (future date corruption rejected) |
| **`UNKNOWN`** | Date missing/malformed | Quarantined / Hidden | **BLOCKED** |

---

## 5. Scope & Quality Rules

### 5.1 Authorized Districts & Kanpur Subdivision Policy
The pipeline strictly authorizes five districts:
1. `Ghaziabad`
2. `Jhansi`
3. `Kanpur` (Kanpur Nagar / Kanpur Grain APMC, Baripaal APMC, Uttaripura APMC, Choubepur APMC)
4. `Lucknow`
5. `Unnao`

> [!IMPORTANT]
> **Kanpur Dehat Quarantine Policy:**
> Uttar Pradesh administrative divisions split the greater Kanpur region into Kanpur Nagar (authorized urban mandis) and Kanpur Dehat (rural mandis including Jhijhank, Rura, Pukharayan). Records returned with `District: Kanpur Dehat` are **strictly quarantined** as `OUT_OF_SCOPE_DISTRICT` to prevent silent geographic scope creep.

### 5.2 Grade Normalization Policy
If the upstream source omits the `Grade` field (e.g. `null`, empty string, or whitespace), it is normalized to:
$$\text{Grade} = \text{"SOURCE\_NOT\_PROVIDED"}$$
**Silent default mapping to `"FAQ"` is strictly forbidden.**

### 5.3 Market Alias Resolution
- Market names matching accepted entries in `data/reference/market_alias_candidates_v21.csv` are mapped to `market_canonical` with status `ACCEPTED`.
- Market names classified as `UNMAPPED/REVIEW` (e.g. `Purwa APMC` in Unnao, `Baripaal APMC -> Varipaal` in Kanpur) are isolated under disposition `UNKNOWN_MARKET_REVIEW`.
- Unrecognized market yards not present in the reference register enter disposition `UNKNOWN_MARKET_REVIEW`.

### 5.4 Honest Physical Price Bounds (No Modal Substitution)
Prices must satisfy:
$$0.0 < P_{\min} \le P_{\text{modal}} \le P_{\max}$$
- All price fields must be positive finite floats.
- **Modal substitution is strictly forbidden:** Missing `min_price` or `max_price` is never substituted with `modal_price`; it is honestly preserved as `None` and quarantined under `MISSING_REQUIRED_FIELDS`.
- Non-finite (`NaN`, `Inf`), non-positive ($\le 0$), and inverted bounds are quarantined as `INVALID_PRICE_BOUNDS`. Original raw inputs are preserved.

### 5.5 Order-Invariant Conflict Safety
If two or more observations in a batch share an identical natural key $(date, district, market, commodity, variety, grade)$ with divergent prices:
- **ALL** members of the conflict group are quarantined under `RecordDisposition.CONFLICTING_QUOTE`.
- Previously accepted or duplicate records for that natural key are retroactively removed from accepted counts.
- The observation date range is recomputed strictly from remaining accepted records.
- All input permutations (`[A,A,B]`, `[A,B,B]`, `[B,A,A]`, `[A,B,A]`) yield identical output arithmetic:
  $$\text{Fetched}(3) = \text{Accepted}(0) + \text{Duplicates}(0) + \text{Quarantined}(3)$$

---

## 6. Snapshot Receipt Architecture

Snapshots are written to `data/live_snapshots/<UTC_RUN_ID>/<District>/page_<offset:05d>.json`.

### Receipt Structure:
```json
{
  "page_offset": 0,
  "page_limit": 1000,
  "retrieval_start_utc": "2026-11-12T12:00:00.000000Z",
  "retrieval_end_utc": "2026-11-12T12:00:01.200000Z",
  "http_status": 200,
  "source_total": 42,
  "fetched_count": 42,
  "content_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "completeness_state": "COMPLETE",
  "sanitized_params": {
    "format": "json",
    "offset": 0,
    "limit": 1000,
    "filters[state]": "Uttar Pradesh",
    "filters[district]": "Kanpur",
    "api-key": "[REDACTED]"
  },
  "endpoint_sanitized": "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070",
  "records": [...],
  "error_message": null,
  "sanitized_credential_detected": false
}
```

A campaign summary receipt is written to `data/live_snapshots/<UTC_RUN_ID>/run_receipt.json`.

---

## 7. Operational Troubleshooting

| Symptom | Cause | Diagnostic Action | Remediation |
| :--- | :--- | :--- | :--- |
| Exit code `2`, state `UNINITIALIZED` | Missing API key | Run presence check | Add `OGD_API_KEY` to `.env` |
| HTTP `401` or `403` | Invalid or expired token | Check response body | Verify account key on data.gov.in portal |
| HTTP `429` Rate Limited | Quota or burst exceeded | Inspect response headers | Backoff and honor `Retry-After` window |
| State `PARTIAL` | Pagination/time budget exceeded | Inspect `run_receipt.json` warnings | Check network latency or increase batch timeout |
| State `QUARANTINED` | Validation or bounds violations | Check `disposition_counts` | Review quarantined records; normal for review markets |
| FileExistsError on write | Run ID collision | Check system clock | Exclusive write prevents overwriting old receipts |

---

## 8. Scheduler Integration Blueprint (Future Owner Activation)

> [!WARNING]
> **AUTOMATION STATUS: INACTIVE**
> Background automation (cron, launchd, systemd) is **NOT activated** under task MP-SRC-004. The instructions below provide a tested blueprint for manual activation by the repository owner following independent operational review.

### 8.1 Proposed Daily Schedule
- **Time:** 06:00 IST (00:30 UTC) daily (following standard overnight Agmarknet clearing).
- **Timezone:** Asia/Kolkata (IST).
- **Timeout:** 180 seconds total campaign hard timeout.
- **Locking:** Single-instance execution via `flock` or PID lockfile to prevent overlapping runs.

### 8.2 Execution Command Template
```bash
/usr/bin/flock -n /tmp/mandi_live_ingest.lock \
  /usr/bin/env python3 -m src.live_price_ingestion \
    --district all \
    --snapshots-dir /path/to/Mandi_Prediction/data/live_snapshots \
  >> /path/to/Mandi_Prediction/data/live_snapshots/ingest_cron.log 2>&1
```

### 8.3 Retention Policy
- Keep daily raw snapshot receipts for 90 days.
- Retain campaign run-receipt summaries indefinitely for audit provenance.
