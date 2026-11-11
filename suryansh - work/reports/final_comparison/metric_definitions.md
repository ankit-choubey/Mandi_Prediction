# Formal Mathematical Metric Definitions & Evaluation Standards

**Project:** Mandi Prediction — APMC Market Intelligence System  
**Investigator:** Suryansh  
**Workspace:** [`/Users/kumarsuryansh/Desktop/Temporary/suryansh - work`](file:///Users/kumarsuryansh/Desktop/Temporary/suryansh%20-%20work)  
**Deliverable:** `reports/final_comparison/metric_definitions.md`  
**Date:** October 23, 2026  

---

## 1. Overview & Evaluation Principles

In wholesale mandi condition classification, agricultural market dynamics produce severe class imbalances (e.g. Wheat with 87% Normal observations) and asymmetric economic costs. Evaluating models strictly using standard Overall Accuracy produces misleading conclusions, masking complete failure on critical market breakout events.

This reference standard documents the exact mathematical definitions, numerators, denominators, and interpretation rules for every metric reported across this research project.

---

## 2. Notation & Indexing

Let $N$ be the total number of evaluated observations in the held-out test partition.  
Let $\mathcal{C} = \{0, 1, 2\}$ represent the three discrete target classes:
- Class $0$: **Unfavorable** ($R_7 < -2.5\%$)
- Class $1$: **Normal** ($-2.5\% \le R_7 \le +2.5\%$)
- Class $2$: **Favorable** ($R_7 > +2.5\%$)

Let $y_i \in \mathcal{C}$ be the true ground-truth label for sample $i$.  
Let $\hat{y}_i \in \mathcal{C}$ be the model's discrete predicted class.  
Let $\hat{p}_{i, c} = P(y_i = c \mid x_i)$ be the model's predicted probability vector such that $\sum_{c=0}^2 \hat{p}_{i, c} = 1$.

Let $C$ be the empirical $3 \times 3$ confusion matrix where element $C_{j, k}$ denotes the number of observations with true class $j$ that were predicted as class $k$:

$$C = \begin{pmatrix} C_{00} & C_{01} & C_{02} \\ C_{10} & C_{11} & C_{12} \\ C_{20} & C_{21} & C_{22} \end{pmatrix}$$

The true class support for class $k$ is $N_k = \sum_{j=0}^2 C_{k, j}$, with $\sum_{k=0}^2 N_k = N$.  
The predicted count for class $k$ is $\hat{N}_k = \sum_{j=0}^2 C_{j, k}$.

---

## 3. Metric Formulations

### 1. Naive Majority-Class Baseline Accuracy
The accuracy achieved by a trivial dummy classifier that unconditionally predicts the most frequent class observed in the test sample:

$$\text{Majority Baseline Acc} = \frac{\max_{k \in \mathcal{C}} N_k}{N} \times 100\%$$

- **Denominators:** Numerator is the support of the dominant class; denominator is $N$.
- **Interpretation:** Establishes the floor that any learned machine learning model must beat to claim genuine predictive utility.

---

### 2. Overall Accuracy
The fraction of all test observations correctly classified:

$$\text{Accuracy} = \frac{\sum_{k=0}^2 C_{kk}}{N} = \frac{C_{00} + C_{11} + C_{22}}{N} \times 100\%$$

- **Critical Limitation:** In Wheat, where $N_1 / N = 87.25\%$, a model predicting Normal 100% of the time achieves $87.25\%$ accuracy while possessing zero practical utility. Overall accuracy is therefore **disqualified as a primary selection metric**.

---

### 3. Accuracy Lift ($\Delta \text{Acc}$)
The absolute percentage-point difference between model accuracy and the naive majority-class baseline:

$$\Delta \text{Acc} = \text{Accuracy} - \text{Majority Baseline Acc}$$

- **Positive Lift ($\Delta \text{Acc} > 0$):** Model extracts real predictive signal beyond the majority prior.
- **Negative Lift ($\Delta \text{Acc} < 0$):** Model makes more errors than a trivial single-class rule.

---

### 4. Per-Class Precision ($P_k$)
The fraction of predictions for class $k$ that were correct:

$$P_k = \frac{C_{kk}}{\hat{N}_k} = \frac{C_{kk}}{\sum_{j=0}^2 C_{j, k}}$$

- **Zero Division Convention:** If $\hat{N}_k = 0$ (model never predicts class $k$), $P_k = 0.0000$.
- **Economic Meaning:**
  - $P_2$ (**Favorable Precision**): When the model tells a farmer to hold produce, how often does a genuine price rally occur? Crucial to prevent wasteful storage expenses.
  - $P_0$ (**Unfavorable Precision**): When the model issues a market crash alert, how often is it genuine?

---

### 5. Per-Class Recall / Sensitivity ($R_k$)
The fraction of actual events of class $k$ that the model detected:

$$R_k = \frac{C_{kk}}{N_k} = \frac{C_{kk}}{\sum_{j=0}^2 C_{k, j}}$$

- **Economic Meaning:**
  - $R_0$ (**Unfavorable Recall**): The proportion of market crashes caught before the farmer arrives at the mandi gate.
  - $R_2$ (**Favorable Recall**): The proportion of market breakouts captured.

---

### 6. Per-Class F1-Score ($F1_k$)
The harmonic mean of precision and recall for class $k$:

$$F1_k = 2 \times \frac{P_k \times R_k}{P_k + R_k} = \frac{2 C_{kk}}{N_k + \hat{N}_k}$$

---

### 7. Macro-Averaged F1-Score (Primary Summary Metric — Rank 1)
The unweighted arithmetic mean of F1-scores across all three classes:

$$\text{Macro F1} = \frac{1}{3} \sum_{k=0}^2 F1_k = \frac{F1_0 + F1_1 + F1_2}{3}$$

- **Why Macro F1 is Primary:** Weights rare market crashes ($k=0$) and rare price rallies ($k=2$) equally with routine stability ($k=1$), preventing majority-class dominance.

---

### 8. Balanced Accuracy (Primary Diagnostic Metric — Rank 2)
The unweighted arithmetic mean of recall across all three classes:

$$\text{Balanced Accuracy} = \frac{1}{3} \sum_{k=0}^2 R_k = \frac{R_0 + R_1 + R_2}{3} \times 100\%$$

- **Theoretical Baseline:** For 3-class classification, purely random guessing achieves **33.33%**.
- **Diagnostic Role:** Directly exposes majority-class collapse. For Wheat, the model's 85.93% accuracy is exposed as a collapse because Balanced Accuracy is only **35.32%** (barely above 33.3%).

---

### 9. Multi-Class Logarithmic Loss (Cross-Entropy Loss)
The penalization of predicted probability distributions against ground truth:

$$\text{Log Loss} = - \frac{1}{N} \sum_{i=1}^N \sum_{c=0}^2 \mathbb{I}(y_i = c) \ln(\max(\epsilon, \min(1 - \epsilon, \hat{p}_{i, c})))$$

Where $\epsilon = 10^{-15}$ prevents numerical undefined log of zero.
- **Role:** Measures whether the model produces well-calibrated probabilities necessary for risk-adjusted economic decision making.

---

## 4. Summary Metric Decision Hierarchy

```text
========================================================================================================================
RANK   METRIC                   PRIMARY PURPOSE                                DECISION USE CASE
========================================================================================================================
1      Macro F1-Score           Overall Model Optimization Standard            Primary metric for candidate selection
2      Balanced Accuracy        Imbalance & Collapse Diagnostic                Mandatory gatekeeper for Wheat and Potato
3      3x3 Confusion Matrix     Directional Reversal Audit                     Detects catastrophic errors (CM[0, 2])
4      Favorable Precision (P2) Holding Advisory Reliability                   Economic validation for storage decisions
5      Unfavorable Recall (R0)  Distress Warning Sensitivity                   Farmer protection from market gluts
6      Accuracy Lift (ΔAcc)     Validation vs Naive Prior                      Sanity check against trivial heuristics
========================================================================================================================
```
