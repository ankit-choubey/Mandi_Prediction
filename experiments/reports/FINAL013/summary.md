# Task MP-FINAL-013: Final UI Closure, Prospective Validation Protocol, and Academic Handoff Summary

**Execution Date**: 2026-11-13 IST
**Task ID**: `MP-FINAL-013`
**Git HEAD Target**: `feat(validation): close UI math and add prospective shadow workflow [MP-FINAL-013]`
**Execution Mode**: Pure Python standard library serving + Vanilla HTML5/CSS3/ES6+ + Node.js native CDP test driver.

---

## 1. Executive Summary

Task `MP-FINAL-013` executes the final engineering and validation phase of the Mandi Price Intelligence System. It accomplishes three primary objectives:
1. **Closes all 6 reproduced UI002 defects** documented in `documentation/UI002_INDEPENDENT_REVIEW.md`, including mathematical equation sign accuracy, authoritative server-side Decimal waterfall decomposition, dynamic provenance hashes in the Reproducibility Drawer, epistemic separation between snapshot import and server execution timestamps, explicit minus sign rendering for negative price movements, and print-media series identity retention.
2. **Freezes the Prospective Validation Architecture** before any forward observations are recorded:
   - Protocol Document: `documentation/FORWARD_VALIDATION_PROTOCOL.md` (Protocol ID `APMC-PV-2026-V1`).
   - Versioned Specification: `experiments/configs/forward_validation_protocol_v1.json`.
   - Bounded Standard-Library CLI: `src/prospective_shadow.py` with append-only JSONL shadow ledger, SHA-256 chaining, process-safe file locking, and staleness/review fail-closed gates.
   - Comprehensive Test Suite: `tests/test_prospective_shadow.py` (6 unit tests passing).
3. **Formalizes the Academic Evaluation Framework**:
   - Realistic Usability Study Protocol: `documentation/USABILITY_STUDY_PROTOCOL.md` with 6 standardized APMC evaluator tasks, informed consent template, Brooke (1996) SUS instruments, and evaluator technical rehearsal evidence.
   - Feature Inventory and Model Comparison Scorecard: `documentation/PROJECT_FEATURES_AND_SCORECARD.md` establishing model trade-offs, literature benchmarks, regression-vs-classification framing, and the optional RAG architectural recommendation.

---

## 2. Six UI002 Defect Closures & Verification Evidence

All 6 review findings identified in `documentation/UI002_INDEPENDENT_REVIEW.md` were repaired in production code and verified via headless Chromium through Chrome DevTools Protocol (`experiments/reviews/test_final013_acceptance.js`):

| Finding ID | Defect Description | Production Fix Implemented | Verification Evidence |
| :--- | :--- | :--- | :--- |
| **UI002-FINDING-01** | Break-even equation banner inverted fee signs ($t_n - (1-L)t_l$). | In `src/static/index.html`, corrected formula to: `P* = [P_0(1+f) + c + (1-L)t_l - t_n] / [(1-L)(1-d)]`. | `CHECK_03_BREAK_EVEN_FORMULA_SIGNS` passed. In fee test ($t_n=10, t_l=20$), break-even matches exact Decimal ₹ 2,611.84 / q. |
| **UI002-FINDING-02** | Holding proceeds decomposed on client using undefined fields, mislabeling net as gross. | Added authoritative `waterfall_components` to `src/economic_model.py` and rendered directly in `src/static/app.js`. Preserved blank-vs-zero semantics. | `CHECK_07` (reference fixture 25970 / 500 / 25470 / +470), `CHECK_08` (financing ₹ -33.56 / +436.44), `CHECK_09` (fees ₹ -100 / ₹ -196 / +374), and `CHECK_10` (missing cost $\to$ `Unavailable`) all passed. |
| **UI002-FINDING-03** | Reproducibility Drawer contained static hardcoded SHA hashes. | In `src/service.py`, dynamically compute SHA-256 of `latest_observation_index.json` on startup; expose via capabilities metadata; populate in `app.js` with live readback. | `CHECK_02_DRAWER_PROVENANCE_HASHES` passed on healthy server (`45c9dd75...` and `3d3bc047...`); `CHECK_14` confirmed hashes revert to `Unavailable` in degraded mode. |
| **UI002-FINDING-04** | Single "Updated" timestamp conflated snapshot import time with server evaluation time. | Separated masthead metadata into `Snapshot:` import timestamp (`generated_at_utc`) and `Server:` runtime timestamp (`server_time_utc`), plus IST calendar date on observation card. | `CHECK_01_HEALTHY_TIMESTAMPS` passed with distinct timestamps. |
| **UI002-FINDING-05** | Negative price changes omitted explicit minus sign (displayed `₹ 79.00`). | Updated `renderPriceMovement` in `src/static/app.js` to prepend explicit minus sign: `− ₹ X.XX (−X.XX%)`. | `CHECK_06_NEGATIVE_DELTA_MINUS_SIGN` passed (`− ₹ 79.00 (−2.82%)`). |
| **UI002-FINDING-06** | Browser test checked existence of DOM nodes without verifying numeric contents; print media dropped series identity. | Added `#print-series-identity` element in `index.html` and `.print-series-header` in `styles.css`. Strengthened test assertions across all visible numbers. | `CHECK_04` & `CHECK_12` passed. Headless Chromium print emulation screenshot confirmed series identity retention. |

---

## 3. Prospective Validation Architecture

- **Protocol Reference Standard**: The audited Naive Persistence benchmark (OOS MAE 106.96 INR/q) serves as the frozen baseline. Candidate models (`UP_CANDIDATE_2026_COHORT_A`: HistGradientBoosting and Ridge) must beat persistence on primary MAE with out-of-sample data.
- **Freshness Policy**: Observations older than 1 calendar day in India Standard Time are automatically abstained (`STALE_OBSERVATION_EXCEEDS_1_DAY`).
- **Nominal Horizon**: $T+7$ calendar days with strict $6 \le \Delta t \le 8$ window matching and tie-breaking by lowest $|\Delta t - 7|$, then earliest arrival time.
- **Real Snapshot Smoke Test**: Run on actual snapshot (`latest_observation_index.json`, dated 2026-11-11; evaluated 2026-11-13 IST):
  - Total eligible series evaluated: 11
  - Issued point forecasts: 0 (zero synthetic or backdated forecasts generated)
  - Abstained stale: 9 series (observation age: 2 days $> 1$ day allowed)
  - Abstained review: 2 series (`UNKNOWN_MARKET_IDENTITY_REVIEW`)
  - Out of candidate scope: 19 series
  - Maturation scorecard: Honestly reports `EMPIRICAL_PENDING` (forward outcomes have not yet closed).

---

## 4. Verification Receipts and Suite Pass Rates

| Test Driver / Suite | Scope | Pass Rate | Execution Time |
| :--- | :--- | :--- | :--- |
| `test_final013_acceptance.js` | 17 comprehensive acceptance & parity checks | **17/17 passed** (100%) | 18.2s |
| `test_interactive_browser_flows.js` | 21 end-to-end interactive browser flows | **21/21 passed** (100%) | 8.1s |
| `check_app001a_review_gates.py` | 29 contract and boundary review gates | **29/29 passed** (100%) | 0.4s |
| `tests/` unit & integration test suite | 385 tests (including 6 shadow CLI tests) | **385 passed**, 18 warnings | 11.6s |
| `backing/` verification suite | 45 offline model and math tests | **45 passed** (100%) | 5.4s |
| `test_ui_serving.py` & `test_integration_release.py` | Clean checkout simulation | **16 passed** (100%) | 1.0s |
| **Combined Regression Pass Rate** | **Total Verification Checks** | **508 passed, 0 failures** | ~45s |

---

## 5. Output Artifact Inventory (`experiments/reports/FINAL013/`)

| File Name | Size (Bytes) | SHA-256 Digest | Description |
| :--- | :--- | :--- | :--- |
| `acceptance_checks_receipt.json` | 20,151 | `ec4f4540a931...` | Structured JSON log of all 17 CDP acceptance checks |
| `prospective_cli_smoke_receipt.json` | 2,172 | `a90623114d59...` | CLI execution receipt of init, validate, issue, and score |
| `screenshot_desktop_1440x900.png` | 137,132 | `96a24eb5ef74...` | Desktop 1440x900 viewport capture |
| `screenshot_desktop_1280x800.png` | 118,688 | `6908480d1964...` | Desktop 1280x800 viewport capture |
| `screenshot_mobile_375x667.png` | 55,404 | `4d1fc3bc5244...` | Mobile 375x667 viewport capture with zero overflow |
| `screenshot_print_preview.png` | 57,212 | `3da95b77e822...` | Headless Chromium print media emulation screenshot |
| `output_manifest.json` | 1,667 | `(self-excluding)` | Cryptographic SHA-256 manifest of report files |

---

## 6. Project Disposition & Remaining Action Accounting

- **Task Status**: MP-FINAL-013 complete.
- **Docker Daemon Packaging**: Disposed as `NOT_RUN` (deliberate local infrastructure decision; launcher, healthcheck, clean-checkout tests, and static serving run natively via standard library).
- **Step 13 Prospective Validation**: Disposed as `ENGINEERING_COMPLETE_EMPIRICAL_PENDING` (protocol frozen, shadow CLI operational, zero fabricated outcomes).
- **Usability Study**: Disposed as `TECHNICAL_REHEARSAL_COMPLETE_FIELD_TRIAL_PENDING` (rehearsal passed, participant Likert scores cannot be manufactured).
- **Main Milestones Remaining**: Exactly **0 engineering milestones** remain. Prospective empirical maturation and human usability trials await future calendar dates.
- **Optional Ablations Remaining**: Exactly **2 optional research ablations** remain (arrivals and localized weather).
