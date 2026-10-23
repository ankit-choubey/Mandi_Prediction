# Mandi Prediction — Raw Price Data Quality & Audit Report

**Repository:** `ankit-choubey/Mandi_Prediction`  
**Branch:** `dev`  
**Reference HEAD:** `14d30f22473441c059bbd37c04c8e993bad2a593`  
**Audit Execution Date:** October 2026  
**Audit Scope:** 100% inspection of all five raw source CSVs in `data/raw/` (160,192 records)

---

## 1. Executive Summary

This report delivers a comprehensive, reproducible data audit of the raw APMC mandi price foundation. Every exclusion, duplicate category, quality violation, and market alias is explicitly quantified and explained.

### Pipeline Row Flow Accounting

```text
====================================================================================================
STAGE                                        ROWS        DELTA     UNIQUE SERIES   STATUS / POLICY
====================================================================================================
1. Raw Source Files (data/raw/*.csv)      160,192            0             2,398   Ingested as-is
2. Price Sanity & Positivity Filtering    160,186           -6             2,398   Dropped (Max_Price = 0)
3. Conflicting Duplicate Exclusion        157,522       -2,664             2,390   Dropped (Strategy 2)
4. Exact Identical Deduplication          157,512          -10             2,390   Dropped (Keep first)
5. Low-Volume Series Filtering (< 20)     150,687       -6,825             1,069   Dropped (<20 history)
====================================================================================================
FINAL RETAINED EMPIRICAL PANEL            150,687       -9,505             1,069   100% Validated
====================================================================================================
```

---

## 2. Ingested Raw File Statistics

| File Name | District Reported | Ingested Rows | Date Span | Unparseable Dates | Corrupted Prices (<= 0) | Price Order Violations | Markets | Commodities | Varieties | Grades | SHA-256 Checksum (Truncated) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `Gaziabaad.csv` | Gaziabaad (Ghaziabad) | 41,495 | 2024-09-01 to 2026-09-01 | 0 | 0 | 0 | 8 | 100 | 109 | 10 | `71601f993e07efa1...` |
| `Jhansi.csv` | Jhansi | 23,625 | 2024-09-01 to 2026-09-01 | 0 | 1 | 1 | 15 | 84 | 96 | 4 | `7d0808d8d3255521...` |
| `Kanpur.csv` | Kanpur | 42,644 | 2024-09-01 to 2026-09-01 | 0 | 4 | 4 | 9 | 102 | 133 | 9 | `0eb17704ebba1f66...` |
| `Lukhnow.csv` | Lukhnow (Lucknow) | 21,063 | 2024-09-01 to 2026-09-01 | 0 | 0 | 0 | 4 | 88 | 96 | 4 | `6ca52743cc2f9059...` |
| `Unnao.csv` | Unnao | 31,365 | 2024-09-01 to 2026-09-01 | 0 | 1 | 1 | 6 | 70 | 90 | 5 | `d4ee358b96cad3a8...` |
| **Total / Across Files** | **5 Districts** | **160,192** | **731 Calendar Days** | **0** | **6** | **6** | **42** | **148** | **226** | **17** | — |

---

## 3. Data Integrity & Validation Checks

### 3.1 Schema & Missing Values
- **Required Columns:** `Arrival_Date`, `Commodity`, `Commodity_Code`, `District`, `Grade`, `Market`, `Max_Price`, `Min_Price`, `Modal_Price`, `State`, `Variety`.
- **Completeness:** **0 missing values (0 nulls)** across all 11 columns and all 160,192 records.
- **Date Format:** 100% parseable as `DD/MM/YYYY`. Continuous 731-day span from September 1, 2024 through September 1, 2026.

### 3.2 Price Positivity and Order Violations (`Min <= Modal <= Max`)
All transaction prices in APMC mandis must satisfy physical bounding:
$$0 < \text{Min\_Price} \le \text{Modal\_Price} \le \text{Max\_Price}$$

Exactly **6 records** in the entire 160,192-record dataset violate this condition due to data transmission corruption where `Max_Price = 0.0`:

| Source File | Arrival Date | Market | Commodity | Variety | Grade | Min Price | Modal Price | Max Price | Diagnosis |
|---|---|---|---|---|---|---|---|---|---|
| `Jhansi.csv` | 05/07/2025 | Jhansi | Mustard | Mustard | FAQ | 2,400.0 | 2,450.0 | **0.0** | Corrupt zero Max_Price (`Modal > Max`, `Min > Max`) |
| `Kanpur.csv` | 26/12/2024 | Kanpur(Grain) | Maize | Maize | FAQ | 1,620.0 | 1,640.0 | **0.0** | Corrupt zero Max_Price (`Modal > Max`, `Min > Max`) |
| `Kanpur.csv` | 29/03/2025 | Uttaripura | Wheat | Dara | FAQ | **0.0** | 2,080.0 | **0.0** | Corrupt zero Min & Max (`Modal > Max`, `Min == Max == 0`) |
| `Kanpur.csv` | 17/07/2025 | Kanpur(Grain) | Arhar (Tur/Red Gram) | Red | FAQ | 8,720.0 | 8,770.0 | **0.0** | Corrupt zero Max_Price (`Modal > Max`, `Min > Max`) |
| `Kanpur.csv` | 17/07/2025 | Kanpur(Grain) | Black Gram (Urd Beans) | Urd | FAQ | 4,130.0 | 4,180.0 | **0.0** | Corrupt zero Max_Price (`Modal > Max`, `Min > Max`) |
| `Unnao.csv` | 28/10/2025 | Bangarmau | Wheat | Dara | FAQ | 2,415.0 | 2,445.0 | **0.0** | Corrupt zero Max_Price (`Modal > Max`, `Min > Max`) |

**Analysis Policy:** These 6 records are dropped during data loading. No interpolation or synthetic imputation is applied.

---

## 4. Duplicate Resolution & Canonical Identity

### 4.1 Canonical Identity Definition
The unique canonical identity of an APMC mandi time series is defined as:
$$\text{Canonical Series Key} = (\text{District}, \text{Market}, \text{Commodity}, \text{Variety}, \text{Grade})$$

Preserving `Grade` is essential: merging records across grades causes artificial multi-grade price collisions.

### 4.2 Exact Duplicates vs. Conflicting Observations
When joining on $(\text{Canonical Series Key}, \text{Arrival\_Date})$:
1. **Exact Identical Duplicates:**
   - 20 rows (10 duplicate pairs) exist where all columns and prices are identical.
   - **Policy:** Retain the first occurrence; drop 10 redundant rows.
2. **Conflicting Same-Series / Same-Date Observations:**
   - 2,664 rows across 1,321 series-dates contain conflicting quotes (differing `Modal_Price`, `Min_Price`, or `Max_Price` on the exact same date for the identical series).
   - **Policy (Strategy 2):** In accordance with DEC-007, silent averaging is strictly rejected because blending conflicting quotes fabricates prices never transacted in the physical mandi. All 2,664 ambiguous rows are quarantined and excluded from empirical training.

---

## 5. Market Name Aliases & November 2025 Transition

In November 2025, the state agricultural marketing board transitioned its reporting schema, appending `" APMC"` to market names across Uttar Pradesh.

### 5.1 Observed Structural Shift
- **Pre-November 2025:** Base market names reported (e.g. `Ghaziabad`, `Lucknow`, `Kanpur(Grain)`, `Bangarmau`).
- **Post-November 2025:** Suffix `" APMC"` appended (e.g. `Ghaziabad APMC`, `Lucknow APMC`, `Kanpur(Grain) APMC`).
- **Overlap Window (Nov 1–5, 2025):** For 2 to 4 dates, both the base name and the APMC-suffixed name reported concurrent prices.
- **Kanpur Specialized Alias:** `Varipaal APMC` and `Baripaal APMC` ran concurrently for 52 dates between March 1, 2026 and April 26, 2026.
- **Unnao Reporting Hiatus:** The `Purwa` market ceased reporting on July 31, 2025. Reporting resumed 204 days later under `Purwa APMC` on February 21, 2026.

### 5.2 Canonical Mapping Table
The repository maintains an audited canonical mapping in `backing/phase_02/outputs/canonical_market_mapping.csv` mapping all 42 raw market strings to 20 physical APMC market yards (plus 1 distinct specialized grain yard in Jhansi).

---

## 6. Series Coverage & Low-Volume Pruning

Following duplicate resolution (157,512 clean rows across 2,390 unique series):
- **High-Volume Valid Series ($\ge 20$ observations):** 1,069 series comprising **150,687 records** (95.67% of clean volume).
- **Low-Volume Sparse Series ($< 20$ observations):** 1,321 series comprising **6,825 records** (4.33% of volume).
- **Policy:** Series with fewer than 20 observations are excluded from econometric and machine learning pipelines because they lack sufficient historical depth for rolling window calculations (e.g., 7-day rolling mean/std) and lag construction.

---

## 7. Audit Conclusion & Reproducibility Verification

The data loading and cleaning pipeline is 100% reproducible via:
```bash
/path/to/python -c "from src.data_loader import load_and_clean_mandi_data; df = load_and_clean_mandi_data()"
```
- **Inputs:** 160,192 raw records
- **Output:** 150,687 clean, deduplicated, validated records
- **Preservation:** `data/raw/` remains 100% unmodified and bitwise identical to origin.
