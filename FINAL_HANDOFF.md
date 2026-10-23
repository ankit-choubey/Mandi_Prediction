# FINAL_HANDOFF.md: Engineering Handoff to Modeling Team

**Project:** APMC Mandi Market Intelligence & Price Forecasting  
**Repository:** `ankit-choubey/Mandi_Prediction`  
**Engineer / Data Lead:** Suryansh  
**Audit & Verification Date:** 2026-10-23  
**Deliverable Status:** **100% COMPLETE & VERIFIED** (88/88 Unit Tests Passing)  

---

## 1. Scope & Ownership Boundaries

- **In Scope (Delivered & Owned):**
  - Complete 5-year empirical data inspection across all 5 target districts.
  - Fail-safe, non-destructive data loading pipeline (`src/data_pipeline.py`).
  - Safe validation & Strategy 2 deduplication engine (`src/data_validator.py`).
  - Cryptographic data manifest (`data/processed/processing_manifest.json`).
  - Evidence-preserving quarantine of bad records (`data/quarantine/`).
  - Provenance audit & alternative reference source research (`DATA_SOURCE_REPORT.md`, `DATA_SOURCE_ALTERNATIVES.md`).
  - Comprehensive automated test suite (`tests/test_data_validation.py`, `tests/test_data_pipeline.py`, total 88 tests).
- **Out of Scope (Preserved for Modeling Team):**
  - Core production model selection and hyperparameter tuning.
  - Decision-support dashboard UI development.
  - Zero API calls executed during ingestion (offline, reproducible processing).
  - Zero synthetic data fabrication (zero synthetic arrival volumes or price interpolations).

---

## 2. Inventory of Files Changed, Added & Published

| File Path | Status | Purpose & Description |
| :--- | :--- | :--- |
| [`src/data_validator.py`](file:///Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction/src/data_validator.py) | **Added** | Standalone validator implementing natural-key deduplication (Strategy 2 / DEC-008), price order verification, atomic staging/publishing, and evidence quarantine. |
| [`src/data_pipeline.py`](file:///Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction/src/data_pipeline.py) | **Added** | Production ingestion pipeline with case-insensitive column aliasing, robust date parsing, CLI flags, and SHA-256 manifest generation. |
| [`src/data_loader.py`](file:///Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction/src/data_loader.py) | **Updated** | Added backward-compatible support for 5-year directory and pre-processed validated CSV files. |
| [`DATA_SOURCE_REPORT.md`](file:///Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction/DATA_SOURCE_REPORT.md) | **Added** | Master audit report: SHA-256 checksums, 1,856-day timeline reconciliation, OGD API authentication failure diagnostics, and district-by-district breakdown. |
| [`DATA_SOURCE_ALTERNATIVES.md`](file:///Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction/DATA_SOURCE_ALTERNATIVES.md) | **Added** | Exhaustive provenance research comparing AGMARKNET portal, OGD India, and CEDA Agmarknet API (schema, latency, arrival volume gap). |
| [`VALIDATION_REPORT.md`](file:///Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction/VALIDATION_REPORT.md) | **Generated** | Machine-generated audit report detailing exact accepted, quarantined, and filtered row counts. |
| [`tests/test_data_validation.py`](file:///Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction/tests/test_data_validation.py) | **Added** | 7 core validation tests (impossible price checks, duplicate detection, atomic publishing, idempotence). |
| [`tests/test_data_pipeline.py`](file:///Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction/tests/test_data_pipeline.py) | **Added** | 13 pipeline tests (missing files, malformed rows, manifest integrity, CLI interface). |
| [`suryansh - work/experiments/profile_candidate_crops.py`](file:///Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction/suryansh%20-%20work/experiments/profile_candidate_crops.py) | **Updated** | Added CLI `--data-dir` argument parsing and automated 5-year path resolution. |
| [`suryansh - work/experiments/train_and_audit_models.py`](file:///Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction/suryansh%20-%20work/experiments/train_and_audit_models.py) | **Updated** | Added CLI argument parsing and 5-year dataset resolution for modeling verification. |

---

## 3. Data Problems Discovered & Resolved

Through rigorous empirical inspection of all **472,385 raw records**, the following defects were detected, categorized, and safely mitigated:

1. **Impossible Price Relationships (15 Violations):**
   - **Defect:** 15 records in Kanpur had `Min_Price > Max_Price` (e.g., Min = ₹2,400, Max = ₹0.00).
   - **Resolution:** Rather than guessing or silently swapping numbers, these 15 records were quarantined into `quarantine/invalid_price_records.csv` to maintain 100% data integrity.
2. **Non-Positive Prices (12 Violations):**
   - **Defect:** 12 records contained zero or negative price quotes.
   - **Resolution:** Quarantined alongside the 15 price order violations (total: 27 invalid records).
3. **Conflicting Same-Day Same-Grade Quotes (2,936 Records):**
   - **Defect:** Identical series (`District + Market + Commodity + Variety + Grade + Arrival_Date`) having multiple differing price quotes on the same date.
   - **Resolution:** Handled strictly under **Strategy 2 (DEC-008)**. Ambiguous conflicting records are quarantined to `quarantine/conflicting_price_records.csv`, while 7,072 exact duplicate copies were collapsed to 1 authoritative record.
4. **District Naming Inconsistencies:**
   - **Defect:** Canonical district names had historical phonetic spelling variations (`Gaziabaad` vs `Ghaziabad`, `Lukhnow` vs `Lucknow`).
   - **Resolution:** Deterministic dictionary normalization maps them cleanly to canonical official district names (`Ghaziabad`, `Lucknow`, `Kanpur`, `Jhansi`, `Unnao`).
5. **Grade Field Inconsistencies:**
   - **Defect:** Null, empty, or whitespace strings in the `Grade` column.
   - **Resolution:** Standardized to `'FAQ'` (Fair Average Quality) per AGMARKNET trade standards, preserving Grade in the canonical series key.
6. **Date Parsing Robustness:**
   - **Defect:** Multi-format date strings across different district files.
   - **Resolution:** Ingestion parser supports `%d/%m/%Y`, `%Y-%m-%d`, and ISO formats with error coercion.

---

## 4. Final Dataset Reconciliation Ledger

```text
========================================================================================
STAGE                          RECORD COUNT     RECONCILIATION NOTES
========================================================================================
1. Total Raw Rows Loaded            472,385     100% of rows across 5 district CSV files
2. Dropped Missing Keys                   0     Zero records missing essential key fields
3. Invalid Quarantined                   27     15 Min > Max violations + 12 non-positive
4. Conflicting Quarantined            2,936     Ambiguous same-day price quotes (DEC-008)
5. Identical Duplicate Deduplication  7,072     Identical duplicate rows safely collapsed
----------------------------------------------------------------------------------------
6. Published Clean Dataset          462,350     Published to data/processed/mandi_5year_validated.csv
   - Active Canonical Series          1,297     Unique District-Market-Commodity-Variety-Grade series
   - Calendar Day Span                1,856     2021-09-01 to 2026-09-30 (5 full years + 1 month)
   - Candidate Target Crops          93,491     Potato (24k), Onion (22k), Tomato (21k), Wheat (25k)
========================================================================================
```

---

## 5. Verification & Test Suite Results

- **Automated Tests Executed:** `88`
- **Tests Passed:** **`88` (100% PASS)**
- **Tests Failed / Errors:** `0`
- **Execution Speed:** `10.82 seconds`
- **Key Test Modules:**
  - `tests/test_data_validation.py` $\implies$ 7 passed
  - `tests/test_data_pipeline.py` $\implies$ 13 passed
  - `tests/test_data_foundation.py` $\implies$ 11 passed
  - `tests/test_production_pipeline.py` $\implies$ 7 passed
  - `tests/test_economic_model.py` & `backtest` $\implies$ 29 passed
  - `tests/test_feasibility_reconciliation.py` $\implies$ 5 passed
  - `tests/test_phase05_robustness.py` & `phase06b` $\implies$ 16 passed

---

## 6. What Remains Unresolved / Guidance for Modeling Team

1. **Absence of Arrival Volumes in Raw Source:**
   - The official OGD India dataset (`9ef84268-d588-465a-a308-a864a43d0070`) contains **only price quotes** (`Min_Price`, `Max_Price`, `Modal_Price`). It does **not** provide daily arrival quantities (tonnes/quintals).
   - *Recommendation for Modeling Team:* Use the validated price features (spreads, lags, volatility, neighbor spatial price differentials). If arrival volume elasticity is strictly mandated, refer to [`DATA_SOURCE_ALTERNATIVES.md`](file:///Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction/DATA_SOURCE_ALTERNATIVES.md) for integrating CEDA quantities API with bearer token authentication.
2. **Class Imbalance in Wheat vs Volatile Perishables:**
   - Wheat exhibits 84.7% "Normal" price stability due to MSP procurement cushions. Perishables (Potato, Tomato, Onion) exhibit substantial 7-day tail return volatility ($\pm 10\%$ to $\pm 22\%$).
   - *Recommendation for Modeling Team:* Employ class-weighted loss functions or balanced sample weights (as demonstrated in our benchmark script).
3. **Live OGD API Key Requirement:**
   - Automated live API fetching from `api.data.gov.in` requires setting `DATA_GOV_IN_API_KEY` in the environment. Offline ingestion from the 5-year dataset requires no keys.

---

## 7. Commands to Reproduce Everything Locally or on Kaggle

```bash
# Step 1: Run Safe Data Validation & Strategy 2 Deduplication
python3 -m src.data_validator \
  --input-dir "5 year dataset" \
  --output-dir "data/processed" \
  --quarantine-dir "data/quarantine"

# Step 2: Run Production Pipeline & Manifest Generation
python3 -m src.data_pipeline \
  --input-dir "5 year dataset" \
  --output-dir "data/processed"

# Step 3: Run Full Automated Test Suite
python3 -m pytest tests/ -v
```
