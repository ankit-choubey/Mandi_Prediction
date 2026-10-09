# Phase 1 Audit: Data Integrity & Exact-Calendar-Date Coverage

**Audit Phase:** Phase 1 — Data Integrity & Temporal Continuity  
**Date:** October 10, 2026  
**Auditor:** Antigravity AI  
**Current Status:** **NOT STARTED (PLANNED SCOPE ONLY)**  
**Decision:** **PENDING EXECUTION**  

> **Evidence Rule Reminder:**
> No Phase 1 tests have been executed under this phase yet. This document specifies the planned protocol, hypotheses to be tested, and output schema. Results must **never** be invented prior to actual execution.

---

## 1. Planned Audit Scope

Phase 1 will conduct a comprehensive empirical audit of data integrity, market-name mapping, observation continuity, and exact calendar-day target matching across all series in the raw APMC dataset.

The investigation is structured around the following 10 work packages:

1. **Raw File & Canonical Schema Verification:**
   - Hash verification of all 5 CSV input files.
   - Per-file encoding, delimiter, and line termination verification.
2. **Market-Name Mapping & Canonicalization Review:**
   - Verification of the Nov 2025 `APMC` renaming transition across all districts.
   - Testing whether stripping ` APMC` and standardizing `Baripaal` $\to$ `Varipaal` reduces nominal mandis from 42 to 21 without date collisions.
3. **Duplicate & Conflicting Record Investigation:**
   - Granular breakdown of the 4,451 records sharing identical series-date keys.
   - Assessment of whether duplicates represent identical entries or contradictory prices.
4. **Price Quality Checks & Domain Sanity:**
   - Investigation of the 6 rows violating $Min \le Modal \le Max$.
   - Identification of extreme outliers (e.g. Wood, Poppy Seeds, Dried Mango) and unit consistency.
5. **Observation Gap Analysis by Series:**
   - Computation of gap lengths (1 day, 2–3 days, 7+ days) across all series.
   - Separation of structural Sunday market closures from non-random administrative slumps.
6. **Exact Calendar-Day $T+3$ and $T+7$ Target Matching:**
   - Measurement of exact matching at $T+3$ and $T+7$ calendar days.
   - Verification that no substituted or next-available observations are used.
7. **Target Coverage & Match Denominators:**
   - Computation of exact match denominators: overall, by district, and by commodity.
   - Identification of series with $<50\%$ vs $\ge 80\%$ continuity.
8. **Target Class Distributions:**
   - Empirical distribution of percentage changes $R_3$ and $R_7$.
   - Measurement of sticky-price rates ($R = 0.00\%$) and evaluation of $\pm 2.5\%$ threshold sensitivity.
9. **Observation Lag (`shift(k)`) vs Calendar Lag ($T-k$) Reform:**
   - Quantitative evaluation of lag distortion in `shift(1)`, `shift(3)`, and `shift(7)`.
   - Prototyping calendar-aware lag merges with bounded staleness.
10. **Automated Unit & Regression Tests:**
    - Implementation of formal pytest suites under `backing/phase_01/tests/`.

---

## 2. Directory & Output Structure for Phase 1

When Phase 1 is executed, artifacts will be deposited strictly within the following reserved directories:

- **Evidence:** [`backing/phase_01/evidence/`](./evidence/)
  - Raw gap histograms, per-commodity continuity tables, and market name mapping tables.
- **Outputs:** [`backing/phase_01/outputs/`](./outputs/)
  - Machine-readable CSV/JSON summaries: `gap_distribution_by_series.csv`, `t7_continuity_by_commodity.csv`, `market_canonicalization_map.json`.
- **Tests:** [`backing/phase_01/tests/`](./tests/)
  - Test scripts: `test_data_integrity.py`, `test_calendar_matching.py`.

---

## 3. Limitations, Risks, and Open Questions

1. **Date Collisions:** Does stripping ` APMC` create conflicting duplicate records on overlapping transition dates?
2. **Commodity Filtering:** Which low-continuity commodities (<50% T+7 coverage) must be excluded from automated forecasting?
3. **Staleness Bound:** What is the maximum acceptable calendar staleness (e.g., 2 days vs 3 days) for forward-filling lag features?

---

## 4. Phase Completion Criteria

Phase 1 will be marked **COMPLETED** only when:
- [ ] All 10 work packages have been executed.
- [ ] All machine-readable outputs are written to `backing/phase_01/outputs/`.
- [ ] Automated tests in `backing/phase_01/tests/` pass.
- [ ] Findings and exact metrics are recorded in this document.
- [ ] Master audit report [`backing/PROJECT_AUDIT.md`](../PROJECT_AUDIT.md) is updated.
