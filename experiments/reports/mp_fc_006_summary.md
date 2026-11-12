# Task Summary: Provisional-v2 Gates and Baseline Scorecard (No ML Models)

**Task ID:** `MP-FC-006`
**Date:** `2026-11-12`
**Execution Environment:** Remote Kaggle CPU Kernel (`theankitchoubey/mp-fc-006-baselines`, version 3, Internet Disabled)
**Dataset:** `theankitchoubey/mandi-prediction-audit-003b` (v1 private, unchanged)
**Baseline Git Commit:** `b231e27cefc8d29bdf448233253eaed7fe44fca0`
**Panel v2 Status:** **PROVISIONAL** (SHA-256: `851e718468d6b8c9fd07944535a462338e71aa105af25339fe9438b697088f31`)
**Audit Status:** Audited under Task `MP-AUDIT-007` (**CHANGES REQUIRED**). Scorecards are artifact-backed provisional benchmarks. The 77-disputed keys sensitivity is superseded due to uncanonicalized APMC matching; full rerun is designated **RERUN REQUIRED**. MASE is **NOT COMPUTED** (skill metric is paired test-relative MAE ratio vs Naive).

---

## 1. Executive Summary & Assertion Gate

Task `MP-FC-006` executes the empirical diagnostic gates on the provisional Panel v2 and establishes the baseline 7-day modal price forecasting scorecard across 4 chronological expanding folds using purely statistical and heuristic baselines (Naive, Moving Average, Seasonal Naive, and Drift). No machine learning models, external weather, or arrivals data were used.

> [!IMPORTANT]
> **Audit Reconciliation Notice (MP-AUDIT-007):**
> 1. **77 Disputed Keys Sensitivity Superseded:** The original sensitivity evaluation checked raw APMC market strings against canonicalized panel market strings (0 matches found). Re-evaluating with canonical market identities alters all 77 keys and requires a remote Kaggle rerun (**RERUN REQUIRED**).
> 2. **Metric Corrections:** Artifact-backed scorecard values from `scorecard_fold_x_tier.csv` supersede rounded/discrepant text in earlier draft summaries.
> 3. **Prediction Sample Limitation:** `baseline_predictions_sample.csv` (5,000 rows) contains F1 origins only; full-fold reproduction requires the complete predictions archive prepared in MP-AUDIT-007.
> 4. **Causal Claims Qualified:** Stable commodity median ratios are consistent with no unit change, but do not statutory prove units. Variety consolidation is empirically associated with volume reduction, but root cause remains an external hypothesis.

### Panel v2 Integrity Assertion Gate:
* **Cell 2 Execution:** Regenerated `mandi_5year_validated_v2.csv` directly from raw source files in `5 year dataset/*.csv` using `MandiDataPipeline(pipeline_version="v2")` and `data/reference/market_aliases.csv`.
* **Computed Digest:** `851e718468d6b8c9fd07944535a462338e71aa105af25339fe9438b697088f31`
* **Integrity Gate:** Asserted exact match against the approved specification hash. Assertion passed with 100% byte-for-byte consistency.

---

## 2. Part B1: Forensic Diagnostic Gates (Empirical Findings)

### Gate B1.a: Alias Transition Forensics
For every candidate pair in `data/reference/market_aliases.csv` (21 accepted pairs + 1 review pair) plus specified special pairs, transition dates, calendar gaps, overlap days, and price agreement were evaluated on raw historical quotes:

| District | Market Raw | Market Canonical | Older Name | Newer Name | Older First | Older Last | Newer First | Newer Last | Gap Days | Overlap Days | Overlapping Keys | Exact Price Match (%) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| Ghaziabad | Ghaziabad APMC | Ghaziabad | Ghaziabad | Ghaziabad APMC | 2021-09-01 | 2025-11-04 | 2025-11-01 | 2026-09-30 | -3 | 4 | 103 | 100.00% |
| Ghaziabad | Hapur APMC | Hapur | Hapur | Hapur APMC | 2021-09-01 | 2025-11-05 | 2025-11-01 | 2026-09-30 | -4 | 4 | 61 | 100.00% |
| Ghaziabad | Muradnagar APMC | Muradnagar | Muradnagar | Muradnagar APMC | 2021-09-01 | 2025-11-04 | 2025-11-01 | 2026-09-30 | -3 | 4 | 34 | 100.00% |
| Ghaziabad | Noida APMC | Noida | Noida | Noida APMC | 2021-09-02 | 2025-11-03 | 2025-11-01 | 2026-09-30 | -2 | 2 | 39 | 100.00% |
| Jhansi | Baruwasagar APMC | Baruwasagar | Baruwasagar | Baruwasagar APMC | 2021-09-02 | 2025-11-05 | 2025-11-03 | 2026-09-30 | -2 | 3 | 5 | 100.00% |
| Jhansi | Chirgaon APMC | Chirgaon | Chirgaon | Chirgaon APMC | 2021-09-01 | 2025-11-04 | 2025-11-02 | 2026-09-30 | -2 | 2 | 6 | 100.00% |
| Jhansi | Gurusarai APMC | Gurusarai | Gurusarai | Gurusarai APMC | 2021-09-01 | 2025-11-04 | 2025-11-01 | 2026-09-30 | -3 | 4 | 28 | 100.00% |
| Jhansi | Jhansi APMC | Jhansi | Jhansi | Jhansi APMC | 2021-09-01 | 2025-11-04 | 2025-11-01 | 2026-09-30 | -3 | 4 | 49 | 100.00% |
| Jhansi | Jhansi (Grain) APMC | Jhansi (Grain) | Jhansi (Grain) | Jhansi (Grain) APMC | 2024-05-25 | 2025-11-03 | 2025-11-02 | 2026-01-14 | -1 | 2 | 5 | 100.00% |
| Jhansi | Jhansi Grain APMC | Jhansi (Grain) | Jhansi (Grain) | Jhansi Grain APMC | 2024-05-25 | 2025-11-03 | 2026-01-01 | 2026-01-14 | +59 | 0 | 0 | N/A |
| Jhansi | Mauranipur APMC | Mauranipur | Mauranipur | Mauranipur APMC | 2021-09-01 | 2025-11-04 | 2025-11-01 | 2026-09-30 | -3 | 4 | 43 | 100.00% |
| Jhansi | Moth APMC | Moth | Moth | Moth APMC | 2021-09-01 | 2025-11-04 | 2025-11-01 | 2026-09-30 | -3 | 4 | 30 | 100.00% |
| Kanpur | Choubepur APMC | Choubepur | Choubepur | Choubepur APMC | 2021-09-01 | 2025-11-04 | 2025-11-01 | 2026-09-30 | -3 | 3 | 66 | 100.00% |
| Kanpur | Kanpur(Grain) APMC | Kanpur(Grain) | Kanpur(Grain) | Kanpur(Grain) APMC | 2021-09-01 | 2025-11-04 | 2025-11-01 | 2026-09-30 | -3 | 3 | 63 | 100.00% |
| Kanpur | Uttaripura APMC | Uttaripura | Uttaripura | Uttaripura APMC | 2021-10-24 | 2025-11-04 | 2025-11-01 | 2026-09-30 | -3 | 3 | 66 | 100.00% |
| Kanpur | Varipaal APMC | Varipaal | Varipaal | Varipaal APMC | 2021-09-01 | 2025-11-04 | 2025-11-01 | 2026-04-26 | -3 | 3 | 47 | 100.00% |
| Lucknow | Banthara APMC | Banthara | Banthara | Banthara APMC | 2022-05-18 | 2025-11-04 | 2025-11-01 | 2026-09-30 | -3 | 4 | 8 | 100.00% |
| Lucknow | Lucknow APMC | Lucknow | Lucknow | Lucknow APMC | 2021-09-01 | 2025-11-04 | 2025-11-02 | 2026-09-30 | -2 | 3 | 64 | 100.00% |
| Unnao | Bangarmau APMC | Bangarmau | Bangarmau | Bangarmau APMC | 2021-09-01 | 2025-11-04 | 2025-11-01 | 2026-09-30 | -3 | 4 | 88 | 100.00% |
| Unnao | Purwa APMC | Purwa | Purwa | Purwa APMC | 2021-09-01 | 2025-07-31 | 2026-02-21 | 2026-09-30 | +205 | 0 | 0 | N/A |
| Unnao | Unnao APMC | Unnao | Unnao | Unnao APMC | 2021-09-01 | 2025-11-04 | 2025-11-01 | 2026-09-30 | -3 | 3 | 27 | 100.00% |
| Kanpur | Baripaal APMC | Varipaal | Varipaal | Baripaal APMC | 2021-09-01 | 2025-11-04 | 2026-03-01 | 2026-09-30 | +117 | 0 | 0 | N/A |
| Kanpur | Baripaal APMC | Varipaal APMC | Varipaal APMC | Baripaal APMC | 2025-11-01 | 2026-04-26 | 2026-03-01 | 2026-09-30 | -56 | 52 | 462 | 95.67% |
| Jhansi | Jhansi Grain APMC | Jhansi (Grain) APMC | Jhansi (Grain) APMC | Jhansi Grain APMC | 2025-11-02 | 2026-01-14 | 2026-01-01 | 2026-01-14 | -13 | 10 | 23 | 100.00% |

#### Observations from Alias Forensics:
1. **Unanimous Price Agreement in Dual-Reporting Overlaps:** Across all 19 standard accepted pairs with overlapping quotes during the 2025-11-01 to 2025-11-05 transition window (758 total overlapping natural keys), exact price agreement is **100.00%**.
2. **Baripaal vs Varipaal APMC Overlap:** In Kanpur, `Varipaal APMC` (reported until 2026-04-26) and `Baripaal APMC` (reported from 2026-03-01) overlapped for 52 calendar days across 462 keys, achieving **95.67% exact price agreement** (442 of 462 exact matches).
3. **Jhansi Grain APMC vs Jhansi (Grain) APMC:** Overlapped for 10 calendar days in January 2026 across 23 keys with **100.00% exact price agreement**.

---

### Gate B1.b: Reclassification of the 1,895 Unmatched In-Window Excel Rows on v2
Across the 14,741 in-window Excel records (2021-09-01 to 2026-09-30), 12,846 matched Panel v2 (87.14%). The 1,895 unmatched records were classified into explicit, mutually exclusive categories:

| Category | Description | Count | Share (%) |
| :--- | :--- | :---: | :---: |
| `low_obs_dropped` | Series present in raw data but dropped by pipeline due to $< 20$ historical observations across 5 years | 923 | 48.71% |
| `other` | Market naming mismatch between Excel and raw files (e.g. Kanpur `Baripaal APMC` unmapped to raw anchor) | 420 | 22.16% |
| `quarantined_strategy2` | Raw records dropped by validation due to invalid price quotes ($\text{Min} > \text{Max}$ or Modal outside $[\text{Min}, \text{Max}]$) | 323 | 17.05% |
| `absent_from_raw` | Record present in Agmarknet Excel reports but completely absent from raw historical download CSVs | 197 | 10.40% |
| `spelling_unmapped` | Same district, market, commodity, and date, but variety or grade string differs slightly | 32 | 1.69% |
| **Total Unmatched** | | **1,895** | **100.00%** |

#### District-Level Breakdown:
| District | `low_obs_dropped` | `other` | `quarantined_strategy2` | `absent_from_raw` | `spelling_unmapped` | Total |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Ghaziabad | 196 | 1 | 81 | 77 | 6 | 361 |
| Jhansi | 205 | 20 | 26 | 22 | 7 | 280 |
| Kanpur | 275 | 379 | 80 | 33 | 5 | 772 |
| Lucknow | 172 | 19 | 106 | 27 | 14 | 338 |
| Unnao | 75 | 1 | 30 | 38 | 0 | 144 |
| **Total** | **923** | **420** | **323** | **197** | **32** | **1,895** |

---

### Gate B1.c: Tier A Training Observations Reconciliation
* **Training Cutoff Date:** `2025-12-18` (prior to Agmarknet 2.0 platform divergence).
* **Eligibility Rule:** Observations $\ge 60$ and coverage $\ge 0.30$ within history dated $\le 2025-12-18$.
* **v1 Tier A (As-Is Market):** 496 series, **384,887 observations**.
* **v2 Tier A (Canonical Market, $\le 2025-12-18$):** 492 series, **387,242 observations** (Net delta: **+2,355 rows**).
* **v2 Tier A (Canonical Market, Full 5-Year Panel):** 492 series, **404,498 observations**.

#### Set Dispositions at Cutoff `2025-12-18`:
* **Entering Series (2 series, +571 observations):**
  - `Kanpur__Uttaripura__Bajra(Pearl Millet/Cumbu)__Hybrid__FAQ` (140 obs)
  - `Kanpur__Varipaal__Apple__Apple__Medium` (431 obs)
* **Leaving Series (6 series, -1,408 observations):**
  - `Jhansi__Chirgaon__Tomato__Tomato__FAQ` (112 obs)
  - `Kanpur__Kanpur(Grain)__Jowar(Sorghum)__White__FAQ` (187 obs)
  - `Kanpur__Uttaripura__Bengal Gram(Gram)(Whole)__Desi (Whole)__FAQ` (165 obs)
  - `Kanpur__Varipaal__Onion__Onion__FAQ` (338 obs)
  - `Lucknow__Lucknow__Carrot__Carrot__FAQ` (384 obs)
  - `Lucknow__Lucknow__Peas cod__Peas cod__FAQ` (222 obs)
* **Common Series (490 series, +3,192 observations):** Observations gained through the merger of pre-Nov 2025 canonical series with early Nov-Dec 2025 APMC-suffixed quotes.

---

### Gate B1.d: Fractional Prices Diagnostics (Post 2026-03)
* **First Calendar Month Exceeding 5% Fractional Share:** **`2026-02`** (8.73% fractional quotes; rises to 35.84% in `2026-03` and peaks at 44.52% in `2026-07`).
* **Post 2026-03 Total Observations:** 31,601 records.
* **Fractional Quotes Post 2026-03:** 12,923 records (**40.89%** fractional; 59.11% exact integers).
* **Adjacent-Day Integer Test:**
  - Among fractional quotes, **78.22%** have an adjacent observation ($t \pm 1$ calendar day) for the same series.
  - Among those adjacent observations, **38.83% are exact integers**, indicating that series routinely alternate between integer and fractional prices within consecutive trading days.
* **Commodity Median Price Ratio (Post 2026-03 vs Pre 2026-03):**
  - Median ratio across commodities: **1.0000**
  - Mean ratio: **1.0788** (Min: 0.6140, Max: 2.9545)
  - The unit-level commodity median is identical before and after March 2026. This is consistent with no unit change, but does not independently establish statutory reporting units without explicit source documentation.

#### Top Decimals Post 2026-03:
| Decimal Part | Frequency | Share (%) |
| :---: | :---: | :---: |
| `.00` (Integer) | 18,678 | 59.11% |
| `.33` | 230 | 0.73% |
| `.50` | 229 | 0.72% |
| `.67` | 203 | 0.64% |
| `.25` | 156 | 0.49% |
| `.57` | 152 | 0.48% |
| `.24` | 150 | 0.47% |
| `.27` | 149 | 0.47% |

---

### Gate B1.e: Monthly Reporting Depth Diagnostics
Across the 61 calendar months, tracking active markets, commodities, and varieties clarifies the structural volume shift:

| Year-Month | Monthly Rows | Active Markets (GZB) | Active Markets (JHS) | Active Markets (KNP) | Active Markets (LKO) | Active Markets (UNA) | Total Active Markets | Unique Commodities | Unique Varieties | Unique Series |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 2025-07 | 8,869 | 4 | 7 | 4 | 2 | 3 | 20 | 65 | 87 | 447 |
| 2025-08 | 8,037 | 4 | 7 | 4 | 2 | 2 | 19 | 64 | 86 | 405 |
| 2025-09 | 7,682 | 4 | 7 | 4 | 2 | 2 | 19 | 61 | 82 | 398 |
| 2025-10 | 6,726 | 4 | 7 | 4 | 2 | 2 | 19 | 61 | 81 | 415 |
| 2025-11 | 3,582 | 4 | 7 | 4 | 2 | 2 | 19 | 65 | 80 | 434 |
| 2025-12 | 3,004 | 3 | 7 | 4 | 2 | 2 | 18 | 48 | 58 | 202 |
| 2026-01 | 1,541 | 3 | 7 | 4 | 2 | 2 | 18 | 47 | 56 | 165 |
| 2026-02 | 871 | 4 | 6 | 4 | 2 | 3 | 19 | 59 | 45 | 233 |
| 2026-03 | 4,141 | 4 | 6 | 5 | 2 | 3 | 20 | 62 | 55 | 372 |
| 2026-04 | 4,722 | 4 | 6 | 5 | 2 | 3 | 20 | 68 | 52 | 421 |
| 2026-05 | 4,834 | 4 | 6 | 4 | 2 | 3 | 19 | 64 | 40 | 389 |
| 2026-06 | 4,828 | 4 | 6 | 4 | 2 | 3 | 19 | 59 | 35 | 383 |
| 2026-07 | 4,431 | 4 | 6 | 4 | 2 | 3 | 19 | 57 | 35 | 382 |
| 2026-08 | 4,213 | 4 | 6 | 4 | 2 | 3 | 19 | 63 | 40 | 377 |
| 2026-09 | 4,432 | 4 | 6 | 4 | 2 | 3 | 19 | 62 | 39 | 372 |

#### Diagnostic Observation on Volume Shift:
* **Active reporting markets remained completely stable:** 18 to 20 markets reported throughout the entire 5 years.
* **Variety consolidation is associated with the post-2026 row drop:** While reporting markets and commodities remained steady, the number of distinct varieties reported declined from ~85 down to ~35-40 in mid-2026. This variety consolidation is empirically correlated with the reduction in multi-variety quotes per market day; direct causal attribution remains an external hypothesis.

---

## 3. Part B2: Baseline Forecasting Scorecard

### Evaluation Protocol:
* **Horizon:** 7 days forward.
* **Target:** Modal price of the observation in $[t+6, t+8]$ closest to $t+7$ (tie: earlier). Target must fall within fold end.
* **Serving-Time Recency Rule:** Origins are evaluated only if the series has $\ge 3$ observations in $[t-30\text{d}, t]$.
* **Models:**
  1. **Naive:** $\hat{y}(t+7) = y(t)$
  2. **Moving Average (MA):** Mean of the last $\le 7$ observations in $[t-30\text{d}, t]$ (abstains if $<3$).
  3. **Seasonal Naive:** Observation nearest to $t+7-364 = t-357$ in $[t-360, t-354]$ (abstains if none; tie: earlier).
  4. **Drift:** $y(t) + 0.5 \times \text{slope} \times 7$, slope from observation nearest $t-14$ in $[t-17, t-11]$ (abstains if none).
* **Confidence Intervals:** 95% cluster bootstrap over series (1,000 resamples, seed 42).

---

### Table 1: Fold $\times$ Tier Scorecard

| Fold | Tier | Model | N Origins | N Series | Abstain (%) | MAE (Rs/qtl) | 95% CI (MAE) | RMSE | MAPE (%) | Median AE | Bias | $\le 5\%$ (%) | Skill vs Naive | 95% CI (Skill) | Low-N |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **F1** | Tier A | Naive | 37,858 | 359 | 0.00% | 101.59 | [89.35, 114.11] | 280.70 | 4.30% | 40.00 | +21.14 | 75.77% | 0.0000 | [0.0000, 0.0000] | False |
| F1 | Tier A | MA | 37,858 | 359 | 0.00% | 131.22 | [113.36, 148.51] | 330.23 | 5.42% | 54.29 | +34.20 | 69.07% | -0.2917 | [-0.3205, -0.2595] | False |
| F1 | Tier A | Seasonal Naive | 35,232 | 359 | 6.94% | 685.48 | [588.02, 790.26] | 1172.99 | 27.84% | 370.00 | +178.11 | 20.18% | -5.7963 | [-6.7564, -5.0198] | False |
| F1 | Tier A | Drift | 37,404 | 359 | 1.20% | 97.95 | [87.19, 109.24] | 272.45 | 4.27% | 41.25 | +6.41 | 76.56% | **+0.0283** | [-0.0018, 0.0582] | False |
| **F2** | Tier A | Naive | 23,490 | 346 | 0.00% | 106.46 | [93.44, 118.92] | 252.94 | 3.60% | 40.00 | +15.16 | 79.47% | 0.0000 | [0.0000, 0.0000] | False |
| F2 | Tier A | MA | 23,490 | 346 | 0.00% | 135.69 | [117.66, 153.48] | 305.98 | 4.35% | 47.86 | +20.08 | 74.59% | -0.2746 | [-0.3051, -0.2410] | False |
| F2 | Tier A | Seasonal Naive | 21,044 | 346 | 10.41% | 979.90 | [823.25, 1157.29] | 1847.57 | 34.03% | 420.00 | +703.42 | 24.28% | -8.0459 | [-9.9901, -6.3941] | False |
| F2 | Tier A | Drift | 23,293 | 346 | 0.84% | 109.80 | [96.31, 122.41] | 254.36 | 3.88% | 42.50 | +12.56 | 77.87% | -0.0282 | [-0.0579, 0.0008] | False |
| **F3** | Tier A | Naive | 1,413 | 102 | 0.00% | 108.11 | [87.32, 131.00] | 197.35 | 6.13% | 50.00 | -12.91 | 61.43% | 0.0000 | [0.0000, 0.0000] | False |
| F3 | Tier A | MA | 1,413 | 102 | 0.00% | 124.63 | [100.03, 153.88] | 202.73 | 7.09% | 71.43 | -11.83 | 56.48% | -0.1528 | [-0.2715, -0.0548] | False |
| F3 | Tier A | Seasonal Naive | 1,322 | 102 | 6.44% | 513.64 | [374.56, 696.12] | 744.30 | 25.12% | 350.00 | -158.44 | 13.69% | -3.7850 | [-5.8690, -2.3931] | False |
| F3 | Tier A | Drift | 1,358 | 102 | 3.89% | 119.53 | [96.69, 146.36] | 217.01 | 6.78% | 60.17 | -14.77 | 60.46% | -0.1129 | [-0.1563, -0.0713] | False |
| **F4** | Tier A | Naive | 2,015 | 37 | 0.00% | 212.84 | [46.91, 458.94] | 785.62 | 6.75% | 22.75 | -12.73 | 74.64% | 0.0000 | [0.0000, 0.0000] | False |
| F4 | Tier A | MA | 2,015 | 37 | 0.00% | 179.27 | [46.69, 374.29] | 635.19 | 5.89% | 29.25 | -22.67 | 75.14% | **+0.1577** | [0.0106, 0.2405] | False |
| F4 | Tier A | Seasonal Naive | 1,602 | 37 | 20.50% | 244.88 | [77.05, 558.08] | 638.84 | 8.26% | 70.00 | -30.18 | 64.86% | -0.6214 | [-4.3191, -0.0795] | False |
| F4 | Tier A | Drift | 1,981 | 37 | 1.69% | 246.80 | [50.42, 536.27] | 886.69 | 7.88% | 31.17 | -6.12 | 71.93% | -0.1568 | [-0.1949, -0.1370] | False |
| **Overall**| **Tier A** | **Naive** | **64,776** | **401** | **0.00%** | **106.96** | **[96.35, 119.03]** | **298.83** | **4.16%** | **40.00** | **+17.17** | **76.76%** | **0.0000** | **[0.0000, 0.0000]** | False |
| Overall | Tier A | MA | 64,776 | 401 | 0.00% | 134.19 | [120.73, 149.35] | 333.37 | 5.08% | 50.71 | +26.30 | 70.98% | -0.2547 | [-0.2909, -0.2105] | False |
| Overall | Tier A | Seasonal Naive | 59,200 | 401 | 8.61% | 774.38 | [661.02, 895.07] | 1433.76 | 29.45% | 375.00 | +351.69 | 22.70% | -6.3738 | [-7.2432, -5.5137] | False |
| Overall | Tier A | Drift | 64,036 | 401 | 1.14% | 107.32 | [95.82, 119.13] | 303.67 | 4.29% | 42.00 | +7.81 | 76.55% | -0.0068 | [-0.0303, 0.0191] | False |
| **Overall**| **Tier B** | **Naive** | **62,932** | **379** | **0.00%** | **105.59** | **[94.09, 118.60]** | **282.95** | **4.13%** | **40.00** | **+18.14** | **76.76%** | **0.0000** | **[0.0000, 0.0000]** | False |
| Overall | Tier B | MA | 62,932 | 379 | 0.00% | 133.63 | [118.77, 150.13] | 325.03 | 5.07% | 51.43 | +27.76 | 70.92% | -0.2655 | [-0.3006, -0.2224] | False |
| Overall | Tier B | Seasonal Naive | 59,121 | 379 | 6.06% | 774.22 | [668.63, 891.12] | 1434.32 | 29.47% | 375.00 | +350.97 | 22.73% | -6.3712 | [-7.3187, -5.4652] | False |
| Overall | Tier B | Drift | 62,232 | 379 | 1.11% | 105.28 | [94.66, 116.84] | 283.06 | 4.24% | 42.50 | +8.38 | 76.63% | -0.0003 | [-0.0266, 0.0246] | False |

---

### Table 2: Focus Crops Baseline Scorecard (Overall Tier A)

| Crop | Model | N Origins | N Series | MAE (Rs/qtl) | 95% CI (MAE) | Skill vs Naive | 95% CI (Skill) | Low-N Flag |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Wheat** | Naive | 4,337 | 20 | 29.77 | [24.85, 35.21] | 0.0000 | [0.0000, 0.0000] | False |
| Wheat | Moving Average | 4,337 | 20 | 35.42 | [30.40, 40.11] | -0.1896 | [-0.2312, -0.1478] | False |
| Wheat | Seasonal Naive | 3,956 | 20 | 152.42 | [140.46, 167.03] | -3.9481 | [-4.7089, -3.3421] | False |
| Wheat | Drift | 4,281 | 20 | 33.44 | [27.95, 39.52] | -0.1325 | [-0.1895, -0.0765] | False |
| **Potato** | Naive | 3,628 | 19 | 49.87 | [43.46, 57.58] | 0.0000 | [0.0000, 0.0000] | False |
| Potato | Moving Average | 3,628 | 19 | 60.57 | [52.63, 69.72] | -0.2145 | [-0.2643, -0.1654] | False |
| Potato | Seasonal Naive | 3,452 | 19 | 689.22 | [656.84, 719.10] | -12.7134 | [-14.7392, -10.9576] | False |
| Potato | Drift | 3,602 | 19 | 52.17 | [43.14, 63.04] | -0.0474 | [-0.1065, 0.0154] | False |
| **Onion** | Naive | 3,454 | 20 | 83.89 | [76.54, 91.35] | 0.0000 | [0.0000, 0.0000] | False |
| Onion | Moving Average | 3,454 | 20 | 113.81 | [103.84, 124.40] | -0.3568 | [-0.4192, -0.2974] | False |
| Onion | Seasonal Naive | 3,106 | 20 | 1115.32 | [1025.59, 1193.89] | -11.8528 | [-13.7543, -10.1582] | False |
| Onion | Drift | 3,441 | 20 | **76.86** | [68.26, 85.01] | **+0.0818** | [0.0315, 0.1294] | False |
| **Tomato** | Naive | 3,024 | 20 | 158.61 | [141.48, 175.28] | 0.0000 | [0.0000, 0.0000] | False |
| Tomato | Moving Average | 3,024 | 20 | 212.41 | [190.71, 232.11] | -0.3392 | [-0.3876, -0.2912] | False |
| Tomato | Seasonal Naive | 2,924 | 20 | 958.66 | [901.89, 1005.45] | -5.1137 | [-5.8450, -4.4715] | False |
| Tomato | Drift | 2,993 | 20 | 158.52 | [137.64, 179.15] | +0.0072 | [-0.0456, 0.0612] | False |
| **Paddy(Dhan)(Common)** | Naive | 594 | 5 | 32.67 | [2.18, 65.32] | 0.0000 | [0.0000, 0.0000] | **True** ($N < 10$) |
| Paddy(Dhan)(Common) | Moving Average | 594 | 5 | **27.51** | [2.08, 54.18] | **+0.1579** | [0.1205, 0.2014] | **True** ($N < 10$) |
| Paddy(Dhan)(Common) | Seasonal Naive | 439 | 5 | 137.30 | [75.85, 175.30] | -2.2000 | [-3.1045, -1.4502] | **True** ($N < 10$) |
| Paddy(Dhan)(Common) | Drift | 594 | 5 | 38.26 | [2.62, 76.64] | -0.1710 | [-0.2201, -0.1198] | **True** ($N < 10$) |
| **Rice** | Naive | 2,732 | 15 | 163.54 | [45.03, 339.56] | 0.0000 | [0.0000, 0.0000] | False |
| Rice | Moving Average | 2,732 | 15 | **138.71** | [43.12, 273.22] | **+0.1518** | [0.0984, 0.2085] | False |
| Rice | Seasonal Naive | 2,467 | 15 | 346.86 | [238.50, 504.77] | -1.5786 | [-2.1054, -1.1420] | False |
| Rice | Drift | 2,707 | 15 | 190.46 | [52.80, 393.37] | -0.1644 | [-0.2185, -0.1102] | False |

---

### Table 3: Sensitivities Scorecard (Overall Tier A)

| Sensitivity Slice | Model | N Origins | N Series | MAE (Rs/qtl) | 95% CI (MAE) | Skill vs Naive | 95% CI (Skill) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Exact T+7 Subset** | Naive | 56,386 | 399 | 104.97 | [93.97, 117.08] | 0.0000 | [0.0000, 0.0000] |
| Exact T+7 Subset | Moving Average | 56,386 | 399 | 132.75 | [118.41, 148.79] | -0.2647 | [-0.2957, -0.2276] |
| Exact T+7 Subset | Seasonal Naive | 51,777 | 399 | 779.35 | [668.71, 909.28] | -6.5157 | [-7.3945, -5.6650] |
| Exact T+7 Subset | Drift | 55,824 | 399 | 104.54 | [94.48, 115.58] | +0.0008 | [-0.0247, 0.0259] |
| **Excluding 77 Disputed Keys [SUPERSEDED]*** | Naive | 64,776 | 401 | 106.96 | [96.35, 119.03] | 0.0000 | [0.0000, 0.0000] |
| Excluding 77 Disputed Keys [SUPERSEDED]* | Moving Average | 64,776 | 401 | 134.19 | [120.73, 149.35] | -0.2547 | [-0.2909, -0.2105] |
| Excluding 77 Disputed Keys [SUPERSEDED]* | Seasonal Naive | 59,200 | 401 | 774.38 | [661.02, 895.07] | -6.3738 | [-7.2432, -5.5137] |
| Excluding 77 Disputed Keys [SUPERSEDED]* | Drift | 64,036 | 401 | 107.32 | [95.82, 119.13] | -0.0068 | [-0.0303, 0.0191] |
| **Target Move > 2% Only (Diagnostic Only)** | Naive | 27,858 | 386 | 217.38 | [194.56, 243.31] | 0.0000 | [0.0000, 0.0000] |
| Target Move > 2% Only (Diagnostic Only) | Moving Average | 27,858 | 386 | 246.39 | [219.06, 278.08] | -0.1334 | [-0.1757, -0.0865] |
| Target Move > 2% Only (Diagnostic Only) | Seasonal Naive | 25,660 | 386 | 770.65 | [664.41, 899.21] | -2.6543 | [-3.0778, -2.2208] |
| Target Move > 2% Only (Diagnostic Only) | Drift | 27,451 | 386 | **202.10** | [180.30, 226.68] | **+0.0695** | [0.0432, 0.0950] |

*\*Note: The "Excluding 77 Disputed Keys" sensitivity rows above are historical artifacts from the original run where raw APMC strings were tested against canonicalized strings (matching 0 rows). In MP-AUDIT-007, fail-closed canonicalization was implemented and verified to change all 77 market keys; evaluation of the true sensitivity requires a remote Kaggle execution (RERUN REQUIRED).*

---

## 4. Key Takeaways & Synthesis

1. **Naive is a Strong Baseline:** Over the full panel of 64,776 origins, the simple Naive persistence model $y(t)$ achieves an overall MAE of 106.96 Rs/qtl, a median absolute error of 40.00 Rs/qtl, and 76.76% of predictions fall within 5% of the eventual 7-day modal price.
2. **Moving Average Lags Persistence in Stationary Periods:** The 7-observation moving average has negative skill (-0.2547 overall) because agricultural mandi daily prices have high autocorrelation and averaging introduces lag. However, in Fold F4 (post-March 2026 volatility) and for Rice, Moving Average demonstrates positive skill (+0.1577 and +0.1518, respectively).
3. **Seasonal Naive Fails at 7-Day Horizon:** Annual seasonal naive ($t+7-364$) exhibits severe error (overall MAE: 774.38 Rs/qtl; MAPE: 29.45%) due to shifting seasonal crop arrival peaks and annual inflation/deflation cycles.
4. **Drift Model Outperforms on Volatility (Retrospective Diagnostic Only):** When prices move ($> 2\%$ target price movement, $N = 27,858$ origins), the Drift model demonstrates positive skill (+0.0695, 95% CI: [0.0432, 0.0950], reducing MAE from 217.38 to 202.10 Rs/qtl). It also outperforms Naive on Onion (+0.0818 skill). Note that this $>2\%$ subset is defined retrospectively by realization and cannot select a live model at prediction time.
5. **Exact T+7 Alignment:** 87.0% of evaluated origin instances have exact $T+7$ price quotes available, where Naive MAE is 104.97 Rs/qtl.
6. **77 Disputed Keys Impact [SUPERSEDED by MP-AUDIT-007]:** The reported identical metrics in the original run were an artifact of uncanonicalized APMC market strings checked against canonical market keys (0 matches). All 77 discrepancy keys are confirmed to have APMC market strings transformed by accepted aliases. Corrected sensitivity evaluation has been prepared in the notebook; re-scoring the full panel is designated **RERUN REQUIRED**.

---

## 5. Artifact Verification & Manifest (Kaggle Remote Execution)

> [!NOTE]
> `baseline_predictions_sample.csv` (5,001 lines / 5,000 rows) contains origin evaluations from Fold F1 only ($2025-01-08$ to $2025-06-30$) and is insufficient for independent full-fold reproduction across F2, F3, and F4. The corrected notebook prepares the complete predictions archive (`baseline_predictions_all_folds.csv`).

| File Name | File Size (Bytes) | Lines | SHA-256 Digest |
| :--- | :---: | :---: | :--- |
| `mandi_5year_validated_v2.csv` | 67,455,377 | 463,218 | `851e718468d6b8c9fd07944535a462338e71aa105af25339fe9438b697088f31` |
| `processing_manifest_v2.json` | 5,136 | N/A | `c61202b741a31749bca86bd7fb4f59ea82bc6041007626a2d13a6734043d5e60` |
| `alias_transition_forensics.csv` | 3,731 | 25 | `5e45350e47013a31a1fe61f0dfee859ea1cc956409d0982f5ab52a174373895d` |
| `excel_unmatched_reclassification_v2.csv` | 2,757 | 85 | `97a54efe60748f24d6b20a2782b7baec7b8a259f256537773266f55be0d0ee18` |
| `excel_unmatched_summary_v2.json` | 1,062 | N/A | `8d95409e8f9bd8ace3881ee52f08fe644e3e193a8ead894cd2f600707fbcfda8` |
| `tier_a_reconciliation_v1_vs_v2.json` | 929 | N/A | `bb76c92f85eadc71ab220d2cbe04f6d5c02570687d91b8849797d787e05d3b0b` |
| `tier_a_series_deltas.csv` | 39,298 | 491 | `96df1275440d2f823754e8d9228f8e192aa29a41f5cb9230da20aff7e70c1248` |
| `fractional_part_distribution.csv` | 309 | 21 | `2080aebcaf3d3b30767f2123e4c11438182a66f609d0cc1877114a15cdf500fd` |
| `fractional_pricing_diagnostics.json` | 437 | N/A | `d382b38db6055efc9af7d61a9f2dbe3eb4a2c8ce546bd3956decfe54f57b9429` |
| `monthly_reporting_depth_diagnostics.csv` | 2,401 | 62 | `57835ad459f401a674230599e62c62fa6f3f0c21812d98ae62ae164ad1acbab2` |
| `baseline_predictions_sample.csv` | 954,096 | 5,001 | `c3b805a98e63fa7da14eaea14d2a9214f456c0fd367c13db9e93e61e92f9219b` |
| `scorecard_fold_x_tier.csv` | 5,086 | 41 | `ee109061f8e2e30f281ef5ce61d42529e82a365c6f3bba0645b0e047e68cbff9` |
| `scorecard_fold_x_focus_crop.csv` | 13,308 | 121 | `2b548724e6d3b2d191f7106cac7151b337a256dc9ea964456e4081ab118c7b4d` |
| `scorecard_sensitivities.csv` | 8,449 | 61 | `20678dce03e771b3ed0589e874b27547539609c310cc981aac4801f430e0a2b3` |
