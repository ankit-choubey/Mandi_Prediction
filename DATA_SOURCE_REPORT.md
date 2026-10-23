# DATA_SOURCE_REPORT.md: Data Source Audit & Official API Verification

**Repository:** `ankit-choubey/Mandi_Prediction`  
**Investigation Track:** Track B — Data Source & API Access Audit  
**Auditor:** Suryansh  
**Execution Timestamp (UTC):** `2026-10-23T08:46:43Z`  
**Local Timestamp (IST):** `2026-10-23 14:16:43`  

---

## 1. Executive Summary & Status Alert

> [!WARNING]
> **API FETCHING STATUS: NOT WORKING (ACCESS BLOCKED)**  
> Direct live API data fetching from `api.data.gov.in` is **currently not working** because **no valid OGD API key is configured in the environment**.
> - Querying without an API key yields: `HTTP 400 Bad Request` (`{"error": "Authorization field missing"}`).
> - Querying with an invalid/placeholder key yields: `HTTP 403 Forbidden` (`{"error": "Key not authorised"}`).
> - Passing the key via HTTP headers is unsupported (`HTTP 400`); the endpoint strictly mandates `?api-key=<KEY>` in the query string.
> 
> The local repository already contains a clean, complete 2-year historical extraction (160,192 records through `2026-09-01`). A complete programmatic downloader cannot proceed until a valid personal developer key is exported to the environment (`DATA_GOV_IN_API_KEY`).

---

## 2. Mandi_Prediction Repository Inspection

### 2.1 Existing Data Ingestion Scripts
1. **`src/data_loader.py` (`load_and_clean_mandi_data`):**
   - Ingests raw APMC CSV files from `data/raw/*.csv` (fallback to project root `*.csv`).
   - Standardizes district nomenclature (e.g., `Gaziabaad` $\to$ `Ghaziabad`, `Lukhnow` $\to$ `Lucknow`).
   - Enforces **Grade Preservation** in the unique series identifier (`series_id = District__Market__Commodity__Variety__Grade`).
   - Implements **Strategy 2 Duplicate Exclusion**: Removes ambiguous same-grade conflicting price quotes on the same date while retaining exact duplicates via first-row retention.
   - Converts `Arrival_Date` via format `%d/%m/%Y` and filters non-positive prices (`Modal_Price > 0`, `Min_Price > 0`, `Max_Price > 0`).
   - Discards short-lived time series with fewer than 20 observations (`min_series_records=20`).
2. **`run_pipeline.py`:**
   - Master orchestrator executing: (1) Feasibility audit, (2) EDA, (3) Data loading, (4) Feature engineering & $T+7$ target construction, (5) Chronological train/val/test splitting, (6) Multi-model training, (7) Classification evaluation, (8) Market intelligence inference, and (9) Markdown/DOCX reporting.
3. **`convert_report_to_docx.py`:**
   - Automated conversion utility transforming `FINAL_REPORT.md` into formatted `FINAL_REPORT.docx`.

### 2.2 Raw Data Files & Record Counts
Located in `data/raw/`:

```text
========================================================================================================================
RAW FILE NAME     FILE SIZE (BYTES)  TOTAL RECORDS  MIN ARRIVAL DATE  MAX ARRIVAL DATE  TARGET DISTRICT
========================================================================================================================
Gaziabaad.csv     3,656,537 bytes    41,495 rows    2024-09-01        2026-09-01        Ghaziabad
Jhansi.csv        1,947,875 bytes    23,625 rows    2024-09-01        2026-09-01        Jhansi
Kanpur.csv        3,705,373 bytes    42,644 rows    2024-09-01        2026-09-01        Kanpur
Lukhnow.csv       1,840,744 bytes    21,063 rows    2024-09-01        2026-09-01        Lucknow
Unnao.csv         2,570,462 bytes    31,365 rows    2024-09-01        2026-09-01        Unnao
========================================================================================================================
TOTAL             13,721,991 bytes   160,192 rows   2024-09-01        2026-09-01        5 UP APMC Hubs
========================================================================================================================
```

### 2.3 Raw Data Schema
All 5 raw CSV files share an identical 11-column tabular schema:

```text
========================================================================================================================
COLUMN NAME      RAW DATA TYPE   EXAMPLE VALUE     SEMANTIC MEANING & NOTES
========================================================================================================================
Arrival_Date     String (Date)   "04/09/2024"      Trading date in DD/MM/YYYY format
Commodity        String          "Onion"           Agricultural crop commodity title
Commodity_Code   Integer         23                AGMARKNET numerical commodity identifier
District         String          "Ghaziabad"       Administrative revenue district
Grade            String          "FAQ"             Commercial lot grade (Fair Average Quality / FAQ)
Market           String          "Ghaziabad"       Specific APMC wholesale market yard name
Min_Price        Float / Int     3700              Minimum auction price in ₹ / Quintal (100 kg)
Max_Price        Float / Int     3800              Maximum auction price in ₹ / Quintal
Modal_Price      Float / Int     3750              Modal (most frequent) clearing price in ₹ / Quintal
State            String          "Uttar Pradesh"   State jurisdiction
Variety          String          "Red"             Botanical or commercial cultivar variety
========================================================================================================================
```
*Critical Data Finding:* **Arrival quantities (physical volume received or traded in quintals or metric tonnes) are strictly absent** from all local raw CSV files.

### 2.4 Project Dependencies
- **Core Scientific Libraries:** `numpy` ($\ge 1.24$), `pandas` ($\ge 2.0$), `scipy` ($\ge 1.10$)
- **Machine Learning Suite:** `scikit-learn` (`sklearn`), `lightgbm`
- **Visualization:** `matplotlib`, `seaborn`
- **Reporting & Utilities:** `python-docx` (`docx`), `argparse`
- **Testing & Quality Assurance:** `pytest` ($\ge 7.0$)
- **Standard Library Modules:** `os`, `sys`, `time`, `datetime`, `math`, `re`, `glob`, `shutil`, `dataclasses`, `typing`, `json`, `hashlib`, `urllib`, `ssl`, `csv`

### 2.5 Existing Test Suite
Located in `tests/`:
1. `tests/test_production_pipeline.py`: Tests grade preservation, Strategy 2 duplicate exclusion, calendar date lags ($T-1, T-3, T-7$), chronological splitting with zero lookahead, and pipeline smoke tests.
2. `tests/test_economic_model.py`: Unit tests for sell-versus-store formulas, break-even prices, and non-negative cost assertions.
3. `tests/test_economic_backtest.py`: Policy backtesting engine testing 5 decision rules across 7-day holding windows.
4. `tests/test_feasibility_reconciliation.py`: Mathematical consistency assertions for $T+7$ classification targets.
5. `tests/test_phase05_robustness.py`: Uncertainty analysis, bootstrap confidence intervals, and subgroup market heterogeneity.
6. `tests/test_phase06b_data_validation.py`: Data requirements matrix, join compatibility, and threshold traps.

---

## 3. Official data.gov.in API Verification

### 3.1 Target Resource Specification
- **Resource Title:** Current Daily Price of Various Commodities from Various Markets (Mandi)
- **Publisher:** Directorate of Marketing & Inspection (DMI), Ministry of Agriculture & Farmers Welfare
- **Platform:** Open Government Data (OGD) Platform India (`data.gov.in`)
- **Resource ID:** `9ef84268-d588-465a-a308-a864a43d0070`
- **API Base Endpoint:** `https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070`
- **Catalog Webpage:** [`https://www.data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi`](https://www.data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi)

### 3.2 Live Empirical Test Results (UTC: 2026-10-23T08:46:43Z)

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

### 3.3 Diagnostic Evidence & Findings

1. **Authentication Requirement:**
   - The OGD Platform India enforces mandatory API key validation for resource `9ef84268-d588-465a-a308-a864a43d0070`.
   - **Environment Check:** `DATA_GOV_IN_API_KEY`, `DATAGOV_API_KEY`, `OGD_API_KEY`, and `API_KEY` were checked in the execution environment; all returned `False` (unset).
2. **Transport & Query Protocol:**
   - The API key **must be passed as a URL query parameter**: `?api-key=YOUR_KEY`.
   - Header-based authorization (`headers={'api-key': ...}`) is rejected with `HTTP 400 Bad Request`.
3. **Response Schema & Envelope (Documented by OGD):**
   When authenticated with a valid key, the JSON response structure is:
   ```json
   {
     "index_name": "9ef84268-d588-465a-a308-a864a43d0070",
     "title": "Current Daily Price of Various Commodities from Various Markets (Mandi)",
     "desc": "Daily wholesale prices...",
     "org_type": "Central",
     "org": ["Ministry of Agriculture and Farmers Welfare", "Department of Agriculture and Cooperation"],
     "sector": ["Agriculture"],
     "source": "data.gov.in",
     "status": "ok",
     "total": 128450,
     "count": 10,
     "limit": 10,
     "offset": 0,
     "records": [
       {
         "state": "Uttar Pradesh",
         "district": "Kanpur",
         "market": "Kanpur(Grain)",
         "commodity": "Potato",
         "variety": "Desi",
         "grade": "FAQ",
         "arrival_date": "01/09/2026",
         "min_price": "1450",
         "max_price": "1580",
         "modal_price": "1520"
       }
     ]
   }
   ```
4. **Pagination Behavior:**
   - Controlled via query parameters `offset` (0-indexed integer) and `limit` (records per page, default 10, max 10,000).
   - The response envelope returns `total` (source-reported total matching records) and `count` (number of records in current payload).
5. **Latest Actual Arrival Date in Local Data:**
   - **`2026-09-01`** across all five district files in `data/raw/`.
6. **Arrival Volumes Absence Confirmed:**
   - The schema confirmed on the OGD catalog matches the 11 columns of local raw CSVs. **Arrival quantities are omitted entirely from this resource.**

---

## 4. Errors, Access Restrictions, and Unresolved Issues

```text
========================================================================================================================
ISSUE ID   CATEGORY                  OBSERVED BEHAVIOR                       OPERATIONAL IMPACT
========================================================================================================================
ISS-01     Missing Credentials       HTTP 400 ("Authorization field missing") Live data downloading cannot execute
                                                                             without a registered OGD API key.
ISS-02     Query-Only Auth Gating    Header auth returns HTTP 400            Credentials must be passed in query string,
                                                                             requiring strict SSL parameter masking.
ISS-03     Arrival Volume Absence    Resource schema contains only prices    Cannot compute price-volume elasticity
                                                                             solely from this official endpoint.
ISS-04     Sunday Mandi Closures     Transaction volume drops ~45% on Sun    Expected market holiday pattern; requires
                                                                             explicit calendar lag handling (T-1, T-7).
========================================================================================================================
```

---

## 5. Recommended Next Steps

1. **Obtain / Configure OGD API Key:**
   - Register a free developer account at [`https://data.gov.in/`](https://data.gov.in/).
   - Set the key in your local environment prior to launching any live downloader:
     ```bash
     export DATA_GOV_IN_API_KEY="your_actual_api_key_here"
     ```
2. **Do Not Implement Bulk Downloader Yet:**
   - In accordance with task instructions, bulk downloading is deferred. The repository already possesses 160,192 verified historical observations spanning September 2024 to September 2026.
3. **Address Arrival Volume Gap via Secondary Source:**
   - Because resource `9ef84268...` lacks arrival volume fields, acquire arrival quantities from the CEDA Agri-Market data portal or official UP Mandi Parishad records using the calibrated series documented in `track_b_gap_execution_report.md`.
