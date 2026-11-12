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
- Cost-aware research economics accounting reconciled with exact algebraic equivalence ($R_{\text{hold}} - R_{\text{sell}} \equiv Q \cdot \delta$ and $\delta(p_{\text{break-even}}) \equiv 0$). Monotonic affine transformation propagates price intervals to holding benefit bounds. Research economics returns `RESEARCH_ONLY` / `ADVICE_BLOCKED`; source-record capability forwarding in the backend still needs correction.
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

The numerical backend repair and responsive research interface are independently verified:
- **Three Boundary Closures Accepted:**
  1. Real source index dynamically derives 26 accepted eligible series (`price_display_permitted: true`) and isolates 4 unapproved market review series (`price_display_permitted: false`) into an amber review preview with withheld prices.
  2. Strict provenance validation rejects unsupported units (e.g. `INR/tonne`), invalid statuses (e.g. `NOT_A_VALID_STATUS`), and overflowing exponents (`1e999`) with HTTP 400. Missing costs leave dependent fields null while preserving explicit-zero inputs.
  3. Historical full generator pipeline raises `PermissionError: LOCAL_FULL_GENERATION_BLOCKED` before any stream decoding or I/O when unauthorized.
- **Step 11 Research Interface Delivered:**
  - Accessible, responsive UI built with pure standard-library vanilla JavaScript and CSS, adhering to calm agricultural aesthetics.
  - Verified across desktop (`1280x800`) and mobile (`375x667`) viewports using real Google Chrome headless automation. Screenshots saved in `experiments/reports/APP001B/screenshot_desktop_1280x800.png` and `experiments/reports/APP001B/screenshot_mobile_375x667.png`.
  - 100% exact scalar and formatted numeric parity confirmed between source CSVs, API envelopes, and rendered DOM elements (catalog inventory 30/26/4, MAE 106.96, RMSE 275.69, F2 92.32%, F3 75.94%, F4 72.26%, economics gross ₹25,000, holding ₹25,470, net gain +₹470.00, break-even ₹2,602.04).
- **Execution & Test Status:**
  - Original 29 executable review gates: **29/29 passed, exit 0**.
  - New boundary and parity verification: **41/41 checks passed, exit 0**.
  - Full test suite: **414 passed** (369 in `tests/` + 45 in `backing/`, 0 failures, 18 numerical runtime warnings).
  - Measured latencies: Full Python process startup `73.36 ms`; warm in-process WSGI handler execution `0.20`–`0.56 ms`.
- **Milestone Accounting:**
  - Steps 8, 9, 10, and 11 are completed and verified.
  - Exactly **2 main milestones remain**: Step 12 (Integration & Production Deployment Architecture) and Step 13 (Forward Prospective Validation & Usability Trial).
  - **2 optional ablations remain**: Arrivals Ablation and Weather Ablation.

The local quotation directory records 0/22 received rates. Commercial profitability and forward reliability remain research debt to be addressed in prospective trials. Future operational forecasts must be logged before outcomes; synthetic operational or scenario data requires prior proposal and approval. See `experiments/reports/APP001B/output_manifest.json` for verified evidence hashes.
