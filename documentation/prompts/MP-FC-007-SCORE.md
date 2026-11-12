# MP-FC-007-SCORE — recover completed training and score saved predictions

Read the owner's standing/push rules, documentation/FC007_RECOVERY_STATUS.md, the original Step 7 protocol, execution ledger, mathematical record and local brain/context.md. GitHub main was independently checked at 2b0bca984d562cc54edb342711332424c3e70098. Check actual local and remote HEAD before work. Preserve all pre-existing uncommitted benchmark/notebook changes and untracked files; do not overwrite concurrent work or broadly stage the repository.

## Objective and authorization

The latest Kaggle run trained all four folds and saved predictions and eight models. It failed afterward with NameError: List is not defined during scorecard function definition. DO NOT REPEAT TRAINING. No model fitting, tuning, kernel push, upload, installation, synthetic generation, credential change, scheduler activation or parallel-lane expansion is authorized here.

Explicit owner approval is required for this narrow local exception: score at most 70,000 rows from the saved real prediction archive, at most 50 MB decoded CSV, at most 512 MB memory, at most 10 minutes total, and at most 30 seconds per stage. All ordinary limits remain for raw datasets and other operations. No raw historical panel read. Without that approval, prepare the reporting-only entrypoint and stop before full scoring. Existing isolated test fixtures remain test evidence only.

## 1. Recover and verify existing evidence

Artifacts were downloaded into ignored experiments/outputs/FC007_recovery/. The nested experiments/outputs/FC007/ directory contains master_predictions_fc007.csv.gz and .parquet. The models/ directory contains Ridge and HGB artifacts for F1–F4. recovery_download_manifest.json records paths, sizes and hashes.

Verify these immutable archive hashes before use:
- CSV.GZ: a61b38328e011b2ed75dd5d814fbf697d624ac948c50a198d374bfcaff2b9970
- Parquet: cc813dbd73c2631df646cc32f1ff2e86079b087bb1fcf3fb198d2e1d41e084d7

Score stored predictions without loading model weights. Do not deserialize incompatible or unverified joblib files. Recover the executed source/config from small output files or the executed notebook if needed; current uncommitted source is not automatically the executed version. Download only relevant small evidence. Record the exact kernel version when verified; otherwise mark it NOT VERIFIED.

Validate actual prediction rows against the logged total 64,776 and fold counts F1 37,858; F2 23,490; F3 1,413; F4 2,015. Check unique fold/full-series/origin keys, Tier B as a subset of Tier A, date-based regimes, target boundaries, finite observed prices and explicit prediction abstentions. Do not delete difficult rows.

Inner tuning scores or manifests may not have been persisted before the crash. Recover only actual saved/logged values. Mark missing evidence NOT RECOVERED; do not fabricate it, infer it from test scores, or rerun tuning. Clearly limit subsequent acceptance if traceability is incomplete.

## 2. Test the complete reporting path before full scoring

Create a standalone reporting entrypoint such as src/score_forecast_archive.py with an explicit --predictions argument. It must never call fit, train, tune or upstream notebook training cells. Correct typing imports or postpone annotation evaluation.

Execute every reporting function definition, every table writer, the assertion receipt, output manifest and readback on a bounded slice of EXISTING real predictions in a temporary directory. Include empty/all-abstained slices, missing naive pairs, zero-error denominators, overlapping tier membership, regime boundaries and canonical 77-key matching. Check exact output schema and required fields. This preflight must catch late NameError/KeyError/serialization failures before the full archive is processed.

Use shared audited metric definitions and efficient series-level error/count preaggregation. Stable series order, seed 42, 1,000 cluster resamples. Keep unpaired point MAE and paired MAE separate when samples differ; confidence intervals must match their estimator. Undefined skill remains undefined. Export numeric confidence bounds, eligible/scored origins and series, paired naive MAE, coverage, abstention, LOW-N, MAE, RMSE, bias, median AE, MAPE with its valid denominator, within-5% share and paired skill. Historical metric confidence intervals are not forecast prediction intervals.

## 3. Score once and checkpoint each completed table

Only after approval and successful miniature reporting, parse CSV.GZ with existing pandas/gzip under the exception bounds. No new PyArrow dependency is needed. Use stage watchdogs; exceeding limits stops with a checkpoint and diagnostic, never silently truncates.

Produce all required fold-by-tier, fold-by-focus-crop, overall-tier, crop, district and date-regime tables for both candidate models and four stored baselines. The six focus crops remain Wheat, Potato, Onion, Tomato, Paddy(Dhan)(Common), Rice. Retain empty slices with LOW-N and undefined metrics.

Sensitivities: exact T+7, retrospective >2% realized movement, and Scope A exclusion by the exact canonical six-part disputed keys. Never substitute an accepted-market list. Historical-removal Scope B requires actual recomputed forecasts; if those columns are absent, report PENDING rather than claim it is implemented or retrain.

Write tables atomically as they complete to experiments/reports/FC007_RECOVERED/. Checkpoint using prediction archive hash, scorer hash and configuration hash. Reuse matching completed outputs. Independently reconcile metric sums, paired denominators, masks and counts against the archive. Generate report numbers from tables; do not hand-type alternative CIs. Underperformance against naive is a valid outcome, not a reason for another search.

Retain full predictions and weights under ignored outputs. Commit only small scorecards, receipts and manifests. Do not issue an ALL GATES PASSED receipt for checks not executed. Mark retrospective development evidence, missing tuning traces and remaining release limitations explicitly.

## 4. Prevent this failure pattern in later steps

Add documentation/FORECAST_BENCHMARK_RUNBOOK.md with these mandatory gates:
- Execute a complete miniature path through prediction, scoring, serialization, manifest and readback before expensive work. When fitting is needed in a future authorized task, its tiny fit belongs in the authorized remote smoke stage.
- Persist feature/target/baseline caches, tuning scores, selected configuration, fold models, predictions and assertion receipts immediately after their stages complete.
- Separate training and reporting commands, so reporting failures never require retraining.
- Reuse checkpoints only when input/code/config/runtime hashes match.
- Record stage timing, row throughput, memory and hard deadlines. Stop early on correctness or scaling failures without pretending partial results are complete.

Observed timing: first tuning 2,977.7 seconds; four final fits total 14.4 seconds. Cache preparation is a likely cause of the first-stage delay, not independently profiled proof. Record this accurately. Prepare optimized vectorized date/rolling/baseline lookup with equivalence tests if needed, but do not rerun completed training merely for speed. A GPU does not fix a missing reporting import or automatically accelerate the existing CPU tree implementation.

Regression tests must verify that scoring cannot call fit, all function definitions execute, required columns fail early, all output types serialize, archive bytes remain unchanged and resume requires matching hashes. Run targeted tests and one final full fixture suite within ordinary limits. No empirical fitting locally.

## 5. Records, allowed changes, push and stop

Allowed: src/score_forecast_archive.py; narrow scoring-only fixes to src/forecast_benchmark.py; tests/test_score_forecast_archive.py; necessary tests/test_forecast_benchmark.py regressions; small experiments/reports/FC007_RECOVERED/ artifacts; experiments/reports/mp_fc_007_recovery_summary.md; documentation/FC007_RECOVERY_STATUS.md; documentation/FORECAST_BENCHMARK_RUNBOOK.md; documentation/MODEL_AND_MATH_VALIDATION.md; documentation/PROJECT_EXECUTION_LEDGER.md; documentation/prompts/MP-FC-007-SCORE.md. Minimal notebook reporting/checkpoint fixes only if clearly separable from concurrent changes. Do not overwrite another agent's generator or stage unrelated work.

Update only ignored brain/context.md, never documentation/context.md. Do not commit raw panels, full predictions, model weights, credentials or generated snapshots. Verify staged allowlist, completed secret-safe scan, scoped whitespace and ignore rules. Normal commit/push per standing branch rules; no force push or merge. Commit: fix(eval): recover saved benchmark predictions without retraining [MP-FC-007-SCORE]. Verify GitHub main before work and the exact resulting SHA after push.

Return CURRENT STEP / ACHIEVED / OPEN / NEXT / MAIN STEPS LEFT / OPTIONAL EXPERIMENTS LEFT. Step 7 remains open until independent review; seven main steps plus two optional remain, and accepted Step 7 leaves six plus two. Include authorization used, kernel evidence, recovered hashes, actual row/fold counts, report preflight and full-scoring receipts, model-versus-naive CIs/coverage, missing evidence, timing, test commands/counts/exits, changed paths, commit/push outcome and MASTER FILE UPDATE. STOP. No Kaggle training or push.
