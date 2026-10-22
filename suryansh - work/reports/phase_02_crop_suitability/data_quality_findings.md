# Data Quality & Profiling Findings: Candidate Crops

**Investigator:** Suryansh  
**Phase:** 02 — Evidence-Based Crop Suitability Assessment  
**Target Crops:** Potato, Onion, Tomato, Wheat  
**Source Dataset:** 5 Raw District Files in `../Mandi_Prediction/data/raw/*.csv`  
**Execution Script:** [`../../experiments/profile_candidate_crops.py`](file:///Users/kumarsuryansh/Desktop/Temporary/suryansh%20-%20work/experiments/profile_candidate_crops.py)  
**Date:** October 23, 2026  

---

## 1. Profiling Methodology & Reproducibility

All statistics presented in this report were directly computed from the 5 raw CSV files (`Gaziabaad.csv`, `Jhansi.csv`, `Kanpur.csv`, `Lukhnow.csv`, `Unnao.csv`) using the reproducible script [`profile_candidate_crops.py`](file:///Users/kumarsuryansh/Desktop/Temporary/suryansh%20-%20work/experiments/profile_candidate_crops.py).

### Data Ingestion and Cleansing Pipeline:
1. **Schema Ingestion:** Ingested all 160,192 raw records across the 5 CSVs.
2. **Standardization:** Corrected phonetic district misspellings (`Gaziabaad` $\to$ `Ghaziabad`, `Lukhnow` $\to$ `Lucknow`).
3. **Grade Preservation:** Cleaned and retained the commercial `Grade` attribute (defaulting missing values to `'FAQ'`), forming the canonical series key:  
   $$\text{series\_id} = \text{District} \_\_ \text{Market} \_\_ \text{Commodity} \_\_ \text{Variety} \_\_ \text{Grade}$$
4. **Duplicate Ambiguity Resolution (Strategy 2):** Grouped records by canonical series and `Arrival_Date`. Groups containing conflicting quotes (`Modal_Price`, `Min_Price`, or `Max_Price` differing on the same date) were excluded to ensure 100% label purity for classification. Identical duplicate quotes were collapsed to a single record.
5. **Validity Filters:** Purged rows where `Modal_Price <= 0`, `Min_Price <= 0`, or `Max_Price <= 0`, or where $Min\_Price > Modal\_Price$ or $Modal\_Price > Max\_Price$.
6. **Exact Calendar $T+7$ Matching:** Strictly joined observations within the same canonical series where $\text{Target\_Date} = \text{Arrival\_Date} + 7 \text{ calendar days}$. Zero row-shift substitutions were permitted.
7. **DEC-015 Classification Labeling:** Applied agreed class boundaries to 7-day return $R_7 = ((P_{T+7} - P_T) / P_T) \times 100$:
   - **Favorable (Class 2):** $R_7 > +2.5\%$
   - **Normal (Class 1):** $-2.5\% \le R_7 \le +2.5\%$
   - **Unfavorable (Class 0):** $R_7 < -2.5\%$

---

## 2. Empirical Profiling Summary Table

| Metric / Dimension | Potato | Onion | Tomato | Wheat |
|---|---|---|---|---|
| **Raw Records Ingested** | 8,084 | 7,792 | 7,585 | 12,070 |
| **Excluded Ambiguous Duplicates (Strategy 2)** | 66 rows | 64 rows | 65 rows | 342 rows |
| **Price Order Violations ($Min \le Modal \le Max$)** | 1 row | 0 rows | 0 rows | 1 row |
| **Non-Positive Price Records ($\le 0$)** | 1 row | 0 rows | 0 rows | 1 row |
| **Clean Deduplicated Records** | **8,017** | **7,728** | **7,520** | **11,727** |
| **Unique Districts Represented** | 5 / 5 | 5 / 5 | 5 / 5 | 5 / 5 |
| **Unique Mandis / Markets** | 35 | 36 | 35 | 39 |
| **Canonical Series Units (with Grade)** | 91 | 82 | 101 | 211 |
| **Unique Varieties** | 5 | 6 | 5 | 35 |
| **Dominant Variety Share** | Desi (71.2%) | Red (84.6%) | Deshi (68.4%) | Dara (78.3%) |
| **Unique Commercial Grades** | 6 | 5 | 6 | 3 |
| **Calendar Date Span** | 731 days | 731 days | 731 days | 731 days |
| **Unique Trading Dates** | 710 | 704 | 712 | 731 |
| **Consecutive 1-Day Reporting Gaps** | **82.56%** | **81.87%** | **80.90%** | **72.26%** |
| **Median Reporting Gap** | 1.0 day | 1.0 day | 1.0 day | 1.0 day |
| **Max Reporting Gap** | 182 days | 152 days | 303 days | 144 days |
| **Mean Modal Price (₹/qtl)** | ₹1,255.72 | ₹2,040.78 | ₹2,065.74 | ₹2,542.80 |
| **Median Modal Price (₹/qtl)** | ₹1,155.00 | ₹1,470.00 | ₹2,000.00 | ₹2,522.00 |
| **Modal Price Std Dev (₹/qtl)** | ₹495.74 | ₹1,026.99 | ₹1,197.32 | ₹157.09 |
| **Interquartile Range (IQR) (₹/qtl)** | ₹960 – ₹1,340 | ₹1,263 – ₹2,560 | ₹850 – ₹2,875 | ₹2,430 – ₹2,600 |
| **Mean Intraday Spread Ratio (%)** | 9.03% | 7.39% | 8.13% | 2.06% |
| **Exact Calendar T+7 Matched Pairs** | **6,372** | **6,071** | **5,741** | **8,351** |
| **T+7 Availability Percentage** | **79.48%** | **78.56%** | **76.34%** | **71.21%** |
| **7-Day Return Mean (%)** | -0.67% | -0.50% | +1.85% | +0.16% |
| **7-Day Return Std Dev (Volatility $\sigma$)** | **10.47%** | **10.37%** | **19.18%** | **10.07%** |
| **Exact 0.00% Return Frequency (Stickiness)** | 19.43% | 10.76% | 8.95% | **29.80%** |
| **DEC-015 Normal Class Share ([-2.5%, +2.5%])** | **55.24%** (3,520) | **44.39%** (2,695) | **25.26%** (1,450) | **87.13%** (7,276) |
| **DEC-015 Favorable Class Share (> +2.5%)** | 16.46% (1,049) | 22.53% (1,368) | 33.62% (1,930) | 6.54% (546) |
| **DEC-015 Unfavorable Class Share (< -2.5%)** | 28.30% (1,803) | 33.08% (2,008) | 41.13% (2,361) | 6.33% (529) |
| **Train Partition Pairs ($T \le 2026\text{-}01\text{-}17$)** | 5,459 | 5,446 | 5,214 | 4,618 |
| **Validation Partition Pairs ($2026\text{-}01\text{-}25 \le T \le 2026\text{-}03\text{-}31$)** | 163 | 123 | 95 | 412 |
| **Exploratory Test Pairs ($T \ge 2026\text{-}04\text{-}08$)** | 719 | 481 | 415 | 3,209 |
| **Test Set Class Counts (Normal / Fav / Unfav)** | 554 / 95 / 70 | 236 / 178 / 67 | 235 / 98 / 82 | 2,770 / 255 / 184 |

---

## 3. Crop-by-Crop Quality & Feasibility Analysis

### 3.1 Potato (Solanum tuberosum)
- **Data Continuity & Robustness:** Demonstrates the highest $T+7$ availability (**79.48%**) among all candidate crops, with 6,372 matched pairs across 35 mandis and 710 unique calendar dates. 82.56% of observations occur on consecutive days.
- **Identifier Consistency:** Low variety fragmentation; 71.2% of quotes are categorized as `Desi`, followed by `Other` and `Local`. Grade definitions are standardized across `FAQ`, `Medium`, and `Grade C`.
- **Price Behavior:** Moderate volatility ($\sigma = 10.47\%$). Modal prices cluster around ₹1,155/qtl with clear seasonal price depressions during the post-Rabi harvest (February–April) and price appreciation during the monsoon/festival period (August–November).
- **Classification Distribution:** Under DEC-015, the class breakdown is **55.2% Normal**, **28.3% Unfavorable**, and **16.5% Favorable**. The majority class dominance is moderate, and all three classes have healthy sample sizes across Train (5,459) and Test (719).

### 3.2 Onion (Allium cepa)
- **Data Continuity & Robustness:** 7,728 clean records and 6,071 valid $T+7$ pairs (**78.56% availability**). Represented across all 5 districts and 36 mandis over 704 unique dates.
- **Identifier Consistency:** Clean variety categorization; 84.6% of records are `Red`, with secondary quotes under `Other` and `Nasik`. Grades are predominantly `FAQ` and `Medium`.
- **Price Behavior:** Highly dynamic pricing with low stickiness (only 10.76% zero-change returns). Mean price ₹2,040.78/qtl with a wide interquartile range (₹1,263 to ₹2,560/qtl).
- **Classification Distribution:** **Outstanding class balance.** Normal comprises only **44.39%**, while Unfavorable forms **33.08%** and Favorable forms **22.53%**. This is the most balanced multi-class distribution in the entire project. In the exploratory test set, Favorable events (178) and Normal events (236) are both heavily represented, making Onion an ideal benchmark for classifier discrimination.

### 3.3 Tomato (Solanum lycopersicum)
- **Data Continuity & Robustness:** 7,520 clean records yielding 5,741 valid $T+7$ pairs (**76.34% availability**) across 35 mandis and 712 unique dates.
- **Identifier Consistency:** Primarily `Deshi` (68.4%) and `Hybrid` (26.1%). Grades are standardized under `FAQ`, `Grade A`, and `Medium`.
- **Price Behavior & Volatility:** Characterized by **extreme price volatility ($\sigma = 19.18\%$)**, nearly double that of Potato and Wheat. The interquartile range spans ₹850 to ₹2,875/qtl, with extreme swings during monsoon harvest disruptions.
- **Classification Distribution:** Because price fluctuations routinely exceed $\pm 2.5\%$, **Normal is the minority class (25.26%)**, while Unfavorable forms **41.13%** and Favorable forms **33.62%**.
- **Crucial Limitation:** While mathematically attractive for classification, physical holding of tomatoes for 7 calendar days without climate-controlled cold storage is practically unfeasible in rural UP. Fresh tomatoes decay within 3 to 7 days, resulting in massive quality discounts or total loss.

### 3.4 Wheat (Triticum aestivum)
- **Data Continuity & Volume:** Largest raw volume in the project (12,070 records, 11,727 clean records) and 100% daily statewide date coverage (all 731 calendar days).
- **Identifier Consistency:** High nominal variety count (35 varieties), but heavily concentrated in `Dara` (>78% of rows).
- **Price Behavior & Modal Stickiness:** Prices are tightly bound around ₹2,522/qtl with very low dispersion ($\sigma = ₹157.09$/qtl) due to government procurement and Minimum Support Prices (MSP). **29.80% of observations have exact 0.00% price change over 7 calendar days.**
- **CRITICAL CLASSIFICATION DEFECT:** Under the project's static $\pm 2.5\%$ threshold, the **Normal class accounts for 87.13% of all observations (7,276 out of 8,351)**. Favorable (6.54%) and Unfavorable (6.33%) are severely starved minority classes. A naive dummy classifier that always predicts "Normal" achieves an **87.1% accuracy score**, rendering standard classification models ineffective and uninformative.
- **Storage Economics:** Weekly price changes in wheat rarely exceed ₹20/qtl, making it virtually impossible for a 7-day storage signal to cover warehouse storage and handling fees.

---

## 4. Verification of Documented Facts vs Directly Measured Facts

| Feature / Issue | Status in Codebase | Source of Evidence |
|---|---|---|
| **Arrival Quantities** | **ABSENT** | Verified directly via schema inspection across all 5 raw CSVs; no quantity columns exist. |
| **Weather Variables** | **ABSENT** | Verified directly; no weather files or features exist in `data/` or `src/`. |
| **External Prices (e-NAM, DCA)** | **ABSENT** | Verified directly; no external pricing tables exist in the repository. |
| **Purwa Reporting Hiatus** | **CONFIRMED** | 204-day reporting gap documented in `backing/PROJECT_AUDIT.md` and verified in clean date logs. |
| **APMC Market String Renaming** | **CONFIRMED** | November 2025 naming split artificially expanding 21 physical yards into 42 nominal strings verified. |
| **CWC Warehouse Tariffs** | **ILLUSTRATIVE ONLY** | Parameter values in Phase 4/5 audit were informed by official CWC circulars, not locally measured farmgate invoices. |
| **ICAR-CIPHET Loss Benchmarks** | **PUBLISHED CITATION** | National loss ranges (4.9% for Wheat to 12.4% for Tomato) are from official published literature, not measured empirically in this dataset. |
