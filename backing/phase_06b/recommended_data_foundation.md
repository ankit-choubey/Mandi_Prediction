# Phase 06b: Recommended Data Foundation & Strategic Roadmap

**Repository:** `ankit-choubey/Mandi_Prediction`  
**Phase:** 06b — Data Discovery, Validation & Mathematical Feasibility  
**Date:** October 2026  
**Auditor:** Priyanshu  

---

## Executive Architecture

This document synthesizes all empirical, statistical, and operational findings from Phase 06b into a definitive data architecture and acquisition strategy. It answers the 14 mandatory foundation questions with evidence established across Phases 0 through 5 and our Phase 06b empirical benchmark suite.

---

### Question 1: What data do we already have?
- **Core APMC Dataset:** Exactly 160,192 raw daily transaction records across 5 Uttar Pradesh districts (`Ghaziabad`, `Jhansi`, `Kanpur`, `Lucknow`, `Unnao`) spanning **September 1, 2024 to September 1, 2026** (731 calendar days, 100% daily coverage statewide).
- **Cleaned Research Core (Strategy 2 / DEC-008):** 157,512 unique series-dates with commercial `Grade` preserved and 2,664 conflicting ambiguous quotes purged; 150,687 records across 1,069 active series with $\ge 20$ historical observations.
- **Audited Market Mappings (DEC-009):** Canonical mapping resolving the November 2025 APMC renaming (unifying 42 nominal market strings into 21 physical mandis; preserving Jhansi vs Jhansi Grain as separate yards).
- **Statutory Benchmarks:** CWC warehousing tariffs (FY 2025–2027), ICAR-CIPHET post-harvest loss parameters, and UP Mandi Parishad statutory cess schedules.

### Question 2: What critical data is missing?
1. **Physical Arrival Quantities ($Q_t$ in Tonnes/Quintals):** Completely omitted from current raw CSVs. Without volume data, price elasticity to supply shocks cannot be modeled.
2. **Meteorological Observations (IMD):** Daily liquid rainfall, maximum/minimum temperature, and relative humidity are not present in the workspace.
3. **Mandi-Level Freight Rates & Fuel Costs:** Realized transport costs between mandis are absent; retail diesel prices are not staged.
4. **Independent Validation Series:** Zero external comparison series from e-NAM, Agmarknet live feeds, or Department of Consumer Affairs (PMD).
5. **Accredited Warehouse Proximity (WDRA):** Distance from mandis to certified public cold storages or godowns is unmapped.

### Question 3: What should we download first?
- **Primary Immediate Acquisition:** **The CEDA Agmarknet Harmonized Archive (Ashoka University)** for Uttar Pradesh (2024–2026).
- **Secondary Immediate Acquisition:** **IMD High-Resolution Gridded Daily Rainfall (0.25° x 0.25°)** and **PPAC Daily Retail Diesel Prices**.

### Question 4: Why?
- **CEDA Agmarknet:** It is an authoritative, cleaned extraction of the exact same underlying AGMARKNET system, but crucially **includes historical daily arrival volumes (Metric Tonnes)** alongside prices. It matches our exact mandi names, dates, commodities, and varieties, enabling an immediate join to backfill physical supply volumes without schema disruption.
- **IMD 0.25° Rainfall:** Required to test whether rainfall disruption shocks explain sudden arrival drops and price spikes.
- **PPAC Diesel:** Provides an objective, daily, non-stationary proxy for road freight transport cost fluctuations between neighboring mandis.

### Question 5: What can actually be joined?
- **Arrival Volumes (CEDA):** Joinable via `District + Market + Commodity + Variety + (Date - 1 day)` (exact calendar join).
- **IMD Gridded Rainfall:** Joinable via `Mandi_Centroid (Lat/Lon) -> Nearest Grid Cell + (Date - 1 day)`.
- **PPAC Diesel Prices:** Joinable via `State (UP) + Date`.
- **CWC Tariffs & UP Mandi Fees:** Joinable via static lookup: `Commodity_Group + Financial_Year`.
- **CACP Minimum Support Price (MSP):** Joinable via `Commodity + Crop_Year`.

### Question 6: What cannot be joined?
- **District Annual Production (DES APY):** Cannot be joined to daily trading series in real time due to severe 12 to 18-month publication latency.
- **e-NAM Live Intraday Auctions:** Only ~30% of physical trade in UP mandis is cleared on e-NAM; joining would drop 70% of historical series.
- **Truck Fleet Telematics / Private Spot Freight:** Lacks standardized geographic identifiers for rural mandis and has no historical archive matching 2024–2026.
- **Informal Moneylender Interest Rates:** Cannot be joined systematically due to absence of village-level credit panels.

### Question 7: What variables are safe?
- Modal Price, Min Price, Max Price at Date $T$.
- Exact calendar historical lags ($P_{T-1}, P_{T-3}, P_{T-7}$).
- Causal rolling moving averages and causal standard deviation ($min\_periods \ge 3$, zero backward-fill).
- Deterministic calendar cycles (Month, Day of Week, Quarter, Season).
- Spatial neighbor price differentials from approved canonical mandis.
- CWC published tariffs, statutory Mandi Cess (2.0%), KCC borrowing rate (7% p.a.), and CACP MSP floors.

### Question 8: What variables require lagging?
- **Physical Arrival Volume:** Must be lagged by $\tau \ge 1$ day ($Q_{T-1}$). Same-day arrival volume $Q_T$ is finalized only after trading closes and cannot be used for morning decision support.
- **IMD Rainfall and Temperature:** Must be lagged by 24 hours ($Rain_{T-1}, Temp_{T-1}$) because IMD 24-hr rainfall is logged at 08:30 IST of Date $T$.
- **Macro Crop Production (if used):** Must be lagged by $\ge 1$ full agricultural year ($\ge 365$ days).

### Question 9: What variables create leakage?
- **Realized Future Weather:** Using observed rain/temp on days $t \in [T+1, T+h]$ instead of an ex-ante forecast generated at Date $T$.
- **Same-Day Arrival Volume ($Q_T$):** Regressing morning price against evening arrival totals.
- **Un-embargoed Rolling Quantiles:** Calculating percentile target thresholds using future data crossing partition boundaries.
- **Retrospectively Revised Advance Crop Estimates:** Consuming final revised production numbers that were revised months after harvest.

### Question 10: Which features should enter the model?
- **Core Predictive Feature Set (Model 2/3):**
  1. Spot modal price and intraday spread ratio ($Spread / Modal$).
  2. Exact calendar lags ($T-1, T-3, T-7$) with explicit `NaN` upon closures.
  3. Causal rolling moving averages ($\bar{P}_{3d}, \bar{P}_{7d}$) and causal volatility ($\sigma_{7d}$).
  4. Calendar indicators (Month, Day of Week, Season).
  5. Spatial neighbor arbitrage spread ($P_{T, \text{local}} - \bar{P}_{T, \text{neighbors}}$).
  6. 1-day lagged arrival volume ($Q_{T-1}$) and arrival anomaly z-score.
  7. 1-day lagged extreme rainfall shock indicator ($Rain_{T-1} > 64.5\text{ mm}$).
  8. Retail diesel price index.

### Question 11: Which should remain research-only?
- **Continuous Point Price Regression:** Research benchmark only; disqualified for operational deployment.
- **Fixed $\pm 5\%$ and Commodity Volatility Thresholds:** Traps $>73\%$ of data in Normal; retained only for sensitivity audits.
- **Economic Storage Policy Backtesting:** Prototype research layer; strictly quarantined from farmer recommendations until multi-month holding is validated.
- **DES Advance Production Forecasts:** Explored for macro regime shifting; excluded from daily operational inference.

### Question 12: What cannot currently be supported?
- **Farmer-Facing Sell-vs-Store Advice:** Strictly prohibited. Phase 5 and Phase 06b prove that 7-day tactical storage loses money in **62% to 93% of decisions** across major crop categories (Perishables 93.1% loss; Grains 87.3% loss).
- **Perishable Tactical Storage:** Ambient storage of tomatoes, cucumbers, and green chillies is physically and economically impossible (requires +18% price gain in 7 days).
- **Continuous Decimal Price Forecasting:** Fails out-of-sample against zero-return persistence across all 5 horizons.

### Question 13: What additional data would be required for Pan-India?
1. **National Mandi Harmonization Table:** Mapping canonical physical APMC yards across all 28 states, resolving local spelling variants and bifurcated market yards.
2. **Accredited Cold Chain Infrastructure Atlas:** Mandatory mapping of cold storages within 15 km of every mandi to determine whether storage is physically possible.
3. **Agro-Climatic Regional Clustering:** Models cannot be generalized pan-India from a single national model. The system requires localized training within India's **15 distinct Agro-Climatic Zones** (e.g. Western Himalayan, Middle Gangetic Plain, Central Plateau, etc.).
4. **State-Specific Mandi Cess and Market Regulation Profiles:** UP imposes 2% cess; Punjab imposes 3% Mandi Fee + 3% RDF (6%); other states have varying statutory deductions.

### Question 14: What should be tested next?
1. **Acquire CEDA Agmarknet UP Data:** Test Model 3 (Price + Seasonality + Spatial + Lagged Arrivals) against Model 2 to measure empirical lift in Macro F1.
2. **Quantile Tercile Target Classification:** Re-benchmark LightGBM using commodity-specific 33/33/33 tercile targets to eliminate baseline majority guessing.
3. **Multi-Month Seasonal Grain Storage Model:** Reformulate the economic storage engine from 7-day tactical holding to **60-day, 90-day, and 180-day seasonal holding** for Wheat and Paddy, testing whether seasonal harvest-to-lean price wedges clear warehouse friction.
