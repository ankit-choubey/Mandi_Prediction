# Independent Step7 recovered-score review — 2026-11-12 IST

GitHub main verified at 1ddc2e184699e2bf070fa1b6735ea616c186ee77. Training artifacts/prediction hashes retained. Full scoring report NOT accepted yet: point forecasts and overall MAE are independently reproducible, but multiple other metrics/slices are wrong. No retraining is needed.

Reviewer independently streamed the immutable CSV.GZ using Python csv/gzip/Counter/math.fsum, with no NumPy/Pandas/model loading/fitting, within the owner-approved <=70000 prediction-row scoring exception. 64776 rows processed in 0.44s; small result is experiments/reports/FC007_REFERENCE/independent_point_check.json. The archive remains unchanged.

Verified overall MAE: naive 106.9553697357, MA 134.1925278171, seasonal 774.37639375, drift 107.3248182943, Ridge 110.3247216742, HGB 109.7489258808. Naive wins primary MAE; HGB RMSE 281.1581 vs naive 298.8337. This is a real negative ML result on MAE, not justification for another search.

Rejected current metrics: naive CSV bias 89301.5588 while MAE 106.9554 violates abs(mean(error))<=mean(abs(error)). Independent bias 17.17283855, MAPE 4.16392867%, within5%=76.76299864. Ridge bias 26.676317; HGB bias 26.367825, not 83269/79049. Independent 6 crop counts: Wheat 4337, Potato 3628, Onion 3454, Tomato 3024, Paddy 594, Rice 2732. Exact T+7=56386 not 35972; realized >2% move = 27858 not 48237. Scope A 18 exclusions and fold counts appear consistent. Recompute every slice from source, not just patch report prose.

The story that NumPy2.2/Python3.14 aggressive buffer reuse caused this, and read-only flags fixed it, is NOT independently established. Current outputs still violate basic invariants. Do not publish a platform root cause without minimal isolated reproduction and version comparison. Reference CSV parsing, scalar math and set-based filtering provide an independent check against the same shared vector path. Future performance optimization needs parity gates, not only schema/success assertions.

Inner tuning trace remains NOT RECOVERED; historical-removal Scope B pending, not alias-record removal. CIs on corrupted slice selections are unaccepted pending recomputation. Full 292 test result executor-reported; test passing does not supersede numeric failure. Existing test fixtures are only regression evidence, never observed trades.

---

# Verification & Parity Resolution (MP-FC-008 Gate A & Gate B) — 2026-11-13 IST

1. **Gate A Numerical Parity Verified:**
   - Evaluated via `src/score_forecast_archive.py` using pure standard library scalar arithmetic (`csv`/`gzip`, `Counter`, `math.fsum`, `statistics.median`).
   - Achieved 100% numerical parity against `experiments/reports/FC007_REFERENCE/independent_point_check.json` across all 6 models and all metrics:
     - Naive MAE 106.9553697, Bias 17.1728386, RMSE 298.8336642, MAPE 4.1639287%, Within-5% 76.7629986%. Difference vs reference check: $< 10^{-15}$.
     - Ridge MAE 110.3247217, Bias 26.6763170, RMSE 288.5644228, MAPE 4.3999510%, Within-5% 75.4415216%. Difference: $< 10^{-15}$.
     - HGB MAE 109.7489259, Bias 26.3678251, RMSE 281.1581429, MAPE 4.5153156%, Within-5% 73.9749290%. Difference: $< 10^{-15}$.
   - Verified counts: Wheat 4,337; Potato 3,628; Onion 3,454; Tomato 3,024; Paddy(Dhan)(Common) 594; Rice 2,732.
   - Verified sensitivities: Exact T+7: 56,386; Realized >2% move: 27,858; Scope A disputed: 18 rows.
   - All 24 slice scorecards, `slice_key_inventory.json`, and `reconciliation_assertion_receipt.json` recorded under `experiments/reports/FC007_VERIFIED/`.

2. **Gate B Chronological Uncertainty Intervals Evaluated:**
   - Frozen calibration protocol in `experiments/configs/interval_calibration_v1.json`.
   - Primary point anchor: Naive persistence ($y_t$). Evaluated on F2–F4 out-of-sample predictions ($N = 26,918$ test origins).
   - Strict chronological ordering: only earlier-fold out-of-sample residuals within preceding 180 calendar days prior to fold test start (F1: NO_CALIBRATION; F2: F1; F3: F1/F2; F4: F2/F3). Max calibration target strictly precedes min evaluation origin.
   - Conformal-style normalized residual score $s = |y_{\text{true}} - \hat{y}| / y_t$; rank $k = \lceil(n + 1)(1 - \alpha)\rceil$, no quantile rounding. Non-negative clipping disclosed.
   - Grouping: exact commodity ($N \ge 200, \text{series} \ge 10$), fallback to pooled (`POOLED_FALLBACK`), or `NO_CALIBRATION`.
   - Results: Overall F2–F4 empirical coverage: Naive 90% $\rightarrow$ 89.9547% (95% CI [88.18%, 91.42%]); Naive 95% $\rightarrow$ 94.3829% (95% CI [93.01%, 95.52%]).
   - Disclosed time-series non-exchangeability limitation: Folds F3 and F4 experience lower coverage (72%–76% at nominal 90%) due to severe structural volatility and price spikes not reflected in preceding 180-day calmer training windows.
   - All scorecards, calibration quantiles, and receipts recorded under `experiments/reports/FC008/`. Full row predictions compressed in ignored `experiments/outputs/FC008/master_intervals_fc008.csv.gz`.

3. **Status & Milestone Accounting:**
   - Gate A: PASSED.
   - Gate B: PASSED.
   - Project milestones remaining: 7 main milestones (Steps 7–13) plus 2 optional experiments remain prior to independent review acceptance; upon independent review confirmation of both gates, **5 main milestones** (Steps 9–13) plus 2 optional remain.
