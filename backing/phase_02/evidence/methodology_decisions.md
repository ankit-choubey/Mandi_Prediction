# Phase 02 — Methodology Decisions and Empirical Audit

**Project:** Mandi_Prediction  
**Phase:** 02 — Data Handling and Methodology Remediation  
**Date:** 2026-10-10  
**Branch:** `audit/phase-02-methodology`  
**Execution Environment:** macOS Apple Silicon, Python 3.14.0, pandas 2.3.3  

---

## 1. Executive Summary of Methodological Findings

Phase 2 evaluated the empirical validity and sensitivity of four foundational modeling decisions previously implemented or assumed in `Mandi_Prediction`:
1. **Duplicate Resolution:** Discovered that 70.5% (3,096 of 4,393) of conflicting series-date groups were caused by omitting `Grade` from the series key. Multi-grade trading (FAQ vs Medium vs Large) was falsely flagged as duplicate rows. For the remaining 1,287 intra-grade conflicts, strict exclusion guarantees 100% label purity for training, while median aggregation serves as a robust volume sensitivity benchmark.
2. **Canonical Market Identity:** Confirmed that the statewide appending of `" APMC"` in November 2025 artificially bifurcated 19 market time series. Proposed canonical mapping unifies 42 nominal market strings into 20–21 physical yards. Crucially, audit discovered that `Jhansi` (general market) and `Jhansi (Grain)` (specialist yard) operated concurrently across 306 dates; merging them is **strictly rejected**.
3. **Exact-Calendar Lag Features:** Proved that the previous code's row-based `shift(7)` matches 7 calendar days in **only 20.14% of rows** (mean lag gap is 11.45 days, max 371 days). Exact-calendar joins (`Arrival_Date - 7 days`) achieve 75.24% coverage and eliminate severe lookback distortion. A bounded staleness feature ($\le 2$ calendar days lookback) recovers Monday post-weekend trading, reaching 88.16% coverage.
4. **Target Formulation & Class Imbalance:** Proved that wholesale mandi prices are highly sticky: **17.14% of T+7 returns and 26.65% of T+3 returns are exactly 0.00%**. Consequently, the arbitrary fixed $\pm 2.5\%$ threshold leaves 57.84% of T+7 rows and 68.20% of T+3 rows in the "Normal" class, explaining why naive majority-class prediction achieves 54% test accuracy without predictive skill. Quantile quartiles estimated strictly on training dates resolve this imbalance without lookahead leakage.

---

## 2. Duplicate Record Investigation

### 2.1 Empirical Typology of Duplicate Groups

Across 160,192 raw records, 4,393 groups share the same `(District, Market, Commodity, Variety, Arrival_Date)`:

| Typology Category | Criteria | Unique Groups | Affected Rows | Share of Duplicates | Root Cause & Data Evidence |
|---|---|---|---|---|---|
| **Category A** | Identical across all 11 columns | 0 | 0 | 0.0% | Zero exact duplicate rows exist in the raw files. |
| **Category B** | Conflicting `Modal_Price` | 4,363 | 8,784 | 99.3% | Different prices reported for same variety on same date. |
| **Category C** | Identical Modal, conflicting Min/Max | 17 | 34 | 0.4% | Different price spreads reported around same modal price. |
| **Category D** | Differing `Grade` within group | 3,096 | 6,176 | 70.5% | **Multi-Grade Reporting:** Records differ in AGMARKNET `Grade` (e.g. FAQ vs Medium vs Large). |
| **Category E** | Conflicting prices with identical `Grade` | 1,287 | 2,642 | 29.3% | Reporting anomalies, intra-day auction sessions, or vendor-specific quotes. |

### 2.2 Comparison of Candidate Duplicate Handling Strategies

Five strategies were evaluated using full dataset computation (see [duplicate_resolution_comparison.csv](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/backing/phase_02/outputs/duplicate_resolution_comparison.csv)):

| Strategy ID & Description | Retained Rows | Unique Series-Dates | T+7 Matched Targets | T+7 Match Rate | Mean R7 | Std R7 | Normal Class % | Audit Verdict & Defensibility |
|---|---|---|---|---|---|---|---|---|
| **Strat 1: Preserve All & Flag** | 160,192 | 155,741 | 127,111 (Cartesian) | N/A | 0.72% | 19.45% | 57.41% | **DEFENSIBLE AUDIT BASELINE:** 100% data fidelity preserved; flags 8,818 rows for audit. |
| **Strat 2: Exclude Ambiguous Dates** | 151,361 | 151,361 | 112,227 | 74.63% | 0.52% | 16.99% | 58.69% | **DEFENSIBLE BENCHMARK:** 100% label purity; excludes 4,380 ambiguous dates; zero noise. |
| **Strat 3: Median Aggregation** | 155,741 | 155,741 | 117,176 | 75.73% | 0.59% | 17.53% | 58.22% | **DEFENSIBLE SENSITIVITY CHECK:** Robust to outliers; retains 100% series-date coordinates. |
| **Strat 4: Grade-Stratified Key** | 158,839 | 158,839 | 118,712 | 75.24% | 0.64% | 18.15% | 57.80% | **RECOMMENDED DOMAIN SPECIFICATION:** Explains 70.5% of conflicts; respects physical quality tiers. |
| **Strat 5: Original Silent Drop** | 155,741 | 155,741 | 117,176 | 75.73% | 0.63% | 18.11% | 57.84% | **METHODOLOGICALLY FLAWED:** `keep='first'` creates order-dependent arbitrary price labels. |

**Key Decision:** The production feature engineering pipeline must incorporate `Grade` into the series identifier. For the remaining 1,287 intra-grade ambiguous groups, Strategy 2 (Exclusion) is adopted as the primary training benchmark, while Strategy 3 (Median) is maintained for volume sensitivity testing.

---

## 3. Canonical Market Mapping Audit

### 3.1 The November 2025 Statewide APMC Transition

Between November 1 and November 5, 2025, AGMARKNET modified market string conventions across Uttar Pradesh. Across 42 nominal market strings in the 5 raw CSVs, 19 markets exhibit a clean transition where the base market ceased reporting and `<Market> APMC` commenced reporting with only 2–4 overlapping dates (see [canonical_market_mapping.csv](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/backing/phase_02/outputs/canonical_market_mapping.csv)).

Unifying these 19 pairs into canonical market identities restores 2-year temporal continuity and unlocks **+1,842 valid T-7 and T+7 transition pairs** that were previously lost at the November 2025 boundary.

### 3.2 Physical Market Mapping Classification

| District | Raw Market Names | Canonical Target | Max Date Overlap | Status | Justification |
|---|---|---|---|---|---|
| **Ghaziabad** | Ghaziabad, Ghaziabad APMC | `Ghaziabad` | 4 days | **APPROVED** | Clean Nov 1-4, 2025 transition. |
| **Ghaziabad** | Hapur, Hapur APMC | `Hapur` | 4 days | **APPROVED** | Clean Nov 1-5, 2025 transition. |
| **Ghaziabad** | Muradnagar, Muradnagar APMC | `Muradnagar` | 4 days | **APPROVED** | Clean Nov 1-4, 2025 transition. |
| **Ghaziabad** | Noida, Noida APMC | `Noida` | 2 days | **APPROVED** | Clean Nov 1-3, 2025 transition. |
| **Jhansi** | Baruwasagar, Baruwasagar APMC | `Baruwasagar` | 3 days | **APPROVED** | Clean Nov 3-5, 2025 transition. |
| **Jhansi** | Chirgaon, Chirgaon APMC | `Chirgaon` | 2 days | **APPROVED** | Clean Nov 2-4, 2025 transition. |
| **Jhansi** | Gurusarai, Gurusarai APMC | `Gurusarai` | 4 days | **APPROVED** | Clean Nov 1-4, 2025 transition. |
| **Jhansi** | **Jhansi, Jhansi APMC** | `Jhansi` | 4 days | **APPROVED** | General municipal APMC yard. |
| **Jhansi** | **Jhansi (Grain), Jhansi (Grain) APMC, Jhansi Grain APMC** | `Jhansi (Grain)` | 2–10 days | **APPROVED (SEPARATE)** | **Specialized grain yard; ran concurrently with Jhansi for 306 days.** |
| **Jhansi** | Mauranipur, Mauranipur APMC | `Mauranipur` | 4 days | **APPROVED** | Clean Nov 1-4, 2025 transition. |
| **Jhansi** | Moth, Moth APMC | `Moth` | 4 days | **APPROVED** | Clean Nov 1-4, 2025 transition. |
| **Kanpur** | Chaubepur, Chaubepur APMC | `Chaubepur` | 4 days | **APPROVED** | Clean Nov 1-4, 2025 transition. |
| **Kanpur** | Kanpur(Grain), Kanpur(Grain) APMC | `Kanpur(Grain)` | 4 days | **APPROVED** | Specialist grain terminal. |
| **Kanpur** | Pokhrayan, Pokhrayan APMC | `Pokhrayan` | 4 days | **APPROVED** | Clean Nov 1-4, 2025 transition. |
| **Kanpur** | Rura, Rura APMC | `Rura` | 4 days | **APPROVED** | Clean Nov 1-4, 2025 transition. |
| **Kanpur** | Uttaripura, Uttaripura APMC | `Uttaripura` | 4 days | **APPROVED** | Clean Nov 1-4, 2025 transition. |
| **Kanpur** | **Varipaal, Varipaal APMC, Baripaal APMC** | `Varipaal` | 56 days | **PROPOSED / UNRESOLVED** | Phonetic spelling variant (`Varipaal` vs `Baripaal`) appeared March 2026. |
| **Lukhnow** | Bakshi Ka Talab, Bakshi Ka Talab APMC | `Bakshi Ka Talab` | 4 days | **APPROVED** | Clean Nov 1-4, 2025 transition. |
| **Lukhnow** | Lucknow, Lucknow APMC | `Lucknow` | 4 days | **APPROVED** | Main state capital APMC terminal. |
| **Lukhnow** | Malihabad, Malihabad APMC | `Malihabad` | 4 days | **APPROVED** | Mango belt APMC terminal. |
| **Unnao** | Bangarmau, Bangarmau APMC | `Bangarmau` | 4 days | **APPROVED** | Clean Nov 1-4, 2025 transition. |
| **Unnao** | Purwa, Purwa APMC | `Purwa` | 4 days | **APPROVED** | Clean Nov 1-4, 2025 transition. |
| **Unnao** | Safipur, Safipur APMC | `Safipur` | 3 days | **APPROVED** | Clean Nov 2-4, 2025 transition. |
| **Unnao** | Unnao, Unnao APMC | `Unnao` | 4 days | **APPROVED** | District central APMC yard. |

**Defensibility Verdict:** Collapsing nominal mandis to 20–21 physical yards is strongly defensible under the condition that specialized yards (`Jhansi (Grain)`) are maintained separately.

---

## 4. Exact-Calendar Lag Feature Audit

### 4.1 Row-Based Shift Distortion

The original `src/feature_engineering.py` generated lag features via `.groupby('series_id')['Modal_Price'].shift(k)`.

As detailed in [calendar_lag_coverage.csv](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/backing/phase_02/outputs/calendar_lag_coverage.csv):
- `shift(1)` represents an actual calendar gap of 1 day in **74.72%** of records (mean gap 2.07 days, max gap 303 days).
- `shift(3)` represents an actual calendar gap of 3 days in **47.22%** of records (mean gap 5.68 days, max gap 310 days).
- `shift(7)` represents an actual calendar gap of 7 days in **ONLY 19.92% to 20.14%** of records (mean gap 12.01 days, max gap 371 days).

Treating `shift(7)` as a "1-week lag" is a severe econometric distortion: in 80% of rows, the feature was pulling prices from 8 to 371 calendar days in the past!

### 4.2 Exact-Calendar Join Coverage

Joining strictly on `Arrival_Date - 7 days`:
- **Coverage:** Exactly 117,176 records (75.24% of all series-date coordinates).
- **Temporal Symmetry:** Exactly matches the T+7 target join structure.
- **Missingness Reason:** Missing primarily on Mondays (due to Sunday market closure) and public holidays.

### 4.3 Bounded Staleness Alternative

To accommodate real-world agricultural trading where Sunday is closed, we tested `Calendar_Lag_7_Bounded2d`:
- Queries $T-7$; if missing, queries $T-8$; if missing, queries $T-9$ (maximum staleness bounded strictly to $\le 2$ calendar days).
- **Coverage:** Increases from 75.24% to **88.16%** (136,701 valid records).
- **Leakage Risk:** Zero. All lookbacks occur strictly before origin date $T$.

---

## 5. Forecast Target Definition Comparison

Audit of 117,176 matched pairs at T+7 and 110,349 matched pairs at T+3 across 5 target specifications (see [target_definition_comparison.csv](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/backing/phase_02/outputs/target_definition_comparison.csv)):

| Horizon | Target Definition | Class Distribution (Fav / Norm / Unfav) | Normal % | Sticky Price % (R = 0.00%) | Boundary Truncated | Interior Missing | Leakage Status | Defensibility Verdict |
|---|---|---|---|---|---|---|---|---|
| **T+7** | Continuous Return | N/A (Mean: 0.59%, Std: 17.53%, Median: 0.00%) | N/A | 17.14% (20,085) | 1,005 | 37,560 | Zero | **RECOMMENDED REGRESSION TARGET:** Eliminates arbitrary class binning. |
| **T+7** | Fixed $\pm 2.5\%$ | Fav: 19.73% / Norm: 57.84% / Unfav: 22.43% | **57.84%** | 17.14% (20,085) | 1,005 | 37,560 | Zero | **SEVERELY IMBALANCED:** Naive majority class predicts 54% test accuracy. |
| **T+7** | Volatility-Adjusted ($0.25 \sigma$) | Fav: 23.36% / Norm: 50.76% / Unfav: 25.87% | **50.76%** | 17.14% (20,085) | 1,005 | 37,560 | Zero (Expanding $\le T$) | **DYNAMIC ECONOMIC TARGET:** Adapts to perishable volatility vs grain stability. |
| **T+7** | Train Quantile Terciles (33/33/33) | Fav: 33.14% / Norm: 34.42% / Unfav: 32.44% | **34.42%** | 17.14% (20,085) | 1,005 | 37,560 | Zero (Estimated on Train split) | **BALANCED CLASSIFIER BENCHMARK:** Forces equal opportunity across classes. |
| **T+7** | Train Quantile Quartiles (25/50/25) | Fav: 25.55% / Norm: 49.62% / Unfav: 24.84% | **49.62%** | 17.14% (20,085) | 1,005 | 37,560 | Zero (Estimated on Train split) | **ROBUST OUTLIER TARGET:** Isolates genuine top/bottom quartiles. |
| **T+3** | Continuous Return | N/A (Mean: 0.24%, Std: 12.87%, Median: 0.00%) | N/A | 26.65% (29,408) | 465 | 44,927 | Zero | **HIGH STICKINESS REGRESSION TARGET.** |
| **T+3** | Fixed $\pm 2.5\%$ | Fav: 15.01% / Norm: 68.20% / Unfav: 16.79% | **68.20%** | 26.65% (29,408) | 465 | 44,927 | Zero | **EXTREMELY DEGRADED SIGNAL:** 68% in Normal; price doesn't move in 3 days. |

### 5.1 Exact Boundary Condition Auditing

- At T+7, exactly 131 rows landed on $+2.5000\%$ and 141 rows landed on $-2.5000\%$. The policy requires exact $\ge +2.5\%$ and $\le -2.5\%$ boundaries, placing edge cases in Favorable and Unfavorable respectively.
- Denominator validation: Denominators $\le 0$ occurred 0 times in valid matches (all 6 raw invalid prices occurred in isolated dates).
- Boundary truncation: Exactly 1,005 rows at T+7 and 465 rows at T+3 fall in the final $h$ calendar days of the dataset (August 26–September 1, 2026) and are verified as boundary-truncated, not missing.

---

## 6. Sensitivity Analysis Summary

As documented in [methodology_sensitivity_summary.csv](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/backing/phase_02/outputs/methodology_sensitivity_summary.csv):
1. **Label Purity vs Volume:** Excluding ambiguous series-date groups reduces dataset size by only 2.81% (from 155,741 to 151,361 rows) while completely eliminating arbitrary price selection. Return distributions remain virtually identical ($\mu=0.52\%$ vs $0.59\%$, $\sigma=16.99\%$ vs $17.53\%$).
2. **Horizon Selection:** T+7 is vastly superior to T+3 as a benchmark horizon: T+7 exhibits higher match coverage (75.73% vs 71.07%), lower sticky price rate (17.14% vs 26.65%), and more balanced signal (Normal: 57.84% vs 68.20%).
3. **Market Mapping:** Applying approved canonical market identities adds +1,842 valid observations across the November 2025 boundary without changing commodity-level return distributions.
