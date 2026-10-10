# Phase 3 Feature Engineering Specification: Strictly Causal Information

## Overview
This document specifies all predictor variables engineered for the Phase 3 baseline modeling experiment.
In accordance with strict leakage-safe auditing standards:
1. Every feature is available at prediction origin date $T$ (after the close of trading on date $T$).
2. No future price, target return, or target label ($T+1$ or later) enters feature calculations.
3. Imputation and scaling transformers are fit exclusively on the Training partition ($T \le \text{2026-01-17}$).
4. Zero future information is backward-filled into historical volatility or lag indicators.

---

## Complete Feature Inventory

| Feature Name | Mathematical Definition | Source Columns | Lookback Window | Availability at $T$ | Missingness & Imputation | Leakage Assessment |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Log_Modal_Price** | $\ln(\max(P_T, 1.0))$ | `Modal_Price_Num` | Date $T$ | Available at close of date $T$ | 0% missing in master data | **ZERO LEAKAGE**: Log monotonic transformation of observed price at $T$. |
| **Price_Spread_Ratio** | $\frac{P_T^{\text{max}} - P_T^{\text{min}}}{\max(P_T, 1.0)}$ | `Max_Price_Num`, `Min_Price_Num`, `Modal_Price_Num` | Date $T$ | Available at close of date $T$ | 0% missing in master data | **ZERO LEAKAGE**: Normalized intraday dispersion within physical mandi auction at $T$. |
| **Past_Return_1d** | $\left[\frac{P_T - P_{T-1}}{P_{T-1}}\right] \times 100$, clipped to $[-100, 300]$ | `Modal_Price_Num`, `Modal_Price_Num_Lag1` | Exact $T-1$ calendar day | Available at $T$ | 27.0% missing (Sunday/holiday closures); imputed with training median | **ZERO LEAKAGE**: Strictly past calendar observation from day $T-1$. |
| **Past_Return_3d** | $\left[\frac{P_T - P_{T-3}}{P_{T-3}}\right] \times 100$, clipped to $[-100, 300]$ | `Modal_Price_Num`, `Modal_Price_Num_Lag3` | Exact $T-3$ calendar days | Available at $T$ | 30.1% missing; imputed with training median | **ZERO LEAKAGE**: Strictly past calendar observation from day $T-3$. |
| **Past_Return_7d** | $\left[\frac{P_T - P_{T-7}}{P_{T-7}}\right] \times 100$, clipped to $[-100, 300]$ | `Modal_Price_Num`, `Modal_Price_Num_Lag7` | Exact $T-7$ calendar days | Available at $T$ | 25.8% missing; imputed with training median | **ZERO LEAKAGE**: Strictly past calendar observation from day $T-7$. |
| **Past_Return_Bounded7d** | $\left[\frac{P_T - P_{\text{Bounded7}}}{P_{\text{Bounded7}}}\right] \times 100$, clipped to $[-100, 300]$ | `Modal_Price_Num`, `Lag_Price_Bounded7` | $T-7$ fallback $T-8$ fallback $T-9$ | Available at $T$ | 12.9% missing; imputed with training median | **ZERO LEAKAGE**: Strictly past observations $\le 9$ days old. |
| **Momentum_Ratio_7d** | $\frac{P_T}{\max(P_{\text{Bounded7}}, 1.0)}$, clipped to $[0.1, 5.0]$ | `Modal_Price_Num`, `Lag_Price_Bounded7` | $T-7$ fallback $T-8$ fallback $T-9$ | Available at $T$ | 12.9% missing; imputed with training median | **ZERO LEAKAGE**: Strictly past momentum ratio relative to past week. |
| **Hist_Vol_Commodity** | Expanding sample std of daily commodity returns up to date $T$ ($\text{min\_periods}=10$) | `Modal_Price_Num`, `Arrival_Date_Parsed`, `Commodity` | All historical dates $\le T$ | Available at $T$ | Missing for initial burn-in (<10 days); imputed with training median | **ZERO LEAKAGE**: Phase 2 causal rule with zero backward-filling of future volatility. |
| **Day_Of_Week** | $\text{DayOfWeek}(T) \in [0, 6]$ (0=Monday) | `Arrival_Date_Parsed` | Date $T$ | Available at $T$ | 0% missing | **ZERO LEAKAGE**: Deterministic astronomical calendar property. |
| **Month** | $\text{Month}(T) \in [1, 12]$ | `Arrival_Date_Parsed` | Date $T$ | Available at $T$ | 0% missing | **ZERO LEAKAGE**: Exogenous calendar seasonality property. |
| **Commodity** | Categorical name (e.g. Potato, Onion, Wheat) | `Commodity` | Static series attribute | Known at origin | One-hot encoded; unknown test categories handled gracefully | **ZERO LEAKAGE**: Physical trade commodity identifier. |
| **Market_Canonical** | Unified canonical market name | `Market`, `canonical_market_mapping.csv` | Static series attribute | Known at origin | One-hot encoded; protected distinct identities preserved | **ZERO LEAKAGE**: Approved Phase 2 canonical mandi identity. |
| **Grade** | Quality classification (FAQ, Medium, etc.) | `Grade` | Static series attribute | Known at origin | One-hot encoded | **ZERO LEAKAGE**: Commercial trade quality grading. |

---

## Leakage Prevention Safeguards

1. **Pre-Prediction Isolation**: All predictors rely exclusively on information available when trading closes on date $T$.
2. **Strict Causal Volatility**: Volatility estimates use expanding windows up to date $T$. No future dates are used, and no future standard deviations are backward-filled.
3. **Training-Only Preprocessing**: The `ColumnTransformer` (consisting of median `SimpleImputer`, `StandardScaler`, and `OneHotEncoder`) is fitted solely on the training partition. The validation and test features are transformed using training parameters.
4. **Automated Verification**: Automated tests in `tests/test_phase03_methodology.py` verify that perturbing prices on days $T+1$ through $T+7$ produces zero change in any feature vector at date $T$.
