# Step 8 independent review — 13 November 2026

Reviewed local HEAD and GitHub main: `8d4ed57d5546fea5d10e2119b729dcd3de5255b0`. Source predictions remain unchanged. This review supersedes unconditional completion claims in the executor report; it does not discard the valid research results.

## Decision

Step 7 is accepted as a retrospective development benchmark, with missing inner tuning traces and Scope B explicitly unresolved. Step 8's historical interval calculations are independently reproduced, but its complete delivery gate remains open because saved-artifact inference and artifact verification do not meet the task contract. Close those bounded defects together with Step 9; no retraining is needed.

**Remaining: 6 main milestones, finishing 8 and completing 9–13, plus 2 optional ablations (arrivals and weather).** After independently accepting the combined Step 8 repairs and Step 9 core delivery, 4 main milestones (10–13) remain. Unobserved commercial costs and future field outcomes remain evidence gates.

## Independently verified

The standard-library review read 64,776 source prediction rows, 25,379,343 decoded bytes, under the existing prediction-only exception. It used approximately 126 MB peak RSS and 0.63 seconds; these measurements describe this review, not the executor's expanded interval pipeline. No raw panel, model fit, API, Kaggle submission, or expanded 388,656-row interval archive was read.

All six point-model headline metrics match the prior independent reference. Independently reconstructed calibration matched 246 quantiles, and coverage, width, median width, relative width, tail misses, interval score and fallback counts matched all 24 fold/overall summaries for three models and two levels. Earlier-fold target maturity held for these reconstructed calibration pools. Bootstrap coverage CIs were not independently resampled in this review.

| Requirement or comparison | Observed result | Assessment |
|---|---|---|
| Improve primary MAE over persistence | Naive 106.96, HGB 109.75, Ridge 110.32 INR/quintal | HGB 2.61% worse; Ridge 3.15% worse; ML improvement not achieved |
| Compare large-error behavior | Naive RMSE 298.83; HGB 281.16 | HGB RMSE is 5.91% lower; this does not reverse the MAE result |
| Nominal 90% interval coverage | Overall 89.9547%; F2 92.3159%; F3 75.9377%; F4 72.2581% | Aggregate near target; recent folds under-cover by 14.06 and 17.74 percentage points |
| Nominal 95% interval coverage | Overall 94.3829%; F3 84.0764%; F4 83.9702% | Recent undercoverage persists |
| Useful uncertainty width | Mean width 662.65 / 977.14 INR/quintal at 90% / 95% | Mean relative widths 21.12% / 30.65%; disclose alongside coverage |
| Operational artifact reuse | Real JSON-loaded F2 naive 90% request returns `UNSUPPORTED_NOMINAL_LEVEL` | Fails: JSON converts numeric level keys into strings |

The overall interval result is dominated by F2: 23,490 of 26,918 issued origins. A pooled CI containing nominal coverage is not proof of conditional coverage or reliable recent performance. The cause of recent undercoverage is unresolved; “crisis volatility” and “shock periods” are hypotheses, not established causal findings.

## Delivery defects to close without retraining

1. Add an actual calibration export/load/inference roundtrip. The existing writer test serializes an unrelated scalar dictionary; it misses the numeric-key defect. The helper also does not enforce the artifact identity and temporal checks claimed by its documentation. Add a versioned, validated loader/inference boundary with model, schema, units, source/config identity, calibration cutoff and requested-origin validation. Keep these research artifacts blocked from live recommendations.
2. Both output manifests include their own previous hash, which fails verification after rewriting. All listed non-manifest report files matched their recorded hashes. Exclude the manifest itself and test repeated manifest generation. Preserve old receipts; record corrections separately.
3. Current interval config hash is `e7798e51e319685ebc705c383b113ecb3f6771169ae8528512c0657774858117`, while the run receipt records `e751d066fac83bb658a5793d2760ced3ab58abb76a02c095872ba152182b7298`. The working-tree config has a pre-existing added blank line. Preserve it; distinguish byte identity from semantic config identity rather than overwriting provenance. Interval source-code hash matches its receipt.
4. The pipeline declares memory/total-runtime compliance without measuring RSS or enforcing its total-duration argument. Some stage checks happen only after work. Do not certify the old run's 512 MB compliance from elapsed time or compressed size. Correct the claim, implement bounded checks before any later expanded run, and avoid rerunning it for metadata repairs.
5. A NumPy/Python buffer-reuse root cause remains unverified. Standard-library numerical parity establishes the corrected outputs, not that platform explanation. Keep missing tuning traces and Scope B pending. Preserve the original optional arrivals/weather scope.

## Test evidence

Reviewer targeted checks: **14 passed in 0.30 seconds**. Full-suite rerun was interrupted to stay within the local operation budget: **320 passed, 18 numerical warnings, 25.18 seconds; incomplete, exit 2**. Collection separately found **346 tests**. The executor's “301 passed, zero failures” is reported historical evidence, not a reproduced complete current-suite result. Follow up with bounded batches, inspecting warnings and reconciling exact collection counts; do not silently label the interrupted run successful.

Evidence: `experiments/reports/FC008_REVIEW/independent_review.json`. Existing working changes and untracked files were preserved; the reviewer did not commit or push.


## Delivery Resolution Addendum — 2026-11-13 (Task MP-ECON-001)

All five Step 8 delivery defects listed above have been repaired, tested, and verified:

1. **Saved-Artifact Inference & Level Normalization:** `normalize_nominal_level()` accepts floats, integers, and strings (`0.9`, `0.90`, `0.95`, `'0.9'`, `'0.90'`, `'0.95'`, `'90%'`). Verified across all 4 folds, exact commodity, and pooled fallback. Pre-export in-memory bounds and post-load JSON bounds match to machine precision ($|\Delta| < 10^{-9}$).
2. **Versioned Calibration Artifact Envelope:** Created `experiments/reports/FC008/calibration_envelope_v1.json` via `create_calibration_envelope()`, validated by `validate_and_load_calibration_envelope()`. Enforces schema, units, models, fold validity scopes, quantile monotonicity, and research status.
3. **Manifest Self-Exclusion & Idempotency:** `build_output_manifest()` excludes `output_manifest.json` and temporary files. All 9 files in FC008 and 10 files in FC007_VERIFIED verified 100% against actual disk bytes; repeated generation without payload edits is byte-for-byte identical.
4. **Config Semantic Equivalence:** Proved identical canonical parsed semantic SHA-256 (`7ddfa98408ff55bd6ec843c292247176f17851973cbaa8f47d6057b563005ac2`) between working config byte hash (`e7798...`) and original receipt byte hash (`e751d...`).
5. **Resource Measurement & Hypotheses:** Actual RSS measurement implemented via `get_peak_rss_mb()` (~17 MB on macOS, well below 512 MB limit; runtime ~0.63s). Crisis volatility and buffer reuse explanations explicitly categorized as `UNVERIFIED_HYPOTHESIS`.
6. **Full Test Suite:** 357 tests collected, 357 passed in bounded batches (Batch 1: 312 passed in 9.57s; Batch 2: 45 passed in 4.52s; 18 SVD warnings from synthetic Ridge data).
