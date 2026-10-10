# Phase 3 Reproduction Instructions

## Environment Prerequisites

- **Python Version**: Python 3.10+ (Tested on Python 3.14.0 on macOS / Apple Silicon).
- **Core Dependencies**:
  - `pandas >= 2.0.0`
  - `numpy >= 1.24.0`
  - `scikit-learn >= 1.3.0`
  - `lightgbm >= 4.0.0`
  - `pytest >= 7.0.0`

Install required packages if not already present:
```bash
pip install pandas numpy scikit-learn lightgbm pytest
```

---

## Step-by-Step Reproduction

### 1. Execute the Phase 3 Experiment Runner
From the repository root directory:
```bash
python3 backing/phase_03/tests/run_phase03_experiment.py
```
*Expected Exit Code*: `0`
*Outputs Generated*:
- `backing/phase_03/outputs/feature_audit.csv`
- `backing/phase_03/outputs/temporal_split_summary.csv`
- `backing/phase_03/outputs/baseline_metrics.csv`
- `backing/phase_03/outputs/model_comparison.csv`
- `backing/phase_03/outputs/classification_report.csv`
- `backing/phase_03/outputs/confusion_matrix.csv`
- `backing/phase_03/outputs/subgroup_performance.csv`
- `backing/phase_03/outputs/regression_metrics.csv`
- `backing/phase_03/logs/phase03_execution.log`

### 2. Run the Phase 3 Test Suite
Run the 16 automated unit and integration tests verifying leakage resistance, embargo purging, holdout integrity review, candidate selection logic, zero-return conventions, and warning diagnostics:
```bash
python3 -m pytest backing/phase_03/tests/test_phase03_methodology.py -v
```
*Expected Result*: `16 passed in < 3s`

### 3. Run the Full Repository Audit Test Suite (Phases 1, 2, 3)
Run all 41 audit tests across the complete project lifecycle:
```bash
python3 -m pytest backing/phase_01/tests/ backing/phase_02/tests/ backing/phase_03/tests/ -v
```
*Expected Result*: `41 passed in < 5s`

---

## Key Output File Locations

- Findings Report: `backing/phase_03/findings.md`
- Holdout Integrity Review: `backing/phase_03/evidence/holdout_integrity_review.md`
- Warning Diagnostics & Resolution: `backing/phase_03/evidence/warning_diagnostics.md`
- Feature Specification: `backing/phase_03/evidence/feature_specification.md`
- Temporal Split Details: `backing/phase_03/evidence/temporal_split.md`
- Methodology Decisions: `backing/phase_03/evidence/methodology_decisions.md`
- Execution Log: `backing/phase_03/logs/phase03_execution.log`
