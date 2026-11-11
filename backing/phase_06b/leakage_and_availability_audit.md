# Phase 06b: Comprehensive Data Leakage and Availability Audit

**Repository:** `ankit-choubey/Mandi_Prediction`  
**Phase:** 06b — Data Discovery, Validation & Mathematical Feasibility  
**Date:** October 2026  
**Auditor:** Priyanshu  
**Classification Protocol:** Four-tier audit standard (`SAFE`, `SAFE WITH LAG`, `UNSAFE`, `UNKNOWN`)

---

## 1. Executive Summary & Governing Principle

In agricultural price forecasting and economic advisory systems, data leakage is the single greatest cause of inflated, non-reproducible backtest performance. A model that achieves 90% accuracy in backtesting using data that would not have been physically or administratively available to a farmer at Date $T$ is not merely flawed—it is catastrophic if deployed in production.

### The Golden Rule of Temporal Validity:
$$\mathcal{I}_T \subset \sigma\left(\{ X_t, Y_t \}_{t \le T}\right)$$
> **"Every feature $X_{i, T}$ fed into a prediction engine generating a forecast at origin date $T$ must be physically observable, recorded, and accessible to the decision-maker prior to or at the exact time the decision must be executed."**

Any variable that requires data from $t > T$, or represents an administrative figure published retrospectively after Date $T$, is strictly prohibited unless lagged by its maximum verification delay.

---

## 2. Feature Classification Taxonomy

Every candidate variable investigated for the expanded Mandi Market Intelligence System is classified into exactly one of four audited tiers:

1. **`SAFE`**: Fully observable and administratively confirmed at or before Date $T$. Can be used directly without additional lag padding.
2. **`SAFE WITH LAG`**: Causally valid and measurable, but subject to operational, reporting, or publication latency. Must be lagged by an explicit buffer $\tau \ge 1$ calendar days.
3. **`UNSAFE`**: Physically or temporally contaminated with future information ($t > T$). Includes same-day end-of-trade totals, retrospective government revisions, un-embargoed quantiles, or realized future weather observations.
4. **`UNKNOWN`**: Availability, publication timestamp, or licensing terms cannot be verified from primary documentation. Quarantined from model training.

---

## 3. Comprehensive Feature-by-Feature Audit Matrix

| Category | Candidate Feature | Proposed Formula / Source | Operational Availability at Time $T$ | Latency / Publication Lag | Classification | Safe Implementation Rule |
|---|---|---|---|---|---|---|
| **Market** | Modal Price ($P_T$) | Current day APMC modal quote | Available at close of auction (~14:00 - 17:00 IST) | 0 to 4 hours post-trade | **SAFE** | Valid for evening next-day or $T+h$ forecasts. |
| **Market** | Min / Max Intraday Spread | $Max\_Price_T - Min\_Price_T$ | Recorded alongside modal price on trade slips | Same-day evening | **SAFE** | Valid intraday dispersion indicator at Date $T$. |
| **Market** | Exact Calendar Lags ($P_{T-1}, P_{T-3}, P_{T-7}$) | Exact date lookup: $P_{\text{Date} - k}$ | Fully archived historical records | None ($k \ge 1$ days historical) | **SAFE** | Enforce exact calendar joins with explicit `NaN` upon closures (DEC-010). |
| **Market** | Causal Moving Averages & Volatility | $\text{mean}(P_{t \le T}), \text{std}(P_{t \le T})$ | Calculated strictly over past window $t \le T$ | None (computed causally) | **SAFE** | Enforce minimum burn-in ($min\_periods \ge 3$) and zero backward-filling. |
| **Market** | Same-Day Arrival Volume ($Q_T$) | Total quantity entering mandi on Date $T$ | Gate tally completed only at market close (18:00 IST) | Intraday trading occurs *while* arrivals enter | **UNSAFE (if predicting $P_T$) / SAFE WITH LAG (for $T+h$)** | If forecasting future horizon $T+h$ ($h \ge 1$), $Q_T$ is technically known by evening. However, to support morning farmer harvest decisions at 06:00 IST, $Q_T$ is **UNSAFE**; must use **Lagged Arrival $Q_{T-1}$**. |
| **Market** | Neighboring Mandi Price Differentials | $P_{T, \text{neighbor}} - P_{T, \text{local}}$ | Published simultaneously by neighboring APMCs | Same-day evening | **SAFE** | Use only verified approved canonical neighbor mappings (DEC-009). |
| **Weather** | Realized Rainfall on Date $T$ | IMD 24-hr rainfall at Date $T$ | Measured at 08:30 IST covering 08:30 $(T-1)$ to 08:30 $(T)$ | 24-hour observation cycle | **SAFE WITH LAG** | Rainfall logged on Date $T$ reflects yesterday's rain. Must be keyed as $Rain_{T-1}$. Realized rainfall on Day $T+1$ through $T+7$ is **STRICTLY UNSAFE**. |
| **Weather** | Numerical Weather Prediction (NWP) Forecast | IMD GFS / WRF 7-day quantitative precipitation forecast | Available at 06:00 IST on Date $T$ | Real-time operational model run | **SAFE (as forecast)** | Model must consume the *historical forecast archive* produced on Date $T$, NEVER future observed weather realizations! |
| **Weather** | Daily Maximum Temperature ($T_{\max}$) | IMD surface observatory reading | Recorded at 17:30 IST on Date $T$ | Evening publication | **SAFE WITH LAG** | Must use $T_{\max, T-1}$ for early morning decision support. |
| **Weather** | Relative Humidity ($RH$) | Morning (08:30) & Evening (17:30) psychrometer | Evening publication | 12 to 24-hour reporting cycle | **SAFE WITH LAG** | Enforce 1-day lag ($RH_{T-1}$). |
| **Weather** | Extreme Weather Disruption Shock | Indicator: $Rain_{T-1} > 64.5\text{ mm}$ | Derived from 24-hr lagged IMD rain gauge | 24-hour lag | **SAFE WITH LAG** | Binary indicator: captures transport washout and yard waterlogging safely. |
| **Production** | Final District Annual Production | DES APY district production | Published 12 to 18 months after agricultural year ends | **12 to 18 months lag** | **STRICTLY UNSAFE** | Using same-crop-year final production injects massive lookahead leakage. Model would know final drought harvest total before harvest occurs! |
| **Production** | Historical Lagged Production ($Y_{t-1}$) | Production from previous agricultural year | Fully published and archived | 1 year historical | **SAFE WITH 1-YEAR LAG** | Only valid with strict 1-year lag: $\text{Crop\_Year} \le \text{Current\_Year} - 1$. (Empirically verified: marginal predictive value for 7-day price return is near zero). |
| **Production** | Quarterly Advance Estimates | DES 1st, 2nd, 3rd, 4th Advance Estimates | Released in Sep, Feb, Apr, Aug | 1 to 3 months seasonal lag | **UNSAFE / HIGH RISK** | Advance estimates undergo retrospective revisions of 10% to 30%. Using final revised historical tables creates lookahead bias. Only point-in-time snapshot tables are safe. |
| **Production** | Remote Sensing / Satellite NDVI Vegetation Index | MODIS / Sentinel-2 10-day composite NDVI | Processed and released with 3 to 5-day latency | 5-day satellite orbital processing | **SAFE WITH LAG** | Enforce minimum 7-day lag on satellite vegetation greenness indices. |
| **Calendar** | Day of Week / Month / Quarter | Gregorian calendar extraction | Deterministic astronomical calendar | None | **SAFE** | Zero leakage risk. Perfectly observable indefinitely into future. |
| **Calendar** | Indian Crop Season (*Kharif*, *Rabi*, *Zaid*) | Agronomic calendar mapping | Deterministic seasonal mapping | None | **SAFE** | Fully observable. Stratifies harvest glut from lean seasons. |
| **Calendar** | Official APMC Mandi Holiday Schedule | State Mandi Parishad gazette | Published in December of preceding calendar year | None (known 1-12 months in advance) | **SAFE** | Known ex-ante. Explains scheduled zero-volume trading hiatuses. |
| **Logistics** | Inter-Mandi Road Distance | OpenStreetMap / NHAI road network distance | Static infrastructure measurement | None | **SAFE** | Static spatial feature; zero temporal leakage. |
| **Logistics** | Daily Retail Diesel Price | PPAC / Oil Marketing Companies daily pump price | Published daily at 06:00 IST | 0 hours (pre-trading) | **SAFE** | Available prior to morning market trading. Highly reliable freight cost proxy. |
| **Logistics** | Commercial Truck Freight Spot Rates | Trucking agent spot quote | Negotiated informally in physical transport yards | Highly opaque; no centralized feed | **UNKNOWN** | **QUARANTINED**. Cannot be verified in historical time series. |
| **Logistics** | Statutory Palledari (Loading/Handling) Fee | UP Mandi Parishad statutory bye-laws | Gazette notification published annually | Fixed annual schedule | **SAFE** | Statutory cost parameter. |
| **Storage** | Published CWC Warehousing Tariff | Central Warehousing Corporation annual circular | Effective 1st April annually | None (published in advance) | **SAFE** | Valid benchmark rate for economic hurdle rate calculation. |
| **Storage** | Physiological Shrinkage Rate ($L$) | ICAR-CIPHET national loss survey monographs | Published research literature | Historical benchmark | **SAFE (as parameter)** | Static empirical parameter. Must NOT be modeled as real-time measured loss unless on-farm sensors exist. |
| **Storage** | Commercial Quality Markdown ($d_q$) | Grade discount factor on damaged produce | Realized only at Date $T+h$ post-storage auction | Future realization | **UNSAFE as feature / SAFE as scenario parameter** | $d_q$ cannot be known at Date $T$. It must enter only as an economic sensitivity scenario parameter, never an ML predictor! |
| **Economic** | Kisan Credit Card (KCC) Subvention Rate | RBI / NABARD Priority Sector Lending Circular | Statutory regulatory rate (7% p.a.) | Published in advance | **SAFE** | Fixed statutory benchmark rate for carrying cost calculation. |
| **Economic** | UP Mandi Cess & Development Cess (2.0%) | UP Krishi Utpadan Mandi Adhiniyam | Statutory state law | None | **SAFE** | Fixed statutory percentage fee. |
| **Economic** | Commission Agent (Arhatiya) Fee | Local mandi convention (1.5% - 2.5%) | Informal or statutory deductions | Highly variable | **UNKNOWN / SCENARIO ONLY** | Keep as configurable sensitivity range (1.0% to 2.5%); do not claim exact point measurement. |
| **Economic** | Minimum Support Price (MSP) | CACP / Cabinet Committee on Economic Affairs | Announced prior to sowing season | None (announced ex-ante) | **SAFE** | Known well in advance of harvest trading. Sets hard price floor for Wheat/Paddy. |

---

## 4. Deep-Dive: Specific High-Risk Leakage Traps

### 4.1 The Same-Day Arrival Volume Trap
- **The Pitfall:** In research papers, researchers frequently regress today's closing price $P_T$ against today's total arrival volume $Q_T$, reporting high $R^2$ and claiming "supply drives price."
- **The Operational Reality:** Farmers load trucks in their villages at 03:00–05:00 IST and arrive at the mandi gate by 06:00–08:00 IST. Open auctions commence at 09:00 IST. Total arrival volume $Q_T$ is not finalized by the Mandi Samiti until after trading concludes in the late afternoon.
- **The Mandatory Safeguard:** Any model advising a farmer *before* they depart their village can strictly use only **Lagged Arrivals $Q_{T-1}$** or a rolling causal average $\bar{Q}_{T-1, 7d}$. Same-day arrival $Q_T$ is **STRICTLY PROHIBITED** for harvest decision support.

### 4.2 The Government Crop Production Revision Trap
- **The Pitfall:** The Directorate of Economics and Statistics (DES) releases four "Advance Estimates" of crop production throughout the agricultural year, followed by "Final Estimates" up to 18 months later.
- **The Operational Reality:** The Final Estimate for Kharif 2024 is finalized in early 2026. If an ML model trained on 2024–2025 data uses the "Final Production" figure, it is consuming future drought or flood harvest damage statistics that were completely unknown to market participants in September 2024!
- **The Mandatory Safeguard:** If macro production data is utilized, it must be lagged by **one full agricultural year ($\ge 365$ calendar days)**.

### 4.3 The Realized Future Weather Fallacy
- **The Pitfall:** Including weather observations from Date $T+1$ through $T+7$ in a model predicting price at $T+7$.
- **The Operational Reality:** On Monday morning (Date $T$), the farmer cannot observe Thursday's actual rainfall.
- **The Mandatory Safeguard:** Future weather realizations ($t > T$) are **100% ILLEGAL**. If future weather is incorporated, it must strictly be drawn from an authenticated historical archive of Numerical Weather Prediction (NWP) 7-day probabilistic forecasts generated on Date $T$.

### 4.4 The Partition Horizon Embargo Leakage
- **The Pitfall:** Splitting time-series data chronologically (e.g. Train $\le$ 2026-01-24, Val $\ge$ 2026-01-25) without an embargo buffer.
- **The Operational Reality:** A record on origin date 2026-01-20 has its target outcome $R_7$ realized on 2026-01-27—which falls inside the Validation period! If that origin is kept in the training set, the training set observes price dynamics occurring inside the validation partition.
- **The Mandatory Safeguard:** Enforce an **8-day purged embargo buffer** at every temporal split boundary (DEC-016), purging all origins $T \in [T_{\text{split}} - 7, T_{\text{split}}]$.

---

## 5. Audit Conclusion & Compliance Certificate

1. **Clean Features Approved for Immediate Modeling (`SAFE` & `SAFE WITH LAG`):**
   - Modal, Min, Max prices at Date $T$.
   - Exact calendar historical lags ($P_{T-1}, P_{T-3}, P_{T-7}$).
   - Causal rolling moving averages, intraday spread ratios, and causal volatility ($min\_periods \ge 3$).
   - Deterministic calendar features (Month, Day of Week, Quarter, Season).
   - Spatial neighbor price spreads from approved canonical mandis.
   - 24-hour lagged IMD rainfall ($Rain_{T-1}$) and temperature ($Temp_{T-1}$).
   - Daily retail diesel prices ($Diesel_T$).
   - CWC storage tariffs, KCC interest rate (7% p.a.), statutory mandi cess (2.0%), and CACP MSP floors.
2. **Features Temporarily Prohibited / Quarantined (`UNSAFE` or `UNKNOWN`):**
   - Same-day arrival volume $Q_T$ (Must be lagged to $T-1$).
   - Current-year DES crop production statistics (Must be lagged by $\ge 1$ year).
   - Realized weather on dates $t > T$ (Prohibited).
   - Unverified truck cartel freight rates and informal moneylender interest rates (Quarantined).
