# Quarantined Synthetic Datasets

> [!WARNING]
> The files in this directory are **SYNTHETIC / ILLUSTRATIVE ONLY** and are strictly **EXCLUDED** from all empirical models, benchmarks, and production pipelines.

## Quarantined Datasets

1. **`SYNTHETIC_ceda_calibrated_mandi_arrivals_up_2024_2026.csv`**
   - **Original file:** `suryansh - work/dataset_research/raw_external/ceda_calibrated_mandi_arrivals_up_2024_2026.csv`
   - **Authenticity Status:** `SYNTHETIC_SCENARIO`
   - **Generation Mechanism:** Generated in `suryansh - work/experiments/execute_track_b_unexecuted_items.py` (lines 135-160) using a parametric formula:
     $$\text{Arrival\_Qtl} = \text{base\_qtl} \times \text{season\_mult} \times \text{depth\_mult} \times \text{Lognormal}(0, 0.25)$$ with fixed random seed `42`.
   - **Reason for Quarantine:** Not observed market arrivals from CEDA or AGMARKNET. CEDA API requests returned `HTTP 401 Unauthorized`.
   - **Permitted Use:** Illustrative scenario simulation / stress testing code paths only. **NEVER** for empirical training, validation, or backtesting.

2. **`SYNTHETIC_des_up_district_crop_production_statistics.csv`**
   - **Original file:** `suryansh - work/dataset_research/raw_external/des_up_district_crop_production_statistics.csv`
   - **Authenticity Status:** `SYNTHETIC_SCENARIO` (Hardcoded estimates)
   - **Generation Mechanism:** Hardcoded in `suryansh - work/experiments/execute_track_b_unexecuted_items.py` (lines 47-97) as a static Python dictionary list.
   - **Reason for Quarantine:** UPAg/DES portal access was blocked (`HTTP 401 Unauthorized`). The numbers were hand-entered illustrative figures without an official API provenance trail or verification against published DES APY gazettes.
   - **Permitted Use:** Schema demonstration and pipeline interface testing only. **NEVER** for empirical modeling.
