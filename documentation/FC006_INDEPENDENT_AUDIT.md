# MP-FC-006 independent audit — 2026-11-12 IST

Verdict: **CHANGES REQUIRED**. The commit and substantial deliverables exist. Broad performance acceptance and the disputed-key sensitivity are withheld. This audit did not retrain or scan the full panel.

## Evidence checked

- GitHub connector independently retrieved commit `7931caaf01ee9e53ea2f18b823d710b8c61851ff` with matching message and changed files. Local `git show` lists 12 changed files; no journal, raw panel, output directory or credential path is among them.
- All 13 artifacts <=10 MB listed in the FC006 execution manifest matched their recorded SHA-256 locally. This checks consistency with that manifest, not independent source authenticity. The 67 MB panel was deliberately not hashed/read locally under the inherited compute limit; its asserted hash remains supported by the execution record, not an independent rerun here.
- Inspected baseline module/test source, notebook evaluation/eligibility/sensitivity sections, small scorecards, diagnostic JSON, alias table and disputed-key CSV. Full line-by-line notebook, embedded-source equivalence and older research reviews remain open.
- `git check-ignore -v brain/context.md` resolves to `/brain/` in `.gitignore`; `git ls-files brain` is empty. Journal exists and is local-only.
- Current tree has a pre-existing one-line FC006 summary modification and untracked datasets/reference material. The pasted report's clean-tree statement is historical, not current state.

## Claim decisions

| Finding | Evidence / decision |
|---|---|
| A007-01, S1: disputed-key sensitivity uses incompatible market identities | All 77 source discrepancy rows contain APMC market names, and the accepted alias table changes all 77. Notebook builds `set_77_keys` from those raw names but checks against canonical panel `market`. There is no canonicalization between these operations. It also silently accepts an empty set if the file is absent. Reject “zero impact”; require canonical keys, fail-closed loading, expected counts, and affected-origin/target/history counts. |
| A007-02, S1: pasted metrics disagree with artifacts | Pasted MA CI/RMSE/MAPE/median/share, seasonal CI/RMSE/MAPE/median/share, drift CI/RMSE/MAPE/median/share/skill differ from saved overall Tier A rows. Use the CSV values below as artifact-backed provisional results; correct report and docs together. The >2% drift skill CI is [0.0432, 0.0950] in CSV, versus [0.0401, 0.0982] in prose. |
| A007-03, S1: series reconciliation narrative is wrong | Pasted report says 9 leaving / 5 entering / >=200 threshold. Diagnostic JSON says 6 leaving / 2 entering; notebook Tier A is >=60 and coverage >=0.30; Tier B >=120. JSON balances: 496 - 6 + 2 = 492; 571 - 1,408 + 3,192 = 2,355; 384,887 + 2,355 = 387,242. |
| A007-04, S2: MASE label is unsupported | Existing documentation table appears to use pooled test MAE divided by overall naive MAE. Conventional MASE scales each series using an in-training naive-error denominator. Baseline module does not implement MASE. Do not label those ratios MASE; compute the declared train-only scaling or mark NOT COMPUTED. |
| A007-05, S1: tests do not cover the actual optimized prediction loop | Leakage fixture tests call baseline functions after `get_history_as_of`; notebook separately implements predictions with NumPy arrays. Reading the loop shows bounded historical windows, but function tests alone do not verify loop equivalence or whole-pipeline invariance. Require notebook-path regression tests, target/fold bounds and causal preprocessing checks. |
| A007-06, S2: per-model series and LOW-N use pre-abstention slice | `evaluate_model_slice` obtains n_series and LOW-N before removing missing model predictions. Require eligible and scored series/origin counts separately, with LOW-N applied to scored cases. |
| A007-07, S1: real-time and historical availability need qualification | Eligibility mask is train-only, but upstream panel low-observation filtering and accepted alias decisions use full-history evidence; assess selection/identity lookahead. Same-day prices are assumed published by forecast issue time, yet historical retrieval timestamps are absent. These are retrospective assumptions, not verified live availability. |
| A007-08, S2: unsupported causal claims | Stable commodity median ratios cannot prove units. Variety-count changes alone do not establish why rows fell. +/-3-day failure only rules out the tested shifts/matching rule. Nov 7 go-live remains unverified despite surviving source-register wording. |
| A007-09, S2: future-outcome-defined subgroup | >2% target-move subset is descriptive retrospective analysis. Its members are unknown at prediction time; it cannot select a live model or policy. Multiple crop/fold comparisons and reused evaluation data require caution. |
| A007-10, S2: trust-policy mismatch | Existing gate permits DELAYED advice; handoff says CURRENT only. Keep policy undecided pending explicit capability-specific reconciliation; do not call code aligned with handoff. |

Severity is provisional triage, not a completed review of every inherited OAI. New ML approval is held pending A007-01/02/03/05/07 disposition.

## Artifact-backed overall Tier A values (not independently regenerated)

| Model | N scored | MAE | RMSE | MAPE % | Median AE | Within 5% % | Skill | 95% skill CI |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Naive | 64,776 | 106.9554 | 298.8337 | 4.16 | 40 | 76.76 | 0 | [0, 0] |
| MA | 64,776 | 134.1925 | 333.3659 | 5.08 | 50.7143 | 70.98 | -0.2547 | [-0.2909, -0.2105] |
| Seasonal naive | 59,200 | 774.3764 | 1433.7629 | 29.45 | 375 | 22.70 | -6.3738 | [-7.2432, -5.5137] |
| Drift | 64,036 | 107.3248 | 303.6659 | 4.29 | 42 | 76.55 | -0.0068 | [-0.0303, 0.0191] |

Skill uses naive error on each model's matching scored cases; dividing displayed model MAE by naive MAE over a different sample will not necessarily reproduce it.

Other arithmetic: unmatched 923+420+323+197+32 = 1,895. F1+F2 = 61,348 of 64,776 origins = 94.7079%; later folds = 3,428. Pooled performance is dominated by 2025. The exported 5,000-row prediction sample contains only F1, so it cannot independently reproduce all-fold scorecards.

## Review log

Received owner-pasted completion report 2026-11-12. Commit verified remotely and locally. Artifact hashes checked within local limits. Panel reproducibility not independently rerun. Targeted fixture-test outcome is recorded in the local journal and mathematical validation addendum after execution. Reported full suite 160 passed / 5.97s is not independently re-executed by this audit. No Kaggle execution, uploads, installs, Git staging/commit/push or baseline report overwrites. Next task MP-AUDIT-007; preserve the original FC006 evidence and supersede disputed claims with explicit corrections.
