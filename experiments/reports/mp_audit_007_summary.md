# Executive Summary & Audit Adjudication: MP-AUDIT-007

**Task ID:** `MP-AUDIT-007`
**Date:** `2026-11-12` (Asia/Kolkata)
**Execution Environment:** Local Machine (Light Audit, Fixture Tests, Source & Notebook Corrections)
**Baseline Git Commit:** `7931caaf01ee9e53ea2f18b823d710b8c61851ff`
**Audit Verdict:** **LOCAL REPAIRS COMPLETE; BASELINE SCORECARD RERUN REQUIRED**
**Authorized Scope:** Local light audit, fixture regression tests, small source/notebook/report corrections. Zero heavy compute, zero full-panel joins, zero data uploads, and zero remote Kaggle pushes.

---

## 1. Executive Summary & Core Deliverables

Task `MP-AUDIT-007` executes a rigorous independent audit and repair of the deliverables, reporting narratives, baseline scoring paths, and evidence records from Task `MP-FC-006`.

The audit uncovers and repairs a critical vulnerability in the sensitivity analysis of the 77 disputed keys, resolves numerical discrepancies between pasted report prose and artifact CSVs, aligns series reconciliation counts with diagnostic manifests, proves mathematical loop equivalence between modular baseline functions and the vectorized notebook loop, implements scored-case series and LOW-N accounting, and prepares the corrected Kaggle execution notebook for a subsequent remote rerun.

### Core Audit Outcomes:
1. **Disputed-Key Canonicalization Repaired (Finding A007-01):**
   - *Vulnerability:* The original FC-006 notebook compared raw `" APMC"` market strings from `diff_77_deep_analysis.csv` against canonicalized panel market strings (e.g. `'Noida APMC'` vs `'Noida'`), resulting in 0 matched keys. The reported "identical sensitivity metrics" was an artifact of identity mismatch, not evidence of zero effect.
   - *Repair:* Implemented `load_canonical_disputed_keys()` with fail-closed assertions. Verified that accepted market aliases transform 100.0% of the 77 raw market strings ($77/77$) into canonical names, yielding exactly 77 unique canonical discrepancy keys.
   - *Dual Sensitivity Scopes Defined:*
     - **Scope (a):** Row-level test origin/target filtering (`in_77_scope_a`).
     - **Scope (b):** Historical intervention excising disputed records from series history before computing baseline forecasts, with explicit origin/target eligibility policies.
2. **Claim-to-Artifact Reconciliation (Finding A007-02):**
   - Corrected all baseline scorecard metrics in the report and math records to match artifact CSVs (`scorecard_fold_x_tier.csv`, `scorecard_sensitivities.csv`).
   - Corrected the Drift $>2\%$ target-move skill 95% CI from reported `[0.0401, 0.0982]` to artifact CSV value `[0.0432, 0.0950]`.
3. **Series Reconciliation Narrative Corrected (Finding A007-03):**
   - Corrected narrative from "9 leaving / 5 entering / >=200 threshold" to verified manifest values: **6 leaving series** (-1,408 obs), **2 entering series** (+571 obs), **490 common series** (+3,192 obs), yielding a net gain of **+2,355 rows** ($384,887 \rightarrow 387,242$ rows $\le 2025-12-18$).
   - Documented actual threshold: $N \ge 60$ and coverage $\ge 0.30$ for Tier A; $N \ge 120$ and coverage $\ge 0.30$ for Tier B.
4. **MASE Withdrawn / Declared NOT COMPUTED (Finding A007-04):**
   - Confirmed baseline engine does not implement in-sample training-only naive scaling.
   - Renamed test-relative metric to **Skill vs Naive**; MASE is officially designated **NOT COMPUTED**.
5. **Scoring Path & Loop Equivalence Proven (Finding A007-05):**
   - Implemented `tests/test_fc006_audit.py` (10 tests, 100% pass) verifying exact float equivalence between modular functions (`src/baselines.py`) and optimized array operations across dense, irregular, missing-anchor, and seasonal tie-breaking fixtures.
   - Verified future price mutation, row insertion, and row deletion invariance (zero leakage).
6. **Scored-Series & LOW-N Accounting (Finding A007-06):**
   - Updated `evaluate_model_slice()` to report both eligible and scored origins/series.
   - Evaluated `low_n_flag` strictly on scored cases ($N_{\text{scored\_origins}} < 200$ or $N_{\text{scored\_series}} < 10$).
7. **Predictions Archive & Reproducibility (Finding A007-02 & Item 5):**
   - Flagged existing `baseline_predictions_sample.csv` (5,000 rows) as F1-only and insufficient for all-fold reproduction.
   - Updated notebook to export `baseline_predictions_all_folds.csv`, `canonical_disputed_keys_audit.csv`, and `exclusion_stage_counts.json`.
   - Designated the remote Kaggle kernel execution as **RERUN REQUIRED**.

---

## 2. Claim-to-Artifact Reconciliation Table

The table below reconciles all reported numbers from the original FC-006 completion text against the persisted artifact CSVs (`experiments/reports/scorecards/` and `experiments/outputs/FC006/`):

| Scope / Metric | Reported in FC-006 Prose | Artifact CSV / Manifest Value | Reconciliation Status | Notes |
| :--- | :---: | :---: | :---: | :--- |
| **Tier A Naive MAE** | 106.96 | 106.9554 | **RECONCILED** | Rounded in prose |
| **Tier A Naive RMSE** | 298.83 | 298.8337 | **RECONCILED** | Exact |
| **Tier A Naive MAPE** | 4.16% | 4.16% | **RECONCILED** | Exact |
| **Tier A Naive Median AE** | 40.00 | 40.0 | **RECONCILED** | Exact |
| **Tier A Naive Share $\le 5\%$** | 76.76% | 76.76% | **RECONCILED** | Exact |
| **Tier A Moving Average MAE** | 134.19 | 134.1925 | **RECONCILED** | Exact |
| **Tier A Moving Average RMSE** | 321.46 | **333.3659** | **CORRECTED** | Discrepancy in prose; corrected to CSV |
| **Tier A Moving Average MAPE** | 5.25% | **5.08%** | **CORRECTED** | Discrepancy in prose; corrected to CSV |
| **Tier A Moving Average Median AE** | 61.29 | **50.7143** | **CORRECTED** | Discrepancy in prose; corrected to CSV |
| **Tier A Moving Average Share $\le 5\%$** | 67.86% | **70.98%** | **CORRECTED** | Discrepancy in prose; corrected to CSV |
| **Tier A Moving Average Skill** | -0.2547 | -0.2547 | **RECONCILED** | Exact |
| **Tier A Seasonal Naive MAE** | 774.38 | 774.3764 | **RECONCILED** | Exact |
| **Tier A Seasonal Naive RMSE** | 1297.86 | **1433.7629** | **CORRECTED** | Discrepancy in prose; corrected to CSV |
| **Tier A Seasonal Naive MAPE** | 32.74% | **29.45%** | **CORRECTED** | Discrepancy in prose; corrected to CSV |
| **Tier A Seasonal Naive Median AE** | 468.00 | **375.0** | **CORRECTED** | Discrepancy in prose; corrected to CSV |
| **Tier A Seasonal Naive Share $\le 5\%$** | 18.06% | **22.70%** | **CORRECTED** | Discrepancy in prose; corrected to CSV |
| **Tier A Seasonal Naive Skill** | -6.3738 | -6.3738 | **RECONCILED** | Exact |
| **Tier A Drift MAE** | 107.32 | 107.3248 | **RECONCILED** | Exact |
| **Tier A Drift RMSE** | 300.56 | **303.6659** | **CORRECTED** | Discrepancy in prose; corrected to CSV |
| **Tier A Drift MAPE** | 4.18% | **4.29%** | **CORRECTED** | Discrepancy in prose; corrected to CSV |
| **Tier A Drift Median AE** | 40.00 | **42.0** | **CORRECTED** | Discrepancy in prose; corrected to CSV |
| **Tier A Drift Share $\le 5\%$** | 76.73% | **76.55%** | **CORRECTED** | Discrepancy in prose; corrected to CSV |
| **Tier A Drift Paired Skill** | -0.0034 | **-0.0068** | **CORRECTED** | Prose reported unweighted; CSV is paired ratio |
| **Tier A Drift 95% Skill CI** | Unreported | [-0.0303, 0.0191] | **RECORDED** | From artifact CSV |
| **Drift Target Move $>2\%$ MAE** | 202.10 | 202.1012 | **RECONCILED** | Exact |
| **Drift Target Move $>2\%$ Skill** | +0.0695 | +0.0695 | **RECONCILED** | Exact |
| **Drift Target Move $>2\%$ 95% CI** | [0.0401, 0.0982] | **[0.0432, 0.0950]** | **CORRECTED** | Discrepancy in prose; corrected to CSV |
| **Tier A Leaving Series Count** | 9 | **6** | **CORRECTED** | Aligned with diagnostic JSON |
| **Tier A Entering Series Count** | 5 | **2** | **CORRECTED** | Aligned with diagnostic JSON |
| **Tier A Common Series Count** | Unreported | **490** | **RECORDED** | $496 - 6 + 2 = 492$ |
| **Tier A Net Observation Delta** | +244 | **+2,355** | **CORRECTED** | +244 was Excel match gain; +2,355 is Tier A obs |
| **Tier A Eligibility Threshold** | $\ge 200$ obs | **$\ge 60$ obs & cov $\ge 0.30$** | **CORRECTED** | Aligned with notebook code |
| **77 Disputed Keys Sensitivity** | Identical | **SUPERSEDED** | **CHANGES REQ** | Raw APMC mismatch; RERUN REQUIRED |

---

## 3. Forensic Analysis of Disputed-Key Canonicalization (Finding A007-01)

### The Identification Vulnerability
In Task MP-DATA-005, discrepancies between the Agmarknet Excel reports and historical downloads were compiled into `diff_77_deep_analysis.csv`. Because these observations originated from modern Agmarknet feeds (Feb–Mar 2026), all 77 rows carried raw market strings with `" APMC"` suffixes (e.g. `Noida APMC`, `Kanpur(Grain) APMC`, `Lucknow APMC`).

In Task MP-FC-006, the baselines notebook constructed `set_77_keys` directly from `diff_77_deep_analysis.csv["Market"]` without applying canonicalization:
```python
# Vulnerable code in FC-006 notebook:
set_77_keys = set(zip(
    df_diff_77["District_Std"].str.strip(),
    df_diff_77["Market"].str.strip(), # Raw APMC strings!
    ...
))
```
However, the evaluated series instances in `df_origins` were derived from `df_v2["Market"]`, which had already been canonicalized by `data_pipeline.py` into canonical anchors (e.g. `Noida`, `Kanpur(Grain)`, `Lucknow`).

Consequently:
$$\mathtt{key\_origin} = (\mathtt{'Ghaziabad'}, \mathtt{'Noida'}, \mathtt{'Onion'}, \mathtt{'Other'}, \mathtt{'FAQ'}, \mathtt{'2026-03-25'}) \notin \mathtt{set\_77\_keys}$$
Because `set_77_keys` contained `('Ghaziabad', 'Noida APMC', ...)`, the membership test was **identically False for all 64,776 origins**. The reported conclusion that "excluding the 77 disputed keys produces identical metrics" was completely artifactual.

### The Repair
1. **Module Implementation:** Added `load_canonical_disputed_keys()` to `src/baselines.py`.
2. **Fail-Closed Verification:**
   - Raises `FileNotFoundError` if the discrepancy file is absent.
   - Raises `ValueError` if required columns are missing.
   - Raises `ValueError` if row count $\ne 77$.
   - Applies `apply_market_canonicalization()` using accepted aliases.
   - Asserts that all 77 market names were transformed ($77/77$ raw APMC $\rightarrow$ canonical).
   - Asserts that exactly 77 unique canonical keys are produced.
3. **Dual Sensitivity Scopes:**
   - **Scope (a) - Row Masking:** Excludes test instances where the origin date key or the target date key is in `set_77_canon_keys`.
   - **Scope (b) - Historical Excising:** Excises disputed observations from the series history before calculating MA and Drift baselines, and excludes test instances where origin or target is disputed.

---

## 4. Scoring Path Equivalence & Anti-Leakage Verification (Finding A007-05)

A comprehensive test suite was authored in `tests/test_fc006_audit.py` to verify:
1. **Dense Daily Fixture Equivalence:** Across 500 days of daily data, `predict_series_vectorized()` and modular functions in `src/baselines.py` match with exact float equality ($< 10^{-12}$ difference) for Naive, MA, Seasonal Naive, Drift, and Target price/date/exact flag.
2. **Irregular Fixture Equivalence:** Across intermittent time series with multi-day gaps, weekends, and abstentions, vectorized array indexing exactly reproduces the modular functions.
3. **Deterministic Tie-Breaking:** Both implementations strictly break distance ties to the earlier calendar date in both seasonal and target windows.
4. **Future Invariance (Anti-Leakage Audit):**
   - Modifying price at $t+10$: zero effect on predictions at $t$.
   - Inserting row at $t+15$: zero effect on predictions at $t$.
   - Deleting row at $t+12$: zero effect on predictions at $t$.
5. **Temporal Boundary Enforcement:**
   - Evaluated origins strictly obey the 7-day embargo ($T_{\text{train}}+1 .. T_{\text{train}}+7$ excluded).
   - Evaluated targets strictly respect fold boundary ($t_{\text{target}} \le \text{fold\_end}$).
6. **Scored-Series & LOW-N:**
   - `evaluate_model_slice()` correctly reports eligible origins/series and scored origins/series.
   - `low_n_flag` triggers if $N_{\text{scored\_origins}} < 200$ or $N_{\text{scored\_series}} < 10$.
7. **Cluster Bootstrap Determinism:**
   - Unique series clusters are sorted deterministically prior to index sampling, guaranteeing exact reproducibility under seed 42 regardless of row ordering.
   - Safe division handles zero naive error without runtime errors.

Test Receipt:
```text
tests/test_baselines.py ........                                         [ 44%]
tests/test_fc006_audit.py ..........                                     [100%]
============================== 18 passed in 0.25s ==============================
```

---

## 5. Causal Wording and Lookahead Limitations (Findings A007-07, A007-08, A007-09)

1. **Retrospective Selection Lookahead:**
   - In Panel v2 construction, market alias acceptance rules and the $<20$ observation threshold were evaluated using the full 5-year dataset.
   - This represents retrospective data harmonization. In prospective live deployment (Release 1 live advisory), alias mappings and eligibility must be fixed strictly as of the forecast issuance timestamp.
2. **Median Price Ratios & Statutory Units:**
   - The commodity median price ratio post vs pre-March 2026 is 1.0000.
   - While this is consistent with no unit scaling change, it does not constitute independent statutory proof of units without official portal documentation.
3. **Variety Consolidation:**
   - Variety consolidation (reporting varieties falling from ~85 to ~35-40) is empirically correlated with the monthly row count drop. Causal attribution remains an external hypothesis.
4. **Retrospective Subgroup Qualification:**
   - The $>2\%$ target move subset ($N = 27,858$ origins) where Drift outperforms Naive (+0.0695 skill) is defined retrospectively by realization. It serves as a diagnostic benchmark, but cannot select live models at prediction time.

---

## 6. Execution Status & Next Actions

- **Local Repairs:** **COMPLETE**.
  - `src/baselines.py` updated with fail-closed disputed keys loader, scored-case evaluation, and vectorized predictor.
  - `tests/test_fc006_audit.py` authored and 100% passing.
  - `experiments/notebooks/mp_fc_006_baselines.ipynb` updated with canonical disputed keys, dual sensitivity scopes, and full predictions archive export.
  - `experiments/reports/mp_fc_006_summary.md` and `documentation/MODEL_AND_MATH_VALIDATION.md` corrected and reconciled.
- **Kaggle Baseline Scorecard:** **RERUN REQUIRED**.
  - A remote Kaggle kernel rerun is required to execute the updated notebook and regenerate `scorecard_sensitivities.csv`, `canonical_disputed_keys_audit.csv`, and `exclusion_stage_counts.json`.
  - Staging of scorecard CSVs without a verified remote run is strictly avoided per push rules.
