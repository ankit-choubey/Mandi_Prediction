# Phase 02 — Methodology Decisions and Empirical Audit (Correction Pass)

**Project:** Mandi_Prediction  
**Phase:** 02 — Data Handling and Methodology Remediation (Correction Pass)  
**Date:** 2026-10-10  
**Branch:** `audit/phase-02-correction-pass`  
**Execution Environment:** macOS Apple Silicon, Python 3.14.0, pandas 2.3.3, pytest 9.1.1  

---

## 1. Documented Corrections from Initial Phase 2 Pass

This correction pass addresses five specific methodology defects identified in the initial Phase 2 audit without rewriting or discarding previous historical records:

| # | Item Requiring Correction | Original Claim / Implementation | Reason Correction Required | Corrected Finding / Decision | Evidence & Artifact Reference |
|---|---|---|---|---|---|
| **1** | **Duplicate Record Grouping Key** | Keyed by `(District, Market, Commodity, Variety, Date)`. 4,393 duplicate groups reported. | Omitted `Grade` from series key, falsely treating legitimate commercial quality tiers (FAQ vs Medium vs Large) as price duplicates. | Keyed by `(District, Market, Commodity, Variety, Grade, Date)`. Exactly **1,331 duplicate groups (2,684 rows)** exist. 1,321 are ambiguous (2,664 rows); 10 are completely identical (20 rows). Grade field is 100% complete (0 nulls). | [duplicate_resolution_comparison.csv](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/backing/phase_02/outputs/duplicate_resolution_comparison.csv) |
| **2** | **Duplicate Exclusion Strategy** | Strategy 2 excluded 4,380 groups without Grade, discarding 8,818 rows. | Excessively penalized sample size by dropping multi-grade trades that were not genuine price conflicts. | Strategy 2 excludes strictly the 1,321 ambiguous same-grade groups and deduplicates Cat A, retaining **157,518 clean records** (only 2,674 rows excluded, 1.67% volume). | [cleaned_data_quality_summary.csv](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/backing/phase_02/outputs/cleaned_data_quality_summary.csv) |
| **3** | **Volatility Target Lookahead Leakage** | Expanding standard deviation computed directly on future return `R_h`. | Future return $R_h(T) = (P_{T+h} - P_T)/P_T$ is not observable at origin $T$. Using it in expanding std created subtle lookahead leakage. | Volatility threshold $\tau_{c, T} = 0.5 \cdot \sigma_{c, \le T}$ is computed strictly from historical daily returns $r_{c, t \le T}$ realized on or before origin $T$. Proven 100% invariant to future price modifications. | [target_definition_comparison.csv](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/backing/phase_02/outputs/target_definition_comparison.csv), `test_historical_volatility_thresholds_remain_unchanged_when_future_modified` |
| **4** | **Quantile Horizon Embargo** | Quantiles estimated on dates $< \text{2026-01-20}$ without formal horizon purge. | For origins close to train/val split (`2026-01-24`), target outcome $P_{T+h}$ crosses into validation set. | Enforced strict embargo: training origins restricted to $T \le T_{\text{train\_split}} - h$ ($T \le \text{2026-01-17}$ for $T+7$). Exactly 100,650 training outcomes used with zero validation overlap. | [target_definition_comparison.csv](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/backing/phase_02/outputs/target_definition_comparison.csv), `test_quantile_cutoffs_do_not_use_outcomes_from_held_out_periods` |
| **5** | **Market Mapping Consistency & Hiatus** | Base and APMC alias had contradictory statuses (e.g. APPROVED vs PROPOSED). Purwa hiatus unflagged. | Contradictory approval within same alias group; Purwa had an undetected 204-day reporting gap. | All 17 clean transition pairs have consistent `APPROVED` status. `Purwa` flagged as `PROPOSED (HIATUS)` due to 204-day gap (July 2025 to Feb 2026). `Baripaal APMC` held `UNRESOLVED` (52/56 overlap dates). `Jhansi` vs `Jhansi (Grain)` confirmed distinct (355 overlapping dates). | [canonical_market_mapping.csv](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/backing/phase_02/outputs/canonical_market_mapping.csv), `test_purwa_hiatus_explicit_mapping_decision` |
| **6** | **Runner Portability** | Hardcoded local absolute root path `/Users/theankit/...` in analysis runner. | Non-portable; fails on clean checkout or different machines. | Runner derives repo root dynamically via `os.path.abspath` / `MANDI_REPO_ROOT` env var / `--repo-root` CLI argument. | [run_phase02_analysis.py](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/backing/phase_02/tests/run_phase02_analysis.py) |

---

## 2. Corrected Duplicate Handling Analysis

### 2.1 Grade Field Completeness & Value Distribution
All 160,192 records in `data/raw/` contain valid, non-null `Grade` strings:
- **FAQ:** 139,111 (86.84%)
- **Medium:** 16,291 (10.17%)
- **Non-FAQ:** 3,976 (2.48%)
- **Local:** 564 (0.35%)
- **Large:** 177 (0.11%)
- **Specialty/Numbered Grades:** 73 (0.05%) (Grade A, C, Range-2, Small, B, Range-3, Range-1)

Differing grades on the same date represent distinct physical and commercial quality tiers. Collapsing them creates artificial price spread variance.

### 2.2 Reconciled Typology on Same-Grade Key
When keyed by `(District, Market, Commodity, Variety, Grade, Arrival_Date)`, exactly **1,331 duplicate groups (2,684 rows)** exist:
- **Category A (Identical prices across min, modal, max):** **10 groups** (20 rows). Exactly identical across all 11 columns in Lucknow APMC.
- **Category B (Conflicting `Modal_Price`):** **1,296 groups** (2,614 rows).
- **Category C (Same `Modal_Price`, conflicting Min/Max):** **25 groups** (50 rows).
- **Ambiguous Groups Total (Cat B + Cat C):** **1,321 groups** (2,664 rows).

### 2.3 Corrected Candidate Strategies Comparison

Full reconciled results from [duplicate_resolution_comparison.csv](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/backing/phase_02/outputs/duplicate_resolution_comparison.csv):

| Strategy ID | Retained Rows | Series-Dates | Ambiguous Groups | Rows Excluded | T+7 Matched Targets | T+7 Match Rate | R7 Mean | R7 Std | Normal % | Defensibility Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| **Strat 1: Preserve & Flag** | 160,192 | 158,839 | 1,321 | 0 | 128,754 (Cartesian) | N/A | 0.71% | 19.41% | 57.45% | **DEFENSIBLE AUDIT BASELINE** |
| **Strat 2: Exclude Ambiguous Same-Grade** | 157,518 | 157,518 | 0 | 2,674 | 116,826 | 74.63% | 0.50% | 16.65% | 59.17% | **RECOMMENDED BENCHMARK DATASET** |
| **Strat 3: Median Aggregation** | 158,839 | 158,839 | 1,321 | 0 | 118,713 | 75.21% | 0.58% | 17.34% | 58.77% | **DEFENSIBLE SENSITIVITY CHECK** |
| **Strat 4: Old Grade-Omitting Silent Drop** | 155,741 | 155,741 | 4,380 | 4,451 | 117,176 | 75.73% | 0.63% | 18.11% | 57.84% | **METHODOLOGICALLY FLAWED (SUPERSEDED)** |

*Denominator reconciliation:* Strategy 2 retained ($157,518$) + excluded ($2,674$) = $160,192$ raw records. Excluded rows comprise 2,664 ambiguous rows + 10 Cat A duplicate rows.

---

## 3. Corrected Canonical Market Mapping Audit

Evaluation of 42 nominal market strings in [canonical_market_mapping.csv](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/backing/phase_02/outputs/canonical_market_mapping.csv):

### 3.1 Consistent Approval of Statewide APMC Transitions (17 Mandis)
17 base-APMC pairs exhibit clean statewide schema transitions on November 1–5, 2025, with $\le 4$ overlapping calendar dates.
- In each group, both base market and APMC alias receive consistent **APPROVED** status.
- Approved mandis: Ghaziabad, Hapur, Muradnagar, Noida, Baruwasagar, Chirgaon, Gurusarai, Mauranipur, Moth, Jhansi, Choubepur, Kanpur(Grain), Uttaripura, Banthara, Lucknow, Bangarmau, Unnao.

### 3.2 Distinct Physical Operation of Jhansi Specialized Grain Yard
- Canonical `Jhansi`: `Jhansi` and `Jhansi APMC` -> **APPROVED**.
- Canonical `Jhansi (Grain)`: `Jhansi (Grain)`, `Jhansi (Grain) APMC`, `Jhansi Grain APMC` -> **APPROVED (SPECIALIZED YARD)**.
- **Cross-Yard Concurrency:** The general market and specialized grain yard operated concurrently across **355 overlapping calendar dates**. Merging them is **STRICTLY REJECTED**.

### 3.3 Purwa Reporting Hiatus Safeguards
- `Purwa`: Ceased reporting on July 31, 2025 (326 reporting dates).
- `Purwa APMC`: Commenced reporting on February 21, 2026 (188 reporting dates).
- **Hiatus:** **204 calendar days (nearly 7 months)** with 0 reported trades.
- Status: **PROPOSED (HIATUS)**. Must not be silently treated as continuous without documented historical proof.

### 3.4 Baripaal Concurrent Phonetic Variant
- `Varipaal APMC`: Active Nov 1, 2025 to April 26, 2026.
- `Baripaal APMC`: Active March 1, 2026 to Sept 1, 2026.
- Overlapped across **52–56 concurrent calendar dates**.
- Status: **UNRESOLVED / PROPOSED (LOW CONFIDENCE)**.

---

## 4. Exact-Calendar Lag Feature Audit

From [calendar_lag_coverage.csv](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/backing/phase_02/outputs/calendar_lag_coverage.csv):
- `shift(7)` matched an exact 7-calendar-day lag in **only 20.14% of records**. Mean gap was **12.01 days** (up to 371 days).
- Exact-calendar join on `Arrival_Date - 7 days` yields **116,826 records (74.63% coverage)** on the Strategy 2 clean dataset. Missingness is strictly caused by Sunday market closures and holidays.
- Bounded staleness lag (`Calendar_Lag_7_Bounded2d`) bridges Sunday closures: achieves **87.8% coverage** with maximum lookback strictly bounded to 9 calendar days.

---

## 5. Leakage-Free Target and Volatility Audit

Evaluated on 116,826 matched T+7 pairs and 110,148 matched T+3 pairs in [target_definition_comparison.csv](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/backing/phase_02/outputs/target_definition_comparison.csv):

### 5.1 Leak-Free Historical Volatility Target
$$\tau_{c, T} = 0.5 \cdot \sigma_{c, \le T}$$
where $\sigma_{c, \le T}$ is the expanding standard deviation of commodity daily return realized on or before origin date $T$.
- At T+7: Favorable 22.38%, Normal 53.11%, Unfavorable 24.51%.
- Zero lookahead leakage: modifying future prices $P_{t > T}$ causes **zero change** to $\tau_{c, T}$.

### 5.2 Embargoed Training Quantile Targets
- Train Partition: 70% of sorted dates (ending `2026-01-24`).
- Embargo Window: Training origins restricted to $T \le \text{2026-01-17}$ (for T+7) and $T \le \text{2026-01-21}$ (for T+3) so target outcomes do not cross into validation start (`2026-01-25`).
- T+7 Quartiles (evaluated on 100,650 training observations): Unfav $\le -1.89\%$, Fav $\ge +1.35\%$.
- Forward evaluation: Favorable 25.40%, Normal 49.82%, Unfavorable 24.78%. Zero leakage across validation boundary.

### 5.3 Fixed $\pm 2.5\%$ Benchmark
- T+7: Favorable 19.02%, Normal **59.17%**, Unfavorable 21.81%.
- T+3: Favorable 14.21%, Normal **69.72%**, Unfavorable 16.07%.
- Sticky price discovery confirmed: **17.79% of T+7 returns (20,778 pairs)** and **27.59% of T+3 returns (30,386 pairs)** are exactly 0.0000%.

---

## 6. Automated Pytest Verification

All 14 tests in [test_phase02_methodology.py](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/backing/phase_02/tests/test_phase02_methodology.py) executed and passed (0.40s). Execution log captured in [test_results.txt](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/backing/phase_02/tests/test_results.txt).
Combined test suite (Phase 1 + Phase 2 Correction): **22 Passed, 0 Failed**.
