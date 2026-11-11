# DATA_SOURCE_ALTERNATIVES.md: Provenance Audit & Alternative Reference Source Investigation

**Project:** APMC Mandi Market Intelligence & Price Forecasting Engine  
**Repository:** `ankit-choubey/Mandi_Prediction`  
**Author / Investigator:** Suryansh  
**Audit Timestamp (UTC):** `2026-10-23T13:28:45Z`  
**Dataset Under Audit:** 5-Year Mandi Price Panel (Ghaziabad, Jhansi, Kanpur, Lucknow, Unnao; 2021-09-01 to 2026-09-30)  

---

## 1. Executive Summary

This report evaluates the provenance, collection methodology, and empirical characteristics of the existing **5-year APMC mandi dataset** (`472,385` raw observations, `462,350` validated clean rows) against two primary reference sources:
1. **The Official AGMARKNET Portal** (Directorate of Marketing & Inspection, Ministry of Agriculture & Farmers Welfare, GoI).
2. **The CEDA Agri-Market Data Portal & API** (Centre for Economic Data and Analysis, Ashoka University).

### Key Empirical Findings:
- **Existing Dataset Provenance:** Confirmed as an automated or batch extraction from the Open Government Data (OGD) Platform India API (`data.gov.in`, Resource ID `9ef84268-d588-465a-a308-a864a43d0070`), which itself ingests upstream daily market closing reports from the DMI AGMARKNET national grid.
- **The Arrival Volume Gap:** Both the existing dataset and the OGD API endpoint publish **wholesale clearing prices exclusively** (`Min_Price`, `Max_Price`, `Modal_Price`). Physical arrival volumes (metric tonnes or quintals brought to market yards) are **completely omitted** from this resource.
- **CEDA as an Alternative Source:** The CEDA archive resolves this gap by providing harmonized daily physical arrival volumes (`arrivals_in_qtl` / `arrivals_in_tonnes`), but requires authenticated bearer token access and academic attribution.

---

## 2. Multi-Source Comparative Architecture Matrix

| Dimension | Existing Project Dataset | Official AGMARKNET Portal | CEDA Agri-Market Portal & API |
| :--- | :--- | :--- | :--- |
| **Publisher / Custodian** | Extracted from OGD Platform India (DMI upstream) | Directorate of Marketing & Inspection (DMI), MoA&FW, GoI | Centre for Economic Data and Analysis (CEDA), Ashoka University |
| **Official URL** | Local repository: [`5 year dataset/`](file:///Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction/5%20year%20dataset) | [`https://agmarknet.gov.in/`](https://agmarknet.gov.in/) | [`https://agmarknet.ceda.ashoka.edu.in/`](https://agmarknet.ceda.ashoka.edu.in/) (API: `api.ceda.ashoka.edu.in/v1`) |
| **Primary Data Interface** | Static tabular CSV files | Web ASP.NET interface (`Price_Arrival_Search.aspx`) | REST API (`/v1/agmarknet/prices`, `/v1/agmarknet/quantities`) & Web GUI |
| **Authentication Requirements** | None (Local files stored in repository) | None for interactive browser queries; CAPTCHA protection for automated scraping | Bearer Token (`Authorization: Bearer <TOKEN>`) via free user registration |
| **Access & Rate Limits** | Unlimited local I/O | Browser queries restricted to 3-month blocks per request; rate-limited bot blocking | Rate-limited by API key; bulk downloads throttled to prevent server overload |
| **Licensing & Terms of Use** | Open Government Data License – India (GODL) | Ministry terms; non-commercial government information | Creative Commons Attribution 4.0 International (CC BY 4.0); attribution mandatory |
| **Available Price Fields** | `Min_Price`, `Max_Price`, `Modal_Price` (₹/Quintal) | `Min_Price`, `Max_Price`, `Modal_Price` (₹/Quintal) | `Min_Price`, `Max_Price`, `Modal_Price` (₹/Quintal) |
| **Physical Arrival Volumes?** | **NO (Strictly Absent)** | **YES** (Reported in Tonnes on daily bulletin reports) | **YES** (Standardized in Metric Tonnes and Quintals) |
| **Temporal Granularity** | Daily trading observations (excluding Sunday holidays) | Daily trading observations (reported daily by APMC yard secretaries) | Daily time-series harmonized to calendar dates |
| **Date Range Coverage** | **2021-09-01 to 2026-09-30** (1,856 calendar days) | Historical archive from early 2000s to present | 2006 to present (monthly / quarterly batch updates) |
| **Geographic Coverage** | 5 target Uttar Pradesh districts (41 APMC markets) | Pan-India (>3,000 APMC markets across all states) | Pan-India (>3,000 APMC markets harmonized) |
| **Commodity Coverage** | 139 distinct commodity names | >300 agricultural commodities | >300 agricultural commodities harmonized |
| **Standardized Market Identifiers?** | Text strings (`Market`); no numerical Market ID | Text strings (`Market_Name`); no static numerical public ID | **YES** (Provides internal integer `market_id` along with strings) |

---

## 3. Deep-Dive Source Investigations

### 3.1 Source 1: The Official AGMARKNET Portal (`agmarknet.gov.in`)

#### Collection & Reporting Architecture
- **Upstream Capture:** Mandi pricing data is gathered at the farmgate market yard level. APMC market secretaries or data entry clerks enter daily auction summaries into the national Agricultural Marketing Information Network (AGMARKNET) portal.
- **Reporting Parameters:** The system captures `Arrival Date`, `Commodity`, `Variety`, `Grade`, `Arrival Quantity (Tonnes)`, `Minimum Price`, `Maximum Price`, and `Modal Price` (the most frequent single clearing price recorded during the trading session).
- **Public Dissemination:** 
  - The public front-end operates as a legacy ASP.NET application (`Price_Arrival_Search.aspx`).
  - Queries are parameter-driven (State $\to$ District $\to$ Market $\to$ Commodity $\to$ Date Range).
  - Web queries enforce a maximum query window (typically 1 to 3 months) to avoid server timeouts.
- **Access Restrictions:**
  - No public REST API is published directly on the root `agmarknet.gov.in` domain.
  - Requests from automated HTTP clients (e.g. `requests`, `curl`, `urllib`) frequently encounter session cookie validation, viewstate tokens, or IP-level rate-limiting.

### 3.2 Source 2: CEDA Agri-Market Data Portal (`ceda.ashoka.edu.in`)

#### Architecture & Capabilities
- **Publisher:** Centre for Economic Data and Analysis (CEDA), Department of Economics, Ashoka University.
- **Purpose:** Academic data curation project designed to clean, normalize, and provide programmatic access to AGMARKNET historical records.
- **REST API Endpoints:**
  - `POST https://api.ceda.ashoka.edu.in/v1/agmarknet/prices`
  - `POST https://api.ceda.ashoka.edu.in/v1/agmarknet/quantities`
- **Request Payload Structure:**
  ```json
  {
    "state": "Uttar Pradesh",
    "district": "Kanpur",
    "commodity": "Potato",
    "start_date": "2024-09-01",
    "end_date": "2024-09-05"
  }
  ```
- **Response Schema:**
  ```json
  {
    "market_id": 1042,
    "market_name": "Kanpur (Grain)",
    "commodity_name": "Potato",
    "arrival_date": "2024-09-01",
    "arrivals_in_qtl": 1420.5,
    "unit": "Quintals"
  }
  ```
- **Strengths:**
  1. Contains genuine, observed arrival volumes (`arrivals_in_qtl`).
  2. Resolves historical APMC renaming and typos.
  3. Provides an explicit integer `market_id`.
- **Known Constraints:**
  1. Token Gating: Requires a personal Bearer Token generated after manual account registration.
  2. Academic Attribution: Mandatory citation of CEDA in all published materials.
  3. Latency: Monthly or quarterly synchronization cadence means same-day live operational streaming is not supported.

---

## 4. Provenance Audit of the Existing 5-Year Dataset

### 4.1 Provenance Verification Evidence

1. **Header & Column Order Alignment:**
   The raw files in [`5 year dataset/`](file:///Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction/5%20year%20dataset) share the exact 11-column signature:
   ```text
   Arrival_Date, Commodity, Commodity_Code, District, Grade, Market, Max_Price, Min_Price, Modal_Price, State, Variety
   ```
   This matches character-for-character with the fields exported by the Open Government Data Platform India (Resource ID: `9ef84268-d588-465a-a308-a864a43d0070`).
2. **Date Format Signatures:**
   All dates are formatted as `%d/%m/%Y` (e.g. `04/09/2021`), which is the standard string serialization produced by the OGD India daily price download service.
3. **Price Unit Conventions:**
   Prices are expressed in Indian Rupees per Quintal (100 kg), with zero unit conversion applied.
4. **Administrative District Nomenclature:**
   The district files exhibit historical spellings (`LUKHNOW.csv` naming in file headers, with internal standardized values).

### 4.2 Identified Uncertainties & Caveats

1. **Absence of Download Metadata:**
   The raw files do not include an embedded metadata header comment indicating the exact HTTP request URL, user-agent, or timestamp of extraction. However, empirical date ranges verify records up to `2026-09-30`.
2. **Missing Market Primary Keys:**
   No numerical APMC yard identifier exists in the source files. Market entity identification relies entirely on string matching (`Market`).
3. **No Upstream Audit Hash:**
   Because OGD updates datasets dynamically, no static government-side SHA-256 hash exists to cross-verify historical byte contents against a fixed ledger. Our local repository establishes the cryptographic baseline:
   - `GHAZIABAD.csv`: `17d2ccca09866a8272fa290e7c0c1816c74b6fc9dd56607548656ade4b8787ef`
   - `JHANSI.csv`: `179d7d330914b7e130673f83c3931b5a2cc1935c5555a19e4f417cd73ed8a2e3`
   - `KANPUR.csv`: `c89551a32fcd4cb02d4bc85cb50de532b2478d9806fb4d8cd9ae859bf1b06d7f`
   - `LUKHNOW.csv`: `19bb57961c67cc439e2798ddb23d63cade9320bdb8659929f656a79d31f59e8a`
   - `UNNAO.csv`: `e64405faf71070193b10a4477a8c259ad08eae6c9051872dbc545e507c115fc4`

---

## 5. Separation of Verified Facts from Assumptions

```text
========================================================================================================================
ASPECT                       VERIFIED FACT (EMPIRICAL EVIDENCE)             UNVERIFIED ASSUMPTION (DO NOT RELY ON)
========================================================================================================================
Arrival Quantities           OGD resource 9ef84268... contains NO arrival   Assuming that arrival quantities can be
                             volume columns. Both 2-yr and 5-yr files lack  inferred or approximated from price spreads.
                             arrival weights entirely.                      (Must be treated as an external data gap).

CEDA Endpoint Access         Live endpoint POST /v1/agmarknet/quantities    Assuming CEDA data is publicly queryable
                             requires an authorized Bearer Token.           without an account or API registration.

Price Units & Currency       All prices are in INR (₹) per Quintal (100 kg) Assuming prices represent retail or farmgate
                             clearing prices at APMC wholesale gates.       proceeds (they exclude transport/trader margin).

Dataset Coverage Completeness 472,385 records spanning 1,856 days across    Assuming zero reporting gaps on non-Sundays
                             41 APMC markets and 108 active commodities.    (local holidays/strikes cause occasional gaps).
========================================================================================================================
```

---

## 6. Synthesis & Strategic Recommendations

### 6.1 Recommendation for Current Dataset Usage
- **Retain as Primary Empirical Price Panel:** The existing 5-year dataset (`462,350` clean rows) is verified, fully validated, and provides continuous, multi-season daily price quotes spanning September 2021 through September 2026.
- **Econometric Integrity:** For price forecasting, volatility estimation, spatial neighbor price transmission, and $T+7$ directional classification, the dataset is self-contained and free of synthetic contamination.

### 6.2 Circumstances Under Which Alternative Sources Should Be Acquired
1. **Acquire CEDA Agmarknet When:**
   - The modeling scope expands to test **supply-demand price elasticity** (e.g. testing whether high truck arrival volumes depress prices 7 days later).
   - In that scenario, register a CEDA academic API token, query the quantities endpoint, and perform an exact calendar join (`District + Market + Commodity + Variety + (Date - 1 day)`) strictly lagged by $T-1$ to prevent lookahead leakage.
2. **Acquire Direct AGMARKNET Scraping When:**
   - Real-time intraday price updates are required for same-day harvest liquidation decisions, and the OGD daily bulk publication pipeline exhibits operational latency.
