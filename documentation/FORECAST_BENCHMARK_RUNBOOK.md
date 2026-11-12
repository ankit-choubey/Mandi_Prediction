# Forecast Benchmark Runbook & Reliability Standard
**Task Reference:** MP-FC-007-SCORE / Step 7 Standard Operating Procedures
**Date:** 2026-11-12 IST
**Status:** ACTIVE

---

## 1. Context and Architectural Purpose

During the execution of Task MP-FC-007R (Kaggle kernel `theankitchoubey/mp-fc-007-price-models`, Version 2), all four outer folds (F1–F4) were fitted, serializing eight model binaries and full predictions (`master_predictions_fc007.parquet` [4,088,120 bytes] and `master_predictions_fc007.csv.gz` [4,889,882 bytes]). The run terminated prematurely at 3,251 seconds (~54 minutes) inside Cell 5 during scorecard function definition with `NameError: name 'List' is not defined`.

This failure demonstrated that **coupling model training and scorecard evaluation into a single monolithic script creates severe operational risk**: an import typo or reporting bug in the evaluation stage forces a choice between losing the run or conducting ad-hoc recovery.

This runbook establishes mandatory architectural and operational gates for all subsequent forecasting benchmarks (Steps 7–13).

---

## 2. Mandatory Reliability Gates

### Gate 1: Complete Miniature Reporting Preflight Before Long-Running Work
- Before initiating any remote training kernel or multi-minute execution, the full reporting pipeline—including all type annotations, function definitions, slice evaluators, table writers, assertion receipts, and manifest generators—must execute on a miniature fixture slice in a temporary directory.
- Preflight must explicitly test edge cases:
  1. Empty slices ($N = 0$).
  2. All-abstained slices (100% NaN predictions).
  3. Missing naive pairs ($y_{\text{naive}} = \text{NaN}$).
  4. Zero-denominator slices ($y_{\text{true}} = y_{\text{naive}}$, where skill is undefined/NaN).
- If model fitting is required in future authorized remote tasks, a tiny smoke test fitting 10 rows belongs in the preflight before the main search.

### Gate 2: Immediate Stage-by-Stage Persistence
- Feature, target, and baseline caches must be flushed to disk immediately upon generation.
- Inner hyperparameter tuning scores, evaluation metrics, and selected configurations must be written to disk immediately after each fold's tuning completes—never buffered in memory until end of job.
- Fold models and prediction chunks must be written immediately after outer evaluation.
- Outputs must be written atomically (`.tmp` write followed by atomic rename) to avoid corrupted or truncated files.

### Gate 3: Strict Decoupling of Training and Scoring Entrypoints
- Model training and prediction generation must run via dedicated CLI entrypoints (e.g., `src/forecast_benchmark.py`).
- Scorecard computation and reporting must run via dedicated standalone entrypoints (e.g., `src/score_forecast_archive.py`).
- Standalone scorers must **never import, define, or invoke** `fit()`, `train()`, `tune()`, or raw panel readers.
- Standalone scorers must accept pre-computed prediction archives (`--predictions <path>`) and output directories (`--output-dir <path>`).

### Gate 4: Cryptographic Checkpointing & Reuse
- Checkpoint reuse is strictly contingent on matching:
  - Input prediction archive SHA-256 digest.
  - Scoring code SHA-256 digest.
  - Configuration JSON SHA-256 digest.
- If hashes match, cached scorecards may be reloaded; if any hash mismatches, execution must re-score or report a diagnostic mismatch.

### Gate 5: Bounded Stage Watchdogs & Telemetry
- Every pipeline stage must enforce hard wall-clock timeouts and memory limits:
  - Archive load/hash stage: $\le 30$ seconds.
  - Preflight validation: $\le 30$ seconds.
  - Scorecard computation: $\le 30$ seconds per slice group.
  - Full execution: strictly within bounded task limits (e.g., $\le 10$ minutes total).
- Memory footprint must remain within strict bounds (e.g., $\le 512$ MB resident set size).
- Exceeding limits triggers immediate exit with diagnostic receipts, never silent data truncation.

---

## 3. Observed Performance Profile & Compute Strategy

### Empirical Kaggle Run Profile (Version 2)
| Stage | Observed Wall-Clock Duration | Row / Candidate Throughput | Dominant Operation |
|---|---|---|---|
| Panel V2 Ingestion & Hash | 12.2 s | 472,385 rows | Parquet read & SHA-256 check |
| Fold 1 Inner Tuning | 2,977.7 s (49.6 min) | 37,858 origins $\times$ 2 splits | Initial causal feature rolling cache population |
| Fold 1 Outer Fit & Predict | 3.7 s | 37,858 test rows | Ridge + HGB fitting |
| Fold 2 Inner Tuning | 53.3 s | 23,490 origins $\times$ 2 splits | Cached feature lookup |
| Fold 2 Outer Fit & Predict | 3.9 s | 23,490 test rows | Ridge + HGB fitting |
| Fold 3 Inner Tuning | 41.7 s | 1,413 origins $\times$ 2 splits | Cached feature lookup |
| Fold 3 Outer Fit & Predict | 3.3 s | 1,413 test rows | Ridge + HGB fitting |
| Fold 4 Inner Tuning | 33.8 s | 2,015 origins $\times$ 2 splits | Cached feature lookup |
| Fold 4 Outer Fit & Predict | 3.5 s | 2,015 test rows | Ridge + HGB fitting |
| **Total Model Fitting (All 4 Folds)** | **14.4 s** | 8 models | CPU Scikit-Learn |
| Cell 5 Function Definition | Crash at 3,251 s | N/A | Missing `List` import |

### Compute Architecture Decisions
1. **Dominant Bottleneck:** Initial feature cache population during Fold 1 inner tuning accounted for >91% of total job runtime (2,977.7s). Model fitting across all 4 folds took only 14.4 seconds combined.
2. **GPU Misconception:** Enabling a GPU accelerator does **not** address rolling feature dictionary lookups or pandas string parsing. Furthermore, standard `HistGradientBoostingRegressor` runs on CPU trees, and `Pipeline(StandardScaler, Ridge)` CPU execution completes in $<4$ seconds per fold. GPU selection must be based on genuine algorithmic acceleration (e.g., deep neural architectures, large batch PyTorch/JAX models), not as a palliative for un-profiled data preprocessing.
3. **Optimized Local Scoring:** Local vector-grouped series-cluster bootstrap computes 24 slice scorecards with 1,000 resamples each across 64,776 rows in **3.67 seconds** using pre-aggregated sums, complying with all local computation boundaries.

---

## 4. Standalone Scoring CLI Reference

```bash
# Score saved predictions without fitting or downloading raw panels
python3 src/score_forecast_archive.py \
    --predictions experiments/outputs/FC007_recovery/experiments/outputs/FC007/master_predictions_fc007.csv.gz \
    --output-dir experiments/reports/FC007_RECOVERED \
    --disputed-file data/reference/canonical_disputed_keys_77.csv \
    --max-rows 70000 \
    --timeout 600
```

### Verified Output Artifacts
- `scorecard_overall.csv`: Overall combined model evaluation vs naive baseline.
- `scorecard_folds.csv`: F1–F4 temporal holdout scorecards.
- `scorecard_tiers.csv`: Tier A and Tier B partition scorecards.
- `scorecard_crops.csv`: Focus crop breakdowns (Wheat, Potato, Onion, Tomato, Paddy, Rice).
- `scorecard_districts.csv`: Target district breakdowns (Ghaziabad, Jhansi, Kanpur, Lucknow, Unnao).
- `scorecard_regimes.csv`: Historical, Transition, and Modern date-based regime scorecards.
- `scorecard_sensitivities.csv`: T+7 exact, realized >2% move, and Scope A disputed exclusion.
- `master_scorecards_all.csv`: Concatenated master scorecard containing all 24 evaluation slices.
- `reconciliation_assertion_receipt.json`: Cryptographic and mathematical verification receipt.
- `output_manifest.json`: Checksum and size manifest of all produced reports.
