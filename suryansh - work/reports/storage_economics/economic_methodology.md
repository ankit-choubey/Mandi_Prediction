# Rigorous Storage Economics Methodology & Decision-Theoretic Framework

**Project:** Mandi Prediction — APMC Market Intelligence System  
**Investigator:** Suryansh  
**Scope:** Potato and Onion Only *(Tomato strictly excluded; Wheat storage excluded)*  
**Workspace:** [`/Users/kumarsuryansh/Desktop/Temporary/suryansh - work`](file:///Users/kumarsuryansh/Desktop/Temporary/suryansh%20-%20work)  
**Deliverable:** `reports/storage_economics/economic_methodology.md`  
**Date:** October 23, 2026  

---

## 1. Fundamental Principle: Why Price Rise $\ne$ Storage Profit

In agricultural commodity analytics, an increase in future wholesale price ($\text{Modal\_Price}_{T+7} > \text{Modal\_Price}_T$) is frequently conflated with a profitable storage recommendation. This is an economic fallacy.

Storing perishable or semi-perishable produce incurs:
1. **Physical Quantity Decay (Shrinkage & Spoilage):** A farmer storing 100 quintals at date $T$ does not have 100 quintals to sell at date $T+7$; moisture loss, rotting, and handling cull reduce physical volume.
2. **Quality Deterioration & Grade Discount:** Produce stored under non-ideal humidity or ambient conditions degrades from Grade `A` or `FAQ` to `Medium` or `Grade C`, fetching a lower market price.
3. **Direct Out-of-Pocket Holding Costs:** Storage fees, loading/unloading labor, handling, fumigation, and APMC mandi user charges.
4. **Opportunity Cost of Capital:** Capital locked up in stored inventory cannot earn short-term interest or settle seasonal farmer debts.

Therefore, an economic holding advisory (`Favorable`) is justified **if and only if** the net realizable proceeds at $T+7$ strictly exceed the immediate spot liquidation proceeds at date $T$.

---

## 2. Mathematical Formulation: Net Incremental Holding Value

To compare the two commercial alternatives on a mathematically consistent physical quantity ($Q_0$) and currency (₹) basis:

### Alternative A: Immediate Spot Sale at Date $T$
The gross proceeds from selling initial quantity $Q_0$ (Quintals) immediately at the mandi gate:

$$\Pi_{\text{Immediate}}(T) = Q_0 \times P_T \times (1 - \tau_{\text{mandi}}) - C_{\text{unload}}$$

Where:
- $Q_0$: Harvest volume brought to market (standardized to $100\text{ Quintals}$).
- $P_T$: Modal clearing price at date $T$ (₹/Quintal).
- $\tau_{\text{mandi}}$: Mandi transaction levy and market fee (typically $1.5\% \text{ to } 2.5\%$).
- $C_{\text{unload}}$: Labor charge for unloading at the auction floor (₹/Quintal).

---

### Alternative B: Hold Produce and Sell at Date $T+H$ (Horizon $H = 7$ Calendar Days)
If the farmer decides to store the produce for $H$ days and sell at date $T+H$:

#### Step 1: Physical Quantity Remaining After Spoilage & Shrinkage
Produce experiences physiological moisture weight loss and fungal decay:

$$Q_{T+H} = Q_0 \times (1 - L_{\text{physical}}(H))$$

Where $L_{\text{physical}}(H)$ is the fractional physical loss over duration $H$ based on ICAR-CIPHET empirical benchmark rates:
- **Potato (Cold Store):** $L_{\text{physical}}(7\text{ days}) \approx 0.5\% \text{ to } 0.8\%$ (chilled, high-humidity environment).
- **Onion (Ventilated Structure / Chawl):** $L_{\text{physical}}(7\text{ days}) \approx 1.5\% \text{ to } 2.5\%$ (ambient respiratory transpiration).
- **Tomato (Uncontrolled Ambient):** $L_{\text{physical}}(7\text{ days}) \approx 12.4\%$ (catastrophic liquefaction decay; hence storage strictly prohibited).

#### Step 2: Quality-Adjusted Realizable Future Price
Produce may suffer cosmetic or firmness degradation during holding:

$$P_{T+H}^{\text{realized}} = P_{T+H} \times (1 - \delta_{\text{grade}})$$

Where $\delta_{\text{grade}}$ is the quality markdown discount ($0.00$ for sound cold-stored tubers; $0.02 \text{ to } 0.05$ for ambient bulb sprouting).

#### Step 3: Total Incremental Holding & Storage Costs
The explicit out-of-pocket holding expenses over duration $H$:

$$C_{\text{holding}}(H) = Q_0 \times \left[ C_{\text{storage}}(H) + C_{\text{handling}} + C_{\text{transport}} \right] + \text{Cost of Capital}$$

Where:
- $C_{\text{storage}}(H)$: Official CWC or cold store tariff for duration $H$ (₹/Quintal).
  - CWC UP warehouse tariff: ₹17.29 to ₹20.00 per quintal per 7-day period.
- $C_{\text{handling}}$: Double-handling labor (loading into storage, stacking, unloading).
- $C_{\text{transport}}$: Local haulage from mandi to storage facility and back (if not co-located).
- $\text{Cost of Capital}$: $Q_0 \times P_T \times \left( \frac{r_{\text{annual}}}{365} \times H \right)$, where $r_{\text{annual}} \approx 12\%$ per annum agricultural credit rate.

#### Step 4: Gross Realizable Future Proceeds
$$\Pi_{\text{Holding}}(T+H) = Q_{T+H} \times P_{T+H}^{\text{realized}} \times (1 - \tau_{\text{mandi}}) - C_{\text{holding}}(H)$$

---

### Step 5: Net Incremental Holding Value ($\Delta \Pi$)

The decision criterion is the net monetary gain (or loss) per initial quintal:

$$\Delta \Pi = \frac{\Pi_{\text{Holding}}(T+H) - \Pi_{\text{Immediate}}(T)}{Q_0} \quad (₹/\text{Quintal})$$

$$\Delta \Pi = \left[ (1 - L_{\text{physical}}) \times P_{T+H}^{\text{realized}} - P_T \right] \times (1 - \tau_{\text{mandi}}) - \left[ C_{\text{storage}} + C_{\text{handling}} + C_{\text{transport}} + \text{Capital Cost} \right]$$

### The Decision Rule:
- If $\Delta \Pi > 0$: **HOLD Produce (Economically Profitable)**.
- If $\Delta \Pi \le 0$: **SELL Immediately (Holding Results in Net Financial Loss)**.

---

## 3. Crop-Specific Storage Architectures

### 1. Potato (Solanum tuberosum) — Cold Storage Dependent
- **Storage Biology:** Semi-perishable tuber with dormancy. Requires low-temperature chilled storage ($2^\circ\text{C} \text{ to } 4^\circ\text{C}$, $90\% \text{ to } 95\%$ relative humidity) to prevent sprouting, rot, and solanine accumulation.
- **Commercial Context in UP:** Uttar Pradesh is India's largest potato producer (Agra-Aligarh-Kanpur belt). Mandis are surrounded by private cold storages. Storage fees are historically structured seasonally (March to October/November) at state-regulated caps (~₹120–₹160 per 50 kg bag, translating to ~₹24–₹32/qtl per month).
- **Short-Term (7-Day) Reality:** Cold stores do not accept 7-day micro-deposits; potato storage is traditionally seasonal. Short-term 7-day holding at the farm gate under ambient shade suffers rapid rotting during summer (April–June).

### 2. Onion (Allium cepa) — Ventilated Storage (Kanda Chawl)
- **Storage Biology:** Bulb with natural dry outer scales. Requires low humidity ($65\% \text{ to } 70\%$) and active ambient air ventilation. Chilling in cold stores causes severe condensation spoilage upon exit.
- **Commercial Context:** Stored in traditional on-farm ventilated structures (*Chawl*) or specialized dry godowns. 7-day short-term holding is commercially common and operational.
- **Historical Backtest Result (Phase 5):** **55.26% Storage Win Rate**; average net profit **+₹154.89 / quintal**. Onion is the most economically viable crop for dynamic holding advisories.

### 3. Tomato (Solanum lycopersicum) — STRICTLY EXCLUDED
- **Perishability:** Extreme climacteric fruit; shelf-life 3 to 7 days under tropical ambient temperatures.
- **Loss Benchmark:** ICAR-CIPHET documents 12.44% loss rate; holding for 7 days without continuous cold chain leads to 30%–50% product destruction.
- **Methodological Prohibition:** In accordance with Section 2 and Section 7 of the Master Prompt, **no storage recommendations or economic returns will be calculated for Tomato**.

---

## 4. Retrospective Historical Audit vs. Prospective Decision Rule

- **Retrospective Comparison:** Uses historical realized future prices ($P_{T+7}$) from the dataset to calculate what the farmer *would have earned*.
- **Prospective Decision Rule:** Operates at date $T$ using the model's **predicted class probabilities** $\hat{P}(\text{Fav} \mid x_T)$:
  $$\mathbb{E}[\Delta \Pi \mid x_T] = \sum_{c \in \{0, 1, 2\}} P(y = c \mid x_T) \times \Delta \Pi(c)$$
  A holding advisory is triggered only when expected gain exceeds a risk-adjusted hurdle threshold.
