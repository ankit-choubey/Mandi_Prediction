# MP-FC-008 — verify all benchmark scores, then evaluate chronological prediction intervals

Read owner standing/push rules, documentation/FC007_SCORE_REVIEW.md, benchmark runbook, feature contract, mathematical record, ledger and brain/context.md. Expected HEAD: 1ddc2e184699e2bf070fa1b6735ea616c186ee77. Check GitHub main, local HEAD and status before work; preserve all existing changes. No destructive Git, broad staging, installs, model fitting/tuning, Kaggle push, raw-panel reads, API calls, scheduler activation or synthetic operational/training/scenario generation.

## Authorization and completion gates

Owner approval must explicitly extend the saved-prediction exception to scoring and calibration: at most 70,000 real archived rows, 50 MB decoded CSV, 512 MB memory, ten minutes total, thirty seconds per stage. No raw historical panel processing or model fitting. Without approval, prepare and test bounded existing samples, then stop.

Use the existing immutable CSV.GZ archive with SHA-256 a61b38328e011b2ed75dd5d814fbf697d624ac948c50a198d374bfcaff2b9970. No Kaggle/GPU session is needed for this arithmetic-only task. Preserve all earlier reports and archives.

This single task has TWO sequential gates: A, independently correct every Step 7 scorecard; B, complete honest Step 8 interval evaluation. Do not begin B until A passes. Seven main milestones plus two optional experiments remain now. If both gates pass independent review, five main milestones (9–13) plus two optional experiments remain. Do not decrement counts merely because code executed.

## A. Independently correct all numerical results

1. Implement a reference path using csv/gzip, Counter, tuple/set filtering, math.fsum and statistics. No NumPy/Pandas expressions in the reference path. Explicitly parse booleans: bool('False') is not an acceptable parser. Source rows remain immutable. Reference assertions are in experiments/reports/FC007_REFERENCE/independent_point_check.json; derive results from the archive before comparing, never copy asserted values into output.

Required counts: 64,776 total; folds 37,858 / 23,490 / 1,413 / 2,015. Wheat 4,337; Potato 3,628; Onion 3,454; Tomato 3,024; Paddy(Dhan)(Common) 594; Rice 2,732. Exact T+7 56,386; realized movement above 2% 27,858. Naive overall bias 17.1728385513, MAPE 4.1639286685%, within-5% 76.7629986415%. Overall MAE: naive 106.9553697357; MA 134.1925278171; seasonal 774.37639375; drift 107.3248182943; Ridge 110.3247216742; HGB 109.7489258808.

2. Find and repair the wrong selection/arithmetic path. Do not assert a NumPy/Python runtime root cause without an isolated reproduction and version comparison. Read-only array flags do not prove correctness. For EVERY overall, fold, tier, crop, district, date-regime and sensitivity slice, export its selected-key count/hash and independently verify all metrics against scalar reference calculations. Check |bias| <= MAE <= RMSE, disjoint counts, finite-value masks, valid percentage denominators, percentages within 0–100, and identical paired-skill origin sets. Do not fix only headline prose.

3. Recompute confidence intervals from VERIFIED per-series error/count aggregates. A deterministic stdlib random.Random(42) cluster bootstrap with 1,000 resamples is acceptable; declare its percentile interpolation and version. Compare selected resample calculations with direct scalar weighted sums. A changed RNG can change finite bootstrap quantiles; explain rather than force old CIs. Clearly separate unpaired MAE and paired MAE/skill when sample sets differ. Undefined denominators stay undefined. Preserve empty slices with LOW-N.

4. Execute the entire miniature report writer, manifest and readback before full scoring. Existing regression fixtures must assert actual numeric answers for constant signed error, cancelling signed errors, MAPE, false boolean values, missing naive, two distinct crops, empty/all-abstained cases and no input mutation. Schema-only tests are insufficient. Save trusted results under experiments/reports/FC007_VERIFIED/, with atomic checkpoints keyed by archive/code/config hashes. Supersede the old false ALL_GATES_PASSED receipt explicitly. Missing inner tuning traces remain NOT RECOVERED. Scope B remains pending unless actual counterfactual predictions were saved. No refitting to reconstruct missing traces.

## B. Chronological empirical prediction intervals

5. Primary point method: the prespecified naive persistence anchor, which wins verified MAE. Ridge/HGB intervals are exploratory and use only their stored predictions. No new point models or hyperparameter search. Freeze this calibration protocol before computing coverage:

- Nominal levels: 90% and 95%.
- At each outer-fold start, use only EARLIER-fold out-of-sample residuals whose actual target dates fall within the preceding 180 calendar days and strictly before the current fold test start.
- F1 has NO_PRIOR_CALIBRATION. F2 may use matured F1; F3 may use matured F1/F2; F4 may use matured F1/F2/F3.
- Assert disjoint origin keys and maximum calibration target date strictly before minimum evaluation origin date. Never calibrate a fold with its own outcomes. Original publication timestamps remain unknown; availability is a retrospective assumption.

6. For finite positive observed y_t, normalized score s = |y_true - y_hat| / y_t. For alpha = 1 - nominal_level, use rank k = ceil((n+1)*(1-alpha)) in sorted calibration scores, with no quantile rounding. If k > n, withhold. Half-width = q*y_t; lower = max(0, y_hat-half_width); upper = y_hat+half_width. Disclose nonnegative-support clipping. No winsorization or test-selected widths.

Group by model and exact commodity. Require at least 200 calibration origins and 10 distinct series. Otherwise use that model's pooled normalized calibration with the same minimums, explicitly labelled POOLED_FALLBACK. If still insufficient, abstain as NO_CALIBRATION. These are prespecified engineering choices, not validated universal thresholds. Report all grouping and fallback denominators.

This is conformal-style chronological residual calibration, NOT proof of IID/exchangeable or distribution-free time-series coverage. Common market shocks, regime shifts and changing fold-specific Ridge/HGB fits limit guarantees. Report empirical coverage only. Document the finite-sample quantile equation and assumptions with Angelopoulos/Bates: https://arxiv.org/abs/2107.07511 . Historical MAE confidence intervals are not future-price prediction intervals.

7. Evaluate fixed intervals on F2–F4 outcomes only after calibration is frozen. Report empirical coverage, deviation from nominal, mean/median/quantile widths, widths divided by y_t, lower/upper miss rates, and interval score: width plus 2/alpha times the amount below the lower endpoint or above the upper endpoint. Include eligible/issued/abstained origins and series, fallback share and LOW-N. Tables: fold/model/level, model/crop/level, district/date-regime and overall evaluated folds. Compute series-cluster bootstrap coverage CIs with 1,000 resamples on verified issued rows; disclose dependence limitations. Missing calibration is not perfect coverage. Do not tune thresholds after viewing test results. Realized >2% movement is descriptive only.

8. Implement src/forecast_intervals.py and frozen experiments/configs/interval_calibration_v1.json. Calibration artifacts include archive/code/config hashes, model/schema/response identifiers, units, calibration start/cutoff/max-target dates, group counts, quantiles, levels, fallback rules and limitations. Shared inference checks artifact/model identity, temporal cutoff, positive finite inputs and calibration availability. It cannot learn from the requested future target. Roundtrip export/load must reproduce intervals. Mutating future outcomes cannot change earlier calibration or intervals.

Forecast/advice gates remain separate: stale/review/unknown-grade/missing-history inputs remain blocked. One recent snapshot does not provide three observations in thirty days. Intervals do not authorize economics or live model deployment.

## C. Complete path, evidence, records and push

9. Test the ACTUAL scoring/calibration path, not a second implementation: no fit/train/tune calls; all function definitions execute; quantile rank/ties; no-calibration/all-fallback; zero-error widths; fold maturity; future mutation; identity separation; serialization and readback. Reuse existing isolated fixtures and bounded real samples. No new synthetic operational datasets. If gate A fails, stop before B; if a time/memory limit is reached, preserve checkpoints and report partial status honestly.

10. Execute A then B once after preflight and approval. Keep full interval rows and source predictions ignored under experiments/outputs/FC008/. Commit only small verified scorecards, manifests, assertions and calibration artifacts under experiments/reports/FC007_VERIFIED/ and experiments/reports/FC008/. Automatically compare every prose number with tables. Retain the source archive hash unchanged. Bad empirical coverage is a finding, not permission to leak outcomes or force passing scores.

11. Update experiments/reports/mp_fc_007_recovery_summary.md with superseded claims, create experiments/reports/mp_fc_008_summary.md, and update documentation/FC007_SCORE_REVIEW.md, mathematical record, benchmark runbook, feature contract and execution ledger. Update only ignored brain/context.md, never documentation/context.md. Preserve current code and review debt accurately.

Allowed changes: narrow metric/scorer fixes in src/forecast_benchmark.py and src/score_forecast_archive.py; src/forecast_intervals.py; tests/test_forecast_intervals.py; necessary metric regression tests; interval config; the small report/artifact paths above; documentation/prompts/MP-FC-008.md and listed review/record files. No raw data, full predictions, weights, credentials or unrelated work in commit.

Run meaningful targeted tests, then one final full fixture suite within ordinary limits. Capture commands/counts/exits, exact staged allowlist, completed secret-safe scan, scoped whitespace and ignore checks. Normal commit/push per standing rules, no force/merge. Commit: feat(uncertainty): verify benchmark scores and evaluate causal intervals [MP-FC-008]. Verify GitHub main before work and the actual resulting SHA after push.

Return CURRENT STEP / ACHIEVED / OPEN / NEXT / MAIN STEPS LEFT / OPTIONAL EXPERIMENTS LEFT; exact authorization used; independent numerical parity receipts; interval coverage/width/score and all denominators; timing, tests, hashes, superseded claims, missing tuning evidence and availability/dependence limitations. No self-approved release or profitability claim. STOP. Next is Step 9 economics, with any synthetic scenario generation still requiring prior explanation and explicit owner approval.
