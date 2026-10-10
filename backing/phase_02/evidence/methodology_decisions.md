# Phase 02 — Methodology Decisions and Empirical Audit (Second Review Pass)

**Project:** Mandi_Prediction  
**Phase:** 02 — Data Handling and Methodology Remediation (Second Review Pass)  
**Date:** 2026-10-10  
**Branch:** `main`  
**Execution Environment:** macOS Apple Silicon, Python 3.14.0, pandas 2.3.3, pytest 9.1.1  

---

## 1. Documented Corrections from Initial Phase 2 Pass

This review pass addresses specific methodology defects identified in the Phase 2 audit without rewriting or discarding previous historical records:

| # | Item Requiring Correction | Original Claim / Implementation | Reason Correction Required | Corrected Finding / Decision | Evidence & Artifact Reference |
|---|---|---|---|---|---|
| **1** | **Duplicate Record Grouping Key** | Keyed by `(District, Market, Commodity, Variety, Date)`. 4,393 duplicate groups reported. | Omitted `Grade` from series key, falsely treating legitimate commercial quality tiers (FAQ vs Medium vs Large) as price duplicates. | Keyed by `(District, Market, Commodity, Variety, Grade, Date)`. Exactly **1,331 duplicate groups (2,684 rows)** exist. 1,321 are ambiguous (2,664 rows); 10 are completely identical (20 rows). Grade field is 100% complete (0 nulls). | [duplicate_resolution_comparison.csv](../outputs/duplicate_resolution_comparison.csv) |
| **2** | **Duplicate Exclusion Strategy** | Strategy 2 excluded 4,380 groups without Grade, discarding 8,818 rows. | Excessively penalized sample size by dropping multi-grade trades that were not genuine price conflicts. | Strategy 2 excludes strictly the 1,321 ambiguous same-grade groups and deduplicates Cat A, retaining **157,518 clean records** (only 2,674 rows excluded, 1.67% volume). | [cleaned_data_quality_summary.csv](../outputs/cleaned_data_quality_summary.csv) |
| **3** | **Volatility Target Lookahead Leakage** | Expanding standard deviation with `.ffill().bfill()`. | `.bfill()` allowed future volatility estimates to populate earlier origins where history was insufficient. | Strictly causal historical volatility: `hist_vol_T = np.nan` for $<10$ prior returns (unclassified burn-in). Zero backward-fill. Invariant to future price modifications. | [target_definition_comparison.csv](../outputs/target_definition_comparison.csv), `test_historical_volatility_causal_no_leakage_and_explicit_burn_in` |
| **4** | **Quantile Horizon Embargo** | Cutoff string assertion only. | Needed empirical data-level verification across training returns and target realization bounds. | Enforced strict embargo: training origins restricted to $T \le T_{\text{train\_split}} - h$ ($T \le \text{2026-01-17}$ for $T+7$). Max realization date is $\le \text{2026-01-24}$. Held-out outcome changes cannot alter training cutoffs. | [target_definition_comparison.csv](../outputs/target_definition_comparison.csv), `test_quantile_embargo_data_level_verification` |
| **5** | **Target-Class Boundary Convention** | Conflicting definitions: Favorable $\ge +2.5\%$ vs agreed closed Normal $[-2.5\%, +2.5\%]$. | Contradiction between specification and code. | Reconciled to agreed convention: Favorable: $R > +2.5\%$, Normal: $-2.5\% \le R \le +2.5\%$, Unfavorable: $R < -2.5\%$. Verified at boundaries $\pm 2.5\%$, just above/below, and zero. | [target_definition_comparison.csv](../outputs/target_definition_comparison.csv), `test_target_class_boundaries_agreed_convention` |
| **6** | **Market Mapping Consistency & Hiatus** | Base and APMC alias had contradictory statuses (e.g. APPROVED vs PROPOSED). Purwa hiatus unflagged. | Contradictory approval within same alias group; Purwa had an undetected 204-day reporting gap. | All 17 clean transition pairs have consistent `APPROVED` status. `Purwa` flagged as `PROPOSED (HIATUS)` due to 204-day gap (July 2025 to Feb 2026). `Baripaal APMC` held `UNRESOLVED` (52 concurrent overlap dates). `Jhansi` vs `Jhansi (Grain)` confirmed distinct (355 overlapping dates). | [canonical_market_mapping.csv](../outputs/canonical_market_mapping.csv), `test_purwa_hiatus_explicit_mapping_decision` |
| **7** | **Bounded-Lag Figures Reconciliation** | Discrepancies between prose and output figures. | Hardcoded numbers in text and runner. | Recomputed dynamically directly from data: 137,212 valid / 157,518 total (87.11% coverage), 20,306 missing (12.89%), 116,826 exact 7-day matches (85.14%), mean gap 7.19 days. | [calendar_lag_coverage.csv](../outputs/calendar_lag_coverage.csv), `test_bounded_lag_figures_reconciled` |
| **8** | **Runner Portability** | Hardcoded local absolute root path `/Users/theankit/...` in analysis runner. | Non-portable; fails on clean checkout or different machines. | Runner derives repo root dynamically via `os.path.abspath` / `MANDI_REPO_ROOT` env var / `--repo-root` CLI argument. Replaced all absolute links in markdown with relative links. | [run_phase02_analysis.py](../tests/run_phase02_analysis.py) |

---

## 2. Corrected Duplicate Handling Analysis

### 2.1 Grade Field Completeness & Value Distribution
All 160,192 records in `data/raw/` contain valid, non-null `Grade` strings:
- **FAQ:** 139,111 (86.84%)
- **Medium:** 16,291 (10.17%)
- **Non-FAQ:** 3,976 (2.48%)
- **Local:** 564 (0.35%)
- **Large:** 177 (0.11%)
- **Specialty/Numbered Grades:** 73 (0.05%) (Grade A, C, Range-2, Small, B, Range-3, Range-1)

Differing grades on the same date represent distinct physical and commercial quality tiers. Collapsing them creates artificial price spread variance.

### 2.2 Reconciled Typology on Same-Grade Key
When keyed by `(District, Market, Commodity, Variety, Grade, Arrival_Date)`, exactly **1,331 duplicate groups (2,684 rows)** exist:
- **Category A (Identical prices across min, modal, max):** **10 groups** (20 rows). Exactly identical across all 11 columns in Lucknow APMC.
- **Category B (Conflicting `Modal_Price`):** **1,296 groups** (2,614 rows).
- **Category C (Same `Modal_Price`, conflicting Min/Max):** **25 groups** (50 rows).
- **Ambiguous Groups Total (Cat B + Cat C):** **1,321 groups** (2,664 rows).

### 2.3 Corrected Candidate Strategies Comparison

Full reconciled results from [duplicate_resolution_comparison.csv](../outputs/duplicate_resolution_comparison.csv):

| Strategy ID | Retained Rows | Series-Dates | Ambiguous Groups | Rows Excluded | T+7 Matched Targets | T+7 Match Rate | Favorable % | Normal % | Unfavorable % | Defensibility Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| **Strat 1: Preserve & Flag** | 160,192 | 158,839 | 1,321 | 0 | 128,754 (Cartesian) | N/A | 19.34% | 58.74% | 21.92% | **DEFENSIBLE AUDIT BASELINE** |
| **Strat 2: Exclude Ambiguous Same-Grade** | 157,518 | 157,518 | 0 | 2,674 | 116,826 | 74.63% | 18.91% | 59.41% | 21.68% | **RECOMMENDED BENCHMARK DATASET** |
| **Strat 3: Median Aggregation** | 158,839 | 158,839 | 1,321 | 0 | 118,713 | 75.21% | 18.93% | 59.38% | 21.69% | **DEFENSIBLE SENSITIVITY CHECK** |
| **Strat 4: Old Grade-Omitting Silent Drop** | 154,642 | 154,642 | 4,380 | 5,550 | 114,846 | 74.27% | 18.97% | 59.80% | 21.23% | **METHODOLOGICALLY FLAWED (SUPERSEDED)** |

*Denominator reconciliation:* Strategy 2 retained ($157,518$) + excluded ($2,674$) = $160,192$ raw records. Excluded rows comprise 2,664 ambiguous rows + 10 Cat A duplicate rows.

---

## 3. Corrected Canonical Market Mapping Audit

Evaluation of 42 nominal market strings in [canonical_market_mapping.csv](../outputs/canonical_market_mapping.csv):

### 3.1 Consistent Approval of Statewide APMC Transitions (17 Mandis)
17 base-APMC pairs exhibit clean statewide schema transitions on November 1–5, 2025, with $\le 4$ overlapping calendar dates.
- In each group, both base market and APMC alias receive consistent **APPROVED** status.
- Approved mandis: Ghaziabad, Hapur, Muradnagar, Noida, Baruwasagar, Chirgaon, Gurusarai, Mauranipur, Moth, Jhansi, Choubepur, Kanpur(Grain), Uttaripura, Banthara, Lucknow, Bangarmau, Unnao.

### 3.2 Distinct Physical Operation of Jhansi Specialized Grain Yard
- Canonical `Jhansi`: `Jhansi` and `Jhansi APMC` -> **APPROVED**.
- Canonical `Jhansi (Grain)`: `Jhansi (Grain)`, `Jhansi (Grain) APMC`, `Jhansi Grain APMC` -> **APPROVED (SPECIALIZED YARD)**.
- **Cross-Yard Concurrency:** The general market and specialized grain yard operated concurrently across **355 overlapping calendar dates**. Merging them is **STRICTLY REJECTED**.

### 3.3 Purwa Reporting Hiatus Safeguards
- `Purwa`: Ceased reporting on July 31, 2025 (326 reporting dates).
- `Purwa APMC`: Commenced reporting on February 21, 2026 (188 reporting dates).
- **Hiatus:** **204 calendar days (nearly 7 months)** with 0 reported trades.
- Status: **PROPOSED (HIATUS)**. Must not be silently treated as continuous without documented historical proof. In modeling lag joins, unapproved mappings are not merged.

### 3.4 Baripaal Concurrent Phonetic Variant
- `Varipaal APMC`: Active Nov 1, 2025 to April 26, 2026.
- `Baripaal APMC`: Active March 1, 2026 to Sept 1, 2026.
- Overlapped across **52 concurrent calendar dates**.
- Status: **UNRESOLVED / PROPOSED (LOW CONFIDENCE)**. Excluded from canonical merge in modeling features.

---

## 4. Exact-Calendar Lag Feature Audit

From [calendar_lag_coverage.csv](../outputs/calendar_lag_coverage.csv):
- `shift(7)` matched an exact 7-calendar-day lag in **only 18.42% of records**. Mean gap was **12.11 days** (up to 398 days).
- Exact-calendar join on `Arrival_Date - 7 days` yields **116,826 records (74.17% coverage)** on the Strategy 2 clean dataset. Missingness is strictly caused by Sunday market closures and holidays.
- Bounded staleness lag (`Calendar_Lag_7_Bounded2d`) bridges Sunday closures: achieves **87.11% coverage (137,212 valid rows out of 157,518; 20,306 missing, 12.89%)** with **85.14% exact 7-day match** and mean gap **7.19 days** (max age bounded to 9 calendar days).

---

## 5. Leakage-Free Target and Volatility Audit

Evaluated on 116,826 matched T+7 pairs and 110,148 matched T+3 pairs in [target_definition_comparison.csv](../outputs/target_definition_comparison.csv):

### 5.1 Causal Historical Volatility Target
$$\tau_{c, T} = 0.5 \cdot \sigma_{c, \le T}$$
where $\sigma_{c, \le T}$ is the expanding standard deviation of commodity daily return realized on or before origin date $T$ with `min_periods=10`.
- **Causal Burn-In Rule:** Dates with $<10$ prior observations have `hist_vol_T = np.nan` and are left unclassified (2,666 pairs at T+7, 2,586 pairs at T+3). Backward-fill is strictly eliminated.
- Classified T+7 pairs ($n=114,160$): Favorable 25,475 (22.32%), Normal 60,910 (53.35%), Unfavorable 27,775 (24.33%).
- Invariance: modifying future prices $P_{t > T}$ causes **zero change** to $\tau_{c, T}$.

### 5.2 Embargoed Training Quantile Targets
- Train Partition: 70% of sorted dates (ending `2026-01-24`).
- Embargo Window: Training origins restricted to $T \le \text{2026-01-17}$ (for T+7) and $T \le \text{2026-01-21}$ (for T+3) so target outcomes do not cross into validation start (`2026-01-25`).
- T+7 Quartiles (evaluated on 100,650 training observations): Unfav $< -1.89\%$, Normal $[-1.89\%, +1.35\%]$, Fav $> +1.35\%$.
- Forward evaluation: Favorable 29,573 (25.31%), Normal 58,377 (49.97%), Unfavorable 28,876 (24.72%). Zero leakage across validation boundary.

### 5.3 Fixed $\pm 2.5\%$ Benchmark (Agreed Convention)
- **T+7 ($n=116,826$):** Favorable ($R > +2.5\%$): 22,089 (18.91%), Normal ($-2.5\% \le R \le +2.5\%$): 69,411 (**59.41%**), Unfavorable ($R < -2.5\%$): 25,326 (21.68%).
- **T+3 ($n=110,148$):** Favorable: 15,502 (14.07%), Normal: 77,070 (**69.97%**), Unfavorable: 17,576 (15.96%).
- Sticky price discovery confirmed: **17.79% of T+7 returns (20,778 pairs)** and **27.59% of T+3 returns (30,386 pairs)** are exactly 0.0000%.

---

## 6. Automated Pytest Verification

All 17 tests in [test_phase02_methodology.py](../tests/test_phase02_methodology.py) executed and passed (0.61s). Execution log captured in [test_results.txt](../tests/test_results.txt).  
Combined test suite (Phase 1 + Phase 2): **25 Passed, 0 Failed (2.56s)**.
