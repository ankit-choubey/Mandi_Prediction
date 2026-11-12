# Independent backend review — 13 November 2026

GitHub main and local HEAD verified at `5a3f5c4b34e84ea95fd4b4b47f387a5735aff5e4`. Existing working changes, including EOF additions to service/test/OpenAPI/migration files, were preserved. This review supersedes the unconditional acceptance and three-milestone count in the executor report.

## What passed

- The modular WSGI service exists and runs. Imported observations remain FILE_IMPORT with live verification false; age is recomputed from actual observation date. The current index contains30 series.
- Missing the entire params object now leaves holding gains unavailable. Invalid numeric domains and the previously tested request/parameter/date horizon mismatch are rejected. A fully entered +470 INR hand case still works with advice blocked.
- The five economic fixture rows now reconcile to independent Decimal accounting within their declared cent rounding, including FIX-05 gain130.57. There are **five rows**, not six as stated in the pasted report; FIX-04's displayed rounded break-even yields a tiny nonzero residual within rounding.
- The exact original receipt from `8d4ed57` is preserved. Metadata-refresh RSS is distinguished from unverified historical full-run memory.
- All24 entries in the three reviewed manifests match their committed HEAD payloads. The working migration receipt has a pre-existing extra blank line, so its working bytes differ from the committed manifest; this is tracked separately from a committed artifact defect.
- Regression verification:344 tests/ passed, one loopback test was denied local port binding, and18 numerical warnings occurred (20.51s). That one test passed in0.55s when local binding was permitted; backing/ passed45 tests in4.50s. Thus390 unique existing tests passed after resolving the environment restriction. The original batch exit was1; it was not a single clean full-suite invocation. Warning causes remain unverified.

## Blocking results

### Benchmark output is numerically wrong

The service returns literal constants instead of verified report data. It also mixes the point benchmark's64,776 origins/F1–F4 with the interval evaluation's26,918 issued origins/F2–F4 under one denominator description.

| Metric | API output | Verified report |
|---|---:|---:|
| Persistence RMSE | 187.72 | 298.8336641813 |
| HGB RMSE | 176.62 | 281.1581429433 |
| Ridge RMSE | 178.61 | 288.5644228101 |
| Persistence95% coverage | 94.72% | 94.3829% |
| HGB90% /95% coverage | 88.42% /93.81% | 89.9955% /94.3978% |
| Ridge90% /95% coverage | 88.15% /93.54% | 89.9955% /94.4312% |
| Persistence F2 coverage at90% | 94.48% | 92.3159% |

Ridge skill is also misreported as-3.14% versus-3.150241% (rounds to-3.15%). Source tables are `FC007_VERIFIED/scorecard_overall.csv` and `FC008/intervals_overall.csv`, plus the fold table. Keep every metric's own population, units, point/interval meaning and lineage. A correct MAE headline does not validate other fields. The HTTP benchmark endpoint and API contract must not be shown as verified professor evidence until corrected.

### Partial cost objects still invent omitted inputs

HTTP economics request Q1/current2000/future2200 with only `params.storage_cost_per_quintal=50` returns gain150 INR by setting every omitted fee, rate and loss to zero. Omitting params entirely returns net-sale proceeds2000 despite the immediate transaction cost being unknown. Gross sale value may be calculated separately; net sale requires that fee. Require complete explicit components at the strict boundary, including explicit zeros, and return null for dependent missing-input calculations. Recording an unverified warning does not supply a missing amount. Provenance unit/status validation also remains incomplete.

### Price trust can increase through defaults

An isolated record lacking grade, disposition and verification becomes gradeFAQ, statusACCEPTED and import-verified true. An injected future row can propagate `active_advice_permitted: true` and other capability booleans from its source dictionary. Invalid `series: []` JSON is accepted as price-ready. Missing-index errors expose the configured internal filesystem path. Validate the index and derive capability decisions at the service boundary; absence is unknown, and source flags cannot override the research-only advice policy. The catalog currently lists seven focus names while claiming six; put documented Paddy aliases in an alias field and preserve the six canonical crops.

### Request and artifact contracts remain incomplete

Direct production WSGI calls reproduce: empty economics object ->500/KeyError; text/plain POST accepted; NaN in a JSON body accepted; negative forecast horizon accepted. Unknown/repeated query/body fields, strict dates, media types and finite JSON need consistent validation rather than relying on output NaN-to-null cleaning.

The envelope loader still accepts a finite positive quantile changed by10%, missing F2 naive model and missing semantic-config identity. It verifies some self-reported header strings but does not pin the payload bytes externally. Numeric inference can change without changing source/code header claims. Validate a trusted expected payload digest and complete model/config/count/rank schema. The full calibration pipeline watchdog is called only before work and after loading; decoded gzipped bytes are not counted and large lists are built before later bounds. It does not establish the advertised incremental enforcement throughout computation.

### Report and test claims need alignment

The pasted report's Agra example is outside the configured five-district index and does not match actual field names. It must be labelled illustrative or replaced with captured supported-market output. Pasted latency p95/max/cold figures differ from saved measurements; source each claim from a receipt and distinguish first request from full process startup. Do not infer an ill-conditioned-SVD cause from a warning location.

New API/service tests instantiate the default service and assert an ignored local index has exactly30 rows; they are not clean-checkout fixtures. Passing locally does not establish reproducible CI. Use injected isolated fixtures for required tests and a separate optional real-snapshot smoke.

## Executable acceptance and next decision

`experiments/reviews/check_app001a_review_gates.py` runs without network or training and returns exit1 today: **8/29 targeted checks pass;21 fail**. Broader direct probes found26 unmet checks among37 targeted cases. These selected adversarial counts are **not a project accuracy/completion score**. Both receipts are under `experiments/reports/APP001A_REVIEW/`. The script includes a valid fully entered economic control, not only rejection cases.

Steps8/9/10 contain verified implementation but their complete delivery gates remain open. **6 main milestones remain: finish8,9,10; then11 interface,12 integration/deployment,13 prospective validation/usability; plus2 optional arrivals/weather ablations.** No finalized earlier audit or model fit needs repeating. Next is one bounded backend completion task, `documentation/prompts/MP-APP-001A-R.md`, with executable failure-to-pass evidence required before UI work. Acceptance would leave3 later main milestones11–13.

Professor readiness: the verified historical research and repaired accounting are suitable for a progress discussion with limitations. The current API benchmark page is not reliable presentation evidence. Live advice, observed profitability and forward reliability remain unestablished. No reviewer production-source edits, commit or push were made.
