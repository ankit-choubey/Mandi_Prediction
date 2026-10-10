# Phase 02 — Findings: Data Handling and Methodology Remediation (Second Review Pass)

**Project:** Mandi_Prediction  
**Corpus:** `ankit-choubey/Mandi_Prediction`  
**Phase:** 02 — Data Handling and Methodology Remediation (Second Review Pass)  
**Status:** **PASS**  
**Date:** 2026-10-10  
**Branch:** `main`  
**Base Commit:** `c8a94ce`  
**Execution Environment:** macOS Apple Silicon, Python 3.14.0, pandas 2.3.3, pytest 9.1.1  

---

## 1. Executive Summary

This second review pass verified and remediated the Phase 02 methodology audit to ensure that every analytical decision is mathematically defensible, reproducible, and free from lookahead leakage. All previous audit evidence has been preserved in version control.

### Summary of Corrections Applied:
1. **Historical-Volatility Leakage Elimination & Causal Burn-In Rule:**
   Inspected and corrected the expanding historical volatility calculation. Removed all backward-fill (`bfill()`) behavior that previously allowed future volatility estimates to populate earlier origins. Defined and implemented a causal rule: origins with fewer than 10 prior daily returns receive `hist_vol_T = np.nan` and remain unclassified (2,666 pairs at T+7, 2,586 pairs at T+3). Added tests proving that modifying future prices strictly after origin $T$ leaves earlier estimates 100% invariant and that no future values backfill into the burn-in period.
2. **Data-Level Quantile Embargo Verification:**
   Replaced the cutoff-string-only test with a comprehensive data-level test. Independently reconstructed the training-origin masks for T+3 and T+7. Verified that every single training target outcome used in cutoff estimation realizes on or before the chronological training boundary (`2026-01-24`). Recomputed quantile cutoffs directly from eligible returns (T+7 Quartiles: Unfav $< -1.89\%$, Fav $> 1.35\%$; T+3 Quartiles: Unfav $< -1.03\%$, Fav $> 0.78\%$) and proved that modifying post-split held-out outcomes causes zero change to training cutoffs.
3. **Bounded-Lag Figures Reconciliation:**
   Recomputed bounded-staleness coverage directly from generated data, eliminating discrepancies between prose and output CSVs: exactly **137,212 valid rows out of 157,518 (87.11% coverage)**, with **20,306 missing (12.89%)**, **116,826 exact 7-day matches (85.14% of valid)**, and a verified mean gap of **7.19 calendar days** (max age bounded to 9 calendar days).
4. **Target-Class Boundary Reconciliation (Agreed Convention):**
   Resolved the boundary convention conflict by enforcing the original agreed convention:
   - **Favorable:** return $> +2.5\%$
   - **Normal:** $-2.5\% \le \text{return} \le +2.5\%$ (closed interval)
   - **Unfavorable:** return $< -2.5\%$
   Added tests for boundary edge cases ($-2.5\%$, $+2.5\%$, $\pm 2.499999\%$, $\pm 2.500001\%$, and $0.0\%$). Recomputed all class distributions: T+7 Normal class is **59.41% (69,411 pairs)**; T+3 Normal class is **69.97% (77,070 pairs)**.
5. **Canonical Market Mapping Safeguards in Features:**
   Ensured proposed and unresolved identities are not silently treated as approved in modeling features. Verified that `Jhansi` and `Jhansi (Grain)` remain distinct (355 overlapping dates), `Purwa`'s 204-day hiatus remains isolated (`PROPOSED`), and `Baripaal APMC` is held `UNRESOLVED` (52 concurrent overlap dates with `Varipaal APMC`). In modeling lag features, only the 17 approved portal mappings are applied.
6. **Reproduction Integrity & Portable Relative Links:**
   Removed all machine-local `file:///Users/...` links from repository documentation, replacing them with relative repository links. Recorded exact Python/library versions, data checksums, and execution commands. Verified portable CLI execution via `--repo-root` and `MANDI_REPO_ROOT`.

---

## 2. Documented Correction Ledger

| Item | Original Phase 2 Implementation | Why Correction Was Required | New Calculation / Decision | Supporting Evidence |
|---|---|---|---|---|
| **Duplicate Group Key** | Grouped by 5 columns omitting `Grade`. | Collapsed FAQ, Medium, and Large trades into false price collisions. | Grouped by 6 columns including `Grade`. Exactly 1,331 duplicate groups (2,684 rows) found. | [duplicate_resolution_comparison.csv](outputs/duplicate_resolution_comparison.csv) |
| **Strategy 2 Exclusion** | Excluded 4,380 groups (8,818 rows dropped, 151,361 retained). | Over-penalized data volume by dropping multi-grade trades. | Excludes 1,321 ambiguous same-grade groups and 10 Cat A duplicate rows (2,674 rows dropped, 157,518 retained). | [cleaned_data_quality_summary.csv](outputs/cleaned_data_quality_summary.csv) |
| **Volatility Target Leakage** | Expanding std followed by `.ffill().bfill()`. | `.bfill()` allowed future volatility estimates to leak into earlier dates with <10 returns. | Strictly causal historical volatility: `hist_vol_T = np.nan` for $<10$ prior returns (unclassified burn-in). Zero backward-fill. | [target_definition_comparison.csv](outputs/target_definition_comparison.csv), `test_historical_volatility_causal_no_leakage_and_explicit_burn_in` |
| **Quantile Embargo Verification** | Asserted rule string text only. | Needed empirical data-level verification across training returns and target realization bounds. | Enforced strict embargo: training origins restricted to $T \le T_{\text{train\_split}} - h$ ($T \le \text{2026-01-17}$ for T+7). Max realization date is $\le \text{2026-01-24}$. | [target_definition_comparison.csv](outputs/target_definition_comparison.csv), `test_quantile_embargo_data_level_verification` |
| **Target Boundary Convention** | Conflicting definitions: Fav $\ge +2.5\%$ vs agreed closed Normal $[-2.5\%, +2.5\%]$. | Contradiction between specification and code. | Reconciled to agreed convention: Favorable: $R > +2.5\%$, Normal: $-2.5\% \le R \le +2.5\%$, Unfavorable: $R < -2.5\%$. Verified at boundaries $\pm 2.5\%$, just above/below, and zero. | [target_definition_comparison.csv](outputs/target_definition_comparison.csv), `test_target_class_boundaries_agreed_convention` |
| **Bounded-Lag Figures** | Discrepancies between prose and output figures (e.g. 87.8% vs 87.11%). | Hardcoded numbers in text and runner. | Recomputed dynamically directly from data: 137,212 valid / 157,518 total (87.11% coverage), 20,306 missing (12.89%), 116,826 exact 7-day matches (85.14%), mean gap 7.19 days. | [calendar_lag_coverage.csv](outputs/calendar_lag_coverage.csv), `test_bounded_lag_figures_reconciled` |
| **Market Safeguards in Modeling** | Inconsistent status between base and alias; Purwa hiatus unrecorded. | Risk of silent merging of unapproved markets into modeling features. | 17 approved pairs have consistent status; Purwa marked `PROPOSED (HIATUS)`; Baripaal held `UNRESOLVED`. Modeling features apply strictly approved mappings. | [canonical_market_mapping.csv](outputs/canonical_market_mapping.csv), `test_canonical_mapping_safeguards_in_modeling_features` |
| **Script Portability & Links** | Hardcoded machine-local paths (`/Users/theankit/...`). | Non-portable across clean checkouts or differing environments. | Dynamic root path derivation via `os.path.abspath` and `MANDI_REPO_ROOT`. All documentation links converted to relative repository paths. | [run_phase02_analysis.py](tests/run_phase02_analysis.py) |

---

## 3. Duplicate Handling Comparison (With Grade Dimension)

### 3.1 Typology on Same-Grade Key
Across all 160,192 raw records:
- **Cat A (Exact Identical Prices across all 11 columns):** **10 groups** (20 rows) in Lucknow APMC.
- **Cat B (Conflicting `Modal_Price` within same grade):** **1,296 groups** (2,614 rows).
- **Cat C (Same `Modal_Price`, conflicting Min/Max within same grade):** **25 groups** (50 rows).
- **Ambiguous Groups Total (Cat B + Cat C):** **1,321 groups** (2,664 rows).

### 3.2 Candidate Strategy Performance
From [duplicate_resolution_comparison.csv](outputs/duplicate_resolution_comparison.csv):

| Strategy | Retained Rows | Unique Series-Dates | Excluded Rows | T+7 Matched Targets | T+7 Match Rate | Favorable % | Normal % | Unfavorable % | Audit Verdict |
|---|---|---|---|---|---|---|---|---|---|
| **Strat 1: Preserve & Flag** | 160,192 | 158,839 | 0 | 128,754 (Cartesian) | N/A | 19.34% | 58.74% | 21.92% | **AUDIT & STORAGE BASELINE** |
| **Strat 2: Exclude Ambiguous Same-Grade** | 157,518 | 157,518 | 2,674 | 116,826 | 74.63% | 18.91% | 59.41% | 21.68% | **RECOMMENDED BENCHMARK** |
| **Strat 3: Median Aggregation** | 158,839 | 158,839 | 0 | 118,713 | 75.21% | 18.93% | 59.38% | 21.69% | **SENSITIVITY EXPERIMENT** |
| **Strat 4: Old Grade-Omitting Silent Drop** | 154,642 | 154,642 | 5,550 | 114,846 | 74.27% | 18.97% | 59.80% | 21.23% | **METHODOLOGICALLY FLAWED** |

---

## 4. Canonical Market Identity Audit

Audited across all 42 raw market names in [canonical_market_mapping.csv](outputs/canonical_market_mapping.csv):
1. **17 Approved Statewide Transitions:** Ghaziabad, Hapur, Muradnagar, Noida, Baruwasagar, Chirgaon, Gurusarai, Mauranipur, Moth, Jhansi, Choubepur, Kanpur(Grain), Uttaripura, Banthara, Lucknow, Bangarmau, Unnao. All exhibit clean November 1–5, 2025 transitions with $\le 4$ overlap dates. Status: **APPROVED** for both base and alias.
2. **Jhansi Specialized Grain Yard Safeguard:** `Jhansi (Grain)` operated concurrently with `Jhansi` general yard across **355 calendar dates**. Merging them is **STRICTLY REJECTED**.
3. **Purwa Reporting Hiatus Safeguard:** `Purwa` ceased on 2025-07-31; `Purwa APMC` resumed on 2026-02-21 (**204-day gap**). Status: **PROPOSED (HIATUS)**. Kept unmerged in modeling features.
4. **Baripaal Concurrent Variant Safeguard:** `Baripaal APMC` overlapped with `Varipaal APMC` across **52 concurrent dates**. Status: **UNRESOLVED / PROPOSED**. Kept unmerged in modeling features.

---

## 5. Calendar Lag Feature Audit

From [calendar_lag_coverage.csv](outputs/calendar_lag_coverage.csv):
- `shift(7)` matches an exact 7-calendar-day lag in **only 18.42% of records** (mean gap 12.11 days, max 398 days).
- Exact calendar join on `Arrival_Date - 7 days` yields **116,826 records (74.17% coverage)** on clean Strategy 2 data.
- Bounded staleness lag (`Calendar_Lag_7_Bounded2d`) bridges Sunday closures: achieves **87.11% coverage (137,212 valid records out of 157,518; 20,306 missing)** with **85.14% exact 7-day match** and mean gap **7.19 calendar days** (lookback strictly bounded to 9 calendar days).
- Canonical market exact calendar lag T-7 (using strictly approved mappings) yields **117,682 valid records (74.71% coverage)**, safely adding valid continuous pairs across the Nov 2025 APMC boundary.

---

## 6. Target Definition and Leakage-Free Volatility Comparison

Audited across 116,826 matched T+7 pairs and 110,148 matched T+3 pairs in [target_definition_comparison.csv](outputs/target_definition_comparison.csv):
- **Sticky Prices:** Exactly 0.00% price change occurs in **17.79% of T+7 pairs (20,778 pairs)** and **27.59% of T+3 pairs (30,386 pairs)**.
- **Fixed $\pm 2.5\%$ Benchmark (Agreed Convention):**
  - **T+7:** Favorable ($R > +2.5\%$): 22,089 (**18.91%**), Normal ($-2.5\% \le R \le +2.5\%$): 69,411 (**59.41%**), Unfavorable ($R < -2.5\%$): 25,326 (**21.68%**).
  - **T+3:** Favorable ($R > +2.5\%$): 15,502 (**14.07%**), Normal ($-2.5\% \le R \le +2.5\%$): 77,070 (**69.97%**), Unfavorable ($R < -2.5\%$): 17,576 (**15.96%**).
- **Leak-Free Volatility Thresholds:** $\tau_{c, T} = 0.5 \cdot \sigma_{c, \le T}$ uses strictly past daily returns up to $T$. Origins with $<10$ returns are left unclassified (2,666 pairs at T+7, 2,586 pairs at T+3). Classified T+7 pairs ($n=114,160$): Favorable 25,475 (22.32%), Normal 60,910 (53.35%), Unfavorable 27,775 (24.33%). Zero leakage.
- **Embargoed Quantile Thresholds:** Quantiles estimated on training returns satisfying $T \le \text{2026-01-17}$ (cutoffs: Unfav $< -1.89\%$, Normal $[-1.89\%, +1.35\%]$, Fav $> +1.35\%$). Forward evaluation: Favorable 29,573 (25.31%), Normal 58,377 (49.97%), Unfavorable 28,876 (24.72%). Zero leakage.

---

## 7. Automated Test Suite Execution

All 17 tests in [test_phase02_methodology.py](tests/test_phase02_methodology.py) passed:
```
backing/phase_02/tests/test_phase02_methodology.py::test_duplicate_group_with_different_grades_and_prices PASSED [  5%]
backing/phase_02/tests/test_phase02_methodology.py::test_same_grade_conflicting_price_examples PASSED [ 11%]
backing/phase_02/tests/test_phase02_methodology.py::test_missing_or_inconsistent_grade_values_audit PASSED [ 17%]
backing/phase_02/tests/test_phase02_methodology.py::test_strategy_exclusions_operate_on_documented_key PASSED [ 23%]
backing/phase_02/tests/test_phase02_methodology.py::test_medians_do_not_combine_different_grades PASSED [ 29%]
backing/phase_02/tests/test_phase02_methodology.py::test_consistent_mapping_status_within_alias_groups PASSED [ 35%]
backing/phase_02/tests/test_phase02_methodology.py::test_concurrent_market_names_remain_distinct PASSED [ 41%]
backing/phase_02/tests/test_phase02_methodology.py::test_purwa_hiatus_explicit_mapping_decision PASSED [ 47%]
backing/phase_02/tests/test_phase02_methodology.py::test_canonical_mapping_safeguards_in_modeling_features PASSED [ 52%]
backing/phase_02/tests/test_phase02_methodology.py::test_historical_volatility_causal_no_leakage_and_explicit_burn_in PASSED [ 58%]
backing/phase_02/tests/test_phase02_methodology.py::test_quantile_embargo_data_level_verification PASSED [ 64%]
backing/phase_02/tests/test_phase02_methodology.py::test_bounded_lag_figures_reconciled PASSED [ 70%]
backing/phase_02/tests/test_phase02_methodology.py::test_target_class_boundaries_agreed_convention PASSED [ 76%]
backing/phase_02/tests/test_phase02_methodology.py::test_independent_reproducibility_exact_joins PASSED [ 82%]
backing/phase_02/tests/test_phase02_methodology.py::test_zero_and_negative_prices_excluded PASSED [ 88%]
backing/phase_02/tests/test_phase02_methodology.py::test_no_cartesian_row_explosion_on_joins PASSED [ 94%]
backing/phase_02/tests/test_phase02_methodology.py::test_every_output_csv_has_expected_schema_and_reconciled_denominators PASSED [100%]
============================== 17 passed in 0.61s ==============================
```
Combined audit suite across Phases 1 and 2: **25 Passed, 0 Failed in 2.56s**.

---

## 8. Defensible Recommendations for Phase 3 Modeling

1. **Adopt Strategy 2 as Primary ML Training Benchmark:** Train models on the 157,518 clean records keyed with Grade.
2. **Apply Approved Canonical Lookups with Safeguards:** Use the 17 approved mappings; keep Jhansi (Grain) distinct; isolate Purwa hiatus.
3. **Replace Row Shifts with Exact Calendar Joins:** Use exact $T-7$ calendar joins and documented $\le 2$d bounded staleness features.
4. **Report Naive Majority Benchmark:** Benchmark all classifiers against the 59.4% majority class baseline; test regression on continuous returns.
