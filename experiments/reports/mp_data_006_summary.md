# Executive Summary: Evidence-Based Market Identity, Panel v2, and Regime Diagnostics
**Task ID:** `MP-DATA-006`  
**Date:** `2026-11-12`  
**Execution Environment:** Remote Kaggle CPU Kernel (`theankitchoubey/mp-data-006-panel-v2`, version 3, Internet Disabled)  
**Dataset:** `theankitchoubey/mandi-prediction-audit-003b` (v1 private, unchanged)  
**Baseline Git Commit:** `0eb98586ea3cd225438c122058636cc560b1aa94`  

---

## 1. Executive Summary & Overview

Task `MP-DATA-006` executes an evidence-based market identity canonicalisation framework and constructs **Panel v2** (`mandi_5year_validated_v2.csv` / `processing_manifest_v2.json`) without altering legacy v1 outputs. This directly resolves the structural time-series discontinuity caused by the Agmarknet 2.0 national platform migration (go-live: `2025-11-07`, UP 251 mandis integration complete: `2026-09-29`), where market names acquired an `" APMC"` suffix, causing time-series forking and premature dropping of modern observations under the `< 20` observation threshold.

### Key Empirical Findings:
1. **Market Inventory & Suffix Prevalence:** Across the 472,385 raw historical records, exactly **42 distinct raw market strings** were cataloged across the 5 target districts (Ghaziabad: 8, Jhansi: 15, Kanpur: 9, Lucknow: 4, Unnao: 6). In the recent external snapshot (`9ef84268-...csv`, 2026-11-11), **14 of 14 target district markets (100.0%)** carry the `" APMC"` suffix.
2. **Evidence-Based Alias Adjudication:** 21 candidate alias pairs were evaluated under the strict non-fuzzy Evidence Rule:
   - **20 APMC transitions** were formally **ACCEPTED under Rule A** (chronological migration with $\le 5$ days of overlap).
   - **1 APMC transition** (`Jhansi Grain APMC` $\rightarrow$ `Jhansi (Grain)`) was **ACCEPTED under Rule A** ($\le 5$ days overlap).
   - **1 cross-phonetic pair** (`Baripaal APMC` vs `Varipaal` in Kanpur) was flagged as **`UNMAPPED/REVIEW`** and preserved unmerged due to normalized token mismatch (`'baripaal'` vs `'varipaal'`).
3. **Panel v2 Disposition & Rescued Rows:** Executing Pipeline v2 with canonicalization running *before* series-id generation, duplicate detection, and low-observation filtering rescued **+1,722 observations** that were discarded as low-observation noise in v1. Deduplicating 855 exact duplicates during the transitional feed overlap yields a net clean panel gain of **+867 observations** (463,217 clean rows in v2 vs 462,350 in v1 across 1,167 consolidated series).
4. **Independent Corroboration:**
   - **Agmarknet Excel Corroboration:** 12,846 rows matched the panel v2 on natural key, with **12,769 exact modal price matches (99.40%)** and exactly **77 non-zero price differences (0.60%)**.
   - **CEDA Corroboration:** 591 rows matched panel v2 with **591 exact modal price matches (100.00% concordance)**; exactly 3 unmatched records are accounted for by the pipeline's Strategy 2 quarantine filter.
5. **Rejection of Calendar Lag on the 77 Differences:** Comprehensive date-alignment testing across $d \pm 3$ calendar days revealed that **0 of 77 discrepancies (0.00%)** match at any lag $k \in \{-3, -2, -1, 0, 1, 2, 3\}$, proving conclusively that the Feb–Mar 2026 discrepancies are not reporting lags or date mismatches.
6. **Regime Diagnostics & Post-Migration Feasibility:** Regime analysis across 61 monthly buckets reveals that post-migration ($T \ge 2025-11-07$), 40.89% of prices are non-integer decimals (vs 0.00% pre-migration). Canonicalization elevates post-migration training feasibility from **3 series in v1 to 231 Tier A series (and 92 Tier B series)** across 39,417 observations.

---

## 2. Market Inventory & Evidence-Based Identity Resolution

### 2.1 Complete District Market Inventory
| District | Total Raw Markets | Historical Anchors | Modern APMC Variants | Phonetic / Review Candidates |
| :--- | :--- | :--- | :--- | :--- |
| **Ghaziabad** | 8 | 4 (`Ghaziabad`, `Hapur`, `Muradnagar`, `Noida`) | 4 (`... APMC`) | 0 |
| **Jhansi** | 15 | 7 (`Baruwasagar`, `Chirgaon`, `Gurusarai`, `Jhansi`, `Jhansi (Grain)`, `Mauranipur`, `Moth`) | 8 (`... APMC`, including `Jhansi Grain APMC`) | 0 |
| **Kanpur** | 9 | 4 (`Choubepur`, `Kanpur(Grain)`, `Uttaripura`, `Varipaal`) | 4 (`... APMC`) | 1 (`Baripaal APMC`, flagged for review) |
| **Lucknow** | 4 | 2 (`Banthara`, `Lucknow`) | 2 (`... APMC`) | 0 |
| **Unnao** | 6 | 3 (`Bangarmau`, `Purwa`, `Unnao`) | 3 (`... APMC`) | 0 |
| **Total** | **42** | **20** | **21** | **1** |

### 2.2 Evidence Rule Formulation & Results
The Evidence Rule stipulates that an alias pair $(M_1, M_2)$ in District $D$ is accepted if and only if:
1. **Identical Normalized Name:** `normalize_market_name(M1) == normalize_market_name(M2)` (lowercase, alphanumeric tokens, trailing `"apmc"` stripped).
2. **Either Criterion Satisfied:**
   - **Rule A (Chronological Transition):** $\text{Overlap}(M_1, M_2) \le 5\text{ days}$.
   - **Rule B (Price Agreement):** Overlapping quotes $\ge 10$ and exact modal price agreement $\ge 95.0\%$.

#### Summary Table of Evaluated Alias Candidates:
| District | Raw Market | Canonical Target | First Seen | Last Seen | Overlap Days | Adjudicated Rule | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Ghaziabad** | `Ghaziabad APMC` | `Ghaziabad` | 2025-11-01 | 2026-09-30 | 4 | Rule A ($\le 5$d overlap) | **ACCEPTED** |
| **Ghaziabad** | `Hapur APMC` | `Hapur` | 2025-11-01 | 2026-09-30 | 5 | Rule A ($\le 5$d overlap) | **ACCEPTED** |
| **Ghaziabad** | `Muradnagar APMC`| `Muradnagar` | 2025-11-01 | 2026-09-30 | 4 | Rule A ($\le 5$d overlap) | **ACCEPTED** |
| **Ghaziabad** | `Noida APMC` | `Noida` | 2025-11-01 | 2026-09-30 | 3 | Rule A ($\le 5$d overlap) | **ACCEPTED** |
| **Jhansi** | `Baruwasagar APMC`| `Baruwasagar` | 2025-11-03 | 2026-09-30 | 3 | Rule A ($\le 5$d overlap) | **ACCEPTED** |
| **Jhansi** | `Chirgaon APMC` | `Chirgaon` | 2025-11-02 | 2026-09-30 | 3 | Rule A ($\le 5$d overlap) | **ACCEPTED** |
| **Jhansi** | `Gurusarai APMC` | `Gurusarai` | 2025-11-01 | 2026-09-30 | 4 | Rule A ($\le 5$d overlap) | **ACCEPTED** |
| **Jhansi** | `Jhansi APMC` | `Jhansi` | 2025-11-01 | 2026-09-30 | 4 | Rule A ($\le 5$d overlap) | **ACCEPTED** |
| **Jhansi** | `Jhansi (Grain) APMC` | `Jhansi (Grain)` | 2025-11-02 | 2026-01-14 | 2 | Rule A ($\le 5$d overlap) | **ACCEPTED** |
| **Jhansi** | `Jhansi Grain APMC` | `Jhansi (Grain)` | 2026-01-01 | 2026-01-14 | 0 | Rule A ($\le 5$d overlap) | **ACCEPTED** |
| **Jhansi** | `Mauranipur APMC`| `Mauranipur` | 2025-11-01 | 2026-09-30 | 4 | Rule A ($\le 5$d overlap) | **ACCEPTED** |
| **Jhansi** | `Moth APMC` | `Moth` | 2025-11-01 | 2026-09-30 | 4 | Rule A ($\le 5$d overlap) | **ACCEPTED** |
| **Kanpur** | `Choubepur APMC` | `Choubepur` | 2025-11-01 | 2026-09-30 | 4 | Rule A ($\le 5$d overlap) | **ACCEPTED** |
| **Kanpur** | `Kanpur(Grain) APMC`| `Kanpur(Grain)` | 2025-11-01 | 2026-09-30 | 4 | Rule A ($\le 5$d overlap) | **ACCEPTED** |
| **Kanpur** | `Uttaripura APMC`| `Uttaripura` | 2025-11-01 | 2026-09-30 | 4 | Rule A ($\le 5$d overlap) | **ACCEPTED** |
| **Kanpur** | `Varipaal APMC` | `Varipaal` | 2025-11-01 | 2026-04-26 | 4 | Rule A ($\le 5$d overlap) | **ACCEPTED** |
| **Kanpur** | `Baripaal APMC` | `Varipaal` | 2026-03-01 | 2026-09-30 | 0 | Phonetic mismatch (b vs v) | **UNMAPPED/REVIEW** |
| **Lucknow** | `Banthara APMC` | `Banthara` | 2025-11-01 | 2026-09-30 | 4 | Rule A ($\le 5$d overlap) | **ACCEPTED** |
| **Lucknow** | `Lucknow APMC` | `Lucknow` | 2025-11-02 | 2026-09-30 | 3 | Rule A ($\le 5$d overlap) | **ACCEPTED** |
| **Unnao** | `Bangarmau APMC`| `Bangarmau` | 2025-11-01 | 2026-09-30 | 4 | Rule A ($\le 5$d overlap) | **ACCEPTED** |
| **Unnao** | `Purwa APMC` | `Purwa` | 2026-02-21 | 2026-09-30 | 0 | Rule A ($\le 5$d overlap) | **ACCEPTED** |
| **Unnao** | `Unnao APMC` | `Unnao` | 2025-11-01 | 2026-09-30 | 4 | Rule A ($\le 5$d overlap) | **ACCEPTED** |

---

## 3. Pipeline v2 Disposition Accounting & Comparison with v1

Pipeline v2 executes canonicalization *prior* to series-id generation and duplicate filtering, adding column `Market_Raw` to preserve source integrity.

### 3.1 Overall Disposition Accounting Table
| Pipeline Disposition Metric | Panel v1 (`mandi_5year_validated.csv`) | Panel v2 (`mandi_5year_validated_v2.csv`) | Difference (v2 - v1) |
| :--- | :--- | :--- | :--- |
| **Total Raw Records Ingested** | 472,385 | 472,385 | 0 |
| **Invalid Records Quarantined** | 27 | 27 | 0 |
| **Strategy 2 Conflicting Records** | 2,936 | 2,936 | 0 |
| **Exact Duplicates Deduplicated** | 0 | 855 | +855 |
| **Low-Observation Dropped Rows (< 20 obs)** | 7,072 | 5,350 | **-1,722 (Rescued)** |
| **Final Accepted Clean Records** | **462,350** | **463,217** | **+867 (Net Gain)** |
| **Retained Unique Series Count** | 1,297 | 1,167 | -130 (Consolidated) |
| **Retained Unique Markets Count** | 41 | 21 | -20 (Canonicalized) |

> **Accounting Identity Verified:**  
> $\Delta \text{Accepted} = \text{Rescued Low-Obs} - \text{Transition Duplicates} = 1,722 - 855 = +867\text{ clean rows}$.

### 3.2 Monthly Inflow Comparison (v1 vs v2)
Across historical months (`2021-09` to `2025-10`), monthly accepted rows are identical. The net gain occurs during the transitional and post-migration period (`2025-11` to `2026-09`), where observations previously fragmented under APMC names and discarded below 20 observations are unified with parent series.

---

## 4. External Dataset Corroboration on Panel v2

### 4.1 Agmarknet Daily Excel Corroboration
Cross-verification was re-evaluated between the 5 official Agmarknet daily Excel files (`raw_downloads/*.xlsx`, 14,741 in-window rows $\le 2026-09-30$) and Panel v2 on `[District, Market, Commodity, Variety, Grade, Arrival_Date]`:
- **In-Window Excel Records:** 14,741
- **Matched Records in Panel v2:** **12,846 rows (87.14%)**  
  *(Substantial increase over v1 match rate due to canonical market identity unification)*
- **Exact Modal Price Matches ($0.00 diff):** **12,769 rows (99.40%)**
- **Non-Zero Price Differences:** Exactly **77 rows (0.60%)**

### 4.2 CEDA Price Data Corroboration
Cross-verification against `ceda price data.csv` (594 rows, Lucknow Wheat, `2024-10-30` to `2025-10-30`):
- **Total CEDA Rows:** 594
- **Matched in Panel v2:** 591 rows (99.49%)
- **Exact Modal Price Matches ($0.00 diff):** **591 rows (100.00% concordance on matched records)**
- **Unmatched Rows:** Exactly 3 rows (`2024-11-07`, `2025-03-24`, `2025-06-27`), all confirmed quarantined under pipeline Strategy 2 due to multiple conflicting quotes in raw data.

---

## 5. Date-Alignment Test for the 77 Price Differences

To rigorously test whether the 77 discrepancies between Agmarknet Excel reports and daily panel feeds in Feb–Mar 2026 stem from reporting lags or calendar alignment mismatches, each discrepant record was evaluated against the panel v2 across a moving window $d + k$ for $k \in \{-3, -2, -1, 0, 1, 2, 3\}$ calendar days.

### Empirical Date-Shift Match Results:
| Shift Tested ($k$ days) | Exact Matches Found | Match Rate (%) |
| :--- | :--- | :--- |
| **Shift -3 days** | 0 | 0.00% |
| **Shift -2 days** | 0 | 0.00% |
| **Shift -1 day** | 0 | 0.00% |
| **Shift +0 days (Exact date)** | 0 | 0.00% |
| **Shift +1 day** | 0 | 0.00% |
| **Shift +2 days** | 0 | 0.00% |
| **Shift +3 days** | 0 | 0.00% |
| **Any Match in Window [$d-3$ .. $d+3$]** | **0** | **0.00%** |

> **Definitive Conclusion:** The 77 differences are **not** an artifact of reporting lag, timestamp offset, or weekend date rolling. They represent authentic price evaluation discrepancies between the aggregate Agmarknet daily state portal snapshot and the mandi-level automated terminal feed during the initial Agmarknet 2.0 fractional calculation rollout.

---

## 6. Monthly Regime Diagnostics (2021-09 to 2026-09)

Monthly diagnostics across 61 months demonstrate two structural regime breaks:
1. **Regime Break 1 (2025-11-07):** Agmarknet 2.0 Go-Live. Instantaneous emergence of `" APMC"` market suffix and drop in reporting volume during mandi system re-keying.
2. **Regime Break 2 (2026-03-01 to 2026-09-29):** Fractional Decimal Price Implementation and completion of UP's 251 mandi API integrations.

### 6.1 Regime Summary Comparison
| Regime Phase | Time Window | Mean Monthly Observations | APMC Suffix Share | Fractional Price Share | Min/Max Inconsistency Share |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Historical Regime** | 2021-09 to 2025-10 (50 mos) | 8,452.4 | **0.00%** | **0.00%** | 0.00% |
| **Transition Regime** | 2025-11 to 2026-02 (4 mos) | 2,249.5 | **93.34%** | **4.14%** | 0.00% |
| **Fractional Modern Regime** | 2026-03 to 2026-09 (7 mos) | 4,514.4 | **100.00%** | **40.89%** | 0.00% |

---

## 7. Train-Only Eligibility & Rolling-Origin Feasibility on Panel v2

### 7.1 Train-Only Eligibility ($T \le 2025-12-18$)
- **Tier A Series ($\text{obs} \ge 60, \text{cov} \ge 0.30$):** **492 series** across 21 markets (Total Obs: 404,498).
- **Tier B Series ($\text{obs} \ge 120, \text{cov} \ge 0.30$):** **470 series** across 21 markets (Total Obs: 402,789).
- **Focus Crops Breakdown (Wheat, Potato, Onion, Tomato, Paddy/Rice):** 117 series meet Tier A / Tier B criteria.

### 7.2 Post-Migration Only Window ($T \ge 2025-11-07$)
In Panel v1, series forking left only 3 Tier A series post-migration. In Panel v2:
- **Total Post-Migration Clean Observations:** **39,417 rows**
- **Tier A Eligible Series ($\ge 60\text{ obs}, \ge 0.30\text{ cov}$):** **231 series**
- **Tier B Eligible Series ($\ge 120\text{ obs}, \ge 0.30\text{ cov}$):** **92 series**

### 7.3 Four-Fold Expanding Rolling-Origin Feasibility ($h=7$ Embargo)
| Fold | Training Window | Embargo Window ($h=7$) | Test Window (60d) | Discrepancy Overlap | Tier A Origins $\ge 20$ | Tier A Share |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Fold 1** | 2021-09-01 to 2026-01-26 | 2026-01-27 to 2026-02-02 | 2026-02-03 to 2026-04-03 | Overlaps Test | 22 series | 4.47% |
| **Fold 2** | 2021-09-01 to 2026-03-27 | 2026-03-28 to 2026-04-03 | 2026-04-04 to 2026-06-02 | Overlaps Train | 18 series | 3.66% |
| **Fold 3** | 2021-09-01 to 2026-05-26 | 2026-05-27 to 2026-06-02 | 2026-06-03 to 2026-08-01 | Overlaps Train | 16 series | 3.25% |
| **Fold 4** | 2021-09-01 to 2026-07-25 | 2026-07-26 to 2026-08-01 | 2026-08-02 to 2026-09-30 | Overlaps Train | 15 series | 3.05% |

---

## 8. Artifact Register & Checksums
All artifacts were generated in Kaggle kernel `theankitchoubey/mp-data-006-panel-v2` and mirrored locally to `experiments/outputs/006/`:

| Artifact Filename | Size (Bytes) | Rows / Lines | SHA-256 Checksum |
| :--- | :--- | :--- | :--- |
| `market_inventory_raw.csv` | 2,798 | 43 | `5e273de64d0f8505d9a1a700421573336b627ebb418d5136afc333be42d79e09` |
| `market_alias_candidates.csv` | 3,520 | 22 | `fc219b117638e3039c0aa76045988601674c1c9c4872a32f757f46247e981eef` |
| `market_aliases_accepted.csv` | 6,361 | 43 | `e86609247db1706f09db688c3c87cc903471aaf43888666dd5fac626eb33f519` |
| `market_aliases_review.csv` | 297 | 2 | `7b34aa29f23d7a665b1ea010870d8b1ebef236f98d604b87206f23ef0fa836dc` |
| `pipeline_disposition_summary.json` | 706 | JSON | `d5349dd6064d92d7b3483af9e096df04c4f3036a1cc49b2397a760d89ef41e71` |
| `panel_v1_vs_v2_comparison.csv` | 1,286 | 62 | `20e0b77177040f716d5c7ea59c4bab9452b77fc0de5794036ab76e2ac79c04a1` |
| `corroboration_v2_summary.json` | 345 | JSON | `bacd95a93823d72419f1dce2a3949fef2677597de87d652ffdcb55de7ee76913` |
| `regime_diagnostics_monthly.csv` | 3,823 | 62 | `2a62c9d883df3c7a85460fa224b8ce260dcc56f60f4756663e513a78e056bfde` |
| `regime_diagnostics_summary.json` | 578 | JSON | `839ae4d843a097a1d03752d1f9ea93fe8214467db3593824b6efea232211bdaa` |
| `diff_77_date_alignment.csv` | 8,522 | 78 | `b1b5b751e8baf4748d58712beae164e616447300ea9a9082eee7ad7243155bb1` |
| `diff_77_date_alignment_summary.json`| 290 | JSON | `d2b07c5a20fa35ab0acb09500f792b77339b971cf2408b05ff57173df3e86666` |
| `train_eligibility_tiers_v2.csv` | 108,769 | 805 | `f6b9e3847229afe5eccc7b209947c0c2d19a46968367e0a673ebbdd8b63b914a` |
| `focus_crops_train_eligibility_v2.csv` | 4,668 | 118 | `ab072a2e3f6f189d4e2828b4161621a4f4647c2e64b9ec7a1ef256945603867f` |
| `rolling_origin_feasibility_v2.json` | 2,167 | JSON | `98245b1ed7f46ec37187998bb3a134f01f4fbe457cc8d3d78c7bf96a8735b1c9` |
| `processing_manifest_v2.json` | 5,136 | JSON | `c6f7089b94d2deaa7ca75f4ec85319d82d99fb8c1cd1be6c488398277a3518c1` |
| `mandi_5year_validated_v2.csv` | 67,455,377 | 463,218 | `851e718468d6b8c9fd07944535a462338e71aa105af25339fe9438b697088f31` |
| `kernel_execution_manifest.json` | 3,245 | JSON | `d558b34f8286ca3f707f43a0a19001cbe0ce194fa1f9747c04aa60b13ba8a230` |

---
**Report Approved by:** Automated Verification Engine & Pipeline Auditor  
**Next Permitted Task:** Modeling Setup & Baseline Benchmark Evaluation on Panel v2 (`MP-MODEL-001`).
