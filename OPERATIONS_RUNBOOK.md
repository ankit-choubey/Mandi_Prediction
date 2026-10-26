# OPERATIONS_RUNBOOK.md: APMC Mandi Real-Time Data Pipeline
## Operational Runbook & System Health Manual

**Project:** APMC Mandi Market Intelligence System  
**Repository:** `ankit-choubey/Mandi_Prediction`  
**Owner / Author:** Om Awasthi (Owner 4: Current-Data Output & Operational Reliability)  
**Version:** 1.0.0  
**Last Updated:** October 2026  

---

## 1. System Mission & Operational Scope

The Mandi Prediction system bridges genuine wholesale agricultural price reporting from the Government of India (data.gov.in / AGMARKNET) with verified, leakage-safe market intelligence.

As defined in **Milestone 3 & Milestone 4** of the Project Execution Plan, the system's operational credibility depends on **absolute truth in reporting**:
* **Observation Date vs. Retrieval Timestamp:** The date produce traded in the mandi (`Arrival_Date`) is **strictly distinguished** from the timestamp our server retrieved the record (`last_successful_fetch_utc`).
* **Offline Safety Fallback:** Upstream network timeouts or API outages **never delete or corrupt** the last validated dataset.
* **Deterministic Output:** All operational displays reproduce deterministically from immutable, SHA-256 hashed data snapshots.

---

## 2. Quick-Start Commands

### 2.1 Display Current Market Intelligence Dashboard
Run the primary operational dashboard to inspect live status, freshness, and reconciliation metrics:
```bash
python3 -m src.current_data_output
```

### 2.2 Query a Specific Commodity / District Snapshot
Look up the latest modal clearing price for a specific crop and district:
```bash
# Query latest Potato observation in Kanpur APMC
python3 -m src.current_data_output --commodity Potato --district Kanpur

# Query latest Onion observation in Unnao APMC
python3 -m src.current_data_output --commodity Onion --district Unnao

# Query latest Wheat observation in Lucknow APMC
python3 -m src.current_data_output --commodity Wheat --district Lucknow
```

### 2.3 Programmatic Machine-Readable JSON Output
Emit structured JSON for automated health monitoring, CI assertion, or dashboard integration:
```bash
python3 -m src.current_data_output --json
```

### 2.4 End-to-End Integration Demo Command (For Ankit / Release Gate)
Execute the complete integration demo validating live data loading, reconciliation balance, and terminal rendering:
```bash
python3 -m src.current_data_output --demo
```

### 2.5 Run the Operational Test Suite
Verify that all 7 operational states, freshness boundaries, and reconciliation arithmetic pass:
```bash
python3 -m unittest tests/test_operational_output.py
```

---

## 3. The 7 Operational Pipeline States

Every pipeline execution evaluates into one of seven mutually exclusive operational states:

| State Code | Operational Meaning | System Behavior & User Alert | Action Required |
|---|---|---|---|
| **`SUCCESS`** | Live fetch succeeded; incoming records pass validation and update current panel. | `[SUCCESS]` Green badge. Displays new record count and updated latest observation date. | None. Normal operations. |
| **`UNCHANGED`** | Live fetch succeeded, but source has not published new trading records since last run. | `[UNCHANGED]` Blue badge. Existing validated dataset preserved without creating duplicate rows. | Normal during market holidays or pre-clearing hours. |
| **`PARTIAL`** | Upstream API truncated response or pagination stopped before 100% of pages were retrieved. | `[PARTIAL]` Amber warning. Incomplete batch is quarantined; previous valid snapshot retained. | Check network stability and API rate-limits. |
| **`QUARANTINED`** | Batch completed, but one or more records failed price bounds ($Min > Max$) or natural-key conflict. | `[QUARANTINED]` Amber badge. Valid records published; bad rows preserved in `data/quarantine/`. | Inspect `data/quarantine/` logs to review bad rows. |
| **`SOURCE_DOWN`** | Upstream data.gov.in API is unreachable or returned HTTP 5xx/408/Timeout. | `[SOURCE_DOWN]` Fallback active. System serves last validated offline snapshot with clear warning. | Retry with backoff. Check government portal status. |
| **`UNINITIALIZED`** | First run failed and zero prior validated snapshots exist in storage. | `[UNINITIALIZED]` Critical failure. Exits with descriptive error; no mock data invented. | Run historical backfill pipeline (`src/data_pipeline.py`). |
| **`STALE_DATA`** | Ingestion succeeded, but newest observation date exceeds freshness threshold (> 5 days). | `[STALE_DATA]` Red alert. Displays exact calendar lag between trading date and system date. | Investigate reporting hiatus or seasonal closure. |

---

## 4. Freshness Policy & Rules

Freshness evaluates the time lag between the **latest observed transaction date** and the current system date:

$$\text{Lag}_{\text{days}} = \text{Date}_{\text{current}} - \text{Date}_{\text{latest observation}}$$

| Freshness Status | Lag Threshold | Practical Agricultural Interpretation |
|---|---|---|
| **`CURRENT`** | $\le 2$ calendar days | Normal daily reporting cadence. APMC mandis report evening clearing data for $T-1$ or $T-2$. |
| **`DELAYED`** | $3$ to $5$ calendar days | Weekend closure (Sundays) or local gazetted holiday. Normal operational buffer. |
| **`STALE`** | $> 5$ calendar days | Strike, seasonal harvest hiatus, or upstream API reporting failure. Must trigger warning. |

> **CRITICAL DIRECTIVE:** A stale observation date **must never be disguised** by showing the server retrieval timestamp. Both dates must always appear side-by-side.

---

## 5. Reconciliation Ledger Accounting

To prevent silent data loss or uncontrolled record swelling, every run accounts for 100% of records under the Section 8 contract:

$$\text{Records Fetched} = \text{Records Accepted} + \text{Records Quarantined}$$

$$\text{Records Accepted} = \text{New Natural Keys} + \text{Unchanged Duplicates} + \text{Corrected Revisions}$$

### Current Validated Snapshot Baseline:
* **Total Raw Rows Loaded:** 472,385
* **Clean Accepted Records:** 462,350
* **Quarantined Invalid (Min > Max, Non-Positive):** 27
* **Quarantined Conflicting (Same Key, Differing Price):** 2,936
* **Low-Observation Filtered:** 7,072
* **Current Active Series:** 1,297 canonical series spanning 1,856 calendar days (2021-09-01 to 2026-09-30)
* **Accepted Dataset SHA-256:** `20a198682c3f5382a25276a916e258f8fef4aa777c9c6d1cebe6e7c03a206dfa`

---

## 6. Troubleshooting & Failure Recovery Runbook

### Scenario A: Upstream data.gov.in API Outage (`SOURCE_DOWN`)
1. **Symptom:** Network error `HTTP 408 / 503` or `ConnectionRefusedError`.
2. **Behavior:** The system automatically logs the outage and serves the latest verified snapshot at `data/processed/mandi_5year_validated.csv`.
3. **Verification Command:**
   ```bash
   python3 -m src.current_data_output --sim-state SOURCE_DOWN
   ```
4. **Recovery Steps:**
   * Verify internet connectivity: `curl -I https://api.data.gov.in`
   * Check government resource status: `https://data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070`
   * Check if private API key in `DATA_GOV_IN_API_KEY` is active and unexpired.

### Scenario B: Quarantined Records Spike (`QUARANTINED`)
1. **Symptom:** `records_quarantined > 0` in dashboard.
2. **Investigation:** Open the quarantine ledgers:
   - `data/quarantine/quarantined_invalid_records.csv`: Inspect price violations ($Min > Max$).
   - `data/quarantine/quarantined_conflicting_records.csv`: Inspect conflicting same-day quotes.
3. **Recovery:** Never manually overwrite or delete quarantined files. Quarantined records remain excluded from model training until official errata are published by DMI / AGMARKNET.

### Scenario C: Stale Data Warning (`STALE_DATA`)
1. **Symptom:** Freshness indicator displays `[STALE] (> 5 calendar days)`.
2. **Investigation:**
   - Inspect the latest arrival date in the dataset: `latest_observation_date`.
   - Check if the mandi was closed for major agricultural festivals (e.g., Diwali, Holi) or harvest hiatus.
   - Run manual fallback inspection against the AGMARKNET web portal (`agmarknet.gov.in`).

---

## 7. Environment Variables & Security Hygiene

* **`DATA_GOV_IN_API_KEY`**: Private API key for data.gov.in daily mandi prices.
  * *Security Directive:* **NEVER commit API keys to Git, hard-code them in source files, or print them in logs.**
  * *Usage:* Pass via terminal environment:
    ```bash
    export DATA_GOV_IN_API_KEY="your_private_api_key_here"
    ```
* **Python Path:** Ensure workspace root is in `PYTHONPATH`:
  ```bash
  export PYTHONPATH=".:$PYTHONPATH"
  ```

---

## 8. Handoff & Release Acceptance Checklist (For Ankit)

- [x] **Separate Timestamps:** Latest Observation Date (`2026-09-30`) and Retrieval Time (`2026-10-23`) rendered independently.
- [x] **Operational States:** All 7 states modeled, documented, and covered by unit tests.
- [x] **Reconciliation Ledger:** Record counts reconcile exactly without silent drops.
- [x] **Deterministic Playback:** Dashboard reproduces directly from verified snapshot.
- [x] **Automated Tests:** 15/15 operational unit tests passing (`tests/test_operational_output.py`).
- [x] **Single Demo Command:** `python3 -m src.current_data_output --demo` provides immediate visual proof.

*Certified by: Om Awasthi — Operational Reliability & Current-Data Output Lead*
