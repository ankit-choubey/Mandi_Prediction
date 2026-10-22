# Validation Risk Register: Classification Pipeline Audit

**Investigator:** Suryansh  
**Phase:** 03 — Classification Evaluation Protocol and Baseline Audit  
**Target Repository:** [`/Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction`](file:///Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction)  
**Workspace:** [`/Users/kumarsuryansh/Desktop/Temporary/suryansh - work`](file:///Users/kumarsuryansh/Desktop/Temporary/suryansh%20-%20work)  
**Date:** October 23, 2026  

---

## 1. Risk Taxonomy & Summary

This register systematically audits all potential sources of leakage, class imbalance, identifier distortion, and evaluation biases in the existing mandi classification pipeline.

| Risk ID | Category | Specific Concern | Severity | Status | Recommended Action |
|---|---|---|---|---|---|
| **VR-01** | Class Imbalance | Wheat Class Collapse (87% Normal) | **CRITICAL** | **CONFIRMED DEFECT** | Mandate Balanced Accuracy & Macro F1; prohibit evaluating Wheat on accuracy alone; propose commodity-specific dynamic thresholds for Stage 4. |
| **VR-02** | Leakage | Target Realization ($T+7$) Cross-Boundary Leakage | **HIGH** | **REMEDIATED & VERIFIED** | Retain strict 8-day embargo buffer purging at Train/Val and Val/Test partition boundaries (`src/evaluate.py`). |
| **VR-03** | Leakage | Lookahead Leakage in Lags and Rolling Windows | **HIGH** | **REMEDIATED & VERIFIED** | Enforce exact calendar date joins ($T-1, T-3, T-7$) with explicit `NaN` upon market closures; causal rolling std with $min\_periods=3$ (zero bfill). |
| **VR-04** | Preprocessing | Feature Scalers & Imputers Fitted Across Splits | **HIGH** | **REMEDIATED & VERIFIED** | Ensure `SimpleImputer` and `StandardScaler` are fitted strictly on the Training partition within scikit-learn Pipelines. |
| **VR-05** | Ambiguity | Same-Grade Conflicting Duplicate Price Quotes | **MEDIUM** | **REMEDIATED & VERIFIED** | Apply Strategy 2 (DEC-008): Exclude all ambiguous same-grade series-dates with conflicting prices to guarantee 100% ground-truth label purity. |
| **VR-06** | Identifiers | Nominal Market Naming Discontinuity (`APMC` suffix) | **MEDIUM** | **CONFIRMED RISK** | Map the 42 nominal market strings to the 21 physical APMC wholesale yards to prevent artificial series fragmentation. |
| **VR-07** | Temporal Shift | Single-Season Held-Out Test Window | **MEDIUM** | **PLAUSIBLE RISK** | The exploratory test window (May–Aug 2026) captures Zaid/early Kharif only. Recommend multi-year rolling temporal backtesting in later phases. |
| **VR-08** | Economic Decoupling| Tomato High Perishability vs Storage Advice | **HIGH** | **CONFIRMED RISK** | Restrict Tomato strictly to directional market condition classification; prohibit coupling with 7-day ambient storage advisory. |
| **VR-09** | Metric Selection | Accuracy Metric Overstating Model Quality | **HIGH** | **CONFIRMED DEFECT** | Disqualify Overall Accuracy as a primary candidate model selection criterion. Benchmark all models against Naive Majority-Class Baseline. |
| **VR-10** | External Joins | Arrival Volume Latency and Unit Mismatches | **MEDIUM** | **PLAUSIBLE RISK** | Verify CEDA quantity arrivals units (tonnes vs quintals) and audit publication delays before introducing as features in Stage 4. |

---

## 2. In-Depth Audit of Specific Risks

### Risk VR-01: Wheat Class Collapse under Fixed $\pm 2.5\%$ Thresholds
- **Evidence:** In the clean dataset, Wheat modal prices are tightly clustered (IQR: ₹2,430 to ₹2,600/qtl; $\sigma = ₹157.09$/qtl) due to government Minimum Support Prices (MSP) and procurement operations. In the held-out exploratory test partition ($N = 2,424$), **87.25% of records fall into the Normal class (2,115 records)**, while Favorable (155, 6.4%) and Unfavorable (154, 6.4%) are tiny minorities.
- **Observed Model Behavior:** The baseline Gradient Boosting model achieves **85.93% Accuracy**, but its **Balanced Accuracy is only 34.13%** and **Macro F1 is 0.3313**. Per-class recall on Favorable is **1.12%** and on Unfavorable is **3.05%**. The model predicts "Normal" on almost every single observation.
- **Evaluation Mandate:** Evaluating Wheat using Accuracy or Weighted F1 is completely uninformative. Performance must be reported via Balanced Accuracy, Macro F1, and the full 3x3 confusion matrix.

### Risk VR-02: Target Realization ($T+7$) Boundary Overlap
- **Evidence:** An observation at origin date $T$ requires observing prices on calendar date $T+7$. If origin dates near the end of the training set ($T_{\text{train\_end}} - 6 \le T \le T_{\text{train\_end}}$) are included, their target outcomes realize during the validation period, creating lookahead label leakage.
- **Verification:** Audited [`src/evaluate.py`](file:///Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction/src/evaluate.py#L52-L68). The code enforces an 8-day embargo buffer:
  ```python
  train_embargo_cutoff = train_cutoff - pd.Timedelta(days=horizon_days + 1)
  train_df = sorted_df[sorted_df['Arrival_Date'] <= train_embargo_cutoff].copy()
  ```
  This purges all origin dates whose $T+7$ realization crosses the validation split boundary. This risk is **fully remediated and verified**.

### Risk VR-03: Temporal Asymmetry and Lookahead in Features
- **Evidence:** Early un-audited scripts used row-based shifts (`shift(7)`), which only matched 7 calendar days in 18.4% of records due to weekend market closures.
- **Verification:** Audited [`src/feature_engineering.py`](file:///Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction/src/feature_engineering.py#L43-L67). Features now use exact calendar date joins (`Arrival_Date - timedelta(days=k)` for $k \in \{1, 3, 7\}$) and causal rolling windows ($min\_periods=3$, zero backward filling). Missing dates produce explicit `NaN`, which are median-imputed inside scikit-learn Pipelines. This risk is **fully remediated and verified**.

### Risk VR-04: Contamination in Preprocessing and Scaling
- **Evidence:** If median imputation, standard scaling, or categorical encodings are fitted on the concatenated dataset (train + val + test), future distribution statistics leak into training.
- **Verification:** Audited [`src/evaluate.py`](file:///Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction/src/evaluate.py#L96-L106) and [`src/models.py`](file:///Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction/src/models.py#L81-L101). All models encapsulate `SimpleImputer` inside `sklearn.pipeline.Pipeline`, which is fitted strictly via `pipeline.fit(X_train, y_train)` and transformed without feedback on validation and test partitions. This risk is **fully remediated and verified**.

### Risk VR-06: Nominal Market Naming Discontinuity (`APMC` Suffix)
- **Evidence:** In November 2025, upstream data sources appended `" APMC"` to market names (e.g. `Lucknow` $\to$ `Lucknow APMC`). If unmapped, this splits a continuous single market time series into two disconnected segments, breaking historical rolling moving averages and lags across the November 2025 boundary.
- **Remediation Status:** Verified canonical alias mapping in `src/feasibility.py` and `backing/PROJECT_AUDIT.md`. Mappings are unified for approved pairs, while distinct concurrent yards (`Jhansi` vs `Jhansi (Grain)`) are strictly preserved.

### Risk VR-08: Tomato Operational Risk Decoupling
- **Evidence:** ICAR-CIPHET post-harvest studies confirm national post-harvest loss of 12.44% for fresh tomatoes. Ambient shelf life is 3 to 7 days.
- **Mandate:** In strict adherence to Section 1 of Prompt 3, Tomato is approved **strictly for price-movement classification modeling**. It must NOT be interpreted as a storage-versus-selling decision advisory.

---

## 3. Residual Risk Summary

All critical data leakage mechanisms (VR-02, VR-03, VR-04) are **verified remediated** in the existing codebase. The primary residual risks are analytical and methodological:
1. **Wheat's severe majority class concentration (87% Normal)**, which requires strict metric governance.
2. **The single-season temporal window of the exploratory test set (May–Aug 2026)**, which captures Zaid / early Kharif dynamics but misses peak Rabi harvest gluts.
