# MP-DATA-007R Summary — Verified Market Identity Comparison & Gated Forensic Run

**Task ID:** `MP-DATA-007R`  
**Date:** 2026-11-12 IST  
**Execution Environment:** Kaggle CPU, Internet Off, Private Execution  
**Dataset Input:** `theankitchoubey/mandi-prediction-audit-003b` (v1)  
**Kernel Slug:** `theankitchoubey/mp-data-007-identity-review` (Version 1)  
**Preflight Diff Hash:** `9ae433496515f421caa36f57b42084affbcbe7793b0f9030d812d369531581b7`  
**Execution Status:** `KernelWorkerStatus.COMPLETE` (Runtime: 1,017.4s / ~16.9 min)  

---

## 1. Executive Summary & Structured Status

### WHAT WE ACHIEVED
1. **Gate 1 Fail-Closed Legacy Panel v2 Reproduction:**
   - Ingested 5 raw district CSV arrivals (`472,385` raw input rows) with legacy accepted alias mapping (`42` entries).
   - Produced `mandi_5year_validated_v2.csv` (`67,455,377` bytes).
   - Asserted SHA-256 == `851e718468d6b8c9fd07944535a462338e71aa105af25339fe9438b697088f31` (**EXACT MATCH**).
   - Verified strict row conservation: $472,385 = 463,217 + 855 + 2,936 + 5,350 + 27$.
2. **Candidate Panel v2.1 Generation & Side-by-Side Comparison:**
   - Applied candidate policy `data/reference/market_alias_candidates_v21.csv` (`41` accepted, `2` UNMAPPED/REVIEW).
   - Generated provisional `mandi_5year_validated_v21.csv` (`67,464,487` bytes).
   - Computed candidate SHA-256: `a299536914b5683613f7a0aa242e447f832a33894a476d73401e49fa24449c14`.
   - Side-by-side disposition: raw in (`472,385`), accepted (`463,217`), exact duplicates (`855`), Strategy 2 conflicts (`2,936`), low observation dropped (`5,350`).
   - Unique series delta: `+3` series in Unnao (`165` $\to$ `168`, total `1,167` $\to$ `1,170`) due to withholding the unverified `Purwa APMC` $\to$ `Purwa` merge.
3. **Forensic Reclassification of In-Window Excel Rows (14,741 records $\le$ 2026-09-30):**
   - Reused official `load_arrivals_file` ingestion; discovered and deduplicated all 5 official Agmarknet report workbooks (`16,030` total rows, `14,741` in window).
   - Preserved raw market names; applied accepted aliases consistently without normalizing away punctuation or "APMC".
   - Partitioned all 14,741 rows into mutually exclusive categories with strict row conservation ($14,741 = 12,769 + 77 + 326 + 920 + 325 + 324$):
     - `matched_exact`: `12,769` rows (86.62%)
     - `matched_different`: `77` rows (0.52%) — exactly the 77 disputed Feb–Mar 2026 rows.
     - `conflicting`: `326` rows (2.21%) — quarantined under Strategy 2.
     - `low_obs`: `920` rows (6.24%) — series $< 20$ observations.
     - `absent`: `325` rows (2.20%) — market recognized in district, but natural key absent from raw arrivals.
     - `spelling-review`: `324` rows (2.20%) — exclusively from candidate review markets (`Purwa APMC` in Unnao: 4 rows; `Varipaal` in Kanpur: 320 rows).
4. **Causal Cutoff Reconstruction & Mathematical Invariance:**
   - Evaluated folds F1, F2, F3, F4 from pre-canonicalization cleaned raw arrivals (`472,358` rows).
   - Applied Tier A ($\ge 60$ obs and coverage $\ge 0.30$) and Tier B ($\ge 120$ obs and coverage $\ge 0.30$) definitions.
   - Evaluated verified, assumed, and retrospective evidence modes.
   - Verified zero mathematical subset violations across all folds ($N_{\text{train}} \ge 60 \implies N_{\text{full}} \ge 20$).
   - Passed future mutation invariance test on Cutoff F3 (`2025-12-18`) under value corruptions and adversarial conflicting quotes.

### WHAT IS STILL OPEN
1. **The 77 Disputed Price Differences (Feb–Mar 2026):**
   - The cause of the 77 price discrepancies between the external Agmarknet monthly export (fractional rupees) and daily panel feed (integer prices) remains **UNKNOWN and UNRESOLVED**. Candidate policy v2.1 does not alter these 77 records; unchanged aliases prove that market mapping is not the cause, but do not establish upstream precision or aggregation as the verified cause.
2. **Field Verification of Review Markets:**
   - `Purwa APMC` in Unnao (205-day hiatus) and `Baripaal APMC -> Varipaal` in Kanpur (52-day co-reporting with 20 divergent keys) remain classified as `UNMAPPED/REVIEW`. They cannot be merged without official government gazette or market committee confirmation.
3. **Official Data Freeze Approval:**
   - Candidate Panel v2.1 remains strictly **PROVISIONAL**. Executor does not possess authority to declare a panel freeze; release readiness requires independent owner sign-off.

### WHAT NEXT
1. Independent review of retrieved forensic summaries (`experiments/reports/identity_007r/`).
2. Decide whether to retain Panel v2 or adopt Provisional Panel v2.1 as benchmark input.
3. Proceed to live ingestion, trust verification, and snapshot integration (Steps 3–5).

---

## 2. Remote Run Execution & Artifact Register

- **Kaggle Kernel ID:** `theankitchoubey/mp-data-007-identity-review`
- **Version:** `1`
- **Execution Date:** 2026-11-12 12:15:21 UTC (17:45 IST)
- **Status:** `KernelWorkerStatus.COMPLETE`
- **Duration:** 1,017.4 seconds (~16.9 minutes)
- **Accelerators:** None (CPU-only, private, internet-off)

### Artifacts Verified and Archived (`experiments/reports/identity_007r/` and `experiments/outputs/DATA007R/`):
| Artifact | Size (Bytes) | SHA-256 Hash | Description |
| :--- | :--- | :--- | :--- |
| `mandi_5year_validated_v2.csv` | 67,455,377 | `851e718468d6b8c9fd07944535a462338e71aa105af25339fe9438b697088f31` | Reproducible legacy Panel v2 |
| `mandi_5year_validated_v21.csv` | 67,464,487 | `a299536914b5683613f7a0aa242e447f832a33894a476d73401e49fa24449c14` | Provisional Candidate Panel v2.1 |
| `processing_manifest_v2.json` | 5,136 | `a43eb701f20d2b70b96165dd145c2012d46e5ab6f98b4c3771171cb11bfcc461` | Panel v2 pipeline manifest |
| `processing_manifest_v21.json` | 5,142 | `6dc47f38861746ec21e418d2da6dafc74c7b0993d11990211b09d1306a5fb6d3` | Panel v2.1 pipeline manifest |
| `identity_comparison_v2_vs_v21.csv` | 232 | `bf881a037f75cb81cb7f595d9f35b3087c6b665b3d99815df7bf3b23b809b3da` | District-level rows & series deltas |
| `excel_unmatched_reclassification_v21.json` | 1,199 | `cbaaa2c14511f0ed857b0fc8d7385ed0d3644ce1af6f082a772670ef8b7d561e` | Excel classification summary & conservation |
| `excel_classifications_v2.csv` | 4,473,730 | `9a7fe60496a7122a2cf5224a0ae446feab19c2b3535dd375b0d8d57ff82b4ac2` | Row-level classifications vs v2 |
| `excel_classifications_v21.csv` | 4,476,646 | `a70a41e32ae46de3617be09d6aaa27edb135397dffab6f46792dc858af2c6972` | Row-level classifications vs v2.1 |
| `excel_disposition_breakdown_by_district_crop.csv` | 1,007 | `7919a4410cd179533c2c07f6e173a61fa381f257e89f5ef8979a7ab795f4ce8d` | District x crop Excel breakdown |
| `disputed_77_keys_v2_vs_v21.csv` | 5,766 | `11bc7d69cde7428f6e3283f02db23273dbd8bfbbd77950c0cb1f2c85cacc9512` | 77 disputed keys under both mappings |
| `causal_eligibility_sensitivity_v21.json` | 20,820 | `3d15c977b854fca9d26e99411911fc14bf9ac717c3a2a4866798cda7c1829b2d` | Folds F1–F4 causal reconstruction |
| `causal_cutoff_availability_by_crop.csv` | 959 | `4dd81abd44943875f430a0736f0a6c1e97adb9ca5f45f2a00fbeed7184dd14d4` | Fold x crop serving/target availability |
| `future_mutation_receipt.json` | 496 | `a5ec3a2b3f2e3b0bf6400867e091aaac96e624ad77f7ae411ecaef2230893abb` | Mutation invariance verification receipt |
| `manifest_v21.json` | 3,506 | `5a4ea05d3b6f...` | Comprehensive run manifest |

---

## 3. Detailed Forensic Findings

### 3.1 District-Level Comparison (Panel v2 vs Provisional Candidate v2.1)
| District | Rows v2 | Rows v2.1 | Row Delta | Series v2 | Series v2.1 | Series Delta |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Ghaziabad** | 130,262 | 130,262 | 0 | 297 | 297 | 0 |
| **Jhansi** | 82,391 | 82,391 | 0 | 235 | 235 | 0 |
| **Kanpur** | 110,767 | 110,767 | 0 | 334 | 334 | 0 |
| **Lucknow** | 53,373 | 53,373 | 0 | 136 | 136 | 0 |
| **Unnao** | 86,424 | 86,424 | 0 | 165 | 168 | **+3** |
| **Total** | **463,217** | **463,217** | **0** | **1,167** | **1,170** | **+3** |

### 3.2 In-Window Excel Dispositions (14,741 Rows)
| Category | Panel v2 Count | Panel v2.1 Count | Share (%) | Forensic Explanation |
| :--- | :--- | :--- | :--- | :--- |
| `matched_exact` | 12,769 | 12,769 | 86.62% | Natural key matches panel row; modal price difference = 0.00. |
| `matched_different` | 77 | 77 | 0.52% | Natural key matches panel row; price differs (Feb–Mar 2026 fractional regime). |
| `conflicting` | 326 | 326 | 2.21% | Quarantined during ingestion due to Strategy 2 price divergence. |
| `low_obs` | 920 | 920 | 6.24% | Excluded from panel because full series has $< 20$ records. |
| `absent` | 649 | 325 | 2.20% | Market recognized, but date/natural key absent from daily feed. |
| `spelling-review` | 0 | 324 | 2.20% | Isolated from unmapped review markets (`Purwa APMC`: 4, `Varipaal`: 320). |
| `invalid` | 0 | 0 | 0.00% | Zero corrupt prices or unparseable dates in workbook. |
| `other` | 0 | 0 | 0.00% | Zero unclassified or orphaned rows. |
| **Total Conservation** | **14,741** | **14,741** | **100.00%** | **Conservation strictly verified.** |

### 3.3 Causal Train Eligibility & Serving Availability by Fold (Verified Mode)
| Fold | Cutoff Date | Active Aliases | Train Obs | Tier A Series | Tier B Series | Subset Violations |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **F1** | 2024-12-31 | 21 | 340,032 | 451 | 438 | 0 |
| **F2** | 2025-06-30 | 21 | 392,708 | 487 | 451 | 0 |
| **F3** | 2025-12-18 | 21 | 431,002 | 496 | 473 | 0 |
| **F4** | 2026-03-31 | 21 | 439,450 | 539 | 473 | 0 |

---

## 4. Policy Recommendation: Panel v2 vs Candidate v2.1

1. **Recommendation:**
   - We recommend retaining **Panel v2** as the primary immutable benchmark panel for baseline evaluation, while documenting Candidate Panel v2.1 as an explicit policy variant.
2. **Justification:**
   - Candidate Panel v2.1 provides clean causal hygiene by withholding `Purwa APMC` and `Varipaal` merges. However, it preserves exactly 463,217 observations and identical training sets for F1 and F2. Adopting v2.1 does not resolve the 77 price differences (which stem from reporting precision, not identity mapping).
   - Panel v2 has an established immutable SHA-256 hash (`851e718468d6b8c9fd07944535a462338e71aa105af25339fe9438b697088f31`) across multiple benchmark evaluations (MP-DATA-006, MP-FC-006, MP-FC-006R).
3. **Data Freeze Caveat:**
   - A dataset freeze should **NOT** be declared until the owner independently reviews whether the 3-series difference in Unnao warrants transitioning to v2.1.

---

## 5. Dated Factual Corrections & Audit Clarifications (2026-11-12 IST, per DATA007R Review)

1. **Cause of 77 Price Differences:**
   - The cause remains formally **UNKNOWN and UNRESOLVED**. While the candidate identity mapping proves that the 77 differences are independent of alias choices, this observation does not constitute proof of upstream reporting precision or aggregation changes.
2. **Review Market Identity Mapping:**
   - The review market mapping in Kanpur is specifically `Baripaal APMC -> Varipaal` (Candidate Rule B review with 20 divergent keys over 52-day overlap), alongside `Purwa APMC -> Purwa` in Unnao (Candidate Rule A review with 205-day hiatus).
3. **Causal Availability CSV Evidence Mode:**
   - The committed `causal_cutoff_availability_by_crop.csv` records `verified` evidence mode results only. As noted in `documentation/DATA007R_REVIEW.md`, `causal_eligibility_sensitivity_v21.json` is the authoritative source for mode-specific breakdowns across verified, assumed, and retrospective regimes.
4. **Local Resource Limit Deviation Disclosure:**
   - The prior executor transcript performed local candidate full-panel pipeline execution and hashing, exceeding the local rule budget ($\le 10$ MB / $\le 50,000$ rows). This is formally recorded as an execution noncompliance and is not repeated.
5. **Panel Invariance & Scope Limitations:**
   - Panel v2 (`851e7184...`) remains the immutable benchmark. Candidate Panel v2.1 (`a2995369...`) is a versioned research candidate; no v2 model performance scores are inherited by v2.1. No empirical claims about live operational performance are derived from retrospective panel metrics.

