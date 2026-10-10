# Phase 5: Commodity, Market, and District Heterogeneity Audit

**Project:** Mandi_Prediction
**Repository:** `ankit-choubey/Mandi_Prediction`
**Phase:** 5 — Robustness, Statistical Uncertainty, and Generalization Audit
**Date:** October 10, 2026
**Artifact:** `backing/phase_05/commodity_market_heterogeneity.md`
**Underlying Data:** `backing/phase_05/outputs/subgroup_heterogeneity.csv`

---

## 1. Subgroup Sample Size Rule and Methodological Safeguards

To prevent over-interpreting noisy, small-sample anomalies:
1. **Minimum Sample Size Threshold:** A subgroup is evaluated only if it contains at least **$N \ge 250$ eligible decisions** in the evaluated partition.
2. **Denominators:**
   - $\text{Eligible Decisions} (N)$: Total trading days meeting exact calendar $T+7$ match requirements.
   - $\text{Times Stored} (N_{\text{stored}})$: Decisions where the model predicted `Favorable` (Class 2).
   - $\text{Storage Win Rate (\%)} = \frac{\sum \mathbf{1}(\Delta r_k > 0)}{N_{\text{stored}}} \times 100\%$.
   - $\text{Mean Return (₹/eligible qtl)} = \frac{1}{N} \sum (d_k \Delta r_k)$.
   - $\text{Mean Return (₹/stored qtl)} = \frac{1}{N_{\text{stored}}} \sum_{k: d_k=1} \Delta r_k$.
3. **Multiple Testing Safeguard:** Testing across 10 commodities, 5 districts, and 17 major mandis introduces substantial multiple-comparison risk. Differences reported below represent observed sample heterogeneity and must not be interpreted as causal or universally persistent commodity traits.
4. **Physical Reality Caveat:** Historical APMC price fluctuations cannot be used to infer physical warehouse access, cold storage availability, or post-harvest durability in rural Uttar Pradesh.

---

## 2. Commodity-Level Heterogeneity (Central Scenario, Exploratory Test)

Evaluated on the Exploratory Test Partition ($n = 9,551$, May 09 – Aug 25, 2026):

| Commodity | Eligible Decisions ($N$) | Times Stored ($N_{\text{stored}}$) | % Stored | Storage Win Rate (%) | Mean Return (₹/eligible qtl) | Mean Return (₹/stored qtl) | 5th Percentile Stored (₹/qtl) |
|---|---|---|---|---|---|---|---|
| **Wheat** | 2,424 | 13 | 0.54% | **15.38%** | **-₹0.22** | **-₹40.39** | -₹189.07 |
| **Potato** | 572 | 229 | 40.03% | **20.52%** | **+₹5.66** | +₹14.14 | -₹106.98 |
| **Tomato** | 342 | 102 | 29.82% | **35.29%** | **-₹3.14** | **-₹10.54** | -₹337.13 |
| **Onion** | 380 | 114 | 30.00% | **55.26%** | **+₹46.47** | +₹154.89 | -₹234.57 |
| **Rice** | 374 | 94 | 25.13% | **55.32%** | **+₹148.81** | +₹592.06 | -₹658.71 |
| **Paddy(Common)** | 391 | 91 | 23.27% | 51.65% | +₹32.25 | +₹138.58 | -₹502.24 |
| **Green Chilli** | 266 | 23 | 8.65% | 30.43% | +₹20.87 | +₹241.42 | -₹230.00 |
| **Lemon** | 260 | 11 | 4.23% | 45.45% | +₹6.50 | +₹153.57 | -₹568.01 |
| **Firewood** | 615 | 313 | 50.89% | 30.67% | **-₹2.82** | **-₹5.53** | -₹88.98 |

### Key Commodity Takeaways:
1. **Cereals (Wheat):** Storing wheat for 7 calendar days produces negative incremental return (-₹0.22/qtl eligible, -₹40.39/stored qtl) with a catastrophic **15.4% win rate**. Weekly cereal price movements are too narrow to overcome the ₹20/qtl storage and 1% physical shrinkage hurdle.
2. **Perishables (Tomato):** Storing tomatoes yields a net financial loss (-₹3.14/qtl eligible, -₹10.54/stored qtl) with a **35.3% win rate**. Ambient holding of tomatoes without climate-controlled cold storage risks physical spoilage far exceeding modeled thresholds.
3. **Semi-Perishables (Onion, Rice):** Both achieve win rates slightly above 50% (55.3%) and positive average returns (+₹46.47 and +₹148.81/qtl). However, tail risk is acute: stored Rice losses at the 5th percentile reach **-₹658.71/qtl**.

---

## 3. Market and District Heterogeneity

### 3.1 District Performance Summary (Exploratory Test)
| District | Eligible Decisions ($N$) | Times Stored ($N_{\text{stored}}$) | Win Rate (%) | Mean Return (₹/eligible qtl) | Mean Return (₹/stored qtl) |
|---|---|---|---|---|---|
| **Ghaziabad** | 1,720 | 336 (19.53%) | 52.68% | +₹99.62 | +₹509.94 |
| **Lucknow** | 1,651 | 351 (21.26%) | 37.61% | +₹84.76 | +₹398.67 |
| **Kanpur** | 2,368 | 403 (17.02%) | 28.78% | +₹32.21 | +₹189.29 |
| **Jhansi** | 2,311 | 289 (12.51%) | 34.26% | +₹6.19 | +₹49.53 |
| **Unnao** | 1,501 | 491 (32.71%) | 37.27% | **+₹0.87** | +₹2.66 |

### 3.2 Individual Mandis With Negative Policy Returns
Across the 17 individual APMC yards meeting the $N \ge 250$ threshold, **five mandis generated negative net returns under the model policy**:
1. **Uttaripura APMC ($N = 409$):** 131 stored, **20.61% win rate**, **-₹8.86 / eligible qtl** (-₹27.65 / stored qtl).
2. **Choubepur APMC ($N = 334$):** 80 stored, **22.50% win rate**, **-₹6.16 / eligible qtl** (-₹25.73 / stored qtl).
3. **Gurusarai APMC ($N = 341$):** 27 stored, **14.81% win rate**, **-₹3.10 / eligible qtl** (-₹39.11 / stored qtl).
4. **Purwa APMC ($N = 325$):** 141 stored, **39.72% win rate**, **-₹1.40 / eligible qtl** (-₹3.24 / stored qtl).
5. **Mauranipur APMC ($N = 471$):** 103 stored, **20.39% win rate**, **-₹1.38 / eligible qtl** (-₹6.30 / stored qtl).

In contrast, high-volume peri-urban consuming markets (**Ghaziabad APMC: +₹169.03/eligible qtl**, **Lucknow APMC: +₹92.92/eligible qtl**) drive the majority of the aggregate positive returns.

---

## 4. Synthesis and Governance Implication

The policy's performance is deeply fragmented across commodities and geographies. Deploying a single statewide decision-support policy would expose producers of Wheat, Tomatoes, and farmers trading in rural secondary yards (e.g., Uttaripura, Gurusarai, Mauranipur) to persistent losses and failure rates exceeding 75%–85%.
