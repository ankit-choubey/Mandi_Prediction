# Evidence-Based Crop Suitability Assessment Report

**Project:** APMC Mandi Market Intelligence System  
**Investigator:** Suryansh  
**Phase:** 02 — Evidence-Based Crop Suitability Assessment  
**Reference Codebase:** [`/Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction`](file:///Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction) (Read-only on `main`)  
**Workspace:** [`/Users/kumarsuryansh/Desktop/Temporary/suryansh - work`](file:///Users/kumarsuryansh/Desktop/Temporary/suryansh%20-%20work)  
**Date:** October 23, 2026  

---

## 1. Executive Summary

This investigation evaluates the empirical suitability of four candidate crops—**Potato**, **Onion**, **Tomato**, and **Wheat**—for the next phase of agricultural market condition classification and decision-support modeling across Uttar Pradesh wholesale mandis. 

Using non-destructive, reproducible data profiling of 160,192 raw records from five key districts (Ghaziabad, Jhansi, Kanpur, Lucknow, and Unnao) spanning September 1, 2024 to September 1, 2026, alongside verifiable external evidence from data.gov.in, CEDA Agri-Market, NASA POWER, ICAR-CIPHET, and CWC, this report establishes:

1. **Onion is the most promising candidate:** It exhibits the most balanced multi-class distribution in the dataset (**Normal: 44.4%**, **Unfavorable: 33.1%**, **Favorable: 22.5%**), low price stickiness (10.8% zero returns), strong $T+7$ continuity (78.6% availability, 6,071 pairs), and demonstrated positive economic storage returns (+₹46.47/qtl) with a 55.3% win rate in historical test data.
2. **Potato is a strong secondary candidate:** It demonstrates the highest exact calendar $T+7$ availability (**79.5%**, 6,372 pairs), low variety fragmentation (71.2% Desi), and moderate class balance (55.2% Normal, 28.3% Unfavorable, 16.5% Favorable). Economic holding is viable but strictly contingent on regional cold-storage logistics.
3. **Tomato exhibits dynamic classification breakouts but severe post-harvest perishability:** Characterized by high volatility ($\sigma = 19.18\%$) where Unfavorable (41.1%) and Favorable (33.6%) both outnumber Normal (25.3%). However, holding ambient fresh tomatoes for 7 days incurs extreme physical spoilage (12.44% loss per ICAR-CIPHET) and negative net economic returns (-₹3.14/qtl).
4. **Wheat is fundamentally defective under fixed $\pm 2.5\%$ classification thresholds:** Despite high record volume (11,727 clean rows), government MSP support and price stickiness cause **87.13% of all observations to fall into the Normal class**, starving minority classes (Favorable 6.5%, Unfavorable 6.3%). Any naive majority baseline achieves 87.1% accuracy without learning. Weekly price movements rarely overcome ₹20/qtl storage and handling hurdles (15.4% win rate).

**Core Recommendation:** Focus the next research phase on a **two-crop portfolio: Onion and Potato**, balancing high data continuity, genuine multi-class discriminative power, and post-harvest holding feasibility.

---

## 2. Research Questions and Methodology

### 2.1 Core Research Questions
1. **Continuity & Coverage:** Which candidate crops possess sufficient consecutive-day continuity and exact calendar $T+7$ target pairs across the five Uttar Pradesh districts?
2. **Label Distribution & Stickiness:** How does the existing 3-class target rule (DEC-015: Favorable $> +2.5\%$, Normal $[-2.5\%, +2.5\%]$, Unfavorable $< -2.5\%$) distribute across each crop? Does wholesale quote stickiness cause pathological majority-class dominance?
3. **Supply & Environmental Feature Feasibility:** Can missing supply variables (arrivals) and agroclimatological factors (rainfall, temperature) be reliably sourced from accessible, low-latency external databases?
4. **Post-Harvest Feasibility:** Can a 7-day holding recommendation be operationalized without triggering catastrophic physical spoilage or financial loss?

### 2.2 Profiling Methodology
All data profiling was executed via a standalone script ([`experiments/profile_candidate_crops.py`](file:///Users/kumarsuryansh/Desktop/Temporary/suryansh%20-%20work/experiments/profile_candidate_crops.py)) operating strictly on the original raw files. It adheres to audited project decisions:
- Preserving commercial `Grade` in the canonical series key: `(District, Market, Commodity, Variety, Grade)`.
- Applying Strategy 2 (DEC-008) to exclude ambiguous same-grade conflicting quotes (eliminating 66 Potato, 64 Onion, 65 Tomato, and 342 Wheat conflicting records).
- Enforcing exact calendar joins for $T+7$ target matching with zero row-shift substitutions.
- Partitioning chronologically with 8-day embargo buffer purging.

---

## 3. Existing Project Data Findings

### 3.1 Empirical Crop Metrics Comparison

| Feature / Dimension | Potato | Onion | Tomato | Wheat |
|---|---|---|---|---|
| **Raw Records Ingested** | 8,084 | 7,792 | 7,585 | 12,070 |
| **Clean Deduplicated Records** | **8,017** | **7,728** | **7,520** | **11,727** |
| **Canonical Series Units** | 91 | 82 | 101 | 211 |
| **Unique Mandis / Markets** | 35 | 36 | 35 | 39 |
| **Districts Represented** | 5 (All) | 5 (All) | 5 (All) | 5 (All) |
| **Unique Dates (out of 731)** | 710 | 704 | 712 | 731 |
| **Consecutive 1-Day Gaps (%)** | 82.56% | 81.87% | 80.90% | 72.26% |
| **Median Reporting Gap** | 1.0 day | 1.0 day | 1.0 day | 1.0 day |
| **Mean Modal Price (₹/qtl)** | ₹1,255.72 | ₹2,040.78 | ₹2,065.74 | ₹2,542.80 |
| **Median Modal Price (₹/qtl)** | ₹1,155.00 | ₹1,470.00 | ₹2,000.00 | ₹2,522.00 |
| **Modal Price Std Dev (₹/qtl)** | ₹495.74 | ₹1,026.99 | ₹1,197.32 | ₹157.09 |
| **Mean Intraday Spread Ratio (%)** | 9.03% | 7.39% | 8.13% | 2.06% |
| **Exact Calendar T+7 Matched Pairs** | **6,372** | **6,071** | **5,741** | **8,351** |
| **Exact T+7 Availability (%)** | **79.48%** | **78.56%** | **76.34%** | **71.21%** |
| **7-Day Return Volatility ($\sigma$)** | 10.47% | 10.37% | **19.18%** | 10.07% |
| **Exact 0.00% Return Share (%)** | 19.43% | 10.76% | 8.95% | **29.80%** |
| **DEC-015 Normal Class Share (%)** | **55.24%** | **44.39%** | **25.26%** | **87.13%** |
| **DEC-015 Favorable Class Share (%)** | 16.46% | 22.53% | 33.62% | 6.54% |
| **DEC-015 Unfavorable Class Share (%)** | 28.30% | 33.08% | 41.13% | 6.33% |
| **Exploratory Test Sample Count** | 719 | 481 | 415 | 3,209 |
| **Test Set Class Split (Normal/Fav/Unfav)**| 554 / 95 / 70 | 236 / 178 / 67 | 235 / 98 / 82 | 2,770 / 255 / 184 |

### 3.2 Data Quality and Schema Verification
- **Zero Nulls:** All raw data files contain 0.00% missing values across all 11 columns.
- **Price Ordering Rule:** $Min \le Modal \le Max$ holds for 99.996% of rows. Exactly 2 non-compliant rows (1 Potato, 1 Wheat) caused by `Max_Price = 0.0` were safely purged.
- **Arrival Volumes:** **Confirmed absent** in all 5 raw dataset files.
- **Weather Features:** **Confirmed absent** in all existing files and modules.

---

## 4. External Data Source Findings & Citations

To address missing arrivals and environmental features, five external data sources were audited:

### 4.1 AGMARKNET via Open Government Data (data.gov.in)
- **Organization:** Ministry of Agriculture and Farmers Welfare / NIC.
- **Resource Identifier:** Resource UUID `9ef84268-d588-465a-a308-a864a43d0070`.
- **Verified Status:** Accessible via REST API using a standard API key.
- **Findings:** The standard API layout mirrors the existing dataset (`state`, `district`, `market`, `commodity`, `variety`, `grade`, `arrival_date`, `min_price`, `max_price`, `modal_price`). Arrival volumes are not provided in this core price resource, confirming that our local files represent the standard AGMARKNET price layout.

### 4.2 CEDA Agri-Market Data Portal (Ashoka University)
- **Organization:** Centre for Economic Data and Analysis (CEDA), Ashoka University.
- **Portal URL:** [`https://agmarknet.ceda.ashoka.edu.in/`](https://agmarknet.ceda.ashoka.edu.in/)
- **API Documentation:** [`https://api.ceda.ashoka.edu.in/documentation/`](https://api.ceda.ashoka.edu.in/documentation/) (Swagger UI) & [`https://api.ceda.ashoka.edu.in/`](https://api.ceda.ashoka.edu.in/)
- **Verified Status:** Fully accessible via interactive web portal and programmatic REST API (`https://api.ceda.ashoka.edu.in/v1`).
- **Endpoints & Schemas:**
  - `POST /agmarknet/prices`: Retrieves modal, min, and max prices.
  - `POST /agmarknet/quantities`: **Retrieves quantity arrivals** (volumes in tonnes/quintals) structured by mandi, commodity, and date.
  - Helper lookups: `GET /agmarknet/commodities`, `GET /agmarknet/geographies`, `POST /agmarknet/markets`.
- **Scope & Relevance:** Covers 300+ commodities across 2,700+ mandis from 2000 to present. Directly provides the missing arrival quantities for our candidate crops (Potato, Onion, Tomato, Wheat). Join keys align on `(District, Market, Commodity, Arrival_Date)`.
- **Terms:** Free for academic and non-commercial research with mandatory attribution (*"CEDA Agri-Market Data, Ashoka University"*).

### 4.3 India Meteorological Department (IMD) Gridded Weather Data
- **Organization:** India Meteorological Department, Ministry of Earth Sciences.
- **Portal URLs:** [`https://www.imdpune.gov.in/cmpg/Griddata/Rainfall_1_NetCDF.html`](https://www.imdpune.gov.in/cmpg/Griddata/Rainfall_1_NetCDF.html) & [`https://imdweb.lwcc.in/`](https://imdweb.lwcc.in/)
- **Verified Status:** Accessible via IMD Pune Climate Monitoring & Prediction Group.
- **Specifications:**
  - Spatial resolution: $0.25^\circ \times 0.25^\circ$ (~$27.5\text{ km} \times 27.5\text{ km}$) gridded matrix ($135 \times 129$ points covering mainland India).
  - Format: Annual NetCDF (`.nc`) files containing daily rainfall layers (1901 to 2024).
  - Join protocol: Mandi geographical coordinates must be mapped to the nearest grid centroid.
- **Operational Limitation:** NetCDF archives are released in annual retrospective batches. The lack of an open, sub-daily REST API prevents real-time feature extraction at prediction time $T$; however, it is highly suitable for historical retrospective model validation.

### 4.4 UPAg — Unified Portal for Agricultural Statistics
- **Organization:** Directorate of Economics & Statistics, Ministry of Agriculture & Farmers Welfare.
- **Portal URL:** [`https://upag.gov.in/`](https://upag.gov.in/)
- **Reports:** [`https://upag.gov.in/primary-estimate-report`](https://upag.gov.in/primary-estimate-report)
- **API Documentation:** [`https://data.upag.gov.in/docs`](https://data.upag.gov.in/docs) (OpenAPI / ReDoc)
- **Verified Status:** Documentation verified. API access requires institutional authentication (`POST /v1/upag/api-data-share/login` using registered `userid` and `password`).
- **Variables & Granularity:** Area, Production, Yield (APY), and advance/primary crop estimates at state and district level.
- **Relevance:** Useful for macro supply-side context (e.g., district-level annual crop output), but annual/seasonal reporting frequency is too coarse to serve as a daily $T+7$ price prediction feature.

### 4.5 NASA POWER Agroclimatology API (Complementary Weather Source)
- **Organization:** NASA Langley Research Center.
- **API Endpoint:** [`https://power.larc.nasa.gov/api/temporal/daily/point`](https://power.larc.nasa.gov/api/temporal/daily/point)
- **Verified Status:** Fully open public REST API; zero API key or login credentials required.
- **Parameters:** `PRECTOTCORR` (daily precipitation), `T2M`, `T2M_MAX`, `T2M_MIN` (temperature), `RH2M` (relative humidity) at point mandi coordinates.
- **Advantage:** Open programmatic REST interface with near-real-time updates (2–4 days MERRA-2 latency), complementing IMD's annual NetCDF archives.

### 4.6 Additional Research Resources Surveyed
1. **Variety-Wise Daily Market Prices (data.gov.in):** [`https://data.gov.in/resource/variety-wise-daily-market-prices-data-commodity`](https://data.gov.in/resource/variety-wise-daily-market-prices-data-commodity) — Confirmed identical 11-column schema to our local AGMARKNET CSVs; arrival volume is confirmed absent.
2. **OGD Crop Production Statistics:** [`https://data.gov.in/dataset-group-name/crop-production-statistics`](https://data.gov.in/dataset-group-name/crop-production-statistics) — Historical district-level area and production aggregates (1997–2021).
3. **NABARD Commodity Research Report:** [`https://www.nabard.org`](https://www.nabard.org) — Curated analysis of daily prices and market arrivals for Tomato, Onion, Potato (TOP) and Wheat (2008–2022), providing an empirical benchmark for seasonal price transmission and supply gluts.
4. **ICAR-CIPHET Benchmark Post-Harvest Loss Studies:** National losses: Wheat (4.93%), Potato (7.32%), Onion (8.20%), Tomato (12.44%).
5. **Central Warehousing Corporation (CWC) Tariffs:** General warehouse slabs range from ₹17.29 to ₹20.00 / quintal per 7-day period.

---

## 5. Crop-by-Crop Suitability Comparison

| Dimension | Potato | Onion | Tomato | Wheat |
|---|---|---|---|---|
| **Data Continuity** | **Excellent (79.5% T+7)** | **Excellent (78.6% T+7)** | **Good (76.3% T+7)** | Moderate (71.2% T+7) |
| **Market Breadth** | 35 mandis (all 5 dist) | 36 mandis (all 5 dist) | 35 mandis (all 5 dist) | 39 mandis (all 5 dist) |
| **Reporting Consistency** | 82.6% consecutive 1d | 81.9% consecutive 1d | 80.9% consecutive 1d | 72.3% consecutive 1d |
| **Variety Standardization** | High (71.2% Desi) | High (84.6% Red) | High (68.4% Deshi) | High (78.3% Dara) |
| **Price Volatility ($\sigma$)** | Moderate (10.5%) | Moderate (10.4%) | **High (19.2%)** | Low (10.1%, tight IQR) |
| **Price Stickiness (0.0% $\Delta P$)** | 19.4% | **10.8% (Very low)** | **9.0% (Lowest)** | **29.8% (High stickiness)** |
| **Class Balance (DEC-015)** | Balanced (55 / 16 / 28) | **Optimal (44 / 23 / 33)** | Breakout (25 / 34 / 41) | **Pathological (87 / 7 / 6)** |
| **Classifier Viability** | **High** | **Highest** | **Moderate to High** | **Unviable (majority dominance)** |
| **Storage Durability** | High (in cold store) | Moderate (ventilated) | **Extremely Low (3-7 days)** | High (ambient warehouse) |
| **Storage Win Rate (Phase 5)** | 20.5% (+₹5.66/qtl) | **55.3% (+₹46.47/qtl)** | 35.3% (-₹3.14/qtl) | 15.4% (-₹0.22/qtl) |
| **External Join Feasibility** | High (CEDA + NASA) | High (CEDA + NASA) | High (CEDA + NASA) | High (CEDA + NASA) |
| **Preliminary Status** | **Promising with limitations** | **Promising** | **Promising with limitations**| **Not suitable for this phase** |

---

## 6. Classification Feasibility Evaluation

Under the project's strict classification mandate (no regression models):

1. **Onion is uniquely suited:** The majority class ("Normal") is bounded at only **44.39%**, ensuring that a naive baseline classifier achieves $<45\%$ accuracy. In the held-out exploratory test set, Favorable (178) and Normal (236) events provide balanced learning targets for machine learning classifiers.
2. **Potato provides a stable benchmark:** "Normal" represents 55.24% of records, with substantial samples in both Favorable (1,049) and Unfavorable (1,803). Test set counts (554 Normal, 95 Favorable, 70 Unfavorable) allow reliable out-of-sample confusion matrix generation.
3. **Tomato exhibits volatility inversion:** With $\sigma = 19.18\%$, the static $\pm 2.5\%$ threshold causes the majority of records to fall into the directional tail classes (41.1% Unfavorable, 33.6% Favorable). While informative for volatility modeling, it deviates from the intended "Normal stability" baseline.
4. **Wheat breaks under static thresholds:** Because wholesale wheat trading is constrained by government procurement and high quote persistence (almost 30% flat zero returns), **87.13% of all samples fall into the Normal class**. Standard classifiers will collapse to predicting "Normal" unconditionally, defeating the purpose of predictive modeling.

---

## 7. Limitations & Uncertainties

1. **Supply Volume Latency:** Ingesting external arrival volumes from CEDA or Agmarknet introduces name-reconciliation risks (e.g., matching `Lucknow APMC` vs `Lucknow (Grain)`).
2. **Weather Granularity:** NASA POWER gridded cells ($~50 \text{ km}$) cannot capture localized thunderstorm downdrafts or hailstorms that damage horticultural crops in specific mandi catchments.
3. **Local Farmgate Storage Costs:** Central Warehousing Corporation rates provide an official institutional tariff ceiling, but actual village cold-storage charges across Uttar Pradesh depend on seasonal reservation contracts and sack handling rates.

---

## 8. Preliminary Recommendation

We recommend proceeding with a focused **two-crop portfolio: Onion and Potato**.

- **Why Onion?** It offers the cleanest multi-class classification dynamics, lowest majority-class stickiness, and strong real-world storage decision relevance.
- **Why Potato?** It provides the highest data continuity, extensive regional production across Uttar Pradesh, and high cold-storage relevance.
- **Why exclude Wheat?** Its 87.1% majority-class concentration renders fixed-threshold classification statistically uninformative.
- **Why defer Tomato?** Ambient 7-day storage holding is physically unviable due to post-harvest rotting without refrigerated logistics.

---

## 9. Explicit Decisions Awaiting User Approval

1. **Candidate Crop Selection:**
   - [ ] **Option A (Recommended):** Approve **Onion and Potato** for Phase 3 feature research and classification evaluation.
   - [ ] **Option B:** Approve **Onion, Potato, and Tomato** (with Tomato restricted to price classification only, excluding ambient storage advice).
   - [ ] **Option C:** Include all four crops (requiring dynamic volatility-scaled thresholds for Wheat).
2. **External Feature Ingestion:**
   - [ ] Approve query and ingestion of sample CEDA arrival volumes and NASA POWER weather variables into `suryansh - work/dataset_research/`.
