# Phase 5: Baseline Reproduction Report

**Project:** Mandi_Prediction
**Repository:** `ankit-choubey/Mandi_Prediction`
**Phase:** 5 — Robustness, Statistical Uncertainty, and Generalization Audit
**Date:** October 10, 2026
**Starting Commit SHA:** `91b8efc6c4940c20d9cd6a994d692ded4523d5a7`

---

## 1. Raw Dataset Integrity and Cryptographic Hashes

All analyses in Phase 5 operate strictly on the existing raw APMC mandi price files in `data/raw/`. No external datasets were downloaded or modified.

| File Path | Size (Bytes) | SHA-256 Hash |
|---|---|---|
| `data/raw/Gaziabaad.csv` | 3,656,537 | `71601f993e07efa146f126747245a7fffb608a307abdea579475ba19bfeb0251` |
| `data/raw/Jhansi.csv` | 1,947,875 | `7d0808d8d32555212af546004195c0ccf58e368106daad67169a231e80988a5c` |
| `data/raw/Kanpur.csv` | 3,705,373 | `0eb17704ebba1f66b8c9ef660f48dabc3665ea4691ed3b8aa20a49df8528d04a` |
| `data/raw/Lukhnow.csv` | 1,840,744 | `6ca52743cc2f9059bf1e3b919b25317aa367f580bbafa6f62adb9db1d759bb13` |
| `data/raw/Unnao.csv` | 2,570,462 | `d4ee358b96cad3a888e4a92acd993327e56c4dc6af6eb60814193f98f591cebc` |

---

## 2. Record Accounting and Pipeline Attrition

The data pipeline transitions from raw transaction records to modeling targets as follows:

| Processing Stage | Record Count | Unique Series | Description / Exclusion Rule |
|---|---|---|---|
| **Raw Input Ingestion** | 160,192 | 2,390 | Combined rows across all 5 raw district files |
| **Purity Filtering (Strategy 2)** | 157,512 | 2,390 | Excludes 2,664 ambiguous conflicting same-grade records across 1,321 dates |
| **Series Activity Filtering** | 150,687 | 1,069 | Retains series with $\ge 20$ historical observations (`min_series_records=20`) |
| **Exact $T+7$ Target Realization** | 115,833 | 1,069 | Requires an exact matching price observation on $\text{Date}_T + 7$ calendar days |

**Class Distribution on Eligible Target Records ($n = 115,833$):**
- **Normal (1):** 68,895 (59.48%) — $\Delta P\% \in [-2.5\%, +2.5\%]$
- **Unfavorable (0):** 25,069 (21.64%) — $\Delta P\% < -2.5\%$
- **Favorable (2):** 21,869 (18.88%) — $\Delta P\% > +2.5\%$

---

## 3. Chronological Partitions and Embargo Buffers

Chronological splitting enforces complete future isolation. All partitions are partitioned globally by origin date $\text{Date}_T$, with 8-day embargo buffers to eliminate target outcome overlap:

| Partition | Date Range ($\text{Date}_T$) | Target Realization ($\text{Date}_{T+7}$) | Records ($n$) | Purpose / Status |
|---|---|---|---|---|
| **Training** | 2024-09-01 to 2026-01-13 | 2024-09-08 to 2026-01-20 | 99,881 | Model fitting only |
| *Train/Val Embargo* | 2026-01-14 to 2026-01-20 | 2026-01-21 to 2026-01-27 | 94 | **Purged** (prevents train lookahead into validation) |
| **Validation** | 2026-01-21 to 2026-05-01 | 2026-01-28 to 2026-05-08 | 5,671 | Hyperparameter freezing & threshold calibration |
| *Val/Test Embargo* | 2026-05-02 to 2026-05-08 | 2026-05-09 to 2026-05-15 | 636 | **Purged** (prevents validation lookahead into test) |
| **Exploratory Test** | 2026-05-09 to 2026-08-25 | 2026-05-16 to 2026-09-01 | 9,551 | **Exploratory evaluation window** (NOT an untouched holdout) |

---

## 4. Model Architecture and Features

- **Algorithm:** Gradient Boosting Classifier (`sklearn.ensemble.GradientBoostingClassifier`)
- **Hyperparameters:** `n_estimators=100`, `max_depth=5`, `learning_rate=0.05`, `random_state=42`. Fit strictly on Training partition ($n = 99,881$).
- **Features (`FEATURE_COLUMNS`, 13 variables):**
  1. `Log_Modal_Price`: $\log(\text{Modal\_Price})$ at Date $T$
  2. `Price_Spread_Ratio`: $(\text{Max\_Price} - \text{Min\_Price}) / \text{Modal\_Price}$ at Date $T$
  3. `Return_1d`: Past 1-day percentage price change
  4. `Return_3d`: Past 3-day percentage price change
  5. `Return_7d`: Past 7-day exact calendar percentage price change
  6. `Price_Change_7d`: Bounded past 7-day price difference
  7. `Momentum_Ratio_7d`: Ratio of short-term to long-term momentum
  8. `Historical_Volatility_Causal`: Expanding causal volatility (`min_periods=10`) with zero backward filling
  9. `DayOfWeek`: Integer day of the week (0–6)
  10. `Month`: Integer calendar month (1–12)
  11. `Commodity_Code`: Ordinal categorical commodity indicator
  12. `Market_Code`: Ordinal categorical canonical market indicator
  13. `Grade_Code`: Ordinal categorical grade indicator

---

## 5. Baseline Predictive Performance

### 5.1 Validation Partition ($n = 5,671$, Jan 21 – May 01, 2026)
- **Overall Accuracy:** 56.85% (3,224 / 5,671)
- **Balanced Accuracy:** 49.48%
- **Macro F1:** 0.4957

| Class | Precision | Recall | F1-Score | Support |
|---|---|---|---|---|
| **Unfavorable (0)** | 0.4459 | 0.4202 | 0.4327 | 1,335 |
| **Normal (1)** | 0.6581 | 0.7713 | 0.7102 | 2,912 |
| **Favorable (2)** | 0.4170 | 0.2928 | 0.3441 | 1,424 |

### 5.2 Exploratory Test Partition ($n = 9,551$, May 09 – Aug 25, 2026)
- **Overall Accuracy:** 60.61% (5,789 / 9,551)
- **Balanced Accuracy:** 49.59%
- **Macro F1:** 0.5041

| Class | Precision | Recall | F1-Score | Support |
|---|---|---|---|---|
| **Unfavorable (0)** | 0.4933 | 0.3191 | 0.3875 | 1,968 |
| **Normal (1)** | 0.6834 | 0.8253 | 0.7477 | 5,306 |
| **Favorable (2)** | 0.4182 | 0.3434 | 0.3771 | 2,277 |

---

## 6. Baseline Economic Performance (Central Scenario Benchmark)

Evaluated under the canonical economic model:
$$\Delta r = (1 - L)(1 - d_q)P_{T7} - P_T\left(1 + \frac{i \cdot h}{365}\right) - (c_s + c_h)$$
Central Scenario Parameters: $c_s = ₹20.00/\text{qtl}$, $c_h = ₹0.00/\text{qtl}$, $L = 0.010$ (1.0%), $i = 0.07$ (7.0% p.a.), $d_q = 0.0$, $h = 7$ days.

| Partition | Policy | Times Stored | % Stored | Win Rate | Mean Return (₹/eligible qtl) | Conditional Return (₹/stored qtl) | Aggregate Net Gain (₹, 10 qtl/decision) |
|---|---|---|---|---|---|---|---|
| **Validation** ($n = 5,671$) | Always Sell | 0 | 0.0% | 0.0% | ₹0.00 | ₹0.00 | ₹0.00 |
| | Always Store | 5,671 | 100.0% | 25.89% | -₹30.32 | -₹30.32 | -₹1,719,222.39 |
| | Trend Momentum | 896 | 15.80% | 22.10% | -₹68.02 | -₹430.52 | -₹3,857,483.49 |
| | **Model Signal** | 1,000 | 17.63% | **37.90%** | **+₹33.55** | **+₹190.27** | **+₹1,902,741.76** |
| | Oracle Benchmark | 1,468 | 25.89% | 100.0% | +₹234.36 | +₹905.34 | +₹13,290,460.97 |
| **Exploratory Test** ($n = 9,551$) | Always Sell | 0 | 0.0% | 0.0% | ₹0.00 | ₹0.00 | ₹0.00 |
| | Always Store | 9,551 | 100.0% | 24.15% | -₹28.29 | -₹28.29 | -₹2,701,769.67 |
| | Trend Momentum | 1,559 | 16.32% | 23.41% | -₹80.72 | -₹494.53 | -₹7,709,706.61 |
| | **Model Signal** | 1,870 | 19.58% | **37.81%** | **+₹42.21** | **+₹215.60** | **+₹4,031,741.12** |
| | Oracle Benchmark | 2,307 | 24.15% | 100.0% | +₹305.22 | +₹1,263.61 | +₹29,151,388.05 |

---

## 7. Audit of Historical Discrepancies

- **Phase 3 vs Phase 4/5 Partition Sizes:**
  Phase 3 exploratory research logs evaluated a temporal partition without the `min_series_records >= 20` series-activity filter, yielding $n=2,914$ validation and $n=12,625$ exploratory test records. Phase 4 and Phase 5 use the production-aligned `load_and_clean_mandi_data(min_series_records=20)` and chronological split `(70% train, 15% val, 15% test)` in `src/evaluate.py`, yielding $n=5,671$ validation and $n=9,551$ exploratory test records.
- **Reproducibility Status:**
  All Phase 4 and Phase 5 results above were **independently reproduced** from scratch in this execution environment without discrepancies.
