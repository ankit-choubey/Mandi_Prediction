# Independent review of MP-ECON-001 — 13 November 2026

GitHub main and local HEAD independently verified at `d0ff42e475375a8de487b8c05d697da27f06adb6`. Review evidence is saved under `experiments/reports/ECON001_REVIEW/`. This decision supersedes the executor's unconditional Step 8/9 completion and four-milestone count.

## Accepted findings

- The saved numeric-level lookup is repaired: 246 exact-commodity/pooled cases across F2–F4, three models and two levels reproduced the same bounds before and after numeric-key JSON loading.
- All 25 entries across the FC007_VERIFIED, FC008 and ECON001 manifests match actual file hashes, with no self-inclusion. Repeated FC008 manifest construction is deterministic. Historical calibration quantile bytes are unchanged from `8d4ed57`.
- Canonical accounting passes the two hand cases: +470 INR for the 50 INR/quintal direct cost case and -230 INR for the 120 INR/quintal case. Independent checks of 1,000 existing-style isolated mathematical fixtures found maximum accounting reconciliation error `6.984919309616089e-10` and break-even residual `1.1759482276829658e-12`, below 1e-7. These are test fixtures, not observed commercial outcomes.
- The local facility directory has 22 records, all with quotation status “Not received” and empty rate amounts. This supports **0/22 quotations in this directory**, not universal commercial-rate unavailability throughout Uttar Pradesh. Empirical profitability remains not evaluated.
- The research evaluator consistently blocks actionable advice. No new synthetic operational dataset was needed or generated for this review.

## Delivery blockers reproduced

### 1. Missing costs still become illustrative values

`evaluate_research_economics()` uses `request.params or get_default_scenarios()["Central"]`. A request with quantity 1, current price 2000, future point 2200 and no economic parameters returns a numeric gain of **155.31506849315065 INR**, using invented-for-this-request defaults: direct cost 20, physical loss 1%, annual rate 7% and omitted charges at zero. It does disclose a default warning and blocks advice, but the required missing-input contract prohibits automatically selecting this profile. Return incomplete/unavailable holding and gain fields until explicit complete inputs are supplied, or require an explicit named illustrative selection under the owner's rules. Do not auto-select it.

The request horizon, parameter horizon and dated price horizon are not reconciled. A request declaring 30 days, a seven-day parameter set and origin/target seven days apart is accepted. Negative later transaction cost, invalid carrying mode and NaN direct cost are also accepted by `EconomicParameters`. Literal type annotations do not validate values at runtime. Provenance values, units and periods are recorded but not checked against amounts actually used.

### 2. Artifact validation remains permissive

The loader accepts an altered code identity, a missing entire F2 payload, a future maximum-calibration-target date and a NaN Wheat quantile. When the envelope's F2 scope is changed to November 2026 and its maximum calibration target to 2099, `predict_interval()` returns SUCCESS for a 13 November 2026 origin. Advice remains blocked, but this is still invalid research inference. The public inference path does not invoke complete envelope validation or enforce actual target maturity. Pin the expected artifact/config/schema identity outside the artifact, validate complete group payloads, and parse/compare actual dates. Corrupt quantiles must be rejected, rather than silently becoming pooled fallback.

### 3. Resource and provenance claims are overstated

`max_duration_seconds` remains unused. RSS is measured near the end but never compared with 512 MB, and large row lists are still built before bounds are checked. Thus “measure and enforce: PASSED” is not supported.

The old interval receipt retained its original timestamp while its code hash was changed from `c6678d9a...` to `a7891026...` and `measured_peak_rss_mb: 23.66` was added. A metadata-refresh measurement cannot establish the historical full pipeline's memory use. Preserve the original run receipt and issue a separately dated migration/correction receipt stating exactly which small operation was measured. The current envelope/receipt code hashes match current code, but this does not repair the historical provenance mismatch. The pasted final report's `5df6c039...` code hash also differs from current bytes.

### 4. Economic fixture reports are not fully reconciled

The production equation passes independent checks, but the committed fixture table does not consistently reproduce from its displayed inputs. For FIX-05, displayed inputs give holding proceeds **2115.566 INR** and gain **130.566 INR**, versus reported **2114.30** and **129.30**. Using the likely unrounded annual 7% / seven-day factor gives approximately 2115.5651 and 130.5651, so the discrepancy is not explained by the printed rate's rounding. FIX-03/04 also lose exact reproducibility because the printed rate factor is rounded and original annual rate/horizon are omitted. Generate report rows from actual results with full input precision, then independently reconcile every row; do not hand-edit only FIX-05's headline.

## Test interpretation

The reviewer independently ran the focused economic/interval/scorer checks: **56 passed in 11.48 seconds**. The full `tests/` batch independently passed **312 tests in 20.20 seconds**, with 18 divide-by-zero/overflow/invalid matmul warnings in the benchmark tuning fixture. The backing/ batch independently passed **45 tests in5.11 seconds**, bringing the bounded full batches to **357 passing tests**. Warning location is observed; the executor's ill-conditioned-SVD root-cause explanation is unverified. Passing current tests does not establish coverage of the adversarial failures above.

## Decision, scope and next task

Step 8 saved-level/manifest repairs and Step 9 accounting core are verified, but **both complete delivery gates remain open**. There are **6 main milestones**: finish 8 and 9, then 10–13; plus **2 optional arrivals/weather ablations**. The next prompt combines the explicit correction gates with Step 10 backend work. Independent acceptance of all three would leave **3 main milestones: interface (11), integration/deployment (12), forward validation and usability (13)**. Commercial-cost evidence remains a release gate.

Executor section30.6 also incorrectly renames Step10 as model training. It remains backend work; no new training run is authorized. Step13 has not been renamed to a professor briefing. It requires forward-only logging before actual outcomes and usability evidence. A randomized trial is not an automatic prerequisite for assessing forecast errors in a prospective shadow evaluation; any later causal policy-effect claim needs its own study design.

The project remains suitable for an honest professor progress discussion. It is not yet a complete backend-ready economics or validated live-advice product. No production source edits, commit or push were made by the reviewer; existing working changes were preserved.
