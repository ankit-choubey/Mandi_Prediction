# Phase 3 Holdout Integrity Review and Evaluation Policy

## 1. Executive Summary & Defect Identification
In the initial Phase 3 implementation, the historical holdout partition spanning origin dates **2026-04-08 to 2026-08-25** ($n=12,625$) was evaluated across multiple classification models (Logistic Regression, Decision Tree, Random Forest, LightGBM) and multiple continuous regression models (Ridge, LightGBM Regressor). Simultaneously, the documentation described this partition as an "untouched single-use final holdout".

This was a methodological defect:
> **Auditing Rule**: A test set cannot be claimed as an "untouched final holdout" once multiple candidate models have been evaluated on it and their test scores inspected by the modeler. Doing so violates the single-use holdout principle and risks selection bias.

---

## 2. Evaluation of Available Data & Holdout Feasibility (Path A vs Path B)

The Phase 3 audit investigated whether a genuinely new, later, independent holdout period could be constructed from the existing dataset (**Path A**):

### Empirical Check on Master Dataset Boundaries
- Total raw records ingested: `160,192` across `data/raw/*.csv`.
- Earliest observation date: `2024-09-01`.
- **Latest observation date in repository**: **`2026-09-01`**.
- For a 7-calendar-day forward prediction target ($T+7$):
  $$\text{Realization Date} = T + 7 \text{ days}$$
  The latest possible origin date $T$ with an observable target price is:
  $$T_{\text{max}} = \text{2026-09-01} - 7\text{ days} = \textbf{2026-08-25}$$
- All records between `2026-08-26` and `2026-09-01` have no observed $T+7$ target within the dataset and are boundary-truncated.

### Conclusion on Holdout Feasibility
**No later observations exist in the repository.** Therefore, Path A (carving a new later holdout) is physically impossible without downloading new external data (which is strictly forbidden in this phase). 

We adopt **Path B**:
- We explicitly re-label the `2026-04-08` to `2026-08-25` partition as **`EXPLORATORY_TEST`** (Historical Holdout).
- We document all test scores as **exploratory/development holdout results**.
- We strictly disclaim any assertion that this partition was an "untouched final test".
- A future observation period (data collected after September 1, 2026) is formally required before claiming an independent, unadulterated final out-of-sample evaluation.

---

## 3. Candidate Model Selection Governance

To guarantee that model selection was not biased by test set inspection:
1. **Selection Decision Driven Solely by Validation Partition** ($n=2,914$, origin dates `2026-01-25` to `2026-03-31`):
   - **Primary Selection Metric**: **Validation Macro F1** and **Validation Balanced Accuracy** (to protect against trivial majority-class collapse).
   - Validation Performance:
     - Majority Class Baseline: Macro F1 = `0.2136` | Balanced Acc = `33.33%`
     - Historical Momentum Rule: Macro F1 = `0.3422` | Balanced Acc = `35.76%`
     - Logistic Regression: Macro F1 = `0.3672` | Balanced Acc = `39.89%`
     - Decision Tree (depth=5): Macro F1 = `0.3626` | Balanced Acc = `39.52%`
     - Random Forest (100 trees): Macro F1 = `0.3362` | Balanced Acc = `37.79%`
     - **LightGBM (100 trees, depth=5)**: Macro F1 = **`0.4369`** | Balanced Acc = **`44.53%`**
2. **Freezing Decision**:
   - LightGBM was selected as the **single primary candidate** because it demonstrated the strongest balanced predictive power on the Validation partition without overfitting.
   - All feature definitions, transformers, hyperparameters, and decision thresholds were frozen before summarizing holdout performance.
3. **Exploratory Holdout Performance**:
   - On the exploratory test partition ($n=12,625$), LightGBM achieved `60.40%` accuracy, `46.19%` balanced accuracy, and `0.4616` Macro F1.
   - These scores confirm that the validation superiority was not an artifact of the validation window, but are explicitly reported as development holdout evidence, not an untouched test score.
