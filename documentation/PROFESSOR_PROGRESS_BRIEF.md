# Mandi Prediction — research progress, 13 November 2026

**Ready for a research progress presentation, with explicit limitations. A completed live farmer advisory or proven profitable storage system has not been established.**

## What the project is building

A market intelligence system for Ghaziabad, Jhansi, Kanpur, Lucknow and Unnao: dated mandi prices, historical trends, evaluated forecasts, uncertainty, and eventually cost-aware selling comparisons. Downloaded official observations support the dataset-first workflow; an API key is optional. A file import is labelled FILE_IMPORT and retains its actual observation date.

The legacy validated benchmark panel contains 463,217 observations across 1,167 series. A separate identity candidate contains 1,170 series and does not inherit the benchmark's scores. Latest imported observations and historical model evaluation are separate evidence streams.

## Research delivered

- Data ingestion, provenance, alias review, conflict handling, freshness and feature eligibility policies, with remaining operational review gates recorded.
- A price-only forecasting benchmark using chronological folds, calendar lag and historical window features, four simple baselines, Ridge and histogram gradient boosting. Ridge tests a regularized linear relationship; boosting tests nonlinear tabular relationships. Neither was assumed superior in advance.
- An immutable archive of 64,776 forecast origins across 401 series. Overall results include benchmark commodities beyond the six focus crops. Target matching is approximately seven calendar days, with the declared six-to-eight-day tolerance. These already-inspected folds are development evidence, not a new untouched final test.
- Empirical prediction intervals calibrated only from matured earlier-fold residuals, with explicit no-calibration abstention for the first fold. Retrospective delivery defects repaired via a versioned calibration envelope (`calibration_envelope_v1.json`) and level-normalized inference helper.
- Cost-aware research economics accounting reconciled with exact algebraic equivalence ($R_{\text{hold}} - R_{\text{sell}} \equiv Q \cdot \delta$ and $\delta(p_{\text{break-even}}) \equiv 0$). Monotonic affine transformation propagates price intervals to holding benefit bounds. Strict capability safety gating keeps advisory status `RESEARCH_ONLY` / `ADVICE_BLOCKED`.
- Storage tariff audit of 22 UP commercial facilities: 0/22 published rates found online. Empirical policy backtest is honestly designated `NOT_EVALUATED_NO_APPROVED_COST_PROFILE`, avoiding fabricated profit claims. Zero synthetic operational data generated.

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

Step 7 is accepted for retrospective development with its recorded limitations. Step 8 artifact delivery defects are resolved. Step 9 core research economics, uncertainty propagation, and capability gating contracts are delivered.

Next come: backend architecture (10), interface/reporting (11), production safety & operational decision runbook (12), and final integration/briefing (13): **4 main milestones remain (Steps 10–13), plus 2 optional arrivals and weather ablations**.

No verified local commercial storage/transport feed exists (0/22 quotes in UP). Any generated economic scenario data needs an explicit proposal and owner approval; realistic synthetic values remain assumptions, not observed commercial costs. Future predictions must be logged before outcomes before claiming forward reliability. A professor can review the current research honestly; live advisory and final field validation remain blocked.

Full repository test suite now collects **357 tests, with 357 passing in bounded batches** (Batch 1: 312 passed in 9.57s, 18 numerical warnings from synthetic Ridge SVD; Batch 2: 45 passed in 4.52s; total ~14.1s). See `documentation/FC008_INDEPENDENT_REVIEW.md`, `documentation/MODEL_AND_MATH_VALIDATION.md`, and `documentation/RESEARCH_ECONOMICS_CONTRACT.md`.
