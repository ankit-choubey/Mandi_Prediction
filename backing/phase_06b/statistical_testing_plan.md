# Phase 06b: Statistical Testing Plan & Hypothesis Testing Protocol

**Repository:** `ankit-choubey/Mandi_Prediction`  
**Phase:** 06b — Data Discovery, Validation & Mathematical Feasibility  
**Date:** October 2026  
**Auditor:** Priyanshu  

---

## 1. Governing Principle: Guarding Against Statistical Illusion

In machine learning and financial econometrics, numerical improvements between models (e.g. Accuracy 58.2% vs 59.1%) are frequently reported as evidence of superiority. In agricultural time-series data, however, observational cross-sectional correlation and temporal persistence frequently produce false-positive statistical significance if standard independent and identically distributed (i.i.d.) assumptions are applied.

> **"A numerical difference between two models is an anecdote. Only a statistically verified difference with documented effect size, cluster-robust confidence intervals, and controlled false discovery rate constitutes scientific evidence."**

---

## 2. Statistical Testing Suite for Agricultural Market Intelligence

To eliminate p-hacking, multiple-testing inflation, and serial correlation bias, the Mandi Prediction system enforces four formal statistical hypothesis tests:

### 2.1 Paired Classification Accuracy: McNemar’s Test
- **Purpose:** Determines whether Model B makes significantly fewer classification errors than Model A (or Naive Baseline) on the exact same paired holdout records.
- **Null Hypothesis ($H_0$):** Both models have equal marginal error rates ($p_b = p_c$).
- **Contingency Matrix:**
  $$\begin{pmatrix} n_{00} & n_{01} \\ n_{10} & n_{11} \end{pmatrix}$$
  where:
  - $n_{00}$ = both models incorrect
  - $n_{11}$ = both models correct
  - $b = n_{10}$ = Model B correct, Model A incorrect (Discordant pair 1)
  - $c = n_{01}$ = Model A correct, Model B incorrect (Discordant pair 2)
- **Test Statistic (with Edwards continuity correction):**
  $$\chi^2 = \frac{(|b - c| - 1)^2}{b + c} \sim \chi^2_1$$
- **Rejection Criterion:** Reject $H_0$ if $p < 0.05$ and $b > c$.
- **Empirical Finding in Phase 06b:**
  In cross-district transferability (LODO), Kanpur ($\chi^2 = 382.71, p < 10^{-15}$), Lucknow ($\chi^2 = 69.73, p < 10^{-15}$), and Ghaziabad ($\chi^2 = 67.37, p < 10^{-15}$) demonstrate overwhelming statistical significance over the majority baseline. Conversely, Jhansi ($\chi^2 = 4.86, p = 0.027$ with $b < c$, meaning Model B made *more* errors than baseline) and Unnao ($\chi^2 = 0.0, p = 1.0$) prove statistically unviable transfer.

### 2.2 Time-Series Forecast Comparison: Diebold-Mariano (DM) Test
- **Purpose:** Tests whether the forecast loss differential between two time-series models (e.g. LightGBM Regressor vs Zero-Return Persistence) is statistically significantly different from zero, accounting for serial correlation in forecast errors.
- **Loss Differential:**
  $$d_t = L(e_{1, t}) - L(e_{2, t})$$
  where $L(e) = |e|$ (MAE loss) or $e^2$ (MSE loss).
- **Test Statistic:**
  $$DM = \frac{\bar{d}}{\sqrt{\hat{V}(\bar{d})}} \xrightarrow{d} \mathcal{N}(0, 1)$$
  where $\hat{V}(\bar{d})$ is the Newey-West heteroskedasticity and autocorrelation consistent (HAC) variance estimator with lag truncation parameter $k = h - 1$ for forecast horizon $h$.
- **Empirical Finding in Phase 06b:**
  Across horizons $T+1$ through $T+30$, the DM statistic for LightGBM vs Persistence yields negative or near-zero statistics with $p < 0.01$, formally confirming that **Persistence achieves statistically superior absolute forecast precision over ML regression**.

### 2.3 Non-Parametric Paired Error Comparison: Wilcoxon Signed-Rank Test
- **Purpose:** Non-parametric alternative to paired t-test; evaluates whether the median absolute error of Model B is lower than Model A without assuming normal error distributions (crucial given agricultural heavy-tailed kurtosis).
- **Null Hypothesis ($H_0$):** The median difference in paired absolute error is zero.
- **Test Statistic:**
  $$W = \min(W^+, W^-)$$
  calculated over signed ranks of $|e_{\text{persist}, i}| - |e_{\text{ML}, i}|$.
- **Empirical Finding in Phase 06b:**
  Wilcoxon test executed across 5,000 paired samples per horizon confirms that persistence has systematically lower median error ($p < 0.0001$ across all 5 horizons).

### 2.4 Cluster Bootstrap Resampling (Accounting for Intra-Series Correlation)
- **The Problem:** Standard row-level bootstrap assumes each mandi quote is independent. In reality, observations within the same commodity-mandi series (`Kanpur__Choubepur__Wheat__Dara__FAQ`) share strong serial correlation and seasonal unobservables.
- **The Cluster Bootstrap Solution:**
  1. Define clusters as unique canonical time-series units: $\mathcal{C}_k = \{\text{District, Market, Commodity, Variety, Grade}\}$.
  2. Resample entire clusters $\mathcal{C}_k$ with replacement ($B = 500$ iterations).
  3. Recompute evaluation metrics on the reconstructed bootstrap sample.
  4. Derive empirical 95% Confidence Intervals: $[\hat{\theta}_{0.025}, \hat{\theta}_{0.975}]$.
- **Benchmark Standards (from Phase 5):**
  - Validation Macro F1 95% CI: **[0.4710, 0.5193]**.
  - Test Macro F1 95% CI: **[0.4822, 0.5242]**.
  - Storage Win Rate 95% CI: **[32.88%, 42.48%]** (Proves win rate is bounded strictly below 50% even under sampling variation).

---

## 3. Multiple Testing Correction Protocol (Controlling False Discovery Rate)

When testing multiple candidate features across multiple commodities and districts:
1. **Benjamini-Hochberg (FDR) Procedure:**
   Rank p-values $p_{(1)} \le p_{(2)} \le \dots \le p_{(m)}$. Find largest $k$ such that:
   $$p_{(k)} \le \frac{k}{m} \alpha$$
   where false discovery rate $\alpha = 0.05$.
2. **Mandatory Reporting Template:**
   Every reported model comparison in Phase 06b and beyond must present:
   - **Sample Size ($n$)**
   - **Point Estimate ($\hat{\theta}$)**
   - **Standard Error ($SE$)**
   - **Cluster Bootstrap 95% Confidence Interval**
   - **Test Statistic ($\chi^2$, $DM$, or $W$)**
   - **Unadjusted and FDR-adjusted p-value**
   - **Effect Size (Cohen's $d$ or Cramér's $V$)**
   - **Practical Operational Significance** (e.g. Does a 0.5% gain change the farmer's break-even decision?)
