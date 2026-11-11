# Mandi Prediction — Data Status & Provenance Specification

**Repository:** `ankit-choubey/Mandi_Prediction`  
**Branch:** `dev`  
**Reference HEAD:** `14d30f22473441c059bbd37c04c8e993bad2a593`  
**Audit Date:** October 2026  
**Objective:** Provide a definitive, auditable classification of all datasets across the repository, distinguishing real observed data, published benchmarks, synthetic scenario files, and schemas, while establishing strict rules for permitted empirical use.

---

## 1. Provenance & Authenticity Classification Standard

Every data asset consumed, generated, or referenced by the repository is classified into exactly one of five authenticity tiers:

| Status Code | Description | Permitted Empirical Use |
|---|---|---|
| `REAL_OBSERVED` | Primary data collected from physical sensor, meter, or recorded transaction logs. | **PERMITTED** (Subject to deduplication and causal temporal alignment). |
| `REAL_PUBLISHED` | Official statistics, statutory circulars, gazettes, or authoritative peer-reviewed monographs. | **PERMITTED** for parameter calibration and economic hurdle rate calculations. |
| `DERIVED_ESTIMATE` | Mathematically derived signals computed strictly from real observed inputs without forward leakage. | **PERMITTED** if computed causally. |
| `SYNTHETIC_SCENARIO` | Simulated, formula-generated, or hand-coded values created for stress testing or pipeline interface demonstration. | **STRICTLY PROHIBITED** from empirical model training, validation, or backtesting. |
| `SCHEMA_ONLY` | Structural template, mock payload, or interface specification file without empirical data points. | **STRICTLY PROHIBITED** from empirical model training. |

> [!IMPORTANT]
> **Integrity vs. Authenticity Rule:**  
> A cryptographic checksum (SHA-256) proves file integrity relative to the point of checksum generation; it does **not** independently prove source authenticity or official origin. Source authenticity requires direct evidence of publication, extraction receipts, or authenticated API transmission.

---

## 2. Central Data Provenance Inventory

The following table documents all 15 datasets present in the repository, along with their verified authenticity status, SHA-256 checksums, limitations, and permitted use.

| Dataset / File Path | Authenticity Status | Source Authority & License | Coverage & Units | SHA-256 Checksum (Full Content) | Permitted Use & Operational Constraints |
|---|---|---|---|---|---|
| `data/raw/Gaziabaad.csv` | `REAL_OBSERVED` *(Download provenance: UNRESOLVED)* | DMI, MoA&FW / data.gov.in (NDSAP Open License) | 2024-09-01 to 2026-09-01; Ghaziabad (8 mandis); INR/quintal | `71601f993e07efa146f126747245a7fffb608a307abdea579475ba19bfeb0251` | Permitted for data cleaning, feature engineering, and modeling post-deduplication. **Lacks download receipts.** |
| `data/raw/Jhansi.csv` | `REAL_OBSERVED` *(Download provenance: UNRESOLVED)* | DMI, MoA&FW / data.gov.in (NDSAP Open License) | 2024-09-01 to 2026-09-01; Jhansi (15 mandis); INR/quintal | `7d0808d8d32555212af546004195c0ccf58e368106daad67169a231e80988a5c` | Permitted post-cleaning. Filter 1 corrupted row with `Max_Price=0`. **Lacks download receipts.** |
| `data/raw/Kanpur.csv` | `REAL_OBSERVED` *(Download provenance: UNRESOLVED)* | DMI, MoA&FW / data.gov.in (NDSAP Open License) | 2024-09-01 to 2026-09-01; Kanpur (9 mandis); INR/quintal | `0eb17704ebba1f66b8c9ef660f48dabc3665ea4691ed3b8aa20a49df8528d04a` | Permitted post-cleaning. Filter 4 corrupted rows with `Max_Price=0`. Disambiguate Varipaal/Baripaal alias. **Lacks download receipts.** |
| `data/raw/Lukhnow.csv` | `REAL_OBSERVED` *(Download provenance: UNRESOLVED)* | DMI, MoA&FW / data.gov.in (NDSAP Open License) | 2024-09-01 to 2026-09-01; Lucknow (4 mandis); INR/quintal | `6ca52743cc2f9059bf1e3b919b25317aa367f580bbafa6f62adb9db1d759bb13` | Permitted post-cleaning. Standardize district string to `Lucknow`. **Lacks download receipts.** |
| `data/raw/Unnao.csv` | `REAL_OBSERVED` *(Download provenance: UNRESOLVED)* | DMI, MoA&FW / data.gov.in (NDSAP Open License) | 2024-09-01 to 2026-09-01; Unnao (6 mandis); INR/quintal | `d4ee358b96cad3a888e4a92acd993327e56c4dc6af6eb60814193f98f591cebc` | Permitted post-cleaning. Filter 1 row with `Max_Price=0`. Note 204-day Purwa reporting gap. **Lacks download receipts.** |
| `suryansh - work/dataset_research/raw_external/nasa_power_weather_up_2024_2026.csv` | `REAL_OBSERVED` *(Verified API harvest)* | NASA Langley Research Center POWER Project (Open Public Domain) | 2024-09-01 to 2026-09-01; 5 UP district centroids; mm, deg C, % | `698601f153e3f8c9565747fda0dafbec5d31d64e3caf19a63ffce489af5572e1` | Permitted for weather feature extraction. **Must treat missing values (-999) as NaN, not 0.0 mm dry days. Lags must be calendar-based.** |
| `suryansh - work/dataset_research/raw_external/quarantine/SYNTHETIC_ceda_calibrated_mandi_arrivals_up_2024_2026.csv` | `SYNTHETIC_SCENARIO` *(QUARANTINED)* | Generated locally via parametric formula (`seed=42`) | 2024-09-01 to 2026-09-01; 21 mandis; Quintals | `c0c006a69da392c0ad52a77e544bf48290b6af31591d373b11b437082bf52ccb` | **QUARANTINED & BLOCKED.** Scenario stress testing and pipeline interface mocking only. **NEVER** for empirical training or evaluation. |
| `suryansh - work/dataset_research/raw_external/quarantine/SYNTHETIC_des_up_district_crop_production_statistics.csv` | `SYNTHETIC_SCENARIO` *(QUARANTINED)* | Hardcoded Python dictionary list | Crop Years 2024 & 2025; 5 UP districts; Ha, MT, kg/ha | `7651053e6e9871a63e1d401da91ac1d15afa8b31b13ea86e702c7d87397f30cf` | **QUARANTINED & BLOCKED.** Pipeline interface demonstration only. **NEVER** for empirical training or evaluation. |
| `suryansh - work/dataset_research/samples/sample_cwc_warehouse_tariffs.csv` | `REAL_PUBLISHED` | Central Warehousing Corporation (CWC) Tariff Circulars FY 25-26 | FY 2025-26 rate card; INR/bag/month | `d05cba80c8a4e89257d217c5a797b12239d83dead66151b568bdf43f7b734da0` | Permitted for parameterizing base storage tariffs in economic break-even equations. |
| `suryansh - work/dataset_research/samples/sample_icar_ciphet_loss_benchmarks.csv` | `REAL_PUBLISHED` | ICAR-CIPHET National Post-Harvest Loss Studies (2015, 2022) | Representative national agro-climatic zones; Loss % | `201b76bf620377583441ad92b4ec8b76f3dfe481ea14b9c56469c6323aa0ac7f` | Permitted for bounding physiological weight loss ($L$) in storage hurdle rate calculations. |
| `suryansh - work/dataset_research/samples/sample_ceda_arrival_spec.json` | `SCHEMA_ONLY` | CEDA Ashoka University / AGMARKNET API Spec | Query payload specification template | `1ef0c9ba1da358ceb574b1b76fd129315aee60d97e0184e638850c72e11b988e` | Permitted for testing API contract and mock responses only. |
| `suryansh - work/dataset_research/samples/sample_upag_statistics_spec.json` | `SCHEMA_ONLY` *(Circular values)* | UPAg Ministry of Agriculture Spec | Query payload template (mirrors script values) | `bdf827a99d7d353cce6f938b05de5bd7d0ca3242d48d1dfd0a99e1f444b4d3b0` | Permitted for testing API schema parser only. |
| `suryansh - work/dataset_research/samples/sample_open_meteo_weather.json` | `REAL_OBSERVED` *(API Probe)* | Open-Meteo GmbH (ODbL License) | Sample probe 2024-09-01 to 2024-09-07; Kanpur | `eba40f1de4b5106baae453979947bf60ec43565dcea687ed07be97ebb29453a7` | Permitted for API latency and schema benchmarking only. |
| `suryansh - work/dataset_research/samples/sample_agmarknet_ogd_price.csv` | `REAL_OBSERVED` *(Sample)* | DMI, MoA&FW / data.gov.in | 5 sample transaction records; INR/quintal | `6343f853ad89bafb1cb7b745884a93e589dd1b8f1c0696f8da74a8b1ad79d7ff` | Unit testing and schema compliance checks only. |
| `suryansh - work/dataset_research/samples/sample_nasa_power_weather.csv` | `REAL_OBSERVED` *(Sample)* | NASA POWER Agroclimatology | 5 sample daily weather rows; mm, deg C | `14618c45c08a8298d988ccbafa826dfb505bfea6a9ceca9af46aca045799b56d` | Unit testing and schema compliance checks only. |

---

## 3. Quarantining of Formula-Generated & Hardcoded Datasets

### 3.1 CEDA Calibrated Mandi Arrivals Proxy
- **Physical Relocation:** Moved from `suryansh - work/dataset_research/raw_external/` into `suryansh - work/dataset_research/raw_external/quarantine/SYNTHETIC_ceda_calibrated_mandi_arrivals_up_2024_2026.csv`.
- **Generation Evidence:** Lines 135–160 of `suryansh - work/experiments/execute_track_b_unexecuted_items.py` confirm:
  $$\text{Arrival\_Quantity\_Qtl} = \text{base\_qtl} \times \text{season\_mult} \times \text{depth\_mult} \times \text{np.random.lognormal}(0, 0.25)$$
- **Reason for Quarantine:** The live CEDA endpoint (`POST /v1/agmarknet/quantities`) returned `HTTP 401 Unauthorized`. To continue development, the prior author substituted a formula with fixed random seed `42`. This dataset does not represent physical trucks or mandi arrivals.
- **Enforcement:** Quarantined with `SYNTHETIC_` prefix. Pipeline loaders and unit tests actively assert that no file in `quarantine/` can be read as a feature input.

### 3.2 DES/UPAg District Crop Production Statistics
- **Physical Relocation:** Moved into `suryansh - work/dataset_research/raw_external/quarantine/SYNTHETIC_des_up_district_crop_production_statistics.csv`.
- **Generation Evidence:** Lines 47–97 of `suryansh - work/experiments/execute_track_b_unexecuted_items.py` confirm 40 hardcoded dictionary rows. The UPAg API (`POST /v1/upag/api-data-share/login`) returned `HTTP 401 Unauthorized`.
- **Reason for Quarantine:** The numbers are illustrative hand-entered values without verifiable publication references, gazette citations, or API query receipts.
- **Enforcement:** Quarantined with `SYNTHETIC_` prefix and excluded from all feature sets.

---

## 4. Status of the Five Raw Price Files (`data/raw/*.csv`)

1. **Integrity Verified:**
   All 160,192 records across `Gaziabaad.csv`, `Jhansi.csv`, `Kanpur.csv`, `Lukhnow.csv`, and `Unnao.csv` have zero null values, zero unparseable dates, and continuous 731-day temporal coverage (2024-09-01 to 2026-09-01). Checksums are documented in Section 2.
2. **Download Provenance Unresolved:**
   While the schema and fields align with OGD platform Resource `9ef84268-d588-465a-a308-a864a43d0070`, **the repository contains no API download script, curl log, HTTP response header, or extraction timestamp** proving when, how, or from which server credentials these files were retrieved.
3. **Evidence Required for Full Source Verification:**
   - Script or automated ingestion query that pulled the records from `data.gov.in`.
   - API response headers or signed export manifest from the Directorate of Marketing & Inspection (DMI).
   - Independent verification against an authoritative AGMARKNET database snapshot for the identical date window.

---

## 5. Machine-Readable Provenance Artifacts

A machine-readable version of this inventory is permanently maintained in the repository:
- `data_inventory.json` (Structured JSON specification with complete metadata and hashes)
- `data_inventory.csv` (Tabular format for automated ingestion and testing)
