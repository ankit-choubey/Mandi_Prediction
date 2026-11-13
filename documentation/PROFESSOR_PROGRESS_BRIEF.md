# Mandi Prediction — research progress, 13 November 2026

**Independent review update:** 424softwaretests pass. Model/fold table and final economics control are correct, but the new displayed break-even equation and waterfall require the bounded repairs in UI002_INDEPENDENT_REVIEW.md before presenting their derivation. UI002 producer report coverage claims50.81%and56.41/45.47/50.81areincorrect;verifiedoverall89.95%,F2/F3/F4=92.32/75.94/72.26. The finalStep13tools/protocol can be completed now;futuremarketperformanceandparticipantusabilityremainpendingactualevidence. ReadPROJECT_FEATURES_AND_SCORECARD.mdforcompletecapabilitiesandmetrics.

**The research web interface has been elevated into a professor-ready Agricultural Price Research Instrument with verified tables, zero external dependencies, accessible zero-origin charts, and 10-step economic waterfall controls. Portable deployment, live farmer advice and observed profitability are not established.**

## What the project is building

A market intelligence system for Ghaziabad, Jhansi, Kanpur, Lucknow and Unnao: dated mandi prices, historical trends, evaluated forecasts, uncertainty, and eventually cost-aware selling comparisons. Downloaded official observations support the dataset-first workflow; an API key is optional. A file import is labelled FILE_IMPORT and retains its actual observation date.

The legacy validated benchmark panel contains 463,217 observations across 1,167 series. A separate identity candidate contains 1,170 series and does not inherit the benchmark's scores. Latest imported observations and historical model evaluation are separate evidence streams.

## Research delivered

- Data ingestion, provenance, alias review, conflict handling, freshness and feature eligibility policies, with remaining operational review gates recorded.
- A price-only forecasting benchmark using chronological folds, calendar lag and historical window features, four simple baselines, Ridge and histogram gradient boosting. Ridge tests a regularized linear relationship; boosting tests nonlinear tabular relationships. Neither was assumed superior in advance.
- An immutable archive of 64,776 forecast origins across 401 series. Overall results include benchmark commodities beyond the six focus crops. Target matching is approximately seven calendar days, with the declared six-to-eight-day tolerance. These already-inspected folds are development evidence, not a new untouched final test.
- Empirical prediction intervals calibrated only from matured earlier-fold residuals, with explicit no-calibration abstention for the first fold. Saved-level JSON lookup and manifest self-exclusion are repaired. Reviewed saved-artifact payload checks pass; unsafe full local generation is blocked by default.
- Cost-aware research economics accounting reconciled with exact algebraic equivalence ($R_{\text{hold}} - R_{\text{sell}} \equiv Q \cdot \delta$ and $\delta(p_{\text{break-even}}) \equiv 0$). Monotonic affine transformation propagates price intervals to holding benefit bounds. Research economics returns `RESEARCH_ONLY` / `ADVICE_BLOCKED`; the backend now preserves26accepted versus4review display decisions. The reviewed client mapping and calculator flows now work.
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

**Step 11's research interface is accepted and elevated into an Agricultural Price Research Instrument (MP-UI-002), and MP-FINAL-013 closes all independent review findings.**
- **Distinctive Scientific Instrument Aesthetic:** Replaced generic corporate admin templates with a calm editorial field notebook / statistical report design system (warm paper canvas `#fcfbf8`, deep ink `#1a1c1e`, restrained crop green `#235834`, turmeric `#b36605`, soil rust `#883a21`). Zero external npm/CDN dependencies (100% vanilla HTML5/CSS3/ES6+, total payload 120.98 KB).
- **Epistemic Order of Legibility:** Strict 6-layer layout: (1) what was actually observed; (2) trustworthiness and freshness; (3) frozen retrospective benchmark achievements; (4) uncertainty across folds; (5) user-entered hold-versus-sell economics; and (6) scientifically unproven / fail-closed boundaries.
- **Truth-Preserving Price Movement & Negative Formatting:** A single observation truthfully displays `Price change unavailable — a second verified observation is required.` Negative price changes explicitly prepend a minus sign (`− ₹ X.XX (−X.XX%)`).
- **Audited Benchmarks & Uncertainty:** Accessible zero-origin horizontal bar charts (0–300 INR/q scale) for Naive MAE 106.96, HGB MAE 109.75 / RMSE 281.16, and Ridge MAE 110.32. Prominent 90% target reference line contrasting with 50.81% realized coverage, alongside explicit F2/F3/F4 fold cards and undercoverage disclosures.
- **Authoritative 10-Step Waterfall Economics:** Arithmetic breakdown table connecting Gross Spot Value through Net Hold Benefit evaluated authoritatively on the server in `src/economic_model.py`. Preserves blank-vs-zero semantics (`Unavailable (Missing Cost)`). Corrected break-even equation signs: $P^* = \frac{P_0(1+f) + c + (1-L)t_l - t_n}{(1-L)(1-d)}$ verified with nonzero fees ($t_n=10, t_l=20 \implies P^* = 2,611.84$).
- **Live Drawer Provenance Hashes & Timestamp Separation:** Live computed SHA-256 digests (`45c9dd75...` and `3d3bc047...`) displayed dynamically in Reproducibility Drawer, reverting to `Unavailable` in degraded mode. Temporal metadata explicitly separated into dataset import time, server runtime time, and IST observation date.
- **Multi-Viewport & Print Parity:** Headless Chromium browser verification across viewports (Desktop 1440x900, Desktop 1280x800, Mobile 375x667) confirmed zero horizontal overflow. Print preview hides interactive widgets while retaining selected series identity and verified observation card.
- **Step 13 Prospective Validation & Usability Protocol Frozen:**
  - Frozen protocol `APMC-PV-2026-V1` (`documentation/FORWARD_VALIDATION_PROTOCOL.md` and `experiments/configs/forward_validation_protocol_v1.json`).
  - Standard-library append-only shadow CLI (`src/prospective_shadow.py`) with SHA-256 chaining and file locking; tested in `tests/test_prospective_shadow.py` (**6/6 passed**). Real snapshot smoke run honestly recorded 9 staleness abstentions and 2 review abstentions with 0 fabricated forecasts. Disposed as `ENGINEERING_COMPLETE_EMPIRICAL_PENDING`.
  - Usability study protocol (`documentation/USABILITY_STUDY_PROTOCOL.md`) with 6 evaluator tasks and Brooke (1996) SUS framework. Evaluator technical rehearsal passed in $< 20$s per task without errors. Disposed as `TECHNICAL_REHEARSAL_COMPLETE_FIELD_TRIAL_PENDING`.
  - Feature inventory & model comparison scorecard (`documentation/PROJECT_FEATURES_AND_SCORECARD.md`) documenting model selection trade-offs, literature matrix with verified DOIs, and optional RAG extension.
- **Verification Matrix:** 17/17 final acceptance checks passed, 21/21 browser flow checks passed, 29/29 review gates passed, 385 passed in `tests/`, 45 passed in `backing/`, 16 passed in clean checkout serving suite. **Total: 508 passed, 0 failures, 18 numerical warnings preserved**.
- **Milestone Dispositions:** Exactly **0 engineering milestones** remain. Step 13 prospective validation is `ENGINEERING_COMPLETE_EMPIRICAL_PENDING`. Usability study is `TECHNICAL_REHEARSAL_COMPLETE_FIELD_TRIAL_PENDING`. Container packaging is `NOT_RUN` (local infrastructure decision). Exactly **2 optional ablations** remain (Arrivals, Weather).

Under task **MP-RELEASE-001R**, the Step 12 code, lifecycle, packaging assets, and test portability blockers were completely resolved:
- **Launcher Entrypoints & Shutdown:** Repaired dynamic root resolution so `python3 src/run_release_service.py --help` and `python3 -m src.run_release_service --help` both succeed under sanitized environments without `PYTHONPATH`. Resolved shutdown deadlock via asynchronous daemon thread dispatch, cleanly terminating `serve_forever()` within 0.55s on SIGTERM and releasing the socket for immediate rebinding.
- **Zero-Dependency Serving:** Added `from __future__ import annotations` and optional lazy NumPy handling in `src/economic_model.py`. Serving path verified with pure standard library under `python3 -S` (exit code 0).
- **True UTC Logging Parity:** Formatted all log entries using `time.gmtime` (`YYYY-MM-DDTHH:MM:SSZ`), verified within $<0.2$s of aware UTC reference.
- **Clean-Checkout Test Portability:** Refactored `tests/test_integration_release.py` with an isolated deterministic 30-series fixture (26 accepted, 4 review) and public `service.reload_index()`. In a genuine `git archive HEAD` clean export without private snapshots, tests passed 9/9 (1 optional smoke skipped).
- **Packaging Assets & Healthcheck Syntax:** Repaired healthcheck one-liner in `Dockerfile` to import `sys`. Added benchmark CSV copies. Configured `.dockerignore` minimal allowlist (43 files, 0.944 MB, well under 2 MB limit). Container execution status is recorded honestly as `NOT_RUN (Docker daemon not running locally)`.
- **Full Test Suite Status:** **424 passed** (379 tests/ in 11.07s with 18 preserved numerical warnings; 45 backing/ in 5.22s). Original 29 gates: 29/29 passed. Chrome CDP suite: 21/21 passed.

For a local demonstration, both root launcher `python3 run_service.py --host 127.0.0.1 --port 8000` and release launcher `python3 src/run_release_service.py --host 127.0.0.1 --port 8000` or `python3 -m src.run_release_service --host 127.0.0.1 --port 8000` are fully verified and operational.

The local directory still records 0/22 commercial quotations. Recent interval undercoverage and negative ML MAE skill remain findings; future accuracy/profitability is not established. Step 13 must log approved shadow predictions before real outcomes and score actual prices with correct maturity/units, not arrivals volume. New synthetic operational/scenario data requires prior proposal/approval. Minor labels describe 5.91% as RMSE reduction (quadratic penalty / variance reduction phrasing removed).
