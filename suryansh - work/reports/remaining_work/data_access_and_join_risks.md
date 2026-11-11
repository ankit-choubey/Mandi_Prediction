# Data Access, Join Integrity, and Temporal Latency Risk Analysis

**Project:** Mandi Prediction — APMC Market Intelligence System  
**Investigator:** Suryansh  
**Workspace:** [`/Users/kumarsuryansh/Desktop/Temporary/suryansh - work`](file:///Users/kumarsuryansh/Desktop/Temporary/suryansh%20-%20work)  
**Deliverable:** `reports/remaining_work/data_access_and_join_risks.md`  
**Date:** October 23, 2026  

---

## 1. Executive Summary

Integrating external data sources introduces operational vulnerabilities that can compromise model validity through **lookahead data leakage**, **silent join dropping**, **unit conversion errors**, or **prospective unviability** (features available historically but absent during real-time deployment).

This document analyzes the specific failure modes associated with external datasets (CEDA arrival volumes, NASA POWER weather, UPAg statistics, and IMD climate grids) and establishes exact mitigation safeguards.

---

## 2. Risk Taxonomy: External Integration Failure Modes

```text
========================================================================================================================
RISK ID  FAILURE MODE                   TARGET DATA SOURCE       SEVERITY    OPERATIONAL IMPACT
========================================================================================================================
EXT-01   Unit Mismatch (Tonnes vs Qtl)  CEDA Agri-Market         HIGH        10x magnitude distortion in volume elasticity
EXT-02   Market Name Aliasing Mismatch  CEDA Agri-Market         HIGH        Silent join failure (unmatched mandi rows)
EXT-03   Publication Delay / Latency    CEDA & NASA POWER        HIGH        Lookahead leakage if unlagged at date T
EXT-04   Institutional Auth Barrier     UPAg Agricultural Portal CRITICAL    Pipeline break; non-reproducible external auth
EXT-05   Annual Release Latency         IMD Gridded Climate      HIGH        Unviable for daily prospective inference
EXT-06   Zero-Arrival Ambiguity         CEDA Agri-Market         MEDIUM      Confounding true zero trade with missing data
EXT-07   Spatial Disaggregation Defect  NASA POWER Weather       MEDIUM      50km grid smoothing over localized rain events
========================================================================================================================
```

---

## 3. In-Depth Failure Mode Analysis & Engineering Safeguards

### Risk EXT-01: Unit Mismatch (Tonnes vs. Quintals in Arrival Data)
- **Mechanism:** In Indian agricultural statistics, state marketing boards alternate between recording arrivals in Metric Tonnes ($1\text{ MT} = 1,000\text{ kg}$) and Quintals ($1\text{ Qtl} = 100\text{ kg} = 0.1\text{ MT}$). While AGMARKNET specifies quintals in primary manuals, regional data pipelines frequently aggregate into tonnes.
- **Vulnerability:** Merging raw arrival figures without unit verification creates a $10\times$ order-of-magnitude error, distorting rolling volume averages and price-volume cross-elasticity features.
- **Mitigation Safeguard:**
  1. Calculate the empirical arrival-to-value distribution per commodity and compare median daily quantities against historical district production.
  2. Implement an automated unit assertion gate in the ingestion pipeline:
     ```python
     # Unit verification assertion
     assert df['Arrival_Quantity'].median() > 0, "Arrival quantity cannot be non-positive"
     if reported_unit.lower() == 'tonnes' or reported_unit.lower() == 'mt':
         df['Arrival_Quantity_Qtl'] = df['Arrival_Quantity'] * 10.0
     elif reported_unit.lower() == 'quintal' or reported_unit.lower() == 'qtl':
         df['Arrival_Quantity_Qtl'] = df['Arrival_Quantity']
     ```

---

### Risk EXT-02: Market Yard Name Aliasing & String Discontinuity
- **Mechanism:** Agmarknet market names suffer from spelling variations, administrative district reassignments, and nominal suffixes (e.g. `Lucknow` vs. `Lucknow APMC` vs. `Lucknow (Grain)`). CEDA maintains a normalized market dimension table that may not match raw local CSV string tokens.
- **Vulnerability:** Standard inner merges on raw `Market` strings result in catastrophic row dropping (often >40% unmatched rows), biasing the training sample toward standardized urban hubs and dropping rural mandis.
- **Mitigation Safeguard:**
  1. Construct an explicit, audited two-way mapping dictionary between `Mandi_Prediction.Market` and `CEDA.market_name`.
  2. Perform left joins and enforce an **empirical join-rate threshold assertion ($\ge 95.0\%$)**:
     ```python
     match_rate = joined['Arrival_Quantity_Qtl'].notna().mean() * 100
     if match_rate < 95.0:
         raise ValueError(f"Unacceptable join match rate: {match_rate:.2f}% < 95.0%")
     ```
  3. Where an individual sub-yard is missing, impute from the district-level commodity aggregate volume.

---

### Risk EXT-03: Publication Delay & Temporal Lookahead Leakage
- **Mechanism:** Wholesale transactions occur between 06:00 and 15:00 IST. Market secretaries upload price and arrival data to AGMARKNET between 17:00 and 22:00 IST. External aggregators (CEDA, NASA POWER) ingest, validate, and publish records with an additional 12 to 48 hours of latency.
- **Vulnerability:** If an inference pipeline running at 09:00 IST on date $T$ uses arrival volume or weather labeled date $T$, it is ingesting future information that had not yet cleared the market at that morning timestamp (lookahead target leakage).
- **Mitigation Safeguard:**
  1. Strictly enforce **lagged ingestion** for all external signals:
     $$\text{Arrival Volume Feature at Date } T = \text{Arrival Quantity}_{T-1}$$
     $$\text{Weather Signals at Date } T = \text{NASA POWER Precipitation & Temp}_{T-3} \text{ (or } T-2\text{)}$$
  2. Under retrospective backtesting, all features are indexed by transaction date $T$, ensuring no timestamp realization exceeds date $T$.

---

### Risk EXT-04: Institutional Authentication Barrier (UPAg Portal)
- **Mechanism:** The UPAg API (`data.upag.gov.in`) requires OAuth2/JWT password credentials (`POST /v1/upag/api-data-share/login`) issued only to authorized government and institutional researchers.
- **Vulnerability:** Building a pipeline dependent on private login credentials violates the core requirement for **independent, open-source scientific reproducibility**. If third-party credentials expire or are unavailable, the codebase cannot be executed.
- **Mitigation Safeguard:**
  1. Exclude UPAg API calls from the active daily prediction pipeline.
  2. Retain publicly available, open-license annual APY statistics from data.gov.in as static macro-economic reference tables if needed.

---

### Risk EXT-05: Annual Release Latency (IMD Gridded Climate Data)
- **Mechanism:** While IMD provides the gold-standard $0.25^\circ \times 0.25^\circ$ gridded rainfall data, files are published in annual retrospective archive batches (e.g., year 2024 published in mid-2025; year 2025 published in 2026).
- **Vulnerability:** An operational forecasting model cannot query IMD gridded data prospectively on day $T$. Any model dependent on IMD gridded arrays would be dead on arrival in production.
- **Mitigation Safeguard:**
  1. Designate IMD gridded NetCDF files strictly for historical climatological backtesting and baseline validation.
  2. Use NASA POWER or open meteorological APIs (e.g. Open-Meteo) for daily continuous inference features.

---

### Risk EXT-06: Zero-Arrival Ambiguity (Absence of Trade vs. Reporting Hiatus)
- **Mechanism:** When a mandi operates on a given date but records 0 arrivals for a commodity, does this represent a supply drought (zero harvest brought to market) or a clerical non-reporting omission?
- **Vulnerability:** Treating missing arrival cells as `0.0` quintals creates false extreme supply shocks that trigger erratic model predictions. Conversely, dropping the row discards valid price signals.
- **Mitigation Safeguard:**
  1. Track active market status: If the mandi reported arrivals for *other* commodities on date $T$, commodity arrival is classified as a genuine supply pause ($0.0\text{ Qtl}$).
  2. If the entire mandi reported 0 transactions across all commodities (e.g. Sunday or festival closure), arrival is assigned `NaN` and handled via causal median imputation inside the Pipeline.

---

## 4. Proposed Smallest Next Step to Obtain Evidence Safely

To obtain concrete empirical evidence without violating project rules (no unauthorized API calls, no account creation, no massive file downloads), we propose the following **minimal, non-invasive next step**:

1. **Phase 1 Probe (Local Mock & Static Documentation Verification):**
   - Test CEDA and NASA POWER response formats using public documentation schemas and isolated Python mock scripts in `experiments/`.
2. **Phase 2 Acquisition Request (Subject to User Approval at Checkpoint 1):**
   - Request explicit user approval to query the **NASA POWER public REST API** for exactly **5 district centroid coordinate points** over the historical date range (September 01, 2024 to September 01, 2026).
   - Expected payload: $\sim 5 \times 731$ rows $= 3,655$ daily weather rows ($< 2\text{ MB}$ total download).
   - Runtime: $< 15\text{ seconds}$ on standard broadband; zero API keys required.
