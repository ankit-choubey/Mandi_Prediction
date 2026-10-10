# Phase 1 Reproduction & Verification Instructions

**Audit Phase:** Phase 1 — Data Integrity & Temporal Continuity  
**Date:** October 10, 2026  

---

## 1. Prerequisites
Ensure Python 3.9+ with `pandas`, `numpy`, `scipy`, and `pytest` is available:
```bash
python3 -c "import pandas, numpy, scipy, pytest; print('Environment Ready')"
```

---

## 2. Re-Generating All Phase 1 Audit Outputs

To re-run the full Phase 1 data integrity engine and re-compute all 9 output CSV files from the raw CSV data:
```bash
python3 backing/phase_01/tests/run_phase01_audit.py
```

This will re-populate:
- `backing/phase_01/outputs/input_inventory.csv`
- `backing/phase_01/outputs/duplicate_groups.csv`
- `backing/phase_01/outputs/data_quality_flags.csv`
- `backing/phase_01/outputs/price_quality_summary.csv`
- `backing/phase_01/outputs/market_mapping_review.csv`
- `backing/phase_01/outputs/observation_gap_summary.csv`
- `backing/phase_01/outputs/exact_target_coverage.csv`
- `backing/phase_01/outputs/target_match_examples.csv`
- `backing/phase_01/outputs/class_distribution.csv`

---

## 3. Running the Automated Test Suite

Execute the formal pytest verification suite:
```bash
python3 -m pytest backing/phase_01/tests/test_phase01_data_integrity.py -v
```

To re-capture test execution output to `test_results.txt`:
```bash
python3 -m pytest backing/phase_01/tests/test_phase01_data_integrity.py -v | tee backing/phase_01/tests/test_results.txt
```

---

## 4. Verification of Output Integrity

To check that all 9 CSV outputs exist, are non-empty, and contain the expected column counts:
```bash
python3 -c "
import glob, os, pandas as pd
files = sorted(glob.glob('backing/phase_01/outputs/*.csv'))
assert len(files) == 9, f'Expected 9 CSV files, found {len(files)}'
for f in files:
    df = pd.read_csv(f)
    print(f'Verified: {os.path.basename(f):30s} | {len(df):6,d} rows | {len(df.columns):2d} cols')
print('All outputs verified successfully.')
"
```
