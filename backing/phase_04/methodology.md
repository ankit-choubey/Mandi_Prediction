# Phase 4: Methodology — Sell-versus-Store Decision Support & Backtesting

**Project:** Mandi_Prediction  
**Repository:** `ankit-choubey/Mandi_Prediction`  
**Phase:** 4 — Economic Decision Support and Sell-versus-Store Validation  
**Date:** October 10, 2026  

---

## 1. Objective and Research Scope

Phase 4 bridges statistical market condition forecasting and empirical economic decision analysis. The primary research question is:
> *Do machine-learning market condition signals generate positive net economic returns for farmers after accounting for physical storage fees, quantity loss, quality degradation, and financing or opportunity costs over a 7-day holding horizon?*

This is an **exploratory research evaluation**. It does NOT constitute operational farmer advice.

---

## 2. Leakage-Safe Data Flow and Canonical Alignment

1. **Canonical Series Identity:**
   All market observations are tracked by the 5-tuple canonical series key:
   $$\text{Series ID} = (\text{District}, \text{Market}, \text{Commodity}, \text{Variety}, \text{Grade})$$
   Preserves commercial grade separation and eliminates cross-grade price distortion.
2. **Strategy 2 Duplicate Exclusion:**
   Excludes 2,664 ambiguous same-grade conflicting quotes across 1,321 dates (DEC-008) to guarantee 100% price quote purity.
3. **Exact Calendar Target Matching:**
   Future price $P_{T7}$ is obtained strictly via exact calendar date merge:
   $$\text{Date}_{\text{target}} = \text{Date}_T + 7 \text{ calendar days}$$
   Next available market observations are **never** substituted for $T+7$.
4. **Horizon-Aware Temporal Splitting & Embargo Purging:**
   Partitions the timeline chronologically with 8-day purged embargo buffers:
   - **Training Partition:** 2024-09-01 to 2026-01-13 ($n = 99,881$ records).
   - **Train/Val Embargo Buffer:** 94 origins purged ($T > 2026-01-13$ and $< 2026-01-21$).
   - **Validation Partition:** 2026-01-21 to 2026-05-01 ($n = 5,671$ records).
   - **Val/Test Embargo Buffer:** 636 origins purged ($T > 2026-05-01$ and $< 2026-05-09$).
   - **Exploratory Historical Test Partition:** 2026-05-09 to 2026-08-25 ($n = 9,551$ records).

---

## 3. Decision Policies Evaluated

Five distinct operational policies are evaluated:

### Policy A: Always Sell Immediately (Baseline)
- **Decision Rule at Date $T$:** SELL immediately.
- **Proceeds:** $R_{\text{sell}} = Q \times P_T$.
- **Incremental Return vs Baseline:** Exactly ₹0.00 / quintal.

### Policy B: Always Store for 7 Days
- **Decision Rule at Date $T$:** STORE produce for 7 days regardless of price signal.
- **Proceeds:** $R_{\text{store}}(P_{T7})$.
- **Incremental Return:** $\Delta R = R_{\text{store}} - R_{\text{sell}}$.

### Policy C: Simple Price-Trend Policy (Information at $T$)
- **Decision Rule at Date $T$:** Uses recent 7-day trailing price momentum (`Price_Change_7d` computed causally at Date $T$).
  $$\text{Action} = \begin{cases} \text{STORE}, & \text{if } \text{Price\_Change\_7d} > \Delta P_{\text{break\_even}}\% \\ \text{SELL}, & \text{otherwise} \end{cases}$$
- Strictly causal: relies only on backward-looking momentum available at $T$.

### Policy D: Model-Signal Policy (Information at $T$)
- **Decision Rule at Date $T$:** Uses the gradient boosted classifier trained strictly on the Training partition.
  $$\text{Action} = \begin{cases} \text{STORE}, & \text{if } \hat{Y}_T = \text{Favorable (Class 2)} \\ \text{SELL}, & \text{otherwise} \end{cases}$$
- Evaluated out-of-sample on Validation ($n = 5,671$) and on the Exploratory Test partition ($n = 9,551$).

### Policy E: Oracle Hindsight Benchmark (Theoretical Upper Bound)
- **Decision Rule at Date $T$:** Possesses perfect future knowledge of $P_{T7}$.
  $$\text{Action} = \begin{cases} \text{STORE}, & \text{if } \Delta R(P_T, P_{T7}) > 0 \\ \text{SELL}, & \text{otherwise} \end{cases}$$
- **Status:** Unattainable upper bound; defines the theoretical ceiling of maximum economic value extractable from 7-day storage.

---

## 4. Evaluation Metrics

For each policy and scenario, the following metrics are computed:
1. **Times Stored & Percent Stored:** Volume of storage decisions triggered.
2. **Storage Win Rate (%):** Proportion of storage actions where net storage proceeds exceeded immediate sale proceeds ($\Delta R > 0$).
3. **Mean Incremental Return (₹ / quintal):** Average net profit or loss per initial quintal across all eligible decision points.
4. **Total Net Gain (₹ / 10 quintals):** Aggregate financial benefit across all decisions for a representative 10-quintal smallholder batch.
5. **Downside Risk (P05 & Worst Case):** The 5th percentile and minimum per-quintal return when storing, capturing severe tail loss risk.

---

## 5. Methodological Safeguards Against Bias

- **No Double Counting:** Carrying costs represent either borrowing interest or opportunity cost, never both.
- **No Free Storage:** Fixed handling and variable storage costs cannot be assumed zero.
- **Exploratory Test Independence:** The historical test partition (May–August 2026) is reported as an exploratory historical evaluation only. No thresholds or decision rules were tuned or selected on this partition.
