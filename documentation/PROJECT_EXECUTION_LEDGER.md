# Project execution ledger and delivery gates

Established 2026-11-12 (IST). Owner requested stepwise executor prompts, independent review, persistent local context, mathematical records, and realistic synthetic economics scenarios. This ledger records readiness; an implementation is not automatically an approved capability.

## Working agreement

- Execute one bounded task; return evidence; audit; then issue the next task. Future task briefs below are a roadmap, not authorization to run all tasks.
- Each task updates `documentation/MODEL_AND_MATH_VALIDATION.md`, this ledger, and local-only `brain/context.md`. The whole `/brain/` directory is already ignored; never force-add it.
- Every report gives baseline/resulting full commit hashes copied from output, changed paths, pre-existing work preserved, exact checks/commands/results, input/output hashes, limitations, and remaining review debt.
- Stage only named deliverables. Never use broad staging in this shared working tree. Exclude secrets, raw panels, `experiments/outputs/`, and the local journal. No destructive Git operations, installs, credential changes, uploads, or Kaggle pushes without the applicable owner authorization. Each task must state what authorization it uses; old one-kernel authorization does not automatically transfer to new work.
- Preserve raw inputs and all pre-existing modifications/untracked files. Local inspection: files <=10 MB, <=50,000 rows, operations <=30 seconds. Full-panel work and training run on Kaggle after authorization. A full test suite that exceeds these limits must be moved or split, not silently run locally.
- Before every push, run the full appropriate repository suite within resource limits, inspect staged paths/diff, and scan without printing secret values. A new failure blocks pushing. Capture remote push outcome and full SHA. No push was performed while establishing this ledger.
- Maintain OBSERVED / INFERRED / HYPOTHESIS and VERIFIED / REPORTED / NOT VERIFIED labels. Never improve a score by hiding abstentions, reducing difficult coverage, or tuning against held-out outcomes.

## Actual baseline

Local FC-006 HEAD: `7931caaf01ee9e53ea2f18b823d710b8c61851ff`, independently found on GitHub through the connector on 2026-11-12. Its parent is MP-DATA-006. FC-006 is implemented but its audit is **CHANGES REQUIRED**, not accepted for release. See `FC006_INDEPENDENT_AUDIT.md`.

Existing capabilities: validated historical-price pipeline; provisional canonical panel v2; CSV/Excel arrivals ingestion; forecasting baselines; earlier classification features/models/evaluation; economic equations and backtests; freshness/safety engine; operational reporting and fixture tests. Existing work in `backing/`, contributor folders, `results/`, and root reports must be reconciled before reuse. Those results are not automatically comparable to FC-006.

Not established: verified automated live ingestion, frozen model-ready panel, approved price ML benchmark, calibrated intervals, deployed API/UI, observed local commercial costs, or prospective field performance. No defensible completion percentage or fixed completion date has been established.

## Ordered task briefs and acceptance gates

| Order / ID | Executor brief | Required evidence before acceptance |
|---|---|---|
| 1 MP-AUDIT-007 | Correct FC-006 reporting, canonicalize disputed keys, audit actual notebook prediction paths, metric definitions, scored-series counts and historical availability | Local audit repairs complete; 10/10 regression checks passed; full claim table reconciled; 77-key canonicalization bug fixed; dual sensitivity scopes implemented; notebook prepared with RERUN REQUIRED for remote all-fold scorecard execution; zero ML added |
| 2 MP-DATA-007 | Resolve alias evidence (including Purwa gap, Jhansi variants, Baripaal), match unmatched quotes, freeze v2 or v2.1 | Explicit identity decisions, no fuzzy automatic merging, conservation, Market_Raw retained, unit/source limitations, input/output hashes; Kaggle rerun authorization if needed |
| 3 MP-SRC-004 | Implement/verify daily price API ingestion for all five districts | Archived response receipts, observation/retrieval separation, pagination and schema checks, source failures, no credentials in files/reports |
| 4 MP-SAFE-001 | Align price/forecast/economics trust gates, including delayed and future observations | Capability-specific policy; fixture tests for all paths; empirical freshness calibration pending if insufficient forward logs; simulated costs never become verified advice |
| 5 MP-OPS-001 | Capture immutable daily snapshots and operate scheduler | Owner-approved schedule/secrets setup, idempotency, revision history, hashes, failure/recovery exercise and data-lag logs |
| 6 MP-DATA-008 | Specify missing-data and serving eligibility policies | Seasonal gaps and reporting calendars; no invented observed prices; denominators for excluded/ineligible/no-target/model-abstained cases; train-only transformations |
| 7 MP-FC-007 | Build price-only lag features and benchmark small ML candidates | Same audited targets/folds/baseline; nested chronological tuning; unseen-series policy; matched-origin skill CIs; per-crop/regime results; complete prediction archive on Kaggle |
| 8 MP-FC-008 | Add intervals, calibration and abstention | Held-out calibration, coverage and width by regime/crop, calibration failure disclosure, coverage-versus-error tradeoff, drift monitoring rules |
| 9 MP-ECON-001 | Build bounded, realistic storage/transport/loss scenarios | Source-backed ranges where available; unsupported bounds labelled assumptions; correct units/horizon; seeded versioned scenarios; equations and break-even reconciliation; scenario sensitivity and downside results |
| 10 MP-APP-001A | Define and implement service/API contracts | Price/forecast/model/trust/version fields, stale/error handling, model compatibility checks, request-level traceability; no frontend claims exceeding service capability |
| 11 MP-APP-001B | Build usable farmer-facing interface | Market/crop selection, history, dated forecasts, intervals, explanations, explicit scenario economics, mobile and user-flow checks |
| 12 MP-RELEASE-001 | Integrate, deploy and test recovery/monitoring | End-to-end snapshots to display; deployment approval; freshness/schema/model alarms, rollback, latency measurement, runbook and evaluation report |
| 13 MP-FIELD-001 | Conduct forward-only shadow evaluation and usability research | Predictions logged before outcomes, declared evaluation window, losses/coverage, participant consent where needed, real feedback; sufficient evidence before actionable economic release |
| Optional MP-ARR-001 / MP-WX-001 | Test arrivals/weather additions separately after Release 1 benchmark | Source/unit/future-date issues resolved; actual publication availability; price-only versus added-feature ablation on matching cases; extra operational cost justified |

Dependencies: baseline/data audit precedes model approval; API and safety work precede claiming live operation; realistic economics simulation can be delivered without commercial quotations but remains a scenario capability. UI can show honest unavailable states. Full empirical economics remains conditional on actual cost evidence.

There are 13 planned delivery packages including the immediate correction audit, plus two optional ablations. Each may need a correction cycle. This is a planning breakdown, not a claim of 13 remaining coding sessions or an 8–14 week commitment.

## Model development rationale to record before training

- Current baselines: naive (persistence anchor); MA (recent smoothing); seasonal naive (annual repeatability check); damped drift (short trend extrapolation). Underperformance is a valid finding.
- Initial proposed ML candidates: regularized linear/ridge model for an interpretable lag baseline; a shallow decision-tree regressor for an interpretable nonlinear comparison; histogram gradient boosting for nonlinear tabular lag features. Candidate choice is provisional and subject to pinned-runtime support and compute limits. Add Random Forest only with a specific comparison hypothesis; do not begin with a large ensemble search.
- Price prediction uses a continuous target. Earlier favorable/normal/unfavorable classifiers answer a different question; any retained classification task needs separately defined labels, balanced metrics, probability calibration and an economic mapping validated independently. Do not use classification accuracy as price forecast accuracy.
- Consider predicting price change or return relative to y(t), reconstruct prices, and compare against direct-price training on inner validation only. Preserve positive prices and disclose any constraints.
- Record features, exact calendar versus observation lags, missing indicators, preprocessing fit cutoff, model/hyperparameters, tuning budget, seeds, runtime/library versions, hashes, temporal availability, training windows, target maturity, folds, losses, limitations, and acceptance decision.
- Existing 2025–2026 folds have already been inspected. They can be development benchmarks; they cannot become an untouched final test again. Reserve future outcomes prospectively or a genuinely uninspected dataset before making final generalization claims.

## Scorecards for every stage

No artificial all-purpose project score. Data: row conservation, invalid/conflict/unmatched shares, source coverage, alias review counts and lag. Forecasts: MAE/RMSE, median AE, bias, percentage metrics with explicit denominators, matched-origin skill and CIs, origin/series counts, eligibility/abstention/availability, crop/regime results. Intervals: empirical coverage, mean width, interval score. Operations: successful complete fetches / attempted fetches, lag, latency percentiles, failures and recovery. Economics: incremental net proceeds, break-even, downside and regret under explicitly named scenarios; distinguish predicted from realized outcomes. Usability: task completion and observed problems.

## Documentation ownership

`PROJECT_MASTER_SPECIFICATION.md`: intended scope. `MODEL_AND_MATH_VALIDATION.md`: definitions, model rationale, methods, results and adjudicated corrections. `DATA_SOURCE_REGISTER.md`: source evidence and units. This ledger: ordered tasks and readiness. Per-task audit reports: claim evidence. `brain/context.md`: local-only resumable state. When documents disagree, preserve the discrepancy and prefer inspectable code/artifacts for what ran; do not treat artifacts as proof of original-source truth.

## Current decision

MP-AUDIT-007 local repairs and claim reconciliation are complete (`LOCAL REPAIRS COMPLETE`). Remote all-fold baseline scorecard execution is flagged as `RERUN REQUIRED` (requiring separate bounded Kaggle kernel authorization). The next planned data task is Task 2 `MP-DATA-007` (resolve alias evidence, match unmatched quotes, freeze v2/v2.1) or an authorized remote rerun of `mp_fc_006_baselines.ipynb`. Do not train new ML models or claim corrected remote scores until rerun is executed and verified.
