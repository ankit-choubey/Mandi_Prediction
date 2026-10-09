# Mandi Prediction: Permanent Mathematical & Statistical Audit Archive

This directory (`backing/`) serves as the permanent, immutable, evidence-backed audit archive for the **APMC Mandi Market Intelligence System** ([ankit-choubey/Mandi_Prediction](https://github.com/ankit-choubey/Mandi_Prediction)).

---

## 1. Why This Audit Archive Exists

Agricultural decision-support systems directly impact farming operations, storage economics, and wholesale logistics. Before deploying machine learning models or economic decision layers, we must establish with scientific rigor whether the data, methodology, and empirical claims are:
1. **Mathematically Valid:** Features, targets, time lags, and break-even formulations are logically and temporally sound with zero lookahead leakage.
2. **Statistically Reliable:** Performance benchmarks significantly exceed naive baselines, distributions are properly characterized, and assertions of accuracy are reproducible.
3. **Practically Defensible:** Assumptions about logistics, spoilage, labor, and warehouse storage costs are grounded in verified official empirical sources rather than fabricated numbers.

This archive preserves every finding, raw check, reproduction script, execution output, and decision record across sequential phases of the audit.

---

## 2. Directory Hierarchy

```text
backing/
├── README.md                  # Archive purpose, rules of evidence, and reproduction guide
├── PROJECT_AUDIT.md           # Master consolidated audit report updated cumulatively
├── phase_00/                  # Phase 0: Repository Discovery, Schema Verification & Setup
│   ├── findings.md            # Detailed phase findings, verified facts, and limitations
│   ├── evidence/              # Environment checks, inventory scans, and execution logs
│   ├── outputs/               # Machine-readable scan outputs and kernel execution logs
│   └── tests/                 # Unit/smoke tests verifying environment & path resolution
└── phase_01/                  # Phase 1: Data Integrity & Exact-Calendar Continuity (Next Phase)
    ├── findings.md            # Planned scope, hypothesis list, and verification status
    ├── evidence/              # Reserved for Phase 1 raw data check evidence
    ├── outputs/               # Reserved for Phase 1 distribution summaries & gap matrices
    └── tests/                 # Reserved for Phase 1 data validation test suites
```

*Note: Directories for future phases (Phase 2, Phase 3, etc.) will be created only when those phases officially begin.*

---

## 3. Strict Rules of Evidence & Scientific Integrity

All work recorded in this archive is governed by non-negotiable principles of scientific integrity:

1. **No Fabrication:** Never fabricate file paths, schemas, dataset sizes, logs, test outputs, accuracy figures, or citations. A test is never marked as passing unless it was executed and succeeded.
2. **Clear Epistemic Distinctions:** Every assertion must explicitly distinguish among:
   - **Observed Evidence:** Concrete, directly measured empirical data (e.g., exact line counts, null counts, verified dates).
   - **Assumptions:** Explicit operational premises (e.g., assuming FAQ grade represents standard trade volume).
   - **Hypotheses:** Testable propositions that require validation before acceptance (e.g., whether Sunday missingness is structural).
   - **Conclusions:** Inferences supported strictly by verified observations.
3. **Labels for Prior Claims:**
   - Any prior claim not yet independently verified must be labeled **`UNVERIFIED`**.
   - Any unresolved variable or parameter must be labeled **`UNKNOWN`**.
4. **Cumulative Master Record:** Every completed phase **must** update [`backing/PROJECT_AUDIT.md`](./PROJECT_AUDIT.md). Earlier findings must **never be silently deleted or rewritten** if later evidence disagrees; rather, the discrepancy must be recorded as an explicit correction citing the superseding evidence.
5. **Preservation of Raw Inputs:** Raw datasets must never be edited, cleaned in place, or overwritten.

---

## 4. How to Reproduce and Verify Results

### Local Environment Verification
Ensure Python 3.9+ with standard data science packages is installed:
```bash
python3 -c "import pandas, numpy, scipy, sklearn, nbformat; print('Dependencies OK')"
```

### Reproducing Phase 0 Notebook Execution
The Phase 0 audit notebook is located at [`notebooks/mandi_mathematical_audit.ipynb`](../notebooks/mandi_mathematical_audit.ipynb). It executes without modifying any files:
```bash
python3 -m jupyter nbconvert --to notebook --execute notebooks/mandi_mathematical_audit.ipynb \
  --output mandi_mathematical_audit.ipynb --output-dir notebooks
```

### Reproducing on Kaggle
1. The notebook is deployed to Kaggle at: [https://www.kaggle.com/code/theankitchoubey/mandi-math-audit-p0](https://www.kaggle.com/code/theankitchoubey/mandi-math-audit-p0)
2. Uses standard Kaggle CPU environment with dataset `theankitchoubey/up-apmc-mandi-raw-dataset`.
3. To pull the latest execution status and logs via the Kaggle CLI:
```bash
kaggle kernels status theankitchoubey/mandi-math-audit-p0
kaggle kernels output theankitchoubey/mandi-math-audit-p0 -p backing/phase_00/outputs/
```
