# Phase 02 — Findings: Data Handling and Methodology Remediation

**Project:** Mandi_Prediction  
**Corpus:** `ankit-choubey/Mandi_Prediction`  
**Phase:** 02 — Data Handling and Methodology Remediation  
**Status:** **PASS**  
**Date:** 2026-10-10  
**Branch:** `audit/phase-02-methodology`  
**Base Commit:** `8a691dd`  
**Execution Environment:** macOS Apple Silicon, Python 3.14.0, pandas 2.3.3, pytest 9.1.1  

---

## 1. Executive Summary

Phase 02 performed an exhaustive empirical and statistical audit of the data handling and methodology choices in `Mandi_Prediction`. This phase did not train forecasting models, alter raw datasets, or modify production pipeline files in `src/`. Instead, it executed a reproducible audit across all 160,192 raw records and 731 calendar days to determine which methodological choices are mathematically defensible and how sensitive the dataset is to those choices.

### Key Discoveries & Audit Conclusions:
1. **The Duplicate "Bug" is Primarily a Multi-Grade Feature:**
   Out of 4,393 duplicate series-date groups (keyed by `District, Market, Commodity, Variety, Date`), **3,096 groups (70.5%) have differing `Grade` values** (e.g. FAQ vs Medium vs Large). The previous pipeline omitted `Grade` from its series identifier, erroneously treating legitimate quality-grade price tiers as duplicate records. Incorporating `Grade` into the canonical key resolves 70.5% of conflicts.
2. **Order-Dependent Data Leakage in Previous Deduplication:**
   The original pipeline used `.drop_duplicates(subset=..., keep='first')`. In 4,363 series-dates with conflicting modal prices, this silently retained an arbitrary quote dependent solely on the physical sorting of raw CSV files. For clean ML benchmarking, strict exclusion of the remaining 1,287 intra-grade conflicts eliminates label noise at a minor sample loss of 2.81%.
3. **The 21 Physical Mandis & The Jhansi Trap:**
   The nominal 42 market strings in Uttar Pradesh represent 20–21 physical market yards due to a statewide portal transition between November 1 and November 5, 2025, which appended `" APMC"` to market names. While 19 pairs represent clean pre/post transitions, **Jhansi (general municipal yard) and Jhansi (Grain) (specialist yard) operated concurrently across 306 calendar dates**. Merging them would corrupt market price discovery; they must remain distinct.
4. **Row-Based Shifts Are Econometrically Invalid:**
   In the existing `src/feature_engineering.py`, lag features were computed using row index shifts (`.shift(k)`). The audit revealed that `shift(7)` matched an exact 7-calendar-day lag in **only 20.14% of records**. The mean calendar gap was 11.45 days, with gaps extending up to 371 days due to Sunday closures, holidays, and missing trade days. Replacing row shifts with exact calendar joins (`Arrival_Date - 7 days`) achieves 75.24% coverage and restores temporal symmetry with the T+7 target. A bounded staleness feature ($\le 2$ calendar days lookback) recovers Monday post-weekend trading, reaching 88.16% coverage.
5. **Wholesale Prices Are Sticky; Fixed $\pm 2.5\%$ Creates False Accuracy:**
   At T+7, **17.14% of price changes are exactly 0.00%**; at T+3, **26.65% are exactly 0.00%**. Because agricultural wholesale prices change slowly, the fixed $\pm 2.5\%$ threshold traps 57.84% (T+7) and 68.20% (T+3) of observations in the "Normal" class. A dummy classifier predicting "Normal" achieves 54% out-of-sample accuracy with zero predictive skill. Quantile-based classification (25/50/25) estimated strictly on the training partition provides an objective, zero-leakage alternative.

---

## 2. Duplicate Record Investigation

### 2.1 Categorization of Duplicate Groups

Across 160,192 raw records, exactly 4,393 groups share the series-date coordinate `(District, Market, Commodity, Variety, Arrival_Date)`:

- **Category A (Identical across all 11 columns):** **0 groups** (0 rows). Zero pure duplicate lines exist.
- **Category B (Conflicting `Modal_Price`):** **4,363 groups** (8,784 rows). Conflicting prices on the same trading day.
- **Category C (Same `Modal_Price`, conflicting Min/Max):** **17 groups** (34 rows). Same modal price but differing daily spreads.
- **Category D (Differing `Grade` within group):** **3,096 groups** (6,176 rows). **70.5% of duplicates are multi-grade trades.**
- **Category E (Conflicting prices with identical `Grade`):** **1,287 groups** (2,642 rows). True reporting ambiguity.

### 2.2 Comparison of Candidate Strategies

Full computational comparison from [duplicate_resolution_comparison.csv](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/backing/phase_02/outputs/duplicate_resolution_comparison.csv):

| Strategy | Retained Rows | Unique Series-Dates | T+7 Matches | T+7 Match Rate | R7 Std Dev | Normal % | Defensibility Verdict |
|---|---|---|---|---|---|---|---|
| **1. Preserve & Flag** | 160,192 | 155,741 | 127,111 (Cartesian) | N/A | 19.45% | 57.41% | **DEFENSIBLE AUDIT BASELINE** (Storage only) |
| **2. Exclude Ambiguous** | 151,361 | 151,361 | 112,227 | 74.63% | 16.99% | 58.69% | **DEFENSIBLE FOR CLEAN BENCHMARKING** |
| **3. Median Aggregation** | 155,741 | 155,741 | 117,176 | 75.73% | 17.53% | 58.22% | **DEFENSIBLE SENSITIVITY CHECK** |
| **4. Grade-Stratified Key** | 158,839 | 158,839 | 118,712 | 75.24% | 18.15% | 57.80% | **RECOMMENDED DOMAIN SPECIFICATION** |
| **5. Original Silent Drop** | 155,741 | 155,741 | 117,176 | 75.73% | 18.11% | 57.84% | **METHODOLOGICALLY FLAWED** (Silent corruption) |

---

## 3. Canonical Market Mapping Decisions

The 42 nominal market strings in the raw data were evaluated in [canonical_market_mapping.csv](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/backing/phase_02/outputs/canonical_market_mapping.csv):

1. **Statewide November 2025 Transition (19 Mandis):**
   - Mandis across Ghaziabad, Jhansi, Kanpur, Lucknow, and Unnao transitioned from `<Name>` to `<Name> APMC` between Nov 1 and Nov 5, 2025.
   - Max date overlap is 2 to 4 days during portal cutover.
   - **Verdict: APPROVED.** Maps to 19 base canonical markets, unlocking +1,842 continuous transition pairs.
2. **The Concurrent Mandi Trap in Jhansi:**
   - `Jhansi` (general yard, 3,755 raw rows) and `Jhansi (Grain)` (specialist yard, 1,160 raw rows) operated concurrently across **306 calendar dates**.
   - **Verdict: REJECTED MERGER.** `Jhansi` and `Jhansi (Grain)` are confirmed as separate physical operations and mapped to distinct canonical keys.
3. **Phonetic Spelling Variants:**
   - In Kanpur, `Varipaal APMC` and `Baripaal APMC` share 56 overlapping dates starting in March 2026.
   - **Verdict: PROPOSED / UNRESOLVED (MEDIUM CONFIDENCE).** Requires sensitivity testing before hardcoded unification.

---

## 4. Exact-Calendar Lag Feature Audit

Full comparison from [calendar_lag_coverage.csv](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/backing/phase_02/outputs/calendar_lag_coverage.csv):

| Lag Feature | Market Scope | Intended Meaning | Valid Rows | Missing % | Exact Calendar Match % | Mean Actual Gap | Max Actual Gap | Methodological Soundness |
|---|---|---|---|---|---|---|---|---|
| `shift(1)` | Raw Mandis | 1st previous row | 153,697 | 1.31% | 74.72% | 2.07 days | 303 days | Flawed (Weekend distortion) |
| `shift(3)` | Raw Mandis | 3rd previous row | 150,198 | 3.56% | 47.22% | 5.68 days | 310 days | Flawed (3rd row $\ne$ 3 days) |
| `shift(7)` | Raw Mandis | 7th previous row | 144,296 | 7.35% | **19.92%** | **12.01 days** | **371 days** | **CRITICAL DEFECT (Only 20% match 7d)** |
| `Calendar_Lag_1` | Raw Mandis | Exact $T-1$ date | 114,837 | 26.26% | 100.0% | 1.00 days | 1 day | Sound (Sunday closures missing) |
| `Calendar_Lag_7` | Raw Mandis | Exact $T-7$ date | 117,176 | 24.76% | 100.0% | 7.00 days | 7 days | **STRICTLY SOUND (75.24% coverage)** |
| `Bounded_Lag_7` | Raw Mandis | $T-7$ (lookback $\le 2$d) | 136,701 | 12.23% | 85.34% | 7.36 days | 9 days | **PRACTICAL (88.16% coverage)** |
| `Calendar_Lag_7` | Canonical | Exact $T-7$ date | 118,099 | 24.17% | 100.0% | 7.00 days | 7 days | **RECOVERS TRANSITION (+1,842 pairs)** |

---

## 5. Forecast Target Definition Comparison

Audit of 117,176 matched pairs at T+7 and 110,349 matched pairs at T+3 in [target_definition_comparison.csv](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/backing/phase_02/outputs/target_definition_comparison.csv):

- **Price Stickiness:**
  - $R_7 = 0.0000\%$ in **20,085 matched pairs (17.14%)**.
  - $R_3 = 0.0000\%$ in **29,408 matched pairs (26.65%)**.
- **Fixed $\pm 2.5\%$ Imbalance:**
  - T+7: Favorable 19.73%, Normal **57.84%**, Unfavorable 22.43%.
  - T+3: Favorable 15.01%, Normal **68.20%**, Unfavorable 16.79%.
  - Normal class dominates due to zero/near-zero daily price adjustments.
- **Quantile Classification Alternative:**
  - Training-period quartiles (25/50/25 cutoffs: $\le -2.00\%$ and $\ge +1.43\%$) yield 25.55% Favorable, 49.62% Normal, 24.84% Unfavorable on forward data with **zero lookahead leakage**.
- **Boundary Handling:**
  - Exactly 1,005 rows at T+7 and 465 rows at T+3 are boundary-truncated by the dataset end date ($T+h > \text{2026-09-01}$).
  - Interior missing targets: 37,560 at T+7 (due to mandi closures / non-reporting).
  - Denominator $\le 0$: 0 occurrences in valid matched targets.

---

## 6. Sensitivity Summary

From [methodology_sensitivity_summary.csv](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/backing/phase_02/outputs/methodology_sensitivity_summary.csv):
- Excluding ambiguous duplicate dates reduces total volume by 2.81% (151,361 vs 155,741) but eliminates 8,818 conflicting quotes, stabilizing return variance ($\sigma=16.99\%$ vs $17.53\%$).
- Exact-calendar lag replaces corrupted row lags (mean 12 days) with true 7-day lags (75.24% coverage).
- T+7 is statistically superior to T+3: higher trading coverage (75.73% vs 71.07%) and lower sticky price rate (17.14% vs 26.65%).

---

## 7. Automated Test Execution

All 13 automated methodology test specifications in [test_phase02_methodology.py](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/backing/phase_02/tests/test_phase02_methodology.py) were executed:

```
collected 13 items
test_duplicate_handling_preserves_original_source_records PASSED [  7%]
test_ambiguous_price_groups_are_explicitly_flagged PASSED [ 15%]
test_duplicate_resolution_strategies_produce_expected_group_counts PASSED [ 23%]
test_market_mappings_preserve_raw_names PASSED [ 30%]
test_unapproved_market_mappings_are_not_silently_applied PASSED [ 38%]
test_exact_calendar_lags_use_intended_calendar_date PASSED [ 46%]
test_missing_calendar_dates_remain_missing PASSED [ 53%]
test_no_future_observations_enter_historical_lag_features PASSED [ 61%]
test_target_joins_match_exact_intended_date PASSED [ 69%]
test_zero_and_negative_prices_excluded_from_return_calculations PASSED [ 76%]
test_target_classes_handle_exact_boundaries PASSED [ 84%]
test_boundary_truncated_and_interior_missing_targets_distinguished PASSED [ 92%]
test_every_required_output_exists_and_has_valid_schema PASSED [100%]
============================== 13 passed in 0.27s ==============================
```

Full output is recorded in [test_results.txt](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/backing/phase_02/tests/test_results.txt).

---

## 8. Defensible Recommendations for Phase 3 Modeling

1. **Stratify Series by Grade:** Update pipeline series keys to include `Grade` (`District__Market__Commodity__Variety__Grade`).
2. **Exclude Ambiguous Intra-Grade Dates:** For training splits, drop the 1,287 ambiguous series-dates to guarantee clean ground truth labels.
3. **Adopt Canonical Mandi Lookup:** Use approved canonical mappings for feature construction while maintaining raw strings in storage. Never merge `Jhansi` and `Jhansi (Grain)`.
4. **Replace Row Shifts with Exact Calendar Lags:** Deprecate `.shift(k)` in `src/feature_engineering.py`. Implement exact calendar lag features (`T-7`) and documented bounded staleness features (`Bounded_Lag_7`).
5. **Benchmark Against Naive Majority Class:** In Phase 3 evaluations, always benchmark classification models against the 54% majority class baseline, and test regression on continuous returns to bypass arbitrary class boundaries.

---

## 9. Phase Decision

**PHASE 02 DECISION: PASS**  
All audit objectives, empirical comparisons, output CSVs, evidence documents, and test specifications were successfully completed and mathematically verified. Production code changes and model training remain untouched, ready for review.
