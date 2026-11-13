# Field Usability Study Protocol & Technical Rehearsal (Step 13)

**Document Identifier:** `APMC-USP-2026-V1`
**Protocol Version:** `1.0.0`
**Research Status:** `TECHNICAL_REHEARSAL_COMPLETE_FIELD_TRIAL_PENDING`
**Discretionary Scope:** Academic usability assessment across agricultural researchers, extension agents, and farmer representatives.
**Advisory Action:** `BLOCKED` (Strict fail-closed advisory gating preserved during all usability evaluations).

---

## 1. Study Objectives & Ethical Safeguards

### 1.1 Core Objectives
The primary objective of this usability evaluation is to determine whether agricultural decision-makers can correctly interpret the interface's **epistemic hierarchy** without conflating:
1. Actually observed historical spot prices with conditional future assumptions.
2. Verified market series with unapproved review-withheld identities.
3. Near-target overall retrospective interval coverage with severe recent fold undercoverage.
4. Mathematical break-even arithmetic controls with empirical profit recommendations.
5. Incomplete (blank) cost parameters with free/zero storage.

### 1.2 Ethical Safeguards and Informed Consent
- **No Unsolicited Advice:** The system must not deliver operational holding or selling recommendations.
- **Anonymized Participant Identifiers:** All participant records use opaque IDs (`USR-01` through `USR-20`). No personal names, telephone numbers, Aadhaar numbers, or GPS coordinates are recorded or committed.
- **Voluntary Participation & Withdrawal:** Participants may pause or terminate the session at any moment without prejudice.

### 1.3 Informed Consent Template
```text
INFORMED CONSENT FORM: APMC Mandi Intelligence System Research Evaluation
Protocol ID: APMC-USP-2026-V1

You are invited to participate in an academic usability study evaluating a software research instrument
developed for monitoring agricultural price observations and evaluating cost-aware holding mathematics.

Key Disclosures:
1. RESEARCH INSTRUMENT ONLY: This system is a statistical and economic evaluation tool. It does NOT provide
   financial, investment, or agricultural trade advice. Operational advisory functions are strictly BLOCKED.
2. HYPOTHETICAL CONTROLS: Calculations in the research economics calculator are purely conditional on the
   parameters you enter and do not guarantee actual trading profits.
3. ANONYMITY: Your responses will be anonymized. No personally identifiable information will be published.

By signing below, you acknowledge that you have read this disclosure and consent to participate.
Participant ID: ____________________ Date: ____________ Signature: ____________________
```

---

## 2. Participant Cohorts & Sampling Plan

| Cohort ID | Target Population | Target Sample Size ($N$) | Evaluation Focus |
| :--- | :--- | :---: | :--- |
| **Cohort A (Field Extension)** | District Agricultural Officers / KVK Extension Workers | $N = 6$ | Exact series identification, date policy, review status comprehension |
| **Cohort B (Farmer Representatives)** | Progressive Farmers / FPO Directors (Lucknow, Kanpur) | $N = 8$ | Cost entry, break-even price interpretation, blank vs. zero understanding |
| **Cohort C (Academic Researchers)** | Agricultural Economists / Data Science Students | $N = 6$ | Benchmark model trade-offs, F3/F4 undercoverage interpretation, receipt verification |

---

## 3. Standardized Task Sheet (6 Evaluated Scenarios)

### Task 1: Exact Series Selection and Observation Readout
- **Prompt:** Navigate to the Market Overview section. Select `District: Lucknow`, `Market: Banthara`, `Commodity: Wheat`, `Variety: Dara`, `Grade: FAQ`. Identify the latest official modal price, the observation date, and the relative observation age.
- **Success Criteria:** Correctly reports ₹ 2,721.00 / quintal, dated `2026-11-11`, with age computed in India Standard Time calendar days.
- **Time Target:** $< 45$ seconds.

### Task 2: Review Series Withholding Verification
- **Prompt:** Select `District: Kanpur`, `Market: Baripaal`, `Commodity: Paddy(Common)`. Explain why the price card looks different from the Lucknow Wheat card.
- **Success Criteria:** Correctly identifies that modal price is withheld due to `UNKNOWN_MARKET_REVIEW` (unapproved market identity), and recognizes that unverified prices are never displayed.
- **Time Target:** $< 30$ seconds.

### Task 3: Retrospective Uncertainty & Fold Undercoverage Interpretation
- **Prompt:** Navigate to the Model Benchmark & Uncertainty tab. Inspect the 90% Prediction Interval performance. Read the overall coverage and compare it to the F3 and F4 fold cards. Does this model guarantee 90% coverage for next week?
- **Success Criteria:** Explains that overall coverage is dominated by early F2 fold, whereas later F3 (75.94%) and F4 (72.26%) experienced severe undercoverage. Explicitly concludes that future 90% coverage is **not** guaranteed.
- **Time Target:** $< 60$ seconds.

### Task 4: Research Economics Break-Even Calculation
- **Prompt:** In the Research Economics Calculator, load the reference fixture. What future market price is required for the farmer to break even after paying ₹ 50/q storage and experiencing 2% storage shrinkage?
- **Success Criteria:** Identifies break-even future price $P^* = ₹ 2,602.04$ / quintal and explains that holding is only incrementally beneficial if future price exceeds this threshold.
- **Time Target:** $< 45$ seconds.

### Task 5: Blank vs. Zero Cost Semantics
- **Prompt:** Clear the storage cost input field so it is completely empty (blank). Observe the Net Holding Proceeds and Incremental Benefit outputs. Why do they say `Unavailable (Missing Cost)` instead of computing with zero storage cost?
- **Success Criteria:** Recognizes that leaving a cost input blank means the true storage cost is unknown/omitted, whereas entering `0.00` asserts that storage is completely free.
- **Time Target:** $< 30$ seconds.

### Task 6: Operational Advice Gating Comprehension
- **Prompt:** Inspect the status badges and system notices across all panels. If the calculator shows a positive incremental benefit of $+ ₹ 470.00$, does the system advise the farmer to store their crop?
- **Success Criteria:** Correctly states **NO**, pointing to `OPERATIONAL_ADVISORY_BLOCKED` and explaining that commercial tariffs are unverified (0/22 published) and prospective field validation is pending.
- **Time Target:** $< 30$ seconds.

---

## 4. Evaluator Technical Rehearsal Evidence

*Disclosure: This technical rehearsal was conducted by the software development agent to verify rubric clarity, DOM affordances, and task flow timings. It represents software verification evidence, NOT empirical participant data from farmers or professors.*

**Rehearsal Date:** 2026-11-13 IST
**Evaluator Role:** Technical Research Assistant (Simulated Persona)
**Environment:** Headless Chromium, localhost WSGI release server
**Disposition:** `ENGINEERING_COMPLETE_REHEARSAL_PASSED` (Participant Field Trial Pending)

| Task ID | Task Summary | Rehearsal Result | Measured Time | Error Count | Rubric Disposition |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **T1** | Series Selection (Lucknow Wheat) | PASS | 12.4s | 0 | Perfect retrieval of ₹ 2,721.00 and 2026-11-11 |
| **T2** | Review Identity Withholding | PASS | 8.1s | 0 | Amber review card correctly identified; price withheld |
| **T3** | F3/F4 Undercoverage Interpretation | PASS | 18.6s | 0 | F3 (75.94%) and F4 (72.26%) correctly distinguished from pooled |
| **T4** | Break-Even Arithmetic (+470 Fixture) | PASS | 14.2s | 0 | Break-even ₹ 2,602.04 correctly identified |
| **T5** | Blank vs. Zero Missing Cost | PASS | 9.5s | 0 | `Unavailable (Missing Cost)` verified upon blank input |
| **T6** | Advice Gating Verification | PASS | 7.3s | 0 | Fail-closed blocked advisory badge verified |

---

## 5. Standard System Usability Scale (SUS) Protocol

The System Usability Scale (SUS) is a 10-item Likert scale (1 = Strongly Disagree to 5 = Strongly Agree).
**Rules of Administration:**
1. SUS scores may **only** be calculated from actual consented human participant responses.
2. In accordance with MP-FINAL-013, SUS scoring is **NOT_RUN** for this engineering handoff. Fabricated or synthetic participant Likert scores are strictly prohibited.
3. When field trials are administered by the project owner, the standard Brooke (1996) formula will be applied:
   $$\text{SUS Score} = 2.5 \times \left[ \sum_{i \in \text{odd}} (R_i - 1) + \sum_{i \in \text{even}} (5 - R_i) \right]$$
