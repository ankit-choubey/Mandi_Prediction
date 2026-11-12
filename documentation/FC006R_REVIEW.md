# Independent FC006R review — 2026-11-12 IST

Decision: accept the corrected run as a **retrospective benchmark for proceeding to Step 2**; not a panel freeze, causal/production validation or ML approval. Commit b4861ee6441ae492483157d47ec8c3431d3a3fb1 verified through GitHub connector. Local inspection found matching commit message and expected deliverables. Executor self-approval wording does not replace this scoped decision.

## Independently checked
- 16 <=10 MB artifacts matched hashes in execution manifest; four small committed CSVs correspond to retrieved results (three scorecards byte-compared, diagnostics inspected).
- All four notebook embedded source modules match working source bytes. Five code cells AST-parse successfully. Notebook is now packaged with the actual shared scorer.
- 40 fold/tier + 120 focus-crop + 80 sensitivity rows = 240. Paired skill identities checked within 1e-4 for all 224 finite values; 16 focus rows have undefined skill. Undefined is not zero.
- Stage conservation: 317 recency + 3,624 missing targets + 2,909 past-fold targets + 64,776 evaluated = 71,626 test-window observations.
- Overall scope counts: 10 disputed origins + 10 disputed targets - 2 both = 18 exclusions; Scope A 64,758. Two extra clean-recency exclusions give Scope B 64,756. Diagnostics list 610 origins with prior disputed history, 13 finite MA changes, 8 finite drift changes and 1 drift finite-to-NaN transition. Seasonal history unaffected in this date range. History-affected counts are not all changed-prediction counts.
- Independent targeted test command: python3 -m pytest tests/test_baselines.py tests/test_fc006_audit.py -q -o cache_dir=/tmp/mandi_fc006r_review_cache --basetemp=/tmp/mandi_fc006r_review_tmp => 23 passed in 0.30s, exit 0.

## Current benchmark and interpretation
Overall Tier A MAE remains naive 106.9554, MA 134.1925, seasonal 774.3764, drift 107.3248 (reported currency unit Rs/quintal; upstream unit provenance still qualified). Paired denominator checks pass. Overall drift skill -0.0068 CI is **[-0.0309, 0.0176]** in rerun CSV. Volatile drift skill +0.0695 CI is **[0.0429, 0.0937]**; pasted report repeats legacy [0.0432,0.0950], which must be corrected in current prose. Point scores agree; bootstrap order changed. Do not attribute changed seasonal/drift CIs solely to a changed finite mask without demonstrating mask changes; stable resampling order alone can change finite-bootstrap quantiles.

Scope B naive MAE 106.8984; MA 134.1756; drift 107.2534; seasonal 774.4716. The earlier zero-impact claim is superseded by actual exclusions, prediction changes and altered metrics. This sensitivity does not resolve why upstream prices differ.

## Limits and review debt
- Full 67 MB panel and 23.7 MB prediction archive were NOT read/hashed/recomputed locally under inherited compute limits. Panel hash and archive row count are supported by execution logs/manifest; independent full-archive reconstruction remains review debt. Log reaches task-complete/artifact export; exact platform status/version/duration is executor-reported, consistent with downloaded logs, not independently queried on Kaggle.
- Full-suite 175 passes remains executor-reported. Reviewer ran targeted fixtures only. Run duration 149.04 sec includes notebook conversion; do not represent it as a separately measured scoring-loop runtime.
- Statistical inference still assumes series-cluster resampling; common shocks, inspected holdouts, historical publication availability, full-history identity evidence and eligibility filtering remain qualified.
- Alias Rule A unbounded gaps, Rule B evidence minima, Baripaal/Purwa/Jhansi and source-unit/source-date issues remain Step 2 items.
- Executor trace contains cancelled/killed staged secret-review task; successful completed scan is not evidenced by that trace. Require recorded scan in next push; no conclusion of a leak follows.

Next: documentation/prompts/MP-DATA-007.md, local candidate policy/freeze preparation. No new Kaggle authorization and no freeze until its evidence passes review. No local project commit/push by reviewer.
