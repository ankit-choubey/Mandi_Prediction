# MP-DATA-008 Completion & Verification Summary

**Task:** MP-DATA-008 — Newest Real-Data Index, Missing-Data Policy & Forecasting Feature Contract  
**Execution Date:** 2026-11-12 IST  
**Git Baseline Commit:** `d8f689a90f89762035aa41f651c26ee2e84dbed5`  
**Execution Mode:** Local-only deterministic validation & configuration preparation  

---

## 1. Executive Summary

Task MP-DATA-008 completed the dataset-first latest-observation infrastructure, repaired operational boundaries, froze the missing-data and temporal evaluation contract for Step 7 continuous price forecasting, and implemented the shared causal feature builder.

### Key Deliverables Completed
1. **Source Inventory & Explicit Configuration:** Formatted and validated `data/reference/operational_sources.json` configuring 11 operational sources with explicit byte counts, SHA-256 hashes, observed date ranges, units, and roles (`HISTORY` vs `LATEST_SNAPSHOT`).
2. **Operational Bug Fixes:**
   - Eliminated silent 25,000-row prefix scan in `CurrentDataReporter.query_latest_observation`. Direct queries now query `data/imported_snapshots/latest_observation_index.json` or enforce $\le 10$ MB / $\le 50,000$ row budgets strictly.
   - Added official `.xlsx` reader in `execute_file_import` supporting title rows and Agmarknet headers, while rejecting unsupported extensions with explicit `ValueError`.
   - Exposed dataset-first CLI arguments (`--import-config`, `--publish-index`) and clear no-argument mode help.
   - Implemented independent `last_successful_import.json` pointer and `load_prior_validated_import` fallback loader without advancing live-success index.
   - Implemented composite SHA-256 hashing and multi-file source linkage.
3. **Published Latest Observation Index:** Ingested real snapshot `data/raw_external/9ef84268-d588-465a-a308-a864a43d0070.csv` (1,202,750 bytes, SHA `3d3bc047...`) and published `data/imported_snapshots/latest_observation_index.json` containing 30 series identities (26 accepted, 4 quarantined for unknown market review).
4. **Missing-Data & Forecast Feature Contract:** Authored `documentation/FORECAST_DATA_FEATURE_CONTRACT.md` and machine-readable `experiments/configs/price_forecast_v1.json` specifying Horizon 7, nearest observed in $[t+6, t+8]$ with earlier tie-break, retrospective availability at 06:00 IST issue time, serving denials, and Tier A/B eligibility.
5. **Shared Causal Feature Builder:** Created `src/forecast_features.py` implementing 21 deterministic price-only and temporal features with exact batch/inference equivalence, calendar lags ($1, 3, 7, 14, 28$), preceding rolling windows ($7\text{d}, 30\text{d}$), and sample variance burn-in.

---

## 2. Real Snapshot Ingestion Evidence

- **Snapshot File:** `data/raw_external/9ef84268-d588-465a-a308-a864a43d0070.csv`
- **File Size:** Exactly 1,202,750 bytes (within $\le 10$ MB local limit)
- **Total Records in File:** 11,720 rows (within $\le 50,000$ rows budget)
- **File SHA-256:** `3d3bc047440186eed49a8764eb28387a99e7293cdc9b62f1d30290b855fedb11`
- **Observation Date:** `2026-11-11` (single trading date)

### Reconciliation & Arithmetic Balancing
$$\text{Total Records Fetched} = 11,720$$
$$\text{Records Accepted} = 26$$
$$\text{Records Quarantined} = 11,694$$
$$\text{Records Duplicate} = 0$$
$$\text{Discrepancy} = 11,720 - (26 + 11,694 + 0) = 0 \quad (\text{Strictly Balanced})$$

### District Breakdown
| District | Fetched | Accepted | Quarantined | Quarantined Reasons |
| :--- | :---: | :---: | :---: | :--- |
| **Ghaziabad** | 3 | 3 | 0 | None |
| **Jhansi** | 7 | 7 | 0 | None |
| **Kanpur** | 7 | 5 | 2 | 2 $\times$ `UNKNOWN_MARKET_REVIEW` (Baripaal APMC) |
| **Lucknow** | 4 | 4 | 0 | None |
| **Unnao** | 9 | 7 | 2 | 2 $\times$ `UNKNOWN_MARKET_REVIEW` (Purwa APMC) |
| *Out-of-Scope (All others)* | 11,690 | 0 | 11,690 | `OUT_OF_SCOPE_DISTRICT` |
| **Total** | **11,720** | **26** | **11,694** | **100% Accounted** |

### Focus Crop Coverage (2026-11-11)
- **Focus Crops Definition:** Exactly Wheat, Potato, Onion, Tomato, Paddy(Dhan)(Common), Rice. (Mustard and Basmati are not focus crops; initial mention corrected).
- **Potato (4 accepted):** Ghaziabad (Rs. 950/Q), Kanpur(Grain) (Rs. 550/Q), Uttaripura (Rs. 500/Q), Lucknow (Rs. 850/Q).
- **Onion (1 accepted):** Kanpur(Grain) (Rs. 3000/Q).
- **Wheat (1 accepted):** Unnao APMC (Rs. 2500/Q).
- **Paddy(Dhan)(Common) (3 accepted, 2 quarantined):** Kanpur(Grain) (Rs. 2000/Q), Unnao (Rs. 2000/Q, Rs. 2025/Q); Baripaal APMC and Purwa APMC quarantined for unknown market review. (Preserved distinct from Rice without equating identities).
- **Tomato & Rice (Milled):** 0 observations in target districts in the 2026-11-11 snapshot. Missing snapshot rows reflect single-day absence from this specific file, not proof of zero real trading. Extrapolation warning applies.

---

## 3. Shared Causal Feature Builder (`src/forecast_features.py`)

- **Code Version:** `1.0.0`
- **Source Code Hash:** `a4f365f7d5ca93740e53e4b78fa189689531109403a45c36582531da1f31f9b3`
- **Total Features:** 21 deterministic price-only and temporal features
- **Causality Proof:** For any origin date $t$, features observe history strictly dated $\le t$. Future row additions, deletions, or target mutations do not alter computed feature vectors.
- **Batch / Inference Equivalence:** For any series and origin date, `compute_batch_features(df)` yields identical feature values to `compute_origin_features(history, t, series)`.

