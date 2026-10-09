# Phase 1 Unresolved Questions & Methodological Blockers

**Audit Phase:** Phase 1 — Data Integrity & Temporal Continuity  
**Date:** October 10, 2026  

---

## 1. Newly Identified Methodological Blockers in Phase 1

### Question 1: Reconciliation of 4,380 Conflicting Duplicate Rows
- **Finding:** 4,380 date-series groups contain multiple records with different modal or spread prices on the exact same calendar date.
- **Previous Action:** Original pipeline executed `df.drop_duplicates(keep='first')`, silently dropping the second record based on arbitrary CSV row ordering.
- **Unresolved Decision:** What is the scientifically defensible method to reconcile these records?
  - *Option A (Daily Average):* Replace duplicate rows with their mean or median price.
  - *Option B (Ambiguity Flag):* Retain the median price but add an explicit binary indicator `Is_Ambiguous_Price_Date = 1`.
  - *Option C (Exclusion):* Drop ambiguous dates from model training to avoid training on contradictory labels.
- **Audit Recommendation:** Option B (impute median + flag ambiguity) preserves sample volume while informing models of label uncertainty.

---

### Question 2: Correction of 6 Inverted Price Rows (Max_Price = 0)
- **Finding:** Exactly 6 rows have `Max_Price = 0.0` while `Modal_Price > 0.0` (e.g. Jhansi 2025-05-14 Wheat Modal=2,450, Max=0; Kanpur grain rows Modal=8,770, Max=0).
- **Previous Action:** Original pipeline left them intact, leading to negative intraday spread calculations (`Max - Min < 0`).
- **Unresolved Decision:** How should these 6 rows be cleaned?
  - *Option A:* Impute `Max_Price = Modal_Price` (assuming max was at least modal price).
  - *Option B:* Drop all 6 rows (representing only 0.0037% of the dataset).
- **Audit Recommendation:** Option A is domain-consistent; alternatively Option B has negligible statistical impact.

---

### Question 3: Market Mapping & Canonicalization Boundaries
- **Finding:** 19 market pairs represent clean pre- and post-November 2025 transitions (`<Market>` $\to$ `<Market> APMC`). However:
  - In **Jhansi District**, `Jhansi` and `Jhansi (Grain)` ran concurrently as separate physical yards with 306 overlapping dates. They must **not** be merged into a single market.
  - In **Kanpur District**, `Varipaal APMC` (stopped April 2026) and `Baripaal APMC` (started March 2026) overlapped for 56 calendar days.
- **Unresolved Decision:** How should the canonical mapping be structured?
  - **Proposed Action:** Formally adopt the mapping table in [`backing/phase_01/outputs/market_mapping_review.csv`](../outputs/market_mapping_review.csv) where `Jhansi` and `Jhansi (Grain)` remain distinct, but APMC suffixes are unified with their parent base yards.

---

### Question 4: Commodity Screening Threshold for Automated Models
- **Finding:** Exact $T+7$ target continuity is 81.9% for Potato, 81.7% for Onion, and 79.5% for Tomato, but drops to **15.2% for Sesame/Til** and **15.3% for Lobia**. Overall, **31.7% of all series have <50% T+7 continuity**.
- **Unresolved Decision:** Should commodities with $<50\%$ or $<60\%$ continuity be excluded from production ML training?
- **Audit Recommendation:** Yes. Enforcing a minimum 60% T+7 continuity threshold prevents models from learning noisy, sporadic price jumps from seasonal or low-volume pulses.

---

### Question 5: Bounded Staleness in Calendar Lags ($T-k$)
- **Finding:** When transitioning from observation shift (`shift(7)`) to calendar joins (`T - 7 days`), Sunday closures and reporting lapses mean that exact $T-7$ is missing in ~22% of rows.
- **Unresolved Decision:** How should feature engineering handle missing calendar days?
  - *Option A:* Strict join; if $T-7$ is unobserved, feature is `NaN` (handled by imputation).
  - *Option B:* Bounded forward-fill; look back up to $\le 2$ calendar days (accepting $T-8$ or $T-9$ if $T-7$ was a Sunday), accompanied by a `Days_Since_Observed_Price` feature.
- **Audit Recommendation:** Option B aligns with how human traders interpret prices after a Sunday closure.
