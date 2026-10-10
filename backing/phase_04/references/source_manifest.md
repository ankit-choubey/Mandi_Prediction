# Phase 4 Reference Source Manifest

**Project:** Mandi_Prediction  
**Repository:** `ankit-choubey/Mandi_Prediction`  
**Phase:** 4 — Economic Decision Support and Sell-versus-Store Validation  
**Date:** October 10, 2026  

---

## 1. Overview of Reference Documents

Phase 4 utilizes two official government reference publications to ground storage cost benchmarks and post-harvest loss assumptions.

In accordance with Phase 4 guidelines:
- Published tariffs are treated as reference benchmarks, not assumed local farmer rates.
- National cumulative post-harvest loss figures are recognized as supply-chain totals, not 7-day storage shrinkage measurements.
- Local parameters are exposed as configurable assumptions with explicit sensitivity bounds.

---

## 2. Document 1: Official Warehousing Tariff Reference

| Field | Detail |
|---|---|
| **Document Title** | Revision of Tariffs for FY 2026–27 w.e.f. 01.04.2026 at RWCs (Ref: CWC CO-CD/10/2025-COMM / E No. 116836) |
| **Issuing Organization** | Central Warehousing Corporation (CWC), Government of India Undertaking |
| **Direct URL** | `https://cewacor.nic.in/Docs/RevisedRWCTariff2627dt23032026.pdf` |
| **Publication Date** | 23 March 2026 |
| **Effective Date** | 01 April 2026 |
| **Retrieval Date** | 10 October 2026 |
| **Local File Path** | [`backing/phase_04/references/cwc_rwc_tariff_fy2026_27.pdf`](./cwc_rwc_tariff_fy2026_27.pdf) |
| **File Size** | 1,258,264 bytes |
| **SHA-256 Checksum** | `f635daee849193845066c29e1aee5c8c1a586ead0452673016f8a41c0f75390e` |
| **Applicable Location** | Regional Warehousing Centres (RWCs) under Regional Offices, including Lucknow and Delhi (Ghaziabad) |
| **Applicable Duration** | Daily standard slabs (Days 1–2, Days 3–6, Day 7+) and monthly reservations for FY 2026–27 |
| **Tariff Units** | Rupees per Metric Ton (PMT) per day (General storage); Rupees per MT per month (Reservation) |

### Key Published Rates & Mathematical Extraction:
1. **General Storage Standard Slabs (Annexure-I, Pages 4–7):**
   - **Lucknow Alamnagar RWC:**
     - Days 1–2: ₹18.50 PMT/day
     - Days 3–6: ₹25.80 PMT/day
     - Days 7–15: ₹32.69 PMT/day
     - **Cumulative 7-Day Storage Cost:**
       $$\text{Cost}_{\text{7d}} = (2 \times 18.50) + (4 \times 25.80) + (1 \times 32.69) = 37.00 + 103.20 + 32.69 = \text{₹}172.89 \text{ per MT}$$
       Since $1 \text{ MT} = 10 \text{ quintals}$, the per-quintal cost is:
       $$c_{\text{storage, 7d}} = \frac{172.89}{10} = \text{₹}17.29 \text{ per quintal for 7 days}$$
   - **Delhi Ghaziabad RWC:**
     - Reservation monthly tariff: ₹231.00 PMT/month = ₹23.10 / quintal / month.
     - Pro-rated 7-day cost: $\approx \text{₹}5.39 \text{ per quintal}$.
2. **Ancillary Charges (Page 2):**
   - Lorry weighment charges: ₹80 per vehicle ($\le 10$ MT) and ₹160 per vehicle ($> 10$ MT) inclusive of 18% GST.
   - Taxes: 18% GST applicable over storage where commercial rates apply.

### Methodological Limitations & Usage:
- **Reference Benchmark Only:** CWC tariffs apply to organized public warehouses and railside container yards. Smallholder farmers face decentralized mandi loading, unloader (*palledari*) charges, local cooperative (*PACS*) or private storage fees, which can range from ₹10 to ₹35/quintal.
- **Scenario Incorporation:** Used to anchor the central storage cost parameter at **₹20.00 / quintal** and conservative bound at **₹35.00 / quintal** (inclusive of local handling and loading).

---

## 3. Document 2: Official Agricultural Post-Harvest Loss Reference

| Field | Detail |
|---|---|
| **Document Title** | Post Harvest Food Loss (Press Information Bureau, Ministry of Food Processing Industries, PRID 1885038) |
| **Issuing Organization** | Ministry of Food Processing Industries (MoFPI), Government of India |
| **Direct URL** | `https://www.pib.gov.in/Pressreleaseshare.aspx?PRID=1885038&lang=2&reg=48` |
| **Publication Date** | 20 December 2022 |
| **Retrieval Date** | 10 October 2026 |
| **Local File Path** | [`backing/phase_04/references/pib_post_harvest_food_loss_2022.pdf`](./pib_post_harvest_food_loss_2022.pdf) |
| **File Size** | 126,305 bytes |
| **SHA-256 Checksum** | `63f2847c46cea8c0c6723195d593924e36e299e36e95195e22ea1e4018ba70fc` |
| **Commissioned Studies** | 1. ICAR-CIPHET (2015): Assessment of Quantitative Harvest and Post Harvest Losses<br>2. NABCONS (2022): Study to Determine Post-Harvest Losses of Agri Produce in India |
| **Applicability** | National commodity estimates across major crop categories |
| **Units** | Percentage of harvest volume lost across supply chain (%) |

### Key Published Findings (Comparative Loss Summary):

| Commodity Category | Specific Crop | ICAR-CIPHET (2015) Loss (%) | NABCONS (2022) Loss (%) |
|---|---|---|---|
| **Cereals** | Overall | 4.67% – 5.99% | 3.89% – 5.92% |
| | **Wheat** | 4.93% | **3.73%** |
| | **Paddy (Rice)** | 5.53% | **5.46%** |
| **Pulses** | Overall | 6.36% – 8.41% | 5.65% – 7.37% |
| **Oilseeds** | Overall | 5.29% – 9.96% | 3.08% – 9.96% |
| **Fruits & Vegetables** | Overall | 4.58% – 15.88% | 4.87% – 11.61% |
| | **Potato** | 7.32% | **5.92%** |
| | **Onion** | 8.20% | **7.02%** |
| | **Tomato** | 12.44% | **11.61%** |

### Methodological Limitations & Usage:
- **Supply-Chain Cumulative:** These national numbers represent cumulative losses occurring from harvesting, threshing, farm storage, transport, wholesale handling, and retail marketing over weeks or months.
- **Not 7-Day Warehouse Shrinkage:** Storing dry grain (Wheat/Paddy) in a bag for 7 days typically causes minimal physical shrinkage ($0.2\% - 0.5\%$), whereas perishables (Tomato/Onion) can experience moisture loss and rotting ($1\% - 3\%$).
- **Scenario Incorporation:** Used to establish realistic loss bounds for a 7-day holding period:
  - Optimistic: $L = 0.5\%$ (0.005)
  - Central: $L = 1.0\%$ (0.010)
  - Conservative: $L = 2.0\%$ (0.020)
  - Severe Perishable Sensitivity: $L = 5.0\%$ (0.050)
