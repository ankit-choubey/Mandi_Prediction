# Executive Summary & Audit Report: MP-FC-006R

**Task ID:** `MP-FC-006R`
**Date:** `2026-11-12` (Asia/Kolkata)
**Execution Environment:** Kaggle CPU (Internet Off, Private, Existing Dataset `mandi-prediction-audit-003b` v1)
**Owner Authorization:** Approved ONE Kaggle CPU kernel push/run; zero dataset uploads, zero installs, zero new ML models, zero automatic retry pushes.
**Kernel ID & Version:** `theankitchoubey/mp-fc-006-baselines` (Version 4)
**Kernel Execution Status:** `KernelWorkerStatus.COMPLETE`
**Execution Run Duration:** 149.04 seconds (~2.5 minutes)
**Baseline Git Commit:** `078ab38b5872615f30647f8ef4dba37f06fcb0c3`
**Resulting Git Commit:** `[to be recorded upon commit]`
**Audit Verdict:** **AUDITED BASELINE RERUN COMPLETE & VERIFIED**

---

## 1. Executive Summary & Verification Receipt

Task `MP-FC-006R` executes the bounded, owner-authorized retrospective rerun of the APMC Mandi price forecasting baseline benchmark across 4 temporal validation folds under provisional Panel v2.

Prior to execution, all Part A preflight checks passed with zero errors:
1. **Decoded-Source Byte Equality:** The stale embedded `baselines.py` payload (previously 24,453 bytes in legacy FC-006) was rebuilt from working source (44,845 bytes, SHA-256: `9cf56e5345235bc593f3bdf62df90e39a56be794edfb5e36fed1b94588c20718`). Decoded bytes matched working source byte-for-byte across all 6 embedded payloads.
2. **Required Imported Symbols:** All 9 production helpers (`check_serving_recency`, `evaluate_series_train_eligibility`, `extract_target_vectorized`, `score_series_origin`, `compute_forecast_metrics`, `cluster_bootstrap_series`, `evaluate_model_slice`, `load_canonical_disputed_keys`, `predict_series_vectorized`) confirmed present and importable.
3. **AST Syntax Parse:** 100% syntax validation across all 5 notebook code cells.
4. **Call Site Integrity:** Notebook loop verified calling `score_series_origin`, `evaluate_series_train_eligibility`, and deterministic iteration via `sorted(all_eligible)`.
5. **Small Bootstrap Smoke Test:** Isolated execution in a clean sandbox confirmed operational readiness.
6. **Full Local Regression Suite:** 175 tests collected and passed in 4.76s.

The remote Kaggle CPU kernel executed to completion (`KernelWorkerStatus.COMPLETE`) in 149.04 seconds. All fail-closed gates passed without deviation.

---

## 2. In-Kernel Gate Results & Verification Receipts

| Gate / Invariant | Master Specification | Remote Execution Value | Status | Artifact Reference |
| :--- | :---: | :---: | :---: | :--- |
| **Panel v2 Row Conservation** | 472,385 raw $\rightarrow$ 463,217 accepted | 472,385 raw $\rightarrow$ 463,217 accepted | **PASSED** | `processing_manifest_v2.json` |
| **Panel v2 SHA-256 Gate** | `851e718468d6b8c9fd07944535a462338e71aa105af25339fe9438b697088f31` | `851e718468d6b8c9fd07944535a462338e71aa105af25339fe9438b697088f31` | **PASSED** | `mandi_5year_validated_v2.csv` |
| **Canonical Disputed Keys** | Exactly 77 unique canonical 6-tuples | Exactly 77 unique canonical keys | **PASSED** | `canonical_disputed_keys_audit.csv` |
| **All-Folds Prediction Archive** | Complete origin predictions ($N = 64,776$) | 64,777 rows (header + 64,776 records) | **PASSED** | `baseline_predictions_all_folds.csv` |
| **Test Window Observations** | Fully reconciled origin transitions | 71,626 raw test window observations | **PASSED** | `exclusion_stage_counts.json` |
| **Recency Exclusion ($<3$ obs)** | Documented exclusion reason | 317 dropped origins | **PASSED** | `exclusion_stage_counts.json` |
| **Missing Target in Window** | Modal price in $[t+6, t+8]$ absent | 3,624 dropped origins | **PASSED** | `exclusion_stage_counts.json` |
| **Target After Fold End** | Strict anti-leakage fold boundary | 2,909 dropped origins | **PASSED** | `exclusion_stage_counts.json` |
| **Tier A Evaluated Origins** | $71,626 - 317 - 3,624 - 2,909 = 64,776$ | **64,776 evaluated origins** | **PASSED** | `exclusion_stage_counts.json` |

---

## 3. Audited Baseline Forecasting Scorecards

### Table 1: Fold $\times$ Tier Scorecard Summary (Tier A, All Four Declared Folds)

All metrics are evaluated on joint finite predictions ($\mathtt{valid\_mask} = \mathtt{isfinite}(y_{\text{true}}) \land \mathtt{isfinite}(y_{\text{model}}) \land \mathtt{isfinite}(y_{\text{naive}})$). Confidence intervals are 95% cluster-bootstrap sampling distributions over unique series (1,000 resamples, seed 42).

| Fold | Model | $N_{\text{elig}}$ | $N_{\text{scored}}$ | Series | Abst. (%) | MAE (Rs/qtl) | Paired Naive MAE | 95% Bootstrap CI on MAE | RMSE | MAPE (%) | Med AE | Bias | $\le 5\%$ | Skill vs Naive | 95% Bootstrap CI on Skill | Low-N |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **F1** | Naive | 37,858 | 37,858 | 359 | 0.00% | 101.59 | 101.59 | [89.65, 115.40] | 280.70 | 4.30% | 40.00 | +21.14 | 75.77% | 0.0000 | [0.0000, 0.0000] | False |
| **F1** | MA | 37,858 | 37,858 | 359 | 0.00% | 131.22 | 101.59 | [114.79, 151.29] | 330.23 | 5.42% | 54.29 | +34.20 | 69.07% | -0.2917 | [-0.3217, -0.2605] | False |
| **F1** | Seasonal | 37,858 | 35,232 | 349 | 6.94% | 685.48 | 100.86 | [590.11, 786.95] | 1172.99 | 27.84% | 370.00 | +178.11 | 20.18% | -5.7963 | [-6.6430, -5.0172] | False |
| **F1** | Drift | 37,858 | 37,404 | 358 | 1.20% | 97.95 | 100.80 | [87.70, 109.43] | 272.45 | 4.27% | 41.25 | +6.41 | 76.56% | +0.0283 | [-0.0046, +0.0594] | False |
| **F2** | Naive | 23,490 | 23,490 | 346 | 0.00% | 106.46 | 106.46 | [93.67, 120.38] | 252.94 | 3.60% | 40.00 | +15.16 | 79.47% | 0.0000 | [0.0000, 0.0000] | False |
| **F2** | MA | 23,490 | 23,490 | 346 | 0.00% | 135.69 | 106.46 | [117.34, 156.23] | 305.98 | 4.35% | 47.86 | +20.08 | 74.59% | -0.2746 | [-0.3081, -0.2394] | False |
| **F2** | Seasonal | 23,490 | 21,044 | 310 | 10.41% | 979.90 | 108.33 | [814.01, 1161.87] | 1847.57 | 34.03% | 420.00 | +703.42 | 24.28% | -8.0459 | [-10.1886, -6.3870] | False |
| **F2** | Drift | 23,490 | 23,293 | 342 | 0.84% | 109.80 | 106.79 | [97.45, 122.93] | 254.36 | 3.88% | 42.50 | +12.56 | 77.87% | -0.0282 | [-0.0584, -0.0008] | False |
| **F3** | Naive | 1,413 | 1,413 | 102 | 0.00% | 108.11 | 108.11 | [85.99, 131.60] | 210.59 | 4.09% | 45.00 | +10.92 | 75.30% | 0.0000 | [0.0000, 0.0000] | False |
| **F3** | MA | 1,413 | 1,413 | 102 | 0.00% | 119.29 | 108.11 | [95.03, 144.17] | 227.17 | 4.54% | 51.43 | +18.42 | 72.82% | -0.1034 | [-0.1584, -0.0560] | False |
| **F3** | Seasonal | 1,413 | 1,322 | 96 | 6.44% | 462.63 | 104.99 | [345.92, 597.58] | 802.39 | 16.32% | 180.00 | +107.03 | 29.50% | -3.4063 | [-4.6368, -2.3638] | False |
| **F3** | Drift | 1,413 | 1,402 | 102 | 0.78% | 107.56 | 108.35 | [85.49, 130.34] | 210.45 | 4.14% | 45.00 | +7.29 | 74.96% | +0.0073 | [-0.0257, +0.0383] | False |
| **F4** | Naive | 2,015 | 2,015 | 37 | 0.00% | 212.84 | 212.84 | [46.46, 459.71] | 733.92 | 5.89% | 20.00 | -15.89 | 78.56% | 0.0000 | [0.0000, 0.0000] | False |
| **F4** | MA | 2,015 | 2,015 | 37 | 0.00% | 179.91 | 212.84 | [43.76, 363.85] | 609.11 | 4.97% | 28.57 | -20.69 | 79.95% | +0.1547 | [-0.1065, +0.2173] | False |
| **F4** | Seasonal | 2,015 | 1,602 | 29 | 20.50% | 244.88 | 151.03 | [78.09, 534.56] | 638.84 | 8.26% | 70.00 | -30.18 | 64.86% | -0.6214 | [-4.2875, -0.0834] | False |
| **F4** | Drift | 2,015 | 1,937 | 35 | 3.87% | 231.25 | 209.61 | [51.52, 513.80] | 791.56 | 6.55% | 28.75 | -10.02 | 76.51% | -0.1032 | [-0.1741, -0.0850] | False |
| **Overall**| Naive | 64,776 | 64,776 | 401 | 0.00% | 106.96 | 106.96 | [95.47, 119.02] | 298.83 | 4.16% | 40.00 | +17.17 | 76.76% | 0.0000 | [0.0000, 0.0000] | False |
| **Overall**| MA | 64,776 | 64,776 | 401 | 0.00% | 134.19 | 106.96 | [119.67, 149.96] | 333.37 | 5.08% | 50.71 | +26.30 | 70.98% | -0.2547 | [-0.2904, -0.2103] | False |
| **Overall**| Seasonal | 64,776 | 59,200 | 362 | 8.61% | 774.38 | 105.02 | [667.74, 890.88] | 1433.76 | 29.45% | 375.00 | +351.69 | 22.70% | -6.3738 | [-7.3355, -5.4701] | False |
| **Overall**| Drift | 64,776 | 64,036 | 398 | 1.14% | 107.32 | 106.60 | [96.32, 119.35] | 303.67 | 4.29% | 42.00 | +7.81 | 76.55% | -0.0068 | [-0.0309, +0.0176] | False |

---

## 4. Sensitivity Scorecard & Retrospective Volatile Subgroup

### Table 2: Sensitivities Scorecard Summary (Overall Tier A)

| Sensitivity Slice | Model | $N_{\text{elig}}$ | $N_{\text{scored}}$ | Abst. (%) | MAE (Rs/qtl) | Paired Naive MAE | Skill vs Naive | 95% Bootstrap CI on MAE |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Exact T+7 Subset** | Naive | 56,386 | 56,386 | 0.00% | 104.97 | 104.97 | 0.0000 | [93.67, 116.77] |
| **Exact T+7 Subset** | MA | 56,386 | 56,386 | 0.00% | 132.75 | 104.97 | -0.2647 | [118.05, 147.92] |
| **Exact T+7 Subset** | Seasonal | 56,386 | 51,777 | 8.17% | 779.35 | 103.70 | -6.5157 | [673.87, 900.02] |
| **Exact T+7 Subset** | Drift | 56,386 | 55,824 | 1.00% | 104.54 | 104.62 | +0.0008 | [94.33, 115.33] |
| **Scope (a): Excluding 77 Disputed Keys** | Naive | 64,758 | 64,758 | 0.00% | 106.93 | 106.93 | 0.0000 | [95.44, 118.87] |
| **Scope (a): Excluding 77 Disputed Keys** | MA | 64,758 | 64,758 | 0.00% | 134.18 | 106.93 | -0.2549 | [119.68, 149.95] |
| **Scope (a): Excluding 77 Disputed Keys** | Seasonal | 64,758 | 59,183 | 8.61% | 774.47 | 104.99 | -6.3763 | [667.74, 891.01] |
| **Scope (a): Excluding 77 Disputed Keys** | Drift | 64,758 | 64,021 | 1.14% | 107.29 | 106.58 | -0.0067 | [96.30, 119.29] |
| **Scope (b): Excising 77 Disputed History** | Naive | 64,756 | 64,756 | 0.00% | 106.90 | 106.90 | 0.0000 | [95.41, 118.74] |
| **Scope (b): Excising 77 Disputed History** | MA | 64,756 | 64,756 | 0.00% | 134.18 | 106.90 | -0.2552 | [119.68, 149.94] |
| **Scope (b): Excising 77 Disputed History** | Seasonal | 64,756 | 59,182 | 8.61% | 774.47 | 105.00 | -6.3762 | [667.74, 891.02] |
| **Scope (b): Excising 77 Disputed History** | Drift | 64,756 | 64,019 | 1.14% | 107.25 | 106.55 | -0.0066 | [96.24, 119.26] |
| **Target Move > 2% Only (Diagnostic Only)** | Naive | 27,858 | 27,858 | 0.00% | 217.38 | 217.38 | 0.0000 | [192.83, 243.12] |
| **Target Move > 2% Only (Diagnostic Only)** | MA | 27,858 | 27,858 | 0.00% | 246.39 | 217.38 | -0.1334 | [218.33, 276.04] |
| **Target Move > 2% Only (Diagnostic Only)** | Seasonal | 27,858 | 25,660 | 7.89% | 770.65 | 210.89 | -2.6543 | [663.78, 895.49] |
| **Target Move > 2% Only (Diagnostic Only)** | Drift | 27,858 | 27,451 | 1.46% | 202.10 | 217.19 | +0.0695 | [182.15, 226.89] |

### Exact Arithmetic Reconciliation for Volatile Subgroup:
- **Eligible Origins:** $N = 27,858$.
- **Drift Scored Instances:** $N = 27,451$.
- **Unscored Instances:** Exactly $27,858 - 27,451 = 407$ instances ($1.46098\% \approx 1.46\%$).
- **Correction:** Prior text reporting 398 missing anchors is superseded by the exact verified count of 407. All 407 instances abstained due to absence of an anchor observation in $[t-17\text{d}, t-11\text{d}]$.
- **Paired Naive MAE on Drift-Scored Instances:** Exactly **217.1854 Rs/qtl** (withdrawing the prior unsupported claim of 217.1723).
- **Skill vs Naive:** $1 - (202.1012 / 217.1854) = 1 - 0.930547 = +0.069453 \approx +0.0695$ (+6.95% skill on volatile moves).
- **95% Bootstrap CI on Volatile Skill:** **[0.0429, 0.0937]** (verified rerun CI from `scorecard_sensitivities.csv`, superseding legacy FC-006 CI of [0.0432, 0.0950]).
- **Scorecard Row & Undefined Skill Reconciliation:** The three scorecards comprise exactly $40 + 120 + 80 = 240$ rows. Of these, exactly 224 rows have finite paired skill identities, and exactly 16 focus-crop rows have undefined (NaN) skill due to $N_{\text{eligible\_origins}} = 0$ (F3 Paddy, F4 Onion, F4 Tomato, F4 Paddy across all 4 models; flagged `low_n_flag = True`). Undefined skill reflects empty historical slices and must never be converted to zero.

---

## 5. Scope B Sensitivity Forensic Accounting

Under `MP-FC-006R`, Scope B historical excising was extended to cover ALL four baseline models. The forensic accounting results from `scope_b_diagnostics_by_fold_crop.csv` establish:

1. **Eligible Origin Deductions:**
   - Total Tier A origins: 64,776.
   - Scope A exclusions (disputed origin or disputed target): 18 origins (10 disputed origin, 10 disputed target, with 2 instances having both origin and target in the 77 disputed keys).
   - Clean Recency Failures: 2 origins in Fold F3 failed the $\ge 3$ observation requirement in $[t-30\text{d}, t]$ after excising the disputed observation.
   - Net Scope B Eligible Origins: $64,776 - 18 - 2 = 64,756$.
2. **Disputed History Removals:**
   - 610 origins had at least one historical observation excised (Fold F3: 51 origins; Fold F4: 559 origins).
3. **Prediction Changes & Validity Transitions:**
   - **Moving Average:**
     - Finite price changed: **13 origins** (F3: 12, F4: 1).
     - Finite $\rightarrow$ NaN transitions: **0**.
     - NaN $\rightarrow$ Finite transitions: **0**.
   - **Seasonal Naive:**
     - Finite price changed: **0**.
     - Finite $\rightarrow$ NaN transitions: **0**.
     - NaN $\rightarrow$ Finite transitions: **0**.
     *(Seasonal lag is $t - 357$ days in 2025; all 77 disputed keys occurred in Feb–Mar 2026).*
   - **Damped Drift:**
     - Finite price changed: **8 origins** (F3: 6, F4: 2).
     - Finite $\rightarrow$ NaN transitions: **1 origin** in Fold F3 (the excised observation was the sole anchor in $[t-17\text{d}, t-11\text{d}]$, causing Drift to abstain on clean history).
     - NaN $\rightarrow$ Finite transitions: **0**.

---

## 6. Scorecard Comparison: Old vs Rerun

| Metric / Dimension | Legacy FC-006 (Old) | Audited FC-006R (Rerun) | Reconciliation Cause |
| :--- | :---: | :---: | :--- |
| **Tier A Naive F1 Origins** | 37,858 | 37,858 | Unchanged (persisted scorecard match) |
| **Tier A Naive F2 Origins** | 23,490 | 23,490 | Unchanged (persisted scorecard match) |
| **Tier A Naive F3 Origins** | 1,413 | 1,413 | Unchanged (persisted scorecard match) |
| **Tier A Naive F4 Origins** | 2,015 | 2,015 | Unchanged (persisted scorecard match) |
| **Tier A Overall Origins** | 64,776 | 64,776 | Exact match ($37,858 + 23,490 + 1,413 + 2,015$) |
| **Overall Naive MAE 95% CI** | [96.3545, 119.0323] | [95.4708, 119.0189] | Deterministic cluster sort + joint mask |
| **Overall MA MAE 95% CI** | [120.7251, 149.3536] | [119.6715, 149.9628] | Deterministic cluster sort + joint mask |
| **Overall Seasonal MAE 95% CI**| [661.0247, 895.0745] | [667.7389, 890.8767] | Joint finite mask (59,200 scored pairs) |
| **Overall Drift MAE 95% CI** | [95.8185, 119.1334] | [96.3202, 119.3452] | Joint finite mask (64,036 scored pairs) |
| **Volatile Subgroup Unscored** | 398 (erroneous) | **407 (exact)** | Arithmetic correction ($27,858 - 27,451 = 407$) |
| **Volatile Paired Naive MAE** | 217.1723 (unsupported) | **217.1854 (exact)** | Computed directly from prediction pairs |
| **Volatile Drift Skill 95% CI** | [0.0432, 0.0950] (legacy) | **[0.0429, 0.0937] (rerun)** | Deterministic cluster bootstrap from scorecard |
| **Overall Drift Skill 95% CI** | [-0.0303, 0.0191] (legacy) | **[-0.0309, 0.0176] (rerun)** | Deterministic cluster bootstrap from scorecard |
| **Scorecard Rows & Undefined Skill** | 240 rows (unannotated) | **224 finite, 16 undefined** | 16 focus-crop rows have N_elig=0 (F3/F4) |
| **Scope B Drift Excising** | Not implemented (0 changes) | **8 finite changed, 1 finite $\rightarrow$ NaN** | Full Scope B excising on all baselines |
| **Scope B Recency Failures** | Not tracked | **2 origins in F3** | Clean recency re-evaluated on clean history |

> [!NOTE]
> Confidence intervals on MAE represent sampling uncertainty of the ratio-of-means cluster bootstrap estimator over series clusters; they are **NOT** forecast prediction intervals.

---

## 7. Operational & Technical Limitations

1. **Provisional Status:** Panel v2 remains **PROVISIONAL**. Accepted market aliases and remaining lookahead concerns are preserved as open audit items pending Task 2 (`MP-DATA-007`).
2. **Data Staleness Gate:** Latest observation is `2026-09-30` (43 days stale relative to `2026-11-12`). Operational advisory remains blocked by `src/health_status.py`.
3. **No ML Approval:** Completion of baseline benchmarking does **NOT** authorize training machine learning models or live advisory deployments.
4. **Conventional MASE:** Formally designated **NOT COMPUTED** (unimplemented in baseline engine).

---

## 8. Master File Update Directive

Per prompt `MP-FC-006R`, the master project documents are updated:
- `documentation/MODEL_AND_MATH_VALIDATION.md`: Added Section 19 with complete run receipt, verified scorecards, and mathematical validation.
- `documentation/PROJECT_EXECUTION_LEDGER.md`: Updated Current Decision reflecting `MP-FC-006R` complete and verified.
- `brain/context.md`: Updated local resumable context. `documentation/context.md` preserved untouched without staging.
