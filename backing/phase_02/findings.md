# Phase 02 — Findings: Data Handling and Methodology Remediation (Correction Pass)

**Project:** Mandi_Prediction  
**Corpus:** `ankit-choubey/Mandi_Prediction`  
**Phase:** 02 — Data Handling and Methodology Remediation (Correction Pass)  
**Status:** **PASS**  
**Date:** 2026-10-10  
**Branch:** `audit/phase-02-correction-pass`  
**Base Commit:** `4206c9c`  
**Execution Environment:** macOS Apple Silicon, Python 3.14.0, pandas 2.3.3, pytest 9.1.1  

---

## 1. Executive Summary

This correction pass reviewed and remediated the Phase 02 methodology audit to ensure that every analytical decision is mathematically defensible, reproducible, and free from lookahead leakage. All previous audit evidence has been preserved in version control.

### Summary of Corrections Applied:
1. **Grade-Stratified Duplicate Resolution:** Reconciled duplicate grouping on `(District, Market, Commodity, Variety, Grade, Arrival_Date)`. Proved that the `Grade` field is 100% complete across all 160,192 records. Differing grades on the same date represent distinct commercial quality tiers, not duplicate errors. On the same-grade key, exactly **1,331 duplicate groups (2,684 rows)** exist (1,296 conflicting modal prices, 25 conflicting spreads, 10 exact duplicates). Strategy 2 (Exclusion of ambiguous same-grade groups) retains **157,518 clean records** (excluding only 2,674 rows / 1.67% volume).
2. **Leakage-Free Volatility Targets:** Replaced expanding standard deviation of future return $R_h$ with historical daily return volatility $\sigma_{c, \le T}$ estimated strictly on or before forecast origin $T$. Verified via synthetic tests that earlier thresholds are 100% invariant to future price modifications.
3. **Embargoed Quantile Cutoffs:** Enforced a strict horizon embargo window on training origins ($T \le \text{2026-01-17}$ for $T+7$) so that training target outcomes never cross into the validation period starting on `2026-01-25`. Exactly 100,650 training returns were used with zero leakage.
4. **Market Mapping Consistency & Hiatus Audit:** Harmonized mapping status across alias groups (17 approved pairs). Discovered and documented a **204-day reporting hiatus** for `Purwa` (flagged as `PROPOSED (HIATUS)`). Maintained `Jhansi` and `Jhansi (Grain)` strictly separate due to **355 overlapping calendar dates**. Held `Baripaal APMC` as `UNRESOLVED` due to 52 concurrent overlap dates with `Varipaal APMC`.
5. **Portable Runner:** Refactored `run_phase02_analysis.py` to derive repository paths dynamically, eliminating hardcoded absolute paths.

---

## 2. Documented Correction Ledger

| Item | Original Phase 2 Implementation | Why Correction Was Required | New Calculation / Decision | Supporting Evidence |
|---|---|---|---|---|
| **Duplicate Group Key** | Grouped by 5 columns omitting `Grade`. | Collapsed FAQ, Medium, and Large trades into false price collisions. | Grouped by 6 columns including `Grade`. Exactly 1,331 duplicate groups (2,684 rows) found. | [duplicate_resolution_comparison.csv](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/backing/phase_02/outputs/duplicate_resolution_comparison.csv) |
| **Strategy 2 Exclusion** | Excluded 4,380 groups (8,818 rows dropped, 151,361 retained). | Over-penalized data volume by dropping multi-grade trades. | Excludes 1,321 ambiguous same-grade groups and 10 Cat A duplicate rows (2,674 rows dropped, 157,518 retained). | [cleaned_data_quality_summary.csv](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/backing/phase_02/outputs/cleaned_data_quality_summary.csv) |
| **Volatility Threshold** | Expanding std on future return $R_h(T)$. | Lookahead leakage: future return realized at $T+h$ is unobservable at $T$. | Historical volatility estimated strictly on past daily returns up to $T$ ($\sigma_{c, \le T}$). | [target_definition_comparison.csv](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/backing/phase_02/outputs/target_definition_comparison.csv) |
| **Quantile Threshold** | Estimated on dates $< \text{2026-01-20}$ without horizon purge. | Origins near train boundary have target outcomes falling into validation set. | Enforced embargo window: origins $T \le T_{\text{train\_split}} - h$ ($T \le \text{2026-01-17}$ for T+7). | [target_definition_comparison.csv](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/backing/phase_02/outputs/target_definition_comparison.csv) |
| **Market Statuses** | Inconsistent status between base and alias; Purwa hiatus unrecorded. | Contradictory approval labels; Purwa had an unflagged 204-day reporting gap. | Approved alias pairs have consistent status; Purwa marked `PROPOSED (HIATUS)`; Baripaal held `UNRESOLVED`. | [canonical_market_mapping.csv](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/backing/phase_02/outputs/canonical_market_mapping.csv) |
| **Script Portability** | Hardcoded `/Users/theankit/...` path in analysis runner. | Non-portable across clean checkouts or differing environments. | Dynamic root path derivation via `os.path.abspath` and `MANDI_REPO_ROOT`. | [run_phase02_analysis.py](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/backing/phase_02/tests/run_phase02_analysis.py) |

---

## 3. Duplicate Handling Comparison (With Grade Dimension)

### 3.1 Typology on Same-Grade Key
Across all 160,192 raw records:
- **Cat A (Exact Identical Prices across all 11 columns):** **10 groups** (20 rows) in Lucknow APMC.
- **Cat B (Conflicting `Modal_Price` within same grade):** **1,296 groups** (2,614 rows).
- **Cat C (Same `Modal_Price`, conflicting Min/Max within same grade):** **25 groups** (50 rows).
- **Ambiguous Groups Total (Cat B + Cat C):** **1,321 groups** (2,664 rows).

### 3.2 Candidate Strategy Performance
From [duplicate_resolution_comparison.csv](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/backing/phase_02/outputs/duplicate_resolution_comparison.csv):

| Strategy | Retained Rows | Unique Series-Dates | Excluded Rows | T+7 Matched Targets | T+7 Match Rate | R7 Std Dev | Normal Class % | Audit Verdict |
|---|---|---|---|---|---|---|---|---|
| **Strat 1: Preserve & Flag** | 160,192 | 158,839 | 0 | 128,754 (Cartesian) | N/A | 19.41% | 57.45% | **AUDIT & STORAGE BASELINE** |
| **Strat 2: Exclude Ambiguous Same-Grade** | 157,518 | 157,518 | 2,674 | 116,826 | 74.63% | 16.65% | 59.17% | **RECOMMENDED BENCHMARK** |
| **Strat 3: Median Aggregation** | 158,839 | 158,839 | 0 | 118,713 | 75.21% | 17.34% | 58.77% | **SENSITIVITY EXPERIMENT** |
| **Strat 4: Old Grade-Omitting Silent Drop** | 155,741 | 155,741 | 4,451 | 117,176 | 75.73% | 18.11% | 57.84% | **METHODOLOGICALLY FLAWED** |

---

## 4. Canonical Market Identity Audit

Audited across all 42 raw market names in [canonical_market_mapping.csv](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/backing/phase_02/outputs/canonical_market_mapping.csv):
1. **17 Approved Statewide Transitions:** Ghaziabad, Hapur, Muradnagar, Noida, Baruwasagar, Chirgaon, Gurusarai, Mauranipur, Moth, Jhansi, Choubepur, Kanpur(Grain), Uttaripura, Banthara, Lucknow, Bangarmau, Unnao. All exhibit clean November 1–5, 2025 transitions with $\le 4$ overlap dates. Status: **APPROVED** for both base and alias.
2. **Jhansi Specialized Grain Yard:** `Jhansi (Grain)` operated concurrently with `Jhansi` general yard across **355 calendar dates**. Merging them is **STRICTLY REJECTED**.
3. **Purwa Reporting Hiatus:** `Purwa` ceased on 2025-07-31; `Purwa APMC` resumed on 2026-02-21 (**204-day gap**). Status: **PROPOSED (HIATUS)**. Must not be treated as continuous without evidence.
4. **Baripaal Concurrent Variant:** `Baripaal APMC` overlapped with `Varipaal APMC` across **52–56 dates**. Status: **UNRESOLVED / PROPOSED**.

---

## 5. Calendar Lag Feature Audit

From [calendar_lag_coverage.csv](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/backing/phase_02/outputs/calendar_lag_coverage.csv):
- `shift(7)` matches an exact 7-calendar-day lag in **only 20.14% of records** (mean gap 12.01 days, max 371 days).
- Exact calendar join on `Arrival_Date - 7 days` yields **116,826 records (74.63% coverage)** on clean Strategy 2 data.
- Bounded staleness lag (`Calendar_Lag_7_Bounded2d`) bridges Sunday closures: achieves **87.8% coverage (136,701 records)** with lookback strictly bounded to 9 calendar days.

---

## 6. Target Definition and Leakage-Free Volatility Comparison

Audited across 116,826 matched T+7 pairs and 110,148 matched T+3 pairs in [target_definition_comparison.csv](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/backing/phase_02/outputs/target_definition_comparison.csv):
- **Sticky Prices:** Exactly 0.00% price change occurs in **17.79% of T+7 pairs (20,778 pairs)** and **27.59% of T+3 pairs (30,386 pairs)**.
- **Fixed $\pm 2.5\%$ Benchmark:** Normal class captures **59.17% (T+7)** and **69.72% (T+3)**. Explains why a naive majority classifier achieves 54% test accuracy without predictive skill.
- **Leak-Free Volatility Thresholds:** $\tau_{c, T} = 0.5 \cdot \sigma_{c, \le T}$ uses strictly past daily returns up to $T$. Class distribution at T+7: Favorable 22.38%, Normal 53.11%, Unfavorable 24.51%. Zero leakage.
- **Embargoed Quantile Thresholds:** Quantiles estimated on 100,650 training returns satisfying $T \le \text{2026-01-17}$ (cutoffs: Unfav $\le -1.89\%$, Fav $\ge +1.35\%$). Forward evaluation: Favorable 25.40%, Normal 49.82%, Unfavorable 24.78%. Zero leakage.

---

## 7. Automated Test Suite Execution

All 14 tests in [test_phase02_methodology.py](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/backing/phase_02/tests/test_phase02_methodology.py) passed:
```
backing/phase_02/tests/test_phase02_methodology.py::test_duplicate_group_with_different_grades_and_prices PASSED [  7%]
backing/phase_02/tests/test_phase02_methodology.py::test_same_grade_conflicting_price_examples PASSED [ 14%]
backing/phase_02/tests/test_phase02_methodology.py::test_missing_or_inconsistent_grade_values_audit PASSED [ 21%]
backing/phase_02/tests/test_phase02_methodology.py::test_strategy_exclusions_operate_on_documented_key PASSED [ 28%]
backing/phase_02/tests/test_phase02_methodology.py::test_medians_do_not_combine_different_grades PASSED [ 35%]
backing/phase_02/tests/test_phase02_methodology.py::test_consistent_mapping_status_within_alias_groups PASSED [ 42%]
backing/phase_02/tests/test_phase02_methodology.py::test_concurrent_market_names_remain_distinct PASSED [ 50%]
backing/phase_02/tests/test_phase02_methodology.py::test_purwa_hiatus_explicit_mapping_decision PASSED [ 57%]
backing/phase_02/tests/test_phase02_methodology.py::test_historical_volatility_thresholds_remain_unchanged_when_future_modified PASSED [ 64%]
backing/phase_02/tests/test_phase02_methodology.py::test_quantile_cutoffs_do_not_use_outcomes_from_held_out_periods PASSED [ 71%]
backing/phase_02/tests/test_phase02_methodology.py::test_independent_reproducibility_exact_joins PASSED [ 78%]
backing/phase_02/tests/test_phase02_methodology.py::test_zero_and_negative_prices_excluded PASSED [ 85%]
backing/phase_02/tests/test_phase02_methodology.py::test_target_classes_handle_exact_boundaries PASSED [ 92%]
backing/phase_02/tests/test_phase02_methodology.py::test_every_output_csv_has_expected_schema_and_reconciled_denominators PASSED [100%]
============================== 14 passed in 0.40s ==============================
```
Combined audit suite across Phases 1 and 2: **22 Passed, 0 Failed**.

---

## 8. Defensible Recommendations for Phase 3 Modeling

1. **Adopt Strategy 2 as Primary ML Training Benchmark:** Train models on the 157,518 clean records keyed with Grade.
2. **Apply Approved Canonical Lookups with Safeguards:** Use the 17 approved mappings; keep Jhansi (Grain) distinct; isolate Purwa hiatus.
3. **Replace Row Shifts with Exact Calendar Joins:** Use exact $T-7$ calendar joins and documented $\le 2$d bounded staleness features.
4. **Report Naive Majority Benchmark:** Benchmark all classifiers against the 54% majority class baseline; test regression on continuous returns.

---

## 9. Phase Decision

**PHASE 02 CORRECTION PASS DECISION: PASS**  
All methodology defects, duplicate keys, market mapping statuses, hiatus safeguards, and leakage-free target definitions are fully remediated, empirically verified, and backed by automated tests. Production files in `src/` and raw datasets remain untouched.
