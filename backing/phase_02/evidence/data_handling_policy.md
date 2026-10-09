# Mandi Prediction Data Handling Policy

**Version:** 2.1 (Phase 02 Correction Pass)  
**Status:** Defensible Methodology Policy  
**Effective Date:** 2026-10-10  
**Branch:** `audit/phase-02-correction-pass`  
**Scope:** All data ingestion, preprocessing, feature engineering, and model evaluation in `Mandi_Prediction`

---

## 1. Core Principle of Non-Destructive Auditing

1. **Raw Data Invariance:** The raw files in `data/raw/` (`Gaziabaad.csv`, `Jhansi.csv`, `Kanpur.csv`, `Lukhnow.csv`, `Unnao.csv`) are permanent historical artifacts. They must never be edited, overwritten, truncated, or cleaned in place.
2. **Explicit Non-Destructive Transformations:** Every filtering, aggregation, mapping, or classification step must be implemented as a reproducible transformation with explicit denominators, input row counts, and exclusion reasons logged.

---

## 2. Duplicate Record Handling Policy

Across the raw dataset of 160,192 records, duplicate analysis must be conducted on the canonical series key that includes commercial `Grade`:
$$\text{series\_key} = \text{District} \parallel \text{Market} \parallel \text{Commodity} \parallel \text{Variety} \parallel \text{Grade}$$

### 2.1 Same-Grade Typology Breakdown
When grouped by `(series_key, Arrival_Date)`, exactly **1,331 duplicate groups (2,684 rows)** exist:

| Category | Definition | Unique Groups | Affected Rows | Policy Treatment |
|---|---|---|---|---|
| **Category A** | Completely identical prices across min, modal, max (and all 11 columns) | 10 | 20 | True deduplication: retain 1 copy, drop duplicate row (10 rows dropped). |
| **Category B** | Conflicting `Modal_Price` within same grade | 1,296 | 2,614 | Ambiguous pricing. **Do not silently drop.** |
| **Category C** | Identical `Modal_Price`, conflicting `Min_Price`/`Max_Price` | 25 | 50 | Price spread ambiguity. |
| **Ambiguous Total** | **Cat B + Cat C** | **1,321** | **2,664** | **Unresolvable reporting ambiguity within same grade.** |

### 2.2 Grade Completeness & Non-Collision
- **Grade Field Completeness:** Verified 100% complete across all 160,192 rows (0 nulls, 0 empty strings). Value distribution: FAQ (139,111), Medium (16,291), Non-FAQ (3,976), Local (564), Large (177), Grade A (25), Grade C (16), Grade Range-2 (14), Small (12), Grade B (3), Grade Range-3 (2), Grade Range-1 (1).
- **Multi-Grade Separation:** Differing grades (e.g. FAQ vs Medium) on the same date represent distinct commercial quality tiers and must never be treated as duplicate price errors.

### 2.3 Prescribed Duplicate Handling Actions
1. **Primary Benchmark Dataset (Strategy 2 — Recommended):**
   - Exclude all 1,321 ambiguous same-grade groups (2,664 rows).
   - Deduplicate the 10 exact duplicate rows from Category A.
   - Retains exactly **157,518 clean records** (157,518 unique series-dates). Total excluded: **2,674 rows (1.67% volume)**.
   - Guarantees 100% label purity with zero order-dependent selection noise.
2. **Sensitivity & Volume Testing (Strategy 3):**
   - Aggregate same-grade daily quotes using the daily median price.
   - Retains all **158,839 unique series-date coordinates**.
   - Must be reported strictly as a sensitivity check, never claimed as official ground truth.
3. **Prohibited Action (Strategy 4 — Superseded):**
   - Calling `.drop_duplicates(subset=..., keep='first')` without Grade is strictly prohibited. It silently discards 4,380 conflicting records based on arbitrary file row order.

---

## 3. Canonical Market Identity Policy

### 3.1 Preserved Raw Names & Separate Canonical Lookups
- Raw market strings must be preserved in all datasets (`Market_Raw`).
- Canonical market identities (`Market_Canonical`) must be applied via explicit non-destructive lookup from [canonical_market_mapping.csv](file:///Users/theankit/Documents/AK/Projects/Mandi_Prediction/backing/phase_02/outputs/canonical_market_mapping.csv).

### 3.2 Approved Portal Transition Mappings
Between Nov 1 and Nov 5, 2025, AGMARKNET appended `" APMC"` across Uttar Pradesh. 17 base-APMC pairs exhibit clean transitions with $\le 4$ overlapping calendar dates.
- Status: **APPROVED** for both base market and APMC alias in each group.

### 3.3 Strict Separation of Concurrent Market Yards
- In Jhansi district, `Jhansi` (general municipal APMC yard) and `Jhansi (Grain)` (specialized grain terminal) operated concurrently across **355 overlapping calendar dates**.
- **PROHIBITION:** `Jhansi` and `Jhansi (Grain)` must **never** be merged. They are approved as distinct canonical markets.

### 3.4 Reporting Hiatus Safeguards (Purwa)
- In Unnao district, `Purwa` ceased reporting on July 31, 2025; `Purwa APMC` commenced reporting on February 21, 2026.
- A **204-day reporting hiatus** (nearly 7 months) separates these records, with 0 overlapping dates.
- Status: **PROPOSED (HIATUS)**. Must not be treated as uninterrupted continuous series without documented external justification.

### 3.5 Phonetic Variants with Concurrent Overlap (Baripaal)
- In Kanpur district, `Baripaal APMC` appeared on March 1, 2026 while `Varipaal APMC` was actively reporting, resulting in **52–56 concurrent overlapping dates**.
- Status: **UNRESOLVED / PROPOSED**. Requires independent verification before unification.

---

## 4. Historical Lag Feature Policy

1. **Row-Based Shifts Prohibited:**
   The use of `.groupby().shift(k)` is prohibited for econometric lag features. `shift(7)` matches an exact 7-day calendar lag in **only 20.14% of records** (mean gap 12.01 days, max gap 371 days).
2. **Exact Calendar Joins Required:**
   Standard lag features must be joined strictly on `Lag_Date = Arrival_Date - k days`. If no trade was recorded on that calendar date, the value must remain `NaN`.
3. **Bounded Staleness Specification:**
   Bounded staleness ($\le 2$ calendar days lookback) is authorized as an explicit alternative feature (`Calendar_Lag_7_Bounded2d`) to bridge Sunday closures, achieving 87.8% coverage with maximum age bounded to 9 calendar days.
4. **No Lookahead Leakage:** Under no circumstances may an observation from $t > T$ enter any historical feature.

---

## 5. Forecast Target Definition & Volatility Policy

1. **Exact Calendar Target Matching:**
   Target prices must match strictly on `Target_Date = Arrival_Date + h days`. Forward-filling missing target dates is prohibited.
2. **Continuous Percentage Return:**
   $$R_h = 100 \times \frac{P_{T+h} - P_T}{P_T}$$
   Denominators $P_T \le 0$ or numerators $P_{T+h} \le 0$ must be excluded.
3. **Exact Class Boundaries:**
   $$\text{Class} = \begin{cases} \text{Favorable}, & \text{if } R_h \ge +2.5\% \\ \text{Unfavorable}, & \text{if } R_h \le -2.5\% \\ \text{Normal}, & \text{if } -2.5\% < R_h < +2.5\% \end{cases}$$
4. **Leak-Free Historical Volatility Thresholds:**
   Volatility-adjusted thresholds must scale using historical return volatility realized **strictly on or before forecast origin $T$**:
   $$\tau_{c, T} = k \cdot \sigma_{c, \le T}$$
   where $\sigma_{c, \le T}$ is estimated from historical daily returns $r_{c, t \le T}$. Future return $R_h(T)$ must **never** be included in the standard deviation at date $T$.
5. **Embargoed Quantile Cutoffs:**
   Quantile thresholds must be estimated strictly on training origins satisfying $T + h \le T_{\text{train\_split}}$ ($T \le \text{2026-01-17}$ for $T+7$). This prevents target outcomes from crossing into held-out validation or test periods.
