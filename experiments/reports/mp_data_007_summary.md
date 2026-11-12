# Executive Summary: Market Identity Policy & Dataset-Freeze Readiness (MP-DATA-007)

**Task ID:** `MP-DATA-007` (Step 2: Market Identity Policy & Dataset-Freeze Readiness)
**Date:** `2026-11-12` (Asia/Kolkata)
**Baseline Commit:** `b4861ee6441ae492483157d47ec8c3431d3a3fb1`
**Verdict:** **DATA POLICY PREPARED / PANEL FREEZE PENDING EXECUTION**
**Execution Environment:** Local Analysis Only (Rules: $\le 10$ MB/file, $\le 50,000$ rows, $\le 30$s compute)

---

## 1. Executive Verdict & Core Decisions

1. **Retrospective Benchmark Accepted:**
   `MP-FC-006R` is accepted as an immutable retrospective benchmark for proceeding to Step 2. Panel v2 (`mandi_5year_validated_v2.csv`) SHA-256 digest `851e718468d6b8c9fd07944535a462338e71aa105af25339fe9438b697088f31` remains the authoritative fail-closed replication anchor.
2. **Zero Remote Compute & Zero Unverified Freeze:**
   This task is strictly local preparation. Zero Kaggle kernels were pushed, zero datasets uploaded, and zero machine learning models trained. **Panel v2 remains PROVISIONAL**; no regenerated panel is declared frozen without verified remote execution evidence.
3. **Candidate Policy v2.1 Formulated:**
   A defensive candidate market identity policy (`evaluate_alias_evidence_v21`, `validate_alias_table`, `build_causal_alias_mapping`) has been implemented in `src/market_identity.py` and saved to `data/reference/market_alias_candidates_v21.csv`. Legacy reproduction paths remain 100% intact and backward-compatible.
4. **Disputed Market Adjudication:**
   - **Purwa (Unnao):** Fails Candidate Rule A due to a **205-calendar-day hiatus** (2025-07-31 to 2026-02-21) with 0 overlapping dates and 0 price concordance. Reclassified to **`UNMAPPED/REVIEW`** in candidate v2.1; physical continuity is plausible, but empirical transition concordance is unverified.
   - **Jhansi Grain Variants (Jhansi):** 59-day gap between `Jhansi Grain APMC` and historical pre-APMC `Jhansi (Grain)` is resolved via **transitive concordance with `Jhansi (Grain) APMC`** (10-day overlap in January 2026, 23 overlapping keys, **100.0% exact price match**). Status: **`ACCEPTED`** under Candidate Rule B.
   - **Baripaal APMC vs Varipaal (Kanpur):** Co-existed for 52 calendar days (2026-03-01 to 2026-04-26) with 462 keys; 442 matched (95.67%), but **20 keys had conflicting prices**, accompanied by normalized base token mismatch (`baripaal` vs `varipaal`). Status: **`UNMAPPED/REVIEW`**; retained as distinct canonical market `Baripaal APMC` to avoid artificial conflict injection.

---

## 2. Complete Forensic Evidence Matrix (24 Candidate Transitions)

The forensic analysis below reconciles `data/reference/market_aliases.csv` against `alias_transition_forensics.csv` (24 evaluated candidate transitions) from `MP-FC-006R`.

> [!IMPORTANT]
> Price agreement percentages below reflect **Modal Price concordance** on overlapping `(Commodity, Variety, Grade, Date)` keys. Minimum and Maximum prices were not matched in the transition forensics artifact; therefore, we certify **modal price concordance only**, not full-quote agreement.

| District | Raw Market Name | Canonical Anchor | Older Name & Date Range | Newer Name & Date Range | Signed Gap | Overlap Days | Overlap Keys | Modal Match (%) | Candidate v2.1 Adjudication & Rationale |
| :--- | :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **Ghaziabad** | Ghaziabad APMC | Ghaziabad | Ghaziabad (2021-09-01..2025-11-04) | Ghaziabad APMC (2025-11-01..2026-09-30) | -3d | 4d | 103 | 100.0% | **ACCEPTED** (Rule A: Verified Migration) |
| **Ghaziabad** | Hapur APMC | Hapur | Hapur (2021-09-01..2025-11-05) | Hapur APMC (2025-11-01..2026-09-30) | -4d | 4d | 61 | 100.0% | **ACCEPTED** (Rule A: Verified Migration) |
| **Ghaziabad** | Muradnagar APMC | Muradnagar | Muradnagar (2021-09-01..2025-11-04) | Muradnagar APMC (2025-11-01..2026-09-30) | -3d | 4d | 34 | 100.0% | **ACCEPTED** (Rule A: Verified Migration) |
| **Ghaziabad** | Noida APMC | Noida | Noida (2021-09-02..2025-11-03) | Noida APMC (2025-11-01..2026-09-30) | -2d | 2d | 39 | 100.0% | **ACCEPTED** (Rule A: Verified Migration) |
| **Jhansi** | Baruwasagar APMC | Baruwasagar | Baruwasagar (2021-09-02..2025-11-05) | Baruwasagar APMC (2025-11-03..2026-09-30) | -2d | 3d | 5 | 100.0% | **ACCEPTED** (Rule A: Verified Migration) |
| **Jhansi** | Chirgaon APMC | Chirgaon | Chirgaon (2021-09-01..2025-11-04) | Chirgaon APMC (2025-11-02..2026-09-30) | -2d | 2d | 6 | 100.0% | **ACCEPTED** (Rule A: Verified Migration) |
| **Jhansi** | Gurusarai APMC | Gurusarai | Gurusarai (2021-09-01..2025-11-04) | Gurusarai APMC (2025-11-01..2026-09-30) | -3d | 4d | 28 | 100.0% | **ACCEPTED** (Rule A: Verified Migration) |
| **Jhansi** | Jhansi APMC | Jhansi | Jhansi (2021-09-01..2025-11-04) | Jhansi APMC (2025-11-01..2026-09-30) | -3d | 4d | 49 | 100.0% | **ACCEPTED** (Rule A: Verified Migration) |
| **Jhansi** | Jhansi (Grain) APMC | Jhansi (Grain) | Jhansi (Grain) (2024-05-25..2025-11-03) | Jhansi (Grain) APMC (2025-11-02..2026-01-14) | -1d | 2d | 5 | 100.0% | **ACCEPTED** (Rule A: Verified Migration) |
| **Jhansi** | Jhansi Grain APMC | Jhansi (Grain) | Jhansi (Grain) (2024-05-25..2025-11-03) | Jhansi Grain APMC (2026-01-01..2026-01-14) | +59d | 0d | 0 | NaN | **ACCEPTED** via Transitive Rule B (see row 24) |
| **Jhansi** | Mauranipur APMC | Mauranipur | Mauranipur (2021-09-01..2025-11-04) | Mauranipur APMC (2025-11-01..2026-09-30) | -3d | 4d | 43 | 100.0% | **ACCEPTED** (Rule A: Verified Migration) |
| **Jhansi** | Moth APMC | Moth | Moth (2021-09-01..2025-11-04) | Moth APMC (2025-11-01..2026-09-30) | -3d | 4d | 30 | 100.0% | **ACCEPTED** (Rule A: Verified Migration) |
| **Kanpur** | Choubepur APMC | Choubepur | Choubepur (2021-09-01..2025-11-04) | Choubepur APMC (2025-11-01..2026-09-30) | -3d | 3d | 66 | 100.0% | **ACCEPTED** (Rule A: Verified Migration) |
| **Kanpur** | Kanpur(Grain) APMC | Kanpur(Grain) | Kanpur(Grain) (2021-09-01..2025-11-04) | Kanpur(Grain) APMC (2025-11-01..2026-09-30) | -3d | 3d | 63 | 100.0% | **ACCEPTED** (Rule A: Verified Migration) |
| **Kanpur** | Uttaripura APMC | Uttaripura | Uttaripura (2021-10-24..2025-11-04) | Uttaripura APMC (2025-11-01..2026-09-30) | -3d | 3d | 66 | 100.0% | **ACCEPTED** (Rule A: Verified Migration) |
| **Kanpur** | Varipaal APMC | Varipaal | Varipaal (2021-09-01..2025-11-04) | Varipaal APMC (2025-11-01..2026-04-26) | -3d | 3d | 47 | 100.0% | **ACCEPTED** (Rule A: Verified Migration) |
| **Lucknow** | Banthara APMC | Banthara | Banthara (2022-05-18..2025-11-04) | Banthara APMC (2025-11-01..2026-09-30) | -3d | 4d | 8 | 100.0% | **ACCEPTED** (Rule A: Verified Migration) |
| **Lucknow** | Lucknow APMC | Lucknow | Lucknow (2021-09-01..2025-11-04) | Lucknow APMC (2025-11-02..2026-09-30) | -2d | 3d | 64 | 100.0% | **ACCEPTED** (Rule A: Verified Migration) |
| **Unnao** | Bangarmau APMC | Bangarmau | Bangarmau (2021-09-01..2025-11-04) | Bangarmau APMC (2025-11-01..2026-09-30) | -3d | 4d | 88 | 100.0% | **ACCEPTED** (Rule A: Verified Migration) |
| **Unnao** | Purwa APMC | Purwa | Purwa (2021-09-01..2025-07-31) | Purwa APMC (2026-02-21..2026-09-30) | +205d | 0d | 0 | NaN | **UNMAPPED/REVIEW** (Fails Rule A: 205d hiatus) |
| **Unnao** | Unnao APMC | Unnao | Unnao (2021-09-01..2025-11-04) | Unnao APMC (2025-11-01..2026-09-30) | -3d | 3d | 27 | 100.0% | **ACCEPTED** (Rule A: Verified Migration) |
| **Kanpur** | Baripaal APMC | Varipaal | Varipaal (2021-09-01..2025-11-04) | Baripaal APMC (2026-03-01..2026-09-30) | +117d | 0d | 0 | NaN | **UNMAPPED/REVIEW** (117d gap vs pre-APMC) |
| **Kanpur** | Baripaal APMC | Varipaal APMC | Varipaal APMC (2025-11-01..2026-04-26) | Baripaal APMC (2026-03-01..2026-09-30) | -56d | 52d | 462 | 95.67% | **UNMAPPED/REVIEW** (20 conflicting keys; b/v mismatch) |
| **Jhansi** | Jhansi Grain APMC | Jhansi (Grain) APMC | Jhansi (Grain) APMC (2025-11-02..2026-01-14) | Jhansi Grain APMC (2026-01-01..2026-01-14) | -13d | 10d | 23 | 100.0% | **ACCEPTED** (Transitive concordance to Jhansi (Grain)) |

### Reference Table Accounting (`data/reference/market_aliases.csv`):
- **Physical Lines in File:** 44 lines (1 header line + 43 data rows).
- **Data Rows:** Exactly 43 CSV rows.
- **Unique Raw Names:** 42 distinct strings (`Baripaal APMC` appears twice: row 24 as single token anchor, row 43 as review row).
- **Canonical Anchors (`market_raw == market_canonical`):** Exactly 21 rows (20 standard anchors + 1 unmerged anchor for `Baripaal APMC`).
- **Accepted Rows:** Exactly 42 rows (21 anchors + 21 non-identity migrations).
- **Review Rows:** Exactly 1 row (`Baripaal APMC -> Varipaal`).
- **Non-Identity Accepted Rows:** Exactly 21 rows.

---

## 3. Disputed Market Identity Adjudications

### 3.1 Purwa (Unnao)
- **Observed Chronology:** Historical `Purwa` ceased reporting on `2025-07-31`. The new name `Purwa APMC` appeared on `2026-02-21`.
- **Gap & Concordance:** 205 calendar days of total reporting hiatus. Overlap $= 0$ days; overlapping keys $= 0$; price agreement $=$ NaN.
- **Why v2 Accepted:** Legacy Rule A checked only `overlap_days <= 5`. A gap of 205 days had `overlap_days == 0 <= 5`, accepting the pair without any upper bound on calendar hiatus.
- **Candidate v2.1 Ruling:** **`UNMAPPED/REVIEW`**. Candidate Rule A enforces `abs(gap_days) <= 14`. A 7-month dark period cannot be assumed continuous without external official verification. In candidate v2.1, `Purwa APMC` is retained as its own market identity `Purwa APMC`. In training folds F1, F2, F3 (ending $\le 2025\text{-}12\text{-}18$), `Purwa APMC` had 0 observations, so withholding this alias produces zero change to historical training tiers.

### 3.2 Jhansi Grain Variants (Jhansi)
- **Observed Chronology:** Historical `Jhansi (Grain)` ceased on `2025-11-03`. Direct comparison to `Jhansi Grain APMC` (first date `2026-01-01`) showed a 59-day gap.
- **Transitive Linkage:** However, `Jhansi (Grain) APMC` migrated directly from `Jhansi (Grain)` on `2025-11-02` (100% price match). Then, between `2026-01-01` and `2026-01-14`, BOTH `Jhansi (Grain) APMC` AND `Jhansi Grain APMC` reported concurrently:
  - Overlap: 10 calendar days.
  - Overlapping keys: 23 unique natural keys.
  - **Exact price agreement: 23 / 23 = 100.0%**.
- **Candidate v2.1 Ruling:** **`ACCEPTED`**. The mapping `Jhansi Grain APMC -> Jhansi (Grain)` is valid via transitive equivalence (`Jhansi Grain APMC` $\equiv$ `Jhansi (Grain) APMC` $\rightarrow$ `Jhansi (Grain)`). The justification is updated from erroneous Rule A to Candidate Rule B (transitive concordance). Redundant duplicate records during the 10-day overlap deduplicate cleanly under identical prices.

### 3.3 Baripaal APMC vs Varipaal (Kanpur)
- **Observed Chronology:** `Varipaal APMC` began `2025-11-01`. `Baripaal APMC` began `2026-03-01`.
- **Co-Reporting Overlap:** Between `2026-03-01` and `2026-04-26` (52 calendar days), both mandis were actively transmitting quotes concurrently:
  - Overlapping natural keys: 462 keys.
  - Exact modal price matches: 442 keys (95.67%).
  - **Conflicting keys: Exactly 20 keys (4.33%) had differing prices on the same day**.
- **Normalization Mismatch:** `normalize_market_name('Baripaal APMC') == 'baripaal'`, while `normalize_market_name('Varipaal APMC') == 'varipaal'`.
- **Candidate v2.1 Ruling:** **`UNMAPPED/REVIEW`**. Although Hindi phonology alternates B/V (बारीपाल / वारीपाल), concurrent reporting with 20 diverging quotes proves they were distinct data channels. Merging them would inject artificial price conflicts into the panel. `Baripaal APMC` remains its own canonical market `Baripaal APMC` (as established in reference row 24).

---

## 4. Candidate Policy v2.1 Architecture & Defensive Gates

In `src/market_identity.py`, Candidate Policy v2.1 adds strict validation and causal awareness while preserving legacy reproduction:

```
[Candidate Evaluation Logic]
       │
       ├── Missing identity fields? ──────> FAIL (MISSING_FIELDS)
       ├── Inverted dates (start > end)? ──> FAIL (INVALID_DATES)
       ├── Different districts? ───────────> FAIL (DIFFERENT_DISTRICTS)
       ├── Normalized name mismatch? ──────> FAIL (NORM_MISMATCH)
       │
       ├── Case A: overlap <= 7d (Handover Window)
       │     ├── gap > 14d? ───────────────> FAIL (Rule A Hiatus Limit Exceeded)
       │     └── handover keys agree? ─────> ACCEPT (Candidate Rule A)
       │
       └── Case B: overlap > 7d (Extended Co-reporting)
             ├── keys < 5? ────────────────> FAIL (Rule B Insufficient Sample)
             ├── agreement >= 95%? ────────> ACCEPT (Candidate Rule B)
             └── agreement < 95%? ─────────> FAIL (Rule B Price Divergence)
```

### Defensive Validation Helpers:
1. `validate_alias_table(alias_df)`:
   - Validates schema against `MARKET_ALIAS_COLUMNS`.
   - Rejects null/empty `district`, `market_raw`, `market_canonical`.
   - Rejects inverted date ranges (`first_date > last_date`).
   - Rejects conflicting duplicate mappings (same `(district, raw_market)` mapped to multiple distinct targets with `ACCEPTED` status).
   - Detects cyclic mappings ($A \rightarrow B$ and $B \rightarrow A$).
2. `build_causal_alias_mapping(alias_df, as_of_date)`:
   - Filters active alias mappings by `evidence_known_date <= as_of_date`.
   - Withholds mappings whose empirical evidence was established after the forecasting cutoff, preventing lookahead bias.

---

## 5. Data Disposition & Unmatched Excel Reclassification

The 1,895 unmatched in-window Excel rows identified in `MP-FC-006R` reconcile as pipeline matching stages:

$$\text{Total Unmatched Rows} = 923 + 420 + 323 + 197 + 32 = 1,895$$

| Pipeline Disposition Category | Count | Proportion | Nature & Diagnostic Meaning |
| :--- | :---: | :---: | :--- |
| **`low_obs_dropped`** | 923 | 48.71% | Row present in raw portal data, but series had $<20$ full-history observations and was pruned before panel construction. |
| **`other`** | 420 | 22.16% | Residual matching failures (Kanpur 379, Jhansi 20, Lucknow 19, Ghaziabad 1, Unnao 1); designated **PENDING REMOTE CHECK**. |
| **`quarantined_strategy2`** | 323 | 17.05% | Multi-modal conflicting price records on identical natural keys; records quarantined to avoid injecting ambiguity. |
| **`absent_from_raw`** | 197 | 10.40% | Records present in Agmarknet Excel exports that never appeared in raw daily portal scrapes. |
| **`spelling_unmapped`** | 32 | 1.69% | Minor commodity or variety spelling divergences between Excel and scraper feeds. |

> [!NOTE]
> Categories represent **pipeline ingestion filter stages**, not independent external ground-truth errors. Quarantine signifies **conflicting quotes**, not corrupted data. No canonical names may be altered solely to artificially inflate external matching.

---

## 6. Causal Sensitivity: Full-History Floor vs Train Eligibility

1. **Mathematical Proof on Floor Interaction:**
   Train-only eligibility at cutoff $T_{\text{cutoff}}$ requires $N_{\text{train}} \ge 60$ observations strictly prior to $T_{\text{cutoff}}$. Full-history pruning requires $N_{\text{full}} \ge 20$ observations across the entire 5-year span.
   Since $N_{\text{full}} \ge N_{\text{train}}$ for every series, any series with $N_{\text{train}} \ge 60$ automatically has $N_{\text{full}} \ge 60 > 20$. Therefore, **the $<20$ full-history floor cannot prune any series that independently satisfies the $\ge 60$ training threshold**.
2. **Border Series via Canonicalization:**
   The only series affected by canonicalization are border series where two raw market labels (e.g. historical and APMC) each had $<20$ observations, but combine to $\ge 20$ observations under an alias. Because APMC names did not exist prior to November 2025, merging them in 2026 adds zero observations prior to `2025-12-18` (Folds F1, F2, F3).

---

## 7. Data Register Reconciliations

1. **Agmarknet 2.0 Go-Live vs First Observation:**
   Bulk Excel downloads begin on `2025-11-07`. The first empirical observation carrying an `' APMC'` suffix in the underlying database appears on **`2025-11-01`**. Exact rollout date is unverified by official gazette.
2. **Endpoint Distance vs Intervening Dates:**
   CEDA data terminates `2025-10-30`. Agmarknet Excel begins `2025-11-07`. Endpoint distance is **8 calendar days**; missing intervening dates count is exactly **7 calendar dates** (`2025-10-31` to `2025-11-06`).
3. **Unit Provenance:**
   Agmarknet Excel explicitly declares `Price Unit: Rs/Quintal` and `Arrival Unit: Tonnes`. Panel price units in historical scraper data were **inferred**; CEDA quantity unit is categorized as **`UNVERIFIED`**.
4. **Scope Exclusions:**
   Synthetic price generation, cold storage adjustments, and gridded weather remain strictly **out of scope** for Release 1 price forecasting.

---

## 8. Proposed Bounded Remote Execution Request (Prepared Kernel)

The comparison notebook and metadata are authored and verified locally. **THEY HAVE NOT BEEN EXECUTED OR PUSHED.**

- **Kernel ID:** `theankitchoubey/mp-data-007-identity-review`
- **Notebook File:** `experiments/notebooks/mp_data_007_identity_review.ipynb`
- **Metadata Path:** `experiments/kaggle/007/kernel-metadata.json`
- **Input Dataset:** Existing private dataset `theankitchoubey/mandi-prediction-audit-003b` (v1)
- **Environment:** Kaggle CPU, Internet Off, Single Private Execution
- **Runtime Budget:** $\le 300$ seconds (5 minutes)
- **Hard-Stop Gate 1:** Panel v2 SHA-256 must equal `851e718468d6b8c9fd07944535a462338e71aa105af25339fe9438b697088f31`. If differs, **HALT**.
- **Expected Deliverable Outputs:**
  - `identity_comparison_v2_vs_v21.csv`
  - `excel_unmatched_reclassification_v21.json`
  - `mandi_5year_validated_v2.csv`
  - `mandi_5year_validated_v21.csv`
  - `manifest_v21.json`
- **Authorization Note:** Zero self-approval. Remote execution requires separate explicit owner approval.
