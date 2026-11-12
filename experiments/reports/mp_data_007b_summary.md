# Executive Summary: Market Identity Evidence Gates & Comparison Experiment Repair (MP-DATA-007B)

**Task ID:** `MP-DATA-007B` (Step 2: Local-Only Correction Pass)
**Date:** `2026-11-12` (Asia/Kolkata)
**Baseline HEAD Commit:** `4cef31a1c4658b0a45504deda9b276e5771736fa`
**Verdict:** **PREPARED FOR REVIEW / CANDIDATE IDENTITY EXPERIMENT REPAIRED**
**Execution Environment:** Local Operations Only (Constraints: $\le 10$ MB/file, $\le 50,000$ rows, $\le 30$s compute)

---

## 1. Executive Overview & Review Resolution

Task `MP-DATA-007B` addresses all 8 findings identified in `documentation/DATA007_REVIEW.md`. It eliminates fabricated result placeholders, enforces fail-closed defensive gates across alias validation and causal cutoff mapping, establishes empirical provenance standards for historical knowledge dates, implements actual shared comparison helpers, and validates the entire pipeline path on synthetic fixtures.

### Key Corrections Implemented:
1. **Elimination of Fabricated Output Labels (S1 Finding 1):**
   Cell 4 of `experiments/notebooks/mp_data_007_identity_review.ipynb` no longer prints literal legacy counts (`1895/923/420/323/197/32`) as computed candidate results. Dynamic matching is implemented via `classify_excel_against_panel()` in `src/identity_comparison.py`. Legacy counts are preserved strictly as reference/assertions.
2. **Implementation of Pre-Floor Causal Reconstruction (S1 Finding 2):**
   Implemented `evaluate_causal_train_eligibility_sensitivity()` and `verify_future_mutation_invariance()` in `src/identity_comparison.py`. Reconstructs training series identities BEFORE the $<20$ full-history low-observation floor, verifies the mathematical subset property ($N_{\text{full}} \ge N_{\text{train}}$ holding identity fixed), and verifies that future value mutations dated strictly after cutoff do not corrupt historical training eligibility.
3. **Rigorous Evidence Provenance Standards (S1 Finding 3):**
   In `data/reference/market_alias_candidates_v21.csv`, historical observation dates are decoupled from evidence knowledge dates. Historical APMC transitions have no dated publication receipts; their `evidence_known_date` is left empty. In `build_causal_alias_mapping()`, `evidence_mode="verified"` strictly withholds nonidentity merges absent publication receipts (zero historical merges). An explicit `assumed_known_date` (`2025-11-05`) is provided solely for sensitivity analysis (`evidence_mode="assumed"`). Fallback to `first_date` is completely eliminated.
4. **Fail-Closed Defensive Validation (S2 Finding 4):**
   `validate_alias_table()` in `src/market_identity.py` now fails closed on unparseable date strings (`"not-a-date"`), NaT values, inverted date ranges, null/empty identities (`None`, `np.nan`, `""`, `"nan"`, `"none"`, `"null"`), invalid status domains, nonterminal mapping chains ($A \rightarrow B$ and $B \rightarrow C$), and duplicate conflicting mappings. Rule B concordance deduplicates unique natural keys to prevent many-to-many joined row inflation.
5. **Real Manifest Dispositions without Default Fallbacks (S2 Finding 5):**
   Implemented `extract_manifest_dispositions()` to parse `manifest["summary_metrics"]` directly. Strictly asserts row conservation ($463,217 + 855 + 2,936 + 5,350 + 27 = 472,385$), raising `KeyError` or `ValueError` if fields are missing or sums do not balance.
6. **Retraction of False Causal Prose (S2 Finding 6):**
   Withdrew the erroneous assertion in `mp_data_007_summary.md` that aliases cannot affect counts before `2025-12-18`. Clarified that November 2025 precedes December 18, 2025, and documented the $+2,355$ net training rows reconciled in FC006R.
7. **Precise Overlap & Policy Definitions (S2 Finding 7):**
   Separated inclusive calendar date-range overlap (14 days for Jhansi Grain APMC) from shared observation dates (10 dates with active quotes in both series). Defined candidate thresholds (14d gap, 7d migration overlap, 5 keys, 95% modal match) as declared assumptions requiring sensitivity analysis, not empirical laws. Replaced "proves distinct data channels" with "demonstrates observed co-reporting with unresolved physical identity."
8. **Workflow Noncompliance Correction (Finding 8):**
   Acknowledged prior modification of `documentation/context.md` as noncompliance. `documentation/context.md` is strictly preserved untouched, unstaged, and uncommitted. ONLY local git-ignored `brain/context.md` is updated.

---

## 2. Code Deliverables & Architecture

### 2.1 `src/market_identity.py` (Core Identity & Gate Extensions)
- `validate_alias_table(alias_df)`: Fail-closed validation for schema, identities, statuses, date parseability, NaT, inverted ranges, duplicate targets, nonterminal chains, and cycles.
- `build_causal_alias_mapping(alias_df, as_of_date, evidence_mode)`:
  - Validates table before processing (raises `ValueError` on failure).
  - Identity anchors ($A \rightarrow A$) are structural labels and always active.
  - Nonidentity merges ($A \rightarrow B$):
    - In `verified` mode: requires `evidence_known_date <= as_of_date`. If missing or unparseable, withholds merge (never falls back to `first_date`).
    - In `assumed` mode: evaluates `assumed_known_date <= as_of_date`.
    - In `retrospective` mode: applies all accepted aliases.
- `evaluate_alias_evidence_v21(...)`:
  - Rejects empty/null identities, malformed dates, NaT, inverted ranges.
  - Requires valid numeric finite prices in `price_1` and `price_2`.
  - In Rule B, deduplicates by natural keys `(Arrival_Date, Commodity, Variety, Grade)` before checking `unique_keys >= min_concordance_keys`.

### 2.2 `src/identity_comparison.py` (New Narrow Shared Helper)
- `extract_manifest_dispositions(manifest)`: Extracts nested fields from `manifest["summary_metrics"]` and verifies exact row conservation.
- `compare_panel_dispositions(v2_manifest, v21_manifest, df_v2, df_v21)`: Computes disposition deltas, series deltas, and district-level breakdowns.
- `classify_excel_against_panel(df_excel, df_panel, df_raw, quarantined_keys, low_obs_keys)`:
  - Strict mutually exclusive precedence: `matched_exact` $\rightarrow$ `matched_different` $\rightarrow$ `quarantined_strategy2` $\rightarrow$ `low_obs_dropped` $\rightarrow$ `spelling_unmapped` $\rightarrow$ `absent_from_raw` $\rightarrow$ `other`.
  - Asserts category conservation against total in-window Excel rows.
- `evaluate_causal_train_eligibility_sensitivity(df_raw, alias_df, cutoffs, evidence_mode)`:
  - Reconstructs series identities BEFORE the full-history floor across F1..F4.
  - Verifies fixed-identity subset invariant: $N_{\text{full}} \ge N_{\text{train}}$.
  - Evaluates forward target availability within test windows.
- `verify_future_mutation_invariance(df_raw, alias_df, cutoff_date)`:
  - Proves that future rows and value mutations strictly after `cutoff_date` leave training series, observation counts, and Tier A eligibility perfectly invariant.

### 2.3 `data/reference/market_alias_candidates_v21.csv`
- Schema: `district,market_raw,market_canonical,rule,evidence,first_date,last_date,overlap_days,price_agreement,status,evidence_known_date,assumed_known_date,knowledge_provenance`.
- 21 canonical anchors: `knowledge_provenance = STRUCTURAL_IDENTITY_ANCHOR`.
- 19 APMC transitions: `evidence_known_date = ""` (empty, fail-closed), `assumed_known_date = 2025-11-05`, `knowledge_provenance = ASSUMED_OBSERVATION_HANDOVER`.
- Jhansi Grain APMC: `assumed_known_date = 2026-01-14`.
- Purwa APMC & Baripaal APMC: `status = UNMAPPED/REVIEW`.

---

## 3. Verification & Testing Evidence

### 3.1 Unit Test Suite Receipts
- `tests/test_identity_policy_v21.py`: **19 passed in 0.19s** (inverted dates, missing fields, duplicate conflicts, cycles, nonterminal chains, malformed dates, NaT dates, null identities, unknown statuses, missing prices, Rule B key deduplication, verified cutoff withholding, assumed cutoff handover, invalid table exception).
- `tests/test_identity_comparison.py`: **8 passed in 0.17s** (manifest extraction, row conservation, schema KeyError, sum mismatch ValueError, side-by-side comparison, Excel classification precedence and conservation, causal train-only cutoffs, future mutation invariance).
- `tests/test_market_identity.py`: **12 passed in 0.16s** (legacy v2 backward compatibility).
- **Full Test Suite:** `python3 -m pytest tests/ -q` $\rightarrow$ **204 passed in 4.69s**, exit code 0.

### 3.2 Rebuilt Prepared Notebook (`mp_data_007_identity_review.ipynb`)
- Rebuilt AFTER all source file edits were finalized.
- All 7 embedded module payloads verified for **100% bit-level byte equality** against working tree files:
  - `src/market_identity.py` (32,140 bytes, sha256=`d374fb95f6e2f449...`)
  - `src/identity_comparison.py` (20,015 bytes, sha256=`0cf39381478c1eab...`)
  - `src/data_pipeline.py` (39,484 bytes, sha256=`c542f8c571fe6eb1...`)
  - `src/ingest_agmarknet_arrivals.py` (43,053 bytes, sha256=`bdca338fe4e8632f...`)
  - `src/baselines.py` (44,845 bytes, sha256=`9cf56e5345235bc5...`)
  - `data/reference/market_aliases.csv` (6,546 bytes, sha256=`57e49682f62e6e9a...`)
  - `data/reference/market_alias_candidates_v21.csv` (9,250 bytes, sha256=`f06c7c243e6b1476...`)
- **AST Parsing:** Verified clean Python AST parse across all 5 code cells.
- **Isolated Miniature Smoke Test:** Executed in temporary directory `/var/folders/.../tmpwynaridg/` using synthetic fixtures only. Verified payload decoding, module imports, pipeline run, manifest extraction, Excel reclassification, causal sensitivity, and future mutation invariance without touching raw panels.
- **Kernel Metadata:** Validated relative path `../../notebooks/mp_data_007_identity_review.ipynb` from `experiments/kaggle/007/` resolves to the target notebook.

---

## 4. Current State & Proposed Bounded Remote Execution Request

### 4.1 Current State
- **Panel v2 Status:** **PROVISIONAL** (unchanged, authoritative baseline hash `851e718468d6b8c9fd07944535a462338e71aa105af25339fe9438b697088f31`).
- **Panel v2.1 Status:** **CANDIDATE / PREPARED FOR REMOTE EVALUATION** (not frozen).
- **Remote Execution Status:** **NOT EXECUTED / ZERO REMOTE PUSHES AUTHORIZED**.

### 4.2 Proposed Bounded Remote Execution Request (Awaiting Owner Approval)
When approved by the user, ONE single private Kaggle CPU kernel run will execute the prepared comparison:
- **Kernel ID:** `theankitchoubey/mp-data-007-identity-review`
- **Metadata Path:** `experiments/kaggle/007/kernel-metadata.json`
- **Notebook File:** `experiments/notebooks/mp_data_007_identity_review.ipynb`
- **Dataset Input:** `theankitchoubey/mandi-prediction-audit-003b` (v1)
- **Environment:** Kaggle CPU, Internet Off, Single Private Execution
- **Runtime Budget:** $\le 300$ seconds (5 minutes)
- **Hard-Stop Gate 1:** Panel v2 SHA-256 == `851e718468d6b8c9fd07944535a462338e71aa105af25339fe9438b697088f31`. If differs, **HALT IMMEDIATELY**.
- **Expected Artifacts:**
  - `identity_comparison_v2_vs_v21.csv`
  - `excel_unmatched_reclassification_v21.json`
  - `mandi_5year_validated_v2.csv`
  - `mandi_5year_validated_v21.csv`
  - `manifest_v21.json`
- **Stop Condition:** Do NOT execute remote push in this task. STOP and report.
