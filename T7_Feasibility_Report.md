# APMC Mandi Market Intelligence System: T+7 Feasibility Report

**Project Title:** District-Level Agricultural Market Condition Classification  
**Status:** Completed and Validated  
**Decision:** **GOOD — Proceed with T+7 Prediction**

---

## Executive Summary
This document reports the comprehensive feasibility audit mandated by `T7_Feasibility_Checklist.txt` before training any predictive models.
The objective is to verify whether the 5-district APMC mandi dataset can realistically support exact 7-calendar-day forward market condition classification ($T \to T+7$) without artificial row shifting, grade collapsing, or data leakage.

The audit confirms **exceptional feasibility**:
- **74.17% exact T+7 availability** (116,819 valid pairs) across calendar dates.
- **794 series** with $\ge 20$ paired observations, and **576 series** with $\ge 50$ pairs.
- Robust distribution across **Favorable** (18.9%), **Normal** (59.4%), and **Unfavorable** (21.7%) market conditions under DEC-015 thresholds.
- Strong concurrent multi-mandi reporting (72.2% multi-mandi overlap) enabling rich neighbouring-mandi intelligence.

---

## Section-by-Section Feasibility Evaluation

### A. Basic Data Structure
All 8 required core columns are present across all 5 district datasets:
- [x] `District`
- [x] `Market`
- [x] `Commodity`
- [x] `Variety`
- [x] `Arrival_Date`
- [x] `Modal_Price`
- [x] `Min_Price`
- [x] `Max_Price`

Additional columns present in source files: `Commodity_Code`, `Grade`, `State`.

### B. Unique Time-Series Identification
A time-series is defined by the canonical 5-tuple incorporating commercial Grade:
`Series = (District, Market, Commodity, Variety, Grade)`
- **Raw records:** 160,192
- **Excluded ambiguous (Strategy 2) / invalid records:** 2,680
- **Deduplicated / Clean records:** 157,512
- **Unique canonical series (with Grade):** 2,390
- **Earliest observation:** 01 September 2024
- **Latest observation:** 01 September 2026
- **Unique calendar dates:** 731

### C. Date Continuity
Analysis of day gaps between consecutive observations within each series:
- **Consecutive daily observations (1 day gap):** 114,933 (74.09%)
- **Small gaps (2–3 days):** 28,698 (18.50%)
- **Large gaps ($>= 7$ days):** 5,570 (3.59%)

Most mandis operate 5–6 days a week with standard Sunday/holiday closures, which accounts for the predictable 2–3 day intervals.

### D. Exact T+7 Calendar Availability (Most Critical Check)
The matching strictly requires:
Target Date = Arrival_Date_T + 7 calendar days
Matching must occur on the exact same `District + Market + Commodity + Variety + Grade`. The next available row was **never** substituted as T+7.

| Metric | Count / Value |
|---|---|
| **Total Possible T Records** | 157,512 |
| **Observations with Exact T+7 Match** | 116,819 |
| **Observations without Exact T+7 Match** | 40,693 |
| **Exact T+7 Availability Percentage** | **74.17%** |

### E. Usable Series Breakdown
Initial screening thresholds:
- **Very weak (<20 pairs):** 1,596 series (excluded from model training)
- **Potentially usable (20–49 pairs):** 218 series
- **Stronger ($>= 50$ pairs):** 576 series
- **Total usable series ($>= 20$ pairs):** **794 series**

### F. T+7 Price Distribution Statistics
Evaluating the percentage change: `Delta_P_Pct = ((Price_T7 - Price_T) / Price_T) * 100`

- **Mean Price Change:** 0.50%
- **Median Price Change:** 0.00%
- **Standard Deviation:** 16.65%
- **5th Percentile:** -13.46%
- **25th Percentile:** -1.84%
- **75th Percentile:** 1.40%
- **95th Percentile:** 14.20%

### G. Classification Target Feasibility
Per Section 6 of the Project Overview and DEC-015, predicting continuous prices is replaced by classifying 3 discrete market conditions:
- **Favorable (Delta_P > +2.5%):** Price appreciation benefiting producers/sellers.
- **Normal (-2.5% <= Delta_P <= +2.5%):** Stable market conditions.
- **Unfavorable (Delta_P < -2.5%):** Price decline indicating adverse conditions.

| Class | Sample Count | Share (%) |
|---|---|---|
| **Favorable** | 22,088 | 18.91% |
| **Normal** | 69,408 | 59.41% |
| **Unfavorable** | 25,323 | 21.68% |
| **Total** | **116,819** | **100.00%** |

The distribution demonstrates ideal balance without acute class collapse.

### H. Price-Range Feasibility
- **Average T+7 Absolute Price Band Width:** Rs. 201.63
- **Average T+7 Relative Price Spread:** 7.04% of modal price
This confirms that mandis record distinct intraday Min/Max bounds, supporting the construction of volatility and dispersion features.

### I. Commodity-Wise Feasibility (Top Commodities)
| Commodity | Total Records | Varieties | Mandis | T+7 Pairs | Availability (%) |
|---|---|---|---|---|---|
| **Wheat** | 11,727.0 | 35.0 | 39.0 | 8,351.0 | 71.2% |
| **Potato** | 8,017.0 | 5.0 | 35.0 | 6,372.0 | 79.5% |
| **Onion** | 7,728.0 | 6.0 | 36.0 | 6,071.0 | 78.6% |
| **Tomato** | 7,520.0 | 5.0 | 35.0 | 5,741.0 | 76.3% |
| **Rice** | 5,908.0 | 35.0 | 36.0 | 4,135.0 | 70.0% |
| **Green Chilli** | 5,076.0 | 2.0 | 28.0 | 3,936.0 | 77.5% |
| **Brinjal** | 4,853.0 | 4.0 | 28.0 | 3,855.0 | 79.4% |
| **Bottle gourd** | 4,667.0 | 2.0 | 29.0 | 3,757.0 | 80.5% |
| **Apple** | 4,386.0 | 6.0 | 27.0 | 3,532.0 | 80.5% |
| **Ginger(Green)** | 4,291.0 | 2.0 | 27.0 | 3,364.0 | 78.4% |
| **Pumpkin** | 4,117.0 | 2.0 | 29.0 | 3,227.0 | 78.4% |
| **Gur(Jaggery)** | 3,742.0 | 6.0 | 32.0 | 2,962.0 | 79.2% |
| **Bengal Gram(Gram)(Whole)** | 3,632.0 | 6.0 | 32.0 | 2,817.0 | 77.6% |
| **Garlic** | 3,530.0 | 5.0 | 25.0 | 2,779.0 | 78.7% |
| **Mustard** | 3,187.0 | 4.0 | 32.0 | 2,305.0 | 72.3% |

### K. Mandi-Wise Feasibility (Top Mandis)
| District | Market / Mandi | Total Records | Commodities | Varieties | T+7 Pairs | Availability (%) |
|---|---|---|---|---|---|---|
| Ghaziabad | **Ghaziabad** | 14,833.0 | 45.0 | 48.0 | 12,879.0 | 86.8% |
| Lucknow | **Lucknow** | 12,232.0 | 49.0 | 48.0 | 11,198.0 | 91.5% |
| Unnao | **Unnao** | 12,647.0 | 47.0 | 47.0 | 10,306.0 | 81.5% |
| Kanpur | **Kanpur(Grain)** | 9,320.0 | 31.0 | 29.0 | 8,422.0 | 90.4% |
| Kanpur | **Choubepur** | 8,587.0 | 33.0 | 29.0 | 7,887.0 | 91.8% |
| Kanpur | **Uttaripura** | 8,180.0 | 32.0 | 32.0 | 7,450.0 | 91.1% |
| Unnao | **Bangarmau** | 7,597.0 | 26.0 | 28.0 | 6,909.0 | 90.9% |
| Ghaziabad | **Noida** | 7,695.0 | 33.0 | 40.0 | 6,280.0 | 81.6% |
| Ghaziabad | **Hapur** | 7,137.0 | 35.0 | 37.0 | 5,132.0 | 71.9% |
| Unnao | **Purwa** | 5,664.0 | 28.0 | 33.0 | 4,815.0 | 85.0% |
| Kanpur | **Varipaal** | 5,222.0 | 62.0 | 72.0 | 2,732.0 | 52.3% |
| Jhansi | **Mauranipur** | 3,948.0 | 21.0 | 19.0 | 2,591.0 | 65.6% |

### L. Neighbouring-Mandi Feasibility
- **Multi-mandi date overlap:** 72.20% of commodity-date instances have 2 or more reporting mandis on the same calendar day.
- Geographical adjacency (e.g. Kanpur, Unnao, Lucknow triangle; Ghaziabad with Noida/Hapur; Jhansi regional mandis) provides continuous cross-mandi price transmission signals.

### M. Weather Data Feasibility
Weather features are evaluated as non-viable for the primary offline dataset: the raw mandi archives do not include recorded weather variables. Per Section M of the Feasibility Checklist, synthetic weather generation is strictly prohibited. Thus, the intelligence architecture focuses cleanly on pure price-action, temporal, district-aggregated, and spatial neighbouring-mandi signals.

---

## N. Final T+7 Feasibility Table

```
======================================================================
                  T+7 FEASIBILITY AUDIT SUMMARY TABLE
======================================================================
Total raw records                               : 160,192
Duplicate records removed                       : 2,680
Total clean records                             : 157,512
Unique districts                                : 5
Unique mandis                                   : 42
Unique commodities                              : 130
Unique varieties                                : 210
Unique canonical series (with Grade)            : 2,390

Records with exact T+7                          : 116,819
Records without T+7                             : 40,693
T+7 availability %                              : 74.17%

Series with >= 20 T+7 pairs                     : 794
Series with >= 50 T+7 pairs                     : 576

Possible classification samples                 : 116,819
  - Favorable samples                           : 22,088 (18.91%)
  - Normal samples                              : 69,408 (59.41%)
  - Unfavorable samples                         : 25,323 (21.68%)
======================================================================
```

---

## O. Final Decision

### Assessment Checklist:
- [x] **High T+7 availability:** 74.17% of clean records have an exact calendar T+7 match.
- [x] **Many usable series:** 794 series have $>= 20$ pairs; 576 have $>= 50$ pairs.
- [x] **Enough samples per class:** Over 22,088 Favorable, 25,323 Unfavorable, and 69,408 Normal.
- [x] **Reasonable price variation:** Standard deviation of 16.65%, with realistic agricultural dynamics.
- [x] **Sufficient mandi overlap:** 72.20% concurrent multi-mandi observations.

### **Final Verdict:**
**GOOD: Proceed with T+7 Prediction**
The dataset strongly satisfies all prerequisites. We proceed to feature engineering, chronological train/validation/test splitting, model training, and district-level intelligence synthesis.
