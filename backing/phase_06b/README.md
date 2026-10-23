# Phase 06b: Data Discovery, Validation & Mathematical Feasibility

**Project:** APMC Mandi Market Intelligence System  
**Repository:** `ankit-choubey/Mandi_Prediction`  
**Phase:** 06b — Data Discovery, Validation & Mathematical Feasibility  
**Branch:** `main`  
**Date:** October 2026  
**Auditor:** Priyanshu  

---

## 1. Executive Mission

The objective of Phase 06b is **NOT to immediately build another machine learning model**. 

Rather, Phase 06b establishes with rigorous empirical, statistical, and operational evidence whether the expanded Mandi Prediction System proposed for agricultural market decision support is actually feasible using real Indian agricultural-market data.

The expanded system was proposed to eventually support:
1. Multi-horizon price prediction ($T+1, T+3, T+7, T+14, T+30$).
2. Price movement classification (Favorable, Normal, Unfavorable).
3. Supply and arrival volume influence.
4. Weather and meteorological shocks.
5. Production and crop acreage seasonality.
6. Storage-duration effects.
7. Storage tariffs and warehouse costs.
8. Transportation freight costs and diesel prices.
9. Labour, bagging, and handling costs.
10. Quality deterioration and price markdowns.
11. Perishability differences between crops.
12. Sell-now versus store economic decision support.
13. District and mandi spatial relationships.
14. Scalable Pan-India multi-state architecture.

In Phase 06b, we subjected every one of these 14 components to empirical verification, mathematical auditing, leakage analysis, and operational feasibility testing.

---

## 2. Directory Structure & Evidence Artifacts

The `backing/phase_06b/` evidence directory contains the complete verified artifact suite:

```text
backing/phase_06b/
├── README.md                                  # Executive guide, navigation, and core findings summary
├── data_requirements_matrix.csv              # 36-variable schema audit across 7 operational categories
├── dataset_inventory.csv                     # 14 real Indian agricultural, weather, and logistics data sources
├── dataset_scorecard.csv                     # 16 candidate datasets scored across 12 dimensions into 4 tiers
├── leakage_and_availability_audit.md         # Four-tier leakage audit (SAFE, SAFE WITH LAG, UNSAFE, UNKNOWN)
├── join_compatibility_matrix.csv             # Spatial, temporal, commodity, and unit join compatibility tests
├── crop_storage_profiles.csv                 # Detailed storage profiles for 18 crops across 3 perishability tiers
├── mathematical_method_comparison.md         # Rigorous comparison of Baselines, ARIMA, ML, and Deep Learning
├── ablation_plan.md                          # Progressive ablation plan for Models 0 through 6
├── statistical_testing_plan.md               # McNemar, Diebold-Mariano, Wilcoxon, and Cluster Bootstrap protocols
├── recommended_data_foundation.md            # Answers to all 14 mandatory foundation and roadmap questions
├── experiment_results.md                     # Empirical findings across multi-horizon, LODO, and hurdle rate tests
├── limitations.md                            # Comprehensive structural, physical, and governance limitations
├── run_phase06b_experiments.py               # Reproducible empirical execution script (15.06s runtime)
├── multi_horizon_feasibility_summary.csv     # Machine-readable multi-horizon availability and distribution stats
├── classification_threshold_comparison.csv   # Machine-readable comparison of 5 thresholding alternatives
├── cross_district_generalization.csv         # Machine-readable Leave-One-District-Out cross validation results
├── multi_horizon_regression_benchmark.csv    # Machine-readable regression vs persistence benchmark across 5 horizons
├── crop_category_hurdle_rate_analysis.csv    # Machine-readable economic hurdle rate calculations by crop tier
└── execution_log.txt                         # Cryptographic execution timestamp and operational trace log
```

---

## 3. Top-Line Empirical Discoveries from Phase 06b

1. **Continuous Price Regression is Structurally Disqualified:**
   Across all five tested horizons ($T+1$ to $T+30$), simple zero-return price stickiness persistence outperforms machine learning regression out-of-sample (Diebold-Mariano $p < 0.01$). This is driven by modal price stickiness (18%–36% of quotes do not change) combined with heavy-tailed jump volatility.
2. **Fixed $\pm 2.5\%$ Band Traps Normal Class:**
   At $T+1$, **80.08%** of records fall into the "Normal" class under $\pm 2.5\%$. At $T+7$, **59.48%** fall into Normal. Quantile terciles (33.3% / 33.3% / 33.3%) is the mathematically superior formulation for machine-learning evaluation.
3. **Cross-District Generalization Fails on Distinct Agro-Climatic Zones:**
   A spatial model trained on Central UP and NCR (Kanpur, Lucknow, Unnao, Ghaziabad) achieves **53.86% accuracy on Jhansi**, which is **worse than the 54.67% naive majority baseline**. Models cannot be generalized pan-India without agro-climatic regional clustering.
4. **7-Day Tactical Storage is Economically Unviable Across Crop Categories:**
   - **Perishables (Tomato/Cucumber):** Requires an **+18.06% price jump in 7 days** to break even against physical rotting and handling friction. Empirical win rate is only **6.94% (93.06% loss frequency)**.
   - **Durable Grains (Wheat/Rice):** Fixed loading/bagging friction (₹23/qtl) requires +1.46% return against +0.59% average weekly price change. Empirical win rate is only **12.75% (87.25% loss frequency)**.
   - **Operational Directive:** 7-day tactical storage advice must remain strictly prohibited. Grains require 60 to 180-day seasonal holding models.
5. **Immediate Data Acquisition Priority:**
   The **CEDA Agmarknet Harmonized Archive (Ashoka University)** must be acquired immediately to backfill missing physical arrival volume quantities (Tonnes) across all 5 UP districts.

---

## 4. Reproducibility & Verification

To reproduce all Phase 06b empirical computations from repository root:
```bash
python backing/phase_06b/run_phase06b_experiments.py
```
Runtime: ~15 seconds on standard hardware. Outputs are saved directly to this directory.
