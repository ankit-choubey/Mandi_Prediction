# Data Source Register & Ingestion Evidence

**Repository:** `ankit-choubey/Mandi_Prediction`  
**Document ID:** `DATA_SOURCE_REGISTER`  
**Established Under Task:** `MP-DATA-003A`  
**Last Updated Under Task:** `MP-DATA-003B`  
**Baseline Git Commit:** `442c6e6cea78025b82c8ca296f8519453afca7d4`  

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

The following register documents every data source group present in the repository, verified by header inspection, manifest entries, and file-level accounting:

| Source Group / Path Pattern | Git Status | Schema (Key Columns) | Grain | Units (Header Evidence) | Date Range | Rows | Provenance Status | Retrieval Evidence | Licence Status | Unresolved Questions |
|---|---|---|---|---|---|---|---|---|---|---|
| **Historical 5-Year Raw Price Files**<br>`5 year dataset/*.csv` (5 files) | **TRACKED** | `Arrival_Date`, `District`, `Market`, `Commodity`, `Variety`, `Grade`, `Min_Price`, `Max_Price`, `Modal_Price`, `Commodity_Code`, `State` | APMC Mandi-Day | **₹ / Quintal** (Standard Agmarknet mandi price convention) | 2021-09-01 to 2026-09-30 (1,856 days) | 472,385 total (Ghaziabad: 132,478; Jhansi: 83,972; Kanpur: 113,319; Lucknow: 54,876; Unnao: 87,740) | UNVERIFIED (Legacy Agmarknet portal download) | Manifest audit baseline; API request logs absent | Open data / NDSAP (to be verified on portal) | 139 commodities in raw files; 31 low-observation commodities dropped in pipeline. |
| **Historical 2-Year Raw Price Files**<br>`data/raw/*.csv` (5 files) | **TRACKED** | `Arrival_Date`, `Commodity`, `Commodity_Code`, `District`, `Grade`, `Market`, `Max_Price`, `Min_Price`, `Modal_Price`, `State`, `Variety` | APMC Mandi-Day | **₹ / Quintal** (Standard Agmarknet mandi price convention) | 2024-09-01 to 2026-09-01 (731 days) | 160,192 total (Ghaziabad: 41,495; Jhansi: 23,625; Kanpur: 42,644; Lucknow: 21,063; Unnao: 31,365) | UNVERIFIED (Legacy Agmarknet 2-year window) | Local CSVs; exact API request logs absent | Open data / NDSAP (to be verified on portal) | 130 commodities; 100% key subset of 5-year raw files; represents recent 2-year window. |
| **Validated 5-Year Price Panel**<br>`data/processed/mandi_5year_validated.csv` (and `mandi_5year_processed.csv`) | **TRACKED** | **12 Columns:** `Arrival_Date`, `District`, `Market`, `Commodity`, `Variety`, `Grade`, `Min_Price`, `Max_Price`, `Modal_Price`, `Commodity_Code`, `State`, `series_id` | APMC Mandi-Day & Series | **₹ / Quintal** | 2021-09-01 to 2026-09-30 (1,856 days) | 462,350 clean accepted rows (41 unique markets, 108 unique commodities, 1,297 series retained) | **PARTIALLY CORROBORATED (scope stated)**: Derived from 5-year raw files; corroborated for five focus crops (2025-11..2026-09 via Agmarknet Excel, 99.39% match) and Lucknow Wheat (2024-10..2025-10 via CEDA, 100% match). Outside these tested scopes, provenance remains uncorroborated. Not authenticated. | Proven by `validation_summary.json` & `processing_manifest.json` | Derived internal artifact | Full row-level multiset reconciliation with raw inputs executed under Kaggle task MP-DATA-003B. |
| **Quarantined Invalid Price Records**<br>`data/quarantine/quarantined_invalid_records.csv` | **TRACKED** | Same 12 columns as panel + `quarantine_reason` | APMC Mandi-Day | **₹ / Quintal** | 2021 to 2026 | 27 rows (34 non-positive prices, 15 min > max, 22 modal > max; multi-fault rows) | Quarantine filter output | Confirmed by `validation_summary.json` (row count: 27) | Internal engineering artifact | Verified bit-level file integrity (SHA-256: `a71956fa...`). |
| **Quarantined Conflicting Price Records**<br>`data/quarantine/quarantined_conflicting_records.csv` | **TRACKED** | Same 12 columns as panel + `conflict_id` | APMC Mandi-Day | **₹ / Quintal** | 2021 to 2026 | 2,936 rows (ambiguous same-grade price records on identical natural key) | Pipeline deduplication filter | Confirmed by `validation_summary.json` (row count: 2,936) | Internal engineering artifact | Verified bit-level file integrity (SHA-256: `cbecfb51...`). |
| **Single-Day Price Snapshot**<br>`data/raw_external/9ef84268-d588-465a-a308-a864a43d0070.csv` | **TRACKED** | `State`, `District`, `Market`, `Commodity`, `Variety`, `Grade`, `Arrival_Date`, `Min_x0020_Price`, `Max_x0020_Price`, `Modal_x0020_Price` | APMC Mandi-Day | **₹ / Quintal** (Header XML encoded: `_x0020_Price`) | 2026-11-11 (Single snapshot date) | 11,720 | UNVERIFIED (data.gov.in resource UUID in filename only) | Filename matches OGD resource UUID; zero API session receipts | Government Open Data Licence — India (to be verified on portal) | Provenance is unverified; filename alone is not external proof of institutional origin. |
| **Agmarknet Arrivals Reports (Excel)**<br>`data/raw/arrivals/historical/raw_downloads/*.xlsx` (5 files) | **TRACKED** | `State/UT`, `District`, `Market`, `Commodity Group`, `Commodity`, `Variety`, `Grade`, `Min Price`, `Max Price`, `Modal Price`, `Price Unit`, `Arrival Quantity`, `Arrival Unit`, `Arrival Date` | APMC Mandi (Market-level) | **Metric Tonnes** (Header: `Arrival Unit` = `"Metric Tonnes"`) | 2025-11-07 to 2026-11-06 | 16,030 total (1,479 Onion, 1,612 Tomato, 8,370 Wheat, 2,271 Rice, 2,298 Potato) | Direct Agmarknet portal web report exports | Title-row Agmarknet report header: `"Daily Price Arrival Report-07-11-2025 to 06-11-2026 for Uttar Pradesh"` | Open data / NDSAP (to be verified on portal) | Price columns present alongside quantity; evaluated for price corroboration under MP-DATA-003B. |
| **CEDA Arrivals Quantity (CSV)**<br>`data/raw/arrivals/historical/raw_downloads/cedaquantity_data.csv` | **TRACKED** | `t`, `cmdty`, `state_id`, `state`, `market_id`, `market_name`, `state_name`, `district_id`, `district_name`, `qty` | APMC Mandi (Market-level; `market_id`: 334 Lucknow, 2584 Banthara) | **UNVERIFIED** (Header: `qty`; no unit column provided) | 2024-10-30 to 2025-10-30 | 615 | Ashoka University CEDA Agmarknet portal mirror | API schema export (`cmdty`, `t`, `market_id`, `state_name`) | Academic research portal (to be verified on portal) | Exact physical unit of `qty` not stated in header; needs external confirmation whether quintals or tonnes. |
| **CEDA Arrivals Quantity (Historical Top-Level)**<br>`data/raw/arrivals/historical/ceda_*.csv` (3 files) | **UNTRACKED** | `t`, `cmdty`, `state_id`, `state`, `market_id`, `market_name`, `state_name`, `district_id`, `district_name`, `qty` | APMC Mandi (Market-level; `market_id`: 334 Lucknow, 2584 Banthara) | **UNVERIFIED** (Header: `qty`; no unit column provided) | 2024-09-01 to 2025-10-30 | 481 total (27 potato part 2, 357 wheat part 1, 97 wheat part 2) | Ashoka University CEDA Agmarknet portal mirror | API schema export matching `cedaquantity_data.csv` | Academic research portal (to be verified on portal) | Provenance anomaly: `ceda_wheat_lucknow_part1.csv` contains Potato rows (`cmdty: Potato`). Wheat part 2 (97 rows) duplicates `cedaquantity_data.csv`. |
| **CEDA Mandi Price Data (CSV)**<br>`data/raw/arrivals/historical/raw_downloads/ceda price data.csv` | **TRACKED** | `t`, `cmdty`, `market_id`, `market_name`, `state_id`, `state_name`, `district_id`, `district_name`, `variety`, `p_min`, `p_max`, `p_modal` | APMC Mandi (Market-level; `market_id`: 334, 2584) | **₹ / Quintal** (Derived from standard Agmarknet mandi price convention; headers: `p_min`, `p_max`, `p_modal`) | 2024-10-30 to 2025-10-30 | 594 | Ashoka University CEDA Agmarknet portal mirror | API schema export (`p_min`, `p_max`, `p_modal`) | Academic research portal (to be verified on portal) | Price-only record (no arrivals quantity); evaluated for price corroboration under MP-DATA-003B. |
| **NASA POWER Gridded Weather**<br>`suryansh - work/dataset_research/raw_external/nasa_power_weather_up_2024_2026.csv` | **TRACKED** | `District`, `Arrival_Date`, `Precipitation_mm`, `Temp_Max_C`, `Temp_Min_C`, `Relative_Humidity_Pct` | District-Day | **mm** (`Precipitation_mm`), **°C** (`Temp_Max_C`, `Temp_Min_C`), **%** (`Relative_Humidity_Pct`) | 2024-09-01 to 2026-09-01 | 3,655 | NASA POWER API Harvest | `acquire_nasa_weather.py` retrieval script in repo | Open NASA data policy (Public domain) | Not integrated into Release 1 price model; historical weather for 2021-2024 unharvested. |
| **Quarantined Synthetic Arrivals**<br>`suryansh - work/dataset_research/raw_external/quarantine/SYNTHETIC_ceda_calibrated_mandi_arrivals_up_2024_2026.csv` | **TRACKED** | `District`, `Market`, `Commodity`, `Variety`, `Grade`, `Arrival_Date`, `Arrival_Quantity_Qtl` | APMC Mandi-Day | **Quintals** (`Arrival_Quantity_Qtl`) | 2024-09-01 to 2026-09-01 | 35,531 | QUARANTINED_SYNTHETIC_PROXY | Calibrated arrival proxy generation script | Internal synthetic proxy | Must NEVER be used as empirical observations; permanently quarantined. |
| **Quarantined Synthetic Production**<br>`suryansh - work/dataset_research/raw_external/quarantine/SYNTHETIC_des_up_district_crop_production_statistics.csv` | **TRACKED** | `State`, `District`, `Commodity`, `Crop_Year`, `Season`, `Area_Hectares`, `Production_Tonnes`, `Yield_Kg_Per_Ha` | District-Crop-Season | **Hectares**, **Tonnes**, **Kg/Ha** | 2024 | 40 | QUARANTINED_SYNTHETIC_PROXY | Synthetic production generation script | Internal synthetic proxy | Must NEVER be used as empirical statistics; permanently quarantined. |
| **DES Production & Yield Statistics**<br>`data/raw/production/DES-District-Data-For-2024-25.csv` | **UNTRACKED** | `State`, `District`, `Crop`, `Season`, `Area-2024-25`, `Production-2024-25`, `Yield-2024-25` | District annual totals | **Hectares** (Area), **Tonnes** (Production), **Kg/Ha** (Yield) by domain convention | Agricultural Year 2024-25 | 237 physical rows | UNVERIFIED (DES MoA&FW convention) | Physical CSV present on disk; download receipt missing | Official publication (to be verified on portal) | **[UNRESOLVED DISCREPANCY]** MP-AUDIT-001 noted 40 rows (referring to synthetic proxy), whereas physical untracked file has 237 rows. Decoupled from Release 1. |
| **Cold Storage Facility Quotations**<br>`data/raw/storage/local_warehouse_quotations.csv` & `UP_Storage_Rate_Research.xlsx` | **UNTRACKED** | `facility_id`, `district`, `facility_name`, `record_type`, `address`, `phone`, `phone_source`, `source_url`, `status_note`, `contacted`, `crops_accepted`, `min_storage_duration`, `rate_amount`, `rate_unit`, etc. | Facility / Warehouse | Quoted ₹ / Bag / Month or ₹ / Qtl | Research survey template | 22 facilities (all marked `"Not received"`) | Local market outreach log | Manual phone survey notes; `Facilities` sheet in XLSX has 22 data rows + header (23 rows) | Private commercial | Zero verified empirical quotes received. Storage costs remain `SCENARIO_ASSUMPTION` only. |
| **Transport Rate Research**<br>`data/raw/storage/transport/transport_quotations.csv` | **UNTRACKED** | `quotation_id`, `crop`, `district`, `route_type`, `origin`, `destination`, `linked_facility_id`, `linked_facility_name`, `provider_slot`, `provider_name`, `provider_contact`, `vehicle_type`, `carrying_capacity_qtl`, `total_fare_rs`, `fare_basis`, etc. | Mandi-to-facility route slot | ₹ / Quintal / Km (Template fields) | Research survey template | 45 physical rows (all marked `"Not collected"`) | Local transporter outreach template | 3 distinct route templates x 5 districts x 3 provider slots | Private commercial | **[UNRESOLVED DISCREPANCY]** MP-AUDIT-001/MP-DATA-003A recorded 18 routes; physical CSV has 45 quotation rows (all uncollected). Zero empirical transport quotes collected. |
| **Crop Storage Parameters Reference**<br>`data/reference/crop_storage_parameters.csv` | **TRACKED** | `source`, `document_filename`, `year`, `page_number`, `crop`, `category`, `parameter_name`, `value`, `unit`, `storage_conditions`, `storage_duration`, `loss_type`, `notes` | Crop parameter | Physical (% loss, INR/qtl, INR/50kg bag) | Published literature benchmarks | 24 physical rows | ICAR, CIPHET, NCCD literature surveys | Explicit citation columns (`document_filename`, `page_number`) | Academic citation / Fair dealing | **[UNRESOLVED DISCREPANCY]** MP-DATA-003A recorded 34 rows; physical CSV contains exactly 24 parameter rows across 8 crops. Reference anchor for scenario bounds. |
| **Legacy Generated Arrivals Partitions**<br>`data/raw/arrivals/historical/agmarknet_arrivals_up_2025_2026.csv` & `{District}_{Commodity}.csv` (25 files) | **TRACKED** | `State`, `District`, `Market`, `Commodity`, `Variety`, `Grade`, `Arrival_Date`, `Arrivals_Tonnes` | Market and District-Crop partitions | Tonnes (Assumed by legacy script) | 2025-11-07 to 2026-11-06 | 16,029 (consolidated) | Generated by legacy `organize_and_export_city_crop` from raw Excel downloads | Derived files inside raw input directory | Internal generated | Contaminated raw input space; excluded from new pipeline inputs by `classify_file()`. |
| **IMD Gridded Weather Documentation**<br>`documentation/IMD_API_REFERENCE.pdf` & `IMD_HISTORICAL_ACCESS_NOTES.md` | **UNTRACKED** | Meteorological reference specs ($0.25^\circ \times 0.25^\circ$ gridded rainfall & temperature) | Spatial grid cell | mm (Rainfall), °C (Temperature) | Access documentation only | Reference documentation | India Meteorological Department (IMD) | Official IMD developer documentation | Proprietary / Official portal access terms | Paid/registered access model; real-time ingestion decoupled from Release 1 price model. |
| **Inventory Manifests & Audit Hashes**<br>`data/manifests/existing_file_inventory.csv` & `checksums.sha256` | **UNTRACKED** | File path, byte size, modification timestamp, SHA-256 hash | File-level | Bytes / Hex digests | Audit snapshot (2026-11-12) | 1,228 manifest entries | Local repository audit tooling | Generated during `MP-AUDIT-001` | Internal engineering | Proves local bit-level file integrity; does not prove origin authenticity. |

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

1. **Kaggle Heavy Compute Audit (MP-DATA-003B):** First remote Kaggle execution performs full row-level multiset reconciliation of all 472,385 raw price records against `mandi_5year_validated.csv`, extracts the 7,072 low-observation dropped rows, profiles series coverage, and conducts price corroboration against Agmarknet Excel and CEDA price data.
2. **Cold Storage Outreach:** Any future transition of storage parameters from `SCENARIO_ASSUMPTION` to `EMPIRICAL_OBSERVATION` requires documented receipt of formal facility quotations.
3. **Release 1 Scope Decoupling:** Ingestion of live price feeds remains decoupled from optional weather and production pipelines.

---

## 5. External Snapshots, Regime Diagnostics, and Provisional Panel v2 Register

### 5.1 Regime Shifts and Hypotheses from External Reports
* **Nomenclature Transition Date in Data:** The first `" APMC"`-named record in the historical raw dataset appears on `2025-11-01`. External government and portal announcements hypothesize this corresponds to the Agmarknet 2.0 national platform rollout (`2025-11-07`).
* **Fractional Pricing Shift Date in Data:** Non-integer fractional prices appear in $<0.01\%$ of records prior to March 2026, rising to **40.89% of monthly records from 2026-03 to 2026-09**. External technical reports hypothesize this reflects automated electronic weighbridge integrations (such as UP's 251 APMC mandis completing automated API feeds in late September 2026).
* **Nomenclature Shift:** Reporting mandi terminal names acquired an `" APMC"` suffix (e.g. `Ghaziabad` $\rightarrow$ `Ghaziabad APMC`, `Noida` $\rightarrow$ `Noida APMC`).

### 5.2 External Snapshot Register
* **File Identifier:** `data/raw_external/9ef84268-d588-465a-a308-a864a43d0070.csv`
* **File Size & Rows:** 1,217,998 bytes (1.2 MB), 11,720 records.
* **Extraction Timestamp:** `2026-11-11` (live export from post-migration portal).
* **Target District Markets:** Exactly 14 markets belong to the 5 target districts; **14 of 14 (100.0%)** carry the `" APMC"` suffix.
* **Provenance Adjudication:** Empirical evidence proving that modern feeds mandate automated market canonicalisation (`data/reference/market_aliases.csv`) to maintain backward compatibility with 5-year historical series.

### 5.3 Provisional Historical Price Panel v2
* **Panel Status:** **PROVISIONAL** (SHA-256: `851e718468d6b8c9fd07944535a462338e71aa105af25339fe9438b697088f31`).
* **Storage Location:** `experiments/outputs/006/mandi_5year_validated_v2.csv` (gitignored, heavy compute artifact).
* **Tracked Processing Manifest:** `data/processed/processing_manifest_v2.json` (SHA-256: `c6f7089b94d2deaa7ca75f4ec85319d82d99fb8c1cd1be6c488398277a3518c1`).
* **Source Raw Files:** 5 files in `5 year dataset/*.csv` (472,385 total rows).
* **Accepted Clean Records:** **463,217 rows** across 1,167 unique series (+867 net rows over v1).
* **Rescued Observations:** **+1,722 rows** previously dropped under the `< 20` observation threshold in v1 due to market identity forking.
* **Transition Overlap Concordance:** 855 exact duplicate rows removed during feed transition alongside unchanged conflicts (2,936) demonstrate that overlapping old and new reporting channels agree on price quotes.
* **Schema Columns:** `Arrival_Date`, `District`, `Market_Raw`, `Market`, `Commodity`, `Variety`, `Grade`, `Min_Price`, `Max_Price`, `Modal_Price`, `Commodity_Code`, `State`, `series_id`.
* **Corroboration Concordance:** 99.40% exact modal price agreement on 12,846 matched Agmarknet Excel rows (87.14% match rate, +244 matched rows vs v1's 85.5%); 100.00% exact agreement on 591 matched CEDA rows.

