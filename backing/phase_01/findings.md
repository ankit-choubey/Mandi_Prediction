# Phase 1 Audit Findings: Data Integrity & Exact-Calendar Continuity

**Audit Phase:** Phase 1 — Data Integrity & Temporal Continuity  
**Date:** October 10, 2026  
**Auditor:** Antigravity AI  
**Status:** **COMPLETED**  
**Audit Decision:** **PASS** (Data verified; key structural bugs and continuity boundaries documented)  
**Git Branch:** `audit/phase-01-data-integrity`  

---

## Executive Summary

Phase 1 conducted an exhaustive empirical audit of the raw APMC dataset across 160,192 records. The investigation verified that the underlying price records from AGMARKNET are authentic, continuous across 731 calendar days, and exhibit 99.996% price order compliance. 

However, Phase 1 uncovered **four critical methodological defects** in the original repository pipeline:
1. **Silent Dropping of Conflicting Prices:** The original code silently dropped 4,380 duplicate records that contained conflicting modal prices on the same calendar date.
2. **Artificial Time-Series Severance:** In November 2025, upstream data appended ` APMC` to market names. Because `series_id` contains `Market`, continuous 2-year series were cut in half, reducing exact $T+7$ matching across the transition week and creating the false impression of 42 mandis instead of 21 physical mandis.
3. **Observation Shift vs Calendar Horizon:** In `feature_engineering.py`, `shift(7)` looks back 8 to 16 calendar days in ~80% of records, creating severe temporal asymmetry against the strictly defined 7-calendar-day target.
4. **Class Imbalance from Sticky Prices:** Over 17% of observations at $T+7$ (and 26.6% at $T+3$) experience **exactly 0.00% price change**. The static $\pm 2.5\%$ threshold places ~58% of the data into the "Normal" class, explaining why naive guessing achieves 54% accuracy on the test set.

---

## 1. Input Verification & File Integrity

All 5 CSV files were cryptographically verified using SHA-256 directly from disk. Raw files were preserved unchanged.

| Filename | File Size | SHA-256 Hash | Rows | Columns | Min Date | Max Date |
|---|---|---|---|---|---|---|
| `Gaziabaad.csv` | 3.49 MB | `71601f993e07efa146f126747245a7fffb608a307abdea579475ba19bfeb0251` | 41,495 | 11 | 2024-09-01 | 2026-09-01 |
| `Jhansi.csv` | 1.86 MB | `7d0808d8d32555212af546004195c0ccf58e368106daad67169a231e80988a5c` | 23,625 | 11 | 2024-09-01 | 2026-09-01 |
| `Kanpur.csv` | 3.53 MB | `0eb17704ebba1f66b8c9ef660f48dabc3665ea4691ed3b8aa20a49df8528d04a` | 42,644 | 11 | 2024-09-01 | 2026-09-01 |
| `Lukhnow.csv` | 1.76 MB | `6ca52743cc2f9059bf1e3b919b25317aa367f580bbafa6f62adb9db1d759bb13` | 21,063 | 11 | 2024-09-01 | 2026-09-01 |
| `Unnao.csv` | 2.45 MB | `d4ee358b96cad3a888e4a92acd993327e56c4dc6af6eb60814193f98f591cebc` | 31,365 | 11 | 2024-09-01 | 2026-09-01 |
| **TOTAL** | **13.09 MB** | — | **160,192** | **11** | **2024-09-01** | **2026-09-01** |

*Output Reference:* [`backing/phase_01/outputs/input_inventory.csv`](./outputs/input_inventory.csv)

---

## 2. Duplicate Records & Price Ambiguity Audit

The canonical series key is defined as `District__Market__Commodity__Variety`. Grouping by `series_id + Arrival_Date` revealed:
- **Total Duplicate Groups:** **4,393 groups** (comprising 8,844 rows).
- **Identical Price Duplicates:** **13 groups** (0.3%) had identical prices across all records.
- **Conflicting Modal Prices:** **4,363 groups** (99.3%) had conflicting modal prices for the same commodity on the same date.
- **Conflicting Min/Max Prices:** **17 groups** (0.4%) had identical modal prices but differing intraday spreads.
- **Total Ambiguous Date Groups:** **4,380 groups (99.7% of all duplicate groups)**.

*Root Cause:* In high-volume mandis (e.g. Ghaziabad and Kanpur), multiple auction lots or arrivals batches for the same produce variety are reported separately on the same day.  
*Critical Defect Found:* The repository's `data_loader.py` executed `drop_duplicates(keep='first')`, silently dropping 4,380 records based on arbitrary CSV row order.  
*Output References:* [`backing/phase_01/outputs/duplicate_groups.csv`](./outputs/duplicate_groups.csv), [`backing/phase_01/outputs/data_quality_flags.csv`](./outputs/data_quality_flags.csv).

---

## 3. Price Quality & Sanity Audit

- **Price Order Rule ($Min \le Modal \le Max$):**
  - Compliant rows: 160,186 (**99.9963%**).
  - Violations: **6 rows (0.0037%)**, exactly all in Kanpur (4 rows), Jhansi (1 row), and Unnao (1 row). In every violation, `Max_Price = 0.0` while `Modal_Price > 0.0`.
- **Zero / Negative Prices:** Exactly the same 6 rows where `Max_Price = 0.0`. Zero negative prices detected.
- **Zero Intraday Spread ($Max == Min$):**
  - **18,000 rows (11.24% of all records)** have zero intraday spread ($Min == Modal == Max$).
  - Highest in Lucknow (15.74%) and Jhansi (15.60%); lowest in Unnao (7.16%). This indicates mandis that report a single flat rate rather than an auction range.
- **Extreme Outliers:** Wood exhibits extreme price dispersion (Median: ₹520, Max: ₹18,000, 34.6x ratio) due to reporting truckload lots vs quintals. Specialty items (Ghee up to ₹1,23,814/quintal, Poppy seeds up to ₹2,14,286/quintal) reflect genuine high-value goods.

*Output Reference:* [`backing/phase_01/outputs/price_quality_summary.csv`](./outputs/price_quality_summary.csv).

---

## 4. Market Mapping & Canonicalization Review

The raw dataset contains 42 nominal market strings across 5 districts. An exhaustive cross-examination of date ranges and trading volume revealed:
- **The November 2025 APMC Naming Switch:**
  19 market pairs represent clean pre- and post-November 2025 transitions (`<Market>` $\to$ `<Market> APMC`). The base market stopped reporting around November 4, 2025, and the APMC market started around November 1, 2025.
- **Overlap Analysis:** Across all 19 transition pairs, the overlap is only 2 to 4 transition days.
- **Critical Caveat — Parallel Physical Yards:**
  In Jhansi District, `Jhansi` (general market) and `Jhansi (Grain)` (grain-specific market) operated concurrently across 306 overlapping dates. They must **not** be merged into a single entity.
- **Phonetic Spelling Variants:**
  In Kanpur, `Varipaal APMC` (stopped late April 2026) and `Baripaal APMC` (started March 2026) overlap for 56 days and represent the same physical market yard.
- **Proposal Status:** All 42 market strings are cataloged in [`backing/phase_01/outputs/market_mapping_review.csv`](./outputs/market_mapping_review.csv). Unification reduces the nominal 42 mandis to the true **21 physical mandis**. Per audit rules, these mappings are preserved as proposals and not merged automatically.

---

## 5. Exact Calendar-Day Target Matching ($T+3$ and $T+7$)

Target matching was performed strictly via exact calendar date joins ($T + \text{horizon}$ calendar days), never substituting the next available observation.

### Explicit Denominators & Coverage Breakdown

| Metric / Horizon | $T+3$ Horizon | $T+7$ Horizon | Explanation |
|---|---|---|---|
| **Total Clean Origin Records** | 155,741 | 155,741 | Clean unique series-date observations |
| **Boundary-Truncated Origins** | 465 (0.30%) | 1,005 (0.65%) | Origins where $T + \text{horizon} > \text{2026-09-01}$ (unobservable by horizon definition) |
| **Eligible Origin Records** | **155,276 (99.70%)** | **154,736 (99.35%)** | Origins within observable calendar bounds |
| **Successfully Matched Targets** | **110,349** | **117,176** | Observations with exact same series at $T + \text{horizon}$ |
| **Interior Missing Gaps** | 44,927 (28.93%) | 37,560 (24.27%) | Eligible origins where mandi had no auction on target date |
| **Match Rate (Over All Origins)** | **70.85%** | **75.24%** | Match rate over total dataset |
| **Match Rate (Over Eligible Origins)**| **71.07%** | **75.73%** | True calendar availability rate |

*Why $T+7$ Match Rate (75.24%) Exceeds $T+3$ (70.85%):*  
Mandis operate on strict weekly trading cycles. Origins on Thursday asking for $T+3$ land on Sunday (when mandis have 45% fewer auctions), whereas $T+7$ from Monday lands on Monday.

### Coverage by District ($T+7$ Eligible Match Rate):
1. **Unnao:** **83.49%** (25,514 matches / 30,561 eligible)
2. **Lucknow:** **79.50%** (16,226 matches / 20,410 eligible)
3. **Kanpur:** **77.37%** (32,603 matches / 42,137 eligible)
4. **Ghaziabad:** **73.12%** (28,482 matches / 38,955 eligible)
5. **Jhansi:** **63.30%** (14,351 matches / 22,673 eligible)

### Coverage by Commodity ($T+7$ Eligible Match Rate):
- **High-Volume Staples (>80%):** Apple (81.56%), Potato (81.55%), Bottle gourd (80.91%), Onion (80.78%), Brinjal (79.76%), Tomato (79.62%).
- **Grain Staples (~71–74%):** Mustard (74.57%), Wheat (73.67%), Rice (71.11%).
- **Sparse Seasonal Crops (<25%):** Sesamum/Til (15.22%), Lobia (15.27%), Methi Seeds (21.66%), Chana Dal (28.24%). Overall, **31.7% of all series have <50% T+7 continuity**.

*Output References:* [`backing/phase_01/outputs/exact_target_coverage.csv`](./outputs/exact_target_coverage.csv), [`backing/phase_01/outputs/target_match_examples.csv`](./outputs/target_match_examples.csv).

---

## 6. Target Class Distributions & Boundary Edge Cases

Target price return: $R_h = \frac{P_{T+h} - P_T}{P_T} \times 100$.

### Empirical Distribution Comparison

| Statistic | $T+3$ Horizon ($n = 110,349$) | $T+7$ Horizon ($n = 117,176$) |
|---|---|---|
| **Mean Return** | $+0.7025\%$ | $+0.6346\%$ |
| **Median Return** | **0.0000%** | **0.0000%** |
| **Standard Deviation** | $22.4592\%$ | $18.1136\%$ |
| **25th Percentile** | $-1.0989\%$ | $-1.9608\%$ |
| **75th Percentile** | $+0.8523\%$ | $+1.5002\%$ |
| **Interquartile Range (IQR)** | **1.9512%** | **3.4609%** |
| **Exact 0.00% Change (Sticky Prices)**| **29,408 records (26.65%)** | **20,085 records (17.14%)** |
| **Favorable ($\ge +2.5\%$)** | 16,558 (15.01%) | 23,118 (19.73%) |
| **Normal ($-2.5\% < R < +2.5\%$)** | **75,261 (68.20%)** | **67,775 (57.84%)** |
| **Unfavorable ($\le -2.5\%$)** | 18,530 (16.79%) | 26,283 (22.43%) |
| **Exact $+2.5000\%$ Edge Cases** | 147 records | 131 records |
| **Exact $-2.5000\%$ Edge Cases** | 110 records | 141 records |

*Boundary Condition Analysis:*  
Because agricultural wholesale prices are sticky, 50% of all 7-day returns fall within $[-1.96\%, +1.50\%]$ (width: 3.46%), and 50% of 3-day returns fall within $[-1.10\%, +0.85\%]$ (width: 1.95%). The static $\pm 2.5\%$ threshold naturally captures 58% to 68% of the data into the "Normal" class, explaining why naive majority guessing achieves 54% accuracy on the chronological test set.

*Output Reference:* [`backing/phase_01/outputs/class_distribution.csv`](./outputs/class_distribution.csv).

---

## 7. Automated Test Suite Execution Results

All 8 formal verification tests in [`backing/phase_01/tests/test_phase01_data_integrity.py`](./tests/test_phase01_data_integrity.py) were executed:

```text
============================= test session starts ==============================
platform darwin -- Python 3.14.0, pytest-9.1.1, pluggy-1.6.0
collected 8 items

TestPhase01DataIntegrity::test_total_raw_record_count PASSED           [ 12%]
TestPhase01DataIntegrity::test_exact_calendar_t7_matching PASSED       [ 25%]
TestPhase01DataIntegrity::test_exact_calendar_t3_matching PASSED       [ 37%]
TestPhase01DataIntegrity::test_missing_target_separation_t7 PASSED     [ 50%]
TestPhase01DataIntegrity::test_duplicate_date_ambiguity PASSED         [ 62%]
TestPhase01DataIntegrity::test_price_order_violations_detection PASSED [ 75%]
TestPhase01DataIntegrity::test_target_class_boundaries_and_edge_cases PASSED [ 87%]
TestPhase01DataIntegrity::test_output_csv_artifacts_exist PASSED       [100%]

============================== 8 passed in 2.08s ===============================
```

*Execution Log Reference:* [`backing/phase_01/tests/test_results.txt`](./tests/test_results.txt).

---

## 8. Summary of Phase 1 Deliverables

1. All 9 machine-readable CSV outputs created under [`backing/phase_01/outputs/`](./outputs/).
2. All supporting evidence documents created under [`backing/phase_01/evidence/`](./evidence/).
3. Automated test suite and verified execution log saved under [`backing/phase_01/tests/`](./tests/).
4. Master project audit report updated at [`backing/PROJECT_AUDIT.md`](../PROJECT_AUDIT.md).

**Decision:** **PASS** (Phase 1 objectives fully met with empirical backing; ready for Phase 2 feature and methodology remediation).
