# Mandi Prediction — research progress, 13 November 2026

**Ready for a research progress presentation, with explicit limitations. A completed live farmer advisory or proven profitable storage system has not been established.**

## What the project is building

A market intelligence system for Ghaziabad, Jhansi, Kanpur, Lucknow and Unnao: dated mandi prices, historical trends, evaluated forecasts, uncertainty, and eventually cost-aware selling comparisons. Downloaded official observations support the dataset-first workflow; an API key is optional. A file import is labelled FILE_IMPORT and retains its actual observation date.

The legacy validated benchmark panel contains 463,217 observations across 1,167 series. A separate identity candidate contains 1,170 series and does not inherit the benchmark's scores. Latest imported observations and historical model evaluation are separate evidence streams.

## Research delivered

- Data ingestion, provenance, alias review, conflict handling, freshness and feature eligibility policies, with remaining operational review gates recorded.
- A price-only forecasting benchmark using chronological folds, calendar lag and historical window features, four simple baselines, Ridge and histogram gradient boosting. Ridge tests a regularized linear relationship; boosting tests nonlinear tabular relationships. Neither was assumed superior in advance.
- An immutable archive of 64,776 forecast origins across 401 series. Overall results include benchmark commodities beyond the six focus crops. Target matching is approximately seven calendar days, with the declared six-to-eight-day tolerance. These already-inspected folds are development evidence, not a new untouched final test.
- Empirical prediction intervals calibrated only from matured earlier-fold residuals, with explicit no-calibration abstention for the first fold. Saved-level JSON lookup and manifest self-exclusion are repaired. Envelope identity/time/quantile validation remains incomplete under adversarial checks.
- Cost-aware research economics accounting reconciled with exact algebraic equivalence ($R_{\text{hold}} - R_{\text{sell}} \equiv Q \cdot \delta$ and $\delta(p_{\text{break-even}}) \equiv 0$). Monotonic affine transformation propagates price intervals to holding benefit bounds. Strict capability safety gating keeps advisory status `RESEARCH_ONLY` / `ADVICE_BLOCKED`.
- Audit of the local directory of 22 UP facilities: 0/22 rate amounts are recorded and all quotations are marked Not received. Empirical policy backtest is honestly designated `NOT_EVALUATED_NO_APPROVED_COST_PROFILE`, avoiding fabricated profit claims. Zero synthetic operational data generated.

## Results to show

| Method | MAE, INR/quintal | RMSE, INR/quintal | Interpretation |
|---|---:|---:|---|
| Persistence: current price as forecast | 106.96 | 298.83 | Best primary MAE on the verified benchmark |
| Histogram gradient boosting | 109.75 | 281.16 | MAE 2.61% worse; RMSE 5.91% lower |
| Ridge | 110.32 | 288.56 | MAE 3.15% worse |

MAE = mean absolute forecast error. RMSE gives more weight to large errors. Both should be shown: the model ranking depends on the loss being measured. Persistence has 76.76% of evaluated forecasts within 5% of the observed target price; this is a specific measured tolerance rate, not general “model accuracy.”

For intervals, normalized past errors are `abs(observed - predicted) / origin_price`. The chosen ordered residual has rank `ceil((n + 1) * nominal_level)`; its scale is multiplied by the origin price. This is retrospective chronological residual calibration. Time dependence and changing populations prevent a blanket distribution-free coverage guarantee.

| Evaluation population | Observed coverage at nominal 90% | At nominal 95% |
|---|---:|---:|
| All issued F2–F4 origins, n = 26,918 | 89.95% | 94.38% |
| F3, n = 1,413 | 75.94% | 84.08% |
| F4, n = 2,015 | 72.26% | 83.97% |

Mean interval widths are 662.65 and 977.14 INR/quintal, respectively. Near-target pooled coverage hides recent undercoverage; F2 supplies 87.27% of issued observations. The recent failure is a research finding. Its cause is unresolved. Do not claim that widening intervals after seeing these outcomes validates the same development test again.

## What this evidence supports

The project demonstrates a real data workflow, reproducible headline benchmark results, a defensible baseline comparison, and a measured uncertainty limitation. A negative ML result is scientifically useful: persistence remains the reference until a candidate improves the declared primary loss on comparable cases.

Independent review reproduced 246 calibration quantiles and 24 model/level/fold-or-overall interval summaries in approximately 0.63 seconds using saved predictions. That is evaluation time, not training time or a measured live-service latency. Suitable compute and avoiding unnecessary retraining make review faster without changing methods.

## What remains

Step 7 is accepted for retrospective development with its recorded limitations. Step 8 numerical evaluation, calibration envelope validation, and manifest repairs are verified. Step 9 canonical research economics, uncertainty propagation, and fail-closed capability safety gating are verified. Step 10 dataset-first backend service, WSGI adapter, loopback launcher, and OpenAPI specification are delivered and verified under MP-APP-001A.

There are **3 main milestones left: interface & reporting (11), production safety & integration deployment (12), and prospective validation & usability (13)**; plus 2 optional arrivals/weather ablations.

No approved complete local commercial cost profile is recorded. The 0/22 quote count describes the inspected directory, not all UP tariff availability. Synthetic operational/scenario data still requires a proposal and explicit owner approval. Empirical profit is NOT_EVALUATED; conditional calculator results are not observed profits. Future forecasts must be logged before outcomes for prospective validation. A professor can review current research, while live farmer advisory remains strictly blocked.

The test suite stands at **390 passing tests across bounded full batches**: 345 in `tests/` (10.06s, 18 numerical matmul warnings in benchmark tuning) and 45 in `backing/` (5.13s, 0 warnings). Service latency measured under loopback smoke achieved median warm latency < 0.25 ms across endpoints (0.196 ms for health, 0.215 ms for latest prices, 0.203 ms for research economics).

See `API_SERVICE_CONTRACT.md`, `MODEL_AND_MATH_VALIDATION.md`, and `experiments/reports/APP001A/` for complete verification evidence. The project is presentable as research progress, with baseline comparisons, uncertainty limitations, and capability gating shown explicitly.
