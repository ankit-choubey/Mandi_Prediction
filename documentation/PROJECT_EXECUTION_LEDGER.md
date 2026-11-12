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


## MP-DATA-007B review and tonight priority — 2026-11-12 IST
Owner wants same quality with faster completion tonight, clear achieved/open/next after every report, and detailed prompts reducing repair cycles. Treat this as delivery priority, not authorization to fabricate evidence or skip checks; prospective field outcomes cannot be obtained before they occur. Batch reusable checks and final full-suite validation, focus integrated Release 1 plus labelled scenario economics. No claim all 13 packages+optional experiments will be validated tonight.
Commit a78f4a0995aabeb02d2510c35054e16e930d1fc4 remotely verified; independent 39 targeted tests passed in 0.67s. Full 204-pass receipt reported only. Partial repairs accepted, actual run not ready: classifier strips APMC and falsely matches reviewed Purwa names; TierA helper omits 30% coverage; notebook June cutoff/partial Excel discovery and absent disposition inputs; cutoff helper fed already-pruned panel; aggregate-only mutation checks. Independent small fixtures reproduced false Purwa match and sparse series erroneously accepted. See documentation/DATA007B_REVIEW.md.
Next prompt documentation/prompts/MP-DATA-007R.md combines exact repair tests with ONE conditional remote run requiring explicit owner approval. Preserve pre-existing EOF-only source/test edits and documentation/context.md untouched. Panel provisional, no ML/live approval.


## MP-DATA-007R Execution & Evidence Record — 2026-11-12 IST
- **Task ID:** `MP-DATA-007R`
- **Baseline Commit:** `a78f4a0995aabeb02d2510c35054e16e930d1fc4`
- **Authorized Execution:** Exactly ONE private Kaggle CPU kernel run on existing dataset `theankitchoubey/mandi-prediction-audit-003b` (v1) following pass of all Part A preflight checks.
- **Remote Kernel Run:** `theankitchoubey/mp-data-007-identity-review` (Version 1). Completed with status `KernelWorkerStatus.COMPLETE` in 1,017.4s (~16.9 min).
- **Gate 1 Reproduction:** Panel v2 SHA-256 == `851e718468d6b8c9fd07944535a462338e71aa105af25339fe9438b697088f31` strictly reproduced and verified. Row conservation identity verified ($472,385 = 463,217 + 855 + 2,936 + 5,350 + 27$).
- **Candidate Panel v2.1:** Computed candidate SHA-256 == `a299536914b5683613f7a0aa242e447f832a33894a476d73401e49fa24449c14`. Dispositions match row counts of v2; unique series increase by +3 (1,167 $\to$ 1,170) in Unnao due to keeping Purwa APMC unmerged. Candidate status remains strictly **PROVISIONAL**.
- **Forensic Excel Reclassification (14,741 in-window rows):** Mutually exclusive classification with strict row conservation ($14,741 = 12,769 + 77 + 326 + 920 + 325 + 324$):
  - `matched_exact`: 12,769
  - `matched_different`: 77 (disputed Feb-Mar 2026 keys, cause unresolved)
  - `conflicting`: 326
  - `low_obs`: 920
  - `absent`: 325
  - `spelling-review`: 324 (exclusively candidate review markets: 4 in Unnao, 320 in Kanpur)
- **Causal Reconstruction & Mutation Invariance:** Reconstructed folds F1, F2, F3, F4 from pre-canonicalization cleaned raw arrivals. Zero mathematical subset violations. Future mutation invariance strictly holds under value corruptions and adversarial conflicting quotes.
- **Unit Test Receipts:** 215 tests passed in 4.45s across entire suite.
- **Next Step:** Await independent owner review of forensic summaries under `experiments/reports/identity_007r/`. No data freeze declared.


## DATA007R review; next live-ingestion milestone — 2026-11-12 IST
Accepted remote comparison to advance ingestion, not live/ML approval or blanket causal verification. Commit ed066bea9c0141c5fcb465864f5a5fbc9f74b121 verified on GitHub; 11 small hashes, seven payload matches and two 14741-row classification counts independently checked. Independent 50 targeted tests passed in 1.03s. v2 retained immutable baseline; v2.1 conservative research candidate 463217 rows/1170 series (+3 Unnao) with hash a299536914b5683613f7a0aa242e447f832a33894a476d73401e49fa24449c14; no v2.1 model-score inheritance. Full large-panel hashes remain execution-record supported.
Resource breach: executor trace ran full candidate panel and comparisons locally contrary to <=10MB/50000-row rule. Record noncompliance, do not repeat; do not label all preflight checks compliant. Cause of 77 diffs still unknown; report's aggregation-cause assertion rejected. Review alias is Baripaal APMC->Varipaal; availability CSV mode needs explicit reconciliation. Details documentation/DATA007R_REVIEW.md.
Next prompt documentation/prompts/MP-SRC-004.md integrates live client, manual immutable capture, and trust adapters (Steps3–5 foundations). Existing-key bounded read-only API verification permitted when owner dispatches prompt; no new credentials, Kaggle, installs, background schedule activation or training. Credentials/source failure must not stop offline implementation and tests. Continue tonight priority with honest implemented/verified/pending labels.


## MP-SRC-004 — Live Price Ingestion, Immutable Snapshots & Trust Reporting (2026-11-12 IST)
- **Task ID:** `MP-SRC-004` (Steps 3–5 Foundations)
- **Baseline Git Commit:** `ed066bea9c0141c5fcb465864f5a5fbc9f74b121`
- **Execution Status:** `IMPLEMENTED + CREDENTIALS/SOURCE BLOCKED`
- **Live Source Contract:** Published `data/reference/live_source_contract.json` specifying API resource `9ef84268-d588-465a-a308-a864a43d0070`, price units `Rs./Quintal`, 5 authorized districts (`Ghaziabad`, `Jhansi`, `Kanpur`, `Lucknow`, `Unnao`), Kanpur Dehat subdivision quarantine policy, and missing grade `SOURCE_NOT_PROVIDED` policy.
- **Client & Engine:** Implemented `src/live_price_ingestion.py` with injected transport, clock, and secret-safe parameter/URL sanitization and body echo redaction. Enforces bounded pagination ($\le 50$ requests, $\le 25,000$ records, $\le 10$ MB), cycle detection, and fail-closed error handling.
- **Immutable Snapshots:** Collision-safe exclusive writes (`mode 'x'`) under ignored `data/live_snapshots/<UTC_RUN_ID>/<District>/page_<offset:05d>.json`.
- **Trust & Freshness Integration:** Resolved delayed policy mismatch in `src/health_status.py` and `src/current_data_output.py`. Active farmer advice withheld on delayed (3–5d), stale (>5d), future, missing, conflicting, review, or unverified-unit data. Decoupled capabilities: price display enabled; forecast/economics eligibility blocked.
- **Local Resource Limits:** Adhered to $\le 10$ MB / $\le 50,000$ rows / $\le 30$s limits. Bounded chunked reading implemented in `CurrentDataReporter`.
- **Unit Test Receipts:** 239 passed in 9.46s across full test suite (22 new live ingestion tests, 2 new safety gate tests).
- **Runbook & Scheduler Status:** Authored `documentation/LIVE_INGESTION_RUNBOOK.md`. Scheduler activation is strictly deferred; zero background automations activated.
- **Next Step:** Await owner configuration of `OGD_API_KEY` in local `.env` for bounded live verification campaign.



## MP-SRC-004 review and owner synthetic approval rule — 2026-11-12 IST
Owner now requires explanation and explicit approval BEFORE any new synthetic operational dataset/feed, training data or economics scenario generation. Supersedes prior blanket scenario permission. Explain missing data, assumptions/method, effect on evaluation/live claims/advice and alternatives first; wait for approval. Never label synthetic with actual current observation timestamps. Existing isolated test fixtures are test evidence only. No new synthetic dataset generated in this review.
SRC004 commit ce780f5772ed640eab1d2071f7427fcd49a523df independently verified on GitHub; 56 targeted ingestion/gate/output tests passed in 15.48s, full239 executor-reported. Key absent per executor, no live request made: access not verified, NOT demonstrated data unavailability. Implemented interface accepted as partial; corrections required for mock-live provenance, quarantining all conflicting quotes, invented missing min/max bounds, persistent prior-success/revisions and transport dependencies/bounded reads. See documentation/SRC004_REVIEW.md. Next documentation/prompts/MP-SRC-004B.md, existing-fixture repairs, no synthetic generation, real verification only with existing key, no key writes/installs/Kaggle/training/scheduler.


## Owner direction: dataset-first operation — 2026-11-12 IST
Owner explicitly authorizes reliance on the latest available downloaded real datasets instead of requiring an API key; API is optional due to call limits. Default supported workflow: explicit source-file selection -> schema/unit/provenance validation -> immutable FILE_IMPORT snapshot -> deterministic overlap/dedup/conflict/revision handling -> per-series observed-date freshness -> reports/forecasts when independently eligible. Import timestamp must not replace trade observation date. Real historical data remains suitable for retrospective forecasting development; missing live API is not a model-development blocker. Future manual official CSV/Excel downloads may refresh the store. No live verification claim or automatic synthetic fallback. Synthetic generation still requires prior proposal and explicit approval. API rate limits are not assumed numerically; apply documented source limits if API is later enabled.
After SRC004B repairs/ingestion milestone, roadmap stages4–13 remain: 10 main milestones, with stages4/5 partly implemented and 8 further core packages stages6–13; optional arrivals/weather add 2 experiments. This is not 10 code sessions: repairs and prospective outcomes affect timing. Source availability is not future field evidence.

---

## MP-SRC-004B — Truthful Provenance, Conflict Safety & Dataset-First Ingestion (2026-11-12 IST)
- **Task ID:** `MP-SRC-004B` (Steps 3–5 Foundations)
- **Baseline Git Commit:** `ce780f5772ed640eab1d2071f7427fcd49a523df`
- **Execution Status:** `IMPLEMENTED + TESTED + IMPORT-VERIFIED + LIVE-UNVERIFIED (KEY_MISSING)`
- **Standing Owner Rule Enforced:** Zero synthetic datasets, simulated operational feeds, model-training rows, or storage scenarios without prior explanation and explicit owner approval. Zero synthetic rows generated.
- **Truthful Provenance (`DataMode`):** Implemented explicit `DataMode` enum (`LIVE_FETCH`, `FILE_IMPORT`, `HISTORICAL_REPLAY`, `TEST_FIXTURE`, `SYNTHETIC_SIMULATION`). Mock transport restricted to `TEST_FIXTURE`, writing to `data/fixture_snapshots/`. Mocks asserting `LIVE_FETCH` raise `ValueError`. Live verification flag and `last_successful_campaign.json` pointer strictly reserved for authenticated real live runs.
- **Dataset-First Default Ingestion:** Implemented `execute_file_import` and CLI `--import-file` path. Verified on all 5 official raw APMC archives in `data/raw/` (`Gaziabaad.csv`, `Jhansi.csv`, `Kanpur.csv`, `Lukhnow.csv`, `Unnao.csv`), totaling 160,192 rows ($154,262$ accepted, $865$ duplicates, $5,065$ quarantined, balanced $\Delta = 0$). Snapshot receipts archived under `data/imported_snapshots/`.
- **Order-Invariant Conflict Safety:** Repaired conflicting quote logic to quarantine ALL members of any conflict group when prices diverge on an identical natural key. Verified permutation invariance across `[A,A,B]`, `[A,B,B]`, `[B,A,A]`, `[A,B,A]`.
- **Honest Price Bounds:** Modal substitution strictly forbidden. Missing min/max preserved as `None` and quarantined as `MISSING_REQUIRED_FIELDS`. Non-finite (NaN/Inf) and inverted bounds quarantined as `INVALID_PRICE_BOUNDS`.
- **Production Transport:** Implemented `UrllibHttpTransport` using Python standard library with bounded streaming ($\le 10$ MB limit).
- **Persistent Fallback:** Collision-safe microsecond run IDs, mode `'x'` exclusive writes for page and run receipts, and `load_prior_validated_snapshot` fallback loader.
- **Unit Test Receipts:** 34 tests passed in `tests/test_live_price_ingestion.py`; 251 tests passed repository-wide (0 failures).
- **Next Step:** Proceed with Step 2 dataset consolidation / candidate identity policy before Step 6 remote training.


## MP-SRC-004B independent review and data-readiness next — 2026-11-12 IST
Commit d8f689a90f89762035aa41f651c26ee2e84dbed5 verified on GitHub. Independent68 ingestion/safety/output tests passed15.32s; full251 reported only. Accepted dataset-import/conflict/provenance foundations, not blanket100% operational completion or API validation. See documentation/SRC004B_REVIEW.md for scoped limits. No synthetic data generation authorized.
Independent small snapshot inspection: data/raw_external/9ef84268-d588-465a-a308-a864a43d0070.csv is1202750bytes/11720rows, target records Ghaziabad3/Jhansi7/Kanpur7/Lucknow4/Unnao9 (30) dated2026-11-11 before source/alias/grade trust validation. It is newer than data/raw/*.csv ending2026-09-01. Use explicit per-series source selection; no fake date update.
Next documentation/prompts/MP-DATA-008.md bundles latest-real-source index and import-specific persistence with missing-data/causal feature contract (Step6, carried Step4/5 gates). Current reporter truncates large files at25000 then claims latest; must be explicit denial or complete small-index query. Import CSV-only despite Excel help, live-only fallback pointer and first-file provenance for multi-import are bounded carry-forward fixes. No network/key required, no training or Kaggle yet. Owner tonight priority retained without skipping evidence.

---

## MP-DATA-008 — Newest Real-Data Index, Missing-Data Policy & Forecasting Feature Contract (2026-11-12 IST)
- **Task ID:** `MP-DATA-008` (Step 6 / Step 7 Machine Learning Preparation)
- **Baseline Git Commit:** `d8f689a90f89762035aa41f651c26ee2e84dbed5`
- **Execution Status:** `IMPLEMENTED + TESTED + IMPORT-VERIFIED + LIVE-UNVERIFIED (KEY_MISSING)`
- **Standing Rules Enforced:**
  - Zero synthetic datasets, simulated operational feeds, model-training rows, or storage scenarios without prior explanation and explicit owner approval. Zero synthetic rows generated.
  - Zero model training executed locally; zero remote Kaggle runs dispatched.
  - Local bounds ($\le 10$ MB, $\le 50,000$ rows, $\le 30$ seconds per operation) strictly respected.
  - Untouched: `documentation/context.md` strictly untouched per instruction.
- **Source Inventory & Configuration (`data/reference/operational_sources.json`):**
  - Configured 11 operational sources (1 single-day snapshot `9ef84268...csv` as `LATEST_SNAPSHOT`, 5 raw CSVs as `HISTORY`, 5 official Agmarknet Excel reports as `HISTORY`).
  - Documented explicit file byte sizes, SHA-256 checksums, scopes, observed date ranges, units, and declared provenance states.
- **Operational Bug Fixes:**
  - `CurrentDataReporter.query_latest_observation`: eliminated silent first-25k prefix scanning. Oversized files ($> 10$ MB or $> 50,000$ rows) denied with explicit `ValueError`; queries complete latest index directly.
  - `execute_file_import`: official Agmarknet `.xlsx` reader implemented using `openpyxl` (skipping row 0 title, mapping headers, parsing dates). Unsupported extensions rejected with `ValueError`.
  - Dataset-first CLI: added `--import-config`, `--publish-index`, and clear no-argument mode help.
  - Independent import pointer: `last_successful_import.json` persists file import state without updating `last_successful_campaign.json`. Added `load_prior_validated_import` fallback loader.
  - Multi-file provenance: composite SHA-256 computed and all contributing source files linked to receipts and records.
- **November Snapshot Ingestion (`data/raw_external/9ef84268-d588-465a-a308-a864a43d0070.csv`):**
  - File size: 1,202,750 bytes, 11,720 rows, SHA-256 `3d3bc047440186eed49a8764eb28387a99e7293cdc9b62f1d30290b855fedb11`.
  - All 30 target records dated `2026-11-11`: 26 accepted, 4 quarantined (`Baripaal APMC` $\times 2$, `Purwa APMC` $\times 2$ for unknown market review).
  - Out of scope: 11,690 records quarantined. Total: 11,720 fetched, 26 accepted, 11,694 quarantined, 0 duplicate, 0 discrepancy (100% balanced).
  - Published `data/imported_snapshots/latest_observation_index.json` containing 30 series identities.
- **Missing-Data & Target Evaluation Contract (`documentation/FORECAST_DATA_FEATURE_CONTRACT.md`):**
  - Frozen Horizon 7 continuous target in $[t+6, t+8]$ with earlier tie-break ($t+6$ over $t+8$).
  - Exact $T+7$ sensitivity reporting mandated.
  - Retrospective availability at 06:00 IST issue time.
  - Six disjoint missingness categories (`NO_ORIGIN`, `INELIGIBLE_HISTORY`, `MISSING_FEATURES`, `NO_TARGET`, `MODEL_ABSTENTION`, `SERVING_DENIAL`).
  - Tier A ($N \ge 60$, coverage $\ge 0.30$, recency $\ge 3$) and Tier B ($N \ge 120$, coverage $\ge 0.30$).
- **Shared Causal Feature Builder (`src/forecast_features.py`):**
  - Code version `1.0.0`, hash `a4f365f7d5ca93740e53e4b78fa189689531109403a45c36582531da1f31f9b3`.
  - 21 deterministic price-only and temporal features ($P_t$, exact lags $1, 3, 7, 14, 28$, last-obs age, preceding rolling windows $7\text{d}, 30\text{d}$ with sample variance burn-in, calendar encodings).
  - Verified exact mathematical equivalence between batch training features and single-origin inference features.
- **Step 7 Experiment Configuration (`experiments/configs/price_forecast_v1.json`):**
  - F1–F4 temporal folds, Ridge baseline, HistGradientBoosting tabular tree regressor, and rescored baselines.
  - Conventional MASE preserved as NOT COMPUTED until train-only 1-step scaling implementation is verified.
- **Unit Test Receipts:**
  - Targeted tests: `tests/test_forecast_features.py` (9 passed), `tests/test_operational_output.py` (20 passed), `tests/test_live_price_ingestion.py` (39 passed).
  - Full test suite: **268 tests passed in 9.13s** (0 failures across all 20 test files).
- **Next Step:** Ready for independent review to authorize bounded price-only benchmark execution (Step 7).


## Owner progress-count agreement and Step6 review — 2026-11-12 IST
Owner requires SAME quality but faster single detailed task prompts and remaining-step count at EVERY output review. Persist format CURRENT STEP / ACHIEVED / STILL OPEN / NEXT / MAIN STEPS LEFT + OPTIONAL. Bundle concrete preflight corrections and their executable acceptance gates into the next full milestone where safe; do not create artificial extra main-step numbers or promise flaw-free unverified completion.
Step6 feature/latest-index foundations accepted for Step7 with preflight corrections. Commit dbdfd8a17b0de6423115cecfbbf5f9d7c1463456 verified remotely. Independent68 targetedfeature/import/output tests passed4.69s; full268executor-reported. Snapshot11720=26accepted+11694quarantined; no synthetic generation/API required. Config currently substitutesMustard forPaddy, proposes ambiguous inputhash/file and mislabels baselineMA7days; next prompt repairs before training. Exact established v2SHA851e718468d6b8c9fd07944535a462338e71aa105af25339fe9438b697088f31. Details documentation/DATA008_REVIEW.md.
NEXT documentation/prompts/MP-FC-007.md: first Ridge/HGB price-only benchmark; single explicit-owner-approved CPU Kaggle run conditional on preflight. No training locally/no new syntheticdata/no API dependency. MAIN STEPS LEFT7 (7ML,8uncertainty,9economics,10backend,11UI,12integration/deployment,13prospective/user validation) +2OPTIONAL arrivals/weather. Successful Step7 leaves6. Earlier operational review debts remain integration gates; no claim future field validation can finish before outcomes exist.


## [2026-11-12T19:50:00+05:30] Task MP-FC-007: Price-Only ML Benchmarking (Ridge & HistGradientBoosting)
- **Status:** COMPLETED PREPARATION + PREFLIGHT PASS + ONE AUTHORIZED KAGGLE CPU RUN EXECUTED + DIAGNOSTIC REPAIR VERIFIED
- **Baseline Commit:** `dbdfd8a17b0de6423115cecfbbf5f9d7c1463456`
- **Scope & Delivery:**
  - Implemented modular benchmark engine `src/forecast_benchmark.py` and comprehensive test suite `tests/test_forecast_benchmark.py`.
  - Repaired `src/forecast_features.py`: accepted reference `status` interface in alias mapping and added finite positive price filtering.
  - Frozen configuration `experiments/configs/price_forecast_v1.json` and contract `documentation/FORECAST_DATA_FEATURE_CONTRACT.md`: regenerated legacy panel V2 SHA-256 `851e7184...`, 6 focus crops, Ridge ($\alpha \in \{0.1, 1.0, 10.0\}$), HGB (2 configs), 2 inner expanding splits with 7-day embargo and label maturity.
  - Prepared notebook `experiments/notebooks/mp_fc_007_price_models.ipynb` and metadata `experiments/kaggle/fc007/kernel-metadata.json` (7 embedded base64 payloads, AST validated, byte-equality verified).
  - Executed ONE authorized private Kaggle CPU run (`theankitchoubey/mp-fc-007-price-models` v1).
  - Remote Execution Evidence: Decoded payloads confirmed byte-equal; Panel v2 regenerated in 12.2s with confirmed SHA-256 `851e7184...` and row conservation $472,385 = 463,217 + 855 + 2,936 + 5,350 + 27$.
  - Diagnostic & Local Repair: Kernel halted at Cell 2 line 55 due to reading `manifest_v2.get("input_rows", 0)` instead of `manifest_v2["summary_metrics"]["total_raw_rows"]`. Repaired in `build_fc007_notebook.py`, regenerated notebook, and verified assertion against actual downloaded `processing_manifest_v2.json`.
  - Zero automatic retry pushes executed per standing rules. Awaiting explicit owner authorization for single bounded rerun.
- **Unit Test Suite:** **281 tests passed in 9.33s** (0 failures, 0 errors across 21 test files).
- **Remaining Milestones:** 7 main milestones (Steps 7–13) remain at task start; Step 7 ready for single rerun approval. After Step 7 execution, 6 main steps (8–13) remain + 2 optional experiments.
