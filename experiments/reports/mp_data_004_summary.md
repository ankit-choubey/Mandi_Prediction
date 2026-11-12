# Kaggle Remote Execution Report: Task MP-DATA-004

**Task ID:** MP-DATA-004  
**Title:** Explain gaps, define target contract, eligibility grids (Kaggle)  
**Execution Timestamp:** 2026-11-12T02:32:07Z  
**Execution Environment:** Kaggle CPU Kernel (Internet Disabled)  
**Kernel ID:** `theankitchoubey/mp-data-004-eligibility-grids` (Version 2)  
**Dataset ID:** `theankitchoubey/mandi-prediction-audit-003b` (Version 1, existing private dataset, 30 files, 101.32 MB)  
**Status:** `KernelWorkerStatus.COMPLETE` (Exit Code 0)  
**Runtime:** Python 3.13.18, Linux (GCC 13.3.0), Pandas 2.3.3, NumPy 2.1.3, OpenPyXL 3.1.5, Scikit-Learn 1.6.1, SciPy 1.16.3  
**Random Seed:** 42  

---

## 1. Executive Summary

Task `MP-DATA-004` executed remotely on Kaggle to investigate the remaining data corroboration gaps, evaluate forward target availability across multiple forecasting contracts, quantify series eligibility across a multi-dimensional parameter grid, and evaluate chronological train/test split feasibility.

All computations were performed without modifying repository pipeline code or uploading new datasets.

---

## 2. Classification of Unmatched Agmarknet Excel Records (2,139 Rows)

Of the 16,030 total Agmarknet daily price arrival report rows (`raw_downloads/*.xlsx`), 1,289 post-date the validated panel cutoff (`2026-09-30`), leaving **14,741 records inside the historical panel window**. Of these, 12,602 records matched the validated panel on the canonical 6-part natural key (`District_Std`, `Market`, `Commodity_Std`, `Variety`, `Grade`, `Arrival_Date`).

The remaining **2,139 unmatched Excel rows** were classified into four mutually exclusive categories:

| Unmatched Category | Rows | Share (%) | Description & Empirical Evidence |
|---|---|---|---|
| `key_in_low_obs_drops` | **1,365** | 63.81% | Series was present in the raw 5-year files, but had $<20$ historical observations across the 5 years and was dropped by the pipeline's series filter. |
| `key_in_quarantined_conflicts` | **326** | 15.24% | Record was present in the raw 5-year data on that exact natural key and date, but was quarantined under Strategy 2 due to conflicting same-grade price quotes. |
| `key_in_raw_diff_spelling` | **281** | 13.14% | A record exists in the raw 5-year data on that `(District, Commodity, Arrival_Date)`, but differs in Market name, Variety spelling, or Grade classification. |
| `absent_from_raw_files` | **167** | 7.81% | No raw 5-year record exists on that `(District, Commodity, Arrival_Date)` in the portal raw price files. |
| **Total Unmatched** | **2,139** | **100.00%** | All 2,139 unmatched records accounted for. |

*Sample Export:* The first 2,000 unmatched records were exported to [`unmatched_excel_sample.csv`](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/experiments/outputs/004/unmatched_excel_sample.csv) (161,802 bytes, 2,001 lines).

---

## 3. Detailed Profile of the 77 Price Differences

Across the 12,602 natural key matched records, 12,525 records (99.39%) matched the validated panel modal price exactly. Exactly 77 records exhibited non-zero price differences:

### 3.1 Size Distribution of Differences ($\Delta P = P_{excel} - P_{panel}$)

| Statistic | Value (₹ / Quintal) |
|---|---|
| **Count** | 77 rows |
| **Mean Difference** | +₹327.12 |
| **Standard Deviation** | ₹1,436.47 |
| **Minimum Difference** | -₹8,634.10 |
| **10th Percentile (P10)** | -₹96.51 |
| **25th Percentile (P25)** | -₹27.07 |
| **Median Difference (P50)** | +₹20.40 |
| **75th Percentile (P75)** | +₹293.66 |
| **90th Percentile (P90)** | +₹2,029.93 |
| **Maximum Difference** | +₹4,342.42 |
| **Mean Absolute Difference ($|\Delta P|$)** | ₹605.17 |
| **Median Absolute Difference** | ₹78.38 |

### 3.2 Quarantine Match & Temporal Bounds
* **Match Against Quarantined Conflicting Prices:** **0 of the 77 rows** matched any quarantined price quote on that natural key. These discrepancies represent surviving single-quote records where the portal export differed from the 5-year raw dump.
* **Dates Involved:** Exactly 27 distinct calendar dates, all concentrated between `2026-02-22` and `2026-03-31` (Feb–March 2026).

---

## 4. Quarantine Adjudication Test (Report Only — No Rule Change)

To evaluate how simple deterministic resolution rules would behave compared to the current Strategy 2 policy (quarantining all ambiguous same-grade quotes on the same date), the conflicting groups in `quarantined_conflicting_records.csv` were tested against overlapping external reference prices from the Agmarknet Excel reports and CEDA price data.

* **Total Quarantined Conflict Groups:** 1,457 natural-key date groups.
* **Groups Overlapping External Reference Data:** 329 groups.

### Rule Concordance Comparison

| Candidate Adjudication Rule | Matches with Reference ($P_{rule} == P_{ref}$) | Concordance Rate (%) | Practical Significance |
|---|---|---|---|
| **`last`** (Last record in file) | **191 / 329** | **58.05%** | Highest concordance; reflects closing or final updated portal quote. |
| **`max`** (Highest modal price) | 174 / 329 | 52.89% | Frequently aligns with premium lot or final quote. |
| **`min`** (Lowest modal price) | 153 / 329 | 46.50% | Aligns with base/opening trade quote. |
| **`first`** (First record in file) | 137 / 329 | 41.64% | Often reflects preliminary morning or early trade entry. |
| **`median`** (Median of conflicting quotes) | 3 / 329 | 0.91% | Rarely matches physical trade quotes. |
| **`mean`** (Rounded mean of conflicting quotes) | 2 / 329 | 0.61% | Fails almost completely; physical mandi prices are discrete bids. |

*Finding:* Synthetic averaging (`mean` or `median`) fails to reflect actual reference transaction prices ($<1\%$ concordance). While `last` matches 58.05% of the time, 41.95% of groups still diverge, confirming that quarantining conflicting records remains necessary to avoid injecting unverified noise into downstream estimators.

---

## 5. Forward Target Availability Analysis

Evaluated across all 462,350 origin observations across the 1,297 retained series:

### 5.1 Overall Forward Availability Shares

| Target Horizon Definition | Qualifying Origins | Share of Panel Origins (%) |
|---|---|---|
| **Exact $T+7$ Observation** | 378,572 | **81.88%** |
| **Window $T+6 \dots T+8$ Observation** | 431,003 | **93.22%** |
| **Window $T+5 \dots T+9$ Observation** | 443,070 | **95.83%** |
| **Next Observation within 10 Days ($t_{next} - T \le 10$)** | 455,831 | **98.59%** |

### 5.2 Day-of-Week Distribution & Market Closure Effect

| Day of Week | Total Origins | Share Exact $T+7$ | Share $T+6 \dots T+8$ | Share $T+5 \dots T+9$ | Next $\le 10$ Days |
|---|---|---|---|---|---|
| **Monday** | 69,895 | 82.98% | 92.71% | 95.74% | 98.91% |
| **Tuesday** | 69,233 | 83.48% | 93.75% | 95.46% | 98.55% |
| **Wednesday** | 71,248 | 82.87% | 94.18% | 96.68% | 98.73% |
| **Thursday** | 65,742 | 81.89% | 94.53% | 97.08% | 99.07% |
| **Friday** | 75,405 | 82.31% | 92.11% | 94.35% | 97.20% |
| **Saturday** | 70,319 | 81.92% | 92.98% | 95.95% | 98.91% |
| **Sunday** | **40,508** | **74.59%** | 91.86% | 95.65% | 99.12% |

*Day-of-Week Insights:* Sunday origin volume is substantially lower (~40.5k vs ~70k on weekdays) due to statutory or customary Sunday APMC market closures. Sunday $T+7$ availability drops to 74.59% because the following Sunday is also typically closed. Conversely, allowing a narrow $\pm 1$ day window ($T+6 \dots T+8$) absorbs weekend closures, raising availability from 81.88% to 93.22%.

### 5.3 Observation Gap Patterns (461,053 Consecutive Pairs)
* **1-Day Gap (Consecutive Trading Days):** 77.92% of pairs
* **2-Day Gap (Single Closure / Weekend):** 14.15% of pairs
* **3+ Day Gap:** 7.92% of pairs
* **Gaps $> 7$ Days:** Only 1.58% of pairs
* **Summary Metrics:** Mean gap: 1.99 days, Median gap: 1.0 day, P90 gap: 2.0 days.

---

## 6. Multi-Dimensional Eligibility Grids

A 90-cell parameter grid was evaluated across all 1,297 series over four axes:
* **Min Observations ($N_{obs}$):** $[30, 60, 120, 250, 500]$
* **Min Calendar Coverage ($\text{cov} = N_{obs} / \text{span}$):** $[0.3, 0.5, 0.7]$
* **Max Longest Gap ($\text{gap}_{max}$):** $[14, 30, 60 \text{ days}]$
* **Recency Threshold:** Last observation $\ge 2026-08-31$ (30 days) or $\ge 2026-07-31$ (60 days)

### 6.1 Sample Grid Slices

| Min Obs | Min Cov | Max Gap | Recency | Qualifying Series | Qualifying Obs | Share of All Series (%) |
|---|---|---|---|---|---|---|
| **30** | 0.3 | 60 | 60d | 192 | 22,641 | 14.80% |
| **60** | 0.3 | 60 | 60d | 183 | 22,206 | 14.11% |
| **120** | 0.3 | 60 | 60d | 79 | 12,704 | 6.09% |
| **120** | 0.5 | 30 | 30d | 74 | 12,056 | 5.71% |
| **250** | 0.5 | 60 | 60d | 2 | 536 | 0.15% |
| **500** | 0.3 | 60 | 60d | 0 | 0 | 0.00% |

*Key Empirical Finding (The Inter-Season Gap Phenomenon):* Requiring $\text{gap}_{max} \le 60$ days across a multi-year panel abruptly eliminates almost all seasonal crop series. Agricultural crops in Uttar Pradesh naturally undergo 3–5 month inter-season gaps between harvesting cycles unless supported by year-round cold storage trading. Setting global gap thresholds without accounting for crop seasonality falsely penalizes valid seasonal series.

*Full Grid Export:* Exported to [`eligibility_grids.csv`](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/experiments/outputs/004/eligibility_grids.csv) (90 rows) and [`focus_crops_eligibility.csv`](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/experiments/outputs/004/focus_crops_eligibility.csv) (579 rows).

---

## 7. Chronological Train/Test Split Feasibility

* **Panel Date Span:** `2021-09-01` to `2026-09-30` (1,856 calendar days)
* **Training Window:** `2021-09-01` to `2025-12-18` (85% date threshold minus 8-day embargo)
* **Embargo Window:** `2025-12-19` to `2025-12-25` (7 days embargo + 1 day transition = 8 days total gap)
* **Test Evaluation Period (Final 15%):** `2025-12-26` to `2026-09-30` (279 calendar days)

### Feasibility by Candidate Eligibility Tier

| Candidate Tier | Tier Criteria | Total Qualifying Series | Series with $\ge 20$ Test Origins | Series with $\ge 50$ Test Origins | Mean Test Origins |
|---|---|---|---|---|---|
| **Inclusive** | $N_{obs} \ge 60, \text{cov} \ge 0.3, \text{gap} \le 60, \text{rec} \le 60$ | 183 | **183 (100.0%)** | **183 (100.0%)** | 119.6 |
| **Balanced** | $N_{obs} \ge 120, \text{cov} \ge 0.3, \text{gap} \le 60, \text{rec} \le 60$ | 79 | **79 (100.0%)** | **79 (100.0%)** | 160.8 |
| **Strict** | $N_{obs} \ge 250, \text{cov} \ge 0.5, \text{gap} \le 30, \text{rec} \le 30$ | 1 | **1 (100.0%)** | **1 (100.0%)** | 244.0 |

*Conclusion:* Every series meeting the Balanced or Inclusive eligibility tier possesses more than 50 evaluation origins in the held-out test window, providing statistical power for model evaluation under an 8-day embargo.

---

## 8. Verified Output Artifacts & Checksums

| Artifact Filename | Size (Bytes) | Line Count | SHA-256 Digest |
|---|---|---|---|
| `unmatched_excel_sample.csv` | 161,802 | 2,001 | `5d3e4c96381c299abace06f524a6178da343ab33b18307d1335075009ce5581a` |
| `unmatched_excel_summary.json` | 4,177 | N/A | `07e38e6c09f523ca28bec04a9a35141cc0d261cde073f50351a139e6294428e7` |
| `diff_77_analysis.json` | 27,628 | N/A | `ff5e30d5c83b647895aff5a16ca49ddb68cde53f3e794fb4f5e9992e2c4b5de3` |
| `quarantine_adjudication_summary.json` | 144,747 | N/A | `1f2b75813f83f982e06afe660ab772edc065bdfb5e59d7e4f4733997834803cb` |
| `target_availability_summary.json` | 10,318 | N/A | `131ed243c1591686a6346d62f099159bbb1c7967d843b6d3b521d1e9d8116099` |
| `target_availability_breakdown.csv` | 36,816 | 374 | `d3da54ec594875e743d3b5deaed9e7a6afb8176c9b0e73f9bb74f9fd14d3e589` |
| `eligibility_grids.csv` | 2,539 | 91 | `cb3b6d5a8fa831e9610ec5cd4ec3c7f4e75dfbe9d06df240c6fb938cd2c403d4` |
| `focus_crops_eligibility.csv` | 25,232 | 580 | `b4a5bb7d63a5d3d2e47687d6cf91c4106799d8f316659fa11ff148766f1d3076` |
| `chronological_split_feasibility.json` | 1,296 | N/A | `0b213e7b6d67179b90293f07c09d071987338cd823c7e804a229a3bebe6e7366` |
| `kernel_execution_manifest.json` | 1,777 | N/A | Checksum manifest generated at runtime |
