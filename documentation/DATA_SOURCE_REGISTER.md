# Data Source Register & Ingestion Evidence

**Repository:** `ankit-choubey/Mandi_Prediction`  
**Document ID:** `DATA_SOURCE_REGISTER`  
**Established Under Task:** `MP-DATA-003A`  
**Last Updated:** 2026-11-12  
**Baseline Git Commit:** `dcdbe34e5489cc13e54e8607afd327ecbb64a981`  

---

## 1. Governance Principles & Verification Framework

All datasets stored, processed, or evaluated in this repository are audited against the **Six Verification Dimensions** established in [`documentation/MODEL_AND_MATH_VALIDATION.md`](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/documentation/MODEL_AND_MATH_VALIDATION.md#L134-L144):

1. **`provenance`:** Upstream institutional source, publisher identity, authentic domain origin, and verifiable retrieval receipts.
2. **`quality`:** Schema integrity, physical bounds compliance ($P_{\min} \le P_{\text{modal}} \le P_{\max}$), null rate, and date parsing consistency.
3. **`availability`:** Endpoint uptime, pagination stability, public access terms, and offline persistence.
4. **`usage_rights`:** Formal legal licence (e.g. NDSAP / open data portal terms, to be verified on the portal), commercial redistribution terms, and mandatory attribution rules.
5. **`data_nature`:** Categorization as `EMPIRICAL_OBSERVATION` (actual auction transactions), `OFFICIAL_STATISTICS` (published government aggregates), `DERIVED_FEATURE` (engineered inputs), or `SCENARIO_ASSUMPTION` (illustrative simulation parameter).
6. **`freshness`:** Calendar lag between the newest observation timestamp and the reference execution date.

> [!IMPORTANT]
> **Cryptographic Integrity vs. Institutional Origin Authenticity:**  
> A SHA-256 cryptographic hash proves strictly that a local byte stream on disk has not suffered corruption, truncation, or silent alteration since hashing. It provides **zero proof** that the payload originated from an authentic government body or reflects genuine transactions. No source is designated "official" or "verified" without documented, external retrieval evidence.

---

## 2. Master Data Source Register Table

The following register documents every data source group present in the repository:

| Source Group / Path Pattern | Git Status | Schema (Key Columns) | Grain | Units (Header Evidence) | Date Range | Rows | Provenance Status | Retrieval Evidence | Licence Status | Unresolved Questions |
|---|---|---|---|---|---|---|---|---|---|---|
| **Agmarknet Arrivals Reports (Excel)**<br>`data/raw/arrivals/historical/raw_downloads/*.xlsx` (5 files) | **TRACKED** | `State/UT`, `District`, `Market`, `Commodity Group`, `Commodity`, `Variety`, `Grade`, `Min Price`, `Max Price`, `Modal Price`, `Price Unit`, `Arrival Quantity`, `Arrival Unit`, `Arrival Date` | APMC Mandi (Market-level) | **Metric Tonnes** (Header: `Arrival Unit` = `"Metric Tonnes"`) | 2025-11-07 to 2026-11-06 | 16,030 total (1,479 Onion, 1,612 Tomato, 8,370 Wheat, 2,271 Rice, 2,298 Potato) | Direct Agmarknet portal web report exports | Title-row Agmarknet report header: `"Daily Price Arrival Report-07-11-2025 to 06-11-2026 for Uttar Pradesh"` | Open data / NDSAP (to be verified on portal) | Price columns present alongside quantity; requires reconciliation against price panels. |
| **CEDA Arrivals Quantity (CSV)**<br>`data/raw/arrivals/historical/raw_downloads/cedaquantity_data.csv` | **TRACKED** | `t`, `cmdty`, `state_id`, `state`, `market_id`, `market_name`, `state_name`, `district_id`, `district_name`, `qty` | APMC Mandi (Market-level; `market_id`: 334 Lucknow, 2584 Banthara) | **UNVERIFIED** (Header: `qty`; no unit column provided) | 2024-10-30 to 2025-10-30 | 615 | Ashoka University CEDA Agmarknet portal mirror | API schema export (`cmdty`, `t`, `market_id`, `state_name`) | Academic research portal (to be verified on portal) | Exact physical unit of `qty` not stated in header; needs external confirmation whether quintals or tonnes. |
| **CEDA Arrivals Quantity (Historical Top-Level)**<br>`data/raw/arrivals/historical/ceda_*.csv` (3 files) | **UNTRACKED** | `t`, `cmdty`, `state_id`, `state`, `market_id`, `market_name`, `state_name`, `district_id`, `district_name`, `qty` | APMC Mandi (Market-level; `market_id`: 334 Lucknow, 2584 Banthara) | **UNVERIFIED** (Header: `qty`; no unit column provided) | 2024-09-01 to 2025-10-30 | 481 total (27 potato part 2, 357 wheat part 1, 97 wheat part 2) | Ashoka University CEDA Agmarknet portal mirror | API schema export matching `cedaquantity_data.csv` | Academic research portal (to be verified on portal) | Provenance anomaly: `ceda_wheat_lucknow_part1.csv` contains Potato rows (`cmdty: Potato`). Wheat part 2 (97 rows) is an exact duplicate of `cedaquantity_data.csv`. |
| **CEDA Mandi Price Data (CSV)**<br>`data/raw/arrivals/historical/raw_downloads/ceda price data.csv` | **TRACKED** | `t`, `cmdty`, `market_id`, `market_name`, `state_id`, `state_name`, `district_id`, `district_name`, `variety`, `p_min`, `p_max`, `p_modal` | APMC Mandi (Market-level; `market_id`: 334, 2584) | **₹ / Quintal** (Derived from standard Agmarknet mandi price convention; headers: `p_min`, `p_max`, `p_modal`) | 2024-10-30 to 2025-10-30 | 594 | Ashoka University CEDA Agmarknet portal mirror | API schema export (`p_min`, `p_max`, `p_modal`) | Academic research portal (to be verified on portal) | Price-only record (no arrivals quantity); rejected during arrivals ingestion as `missing_quantity`. |
| **Historical 5-Year Price Raw Files**<br>`data/raw/{District}.csv` (5 files) | **TRACKED** | `Arrival_Date`, `Commodity`, `Commodity_Code`, `District`, `Grade`, `Market`, `Max_Price`, `Min_Price`, `Modal_Price`, `State`, `Variety` | APMC Mandi (Market-level) | **₹ / Quintal** (Header implicit; validated across domain conventions) | 2020-01-01 to 2024-12-31 (approx.) | 472,385 | Legacy project download (Agmarknet) | Audit reported baseline; API retrieval receipt pending | Open data / NDSAP (to be verified on portal) | Full audit of initial download parameters deferred to Kaggle heavy compute run. |
| **Validated 5-Year Price Panel**<br>`data/processed/mandi_5year_validated.csv` | **TRACKED** | Cleaned panel schema (42 engineered columns, target price, chronological sort) | APMC Mandi & District aggregate | **₹ / Quintal** | 2020 to 2024 | 462,350 | Processed from raw 5-year files via `src/data_pipeline.py` | Commit `3ea19fdd` pipeline execution logs | Derived internal | Heavy compute processing restricted to Kaggle environment per standing rules. |
| **Single-Day Price Snapshot**<br>`data/raw_external/9ef84268-d588-465a-a308-a864a43d0070.csv` | **TRACKED** | `State`, `District`, `Market`, `Commodity`, `Variety`, `Grade`, `Arrival_Date`, `Min_x0020_Price`, `Max_x0020_Price`, `Modal_x0020_Price` | APMC Mandi (Market-level) | **₹ / Quintal** (Header XML encoded: `_x0020_Price`) | 2026-11-11 (Single snapshot) | 11,720 | OGD India (data.gov.in) API UUID resource download | Resource ID `9ef84268-d588-465a-a308-a864a43d0070` in filename | Government Open Data Licence — India (GODL) | Live automated pull pipeline not yet verified; manual download UUID only. |
| **Legacy Generated Arrivals Partitions**<br>`data/raw/arrivals/historical/agmarknet_arrivals_up_2025_2026.csv` & `{District}_{Commodity}.csv` (25 files) | **TRACKED** | `State`, `District`, `Market`, `Commodity`, `Variety`, `Grade`, `Arrival_Date`, `Arrivals_Tonnes` | Market and District-Crop partitions | Tonnes (Assumed by legacy script) | 2025-11-07 to 2026-11-06 | 16,029 (consolidated) | Generated by legacy `organize_and_export_city_crop` from raw Excel downloads | Derived files inside raw input directory | Internal generated | Contaminated raw input space; excluded from new pipeline inputs by `classify_file()`. |
| **DES Production & Yield Statistics**<br>`data/raw/production/DES-District-Data-For-2024-25.csv` | **UNTRACKED** | `State`, `District`, `Crop`, `Season`, `Area-2024-25`, `Production-2024-25`, `Yield-2024-25` | District annual totals | **Hectares** (Area), **Tonnes** (Production), **Kg/Ha** (Yield) | Agricultural Year 2024-25 | 237 | Directorate of Economics and Statistics (DES), MoA&FW | File naming DES convention | Official publication (to be verified on portal) | Annual static estimates; not empirical high-frequency mandi arrivals. Decoupled from Release 1. |
| **Cold Storage Facility Quotations**<br>`data/raw/storage/local_warehouse_quotations.csv` & `UP_Storage_Rate_Research.xlsx` | **UNTRACKED** | `facility_id`, `district`, `facility_name`, `record_type`, `rate_amount`, `rate_unit`, `quotation_status`, etc. | Facility / Warehouse | Quoted ₹ / Bag / Month or ₹ / Qtl | Research survey template | 22 facilities (all marked `"Not received"`) | Local market outreach log | Manual phone survey notes | Private commercial | Zero verified empirical quotes received. Storage costs remain `SCENARIO_ASSUMPTION` only. |
| **Transport Rate Research**<br>`data/raw/storage/transport/transport_quotations.csv` | **UNTRACKED** | Route, origin, destination, vehicle type, quote amount, distance km | Mandi-to-facility route | ₹ / Quintal / Km | Research survey template | 18 routes | Local transporter outreach log | Field research notes | Private commercial | Illustrative haulage assumptions; treated as `SCENARIO_ASSUMPTION` until formal invoices verified. |
| **Crop Storage Parameters Reference**<br>`data/reference/crop_storage_parameters.csv` | **TRACKED** | `source`, `document_filename`, `year`, `page_number`, `crop`, `category`, `parameter_name`, `value`, `unit`, `storage_conditions`, `storage_duration`, `loss_type`, `notes` | Crop parameter | Physical (% loss, °C, % RH, days) | Published literature benchmarks | 34 parameter rows | ICAR, CIPHET, NCCD literature surveys | Explicit citation columns (`document_filename`, `page_number`) | Academic citation / Fair dealing | Verified technical reference anchors for `SCENARIO_ASSUMPTION` bounds. |
| **IMD Gridded Weather Documentation**<br>`documentation/IMD_API_REFERENCE.pdf` & `IMD_HISTORICAL_ACCESS_NOTES.md` | **UNTRACKED** | Meteorological reference specs ($0.25^\circ \times 0.25^\circ$ gridded rainfall & temperature) | Spatial grid cell | mm (Rainfall), °C (Temperature) | Access documentation only | Reference documentation | India Meteorological Department (IMD) | Official IMD developer documentation | Proprietary / Official portal access terms | Paid/registered access model; real-time ingestion decoupled from Release 1 price model. |
| **Inventory Manifests & Audit Hashes**<br>`data/manifests/existing_file_inventory.csv` & `checksums.sha256` | **UNTRACKED** | File path, byte size, modification timestamp, SHA-256 hash | File-level | Bytes / Hex digests | Audit snapshot (2026-11-12) | 1,228 manifest entries | Local repository audit tooling | Generated during `MP-AUDIT-001` | Internal engineering | Proves local bit-level file integrity; does not prove origin authenticity. |
| **Quarantined Records**<br>`data/quarantine/quarantined_*.csv` (2 files) | **TRACKED** | Same as processed panel with `quarantine_reason` | APMC Mandi | ₹ / Quintal | 2020 to 2024 | 9,845 conflicting, 190 invalid | Cleaned panel quarantine output | Processing pipeline audit artifacts | Internal engineering | Contains records rejected for $P \le 0$, extreme anomalies, or contradictory pricing. |

---

## 3. Detailed Profile: Arrivals Datasets (MP-DATA-003A Empirical Audit)

### 3.1 Grain Evidence & Spatial Hierarchy

Both the Agmarknet Excel reports and CEDA CSV quantity files are recorded at the **APMC Mandi (Market) level**, NOT aggregated district totals:

1. **Agmarknet Excel Reports:**
   - Explicit `Market` column present across all 5 files.
   - Contains distinct APMC mandis within each district:
     - **Ghaziabad (4 mandis):** Ghaziabad APMC, Hapur APMC, Muradnagar APMC, Noida APMC.
     - **Jhansi (6 mandis):** Chirgaon APMC, Gurusarai APMC, Jhansi APMC, Jhansi Grain APMC, Mauranipur APMC, Moth APMC.
     - **Kanpur (4 mandis):** Baripaal APMC, Choubepur APMC, Kanpur(Grain) APMC, Uttaripura APMC.
     - **Lucknow (2 mandis):** Banthara APMC, Lucknow APMC.
     - **Unnao (3 mandis):** Bangarmau APMC, Purwa APMC, Unnao APMC.
   - **Empirical Multi-Row Grain Evidence:** 1,327 instances occur where multiple market records exist on the exact same date for the same district and commodity (e.g. on `2025-11-10` in Ghaziabad for Wheat: Ghaziabad APMC reported 1,007.0 tonnes, while Hapur APMC reported 800.0 tonnes).
   - `market_id` column: Absent in standard Excel download view.

2. **CEDA Quantity Datasets:**
   - Explicit `market_name` and `market_id` columns present.
   - Mandis identified: `market_id = 334` (Lucknow APMC) and `market_id = 2584` (Banthara APMC).
   - **Empirical Multi-Row Grain Evidence:** 261 instances occur where both Lucknow and Banthara report separate arrivals on the exact same date for the same commodity (e.g. on `2024-10-30` for Wheat in Lucknow: Lucknow APMC reported 350.0 and Banthara reported 486.0).

---

### 3.2 Temporal Coverage & Disjoint Date Overlap Analysis

A rigorous, read-only cross-source comparison was executed across every `(district, commodity)` pair:

* **CEDA Ingestion Date Coverage:** `2024-09-01` to `2025-10-30` (384 potato records, 712 wheat records; limited to Lucknow district).
* **Agmarknet Excel Date Coverage:** `2025-11-07` to `2026-11-06` (16,030 records across all 5 districts: Ghaziabad, Jhansi, Kanpur, Lucknow, Unnao; covering Onion, Potato, Rice, Tomato, Wheat).

**Key Empirical Finding:**  
There are **ZERO overlapping dates** between CEDA quantity files and Agmarknet Excel reports across all 25 `(district, commodity)` combinations. CEDA records terminate on **2025-10-30**, and Agmarknet Excel records commence on **2025-11-07** (an 8-day non-overlapping gap). Consequently, direct numerical ratio comparisons on identical calendar dates are mathematically impossible due to disjoint observation windows.

---

### 3.3 Conservation of Rows Across Combined Ingestion Dry-Run

Executing the non-destructive arrivals ingestion pipeline (`src/ingest_agmarknet_arrivals.py`) in read-only dry-run mode (`write=False`) across all discovered raw input files (`data/raw/arrivals/historical/` and `raw_downloads/`) proves exact mathematical conservation of rows:

$$\text{rows\_in} = \text{rows\_out} + \text{duplicates} + \text{conflicts} + \text{rejected}$$

$$17,720 = 17,028 + 97 + 0 + 595$$

* **$\text{total\_rows\_in} = 17,720$:**
  * 5 Agmarknet Excel files: $1,479 + 1,612 + 8,370 + 2,271 + 2,298 = 16,030$
  * 3 CEDA historical CSVs: $27 + 357 + 97 = 481$
  * 1 CEDA quantity download: $615$
  * 1 CEDA price download: $594$
* **$\text{total\_rejected} = 595$:**
  * `594` from `ceda price data.csv` (`missing_quantity`: price-only records containing no arrivals volume).
  * `1` from `Daily Price Arrival Report... (4).xlsx` (`missing_quantity`: null cell in row).
  * `0` missing district, `0` missing commodity, `0` unparseable dates.
* **$\text{total\_duplicates} = 97$:**
  * Exactly 97 rows in `ceda_wheat_lucknow_part2.csv` (`2025-09-01` to `2025-10-30`) duplicate rows in `cedaquantity_data.csv` on the canonical natural key with identical quantities; 1 copy preserved, 97 redundant rows cleanly deduplicated.
* **$\text{total\_conflicts} = 0$:**
  * Zero natural key collisions with differing quantities or prices.
* **$\text{total\_rows\_out} = 17,028$:**
  * Clean, standardized, immutable records accepted into target partitions.
  * **Units breakdown:** 16,029 verified as `Metric Tonnes` (from Agmarknet Excel header `Arrival Unit`); 999 categorized as `UNVERIFIED` (from CEDA `qty` header, preserving raw numbers while leaving `Arrivals_Tonnes` as `NaN`).

---

### 3.4 Provenance & Anomaly Observations

1. **Naming Anomaly in Untracked CEDA File:**  
   The file `data/raw/arrivals/historical/ceda_wheat_lucknow_part1.csv` is named "wheat", but 100% of its 357 records have `cmdty == 'Potato'`. The pipeline correctly standardizes these rows based on internal row content rather than trusting file stems.
2. **Redundant Column Dropping:**  
   CEDA CSVs contain both `state` and `state_name` columns with identical `"Uttar Pradesh"` content. The ingestion engine detects this redundancy and safely drops the duplicate column without raising a false collision.
3. **Agmarknet Excel Title Rows:**  
   Agmarknet web portal exports place a descriptive report string in row 0 (`Daily Price Arrival Report...`) and actual column headers in row 1. The ingestion engine dynamically detects this structure, realigning column headers and preserving all data rows.

---

## 4. Next Actions & Traceability

1. **Kaggle Heavy Compute Audit:** Full validation and multi-model benchmark evaluation of the 462k-row historical price panel will run strictly on Kaggle per project standing rules.
2. **Cold Storage Outreach:** Any future transition of storage parameters from `SCENARIO_ASSUMPTION` to `EMPIRICAL_OBSERVATION` requires documented receipt of formal facility quotations.
3. **Release 1 Scope Decoupling:** Ingestion of live price feeds remains decoupled from optional weather and production pipelines.
