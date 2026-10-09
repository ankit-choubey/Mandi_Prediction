# Phase 1 Input Verification & Series Key Documentation

**Audit Phase:** Phase 1 — Data Integrity & Temporal Continuity  
**Date:** October 10, 2026  
**Auditor:** Antigravity AI  

---

## 1. Input File Hash & Cryptographic Verification

All 5 raw input files were hashed using SHA-256 directly from disk. Raw files were preserved strictly unchanged.

| Filename | File Size | SHA-256 Checksum | Row Count | Column Count | Date Range |
|---|---|---|---|---|---|
| `Gaziabaad.csv` | 3,656,537 bytes (3.49 MB) | `71601f993e07efa146f126747245a7fffb608a307abdea579475ba19bfeb0251` | 41,495 | 11 | 2024-09-01 to 2026-09-01 |
| `Jhansi.csv` | 1,947,875 bytes (1.86 MB) | `7d0808d8d32555212af546004195c0ccf58e368106daad67169a231e80988a5c` | 23,625 | 11 | 2024-09-01 to 2026-09-01 |
| `Kanpur.csv` | 3,705,373 bytes (3.53 MB) | `0eb17704ebba1f66b8c9ef660f48dabc3665ea4691ed3b8aa20a49df8528d04a` | 42,644 | 11 | 2024-09-01 to 2026-09-01 |
| `Lukhnow.csv` | 1,840,744 bytes (1.76 MB) | `6ca52743cc2f9059bf1e3b919b25317aa367f580bbafa6f62adb9db1d759bb13` | 21,063 | 11 | 2024-09-01 to 2026-09-01 |
| `Unnao.csv` | 2,570,462 bytes (2.45 MB) | `d4ee358b96cad3a888e4a92acd993327e56c4dc6af6eb60814193f98f591cebc` | 31,365 | 11 | 2024-09-01 to 2026-09-01 |
| **TOTAL** | **13,720,991 bytes (13.09 MB)** | — | **160,192** | **11** | **2024-09-01 to 2026-09-01** |

---

## 2. Series Definition & Canonical Key Specification

In agricultural wholesale market analysis, an individual time series must represent an isolated, continuous price stream for a specific commodity traded at a specific physical marketplace.

### The Canonical Series Key
$$\text{Series ID} = \text{District} + \text{"\_\_"} + \text{Market} + \text{"\_\_"} + \text{Commodity} + \text{"\_\_"} + \text{Variety}$$

- **Components:**
  1. `District`: Administrative district (Ghaziabad, Jhansi, Kanpur, Lucknow, Unnao).
  2. `Market`: Wholesale mandi yard name (e.g. `Banthara`, `Kanpur(Grain)`).
  3. `Commodity`: Agricultural produce name (e.g. `Potato`, `Wheat`, `Tomato`).
  4. `Variety`: Specific sub-type or commercial grade (e.g. `Deshi`, `Dara`, `Red`).
- **Nominal Series Count:** **2,044 unique series** identified in raw data.
- **Physical Series Count (Post-APMC Proposal):** **1,599 physical series** (if ` APMC` suffix is stripped to unify pre- and post-November 2025 records).

---

## 3. Duplicate Records & Ambiguity Resolution Protocol

When multiple records share an identical `(District, Market, Commodity, Variety, Arrival_Date)` tuple:

### Empirical Audit Findings:
- Total duplicate series-date groups: **4,393 groups** (comprising 8,844 total rows).
- Groups with **identical prices** across Modal, Min, and Max: **13 groups** (0.3%).
- Groups with **conflicting Modal prices**: **4,363 groups** (99.3%).
- Groups with **identical Modal prices but conflicting Min/Max spread**: **17 groups** (0.4%).
- Total groups with **conflicting prices**: **4,380 groups** (99.7%).

### Methodological Defect in Existing Pipeline:
In `src/data_loader.py` line 58:
```python
df = df.drop_duplicates(subset=series_cols + ['Arrival_Date'], keep='first').copy()
```
The original codebase used `keep='first'`, which **silently dropped 4,380 conflicting records** based solely on arbitrary file ordering.

### Phase 1 Audit Protocol:
1. No records were silently deleted. Every flagged duplicate is cataloged in [`backing/phase_01/outputs/duplicate_groups.csv`](../outputs/duplicate_groups.csv).
2. For exact calendar matching benchmarks, the canonical deduplicated baseline (155,741 records) was analyzed, and every conflicting row was flagged in [`backing/phase_01/outputs/data_quality_flags.csv`](../outputs/data_quality_flags.csv) under `AMBIGUOUS_DUPLICATE_DATE`.
3. In subsequent feature engineering (Phase 2), duplicate date conflicts must either be resolved via trade-weighted daily averages or explicitly flagged with an ambiguity indicator.
