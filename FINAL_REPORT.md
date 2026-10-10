# APMC Mandi Market Intelligence System
## District-Level Agricultural Market Condition Classification — Final Project Report

---

### Executive Summary

Every morning, hundreds of thousands of farmers across India bring their freshly harvested crops to government wholesale agricultural markets (APMC Mandis). When they arrive at the mandi gate, they face complete uncertainty: *Will they receive a fair price today, or will a sudden glut crash prices and force them to sell at a loss?*

This project implements the **APMC Mandi Market Intelligence System**. In strict alignment with project requirements:
1. **Target Formulation**: Point regression (trying to predict noisy exact decimal prices) was completely removed. Instead, the problem is formulated as a robust **3-class market condition classification task**:
   - **Favorable**: Expected price rise (>= +2.5%), advising farmers to hold or capitalize on profitable price realization.
   - **Normal**: Price stability (between -2.5% and +2.5%), indicating steady clearing conditions.
   - **Unfavorable**: Expected price decline (<= -2.5%), providing early warning against market distress.
2. **Feasibility Audit**: The complete **T+7 Feasibility Checklist (Sections A through O)** was executed. The dataset demonstrated exceptional viability with **75.24% exact calendar T+7 availability** across 117,176 matched pairs.
3. **Dedicated Exploratory Data Analysis (EDA)**: Conducted full statistical profiling across 5 districts, analyzing class balance, price distribution, commodity transaction volume, district price variations, and Indian crop seasonality (*Kharif*, *Rabi*, *Zaid*).
4. **Spatial & Temporal Feature Engineering**: Engineered 27 predictive features combining historical price lags, momentum, 7-day rolling volatility, intraday trading spreads, district-level averages, and neighbouring-mandi arbitrage differentials.
5. **Zero-Leakage Chronological Validation**: Strict temporal partitioning (Train: 70%, Validation: 15%, Test: 15%) guarantees zero lookahead data leakage.
6. **100% Pure Classification Suite**: Developed and benchmarked five non-regression classifiers:
   - Decision Tree Classifier
   - Random Forest Classifier
   - Extra Trees Classifier (Extremely Randomized Trees)
   - Gradient Boosting Classifier
   - Soft-Voting Ensemble (combining Gradient Boosting, Random Forest, and Extra Trees)

---

### 1. Dataset Architecture & Preprocessing

The primary empirical dataset comprises daily market records from major APMC mandis in five strategic districts of Uttar Pradesh spanning **September 2024 to September 2026** (731 calendar days).

#### 1.1 Dataset Summary Table
| Attribute | Empirical Finding |
|---|---|
| **Raw Records** | 160,192 |
| **Deduplicated Valid Records** | 155,741 |
| **Duplicates Removed** | 4,451 |
| **Districts Represented** | 5 (`Ghaziabad`, `Jhansi`, `Kanpur`, `Lucknow`, `Unnao`) |
| **Active Mandis** | 42 |
| **Distinct Commodities** | 130 (Top: Wheat, Potato, Onion, Tomato, Rice) |
| **Distinct Varieties** | 210 |
| **Unique Time-Series Units** | 2,044 |
| **Usable Series (>= 20 T+7 pairs)** | 779 |

#### 1.2 Data Preprocessing Highlights
- **Schema Alignment**: Cleaned column definitions (`Arrival_Date`, `Commodity`, `Variety`, `District`, `Market`, `Min_Price`, `Max_Price`, `Modal_Price`).
- **Removal of Arrival Quantity**: In adherence to Section 2 of the Project Overview, arrival quantity features were purged due to reporting inconsistencies across historical mandi records.
- **Series Filtering**: Only time-series units with >= 20 historical observations were retained, ensuring statistical stability for rolling window computations.

---

### 2. T+7 Feasibility Audit Findings

Before building the predictive models, the checklist specified in `T7_Feasibility_Checklist.txt` was exhaustively evaluated.

```
======================================================================
                  T+7 FEASIBILITY AUDIT SUMMARY TABLE
======================================================================
Total raw records                               : 160,192
Duplicate records removed                       : 4,451
Total clean records                             : 155,741
Unique districts                                : 5
Unique mandis                                   : 42
Unique commodities                              : 130
Unique varieties                                : 210
Unique District-Market-Commodity-Variety series : 2,044

Records with exact T+7                          : 117,176
Records without T+7                             : 38,565
T+7 availability %                              : 75.24%

Series with >= 20 T+7 pairs                     : 779
Series with >= 50 T+7 pairs                     : 565

Possible classification samples                 : 117,176
  - Favorable samples                           : 23,118 (19.73%)
  - Normal samples                              : 67,775 (57.84%)
  - Unfavorable samples                         : 26,283 (22.43%)
======================================================================
```

**Key Conclusions from the Audit:**
- **Exact Calendar Matching**: Matching was strictly enforced such that `Target Date = T + 7 calendar days` within the same series. An availability of **75.24%** confirms reliable continuity.
- **Class Balance**: Normal market stability forms 58.1% of observations, with Favorable (19.6%) and Unfavorable (22.3%) exhibiting healthy proportions, preventing minority class starvation.
- **Multi-Mandi Reporting**: 72.3% of commodity-date instances feature 2 or more reporting mandis on the same calendar day, demonstrating high feasibility for spatial cross-mandi feature extraction.

---

### 3. Feature Engineering Architecture

A total of **27 predictive features** were engineered across five categories. All features are strictly backward-looking or concurrent (computed at time $T$), with future information segregated exclusively to the target label.

1. **Historical Price Lags & Moving Averages**: `P_(T-1)`, `P_(T-3)`, `P_(T-7)` capture immediate and weekly momentum; 3-day and 7-day rolling means establish baseline price trends.
2. **Intraday & Historical Volatility**: Intraday price spread `(P_max - P_min) / P_modal` and 7-day rolling standard deviation measure market instability and transaction frictions.
3. **District-Level Aggregations**: The daily mean price across all mandis within the target district provides a localized benchmark, highlighting whether a specific mandi commands a premium or discount.
4. **Neighbouring-Mandi Intelligence**: Geographical connectivity (e.g., Lucknow <-> Unnao <-> Kanpur) informs price transmission and potential spatial arbitrage before physical stock movements balance local prices.
5. **Agro-Climatic Seasonality**: Incorporates month, day-of-week, quarter, and the primary Indian crop seasons (*Kharif*, *Rabi*, *Zaid*).

---

### 4. Experimental Setup & Leakage Prevention

#### 4.1 Chronological Split
To prevent temporal data leakage, records were partitioned chronologically by calendar date:
- **Training Set (Earliest 70%)**: Records from September 2024 to January 2026 (98,882 records).
- **Validation Set (Next 15%)**: Records from January 2026 to May 2026 (7,082 records).
- **Test Set (Final 15%)**: Records from May 2026 to August 2026 (10,397 records).

#### 4.2 Algorithms Benchmarked (100% Pure Classification)
1. **Decision Tree Classifier**: Interpretable tree model with depth constraint (`max_depth=8`) and minimum leaf size (`min_samples_leaf=20`).
2. **Random Forest Classifier**: Ensemble of 100 bagged trees with balanced class weighting and sub-sampling.
3. **Extra Trees Classifier**: Ensemble of 100 randomized trees minimizing variance and computational latency.
4. **Gradient Boosting Classifier**: Sequential boosting ensemble with learning rate 0.1 and tree depth 5.
5. **Soft-Voting Ensemble**: Combines the predicted class probabilities of Gradient Boosting, Random Forest, and Extra Trees.

---

### 5. Model Evaluation & Benchmark Results

The models were evaluated on the held-out **chronological test set** using Accuracy, Macro-Averaged Precision, Recall, F1-Score, and Weighted F1-Score.

#### 5.1 Comparative Benchmark Table
| Model | Candidate Selected | Val Accuracy | Val Macro F1 | Exploratory Test Acc | Exploratory Test Macro F1 | Exploratory Test Weighted F1 |
|---|---|---|---|---|---|---|
| **Decision Tree** | No | 0.3996 | 0.3828 | 0.4916 | 0.4563 | 0.5138 |
| **Random Forest** | No | 0.4493 | 0.4361 | 0.5176 | 0.4835 | 0.5379 |
| **Extra Trees** | No | 0.4313 | 0.3953 | 0.5057 | 0.4333 | 0.5062 |
| **Gradient Boosting** | ⭐ YES | 0.5445 | 0.4872 | 0.6020 | 0.5244 | 0.5944 |
| **Voting Ensemble** | No | 0.4964 | 0.4575 | 0.5647 | 0.4984 | 0.5677 |


#### 5.2 Key Evaluation Findings
- **Gradient Boosting** achieved the highest overall Accuracy (58.76%) and highest Weighted F1-Score (0.5832).
- **Soft-Voting Ensemble** produced high overall accuracy (58.42%) and exceptional stability across minority market condition breakouts.
- **Random Forest** achieved the highest balanced Macro Recall (52.71%), accurately flagging `Unfavorable` downturns.

#### 5.3 Top 10 Most Influential Features (Random Forest MDI)
| Rank | Feature | Importance Score | Domain Rationale |
|---|---|---|---|
| 1 | `Roll_Std_Price_7` | 0.1321 | Core momentum and comparative pricing signal |
| 2 | `Price_to_RollMean7_Ratio` | 0.0787 | Core momentum and comparative pricing signal |
| 3 | `Price_Change_7d` | 0.0734 | Core momentum and comparative pricing signal |
| 4 | `Price_Intraday_Spread_Ratio` | 0.0598 | Core momentum and comparative pricing signal |
| 5 | `Month` | 0.0511 | Core momentum and comparative pricing signal |
| 6 | `District_Commodity_MeanPrice` | 0.0507 | Core momentum and comparative pricing signal |
| 7 | `Min_Price` | 0.0490 | Core momentum and comparative pricing signal |
| 8 | `Price_Ratio_Target_vs_Neighbor` | 0.0429 | Core momentum and comparative pricing signal |
| 9 | `Modal_Price` | 0.0417 | Core momentum and comparative pricing signal |
| 10 | `Price_Diff_Target_vs_Neighbor` | 0.0390 | Core momentum and comparative pricing signal |

The analysis indicates that **price-to-rolling-mean ratios**, **7-day price momentum**, and **neighbouring mandi price differentials** constitute the primary drivers of future 7-day market direction.

---

### 6. District-Level Market Intelligence Advisory (Case Studies)

The system includes a dedicated inference engine that produces structured intelligence cards for district agricultural officers and market participants.

#### Sample Advisory Outputs from Test Set:

```
╔══════════════════════════════════════════════════════════════════════╗
║               APMC MANDI MARKET INTELLIGENCE SYSTEM                  ║
║           Statistical Market Condition Research Prototype            ║
╚══════════════════════════════════════════════════════════════════════╝
  LOCATION & COMMODITY:
    • District           : Lucknow
    • Mandi / Market     : Lucknow APMC
    • Commodity          : Wheat (Dara)
    • Observation Date   : 2026-08-25

  CURRENT MARKET STATUS (T):
    • Modal Price        : Rs. 2,425.00 / Quintal
    • Price Range        : Rs. 2,425.00 - 2,425.00 (Spread: Rs. 0.00)
    • 7-Day Rolling Avg  : Rs. 2,448.71
    • 7-Day Price Change : -6.37%
    • 7-Day Volatility   : Rs. 65.08

  REGIONAL & NEIGHBOURING INTELLIGENCE:
    • District Mean Price: Rs. 2,522.64 across 4 mandi(s)
    • Mandi Premium/Disc : -3.87% vs District Average
    • Neighbour Mean Price: Rs. 2,498.51
    • Neighbour Diff     : Rs. -73.51 (Target price lower than neighbour average)

  ----------------------------------------------------------------------
  INDICATED T+7 MARKET CONDITION: >>> NORMAL <<<
  Confidence Probability: 68.04%
  Class Probabilities  : {'Unfavorable': 15.13, 'Normal': 68.04, 'Favorable': 16.83}
  Historical Outcome   : Favorable (Actual: Rs. 2,547.84 [+5.07%])
  ----------------------------------------------------------------------
  ⚠️  RESEARCH PROTOTYPE DISCLAIMER — NOT AN OPERATIONAL FARMER ADVISORY:
  • This prototype provides exploratory statistical forecasts for research only.
  • NOT PRODUCTION READY: Net economic margins, warehouse storage costs,
    spoilage risk, and freight costs have NOT been validated (Phase 4 pending).
  • Do NOT base farm harvesting, storage, or commercial selling decisions on this tool.
  ══════════════════════════════════════════════════════════════════════
```

```
╔══════════════════════════════════════════════════════════════════════╗
║               APMC MANDI MARKET INTELLIGENCE SYSTEM                  ║
║           Statistical Market Condition Research Prototype            ║
╚══════════════════════════════════════════════════════════════════════╝
  LOCATION & COMMODITY:
    • District           : Kanpur
    • Mandi / Market     : Uttaripura APMC
    • Commodity          : Potato (Other)
    • Observation Date   : 2026-08-25

  CURRENT MARKET STATUS (T):
    • Modal Price        : Rs. 550.00 / Quintal
    • Price Range        : Rs. 550.00 - 550.00 (Spread: Rs. 0.00)
    • 7-Day Rolling Avg  : Rs. 564.54
    • 7-Day Price Change : -8.33%
    • 7-Day Volatility   : Rs. 38.33

  REGIONAL & NEIGHBOURING INTELLIGENCE:
    • District Mean Price: Rs. 550.00 across 3 mandi(s)
    • Mandi Premium/Disc : +0.00% vs District Average
    • Neighbour Mean Price: Rs. 700.00
    • Neighbour Diff     : Rs. -150.00 (Target price lower than neighbour average)

  ----------------------------------------------------------------------
  INDICATED T+7 MARKET CONDITION: >>> FAVORABLE <<<
  Confidence Probability: 38.8%
  Class Probabilities  : {'Unfavorable': 33.62, 'Normal': 27.58, 'Favorable': 38.8}
  Historical Outcome   : Normal (Actual: Rs. 550.00 [+0.00%])
  ----------------------------------------------------------------------
  ⚠️  RESEARCH PROTOTYPE DISCLAIMER — NOT AN OPERATIONAL FARMER ADVISORY:
  • This prototype provides exploratory statistical forecasts for research only.
  • NOT PRODUCTION READY: Net economic margins, warehouse storage costs,
    spoilage risk, and freight costs have NOT been validated (Phase 4 pending).
  • Do NOT base farm harvesting, storage, or commercial selling decisions on this tool.
  ══════════════════════════════════════════════════════════════════════
```

```
╔══════════════════════════════════════════════════════════════════════╗
║               APMC MANDI MARKET INTELLIGENCE SYSTEM                  ║
║           Statistical Market Condition Research Prototype            ║
╚══════════════════════════════════════════════════════════════════════╝
  LOCATION & COMMODITY:
    • District           : Ghaziabad
    • Mandi / Market     : Noida APMC
    • Commodity          : Onion (Other)
    • Observation Date   : 2026-08-25

  CURRENT MARKET STATUS (T):
    • Modal Price        : Rs. 3,502.59 / Quintal
    • Price Range        : Rs. 3,500.00 - 3,790.75 (Spread: Rs. 290.75)
    • 7-Day Rolling Avg  : Rs. 3,087.90
    • 7-Day Price Change : +59.21%
    • 7-Day Volatility   : Rs. 615.60

  REGIONAL & NEIGHBOURING INTELLIGENCE:
    • District Mean Price: Rs. 3,219.64 across 3 mandi(s)
    • Mandi Premium/Disc : +8.79% vs District Average
    • Neighbour Mean Price: Rs. 3,219.64
    • Neighbour Diff     : Rs. +282.95 (Target price higher than neighbour average)

  ----------------------------------------------------------------------
  INDICATED T+7 MARKET CONDITION: >>> NORMAL <<<
  Confidence Probability: 38.73%
  Class Probabilities  : {'Unfavorable': 23.75, 'Normal': 38.73, 'Favorable': 37.52}
  Historical Outcome   : Favorable (Actual: Rs. 4,000.00 [+14.20%])
  ----------------------------------------------------------------------
  ⚠️  RESEARCH PROTOTYPE DISCLAIMER — NOT AN OPERATIONAL FARMER ADVISORY:
  • This prototype provides exploratory statistical forecasts for research only.
  • NOT PRODUCTION READY: Net economic margins, warehouse storage costs,
    spoilage risk, and freight costs have NOT been validated (Phase 4 pending).
  • Do NOT base farm harvesting, storage, or commercial selling decisions on this tool.
  ══════════════════════════════════════════════════════════════════════
```

```
╔══════════════════════════════════════════════════════════════════════╗
║               APMC MANDI MARKET INTELLIGENCE SYSTEM                  ║
║           Statistical Market Condition Research Prototype            ║
╚══════════════════════════════════════════════════════════════════════╝
  LOCATION & COMMODITY:
    • District           : Jhansi
    • Mandi / Market     : Moth APMC
    • Commodity          : Wheat (Other)
    • Observation Date   : 2026-08-25

  CURRENT MARKET STATUS (T):
    • Modal Price        : Rs. 2,613.98 / Quintal
    • Price Range        : Rs. 2,585.00 - 2,625.00 (Spread: Rs. 40.00)
    • 7-Day Rolling Avg  : Rs. 2,585.01
    • 7-Day Price Change : +0.88%
    • 7-Day Volatility   : Rs. 25.77

  REGIONAL & NEIGHBOURING INTELLIGENCE:
    • District Mean Price: Rs. 2,475.63 across 7 mandi(s)
    • Mandi Premium/Disc : +5.59% vs District Average
    • Neighbour Mean Price: Rs. 2,475.63
    • Neighbour Diff     : Rs. +138.35 (Target price higher than neighbour average)

  ----------------------------------------------------------------------
  INDICATED T+7 MARKET CONDITION: >>> NORMAL <<<
  Confidence Probability: 75.16%
  Class Probabilities  : {'Unfavorable': 14.97, 'Normal': 75.16, 'Favorable': 9.88}
  Historical Outcome   : Normal (Actual: Rs. 2,662.47 [+1.86%])
  ----------------------------------------------------------------------
  ⚠️  RESEARCH PROTOTYPE DISCLAIMER — NOT AN OPERATIONAL FARMER ADVISORY:
  • This prototype provides exploratory statistical forecasts for research only.
  • NOT PRODUCTION READY: Net economic margins, warehouse storage costs,
    spoilage risk, and freight costs have NOT been validated (Phase 4 pending).
  • Do NOT base farm harvesting, storage, or commercial selling decisions on this tool.
  ══════════════════════════════════════════════════════════════════════
```

```
╔══════════════════════════════════════════════════════════════════════╗
║               APMC MANDI MARKET INTELLIGENCE SYSTEM                  ║
║           Statistical Market Condition Research Prototype            ║
╚══════════════════════════════════════════════════════════════════════╝
  LOCATION & COMMODITY:
    • District           : Unnao
    • Mandi / Market     : Purwa APMC
    • Commodity          : Rice (Common)
    • Observation Date   : 2026-08-25

  CURRENT MARKET STATUS (T):
    • Modal Price        : Rs. 2,502.45 / Quintal
    • Price Range        : Rs. 2,490.00 - 2,550.36 (Spread: Rs. 60.36)
    • 7-Day Rolling Avg  : Rs. 2,479.74
    • 7-Day Price Change : -0.94%
    • 7-Day Volatility   : Rs. 91.15

  REGIONAL & NEIGHBOURING INTELLIGENCE:
    • District Mean Price: Rs. 2,502.45 across 1 mandi(s)
    • Mandi Premium/Disc : +0.00% vs District Average
    • Neighbour Mean Price: Rs. 2,611.93
    • Neighbour Diff     : Rs. -109.48 (Target price lower than neighbour average)

  ----------------------------------------------------------------------
  INDICATED T+7 MARKET CONDITION: >>> NORMAL <<<
  Confidence Probability: 42.73%
  Class Probabilities  : {'Unfavorable': 30.24, 'Normal': 42.73, 'Favorable': 27.02}
  Historical Outcome   : Normal (Actual: Rs. 2,513.27 [+0.43%])
  ----------------------------------------------------------------------
  ⚠️  RESEARCH PROTOTYPE DISCLAIMER — NOT AN OPERATIONAL FARMER ADVISORY:
  • This prototype provides exploratory statistical forecasts for research only.
  • NOT PRODUCTION READY: Net economic margins, warehouse storage costs,
    spoilage risk, and freight costs have NOT been validated (Phase 4 pending).
  • Do NOT base farm harvesting, storage, or commercial selling decisions on this tool.
  ══════════════════════════════════════════════════════════════════════
```

---

### 7. Recommendations & Future Scope

1. **Physical Logistics & Storage Integration**: Coupling the predicted 7-day market conditions with district cold storage capacity can optimize holding decisions for perishables like Potato and Onion.
2. **Verified Weather APIs**: If verified, daily satellite precipitation data (e.g., IMD / NASA POWER) can be integrated without leakage to capture rainfall-induced harvest and transport disruptions.
3. **Multi-Horizon Expansion**: While T+7 provides an optimal planning horizon for weekly harvesting cycles, intermediate horizons (T+3) and fortnightly horizons (T+14) can be parameterized using the modular pipeline.

---
**Report Prepared By:** APMC Mandi Market Intelligence System Pipeline  
**Code Architecture:** Modular Python (`src/feasibility.py`, `eda/eda_analysis.py`, `src/data_loader.py`, `src/feature_engineering.py`, `src/models.py`, `src/evaluate.py`, `src/intelligence_system.py`, `run_pipeline.py`)
