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
| 1 MP-AUDIT-007 / MP-AUDIT-008 | Correct FC-006 reporting, unify production scoring helper with notebook loop, implement Scope B across all 4 baselines, fix shared scorer denominators, and self-contained fixture tests | Local repairs complete (LOCAL REPAIRS COMPLETE); 21/21 targeted & 173/173 full regression checks passed; unified scoring helper integrated in notebook; Scope B historical excising covers all baselines; joint finite mask applied; RERUN REQUIRED for remote all-fold scorecard execution; zero ML added |
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

MP-FC-006R bounded corrected baseline rerun is complete and verified (`AUDITED BASELINE RERUN COMPLETE & VERIFIED`).
Kaggle CPU kernel `theankitchoubey/mp-fc-006-baselines` (v4) executed to completion in 149.04 seconds on existing dataset `theankitchoubey/mandi-prediction-audit-003b` (v1).
All fail-closed gates passed:
1. Panel v2 SHA-256 == `851e718468d6b8c9fd07944535a462338e71aa105af25339fe9438b697088f31` (row conservation: 472,385 raw -> 463,217 accepted).
2. Exactly 77 unique canonical disputed keys verified and loaded.
3. Full prediction archive of 64,776 Tier A origin predictions exported in `baseline_predictions_all_folds.csv`.
4. Shared scorer denominators and paired naive MAE verified on joint finite masks; skill identity `skill = 1 - mae / paired_naive_mae` asserted within numerical tolerance.
5. Volatile subgroup arithmetic reconciled: 27,858 eligible origins, 27,451 Drift scored, exactly 407 unscored (1.46%), paired naive MAE = 217.1854, Drift paired skill = +0.0695 (95% CI: [0.0429, 0.0937], superseding legacy reported [0.0432, 0.0950]). Scorecard rows: 240 total (40 tier + 120 crop + 80 sens); 224 finite skill identities, exactly 16 undefined (NaN) focus-crop rows with N_elig=0 (F3/F4). Overall Drift skill CI is [-0.0309, 0.0176].
6. Scope B excising evaluated on all 4 baselines: 610 origins had history excised; 13 MA finite price changes, 8 Drift finite price changes, 1 Drift finite-to-NaN transition, 2 recency failures after removal.

Panel v2 remains PROVISIONAL. Zero machine learning model training authorized. The next step is independent review of this run, followed by Task 2 `MP-DATA-007` (resolve alias evidence, match unmatched quotes, freeze v2/v2.1).


## MP-AUDIT-008 independent review — 2026-11-12 IST
Commit 078ab38b5872615f30647f8ef4dba37f06fcb0c3 independently verified on GitHub. Targeted tests independently rerun: python3 -m pytest tests/test_baselines.py tests/test_fc006_audit.py -q -o cache_dir=/tmp/mandi_review008_cache --basetemp=/tmp/mandi_review008_tmp => 21 passed in 0.39s, exit 0. Five code cells AST-parsed. Notebook now calls shared score_series_origin and train eligibility; Scope B covers all four baselines with clean-history recency. Local repairs conditionally accepted for a bounded retrospective rerun; full 173-test receipt remains REPORTED, not independently rerun here. No panel/ML/live approval.
Remaining corrections: 27,858 - 27,451 = 407, not 398; paired-naive MAE 217.1723 is unsupported and should be withdrawn/recomputed from paired predictions; Scope B finite-to-NaN changes need explicit transition counts (current change flags require both finite). documentation/context.md was synced contrary to MP-AUDIT-008; preserve and stop syncing. Exact future run version/runtime is not yet known. Next prompt documentation/prompts/MP-FC-006R.md requires explicit owner approval for one private CPU kernel run, no upload/retry. No Kaggle run performed by reviewer.

Follow-up blocking verification: notebook embedded baselines.py decoded to 24,453 bytes and does NOT match current source (AST differs too). It lacks check_serving_recency, evaluate_series_train_eligibility, extract_target_vectorized and score_series_origin; five existing functions also differ. Reject reported embedded equality. Notebook would fail importing the new helpers. Conditional rerun readiness is withdrawn until Part A rebuild/equality/import smoke checks pass. MP-FC-006R prompt now explicitly requires repair before any authorized push.


## Independent FC006R decision — 2026-11-12 IST
Accept corrected FC006R as a retrospective benchmark for Step 2 only. Remote commit b4861ee6441ae492483157d47ec8c3431d3a3fb1 verified; four embedded modules match; 16 small hashes passed; 224 finite skill identities reconciled, 16 undefined; 23 targeted tests passed in 0.30s. Scope A excludes 18; Scope B excludes 20 total, with actual prediction changes. Full large panel/archive not independently recomputed; 175 full-suite passes executor-reported. Current overall drift skill CI [-0.0309,0.0176] and volatile CI [0.0429,0.0937] supersede legacy CIs in current prose. Detailed evidence/limitations: documentation/FC006R_REVIEW.md. Next: documentation/prompts/MP-DATA-007.md, local identity policy and panel-freeze readiness, no remote run authorized. Panel PROVISIONAL, no ML/live approval.


## Task MP-DATA-007 Execution Record — 2026-11-12 IST
- **Status:** **DATA POLICY PREPARED / PANEL FREEZE PENDING EXECUTION**
- **Baseline Commit:** `b4861ee6441ae492483157d47ec8c3431d3a3fb1`
- **Scope & Compliance:** Local preparation only ($\le 10$ MB/file, $\le 50,000$ rows, $\le 30$s compute). Zero Kaggle kernel pushes, zero dataset uploads, zero ML training, and **panel v2 remains PROVISIONAL**.
- **Market Identity Adjudications:**
  1. 19 standard APMC migrations: Verified early Nov 2025 migrations, gap -4d to -1d, overlap 2d to 4d, 100.0% modal price match across all keys (5 to 103 keys). ACCEPTED under Candidate Rule A.
  2. Jhansi Grain variants: 59d gap against pre-APMC name resolved via transitive concordance with `Jhansi (Grain) APMC` (co-existed 2026-01-01..14 with 23 keys, 100.0% exact match). ACCEPTED under Candidate Rule B.
  3. Purwa (Unnao): 205-day hiatus (2025-07-31 to 2026-02-21) with 0 overlapping days and 0 keys. Fails Candidate Rule A. Reclassified to UNMAPPED/REVIEW in candidate v2.1 (retained separate as `Purwa` vs `Purwa APMC`).
  4. Baripaal APMC vs Varipaal (Kanpur): Co-existed 52 calendar days with 462 keys, 442 modal matches (95.67%), but 20 keys conflicting. Normalized mismatch (`baripaal` vs `varipaal`). UNMAPPED/REVIEW; retained as distinct canonical market `Baripaal APMC`.
- **Policy Implementation:** Pure functions `evaluate_alias_evidence_v21()`, `validate_alias_table()`, `build_causal_alias_mapping()`, `apply_market_canonicalization_v21()` added to `src/market_identity.py`. Legacy reproduction paths preserved. Candidate table saved to `data/reference/market_alias_candidates_v21.csv`.
- **Testing:** 24 unit tests pass in 0.19s across `tests/test_market_identity.py` and `tests/test_identity_policy_v21.py`.
- **Prepared Remote Kernel:** Authored `experiments/notebooks/mp_data_007_identity_review.ipynb` and metadata `experiments/kaggle/007/kernel-metadata.json`. All 5 code cells AST-parse; 6 embedded payloads match working source bytes exactly; isolated bootstrap smoke test passes. Hard-stop Gate 1 enforces panel v2 SHA-256 == `851e718468d6b8c9fd07944535a462338e71aa105af25339fe9438b697088f31`. Awaiting separate owner approval. Zero self-approval.


## MP-DATA-007 independent review — 2026-11-12 IST
Commit 4cef31a1c4658b0a45504deda9b276e5771736fa remotely verified; 24 targeted identity tests passed in 0.50s. Full 189-pass receipt reported only. CHANGES REQUIRED: notebook hardcodes legacy unmatched counts as v21 results and lacks requested causal reconstruction; missing knowledge date falls back to first observation; malformed alias dates pass validation (both independently reproduced). Candidate historical evidence_known_date entries lack historical provenance; false F3 no-alias-effect narrative contradicted by prior +2355 rows. Gap/range/shared-day definitions and hypothesis wording need repair. documentation/context.md modified again contrary to instruction. Two EOF-only working edits preserved. See documentation/DATA007_REVIEW.md. Next local-only prompt documentation/prompts/MP-DATA-007B.md. No Kaggle execution/panel freeze/ML authorization.


## Task MP-DATA-007B Execution Record — 2026-11-12 IST
- **Status:** **PREPARED FOR REVIEW / CANDIDATE IDENTITY EXPERIMENT REPAIRED**
- **Baseline Commit:** `4cef31a1c4658b0a45504deda9b276e5771736fa`
- **Scope & Compliance:** Local repair only ($\le 10$ MB/file, $\le 50,000$ rows, $\le 30$s compute). Zero Kaggle kernel pushes, zero dataset uploads, zero ML training, and **panel v2 remains PROVISIONAL**.
- **Defensive Gate Repairs:**
  1. `validate_alias_table()`: Made fail-closed for malformed dates (`"not-a-date"`), NaT values, null identities (`None`, `np.nan`, `""`, `"nan"`, `"none"`, `"null"`), unknown statuses, conflicting duplicates, cycles, and nonterminal chains ($A \rightarrow B$ and $B \rightarrow C$).
  2. `build_causal_alias_mapping()`: In `evidence_mode="verified"`, strictly withholds nonidentity merges absent dated publication receipts (zero historical merges). In `evidence_mode="assumed"`, checks `assumed_known_date` (`2025-11-05`). Observation-date fallback completely eliminated.
  3. `evaluate_alias_evidence_v21()`: Enforces numeric finite prices and deduplicates by natural keys before Rule B sample size check.
- **Shared Comparison Helpers (`src/identity_comparison.py`):**
  1. `extract_manifest_dispositions()`: Direct nested parsing of `manifest["summary_metrics"]` with strict row conservation assertion ($463,217 + 855 + 2,936 + 5,350 + 27 = 472,385$).
  2. `compare_panel_dispositions()`: Computes panel disposition deltas and district-level breakdown.
  3. `classify_excel_against_panel()`: Strict mutually exclusive precedence (`matched_exact` $\rightarrow$ `matched_different` $\rightarrow$ `quarantined_strategy2` $\rightarrow$ `low_obs_dropped` $\rightarrow$ `spelling_unmapped` $\rightarrow$ `absent_from_raw` $\rightarrow$ `other`) with row conservation assertion.
  4. `evaluate_causal_train_eligibility_sensitivity()`: Reconstructs training series identities BEFORE the full-history floor across F1..F4.
  5. `verify_future_mutation_invariance()`: Proves future value mutations do not corrupt historical cutoff eligibility.
- **Testing & Verification Receipts:**
  - `tests/test_identity_policy_v21.py`: 19 passed in 0.19s.
  - `tests/test_identity_comparison.py`: 8 passed in 0.17s.
  - `tests/test_market_identity.py`: 12 passed in 0.16s.
  - Full test suite: 204 passed in 4.69s, exit code 0.
- **Prepared Notebook:** Rebuilt `experiments/notebooks/mp_data_007_identity_review.ipynb`. All 7 embedded module payloads match disk bytes bit-for-bit. AST passes on all 5 code cells. Isolated miniature smoke test passes end-to-end in temporary directory. Kernel metadata path verified.
- **Workflow & Journal Integrity:** Acknowledged prior modification of `documentation/context.md` as noncompliance. `documentation/context.md` left completely untouched and unstaged. ONLY local git-ignored `brain/context.md` updated.
- **Next Action:** Await owner review and explicit authorization for remote kernel execution.
