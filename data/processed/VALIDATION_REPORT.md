# VALIDATION_REPORT.md: Safe Validation, Quarantine & Deduplication Audit

**Repository:** `ankit-choubey/Mandi_Prediction`  
**Execution Timestamp (UTC):** `2026-10-23T09:52:05.823480+00:00`  
**Engine Version:** `1.0.0`  
**Natural Key:** `State + District + Market + Commodity + Variety + Grade + Arrival_Date`  
**Conflict Resolution Policy:** Strict Quarantine & Evidence Preservation (Strategy 2 / DEC-008)  

---

## 1. Executive Accounting & Gatekeeper Verdict

| Metric Category | Count / Value | Proportion of Input | Disposition & Action |
| :--- | :--- | :--- | :--- |
| **Total Input Raw Rows** | **472,385** | 100.0% | Complete ingestion from 5 source CSVs |
| **Accepted Clean Observations** | **462,350** | **97.88%** | **PASSED** (Published to clean panel) |
| **Quarantined Invalid Records** | **27** | 0.0057% | **QUARANTINED** (Structural / price violation) |
| **Quarantined Conflicting Records** | **2,936** | 0.62% | **QUARANTINED** (Strategy 2 conflicting prices) |
| **Exact Duplicates Removed** | **0** | 0.0% | Deduped via first-row retention |
| **Low-Observation Series Dropped** | **7,072** | 1.5% | Filtered (< 20 historical observations) |
| **Active Canonical Series Retained**| **1,297** | — | Grade-preserving series identity |
| **Temporal Observation Window** | **2021-09-01 to 2026-09-30** | **1,856 days** | 5 full years + 1 month coverage |

---

## 2. In-Depth Failure & Anomaly Breakdown

Every rejected observation was segregated with its original values and line-level traceability:

```text
========================================================================================================================
ANOMALY CATEGORY                     VIOLATION CODE                 OCCURRENCES  HANDLING ACTION
========================================================================================================================
Impossible Price: Min > Max          IMP_RELATIONSHIP_MIN_GT_MAX    15           Quarantined (Never silently swapped)
Impossible Price: Modal > Max        IMP_RELATIONSHIP_MODAL_GT_MAX  22           Quarantined (Modal exceeds ceiling)
Impossible Price: Modal < Min        IMP_RELATIONSHIP_MODAL_LT_MIN  0            Quarantined (Modal below floor)
Non-Positive Prices (<= 0)           PRICE_NON_POSITIVE             34           Quarantined (Zero / negative values)
Unparseable / Corrupt Prices         PRICE_NOT_FINITE / STRING      0            Quarantined (Text / NaN in prices)
Invalid / Malformed Arrival Dates    DATE_OUT_OF_BOUNDS_OR_INVALID  0            Quarantined (Bad formats / invalid days)
Missing Mandatory Attributes         MISSING_REQUIRED_FIELD         0            Quarantined (Null commodity / market)
Conflicting Natural Key Price Quotes CONFLICTING_NATURAL_KEY_PRICES 2,936        Quarantined (Evidence logged, DEC-008)
District Naming Inconsistencies      DISTRICT_TYPO_NORMALIZED       0           Normalized (Original tracked in audit)
========================================================================================================================
```

---

## 3. Natural Key & Deduplication Methodology

### 3.1 Official Market ID vs. Natural Key
The source OGD platform schema (`9ef84268-d588-465a-a308-a864a43d0070`) **does not include an official Market ID or Market Code column**. Physical APMC yards are designated by administrative strings (`Market`). Furthermore, `Commodity_Code` exhibits code collisions across 16 distinct commodities.
Therefore, the validated and approved natural key is strictly:
$$\text{Natural Key} = (\text{State}, \text{District}, \text{Market}, \text{Commodity}, \text{Variety}, \text{Grade}, \text{Arrival\_Date})$$

### 3.2 Strategy 2 Conflict Resolution (DEC-008)
- **Exact Duplicates:** Observations sharing the exact same 7-tuple natural key AND identical prices (`Min_Price == Min_Price`, `Max_Price == Max_Price`, `Modal_Price == Modal_Price`). First row is preserved; redundant identical quotes are logged.
- **Conflicting Records:** Observations sharing the exact same 7-tuple natural key BUT exhibiting differing price quotes (reporting updates or contradictory quotes from separate auction sessions). In accordance with Decision DEC-008, **all conflicting rows are excluded from ML training and quarantined with full raw values into `quarantined_conflicting_records.csv`** to guarantee 100% price quote purity.

---

## 4. Idempotence & Safe Atomic Publishing

1. **Idempotence Assertion:**
   Rerunning this validation suite on the raw dataset produces identical row counts, identical hash digests, and zero compounding modifications.
2. **Safe Staging Pattern:**
   The dataset is staged to a hidden staging path (`.mandi_5year_validated.csv.staging`). Only upon verifying that:
   - Accepted row count $> 0$
   - Zero impossible price relationships (`Min > Max` count $== 0$)
   - Zero natural key duplicate collisions
   is the file atomically moved to [`data/processed/mandi_5year_validated.csv`](file:///Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction/data/processed/mandi_5year_validated.csv). If processing fails, previous valid files remain completely unharmed.

---

## 5. Artifact Ledger & SHA-256 Checksums

```text
========================================================================================================================
ARTIFACT TYPE          FILE PATH                                      SIZE (BYTES)  SHA-256 CHECKSUM
========================================================================================================================
Accepted Clean Dataset data/processed/mandi_5year_validated.csv 63,435,793      20a198682c3f5382a25276a916e258f8fef4aa777c9c6d1cebe6e7c03a206dfa
Invalid Quarantine     data/quarantine/quarantined_invalid_records.csv     10,848        a71956fa5f92084aa8595fb54d48b48a7ebe99fef7a1c49f745c4e2178c1ff4e
Conflict Quarantine    data/quarantine/quarantined_conflicting_records.csv 1,210,155      cbecfb510cf6873e4fb698309fe34b1f35555df885bcaf44e84510461e49b0aa
Validation Summary     data/processed/validation_summary.json        3,888         7e994a1d0bd5c0f0f02ef0c185286574b743197cf9831afc4591e895ab67e95b
========================================================================================================================
```
