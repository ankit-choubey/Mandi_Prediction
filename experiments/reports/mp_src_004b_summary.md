# MP-SRC-004B Summary — Truthful Provenance, Conflict Safety, Persistent Receipts & Dataset-First Ingestion

**Task ID:** `MP-SRC-004B` (Steps 3–5 Foundations)
**Date:** 2026-11-12 IST
**Baseline Git Commit:** `ce780f5772ed640eab1d2071f7427fcd49a523df`
**Operational Status:** `IMPLEMENTED + TESTED + IMPORT-VERIFIED + LIVE-UNVERIFIED (KEY_MISSING)`
**Target Live Resource:** `https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070`
**Credential Check:** `OGD_API_KEY` absent from local environment and `.env`. Offline implementation, full contract v1.2.0, standard library streaming transport, file import CLI, conflict safety, honest price bounds, immutable snapshot engine, and unit test suite completed. Live verification campaign blocked pending local key configuration.
**Standing Owner Rule:** Zero synthetic datasets, simulated operational feeds, model-training rows, or storage scenarios without prior explanation and explicit owner approval.

---

## 1. Executive Summary & Structured Status

### WHAT WE ACHIEVED

1. **Truthful Source Provenance (`DataMode` Enum & Namespace Separation):**
   - Implemented explicit provenance tracking via `DataMode`:
     - `LIVE_FETCH`: Authenticated real-network campaign against data.gov.in. Only mode that can set `is_live_verified=True` or advance `last_successful_campaign.json`.
     - `HISTORICAL_REPLAY`: Replay of preserved past observations preserving original trade and retrieval timestamps.
     - `TEST_FIXTURE`: Offline test harnesses and mock transports. Mocks claiming `LIVE_FETCH` raise `ValueError`. Writes to `data/fixture_snapshots/`.
     - `FILE_IMPORT`: Owner-selected downloaded official APMC CSV/Excel files (`data/raw/*.csv`). Never sets `is_live_verified=True` and never advances live-success index.
     - `SYNTHETIC_SIMULATION`: Reserved mode strictly requiring prior explanation and explicit owner approval. Zero synthetic rows generated.
   - Carried `data_mode` and `is_synthetic` through all records, page receipts, campaign results, health reports, and capabilities.

2. **Dataset-First Default Ingestion (`execute_file_import` & CLI `--import-file`):**
   - Built a deterministic file import path through the identical validation, conflict-safety, and snapshot persistence engine.
   - Enforced local processing bounds: $\le 10$ MB file size and $\le 50,000$ rows per file.
   - Computes SHA-256 of imported files and archives immutable `PageReceipt` and `run_receipt.json` under `data/imported_snapshots/`.
   - Verified on all 5 official observed APMC raw archives in `data/raw/` (Gaziabaad, Jhansi, Kanpur, Lukhnow, Unnao), totaling 160,192 rows, executing in $< 5$ seconds locally.

3. **Order-Invariant Conflict Safety:**
   - Repaired conflicting quote logic: when two or more records in a batch share an identical natural key $(date, district, market, commodity, variety, grade)$ with divergent prices $(P_1 \ne P_2)$, **ALL** members of the conflict group are quarantined as `RecordDisposition.CONFLICTING_QUOTE`.
   - Retroactively removes previously accepted or duplicate records belonging to the conflict group and decrements counts accurately.
   - Recomputes observation date range strictly from remaining accepted records.
   - Mathematically verified: all permutations of conflict groups (`[A,A,B]`, `[A,B,B]`, `[B,A,A]`, `[A,B,A]`) yield identical outcomes ($0$ accepted, $0$ duplicates, $3$ quarantined, $3$ fetched, arithmetic balanced).

4. **Honest Price Bounds (Modal Substitution Eliminated):**
   - Modal price substitution ($P_{\min} = P_{\text{modal}}$) is strictly forbidden.
   - Missing `min_price` or `max_price` is preserved as `None` and quarantined as `MISSING_REQUIRED_FIELDS` with explicit reason.
   - Non-finite (`NaN`, `Inf`), non-positive ($\le 0$), and inverted bounds ($P_{\min} > P_{\text{modal}}$ or $P_{\text{modal}} > P_{\max}$) quarantined as `INVALID_PRICE_BOUNDS`. Original raw fields preserved intact.

5. **Production Networking via Standard Library:**
   - Implemented `UrllibHttpTransport` using `urllib.request` with bounded chunked streaming (aborts if response exceeds 10 MB).
   - Sanitizes exact key values and sensitive query parameters in exceptions, URLs, and receipts without leaking sentinels.

6. **Collision-Safe Persistence & Fallback Architecture:**
   - Microsecond-resolution UTC run IDs (`%Y%m%dT%H%M%S_%fZ`).
   - Exclusive file creation (`mode 'x'`) enforced for both `page_<offset:05d>.json` and `run_receipt.json`. Re-execution collisions fail closed with `FileExistsError`.
   - Atomic pointer `last_successful_campaign.json` updated strictly when `campaign.is_live_verified == True`.
   - Implemented `load_prior_validated_snapshot` to recover prior verified campaigns as labeled fallback with original trade/retrieval timestamps.

7. **Contract & Runbook Updates:**
   - Bumped contract to version `1.2.0` in `data/reference/live_source_contract.json` with `FILE_IMPORT` mode and conflict/bounds rules.
   - Updated `documentation/LIVE_INGESTION_RUNBOOK.md` with complete operator instructions for dataset import, live preflight, exit codes, and fallback handling.

8. **Comprehensive Pytest Verification:**
   - 34 dedicated tests in `tests/test_live_price_ingestion.py` (covering provenance mismatch, permutations, cross-page conflicts, honest bounds, collision safety, fallback loader, file import provenance, idempotent runs, and CLI).
   - Entire repository test suite passes: **251 passed in 9.03s** (0 failures).

---

### WHAT IS STILL OPEN

1. **Real Network Verification Campaign on data.gov.in API:**
   - Blocked due to `KEY_MISSING` (`OGD_API_KEY` not configured in local environment or `.env`).
   - The client reports exit code `2` with `KEY_MISSING`. Offline implementation is complete and verified.
2. **Review Market Field Verification:**
   - `Purwa APMC` (Unnao) and `Baripaal APMC -> Varipaal` (Kanpur) remain classified as `UNMAPPED/REVIEW`.
3. **The 77 Feb–Mar 2026 Price Discrepancies:**
   - Root cause remains UNRESOLVED between monthly export and daily panel feed; requires source-level inquiry.
4. **Scheduler Activation:**
   - Standalone background cron/launchd automations remain INACTIVE pending explicit owner activation.

---

### WHAT NEXT

1. **Dataset-First Operational Ingestion:**
   - Run manual file imports on authorized raw APMC files using `python3 -m src.live_price_ingestion --import-file data/raw/<District>.csv`.
2. **Optional Live Verification Campaign:**
   - If owner provides `OGD_API_KEY` in local `.env`, execute:
     `python3 -m src.live_price_ingestion --district all`
     (Authorized limit: 1 run, $\le 50$ requests, $\le 25,000$ rows).
3. **Step 2 Dataset Finalization:**
   - Proceed with market identity consolidation (v2.1 policy) before any remote model training in Step 6.

---

## 2. Tested vs Live-Verified Capabilities

| Capability | Implementation Status | Tested via Mock / Fixture | Tested via File Import | Live-Verified on API | Safety / Governance Policy |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **HTTP Transport (Urllib stdlib)** | IMPLEMENTED | YES | N/A | UNVERIFIED (`KEY_MISSING`) | Bounded streaming $\le 10$ MB |
| **Secret Sanitization** | IMPLEMENTED | YES | YES | UNVERIFIED | Sentinel and real keys never logged |
| **Pagination Loop** | IMPLEMENTED | YES | N/A | UNVERIFIED | Detects hash collision, total shifts |
| **Order-Invariant Conflict Safety**| IMPLEMENTED | YES | YES | UNVERIFIED | All divergent quotes quarantined |
| **Honest Price Bounds** | IMPLEMENTED | YES | YES | UNVERIFIED | Modal substitution strictly eliminated |
| **Missing Grade Normalization** | IMPLEMENTED | YES | YES | UNVERIFIED | `SOURCE_NOT_PROVIDED` (never FAQ) |
| **Scope Quarantine (Kanpur Dehat)**| IMPLEMENTED | YES | YES | UNVERIFIED | Administrative subdivision excluded |
| **Collision-Safe Persistence** | IMPLEMENTED | YES | YES | UNVERIFIED | Exclusive write `mode 'x'` |
| **Dataset File Import** | IMPLEMENTED | YES | YES (`160,192` rows) | N/A | `FILE_IMPORT` provenance, no live flag |
| **Persistent Snapshot Fallback**| IMPLEMENTED | YES | YES | UNVERIFIED | Preserves original timestamps |
| **Commercial Advice Safety Gate** | IMPLEMENTED | YES | YES | UNVERIFIED | Blocked on live/imported data |

---

## 3. Dataset-First Evidence Table (Real APMC Raw Files)

All five official observed APMC raw archives in `data/raw/` were evaluated against the production ingestion engine:

| Source File | District | Size (MB) | Total Rows | Accepted | Duplicates | Quarantined | Arithmetic Balanced | Observation Date Range |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `Gaziabaad.csv` | Ghaziabad | 3.49 MB | 41,495 | 40,654 | 237 | 604 | YES ($41495 = 40654+237+604$) | 2024-09-01 to 2026-09-01 |
| `Jhansi.csv` | Jhansi | 1.86 MB | 23,625 | 23,066 | 189 | 370 | YES ($23625 = 23066+189+370$) | 2024-09-01 to 2026-09-01 |
| `Kanpur.csv` | Kanpur | 3.53 MB | 42,644 | 40,373 | 242 | 2,029 | YES ($42644 = 40373+242+2029$) | 2024-09-01 to 2026-09-01 |
| `Lukhnow.csv` | Lucknow | 1.76 MB | 21,063 | 20,233 | 82 | 748 | YES ($21063 = 20233+82+748$) | 2024-09-01 to 2026-09-01 |
| `Unnao.csv` | Unnao | 2.45 MB | 31,365 | 29,936 | 115 | 1,314 | YES ($31365 = 29936+115+1314$) | 2024-09-01 to 2026-09-01 |
| **TOTAL** | **5 Districts** | **13.09 MB** | **160,192** | **154,262** | **865** | **5,065** | **YES (100% Balanced)** | **2-Year APMC Panel** |

*Note: Individual file imports adhere to $\le 10$ MB and $\le 50,000$ rows local processing limits.*

---

## 4. Conflict Group Permutation Proof

For any natural key $K = (date, district, market, commodity, variety, grade)$ with quotes $A = (550, 600, 575)$ and $B = (600, 700, 650)$:

$$\text{Fetched}(3) = \text{Accepted}(0) + \text{Duplicates}(0) + \text{Quarantined}(3)$$

| Permutation | Initial Evaluation | Conflicting Observation | Retroactive Action | Final Accepted | Final Duplicates | Final Quarantined |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `[A, A, B]` | $A$ accepted, $A$ duplicate | $B$ divergent | $A_1, A_2$ removed, all 3 quarantined | 0 | 0 | 3 |
| `[A, B, B]` | $A$ accepted | $B$ divergent | $A_1$ removed, $B_1$ quarantined, $B_2$ quarantined | 0 | 0 | 3 |
| `[B, A, A]` | $B$ accepted | $A$ divergent | $B_1$ removed, $A_1$ quarantined, $A_2$ quarantined | 0 | 0 | 3 |
| `[A, B, A]` | $A$ accepted | $B$ divergent | $A_1$ removed, $A_2$ incoming to conflicted key quarantined | 0 | 0 | 3 |

All permutations yield identical output state, ensuring strict order-invariance.

---

## 5. Verification Test Suite Receipts

```
============================= test session starts ==============================
platform darwin -- Python 3.14.0, pytest-9.1.1, pluggy-1.6.0
rootdir: /Users/theankit/Documents/AK/Projects/Mandi_Prediction
plugins: anyio-4.11.0
collected 251 items

tests/test_baselines.py ........                                         [  3%]
tests/test_data_foundation.py ...........                                [  7%]
tests/test_data_pipeline.py ..............                               [ 13%]
tests/test_data_validation.py .......                                    [ 15%]
tests/test_economic_backtest.py ............                             [ 20%]
tests/test_economic_model.py ...................                         [ 28%]
tests/test_fc006_audit.py ...............                                [ 34%]
tests/test_feasibility_reconciliation.py .....                           [ 36%]
tests/test_identity_comparison.py ...................                    [ 43%]
tests/test_identity_policy_v21.py ...................                    [ 51%]
tests/test_ingest_agmarknet_arrivals.py ..                               [ 52%]
tests/test_ingest_arrivals_immutability.py ...................           [ 59%]
tests/test_live_price_ingestion.py ..................................    [ 73%]
tests/test_market_identity.py ............                               [ 78%]
tests/test_operational_output.py .................                       [ 84%]
tests/test_phase05_robustness.py ......                                  [ 87%]
tests/test_phase06b_data_validation.py ........                          [ 90%]
tests/test_production_pipeline.py .......                                [ 93%]
tests/test_recommendation_safety_gate.py .................               [100%]

============================= 251 passed in 9.03s ==============================
```
