# Mandi Prediction Data Handling Policy

**Version:** 2.0 (Phase 02 Remediation)  
**Status:** Defensible Methodology Policy  
**Effective Date:** 2026-10-10  
**Scope:** All data ingestion, preprocessing, feature engineering, and model evaluation in `Mandi_Prediction`

---

## 1. Core Principle of Non-Destructive Auditing

1. **Raw Data Invariance:** The raw files in `data/raw/` (`Gaziabaad.csv`, `Jhansi.csv`, `Kanpur.csv`, `Lukhnow.csv`, `Unnao.csv`) are permanent historical artifacts. They must never be edited, overwritten, truncated, or cleaned in place.
2. **Explicit Transformations:** Every filtering, aggregation, mapping, or classification step must be implemented as a reproducible, non-destructive transformation with explicit denominators and exclusion reasons logged.

---

## 2. Duplicate Record Handling Policy

In the raw dataset of 160,192 records, 4,393 series-date groups share the identical key `(District, Market, Commodity, Variety, Arrival_Date)`:

| Category | Definition | Count | Policy Treatment |
|---|---|---|---|
| **Category A** | Completely identical across all 11 columns | 0 | True deduplication permissible (0 instances found). |
| **Category B** | Conflicting `Modal_Price` | 4,363 | Ambiguous pricing. **Do not silently drop.** |
| **Category C** | Identical `Modal_Price`, conflicting `Min_Price`/`Max_Price` | 17 | Price spread ambiguity. |
| **Category D** | Differing `Grade` within group (e.g. FAQ vs Medium) | 3,096 | **Resolved by Grade Stratification.** Commercial quality tiers must be included in the series key. |
| **Category E** | Conflicting prices with identical `Grade` | 1,287 | Unresolvable reporting ambiguity. |

### Prescribed Actions:
1. **Primary Series Key Formulation:**
   The canonical series key must be stratified by Grade:
   $$\text{series\_key} = \text{District} \parallel \text{Market} \parallel \text{Commodity} \parallel \text{Variety} \parallel \text{Grade}$$
   This resolves 70.5% (3,096 groups) of apparent duplicate records by recognizing legitimate commercial grade pricing.
2. **Treatment of Intra-Grade Conflicts (1,287 groups / 2,642 rows):**
   - **For Training & Benchmark Datasets (Strategy 2):** Exclude ambiguous series-dates completely to guarantee 100% label purity and avoid fitting models on arbitrary raw file order.
   - **For Sensitivity & Volume Testing (Strategy 3):** Aggregate conflicting daily quotes using the median price. Must be reported as a sensitivity check, never as authoritative ground truth.
   - **Prohibited Action (Strategy 5):** Calling `.drop_duplicates(subset=..., keep='first')` is strictly prohibited. It introduces order-dependent label corruption.

---

## 3. Canonical Market Identity Policy

Between November 1 and November 5, 2025, the AGMARKNET portal updated market reporting strings statewide by appending `" APMC"` to existing market names.

### Prescribed Rules:
1. **Preserve Raw Strings:** Raw market names must be preserved in all database columns (`Market_Raw`).
2. **Explicit Canonical Lookup:** Canonical market identities (`Market_Canonical`) must be joined via the audited mapping table [canonical_market_mapping.csv](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/backing/phase_02/outputs/canonical_market_mapping.csv).
3. **Approved Pre/Post Transitions:** 19 market pairs represent unambiguous statewide portal naming transitions (e.g., `Ghaziabad` $\to$ `Ghaziabad APMC`, `Noida` $\to$ `Noida APMC`). These mappings are APPROVED for temporal continuity.
4. **Strict Separation of Concurrent Yards:**
   - In Jhansi district, `Jhansi` (general municipal yard) and `Jhansi (Grain)` (specialist grain yard) operated concurrently across 306 calendar days.
   - **PROHIBITION:** `Jhansi` and `Jhansi (Grain)` must **never** be merged. They represent distinct physical trading locations.
5. **Handling Phonetic Spelling Variants:**
   - In Kanpur district, `Baripaal APMC` appeared in March 2026 alongside `Varipaal APMC` with 56 overlapping dates. This mapping remains `PROPOSED / MEDIUM CONFIDENCE` and must not be hardcoded without sensitivity validation.

---

## 4. Historical Lag Feature Policy

Lag features serve as inputs ($X_T$) to forecast future prices ($Y_{T+h}$).

### Prescribed Rules:
1. **Row-Based Shifts Prohibited:**
   The use of `.groupby().shift(k)` is strictly prohibited for calendar-based econometric features. Because mandi auctions close on Sundays, gazetted holidays, and during supply shocks, the $k$-th prior row is irregular. Specifically, `shift(7)` is 7 calendar days ago in only 20.14% of rows, with a mean gap of 11.45 days.
2. **Exact Calendar Joins Required:**
   The standard lag feature must be joined strictly on:
   $$\text{Lag\_Date} = \text{Arrival\_Date} - k \text{ days}$$
   If no auction was recorded on that exact calendar date, the lag value must remain `NaN`.
3. **Bounded Staleness Specifications:**
   If non-trading days (e.g. Sunday closures) must be bridged, the feature must be explicitly named as bounded staleness and declare its maximum permissible lookback window:
   - `Calendar_Lag_1_Bounded2d`: Uses price at $T-1$; if missing, looks back up to $T-3$ (maximum age 3 calendar days).
   - `Calendar_Lag_7_Bounded2d`: Uses price at $T-7$; if missing, looks back up to $T-9$ (maximum age 9 calendar days).
4. **No Lookahead Leakage:** Under no circumstances may an observation from $t > T$ enter any historical feature.

---

## 5. Forecast Target Definition Policy

Target returns are evaluated at horizon $h \in \{3, 7\}$ calendar days.

### Prescribed Mathematical Definitions:
1. **Target Date Matching:**
   Target prices must be matched strictly on:
   $$\text{Target\_Date} = \text{Arrival\_Date} + h \text{ calendar days}$$
   For origin date $T$, if no price is recorded on $T+h$, the target is `NaN`. **Forward-filling or substituting the next available observation is strictly prohibited.**
2. **Continuous Percentage Return:**
   $$R_h = 100 \times \frac{P_{T+h} - P_T}{P_T}$$
3. **Invalid Price Exclusions:**
   Any observation where $P_T \le 0$ or $P_{T+h} \le 0$ must be excluded from return calculations (denominator $\le 0$ is economically invalid).
4. **Boundary Condition Accounting:**
   - **Boundary-Truncated:** Origins where $T + h > \text{Max\_Date}$ (September 1, 2026) cannot be evaluated and must be logged as boundary-truncated ($N=1,005$ at T+7; $N=465$ at T+3).
   - **Interior-Missing:** Origins where $T + h \le \text{Max\_Date}$ but the mandi was closed or did not report are interior-missing ($N=37,560$ at T+7; $N=44,927$ at T+3).
5. **Exact Three-Class Classification Boundaries:**
   When evaluating the 3-class target:
   $$\text{Class} = \begin{cases} \text{Favorable}, & \text{if } R_h \ge +2.5\% \\ \text{Unfavorable}, & \text{if } R_h \le -2.5\% \\ \text{Normal}, & \text{if } -2.5\% < R_h < +2.5\% \end{cases}$$
   The exact boundary cases $R_h = +2.5\%$ and $R_h = -2.5\%$ must be mapped to Favorable and Unfavorable, respectively.
6. **Quantile and Volatility Alternatives:**
   When benchmarking classification models against severe class imbalance (where Normal captures 58–68%), quantile cutoffs or volatility scaling must be estimated strictly on the training partition ($T < \text{2026-01-20}$) and frozen prior to out-of-sample evaluation.
