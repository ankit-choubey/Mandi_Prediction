# Prospective Shadow Validation Protocol (Step 13)

**Protocol Identifier:** `APMC-PV-2026-V1`
**Version:** `1.0.0`
**Status:** `FROZEN_BEFORE_OUTCOMES`
**Target Region:** Uttar Pradesh (Ghaziabad, Jhansi, Kanpur, Lucknow, Unnao)
**Reference Model:** Naive Persistence ($\hat{P}_{t+7} = P_t$)
**Advisory Action:** `BLOCKED` (Strict separation between research reliability evaluation and operational advice)

---

## 1. Scope, Objectives & Invariants

This protocol governs the prospective forward validation (Milestone Step 13) of agricultural mandi modal price forecasting in Uttar Pradesh. In accordance with strict scientific evaluation standards:
1. **Zero Retrospective Contamination:** Forecast issuance records must be generated, cryptographically hashed, and committed *before* target market outcomes occur.
2. **Persistence as Prospective Reference:** Naive persistence ($\hat{P}_{t+7} = \text{most recent permitted modal price observed at or before issuance}$) serves as the prospective reference standard. Retrospective candidates (Ridge, HistGradientBoosting) remain frozen retrospective development artifacts and are **not** deployed to forward operations until separately shown compatible with live runtime feature pipelines and approved under a formal challenger protocol.
3. **Candidate Panel Disambiguation:** The active 30-series candidate cohort (26 accepted, 4 review-withheld) does **not** inherit legacy benchmark error distributions or coverage rates from the 463,217-row retrospective archive. It forms an independent forward evaluation population (`cohort_id: UP_CANDIDATE_2026_COHORT_A`).
4. **Interval Status Explicitly UNAVAILABLE:** Historical calibration envelopes from earlier folds cannot guarantee future coverage under non-stationary market regimes. Forward prediction intervals remain `UNAVAILABLE` unless a past-only rolling calibration protocol is specifically approved. No forward 90% coverage guarantee is claimed or assumed.
5. **Separation of Forecasting and Operational Advisory:** Gating metrics evaluate mathematical forecast error only. Satisfying statistical criteria does **not** authorize active farmer advisory. Advisory remains fail-closed `BLOCKED`.

---

## 2. Eligible Cohort & Data Provenance Policy

### 2.1 Eligible Series Definition
A series is eligible for prospective shadow issuance if and only if all of the following conditions are met:
- **Geographic Boundary:** APMC mandi located within the five declared districts (Ghaziabad, Jhansi, Kanpur, Lucknow, Unnao).
- **Approved Commodity & Identity:** Canonical identity verified against the declared six focus crops (`Wheat`, `Potato`, `Onion`, `Tomato`, `Paddy(Common)`, `Rice`) or approved regional commodities.
- **Review Status:** Market identity status is `ACCEPTED` (`price_display_permitted = true`). Series flagged as `UNKNOWN_MARKET_REVIEW` (e.g. Kanpur Baripaal APMC) are **abstained** with reason `UNKNOWN_MARKET_IDENTITY_REVIEW`.
- **Unit Standard:** Price reported in official Indian Rupees per quintal (`INR/quintal`). Any alternate unit basis is rejected.
- **Positivity Guard:** Modal price $P_t > 0$, finite float.

### 2.2 Freshness & Preflight Validity Policy
- **Maximum Allowable Observation Age:** At issuance, the source observation date must be **no older than one India Standard Time (IST) calendar day** relative to the current IST date ($\Delta \text{days} \le 1$).
- **Stale Observation Policy:** If the latest available observation is $> 1$ calendar day old at the time of snapshot processing, the series is **abstained** with code `STALE_OBSERVATION_EXCEEDS_1_DAY`. Eligibility rules will **never** be silently relaxed to force issuance of stale observations.
- **Auction Timing Reality:** Official Agmarknet daily price bulletin files provide date-level modal prices, not auction clock timestamps. The system records `source_observation_date`, `file_import_timestamp_utc`, and `issuance_timestamp_utc`. Pre-auction issuance is not claimed without certified exchange timestamp receipts.

---

## 3. Issuance & Immutability Rules

### 3.1 Idempotency and Append-Only Registry
- Each shadow forecast record is written to an append-only JSON Lines registry (`data/shadow_registry/forward_forecast_log.jsonl`).
- The canonical record key is `(cohort_id, protocol_version, series_id, origin_date, target_expected_date)`.
- Reissuance attempts with conflicting forecast values are strictly rejected with an integrity error.
- Accidental tampering is detected via record SHA-256 hash chaining:
  $$H_k = \text{SHA-256}(H_{k-1} \,||\, \text{CanonicalJSON}(R_k))$$
  *Disclosure: Hash chaining verifies local sequential file integrity; it is not an externally notarized or blockchain timestamp.*

### 3.2 Shadow Record Schema
Each issued shadow record must contain:
```json
{
  "record_id": "SHD-20261113-LKW-WHT-001",
  "cohort_id": "UP_CANDIDATE_2026_COHORT_A",
  "protocol_version": "1.0.0",
  "config_hash": "<SHA-256 of frozen config>",
  "code_version": "git-6af1dbc0",
  "series_id": "up_lucknow_banthara_wheat_dara_faq",
  "canonical_identity": {
    "district": "Lucknow",
    "market": "Banthara",
    "commodity": "Wheat",
    "variety": "Dara",
    "grade": "FAQ"
  },
  "origin_observation_date": "2026-11-12",
  "origin_modal_price": 2721.0,
  "units": "INR/quintal",
  "source_index_file_sha256": "45c9dd75fcfc519e60911bff64bc7eaa91012c974bec4a5596d83af4340563d4",
  "composite_source_sha256": "3d3bc047440186eed49a8764eb28387a99e7293cdc9b62f1d30290b855fedb11",
  "issuance_timestamp_utc": "2026-11-13T00:15:00Z",
  "target_expected_date": "2026-11-19",
  "target_window_min_date": "2026-11-18",
  "target_window_max_date": "2026-11-20",
  "model_id": "naive_persistence",
  "point_forecast": 2721.0,
  "interval_status": "UNAVAILABLE",
  "status": "ISSUED",
  "abstention_reason": null,
  "prev_record_hash": "<hex>",
  "record_hash": "<hex>"
}
```

---

## 4. Outcome Matching & Maturation Policy

### 4.1 Target Window ($T+7$ Nominal, 6–8 Day Tolerance)
Consistent with frozen benchmark settings (Step 6/7 feature contract):
- Nominal horizon: $T + 7$ calendar days.
- Allowable match window: $[T + 6, T + 8]$ calendar days.
- **Tie-Breaking Rule:** If multiple valid market observations occur within the $[T+6, T+8]$ window:
  1. Exact $T+7$ day match takes absolute precedence.
  2. If $T+7$ is absent, the date closest to $T+7$ is selected ($|t_{\text{obs}} - (T+7)| = 1$).
  3. If $T+6$ and $T+8$ are both present and $T+7$ is missing, the earlier date ($T+6$) is selected by convention.
- **Maturity Rule:** Matching is **only finalized** after the full target window closes ($t_{\text{current}} > T + 8$ IST). Until $T+8$ closes, the forecast remains in `PENDING_MATURATION` status.

### 4.2 Handling Missing and Revised Outcomes
- If no valid observation is recorded for the exact series within $[T+6, T+8]$, the outcome is marked `UNMATCHED_NO_OBSERVATION`. It is not backfilled from neighboring markets or synthetic interpolations.
- If official Agmarknet sources post a revised price for a previously matched date, the revision is logged in an append-only revision ledger (`data/shadow_registry/outcome_revisions.jsonl`). Primary scorecards use the first verified publication; a secondary sensitivity scorecard reports post-revision impact.

---

## 5. Evaluation Metrics & Minimum Evidence Plan

### 5.1 Predeclared Metrics
- **Primary Metric:** Mean Absolute Error (MAE), expressed in INR/quintal:
  $$\text{MAE} = \frac{1}{N} \sum_{i=1}^N |y_i - \hat{y}_i|$$
- **Secondary Metrics:**
  - Root Mean Squared Error (RMSE), in INR/quintal.
  - Mean Directional Bias: $\frac{1}{N} \sum (y_i - \hat{y}_i)$.
  - Mean Absolute Percentage Error (MAPE):
    $$\text{MAPE} = \frac{1}{N} \sum_{i=1}^N \frac{|y_i - \hat{y}_i|}{y_i} \times 100\% \quad (y_i > 0)$$
  - Tolerance Accuracy (Within 5% of realization):
    $$\text{Accuracy}_{\pm 5\%} = \frac{1}{N} \sum_{i=1}^N \mathbb{I}\left(\frac{|y_i - \hat{y}_i|}{y_i} \le 0.05\right) \times 100\%$$
    *(Clarification: this is a specific tolerance rate, NOT continuous regression accuracy = $100 - \text{MAPE}$).*
  - Issuance Rate and Abstention Rate.
- **Stratification:** Metrics must be reported by commodity, district, and market, with explicit sample size $N$ and a `LOW_N` flag for slices with $N < 30$.

### 5.2 Minimum Evidence Plan
- **Sample Size Target:** A minimum plan of $N \ge 150$ matured forward forecast origins across at least 15 active series over a continuous 6-week operational shadow monitoring window.
- **Statistical Independence Disclosure:** Daily observations within the same market and crop are temporally autocorrelated and spatially correlated across neighboring APMCs. Therefore, standard i.i.d. Gaussian confidence intervals are invalid. Standard errors must use block-bootstrap by calendar week or clustered standard errors by mandi-crop series.

---

## 6. Model Success Gates vs. Advisory Authorization

Passing prospective evaluation gates does **not** equal advisory authorization:

| Milestone / Gate | Criteria | Authority Granted Upon Pass |
| :--- | :--- | :--- |
| **Gate 1: Forward Implementation Integrity** | Zero schema, hash, or timing anomalies over 6 weeks | Certifies prospective software pipeline |
| **Gate 2: Baseline Benchmark Competence** | Candidate model achieves lower primary MAE than Naive Persistence on matched forward origins | Validates statistical candidate superiority |
| **Gate 3: Empirical Uncertainty Reliability** | Calibrated forward intervals achieve $\ge 85\%$ empirical coverage on out-of-sample forward cohort | Validates risk interval calibration |
| **Gate 4: Operational Farmer Advisory** | **Requires separate ethical, commercial tariff ($>0/22$), and field usability sign-off** | **STRICTLY BLOCKED AT PRESENT** |
