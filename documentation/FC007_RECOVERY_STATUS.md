# Step7 current-run recovery — 2026-11-12 IST

Latest GitHub main independently checked via GitHub connector: 2b0bca984d562cc54edb342711332424c3e70098. Current local benchmark/notebook corrections remain uncommitted; preserve all work. Current Kaggle status queried directly: KernelWorkerStatus.ERROR. Retrieved ONLY latest log and saved model/prediction artifacts; no push, cancellation or training performed by reviewer.

The latest run is different from the earlier manifest failure. Log reaches all four outer folds and writes master_predictions_fc007.parquet (4088120bytes) plus csv.gz (4889882bytes), then fails in scorecard-cell function definition: NameError: name List is not defined, around3251s. Final log conversion ends3261s (~54.4min). No new modelling scorecard has been accepted.

Timing evidence: first inner tuning2977.7s (49.63min), outer fit3.7s; second tuning53.3s/fit3.9s; third41.7s/fit3.3s; fourth33.8s/fit3.5s. First tuning includes initial cache population; code still loops perorigin across histories and calls pandas baselines. Feature/cache preparation is the likely dominant bottleneck, not demonstrated by independent perfunction profiling. Final model fitting alone total14.4s, so switching GPU does not address the observed majority cost. No guarantee future elapsed runtime can be fixed independent of Kaggle queues/hardware.

Recovered into ignored experiments/outputs/FC007_recovery/: eight model files (Ridge/HGB x4folds), both prediction archives and latest log. recovery_download_manifest.json holds actual paths/byte sizes/SHA256. CSV.GZ hash a61b38328e011b2ed75dd5d814fbf697d624ac948c50a198d374bfcaff2b9970; Parquet cc813dbd73c2631df646cc32f1ff2e86079b087bb1fcf3fb198d2e1d41e084d7. Hashes were computed on <=10MB compressed/binary artifacts. Reviewer inspected only CSV header/first record, not allpredictionrows or deserializedmodels. Log fold counts37858+23490+1413+2015=64776; actual archive row count must be independently checked by scoring task. Do NOT discard saved training outputs or rerun tuning to fix missing import.

Next: MP-FC-007-SCORE, recovery/reporting only, requires owner explicit one-time local prediction-scoring exception above50000rows (max70000actual archivedpredictionrows,50MBdecodedCSV,512MBmemory,10min total,30sper stage). Original rawpanel limits unchanged; no refit/no fullpanel read/no Kagglepush. If permission absent, prepare scorer and stop. Missing inner-tuning scores/manifests not saved before crash must remain NOT RECOVERED, not fabricated/recomputed with new tuning. Audit recovered development predictions and identify remaining evidence before milestone acceptance.

Future reliability contract: execute full miniature path through scorecards/manifests/checkpoints before any expensive real workload; imports/functiondefinitions cannot be left unexecuted. Persist causalfeaturecache, tuningtrace, foldmodels+predictions and assertionreceipts as each stage finishes. Split training and scoring entrypoints; allow scoring from immutable existing predictions without recomputation. Stage telemetry/rowthroughput, hard deadlines and reuse matching checkpoints by input+code+config hashes. CPU/GPU chosen from observed bottleneck and genuine supported use, not merely enabled flag. Read GitHub main before dispatch and verify resulting pushed SHA after each report; during long jobs check on meaningful progress/finish/failure, not unsupported claim of unattended permanent monitoring.

Mainstepsleft7 (current7–13), optional2. No independent-lane launch yet. After accepted Step7,6main remain. Owner single-pass target cannot waive a failed integrity gate or authorize fabricated realtime/synthetic results.

---

## MP-FC-007-SCORE Recovery Execution Complete — 2026-11-12 IST
* **Task ID:** MP-FC-007-SCORE
* **Status:** COMPLETE (Zero Retraining; Standalone Scorer Executed Under Explicit Owner Exception)
* **Archive Hash Verification:** `master_predictions_fc007.csv.gz` SHA-256 `a61b38328e011b2ed75dd5d814fbf697d624ac948c50a198d374bfcaff2b9970` (100% verified).
* **Row Accounting:** Exactly 64,776 rows scored across all four outer folds (F1: 37,858; F2: 23,490; F3: 1,413; F4: 2,015). Tier B (62,932) is a strict subset of Tier A (64,776). Scope A 77-key matches: 18 rows.
* **Preflight & Timing:** Miniature reporting preflight passed in 0.02s. Full 24-slice scorecard evaluation with 1,000 series-cluster bootstrap resamples completed in 3.67 seconds using optimized vector groupby pre-aggregation.
* **Key Results:** Naive baseline MAE is 106.96 INR/q. HGB MAE is 109.75 (Skill -2.61%, 95% CI [-4.28%, -1.21%]); Ridge MAE is 110.32 (Skill -3.15%, 95% CI [-4.92%, -1.72%]). Naive baseline dominates candidate price-only ML models across historical mandi price panels.
* **Outputs:** 8 scorecards, reconciliation assertion receipt, and output manifest written atomically to `experiments/reports/FC007_RECOVERED/`. Runbook added to `documentation/FORECAST_BENCHMARK_RUNBOOK.md`. Summary report at `experiments/reports/mp_fc_007_recovery_summary.md`.
* **Missing Evidence:** Inner tuning scores trace across grids was not persisted before remote crash and is marked NOT RECOVERED.
* **Milestone Accounting:** Main steps left: 7 (current Step 7 remains open until independent review; accepted Step 7 leaves 6 main steps 8–13 + 2 optional).
