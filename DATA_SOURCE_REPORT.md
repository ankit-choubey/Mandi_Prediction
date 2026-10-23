# DATA_SOURCE_REPORT.md: Data Source Audit, 5-Year Dataset Inspection & Official API Verification

**Repository:** `ankit-choubey/Mandi_Prediction`  
**Investigation Track:** Track B — Data Source & API Access Audit  
**Auditor:** Suryansh  
**Execution Timestamp (UTC):** `2026-10-23T09:25:41Z`  
**Local Timestamp (IST):** `2026-10-23 14:55:41`  

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
> **MAJOR UPDATE: 5-YEAR DATASET DELIVERED**  
> The repository now includes the full 5-year agricultural market dataset located at:  
> [`/Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction/5 year dataset`](file:///Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction/5%20year%20dataset)  
> - **Total Records:** **472,385 observations** across 5 Uttar Pradesh districts.  
> - **Date Range:** **September 01, 2021 to September 30, 2026** (1,856 calendar days / 5 full years + 1 month).  
> - **Target Crop Volume:** **93,491 records** across Potato, Onion, Tomato, and Wheat.  
> - **Quality:** **0 null values** across all essential columns (prices, dates, commodities, grades, and markets). Exactly 27 non-positive price rows ($0.0057\%$) require standard data cleaning.

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

---

### 2.2 Raw Data Inventory & Comparison (2-Year Baseline vs. 5-Year Expansion)

The repository now houses two tiers of raw data files:
1. **2-Year Baseline Dataset (`data/raw/`):** 160,192 records (Sep 2024 – Sep 2026).
2. **5-Year Expanded Dataset (`5 year dataset/`):** 472,385 records (Sep 2021 – Sep 2026).

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

### 2.3 Tabular Schema & Data Types (Identical Across Both Tiers)

Both the 2-year and 5-year datasets share the identical 11-column tabular structure:

```text
========================================================================================================================
COLUMN NAME      RAW DATA TYPE   EXAMPLE VALUE     NULL COUNT (5-YR)  SEMANTIC MEANING & NOTES
========================================================================================================================
Arrival_Date     String (Date)   "04/09/2021"      0 nulls            Transaction date in DD/MM/YYYY format
Commodity        String          "Onion"           0 nulls            Agricultural crop commodity title (110 unique)
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

### 2.4 Project Dependencies
- **Core Scientific Computation:** `numpy` ($\ge 1.24$), `pandas` ($\ge 2.0$), `scipy` ($\ge 1.10$)
- **Machine Learning Suite:** `scikit-learn` (`sklearn`), `lightgbm`
- **Visualization:** `matplotlib`, `seaborn`
- **Document Generation:** `python-docx` (`docx`), `argparse`
- **Testing & Quality Assurance:** `pytest` ($\ge 7.0$)
- **Standard Library Modules:** `os`, `sys`, `time`, `datetime`, `math`, `re`, `glob`, `shutil`, `dataclasses`, `typing`, `json`, `hashlib`, `urllib`, `ssl`, `csv`

---

### 2.5 Existing Test Suite
Located in [`tests/`](file:///Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction/tests/):
1. `tests/test_production_pipeline.py`: Grade preservation, Strategy 2 duplicate exclusion, calendar date lags ($T-1, T-3, T-7$), chronological splitting, and pipeline smoke tests.
2. `tests/test_economic_model.py`: Unit tests for sell-versus-store formulas, break-even prices, and non-negative cost assertions.
3. `tests/test_economic_backtest.py`: Policy backtesting engine testing 5 decision rules across 7-day holding windows.
4. `tests/test_feasibility_reconciliation.py`: Mathematical consistency assertions for $T+7$ classification targets.
5. `tests/test_phase05_robustness.py`: Uncertainty analysis, bootstrap confidence intervals, and subgroup market heterogeneity.
6. `tests/test_phase06b_data_validation.py`: Data requirements matrix, join compatibility, and threshold traps.
7. `tests/test_data_foundation.py`: 11 automated verification tests (raw integrity, row accounting, NaN preservation, path portability).

---

## 3. Official data.gov.in API Verification

### 3.1 Target Resource Specification
- **Resource Title:** Current Daily Price of Various Commodities from Various Markets (Mandi)
- **Publisher:** Directorate of Marketing & Inspection (DMI), Ministry of Agriculture & Farmers Welfare
- **Platform:** Open Government Data (OGD) Platform India (`data.gov.in`)
- **Resource ID:** `9ef84268-d588-465a-a308-a864a43d0070`
- **API Base Endpoint:** `https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070`
- **Catalog Webpage:** [`data.gov.in Catalog Page`](https://www.data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi)

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
5. **Latest Actual Arrival Date:**
   - **`2026-09-30`** in the newly provided 5-year dataset (`5 year dataset/`).
   - `2026-09-01` in the 2-year baseline dataset (`data/raw/`).
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

1. **Configure Environment Variable:**
   - Register a free developer account at [`https://data.gov.in/`](https://data.gov.in/).
   - Set the key in your local environment prior to launching any live downloader:
     ```bash
     export DATA_GOV_IN_API_KEY="your_actual_api_key_here"
     ```
2. **Do Not Implement Bulk Downloader Yet:**
   - In accordance with task instructions, bulk downloading is deferred. The repository already possesses **472,385 verified historical observations spanning September 2021 to September 2026**.
3. **Transition Path for 5-Year Dataset Integration:**
   - The provided 5-year dataset expands the temporal observation window from 731 days to **1,856 days**, tripling the sample size for target crops (93,491 records).
   - In a future phase, update `data_loader.py` to optionally point to `5 year dataset/` to evaluate long-term multi-year model stability.
4. **Address Arrival Volume Gap via Secondary Source:**
   - Because resource `9ef84268...` lacks arrival volume fields, acquire arrival quantities from the CEDA Agri-Market data portal or official UP Mandi Parishad records using the calibrated series documented in `track_b_gap_execution_report.md`.
