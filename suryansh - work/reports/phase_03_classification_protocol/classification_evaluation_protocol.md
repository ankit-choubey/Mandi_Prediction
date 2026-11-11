# Classification Evaluation Protocol & Baseline Audit Report

**Project:** Mandi Prediction — Agricultural Market Condition Classification  
**Researcher:** Suryansh  
**Phase:** 03 — Classification Evaluation Protocol and Baseline Audit  
**Approved Crop Scope:**  
- **Potato:** Main study.  
- **Onion:** Main study.  
- **Tomato:** Exploratory price-movement classification only (strictly decoupled from storage advisory).  
- **Wheat:** Main study, with special attention to majority-class concentration.  
**Reference Codebase:** [`/Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction`](file:///Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction) (Strictly read-only on `main`)  
**Separate Workspace:** [`/Users/kumarsuryansh/Desktop/Temporary/suryansh - work`](file:///Users/kumarsuryansh/Desktop/Temporary/suryansh%20-%20work)  
**Date:** October 23, 2026  

---

## 1. Purpose and Scope

This protocol establishes the formal mathematical, statistical, and operational evaluation standards for multi-class agricultural market condition prediction across APMC wholesale mandis in Uttar Pradesh. 

It defines the metric suite, auditing standards, leakage-prevention safeguards, and crop-specific evaluation protocols to govern all subsequent feature discovery and model validation experiments in Suryansh's workspace.

---

## 2. Existing Pipeline & What the Classifier Actually Predicts

### 2.1 The Prediction Target
The system replaces point-price regression with a **discrete 3-class market condition classification task** forecasting the directional condition of a specific canonical agricultural series exactly **seven calendar days into the future ($T+7$)**:

$$\text{series\_id} = \text{District} \_\_ \text{Market} \_\_ \text{Commodity} \_\_ \text{Variety} \_\_ \text{Grade}$$

The target is derived strictly from the percentage price change over 7 calendar days within the same series:

$$R_7 = \left( \frac{\text{Modal\_Price}_{T+7} - \text{Modal\_Price}_T}{\text{Modal\_Price}_T} \right) \times 100$$

### 2.2 Class Definitions and Threshold Boundaries (DEC-015)
As audited in [`src/feature_engineering.py`](file:///Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction/src/feature_engineering.py#L159-L174) and reconciled under DEC-015:

| Class Code | Market Condition | Mathematical Boundary | Simple English Interpretation | Intended Commercial Farmer Advisory |
|---|---|---|---|---|
| **0** | 📉 **Unfavorable** | $R_7 < -2.5\%$ | Bearish market; significant downward price drop exceeding 2.5%. | Warning to harvest and sell immediately at Date $T$; alert against holding produce. |
| **1** | ⚖️ **Normal** | $-2.5\% \le R_7 \le +2.5\%$ | Stable, steady market; price fluctuations bounded within $\pm 2.5\%$. | Routine harvest and sale schedule; no abnormal price action expected. |
| **2** | 📈 **Favorable** | $R_7 > +2.5\%$ | Bullish market; upward price appreciation exceeding 2.5%. | Hold harvest or divert produce to capture expected future premium prices. |

*(Important: For Tomato, predictions reflect short-term market price shifts only and must NOT be used for holding advice due to ambient perishability).*

### 2.3 Active Pipeline Architecture & Baseline Model Suite
Audited in [`src/models.py`](file:///Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction/src/models.py#L34-L102) and [`src/evaluate.py`](file:///Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction/src/evaluate.py#L80-L128):
1. **Decision Tree Classifier:** `max_depth=8`, `min_samples_leaf=20`, `class_weight='balanced'`.
2. **Random Forest Classifier:** 100 bagged trees, `max_depth=12`, `min_samples_leaf=15`, `class_weight='balanced'`.
3. **Extra Trees Classifier:** 100 randomized trees, `max_depth=12`, `min_samples_leaf=15`, `class_weight='balanced'`.
4. **Gradient Boosting Classifier:** 100 boosted trees, `max_depth=5`, `learning_rate=0.1`.
5. **Soft-Voting Ensemble:** Combines soft class probabilities from Gradient Boosting, Random Forest, and Extra Trees.

All classifiers are wrapped inside `sklearn.pipeline.Pipeline` with `SimpleImputer(strategy='median')`. The primary candidate model is selected strictly on the **Validation partition based on highest Validation Macro F1**, and evaluated once on the exploratory historical test partition.

---

## 3. Auditing Target Labels and Generation Logic

### 3.1 Future Observation Dependency & Join Logic
- **Code Reference:** [`src/feature_engineering.py`](file:///Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction/src/feature_engineering.py#L143-L155)
- **Method:** An inner merge links observation date $T$ with future date $T+7$:
  ```python
  df['Target_Date'] = df['Arrival_Date'] + timedelta(days=7)
  matched = pd.merge(df, t7_lookup, left_on=['series_id', 'Target_Date'], right_on=['series_id', 'Arrival_Date'], how='inner')
  ```
- **Audited Safeguard:** If no market transaction occurred on exact calendar date $T+7$ (e.g., due to Sunday closure or holiday), the record is **omitted from the classification dataset**. Crucially, the code does **NOT** substitute $T+6$ or $T+8$ as the target.
- **Leakage Check:** All input features (`FEATURE_COLUMNS`) are constructed strictly using prices and moving averages at date $t \le T$. Target price `Modal_Price_T7` is strictly segregated to `Target_Class` and is never exposed to feature matrices.

### 3.2 Fixed vs Dynamic Threshold Justification
- The static $\pm 2.5\%$ threshold was empirically chosen in the master project to represent a meaningful wholesale price swing exceeding typical daily transport frictions.
- **Audit Defect Identified:** The fixed threshold fails to account for commodity-specific volatility dispersion:
  - In **Wheat** ($\sigma \approx 10\%$, IQR: ₹2,430–₹2,600/qtl), weekly movements rarely cross $\pm 2.5\%$, concentrating **87.13% of all data in the Normal class**.
  - In **Tomato** ($\sigma \approx 19.2\%$), weekly movements routinely exceed $\pm 2.5\%$, reducing the Normal class to a **25.26% minority**.
- **Action for This Phase:** Preserve the canonical DEC-015 thresholds for baseline comparability; in Stage 4, test commodity-specific volatility quantiles for Wheat as an approved experimental branch.

---

## 4. Evaluation Metric Protocol & Error Cost Interpretation

### 4.1 Recommended Metric Hierarchy

Because agricultural mandi prices exhibit severe modal quote stickiness (where 10% to 30% of quotes experience exact 0.00% change over 7 days), **Overall Accuracy is completely disqualified as a primary evaluation criterion**. 

| Metric | Role | Target Benchmark | Mathematical Definition & Rationale |
|---|---|---|---|
| **Macro F1-Score** | **Primary Summary Metric (Rank 1)** | $> 0.50$ (Beat naive 0.23–0.34) | $\frac{1}{3} \sum_{k=0}^2 F1_k$. Weights minority breakout classes (`Favorable`, `Unfavorable`) equally with `Normal` stability. Prevents models from gaming metrics by over-predicting the majority class. |
| **Balanced Accuracy** | **Primary Diagnostic Metric (Rank 2)** | $> 45\%$ (Beat random 33.3%) | $\frac{1}{3} \sum_{k=0}^2 \text{Recall}_k$. Equivalent to accuracy under perfect class balance. Immediately exposes majority-class collapse. |
| **Confusion Matrix** | **Primary Diagnostic Artifact** | 3x3 Table | Full empirical contingency matrix mapping true vs predicted market conditions. Mandatory for auditing asymmetric error costs. |
| **Per-Class Precision & Recall** | **Secondary Diagnostics** | Evaluated per class | Tracks precision and sensitivity on commercial holding (`Favorable`) vs liquidation (`Unfavorable`). |
| **Overall Accuracy** | **Supporting Metric Only** | Must report Lift vs Naive | $\frac{\sum TP_k}{N}$. Must always be reported alongside **Naive Majority-Class Accuracy** ($\Delta \text{Acc} = \text{Acc}_{\text{model}} - \text{Acc}_{\text{naive}}$). |
| **Multi-Class Log Loss** | **Secondary (Probabilistic)** | $< 0.90$ | Cross-entropy loss evaluating calibration of predicted class probabilities (`Prob_Unfavorable`, `Prob_Normal`, `Prob_Favorable`). |

---

### 4.2 Domain Error-Cost Interpretation (Asymmetric Risk)

In agricultural fintech and advisory, different classification mistakes carry vastly different commercial costs:

```text
                                  ACTUAL MARKET CONDITION (Ground Truth)
                        ┌───────────────────┬───────────────────┬───────────────────┐
                        │    UNFAVORABLE    │      NORMAL       │     FAVORABLE     │
┌───────────┬───────────┼───────────────────┼───────────────────┼───────────────────┤
│           │UNFAVORABLE│ Correct Warning   │ False Alarm       │ Costly Under-Sell │
│           │           │ (Avoids Glut)     │ (Premature Sell)  │ (Missed Premium)  │
│           ├───────────┼───────────────────┼───────────────────┼───────────────────┤
│ PREDICTED │  NORMAL   │ Blind to Crash    │ Correct Baseline  │ Missed Breakout   │
│ CONDITION │           │ (Distress Sale)   │ (Orderly Clearing)│ (Routine Sale)    │
│           ├───────────┼───────────────────┼───────────────────┼───────────────────┤
│           │ FAVORABLE │ Catastrophic Loss │ Costly Hold       │ Correct Hold      │
│           │           │ (Hold into Crash) │ (Unnecessary Fee) │ (Captures Gain)   │
└───────────┴───────────┴───────────────────┴───────────────────┴───────────────────┘
```

1. **Catastrophic Directional Reversal (Predicting Favorable when Unfavorable occurs):**  
   - *Consequence:* The farmer is advised to pay storage fees (₹20/qtl) and hold produce, only for the market to crash. The farmer suffers both price decline and accumulated storage/loss costs.
   - *Metric that flags this:* Bottom-left cell of the confusion matrix (`True 0, Pred 2`).
2. **False Favorable / Bad Storage Advice (Predicting Favorable when Normal occurs):**  
   - *Consequence:* The farmer incurs storage fees and shrinkage without capturing any offsetting price appreciation.
   - *Metric that flags this:* Precision for Class 2 (`Favorable`).
3. **Missed Market Crash / Blindness to Distress (Predicting Normal when Unfavorable occurs):**  
   - *Consequence:* The farmer brings produce to the mandi gate expecting normal prices, only to face an unexpected local glut and distress selling.
   - *Metric that flags this:* Recall for Class 0 (`Unfavorable`).

---

## 5. Validation Quality & Leakage Safeguards

The validation protocol is audited against eight critical methodological standards:

| Validation Standard | Implementation in Existing Pipeline | Audit Verdict |
|---|---|---|
| **Chronological Ordering** | Splits by unique `Arrival_Date`: Train (70%, 2024-09 to 2026-01), Val (15%, 2026-01 to 2026-05), Test (15%, 2026-05 to 2026-08). | **VERIFIED CLEAN** |
| **Horizon Embargo Purging** | Enforces an **8-day buffer purging** at Train/Val and Val/Test split boundaries (`src/evaluate.py#L52-L68`). | **VERIFIED CLEAN** (Zero cross-partition label leakage). |
| **Feature Lags & Moving Averages** | Enforces exact calendar joins ($T-1, T-3, T-7$) with explicit `NaN` upon closed dates; rolling std uses $min\_periods=3$ with zero backward filling. | **VERIFIED CLEAN** (Zero lookahead feature leakage). |
| **Pipeline Fitting Isolation** | Median imputation and standard scaling are encapsulated in `Pipeline` and fitted strictly on `X_train`. | **VERIFIED CLEAN** |
| **Duplicate Group Resolution** | Strategy 2 (DEC-008) drops all 1,321 ambiguous same-grade conflicting quotes across 2,664 rows. | **VERIFIED CLEAN** (100% ground-truth label purity). |
| **Series Identity** | Series key explicitly incorporates commercial `Grade`: `(District, Market, Commodity, Variety, Grade)`. | **VERIFIED CLEAN** (Prevents multi-grade collisions). |
| **Class Representation in Test** | Held-out exploratory test set contains all 3 classes for all 4 approved crops. | **VERIFIED CLEAN** |
| **Single-Season Holdout Window** | Exploratory test window covers May 09 to August 25, 2026 (Zaid & early Kharif). | **RESIDUAL RISK** (Misses peak Rabi winter harvest dynamics). |

---

## 6. Crop-Specific Baseline Performance Audit

Evaluated on the held-out exploratory test partition ($N = 9,551$; May 09 to August 25, 2026) using the audited Phase 5 model predictions ([`backing/phase_05/outputs/test_predictions.csv.gz`](file:///Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction/backing/phase_05/outputs/test_predictions.csv.gz)):

```text
========================================================================================================================
                                     HISTORICAL TEST PARTITION BASELINE PERFORMANCE TABLE
========================================================================================================================
Crop / Group   Sample (N)   Majority Acc   Model Acc   Accuracy Lift   Balanced Acc   Macro F1   Multi-Class Log Loss
------------------------------------------------------------------------------------------------------------------------
ALL_CROPS        9,551        55.55%        60.61%        +5.06%         49.59%        0.5041           0.8986
Onion              380        47.89%        56.05%        +8.16%         52.21%        0.5070           0.9419
Potato             572        76.92%        61.19%       -15.73%         59.51%        0.5368           0.8967
Tomato             342        51.17%        53.22%        +2.05%         48.17%        0.4858           0.9852
Wheat            2,424        87.25%        85.93%        -1.32%         34.13%        0.3313           0.5401
========================================================================================================================
```

### 6.1 Onion: The Most Balanced and Discriminative Crop
- **Performance:** **+8.16% accuracy lift** over naive baseline (56.05% vs 47.89%); Balanced Accuracy **52.21%**; Macro F1 **0.5070**.
- **Per-Class Metrics:** Favorable Precision is **55.26%** (Recall 41.18%); Unfavorable Recall is **43.75%** (Precision 31.82%).
- **Verdict:** Onion is the cleanest benchmark crop for agricultural market condition classification.

### 6.2 Potato: Highest Macro F1 and Balanced Detection
- **Performance:** Balanced Accuracy is **59.51%** (highest across all crops); Macro F1 is **0.5368**.
- **Understanding the Accuracy Metric:** Naive guessing achieves 76.92% accuracy by predicting "Normal" 100% of the time, but achieves 0.0% recall on rallies and drops (Balanced Acc 33.3%, Macro F1 0.289). The trained model detects 73.61% of Favorable rallies and 43.33% of Unfavorable drops, yielding a real-world predictive model.

### 6.3 Tomato: Volatile Directional Shifts
- **Performance:** Model Accuracy is **53.22%** (+2.05% lift over baseline); Balanced Accuracy **48.17%**; Macro F1 **0.4858**.
- **Operational Restriction:** Tomato is approved **strictly for price-movement classification evaluation**. Due to post-harvest decay (12.44% loss; 3–7 day shelf life), predictions must never be interpreted as holding recommendations.

### 6.4 Wheat: Verified Majority-Class Collapse
- **Performance Defect:** Under fixed $\pm 2.5\%$ thresholds, **87.25% of test records belong to the Normal class**.
- **Model Collapse:** The model achieves 85.93% overall accuracy, but its **Balanced Accuracy is only 34.13%** (barely above random 33.3%) and **Macro F1 is 0.3313**.
- **Minority Failure:** Recall on Favorable rallies is **1.29%** (misses 98.7% of rallies); Recall on Unfavorable crashes is **3.25%** (misses 96.8% of drops). The model predicts Normal on 2,366 out of 2,424 observations (97.6%).
- **Protocol Mandate:** Wheat must **never be evaluated using Accuracy or Weighted F1**. Balanced Accuracy, Macro F1, and minority recall are strictly mandatory.

---

## 7. Execution Gate: Retraining vs Frozen Baselines

- **Current Status:** Exact baseline metrics across all 4 crops have been independently extracted from the verified Phase 5 prediction outputs ([`reports/phase_03_classification_protocol/baseline_metrics_summary.csv`](file:///Users/kumarsuryansh/Desktop/Temporary/suryansh%20-%20work/reports/phase_03_classification_protocol/baseline_metrics_summary.csv)).
- **Proposed Command for Fresh Retraining (If Requested):**
  ```bash
  python3 "/Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction/run_pipeline.py"
  ```
  *(Runtime: ~45–60 seconds CPU; regenerates all plots in results/).*
- **Recommendation:** Freeze the audited Phase 5 metrics as our reference baseline to maintain clean reproducibility without unnecessary computation.

---

## 8. Summary of Protocol Recommendations

1. **Primary Metric Suite:** Adopt **Macro F1-Score** as the primary summary metric, **Balanced Accuracy** as the primary diagnostic metric, and the **3x3 Confusion Matrix** as the mandatory diagnostic artifact.
2. **Benchmark Reporting:** Require every model report to display **Lift over Naive Majority-Class Baseline** ($\Delta \text{Acc}$).
3. **Wheat Governance:** Evaluate Wheat strictly on Balanced Accuracy, Macro F1, and minority recall; explore volatility-scaled quantile thresholds in Stage 4.
4. **Tomato Restriction:** Treat Tomato exclusively as an exploratory price-direction classification problem, prohibiting ambient storage advice.
