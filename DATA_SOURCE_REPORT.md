# DATA_SOURCE_REPORT.md: Data Source Audit, 5-Year Dataset Inspection, API Verification & End-to-End Pipeline Audit

**Repository:** `ankit-choubey/Mandi_Prediction`  
**Investigation Track:** Track B — Data Source, API Verification & End-to-End Pipeline Audit  
**Auditor / Investigator:** Suryansh  
**Execution Timestamp (UTC):** `2026-10-23T13:30:15Z`  
**Verification Status:** **100% VERIFIED** (88/88 Automated Tests Passing)  

---

## 1. Executive Summary & Critical Status Alerts

> [!WARNING]
> **API FETCHING STATUS: NOT WORKING (ACCESS BLOCKED)**  
> Direct live API data fetching from `api.data.gov.in` is **currently blocked / not working** because **no valid OGD API key is configured in the environment**:
> - **Query without API key:** `HTTP 400 Bad Request` $\implies$ `{"error": "Authorization field missing"}`
> - **Query with invalid / dummy key:** `HTTP 403 Forbidden` $\implies$ `{"error": "Key not authorised"}`
> - **Query with header authentication:** `HTTP 400 Bad Request` $\implies$ The platform strictly requires the key to be passed as a URL query parameter (`?api-key=...`).
> 
> To enable live fetching, you must export a valid personal API key obtained from [data.gov.in](https://data.gov.in/):
> ```bash
> export DATA_GOV_IN_API_KEY="your_actual_ogd_api_key_here"
> ```

> [!NOTE]
> **MAJOR MILESTONE: 5-YEAR DATASET DELIVERED, VALIDATED & PUBLISHED**  
> The repository now houses the complete 5-year agricultural market dataset located at:  
> [`5 year dataset/`](file:///Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction/5%20year%20dataset)  
> - **Total Raw Records:** **472,385 observations** across 5 Uttar Pradesh districts.  
> - **Date Range:** **September 01, 2021 to September 30, 2026** (1,856 calendar days / 5 full years + 1 month).  
> - **Target Crop Volume:** **93,491 raw records** across Potato, Onion, Tomato, and Wheat (tripled from 35,531 rows).  
> - **Published Clean Panel:** **462,350 clean observations** across 1,297 active canonical series, published atomically to [`data/processed/mandi_5year_validated.csv`](file:///Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction/data/processed/mandi_5year_validated.csv).
> - **Evidence-Preserving Quarantine:** 27 invalid records (with 15 Min > Max violations) and 2,936 conflicting price records segregated into [`data/quarantine/`](file:///Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction/data/quarantine).

---

## 2. Mandi_Prediction Repository Inspection

### 2.1 Existing Ingestion & Processing Scripts
1. **`src/data_validator.py` (`MandiDataValidator`):**
   - Natural-key validator (`State + District + Market + Commodity + Variety + Grade + Arrival_Date`).
   - Detects impossible price relationships (`Min > Max`, `Modal > Max`, `Modal < Min`) and flags them for quarantine rather than silently swapping.
   - Applies Strategy 2 (DEC-008) conflict isolation, preserves raw values in quarantine, and publishes atomically.
2. **`src/data_pipeline.py` (`MandiDataPipeline`):**
   - High-throughput ingestion engine with case-insensitive column aliasing, multi-format date parsing, and cryptographic manifest generation (`processing_manifest.json`).
3. **`src/data_loader.py` (`load_and_clean_mandi_data`):**
   - Seamless loader supporting 2-year raw baseline, direct 5-year raw folder, and pre-processed validated files with 100% backward compatibility.
4. **`run_pipeline.py`:**
   - Master orchestrator for feasibility audit, EDA, data loading, lag engineering ($T-1, T-3, T-7$), multi-model training, and classification evaluation.

---

### 2.2 Raw Data Inventory & Comparison (2-Year Baseline vs. 5-Year Expansion)

```text
===================================================================================================================================
DISTRICT    2-YEAR RAW FILE (data/raw/)     5-YEAR EXPANDED FILE (5 year dataset/)  DATE RANGE (5-YEAR)      5-YEAR TARGET CROPS
===================================================================================================================================
Ghaziabad   Gaziabaad.csv (41,495 rows)     GHAZIABAD.csv (132,478 rows / 11.6 MB)  2021-09-01 to 2026-09-30 Potato: 5,453 | Onion: 5,152
                                                                                                             Tomato: 5,095 | Wheat: 3,818
Jhansi      Jhansi.csv    (23,625 rows)     JHANSI.csv    (83,972 rows  / 6.9 MB)   2021-09-01 to 2026-09-30 Potato: 6,790 | Onion: 7,329
                                                                                                             Tomato: 6,260 | Wheat: 6,234
Kanpur      Kanpur.csv    (42,644 rows)     KANPUR.csv    (113,319 rows / 9.8 MB)   2021-09-01 to 2026-09-30 Potato: 5,847 | Onion: 4,306
                                                                                                             Tomato: 4,575 | Wheat: 7,229
Lucknow     Lukhnow.csv   (21,063 rows)     LUKHNOW.csv   (54,876 rows  / 4.8 MB)   2021-09-01 to 2026-09-30 Potato: 1,679 | Onion: 1,632
                                                                                                             Tomato: 1,553 | Wheat: 3,184
Unnao       Unnao.csv     (31,365 rows)     UNNAO.csv     (87,740 rows  / 7.1 MB)   2021-09-01 to 2026-09-30 Potato: 4,243 | Onion: 4,046
                                                                                                             Tomato: 3,917 | Wheat: 5,149
===================================================================================================================================
TOTALS      5 files: 160,192 rows (13.7 MB) 5 files: 472,385 rows (40.3 MB)         2021-09-01 to 2026-09-30 4 Crops: 93,491 records
===================================================================================================================================
```

---

### 2.3 Tabular Schema & Data Types

Both the 2-year and 5-year datasets share the identical 11-column tabular structure:

```text
========================================================================================================================
COLUMN NAME      RAW DATA TYPE   EXAMPLE VALUE     NULL COUNT (5-YR)  SEMANTIC MEANING & NOTES
========================================================================================================================
Arrival_Date     String (Date)   "04/09/2021"      0 nulls            Transaction date in DD/MM/YYYY format
Commodity        String          "Onion"           0 nulls            Agricultural crop commodity title (139 unique)
Commodity_Code   Integer         23                0 nulls            AGMARKNET numerical commodity identifier
District         String          "Ghaziabad"       0 nulls            Administrative revenue district
Grade            String          "FAQ"             0 nulls            Commercial lot grade (FAQ, Medium, Large)
Market           String          "Ghaziabad"       0 nulls            Specific APMC wholesale market yard name
Min_Price        Float / Int     3700.0            0 nulls            Minimum auction price in ₹ / Quintal (100 kg)
Max_Price        Float / Int     3800.0            0 nulls            Maximum auction price in ₹ / Quintal
Modal_Price      Float / Int     3750.0            0 nulls            Modal (most frequent) clearing price in ₹ / Quintal
State            String          "Uttar Pradesh"   0 nulls            State jurisdiction
Variety          String          "Red"             0 nulls            Botanical or commercial cultivar variety
========================================================================================================================
```

> **Key Negative Finding:** **Daily arrival volumes (quantities traded or received in quintals or metric tonnes) are strictly absent** across both the 2-year and 5-year raw CSV files, confirming that the underlying OGD resource (`9ef84268-d588-465a-a308-a864a43d0070`) exclusively publishes wholesale prices.

---

### 2.4 Existing Test Suite Summary

Located in [`tests/`](file:///Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction/tests/) (**88 automated tests passing**):
1. `tests/test_data_validation.py` (7 tests): Impossible price relationships, natural key conflicts, non-positive price quarantine, district typos, idempotence, atomic publishing safety, raw preservation.
2. `tests/test_data_pipeline.py` (13 tests): Ingestion, empty files, malformed rows, missing columns, manifest accounting, target crops filter, CLI execution.
3. `tests/test_data_foundation.py` (11 tests): Provenance verification, row accounting, NaN preservation, zero machine-specific paths.
4. `tests/test_production_pipeline.py` (7 tests): Grade preservation, lag leakage prevention, chronological splitting.
5. `tests/test_economic_model.py` (19 tests): Unit economics, break-even boundaries, non-negative storage costs.
6. `tests/test_economic_backtest.py` (12 tests): 7-day holding window decision rules.
7. `tests/test_feasibility_reconciliation.py` (5 tests): $T+7$ classification target consistency.
8. `tests/test_phase05_robustness.py` (6 tests): Bootstrap confidence intervals and subgroup stability.
9. `tests/test_phase06b_data_validation.py` (8 tests): Data requirements matrix, join traps.

---

## 3. Official data.gov.in API Verification

### 3.1 Target Resource Specification
- **Resource Title:** Current Daily Price of Various Commodities from Various Markets (Mandi)
- **Publisher:** Directorate of Marketing & Inspection (DMI), Ministry of Agriculture & Farmers Welfare
- **Platform:** Open Government Data (OGD) Platform India (`data.gov.in`)
- **Resource ID:** `9ef84268-d588-465a-a308-a864a43d0070`
- **API Base Endpoint:** `https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070`

### 3.2 Live Empirical Test Results (UTC: 2026-10-23T09:25:41Z)

```text
========================================================================================================================
PROBE SCENARIO             REQUEST DETAILS                                      HTTP STATUS   RESPONSE BODY / ERROR
========================================================================================================================
Test 1: No API Key         GET /resource/9ef84268...?format=json&limit=10       400 Bad Req   {"error": "Authorization field missing"}
Test 2: Dummy / Bad Key    GET /resource/9ef84268...?api-key=[REDACTED]...     403 Forbidden {"error": "Key not authorised"}
Test 3: Header Auth        GET /resource/9ef84268... (Header: 'api-key')        400 Bad Req   {"error": "Authorization field missing"}
Test 4: Catalog Web Page   GET https://www.data.gov.in/resource/...            200 OK        HTML Document (1,120,997 bytes)
========================================================================================================================
```

---

## 4. End-to-End Pipeline Verification & Empirical Audit

### 4.1 Measured Input and Output Cryptographic SHA-256 Ledger

```text
========================================================================================================================
FILE TYPE       FILE NAME / PATH                                     SIZE (BYTES)  SHA-256 CHECKSUM
========================================================================================================================
Raw Source 1    5 year dataset/GHAZIABAD.csv                         11,616,749    17d2ccca09866a8272fa290e7c0c1816c74b6fc9dd56607548656ade4b8787ef
Raw Source 2    5 year dataset/JHANSI.csv                             6,904,178    179d7d330914b7e130673f83c3931b5a2cc1935c5555a19e4f417cd73ed8a2e3
Raw Source 3    5 year dataset/KANPUR.csv                             9,843,548    c89551a32fcd4cb02d4bc85cb50de532b2478d9806fb4d8cd9ae859bf1b06d7f
Raw Source 4    5 year dataset/LUKHNOW.csv                            4,809,204    19bb57961c67cc439e2798ddb23d63cade9320bdb8659929f656a79d31f59e8a
Raw Source 5    5 year dataset/UNNAO.csv                              7,141,707    e64405faf71070193b10a4477a8c259ad08eae6c9051872dbc545e507c115fc4
------------------------------------------------------------------------------------------------------------------------
Clean Published data/processed/mandi_5year_validated.csv             63,435,793    20a198682c3f5382a25276a916e258f8fef4aa777c9c6d1cebe6e7c03a206dfa
Invalid Quaran. data/quarantine/quarantined_invalid_records.csv          11,260    c45ee0c46b1c2b53b84177372d8e484c264d1736bca42b8eec86ad60fc8aa8ad
Conflict Quaran.data/quarantine/quarantined_conflicting_records.csv   1,215,840    691c7ae93d58434c442e3a89e47265910be226e6ec3505cf4e82b71a2da38e88
Audit Report    VALIDATION_REPORT.md                                      6,262    b127ba2d075ebf17c46955a9b74304856a297e64177b963628bbdc6d790757e7
Manifest JSON   data/processed/validation_summary.json                    3,865    3fece0dd59a95393ce0dca44ba187f54c9d7bf5495cfa4911d331feeb9c9f4d7
========================================================================================================================
```

---

### 4.2 Comprehensive Row Reconciliation Ledger

$$\text{Total Raw Rows (472,385)} = \text{Clean Accepted (462,350)} + \text{Quarantined Invalid (27)} + \text{Quarantined Conflicts (2,936)} + \text{Low-Obs Dropped (7,072)}$$

```text
========================================================================================================================
PROCESSING STAGE / CATEGORY                   ROW COUNT   PERCENTAGE OF RAW   STATUS & DISPOSITION
========================================================================================================================
1. Total Raw Rows Ingested                      472,385             100.00%   Input baseline across 5 raw district CSVs
2. Structurally Valid Parsed Rows               472,358              99.99%   Passed dates, types, and column checks
3. Quarantined Structurally Invalid Records          27               0.01%   Quarantined to quarantined_invalid_records.csv
   - Min_Price > Max_Price (Max == 0.0)              15                       Flagged: IMP_RELATIONSHIP_MIN_GT_MAX
   - Modal_Price > Max_Price (Modal > Ceiling)       22                       Flagged: IMP_RELATIONSHIP_MODAL_GT_MAX
   - Non-Positive Prices (<= 0)                      34 instances             Flagged: PRICE_NON_POSITIVE
4. Quarantined Conflicting Price Records          2,936               0.62%   Quarantined to quarantined_conflicting_records.csv
   - Same-grade series dates with price clashes   1,457 dates                 Strategy 2 / DEC-008 100% label purity
5. Exact Identical Duplicates Deduplicated            0               0.00%   Zero redundant identical rows in 5-yr raw files
6. Low-Observation Series Filter (< 20 obs)       7,072               1.50%   Series with insufficient historical depth
7. Final Published Clean Observations           462,350              97.88%   Published atomically with 100% natural-key uniqueness
========================================================================================================================
```

---

### 4.3 Pipeline Verification Checklist & Evidence

| Verification Assertion | Measured Result | Audit Evidence & Notes |
| :--- | :--- | :--- |
| **All Expected Files Discovered?** | **YES (5/5 files)** | `GHAZIABAD.csv`, `JHANSI.csv`, `KANPUR.csv`, `LUKHNOW.csv`, `UNNAO.csv` found and loaded. |
| **District Coverage Complete?** | **YES (5/5 districts)** | Ghaziabad (132,478), Jhansi (83,972), Kanpur (113,319), Lucknow (54,876), Unnao (87,740). |
| **Date Range Spanned?** | **1,856 Calendar Days** | Earliest: `2021-09-01` \| Latest: `2026-09-30` (5 full years + 1 month). |
| **Reproducibility & Idempotency?** | **VERIFIED (100%)** | Repeated runs generate identical accepted rows (462,350) and identical SHA-256 digests. |
| **Natural-Key Uniqueness?** | **VERIFIED (0 duplicates)** | `df.duplicated(subset=NATURAL_KEY_COLUMNS).sum() == 0` on published clean dataset. |
| **Source File Immutability?** | **VERIFIED (100% untouched)**| Raw files opened read-only. SHA-256 before == SHA-256 after pipeline execution. |
| **Fail-Safe Atomic Publishing?** | **VERIFIED (Zero corruption)**| Output staged to `.staging` file; verified prior to atomic move. Existing valid files preserved on error. |
| **Absence of Synthetic Records?** | **VERIFIED (Clean empirical)**| Synthetic arrival scenarios quarantined in `suryansh - work/.../quarantine/`. Core data is 100% empirical. |
| **Credential Safety?** | **VERIFIED (Safe)** | No API keys committed or exposed. Checked `DATA_GOV_IN_API_KEY` in environment. |
| **Automated Test Results?** | **88 / 88 PASSED** | `tests/test_data_validation.py` (7/7), `tests/test_data_pipeline.py` (13/13), baseline (68/68). |

---

## 5. Errors, Access Restrictions, and Known Limitations

```text
========================================================================================================================
ISSUE ID   CATEGORY                  OBSERVED BEHAVIOR                       OPERATIONAL IMPACT & REMEDIATION
========================================================================================================================
ISS-01     Missing Credentials       HTTP 400 ("Authorization field missing") Live downloading cannot execute without
                                                                             exporting DATA_GOV_IN_API_KEY.
ISS-02     Query-Only Auth Gating    Header auth returns HTTP 400            Credentials must be passed in query string (?api-key=...).
ISS-03     Arrival Volume Absence    Resource schema contains only prices    Cannot compute price-volume elasticity from this resource.
                                                                             Alternative: CEDA quantities API (see DATA_SOURCE_ALTERNATIVES.md).
ISS-04     Max_Price Zero Anomaly    15 records have Min > 0 but Max == 0.0  Quarantined to quarantined_invalid_records.csv.
ISS-05     Conflicting Price Quotes  2,936 rows have differing prices on     Quarantined to quarantined_conflicting_records.csv under DEC-008.
                                     same series-date
========================================================================================================================
```

---

## 6. Exact Execution Commands

```bash
# 1. Run Data Validation & Safe Deduplication Engine
python3 -m src.data_validator \
  --input-dir "5 year dataset" \
  --output-dir "data/processed" \
  --quarantine-dir "data/quarantine" \
  --output-filename "mandi_5year_validated.csv" \
  --report-filename "VALIDATION_REPORT.md" \
  --min-series-records 20

# 2. Run Production Data Loading Pipeline
python3 -m src.data_pipeline \
  --input-dir "5 year dataset" \
  --output-dir "data/processed" \
  --output-filename "mandi_5year_processed.csv" \
  --manifest-filename "processing_manifest.json" \
  --min-series-records 20

# 3. Run Automated Unit Test Suite (88 tests)
python3 -m pytest tests/ -v
```
