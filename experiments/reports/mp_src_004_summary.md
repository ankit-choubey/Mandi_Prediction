# MP-SRC-004 Summary — Live Price Ingestion, Immutable Snapshots & Trust Reporting

**Task ID:** `MP-SRC-004` (Steps 3–5 Foundations)
**Date:** 2026-11-12 IST
**Baseline Git Commit:** `ed066bea9c0141c5fcb465864f5a5fbc9f74b121`
**Operational Status:** `IMPLEMENTED + CREDENTIALS/SOURCE BLOCKED`
**Live Endpoint Authorized:** `https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070`
**Credential State:** `OGD_API_KEY` absent from local environment and `.env`. Offline implementation, full contract, CLI, immutable snapshot engine, safety gate adapters, and unit test suite completed. Live verification campaign blocked pending local key configuration.

---

## 1. Executive Summary & Structured Status

### WHAT WE ACHIEVED
1. **Live Source Contract & Scope Definition (`data/reference/live_source_contract.json`):**
   - Formalized official data contract for data.gov.in / AGMARKNET resource `9ef84268-d588-465a-a308-a864a43d0070`.
   - Documented published wholesale price units as **Rs./Quintal** (verified from portal metadata, not inferred from price magnitudes).
   - Scoped exactly 5 authorized districts: `Ghaziabad`, `Jhansi`, `Kanpur`, `Lucknow`, and `Unnao`.
   - Established explicit policy for Kanpur subdivision ambiguity: `Kanpur Dehat` records are quarantined as `OUT_OF_SCOPE_DISTRICT` to prevent silent geographic scope creep.
   - Mandated missing grade normalization: missing/empty grade values are recorded explicitly as `SOURCE_NOT_PROVIDED`, never silently defaulted to `FAQ`.
2. **Reliable, Bounded Client & Snapshot Engine (`src/live_price_ingestion.py`):**
   - Built a modular, testable ingestion client with dependency injection for HTTP transport and system clock.
   - Bounded execution budgets enforced: $\le 50$ HTTP requests, $\le 25,000$ records, $\le 10$ MB per response, $10$s per-request timeout, $30$s per-district batch timeout.
   - Fail-closed pagination loop: detects repeated page content hashes, unadvancing offsets, unstable totals, and ignored district filters.
   - Built secret-safe credential loader: reads `OGD_API_KEY` from environment or ignored `.env` without shell execution or logging.
   - Implemented URL/parameter/exception sanitization and response body credential-echo detection/redaction.
   - Immutable snapshot storage under ignored `data/live_snapshots/<UTC_RUN_ID>/<District>/page_<offset:05d>.json` with exclusive writes (`mode 'x'`).
3. **Operational Trust & Safety Gate Policy Resolution (`src/health_status.py`, `src/current_data_output.py`):**
   - Resolved delayed policy mismatch: `CURRENT` $\le 2$ calendar days, `DELAYED` 3–5 calendar days, `STALE` $> 5$ calendar days.
   - Enforced policy that active commercial farmer advice is **withheld/blocked** on delayed, stale, future, missing, conflicting, review, or unverified-unit data.
   - Decoupled system capabilities: price display permitted with explicit observation date disclosures, while forecast eligibility and economics eligibility remain decoupled and blocked.
   - Bounded reads in `CurrentDataReporter` to strictly adhere to local resource constraints ($\le 10$ MB, $\le 50,000$ rows).
4. **Comprehensive Unit Test Suite (`tests/test_live_price_ingestion.py`, 22 tests):**
   - Exercised multi-page pagination, exact duplicates, conflicting quotes, same-payload refetch with independent receipts, repeated page abort, unstable totals, ignored district filters, HTTP 401/403/429/500, timeouts, malformed/source-error JSON, empty valid results, missing fields/grade, price bounds violations, malformed/future dates, unknown aliases, cross-district subdivision, IST day boundary, immutable collision protection, and secret sentinel absence.
   - Full test suite passed: **239 tests passed in 9.46s** (from 215 tests previously, +24 tests, 0 failures).
5. **Runbook & Operational Documentation (`documentation/LIVE_INGESTION_RUNBOOK.md`):**
   - Authored end-to-end runbook covering key configuration, manual CLI commands, exit codes, safety gate matrix, troubleshooting, and future scheduler integration blueprint.

### WHAT IS STILL OPEN
1. **Live Network Verification Campaign:**
   - Because `OGD_API_KEY` is not present in the local environment or `.env`, live verification against `api.data.gov.in` is **BLOCKED**. The implementation is 100% complete and tested with offline fixtures, but real API network calls have not been dispatched.
2. **Review Market Field Verification:**
   - `Purwa APMC` (Unnao) and `Baripaal APMC -> Varipaal` (Kanpur) remain classified as `UNMAPPED/REVIEW`.
3. **The 77 Feb–Mar 2026 Price Discrepancies:**
   - Cause remains UNKNOWN/UNRESOLVED between monthly export and daily panel feed.
4. **Scheduler Activation:**
   - Background automation (cron, launchd) is deliberately **INACTIVE** pending owner operational review.

### WHAT NEXT
1. Owner configures `OGD_API_KEY` in local `.env`.
2. Execute a single bounded verification campaign: `python3 -m src.live_price_ingestion --district all`.
3. Review retrieved live snapshot receipts under `data/live_snapshots/` and verify API uptime and live observation lag.
4. Owner decides on scheduler activation and benchmark dataset transition (v2 vs v2.1).

---

## 2. Capability Matrix: Tested vs Live-Verified

| Capability | Implementation Status | Tested via Mock / Fixtures | Live-Verified on API | Safety / Governance Policy |
| :--- | :--- | :--- | :--- | :--- |
| **API Parameter Sanitization** | `IMPLEMENTED` | `YES` (Test 01) | `PENDING_KEY` | Zero credential leakage permitted |
| **Pagination & Offset Loop** | `IMPLEMENTED` | `YES` (Test 02) | `PENDING_KEY` | Bounded $\le 50$ reqs, $\le 25,000$ rows |
| **Duplicate Deduplication** | `IMPLEMENTED` | `YES` (Test 03) | `PENDING_KEY` | Same key + same price $\to$ duplicate |
| **Conflicting Quote Quarantine** | `IMPLEMENTED` | `YES` (Test 04) | `PENDING_KEY` | Same key + divergent price $\to$ quarantined |
| **Immutable Snapshot Persistence** | `IMPLEMENTED` | `YES` (Test 05, 20) | `PENDING_KEY` | Collision-safe exclusive write (`mode 'x'`) |
| **Fail-Closed Cycle Detection** | `IMPLEMENTED` | `YES` (Test 06, 07) | `PENDING_KEY` | Aborts on repeated page hash or shifting total |
| **District Scope Enforcement** | `IMPLEMENTED` | `YES` (Test 08, 18) | `PENDING_KEY` | 5 approved districts; Kanpur Dehat quarantined |
| **HTTP Error Recovery & Backoff** | `IMPLEMENTED` | `YES` (Test 09-11) | `PENDING_KEY` | Immediate fail on 401/403; retry 429/5xx |
| **Grade Normalization** | `IMPLEMENTED` | `YES` (Test 14) | `PENDING_KEY` | Missing $\to$ `SOURCE_NOT_PROVIDED`, never `FAQ` |
| **Price Bounds Validation** | `IMPLEMENTED` | `YES` (Test 15) | `PENDING_KEY` | $0 < P_{\min} \le P_{\text{modal}} \le P_{\max}$ |
| **Market Alias Review Isolation** | `IMPLEMENTED` | `YES` (Test 17) | `PENDING_KEY` | Unmapped yards $\to$ `UNKNOWN_MARKET_REVIEW` |
| **Freshness Evaluation (IST)** | `IMPLEMENTED` | `YES` (Test 19) | `PENDING_KEY` | $\le 2$d CURRENT, 3–5d DELAYED, $>5$d STALE |
| **Price Display Capability** | `IMPLEMENTED` | `YES` (Test 22) | `PENDING_KEY` | Enabled for CURRENT and DELAYED with trade date |
| **Live Forecast Model Serving** | `DISABLED` | `N/A` | `NO` | Blocked (no approved live forecast model) |
| **Active Farmer Advisory Advice** | `BLOCKED` | `YES` (Gate tests) | `NO` | Blocked (requires empirical costs and CURRENT data) |

---

## 3. Five-District Evidence & Scope Register

| District | Scope Status | Mandi Yards Recognized | Subdivision / Scope Policy | Offline Harvest Outcome | Live API Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Ghaziabad** | Authorized (1 of 5) | Ghaziabad APMC, Hapur APMC, Muradnagar APMC, Noida APMC | Approved district; exact match | Verified (Mock: 0 errors) | `BLOCKED (KEY_MISSING)` |
| **Jhansi** | Authorized (2 of 5) | Chirgaon, Gurusarai, Jhansi, Jhansi (Grain), Mauranipur, Moth | Approved district; exact match | Verified (Mock: 0 errors) | `BLOCKED (KEY_MISSING)` |
| **Kanpur** | Authorized (3 of 5) | Kanpur(Grain), Choubepur, Uttaripura, Baripaal | Authorized urban mandis. **Kanpur Dehat** (Jhijhank, Rura, Pukharayan) quarantined | Verified (Mock: 1 accepted, 1 review) | `BLOCKED (KEY_MISSING)` |
| **Lucknow** | Authorized (4 of 5) | Lucknow APMC, Banthara APMC | Approved district; exact match | Verified (Mock: 3 accepted, 2 pages) | `BLOCKED (KEY_MISSING)` |
| **Unnao** | Authorized (5 of 5) | Bangarmau APMC, Unnao APMC; Purwa APMC (Review) | Approved district; Purwa APMC isolated for review | Verified (Mock: 0 errors) | `BLOCKED (KEY_MISSING)` |

---

## 4. Test Receipts & Verification Evidence

### Targeted Suite Execution:
```bash
python3 -m pytest tests/test_live_price_ingestion.py tests/test_recommendation_safety_gate.py tests/test_operational_output.py -v
```
**Outcome:** 56 passed in 5.42s (Exit code: 0).

### Full Repository Test Suite Execution:
```bash
python3 -m pytest tests/ -q
```
**Outcome:** 239 passed in 9.46s (Exit code: 0).

### Key Test Receipts:
- Secret sentinel absent from URLs, error messages, and written JSON receipts (`test_01`).
- Multi-page pagination advances offset and conserves rows ($3 = 3 + 0 + 0$, `test_02`).
- Identical duplicates deduplicated ($2 = 1 + 1 + 0$, `test_03`).
- Conflicting quotes quarantined ($2 = 1 + 0 + 1$, `test_04`).
- Successive identical fetches produce independent receipts with matching content SHA-256 (`test_05`).
- Repeated page detected and aborted (`test_06`).
- Unstable source total detected and reported as `PARTIAL` (`test_07`).
- Ignored district filter quarantined as `OUT_OF_SCOPE_DISTRICT` (`test_08`).
- HTTP 401/403 fails closed immediately without retry (`test_09`).
- HTTP 429 honors Retry-After header within budget (`test_10`).
- Missing grade normalized to `SOURCE_NOT_PROVIDED` (`test_14`).
- Kanpur Dehat quarantined as `OUT_OF_SCOPE_DISTRICT` (`test_18`).
- Delayed active advice withheld / blocked (`test_19`, `test_recommendation_safety_gate.py:test_02`).
- Immutable exclusive write prevents overwrite with `FileExistsError` (`test_20`).
- Partial runs never advance `last_successful_fetch_utc` (`test_21`).
- End-to-end fixture fetch $\to$ archive $\to$ validation $\to$ health output verified (`test_22`).

---

## 5. Reconciliation Arithmetic & Invariance Guarantees

The ingestion client enforces strict disjoint conservation across all batches:
$$\text{records\_fetched} = \text{records\_accepted} + \text{records\_duplicate} + \sum_{k} \text{records\_quarantined}_k$$

Where quarantine categories are mutually exclusive:
1. `INVALID_PRICE_BOUNDS` ($P_{\min} \le 0$ or $P_{\min} > P_{\text{modal}}$ or $P_{\text{modal}} > P_{\max}$)
2. `MALFORMED_DATE` (unparseable date string)
3. `FUTURE_DATED` ($T_{\text{obs}} > T_{\text{ref, IST}}$)
4. `OUT_OF_SCOPE_DISTRICT` (non-approved district or Kanpur Dehat subdivision)
5. `UNKNOWN_MARKET_REVIEW` (unrecognized or review market yard)
6. `CONFLICTING_QUOTE` (divergent prices on identical natural key)
7. `MISSING_REQUIRED_FIELDS` (null mandatory schema keys)

Arithmetic is validated automatically via `DistrictIngestionResult.validate_arithmetic()` and `IngestionCampaignResult.validate_arithmetic()`. Any discrepancy raises an unhandled balance exception.

---

## 6. Policy Changes & Governance Resolutions

1. **Delayed Advice Policy Resolution:**
   - Previous behavior: DELAYED data (3–5 calendar days old) permitted storage advice with a delay notice.
   - Resolved policy: DELAYED data permits **price display** with trade date disclosures, but active commercial storage recommendations are **withheld / blocked** (`is_permitted = False`, `action = "BLOCKED"`). Commercial recommendations require fresh (`CURRENT` $\le 2$ calendar days) data to protect farmers against financial loss.
2. **Review Market & Unit Safety Gates:**
   - Markets with alias status `REVIEW` or observations with unverified units block active commercial recommendations.
3. **Decoupled System Capabilities:**
   - Price display, forecasting eligibility, and economic advisory eligibility are strictly decoupled. Live price arrival does not automatically enable ML forecast serving or commercial storage advice.

---

## 7. Review Debt & Historical Carry-Forwards

Per `documentation/DATA007R_REVIEW.md`:
1. **The 77 Price Differences:** Cause remains UNKNOWN / UNRESOLVED. Retaining identical aliases rules out market mapping as the cause, but does not prove upstream reporting precision or aggregation changes.
2. **Review Market Mapping Naming:** Correctly documented as `Baripaal APMC -> Varipaal` in Kanpur and `Purwa APMC -> Purwa` in Unnao.
3. **Causal Availability Evidence Mode:** `causal_eligibility_sensitivity_v21.json` is the authoritative source for mode-specific breakdowns; CSV contains `verified` mode only.
4. **Local Resource Limits:** Prior executor local full-panel run noted as noncompliant; strict limits ($\le 10$ MB, $\le 50,000$ rows) adhered to in MP-SRC-004.
5. **Panel Invariance:** Panel v2 (`851e7184...`) remains the immutable benchmark. Candidate Panel v2.1 (`a2995369...`) is a versioned research candidate; no v2 model performance scores are inherited by v2.1.
