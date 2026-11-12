# Kaggle Remote Execution Report: Task MP-DATA-003B

**Task ID:** MP-DATA-003B  
**Execution Timestamp:** 2026-11-12T01:42:28Z  
**Execution Environment:** Kaggle CPU Kernel (Internet Disabled)  
**Kernel ID:** `theankitchoubey/mp-data-003b-price-profile` (Version 2)  
**Dataset ID:** `theankitchoubey/mandi-prediction-audit-003b` (Version 1, 30 files, 101.32 MB)  
**Status:** `KernelWorkerStatus.COMPLETE` (Exit Code 0)  
**Runtime:** Python 3.13.18, Linux (GCC 13.3.0), Pandas 2.3.3, NumPy 2.1.3, OpenPyXL 3.1.5, Scikit-Learn 1.6.1, SciPy 1.16.3  
**Random Seed:** 42  

---

## 1. Executive Summary

This report documents the first remote execution on Kaggle for Task `MP-DATA-003B`. The remote kernel executed four independent verification protocols without modifying any pipeline source code:
1. **Row-Level Disposition Proof:** Audited and reconciled all 472,385 raw price records from the 5-year historical raw dataset into mutually exclusive, collectively exhaustive buckets. Proved exact multiset identity between the pipeline's surviving records and the committed `data/processed/mandi_5year_validated.csv`.
2. **Series Eligibility Profiling:** Profiled all 1,297 retained commodity-market series across five districts, establishing empirical distributions of observation counts, calendar spans, gaps, and coverage shares.
3. **Agmarknet Daily Excel Corroboration:** Cross-verified panel prices against external Agmarknet daily price arrival reports (`raw_downloads/*.xlsx`, 16,030 records), demonstrating 99.39% exact concordance on natural key matches and identifying 1,289 records post-dating the panel cutoff.
4. **CEDA Price Data Corroboration:** Cross-verified panel prices against external CEDA price data (`ceda price data.csv`, 594 records for Lucknow Wheat), demonstrating 100.00% exact concordance on matched records and proving that the 3 unmatched records were quarantined under pipeline Strategy 2.

> **Provenance Qualification:** Historical price panel provenance is **PARTIALLY CORROBORATED** for the scopes tested only: five focus crops (Wheat, Potato, Onion, Tomato, Rice) across `2025-11-07` to `2026-09-30` from Agmarknet Excel reports, and Lucknow Wheat across `2024-10-30` to `2025-10-30` from CEDA price data. Observations outside these specific temporal and commodity windows remain uncorroborated. The panel must not be characterized as fully authenticated.

---

## 2. Row-Level Disposition & Multiset Verification

### 2.1 Mathematical Conservation Identity
Every raw record was accounted for with zero leakage:
$$\text{Total Raw Rows (472,385)} = \text{Accepted (462,350)} + \text{Invalid (27)} + \text{Conflicting (2,936)} + \text{Low-Obs Dropped (7,072)} + \text{Exact Dupes (0)}$$

* **Conservation Check:** $462,350 + 27 + 2,936 + 7,072 + 0 = 472,385$ (**VERIFIED TRUE**)
* **Multiset Identity Check:** Comparing the 462,350 accepted rows against committed `data/processed/mandi_5year_validated.csv` across all common natural key and price columns yielded **0 discrepancies** (**VERIFIED TRUE**).

### 2.2 Per-File Raw Disposition Breakdown

| District Raw File | Raw Rows | Invalid Dropped | Conflicting Quarantined | Low-Obs Dropped | Accepted Panel Rows | Primary Invalid Reason |
|---|---|---|---|---|---|---|
| `GHAZIABAD.csv` | 132,478 | 4 | 938 | 2,412 | 129,124 | Non-positive modal price ($\le 0$) |
| `JHANSI.csv` | 83,972 | 13 | 412 | 1,189 | 82,358 | Non-positive modal price ($\le 0$) |
| `KANPUR.csv` | 113,319 | 9 | 741 | 1,824 | 110,745 | Non-positive modal price ($\le 0$) |
| `LUKHNOW.csv` | 54,876 | 0 | 382 | 811 | 53,683 | None (0 invalid) |
| `UNNAO.csv` | 87,740 | 1 | 463 | 836 | 86,440 | Non-positive modal price ($\le 0$) |
| **Total** | **472,385** | **27** | **2,936** | **7,072** | **462,350** | **100% Accounted** |

*Note:* `low_obs_dropped_rows.csv` (7,072 data rows + header = 7,073 lines) was exported and verified.

---

## 3. Series Eligibility Profile (1,297 Retained Series)

Across the 5 districts, 41 distinct markets, and 108 distinct commodities:

| Metric | Min | P10 | P25 | Median (P50) | Mean | P75 | P90 | Max |
|---|---|---|---|---|---|---|---|---|
| **Observation Count** | 20.0 | 29.0 | 48.0 | 139.0 | 356.5 | 569.0 | 1,177.4 | 1,426.0 |
| **Calendar Span (Days)** | 21.0 | 76.0 | 197.0 | 334.0 | 706.9 | 1,459.0 | 1,525.0 | 1,527.0 |
| **Coverage Share** | 0.0198 | 0.1345 | 0.2385 | 0.4663 | 0.4784 | 0.7162 | 0.8228 | 0.9720 |
| **Longest Gap (Days)** | 2.0 | 5.0 | 9.0 | 21.0 | 94.1 | 102.0 | 283.8 | 1,289.0 |
| **Missing Days** | 1.0 | 27.0 | 93.0 | 174.0 | 350.4 | 542.0 | 986.0 | 1,468.0 |

*Note:* `series_eligibility.csv` (1,297 data rows + header = 1,298 lines) was exported and verified.

---

## 4. Price Corroboration

### 4.1 Agmarknet Daily Excel Reports vs Panel
* **Source Files:** 5 Agmarknet Excel files covering `2025-11-07` to `2026-11-06` (16,030 total rows).
* **Records Post-Panel Cutoff:** 1,289 rows across 27 distinct calendar dates (`2026-10-01` to `2026-11-06`) exist in the Excel files but are outside the 5-year panel window (`2021-09-01` to `2026-09-30`).
* **Matched Natural Key Rows:** 12,602 rows.
* **Exact Price Matches:** 12,525 rows (**99.39% concordance**).
* **Median Price Difference:** ₹0.00.
* **Discrepancy Distribution:** Exactly 77 rows exhibited non-zero price differences across the matched panel window. Discrepancies by district and crop are: Ghaziabad Potato: 23, Lucknow Rice: 16, Lucknow Wheat: 7, Ghaziabad Onion: 5, Ghaziabad Rice: 5, Ghaziabad Tomato: 4, Kanpur Onion: 3, Jhansi Wheat: 3, Kanpur Rice: 2, Kanpur Wheat: 2, Lucknow Onion: 2, Unnao Wheat: 2, Kanpur Potato: 1, Lucknow Potato: 1, and Lucknow Tomato: 1 (total: 77). All 77 rows are captured in `corroboration_diff_sample.csv`.

#### Commodity-District Concordance Breakdown

| District | Commodity | Matched Rows | Exact Match Count | Exact Match % | Mean Diff (₹) | Median Diff (₹) |
|---|---|---|---|---|---|---|
| Ghaziabad | Onion | 350 | 345 | 98.57% | -0.33 | 0.00 |
| Ghaziabad | Potato | 533 | 510 | 95.68% | -0.01 | 0.00 |
| Ghaziabad | Rice | 311 | 306 | 98.39% | -2.37 | 0.00 |
| Ghaziabad | Tomato | 416 | 412 | 99.04% | 1.10 | 0.00 |
| Ghaziabad | Wheat | 617 | 617 | 100.00% | 0.00 | 0.00 |
| Jhansi | Onion | 186 | 186 | 100.00% | 0.00 | 0.00 |
| Jhansi | Potato | 114 | 114 | 100.00% | 0.00 | 0.00 |
| Jhansi | Tomato | 312 | 312 | 100.00% | 0.00 | 0.00 |
| Jhansi | Wheat | 2,042 | 2,039 | 99.85% | -0.04 | 0.00 |
| Kanpur | Onion | 372 | 369 | 99.19% | 0.21 | 0.00 |
| Kanpur | Potato | 696 | 695 | 99.86% | 0.00 | 0.00 |
| Kanpur | Rice | 405 | 403 | 99.51% | 5.64 | 0.00 |
| Kanpur | Tomato | 366 | 366 | 100.00% | 0.00 | 0.00 |
| Kanpur | Wheat | 1,788 | 1,786 | 99.89% | 0.06 | 0.00 |
| Lucknow | Onion | 160 | 158 | 98.75% | 0.04 | 0.00 |
| Lucknow | Potato | 223 | 222 | 99.55% | 0.00 | 0.00 |
| Lucknow | Rice | 575 | 559 | 97.22% | 40.36 | 0.00 |
| Lucknow | Tomato | 104 | 103 | 99.04% | -0.69 | 0.00 |
| Lucknow | Wheat | 1,049 | 1,042 | 99.33% | 0.06 | 0.00 |
| Unnao | Onion | 82 | 82 | 100.00% | 0.00 | 0.00 |
| Unnao | Potato | 246 | 246 | 100.00% | 0.00 | 0.00 |
| Unnao | Rice | 318 | 318 | 100.00% | 0.00 | 0.00 |
| Unnao | Tomato | 20 | 20 | 100.00% | 0.00 | 0.00 |
| Unnao | Wheat | 1,317 | 1,315 | 99.85% | 0.00 | 0.00 |

### 4.2 CEDA Price Data vs Panel (Lucknow Wheat)
* **Source File:** `ceda price data.csv` (594 rows, covering `2024-10-30` to `2025-10-30`).
* **Matched Rows:** 591 rows.
* **Exact Price Matches:** 591 rows (**100.00% concordance**).
* **Mean Difference:** ₹0.0000.
* **Unmatched Rows:** Exactly 3 rows:
  1. `2024-11-07` (Banthara, Wheat, Dara, Modal Price: 2,853): Quarantined under Strategy 2 (6 conflicting rows found on this date in `quarantined_conflicting_records.csv`).
  2. `2025-03-24` (Lucknow, Wheat, Dara, Modal Price: 2,880): Quarantined under Strategy 2 (2 conflicting rows found on this date in `quarantined_conflicting_records.csv`).
  3. `2025-06-27` (Banthara, Wheat, Dara, Modal Price: 2,582): Quarantined under Strategy 2 (2 conflicting rows found on this date in `quarantined_conflicting_records.csv`).
* **Resolution:** Exactly 3 CEDA records did not match the validated panel; for all 3 records, conflicting records on the identical date were identified in `data/quarantine/quarantined_conflicting_records.csv`, demonstrating that the pipeline's Strategy 2 quarantine rule was applied as designed (this confirms rule execution fidelity, not that the quarantine rule itself is optimal or correct).

---

## 5. Artifact Verification & Hashes

All 7 output artifacts generated by the remote kernel were downloaded to `experiments/outputs/003b/` and verified:

| Artifact Filename | Size (Bytes) | Line Count | SHA-256 Digest |
|---|---|---|---|
| `low_obs_dropped_rows.csv` | 1,107,461 | 7,073 | `b0f0ea08e67c67f41acbab18e7239fafb9641b33d9cbf528c52950d1facf158c` |
| `series_eligibility.csv` | 174,644 | 1,298 | `deaca152a5db96d7edc0deb009034a463c1110448591360aec4ad5591c516b48` |
| `corroboration_diff_sample.csv` | 6,385 | 78 | `e82ab3bb4e1a6a7058d20032b915513594bea0a51edf83d7d6f2a88880e828c7` |
| `disposition_summary.json` | 1,710 | N/A | `362c7923cf77dd17cec1ef722eabf7bef1d1d59a52438afc3737435da068c7b6` |
| `series_profile_summary.json` | 1,330 | N/A | `3690179c2a2f07ca88b6c5fcfc22b7ea236a880614037ecaa3d3b5e532d39d9f` |
| `excel_corroboration_summary.json` | 7,164 | N/A | `05fefe69f9dd783f18ecd2ef9788aeafab8196127de58107bcb63ed92d67c32e` |
| `ceda_corroboration_summary.json` | 1,424 | N/A | `5dc430161519139e9e42c2183ecf7d1a3523959666248d9d8992e06601b4e172` |
