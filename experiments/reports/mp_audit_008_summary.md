# Executive Summary & Audit Report: MP-AUDIT-008

**Task ID:** `MP-AUDIT-008`
**Date:** `2026-11-12` (Asia/Kolkata)
**Execution Environment:** Local Machine (Light Audit, Scoring Helper Modularization, Fixture Regression Tests, Notebook Preparation)
**Baseline Git Commit:** `250eb45e10e8accc614f7c9334a19b9042a5b8f7`
**Resulting Git Commit:** `[to be recorded upon commit]`
**Audit Verdict:** **LOCAL REPAIRS COMPLETE; BASELINE SCORECARD RERUN REQUIRED**
**Authorized Scope:** Local light repairs and fixture checks only. Zero model training, zero full-panel scans/joins, zero dataset uploads, and zero remote Kaggle pushes. All operations strictly $\le 10$ MB, $\le 50,000$ rows, $\le 30$ seconds.

---

## 1. Executive Summary & Core Deliverables

Task `MP-AUDIT-008` completes Step 1 scoring repairs and evidence reconciliation for `MP-FC-006` prior to any remote Kaggle execution or new ML modeling.

The audit unifies the production scoring path between modular functions and the notebook loop, implements comprehensive Scope B historical excising across ALL four baseline models (Naive, Moving Average, Seasonal Naive, and Drift), corrects shared scorer denominators to use a consistent joint finite-value mask on paired instances, replaces gitignored-output test dependencies with self-contained fixtures, verifies byte-for-byte embedded payload equality and AST syntax in the notebook, and reconciles all completion record arithmetic against persisted artifact scorecards.

### Key Deliverables Completed:
1. **Completion Record & Arithmetic Reconciled:**
   - Corrected Tier A Naive fold origin counts from erroneous pasted values (45,958 / 15,390 / 1,791 / 1,637) to exact artifact scorecard values: **F1: 37,858; F2: 23,490; F3: 1,413; F4: 2,015; Total: 64,776**.
   - Reconciled Overall Tier A 95% bootstrap confidence intervals for MAE:
     - **Naive:** `[96.3545, 119.0323]`
     - **Moving Average:** `[120.7251, 149.3536]`
     - **Seasonal Naive:** `[661.0247, 895.0745]`
     - **Damped Drift:** `[95.8185, 119.1334]`
   - Clarified volatile subgroup numbers: **27,858 origins** represent eligible instances for the $>2\%$ target move subset; **Drift scores 27,451** of these (with 1.46% abstention / 398 missing anchor instances).
   - Reconciled series transitions (496 - 6 + 2 = 492; 384,887 + 2,355 = 387,242 rows); clarified that low-coverage entries/exits must not be attributed to alias consolidation without per-series evidence.
   - Formally designated MASE as **NOT COMPUTED** and qualified all causal assertions.

2. **Unified Production Scoring Helper (`src/baselines.py`):**
   - Implemented `score_series_origin()`, `check_serving_recency()`, `extract_target_vectorized()`, and `evaluate_series_train_eligibility()`.
   - Eliminates duplicate inline array logic: the notebook loop now calls the exact tested production helper.
   - Enforces deterministic chronological ordering at the helper boundary (sorting unsorted inputs).

3. **Scope B Sensitivity for ALL Four Baselines:**
   - In `score_series_origin()`, Scope B historical excising is now executed for **Naive, Moving Average, Seasonal Naive, and Drift**.
   - Disputed origin or target explicitly makes the origin ineligible (`scope_b_eligible = False`), recording `scope_b_ineligible_reason`.
   - On clean counterfactual history $\le t$, serving recency ($\ge 3$ observations in $[t-30\text{d}, t]$) is re-evaluated; if $<3$, origin abstains with `recency_failure_after_removal`.
   - If clean recency passes, counterfactual predictions are computed on clean history:
     - Naive: $y(t)$
     - MA: mean of last $\le 7$ observations from clean $[t-30\text{d}, t]$
     - Seasonal Naive: observation nearest $t-357$ from clean $[t-360, t-354]$
     - Drift: anchor nearest $t-14$ from clean $[t-17, t-11]$
   - Emits change flags: `ma_changed_scope_b`, `seasonal_changed_scope_b`, `drift_changed_scope_b`, `scope_b_has_removed_history`.
   - Notebook exports `scope_b_diagnostics_by_fold_crop.csv`.

4. **Shared Scorer Denominators & Joint Finite Masking:**
   - Fixed `evaluate_model_slice()` and `compute_forecast_metrics()` to apply a joint finite mask:
     $$\mathtt{valid\_mask} = \mathtt{isfinite}(y_{\text{true}}) \land \mathtt{isfinite}(y_{\text{model}}) \land \mathtt{isfinite}(y_{\text{naive}})$$
   - Both model error and naive error are evaluated strictly on matching valid pairs.
   - Asserted $N_{\text{scored}} \le N_{\text{eligible}}$.
   - `low_n_flag` is computed strictly on scored origins ($<200$) and scored series ($<10$).
   - All-abstained cases safely return `np.nan` for all metrics and CIs with `low_n_flag = True`.
   - Undefined skill returns `np.nan`, never silently zero.

5. **Self-Contained Fixture Regression Suite (`tests/test_fc006_audit.py`):**
   - Replaced dependency on `experiments/outputs/` with self-contained 77-row fixture tests.
   - Tested all 4 declared folds (F1, F2, F3, F4) with 7-day embargo exclusion and target $\le \text{fold\_end}$.
   - Tested future mutation invariance (prices, insertions, deletions) on baseline predictions and train-only eligibility.
   - Tested all six Scope B cases: removed MA obs, removed drift anchor, removed seasonal anchor, disputed origin, disputed target, and removal causing recency failure.
   - Tested shuffled date normalization.
   - Test receipts: **21 passed in 0.26s** (`test_baselines.py` + `test_fc006_audit.py`), **173 passed in 4.56s** across full repository test suite.

6. **Notebook Verification & Reproducibility:**
   - Verified that decoded base64 payload in Cell 1 matches committed `src/baselines.py` **byte-for-byte** (25,714 bytes).
   - AST-parsed all 5 code cells with **100% syntax success**.

---

## 2. Reconciled Claim & Scorecard Table

| Scope / Metric | Erroneous / Stale Text | Artifact Scorecard Value | Status | Artifact Reference |
| :--- | :---: | :---: | :---: | :--- |
| **Tier A Naive Fold 1 Origins** | 45,958 | **37,858** | **CORRECTED** | `scorecard_fold_x_tier.csv` (row 0) |
| **Tier A Naive Fold 2 Origins** | 15,390 | **23,490** | **CORRECTED** | `scorecard_fold_x_tier.csv` (row 8) |
| **Tier A Naive Fold 3 Origins** | 1,791 | **1,413** | **CORRECTED** | `scorecard_fold_x_tier.csv` (row 16) |
| **Tier A Naive Fold 4 Origins** | 1,637 | **2,015** | **CORRECTED** | `scorecard_fold_x_tier.csv` (row 24) |
| **Tier A Naive Total Origins** | 64,776 | **64,776** | **RECONCILED** | $37,858 + 23,490 + 1,413 + 2,015 = 64,776$ |
| **Overall Tier A Naive MAE 95% CI** | Unreported | **[96.3545, 119.0323]** | **RECORDED** | `scorecard_fold_x_tier.csv` (row 32) |
| **Overall Tier A MA MAE 95% CI** | [121.28, 149.07] | **[120.7251, 149.3536]** | **CORRECTED** | `scorecard_fold_x_tier.csv` (row 33) |
| **Overall Tier A Seasonal MAE 95% CI** | [690.69, 860.77] | **[661.0247, 895.0745]** | **CORRECTED** | `scorecard_fold_x_tier.csv` (row 34) |
| **Overall Tier A Drift MAE 95% CI** | [96.65, 119.55] | **[95.8185, 119.1334]** | **CORRECTED** | `scorecard_fold_x_tier.csv` (row 35) |
| **Volatile Subgroup Eligible Origins** | 27,858 | **27,858** | **RECONCILED** | `scorecard_sensitivities.csv` (row 56) |
| **Volatile Subgroup Drift Scored** | 27,858 | **27,451** | **CORRECTED** | `scorecard_sensitivities.csv` (row 59, 1.46% abstention) |
| **Volatile Subgroup Drift Skill 95% CI**| [0.0401, 0.0982] | **[0.0432, 0.0950]** | **CORRECTED** | `scorecard_sensitivities.csv` (row 59) |
| **Tier A Leaving Series Count** | 9 | **6** | **CORRECTED** | `tier_a_reconciliation_v1_vs_v2.json` |
| **Tier A Entering Series Count** | 5 | **2** | **CORRECTED** | `tier_a_reconciliation_v1_vs_v2.json` |
| **Tier A Common Series Count** | Unreported | **490** | **RECORDED** | $496 - 6 + 2 = 492$ |
| **Tier A Observation Delta** | +244 | **+2,355** | **CORRECTED** | $384,887 \rightarrow 387,242$ rows $\le 2025-12-18$ |
| **MASE Benchmark Label** | 0.75 / 1.25 | **NOT COMPUTED** | **WITHDRAWN** | Section 16 & Section 18 |

---

## 3. Scope B Sensitivity Implementation Details

Under Task MP-AUDIT-008, Scope B is formalized as an interventionist counterfactual evaluation on series history:

```text
                                Origin t
                                   │
Series History:  ... [●] ── [X] ───●────────── [T] ─── ...
                             ▲      │           ▲
                     Disputed Date  y(t)      Target Date
```

1. **Explicit Eligibility Policy:**
   - If origin date $t \in \mathcal{K}_{77}$: `scope_b_eligible = False`, `reason = "disputed_origin"`.
   - If target date $t_{\text{target}} \in \mathcal{K}_{77}$: `scope_b_eligible = False`, `reason = "disputed_target"`.
2. **Historical Excising for All Models:**
   - For all observations strictly before $t$ ($t_{\text{obs}} < t$), if $t_{\text{obs}} \in \mathcal{K}_{77}$, the observation is removed from the series array.
3. **Clean Recency Verification:**
   - Serving recency is re-evaluated: count of clean observations in $[t - 30\text{d}, t]$ must be $\ge 3$.
   - If $<3$: `scope_b_eligible = False`, `reason = "recency_failure_after_removal"`. All Scope B forecasts abstain (NaN).
4. **Counterfactual Predictions:**
   - **Naive:** $\hat{y}_{\text{naive}}(t+7) = y(t)$ (unchanged since $t$ is non-disputed).
   - **Moving Average:** Mean of the last $\le 7$ observations in clean $[t - 30\text{d}, t]$.
   - **Seasonal Naive:** Observation nearest $t - 357$ in clean $[t - 360, t - 354]$ (earlier tie-breaker).
   - **Damped Drift:** Slope computed from clean anchor nearest $t - 14$ in $[t - 17, t - 11]$.

---

## 4. Test Receipts

### Targeted Baseline & Audit Test Suite
```text
Command: python3 -m pytest tests/test_baselines.py tests/test_fc006_audit.py
Platform: Darwin -- Python 3.14.0, pytest-9.1.1, pluggy-1.6.0

tests/test_baselines.py ........                                         [ 38%]
tests/test_fc006_audit.py .............                                  [100%]

============================== 21 passed in 0.26s ==============================
```

### Full Repository Regression Test Suite
```text
Command: python3 -m pytest tests/
Platform: Darwin -- Python 3.14.0, pytest-9.1.1, pluggy-1.6.0

tests/test_baselines.py ........                                         [  4%]
tests/test_data_foundation.py ...........                                [ 10%]
tests/test_data_pipeline.py ..............                               [ 19%]
tests/test_data_validation.py .......                                    [ 23%]
tests/test_economic_backtest.py ............                             [ 30%]
tests/test_economic_model.py ...................                         [ 41%]
tests/test_fc006_audit.py .............                                  [ 48%]
tests/test_feasibility_reconciliation.py .....                           [ 51%]
tests/test_ingest_agmarknet_arrivals.py ..                               [ 52%]
tests/test_ingest_arrivals_immutability.py ...................           [ 63%]
tests/test_market_identity.py ..........                                 [ 69%]
tests/test_operational_output.py .................                       [ 79%]
tests/test_phase05_robustness.py ......                                  [ 82%]
tests/test_phase06b_data_validation.py ........                          [ 87%]
tests/test_production_pipeline.py .......                                [ 91%]
tests/test_recommendation_safety_gate.py ...............                 [100%]

============================= 173 passed in 4.56s ==============================
```

---

## 5. Unresolved Scientific Limitations & Lookahead Debt

1. **Panel Harmonization Lookahead:**
   The low-observation filter ($<20$ observations) and accepted alias transition decisions in `data_pipeline.py` (panel v2) utilize the full 5-year panel history. This introduces retrospective lookahead into market identity resolution and series selection. Panel v2 remains strictly **PROVISIONAL** until a causal, rolling-origin harmonization pipeline is benchmarked.
2. **Retrospective Volatile Subgroup:**
   The $>2\%$ target-move subset conditions on $|y(t_{\text{target}}) - y(t)| / y(t) > 0.02$. Because future prices are unobserved at prediction time $t$, this subset is a descriptive diagnostic benchmark only and cannot be used for live model selection or adaptive dispatch.
3. **Data Freshness Gap:**
   Latest raw observation is `2026-09-30` (43 days stale relative to `2026-11-12`). Recommendation safety gate blocks operational advisory until live feeds are connected.

---

## 6. Proposed Bounded Remote Rerun Request

To regenerate the verified baseline scorecards with the corrected scoring engine and full prediction archive, the following remote Kaggle run is proposed for owner authorization:

- **Target Kernel:** `theankitchoubey/mp-fc-006-baselines` (v4)
- **Execution Target:** Kaggle CPU, Internet Disabled, Single Session
- **Dataset Input:** Existing private dataset `theankitchoubey/mandi-prediction-audit-003b` (v1)
- **Source Modules Embedded:** `src/data_pipeline.py`, `src/market_identity.py`, `src/baselines.py` (matching commit `[to be recorded]`)
- **Required Assertions:**
  - Panel v2 SHA-256 == `851e718468d6b8c9fd07944535a462338e71aa105af25339fe9438b697088f31`. If it differs, STOP immediately.
  - Fail-closed loading of canonical disputed keys ($N = 77$).
- **Expected Artifacts:**
  1. `scorecard_fold_x_tier.csv`
  2. `scorecard_fold_x_focus_crop.csv`
  3. `scorecard_sensitivities.csv` (with corrected Scope a and Scope b evaluations)
  4. `scope_b_diagnostics_by_fold_crop.csv` (detailed exclusion and change accounting)
  5. `canonical_disputed_keys_audit.csv`
  6. `exclusion_stage_counts.json`
  7. `baseline_predictions_sample.csv` (5,000 rows)
  8. `baseline_predictions_all_folds.csv` (complete archive of all ~64,776 Tier A origin evaluations)
  9. `kernel_execution_manifest.json`
- **Expected Runtime / Budget:** ~90 seconds on Kaggle CPU (within standard quota limits).
- **Stop Conditions:** Zero local execution of heavy loops. No Kaggle push or execution without explicit owner authorization.
