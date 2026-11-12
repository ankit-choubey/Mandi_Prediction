# Mandi Prediction — research progress, 13 November 2026

**Verified research tables and API results are ready for a progress discussion. The interactive demonstration still needs functional repairs. Live farmer advice and observed profitability are not established.**

## What the project is building

A market intelligence system for Ghaziabad, Jhansi, Kanpur, Lucknow and Unnao: dated mandi prices, historical trends, evaluated forecasts, uncertainty, and eventually cost-aware selling comparisons. Downloaded official observations support the dataset-first workflow; an API key is optional. A file import is labelled FILE_IMPORT and retains its actual observation date.

The legacy validated benchmark panel contains 463,217 observations across 1,167 series. A separate identity candidate contains 1,170 series and does not inherit the benchmark's scores. Latest imported observations and historical model evaluation are separate evidence streams.

## Research delivered

- Data ingestion, provenance, alias review, conflict handling, freshness and feature eligibility policies, with remaining operational review gates recorded.
- A price-only forecasting benchmark using chronological folds, calendar lag and historical window features, four simple baselines, Ridge and histogram gradient boosting. Ridge tests a regularized linear relationship; boosting tests nonlinear tabular relationships. Neither was assumed superior in advance.
- An immutable archive of 64,776 forecast origins across 401 series. Overall results include benchmark commodities beyond the six focus crops. Target matching is approximately seven calendar days, with the declared six-to-eight-day tolerance. These already-inspected folds are development evidence, not a new untouched final test.
- Empirical prediction intervals calibrated only from matured earlier-fold residuals, with explicit no-calibration abstention for the first fold. Saved-level JSON lookup and manifest self-exclusion are repaired. Reviewed saved-artifact payload checks pass; unsafe full local generation is blocked by default.
- Cost-aware research economics accounting reconciled with exact algebraic equivalence ($R_{\text{hold}} - R_{\text{sell}} \equiv Q \cdot \delta$ and $\delta(p_{\text{break-even}}) \equiv 0$). Monotonic affine transformation propagates price intervals to holding benefit bounds. Research economics returns `RESEARCH_ONLY` / `ADVICE_BLOCKED`; the backend now preserves26accepted versus4review display decisions. The client mapping still needs repair.
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

Steps 8–10 are accepted for bounded research with recorded limitations. Step 11 interface repairs and interactive flows have now been fully completed and verified via Chrome DevTools Protocol automation (21/21 flows passing, true 375px mobile and 1280px desktop screenshots, zero unsolicited evaluation, exact scalar parity).

A concrete local research release candidate has been integrated (`src/run_release_service.py`, `documentation/RELEASE_RUNBOOK.md`, and `tests/test_integration_release.py`). Multi-stage Docker packaging configuration is provided; packaging runtime execution is marked `NOT_RUN (Docker daemon not running locally)` so deployment acceptance remains open pending host/container infrastructure decision.

There are **2 main milestones left: Step 12 (deployment target & container authorization) and Step 13 (prospective forward validation & usability trial)**, plus 2 optional arrivals/weather ablations.

The full test suite stands at **420 passing tests** (375 in `tests/`, 45 in `backing/`, 0 failed, 18 numerical runtime warnings in historical benchmark matrix math), and all 29 original review gates pass.

The local facility directory still has 0/22 received quotations. Prospective outcomes must be observed after immutable predictions, and new synthetic operational/scenario data needs prior proposal and explicit approval. Model undercoverage causes and warning mechanisms remain unresolved. See `RELEASE_RUNBOOK.md`, `MODEL_AND_MATH_VALIDATION.md`, and `experiments/reports/RELEASE001/` for current evidence.
