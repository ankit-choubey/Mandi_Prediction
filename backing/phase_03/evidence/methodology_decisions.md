# Phase 3 Methodology Decisions and Model Selection Rationales

## 1. Task Definition & Target Formulation
The primary task is 3-class classification over a fixed 7-calendar-day forward horizon:
- **Favorable**: $R_7 > +2.5\%$
- **Normal**: $-2.5\% \le R_7 \le +2.5\%$
- **Unfavorable**: $R_7 < -2.5\%$

### Why Directional Classification instead of Continuous Price Prediction?
1. **Physical Mandi Stickiness**: Wholesale agricultural prices frequently remain unchanged for consecutive days within local mandi yards due to convention and modal lot bidding.
2. **Asymmetric Decision Value**: For farmers and traders deciding whether to sell immediately or hold produce, small sub-2% fluctuations are noise consumed by transport/handling costs. Distinguishing genuine upward breakout ($>+2.5\%$) from downward decline ($<-2.5\%$) is the economically relevant signal.
3. **Secondary Regression Evaluation**: To test this empirically, continuous return percentage regression was evaluated as a secondary experiment. Results confirm that simple Zero-Return persistence beats complex regressors on MAE (11.06% vs 13.20% for LightGBM Regressor), whereas classification models succeed in extracting non-trivial directional regime signals.

---

## 2. Selection of Baselines

Four non-trivial, leakage-safe baselines were implemented:

1. **Baseline A: Majority-Class Predictor**
   - *Logic*: Always predicts "Normal", the most frequent class in historical training data (60.26%).
   - *Rationale*: Defines the absolute floor for uncalibrated accuracy. Any model reporting >50% accuracy on this dataset might simply be masquerading as the majority class while providing zero value on break-out price swings.

2. **Baseline B: Historical Class Frequency Baseline**
   - *Logic*: Draws random predictions according to the empirical training class prior ($P(\text{Normal})=0.6026, P(\text{Unfav})=0.2168, P(\text{Fav})=0.1807$).
   - *Rationale*: Benchmarks random guessing calibrated to class imbalance.

3. **Baseline C: Simple Historical Momentum Rule**
   - *Logic*: Predicts future direction from past 7-day price movement:
     $$\hat{Y} = \begin{cases} \text{Favorable} & \text{if } R_{-7} > +2.5\% \\ \text{Unfavorable} & \text{if } R_{-7} < -2.5\% \\ \text{Normal} & \text{otherwise} \end{cases}$$
   - *Rationale*: A classic technical trading rule that requires zero machine learning. Establishes whether past momentum alone explains future price movement.

4. **Baseline D: Persistence / No-Change Benchmark**
   - *Logic*: Assumes price stickiness (future price = current price $\implies R_7 = 0\% \implies \text{Normal}$).
   - *Rationale*: Equivalent to the majority class under the fixed threshold convention, representing wholesale inertia.

---

## 3. Candidate Models

1. **Multinomial Logistic Regression**:
   - Baseline parametric linear model with L2 regularization. Provides direct interpretability of linear feature weights.
2. **Decision Tree (Constrained)**:
   - Non-linear tree model with `max_depth=5` and `min_samples_leaf=50` to prevent overfitting.
3. **Random Forest Ensemble**:
   - Bagged ensemble (`n_estimators=100, max_depth=8, min_samples_leaf=20`) to capture non-linear feature interactions with variance reduction.
4. **LightGBM (Gradient Boosted Decision Trees)**:
   - Modern histogram-based gradient boosting (`n_estimators=100, max_depth=5, lr=0.05, min_child_samples=50`). State-of-the-art tabular benchmark.

---

## 4. Evaluation Metrics Rationale

- **Accuracy**: Reported for completeness, but explicitly disqualified as the primary selection criterion due to class imbalance (Majority class alone gets 55.90% accuracy).
- **Balanced Accuracy**: Arithmetic mean of per-class recalls. Penalizes models that collapse into the majority class.
- **Macro F1**: Unweighted harmonic mean of per-class precision and recall. Treats minority classes (Favorable, Unfavorable) with equal importance to Normal.
- **Subgroup Evaluations**: Evaluated separately across the top 5 commodities and top 5 mandi yards. Subgroups with $<30$ samples are flagged as "INSUFFICIENT EVIDENCE" to avoid unreliable assertions.

---

## 5. Model Selection Decision on Validation Data

Candidate model selection was performed strictly using the **Validation Partition** ($n=2,914$, origin dates `2026-01-25` to `2026-03-31`):
- Majority Baseline: Balanced Acc = **33.33%**, Macro F1 = **0.2136**
- Historical Momentum Rule: Balanced Acc = **35.76%**, Macro F1 = **0.3422**
- Logistic Regression: Balanced Acc = **39.89%**, Macro F1 = **0.3672**
- Decision Tree: Balanced Acc = **39.52%**, Macro F1 = **0.3626**
- Random Forest: Balanced Acc = **37.79%**, Macro F1 = **0.3362**
- **LightGBM**: Balanced Acc = **44.53%**, Macro F1 = **0.4369**

**LightGBM** achieved the highest Macro F1 (0.4369) and Balanced Accuracy (44.53%) on validation data without overfitting, and was frozen as the single primary candidate. Test holdout performance (60.40% acc, 0.4616 Macro F1) is reported as an exploratory historical baseline, NOT as an unexamined holdout.

---

## 6. Zero-Return Persistence Metric Convention
For the `Zero_Return_Persistence_Benchmark`, the predicted return is strictly $0.0\%$. Under the standard directional sign evaluation:
$$\text{Directional Match} = \mathbf{1}_{\{y_{\text{true}} \times \hat{y} > 0\}}$$
Because $\hat{y} = 0$, $y_{\text{true}} \times 0 = 0$, which is never strictly greater than zero.
Evaluating this as 0% directional accuracy is misleading because a 0 prediction has no positive or negative directional sign.
**Decision**: In accordance with methodological standards, directional accuracy for the Zero-Return benchmark is formally designated **`N/A`** (with explanation), while its MAE (9.81% Val, 11.06% Test) and RMSE (38.76% Val, 35.27% Test) are preserved as the primary continuous benchmarks.

---

## 7. Numerical Diagnostics for Logistic Regression
The 1,350 RuntimeWarnings in Logistic Regression were empirically traced to Apple Accelerate BLAS hardware FPU denormal flags during SIMD matrix multiplication on zero/sparse matrices in NumPy 2.x on macOS arm64.
All fitted model coefficients were verified to be 100% finite and non-NaN. Scoped handling via `np.errstate(divide='ignore', over='ignore', invalid='ignore')` resolves spurious hardware flags while preserving true algorithmic convergence checks (0 ConvergenceWarnings under max_iter=1000).

---

## 8. Disclaimers on Farmer Decision Utility
While LightGBM demonstrates statistically significant predictive improvements over majority baselines, **no claim is made that the model is ready or superior for real-world farmer sell/store recommendations**. A real-world decision requires explicit modeling of storage losses, cold storage electricity charges, bagging fees, local transport costs, and risk aversion, which are outside the scope of Phase 3 baseline modeling.

