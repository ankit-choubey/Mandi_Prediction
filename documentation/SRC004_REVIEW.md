# MP-SRC-004 independent review — 2026-11-12 IST

Commit ce780f5772ed640eab1d2071f7427fcd49a523df verified through GitHub connector. Independent targeted command python3 -m pytest tests/test_live_price_ingestion.py tests/test_recommendation_safety_gate.py tests/test_operational_output.py -q -o cache_dir=/tmp/mandi_src004_review_cache --basetemp=/tmp/mandi_src004_review_tmp => 56 passed in 15.48s, exit 0. Full 239-pass receipt remains executor-reported. Working live_source_contract.json has an extra EOF blank line, preserved.

Achieved: modular client, transport injection, bounded pagination, immutable page receipts, missing-key CLI state, revised delayed-advice gate and operational documentation. Live source was NOT contacted because key absent per executor. Missing credentials do not demonstrate that source data is unavailable. Do not claim 100% implementation complete from fixture tests.

Material issues seen in code:
- execute_campaign sets is_live_verified=True solely on successful accepted records; transport provenance is not checked. Mock/dry-run success can masquerade as verified live. Fixture transport also writes into default live snapshot root unless caller overrides it. Demo/source provenance must be explicit and propagate into all records/receipts/health/capabilities.
- Within-batch conflict logic quarantines incoming conflicting quote but leaves previously accepted same-key quote in accepted_records and natural_key_registry. Quarantine all members of that unresolved conflict group, with counters/reconciliation adjusted and no stale accepted date range.
- Missing min/max prices are filled with modal_price; infinite values may pass ordered bounds. Required source field/nonfinite handling must not fabricate observed bounds.
- run_receipt uses write mode w and second-resolution run IDs; page files are exclusive but run receipt can overwrite. Make all receipt/state publication collision-safe.
- last_successful_fetch is derived from the current campaign only; no persisted prior success/fallback load or cross-run revision/supersession logic exists despite claims. Implement or label not implemented; missing key should produce diagnostic receipt without touching last success. Per-market freshness and source-vs-observation states must remain distinct.
- Production transport depends on unpinned requests (not in requirements). Prefer stdlib within no-install scope or explicitly record runtime dependency; response size is checked after full body read, not bounded streaming. Tests do not establish real endpoint request/schema compatibility.

Source contract official-unit and Kanpur boundary claims need exact supporting evidence; no independent official-metadata verification was performed in this review. Live key absence remains executor-reported; reviewer did not print/read secrets. Candidate market statuses and unknown grade must remain visible.

Owner new instruction supersedes prior blanket synthetic-scenario permission: before any new synthetic operational feed/dataset, model-training data or economics scenario generation, explain missing data, proposed substitute, realistic assumptions, affected metrics/use limits and obtain explicit owner approval. No new synthetic dataset was generated during this review. Existing test fixtures are not live evidence. No automatic fake-now fallback. Continue using real historical observations with honest dates while credentials pending; implementation/tests can proceed independently.

Next: documentation/prompts/MP-SRC-004B.md, source/trust repair plus bounded real verification if existing key becomes available; no synthetic data creation, no new dependencies, Kaggle, model training or activated scheduling.
