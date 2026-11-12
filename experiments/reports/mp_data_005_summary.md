# MP-DATA-005: Feb–Mar 2026 Price Discrepancy Analysis, Panel Anomaly Scan, and Train-Only Eligibility Report

**Task ID:** `MP-DATA-005`  
**Execution Environment:** Kaggle CPU Kernel (`theankitchoubey/mp-data-005-quality`, internet disabled)  
**Evaluated Dataset:** `theankitchoubey/mandi-prediction-audit-003b` (v1 private, unchanged)  
**Execution Date:** 2026-11-12  
**Kernel Execution Time:** 32.2 seconds  
**Kernel Status:** Complete (`KernelWorkerStatus.COMPLETE`, exit code 0)  

---

## 1. Executive Summary & Plain-Language Determination

### Question: Is the Feb–Mar 2026 Price Discrepancy a Unit/Format Problem, Late Revisions, Real Price Moves, or Unresolved?

**Determination:**  
The Feb–Mar 2026 price discrepancy is **(d) an unresolved data-entry / upstream revision anomaly**, with decisive evidence of **(b) post-aggregation late revisions and format shifts**, and is **definitively NOT (a) a unit conversion error**.

### Supporting Empirical Proof:
1. **No Unit Conversion Factor:** Testing candidate constant scaling factors ($0.001, 0.01, 0.1, 0.5, 2.0, 10.0, 100.0, 1000.0$) against all 77 discrepant rows yielded **exactly 0 matches** (0.00% within 1% tolerance). Both datasets explicitly record prices in **₹/Quintal**. Ratios span $[0.2632, 2.5492]$ with a median of $1.0128$ and mean of $1.1386$.
2. **Format Shift to Fractional Prices:** In historical data prior to 2026, fractional non-integer prices occurred in $<0.01\%$ of rows. In March 2026, **40.13% of all panel observations (1,649 / 4,109 rows)** suddenly recorded fractional decimal prices. 100% of the 77 Excel differences (77/77) contain non-zero decimal fractions.
3. **Market Naming Fork (`APMC` Suffix):** In late 2025/2026, raw Agmarknet feeds appended ` APMC` to market names (e.g., `Ghaziabad APMC` vs historical `Ghaziabad`). Because the pipeline's natural key incorporates `Market`, this naming shift forked historical time series into disjoint identities.
4. **Temporal Concentration:** The 77 differences are tightly clustered in late February and late March 2026 (peaking at a 26.55% discrepancy rate in the week of 2026-02-23 and 6.61% in the week of 2026-03-23), while surrounding periods exhibit $\ge 97\%$ exact agreement.

---

## 2. Part 1 — Deep Dive Analysis of the 77 Price Differences

A complete natural-key inner merge was performed between the 5 official Agmarknet Excel files (`raw_downloads/*.xlsx`, 2,525 rows) and the validated panel (`data/processed/mandi_5year_validated.csv`, 462,350 rows) on `[District, Market, Commodity, Variety, Grade, Arrival_Date]`.

- **Total Matched Records:** 1,939 rows.
- **Exact Modal Price Matches ($0.00 difference):** 1,862 rows (96.03%).
- **Non-Zero Price Differences:** Exactly **77 rows** (3.97%).

### Ratio Distribution ($\text{Modal}_{\text{Excel}} / \text{Modal}_{\text{Panel}}$)
| Statistic | Value |
| :--- | :--- |
| **Count** | 77 |
| **Minimum Ratio** | 0.2632 |
| **10th Percentile (P10)** | 0.9284 |
| **25th Percentile (P25)** | 0.9839 |
| **Median Ratio** | 1.0128 |
| **75th Percentile (P75)** | 1.1454 |
| **90th Percentile (P90)** | 1.5627 |
| **Maximum Ratio** | 2.5492 |
| **Mean Ratio** | 1.1386 |

### Constant Factor Candidate Test (within 1% tolerance)
| Factor | Expected Bug | Matches Found | Match Rate |
| :--- | :--- | :--- | :--- |
| **0.001** | ₹/kg to ₹/tonne scaling error | 0 | 0.00% |
| **0.01** | Paise to Rupee / percentage scaling | 0 | 0.00% |
| **0.1** | Decimal shift / 10x error | 0 | 0.00% |
| **0.5** | Half-price / 50 kg bag factor | 0 | 0.00% |
| **2.0** | Double-price / 200 kg factor | 0 | 0.00% |
| **10.0** | 10x multiplier | 0 | 0.00% |
| **100.0** | ₹/Quintal to ₹/kg inversion | 0 | 0.00% |
| **1000.0** | ₹/tonne to ₹/kg inversion | 0 | 0.00% |

### Decimals and Units
- **Excel Quotes with Non-Zero Decimals:** 77 of 77 (100.0%).
- **Panel Quotes with Non-Zero Decimals:** 45 of 77 (58.44%).
- **Excel Price Units:** 100% recorded as `Rs/Quintal` (or `Rs./Quintal`).
- **Excel Arrival Units:** 100% recorded as `Tonnes`.

---

## 3. Part 2 — Cluster Scope Analysis (2026-02-15 to 2026-04-07)

During the 7-week window enclosing the discrepancy:
- **Total Excel Records:** 2,098
- **Records Matched in Panel:** 1,579 (75.26% match rate)
- **Exact Modal Price Matches:** 1,502 (95.12% exact match rate among matched records)
- **Discrepant Records:** 77 (4.88%)

### Weekly Progression
| Week Starting | Excel Rows | Matched Rows | Exact Matches | Discrepancies | Match % | Exact % |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **2026-02-16** | 5 | 1 | 1 | 0 | 20.00% | 100.00% |
| **2026-02-23** | 161 | 113 | 83 | 30 | 70.19% | 73.45% |
| **2026-03-02** | 338 | 272 | 264 | 8 | 80.47% | 97.06% |
| **2026-03-09** | 358 | 288 | 282 | 6 | 80.45% | 97.92% |
| **2026-03-16** | 417 | 321 | 315 | 6 | 76.98% | 98.13% |
| **2026-03-23** | 465 | 348 | 325 | 23 | 74.84% | 93.39% |
| **2026-03-30** | 342 | 228 | 224 | 4 | 66.67% | 98.25% |
| **2026-04-06** | 12 | 8 | 8 | 0 | 66.67% | 100.00% |

The discrepancy is isolated to two discrete reporting waves: late February (week of 2026-02-23) and late March (week of 2026-03-23).

---

## 4. Part 3 — Panel-Wide Anomaly Scan (462,350 Rows)

A scan across all 462,350 validated rows evaluated four non-destructive diagnostic flags:
1. `flag_price_jump`: Day-over-day price ratio outside $[0.5, 2.0]$.
2. `flag_non_integer`: Fractional decimal prices ($\text{price} \pmod 1 \neq 0$).
3. `flag_median_3x`: Price $> 3\times$ or $< \frac{1}{3}\times$ the series full-panel median.
4. `flag_min_max_inconsistency`: $\text{Min} > \text{Max}$ or $\text{Modal} \notin [\text{Min}, \text{Max}]$.

### Panel Summary
| Diagnostic Flag | Row Count | Flagged Rate |
| :--- | :--- | :--- |
| **Day-over-day price jump ($<0.5$ or $>2.0$)** | 1,677 | 0.36% |
| **Fractional (non-integer) price** | 13,061 | 2.82% |
| **Outside $3\times$ series median** | 1,468 | 0.32% |
| **Min/Max internal inconsistency** | **0** | **0.00%** |
| **Any anomaly flag** | **14,845** | **3.21%** |

### Historical vs. 2026 Anomaly Spike
| Time Period | Total Obs | Price Jumps | Non-Integer Obs | Any Anomaly Obs | Anomaly Rate |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **2021-09 to 2025-10** (Historical) | 437,330 | 1,472 | 1 | 3,365 | 0.77% |
| **2025-11** | 3,083 | 7 | 0 | 7 | 0.23% |
| **2025-12** | 2,873 | 8 | 1 | 8 | 0.28% |
| **2026-01** | 1,459 | 0 | 0 | 0 | 0.00% |
| **2026-02** | 858 | 2 | 144 | 147 | 17.13% |
| **2026-03** | **4,109** | **49** | **1,649** | **1,686** | **41.03%** |
| **2026-04** | 4,674 | 117 | 1,812 | 1,874 | 40.09% |
| **2026-05** | 4,819 | 130 | 1,947 | 2,018 | 41.88% |
| **2026-06** | 4,821 | 218 | 2,068 | 2,173 | 45.07% |
| **2026-07** | 4,426 | 170 | 1,903 | 1,987 | 44.89% |
| **2026-08** | 4,210 | 161 | 1,716 | 1,791 | 42.54% |
| **2026-09** | 4,432 | 199 | 1,820 | 1,916 | 43.23% |

From March 2026 onwards, the anomaly rate jumps from $<0.3\%$ to $>40\%$, driven almost entirely by the sudden introduction of fractional decimal prices (which also characterized the 77 discrepancy rows).

---

## 5. Part 4 — Train-Only Eligibility ($T \le 2025-12-18$)

Series eligibility was evaluated strictly within the training window ending `2025-12-18` (1,570 calendar days, 439,077 total observations):
- **Tier A Criterion:** $N_{\text{obs, train}} \ge 60$ and $\text{Coverage}_{\text{train}} \ge 0.30$.
- **Tier B Criterion:** $N_{\text{obs, train}} \ge 120$ and $\text{Coverage}_{\text{train}} \ge 0.30$.

### Eligibility Totals
| Eligibility Scope | Series Count | Unique Markets | Total Training Obs |
| :--- | :--- | :--- | :--- |
| **As-Is Series ID (Tier A)** | 496 | 20 | 384,887 |
| **As-Is Series ID (Tier B)** | 473 | 20 | 383,037 |
| **Canonical Series ID (Tier A)** | 495 | 20 | 385,821 |
| **Canonical Series ID (Tier B)** | 472 | 20 | 383,971 |

### Focus Crops Breakdown (As-Is Series ID)
| Commodity | Unique Markets | Total Series | Tier A Series | Tier B Series | Tier A Obs |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Wheat** | 16 | 45 | 34 | 33 | 31,349 |
| **Potato** | 15 | 33 | 25 | 25 | 26,081 |
| **Onion** | 13 | 24 | 19 | 19 | 18,916 |
| **Tomato** | 12 | 23 | 18 | 18 | 18,245 |
| **Rice** | 12 | 22 | 16 | 16 | 14,024 |
| **Paddy(Dhan)(Common)** | 11 | 14 | 12 | 12 | 9,842 |

---

## 6. Parts 5 & 6 — Serving-Time Rule & Series-Level Forward Availability

### The APMC Market Naming Discontinuity
In late 2025, Agmarknet raw data collection appended ` APMC` to market names (e.g., `Ghaziabad` became `Ghaziabad APMC`).
- Under the current pipeline natural key (`series_cols = ["District", "Market", "Commodity", "Variety", "Grade"]`), this created a disjoint series for every market.
- In training ($T \le 2025-12-18$), APMC-suffixed series only had up to 43 observations (mean 22.5), failing Tier A/B eligibility.
- In 2026, **100% of observations** carried the ` APMC` suffix.
- As a consequence, under as-is `series_id`, Tier A series have **0 observations in 2026**.
- Under canonical market normalization (`Market_Canonical = Market.replace(r'\s+APMC$', '')`), historical and 2026 observations unify seamlessly.

### Serving-Time Rule Feasibility
| Metric | As-Is `series_id` | Canonical `series_id_canonical` |
| :--- | :--- | :--- |
| **Tier A Recency $\le 14$ days at cutoff (2025-12-18)** | 0.00% (min recency 43d) | 19.80% (98 series) |
| **Tier A Recency $\le 30$ days at cutoff (2025-12-18)** | 0.00% (median recency 45d) | 20.81% (103 series) |
| **Tier A Test Origins Evaluated ($T \ge 2025-12-26$)** | 0 | 4,418 |
| **Tier A Test Origins Passing 14-Day Recency** | 0.00% | **99.00% (4,374 / 4,418)** |
| **Tier B Test Origins Passing 14-Day Recency** | 0.00% | **99.00% (4,374 / 4,418)** |

When market names are canonically unified, **99.00% of test origins satisfy the serving-time availability constraint** ($[T-14, T)$ has an observation).

### Unweighted Series-Level Forward Availability (Canonical Tier A, 495 Series)
| Target Availability | Min | P10 | P25 | Median | P75 | P90 | Max | Mean |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **$T+7$ Exact Match** | 0.4158 | 0.6763 | 0.7591 | **0.8675** | 0.9196 | 0.9439 | 0.9689 | **0.8319** |
| **$T+6..T+8$ Window** | 0.6562 | 0.8658 | 0.9226 | **0.9602** | 0.9808 | 0.9896 | 0.9973 | **0.9421** |

For canonical Tier A series, the median series has an exact $T+7$ observation on **86.75% of origins**, and a near-horizon observation ($T \in [6, 8]$) on **96.02% of origins**.

---

## 7. Part 7 — Rolling-Origin Cross-Validation Feasibility (4 Folds)

Four expanding 60-day evaluation folds ending `2026-09-30` were evaluated with a strict 7-date embargo ($h=7$):
- **Fold 1:** Test `2026-02-03 to 2026-04-03` | Embargo `2026-01-27 to 2026-02-02` | Train `2021-09-01 to 2026-01-26`.  
  *Test window overlaps the Feb–Mar 2026 discrepancy.*
- **Fold 2:** Test `2026-04-04 to 2026-06-02` | Embargo `2026-03-28 to 2026-04-03` | Train `2021-09-01 to 2026-03-27`.  
  *Train window overlaps the Feb–Mar 2026 discrepancy.*
- **Fold 3:** Test `2026-06-03 to 2026-08-01` | Embargo `2026-05-27 to 2026-06-02` | Train `2021-09-01 to 2026-05-26`.  
  *Train window overlaps the Feb–Mar 2026 discrepancy.*
- **Fold 4:** Test `2026-08-02 to 2026-09-30` | Embargo `2026-07-26 to 2026-08-01` | Train `2021-09-01 to 2026-07-25`.  
  *Train window overlaps the Feb–Mar 2026 discrepancy.*

### Fold Feasibility Summary
| Fold | Test Window | As-Is Tier A $\ge 20$ Origins | Canon Tier A $\ge 20$ Origins | Canon Tier A % | Canon Tier B $\ge 20$ Origins | Canon Tier B % |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | `2026-02-03 to 2026-04-03` | 0 (0.0%) | 22 | 4.44% | 22 | 4.66% |
| **2** | `2026-04-04 to 2026-06-02` | 0 (0.0%) | 18 | 3.64% | 18 | 3.81% |
| **3** | `2026-06-03 to 2026-08-01` | 0 (0.0%) | 16 | 3.23% | 16 | 3.39% |
| **4** | `2026-08-02 to 2026-09-30` | 0 (0.0%) | 15 | 3.03% | 15 | 3.18% |

---

## 8. Generated Output Artifacts & Checksums

| Artifact File | Size (Bytes) | Lines | SHA-256 Digest |
| :--- | :--- | :--- | :--- |
| `diff_77_deep_analysis.csv` | 10,087 | 78 | `93341b3c3b4b4f7571b67b467025f86a53cc439cf198a6bd36ee18097975b5c1` |
| `diff_77_deep_analysis.json` | 38,364 | N/A | `e323a5bb6d9ad19f530b258557204dca808a8145172a638e95346360c771a3b4` |
| `feb_mar_cluster_weekly.csv` | 402 | 10 | `9d983e9d1d6b593a4d11d89673ee8bed2f738b3985c818a9a6d63d0e11e56686` |
| `feb_mar_cluster_summary.json` | 3,159 | N/A | `fd771157403c5e20989951619947a20464d210edb4f738a2694baff4296557b9` |
| `monthly_anomaly_distribution.csv` | 1,977 | 62 | `660e793534e3ae0d476a88e0e930896c7b0989d6b9fc4f0e190511d49e025899` |
| `panel_anomalies_sample.csv` | 277,485 | 2,001 | `b60f28d2b482b0f31c3ebaf5cffc623285df4199e0915581e80b3e9cab7c9a85` |
| `anomaly_scan_summary.json` | 704 | N/A | `053841504142492f1093686701ea666cc3686a5e0243b20c14782ace324cafb3` |
| `train_eligibility_tiers.csv` | 135,881 | 922 | `c407311b210c29c8cd71d8d3740f0b9b78ca0cd9965e2e98cce0c2d52cfe753a` |
| `focus_crops_train_eligibility.csv` | 6,367 | 161 | `2df773a912ea3e9ed2738260430fda34fd7210b9c880248131b98f8dc4a9e7a3` |
| `serving_rule_feasibility.json` | 1,023 | N/A | `b9f149c5de57be5023240f3a504f17d7b43d0af3df350bc401888ae25e839b35` |
| `series_level_availability_summary.json` | 999 | N/A | `c1484fe3da9377448261e081829219c84fd4591fbca0ed68a0bd70d809dc6829` |
| `rolling_origin_feasibility.json` | 2,619 | N/A | `dddab43dbb193adc2c9fa668964376e1800520e3a2b07007d132f251ac2358fc` |
| `kernel_execution_manifest.json` | 1,777 | N/A | Generated dynamically at runtime |
