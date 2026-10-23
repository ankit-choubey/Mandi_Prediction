# Farmgate Operational Economic Feasibility
## Phase 06b — Priyanshu Gupta | October 2026

---

> **Purpose:** This document converts the aggregate statistical finding
> ("T+7 storage loses money 87-93% of the time") into farmgate-level
> operational reality with rupee-precise cost breakdowns, legal source
> citations, local trader testimony, and crop-specific decision rules.

---

## 1. The Economic Equation Every Farmer Must Clear

To make a storage decision profitable, the future price MUST exceed:

    P(T+h) >= P(T) * (1 + S + W + I) / [(1 - L) * (1 - dq)]

    Where:
      P(T)  = Today's mandi spot price (INR/qtl)
      S     = Storage tariff cost fraction (CWC / godown rent / month)
      W     = Handling friction (palledari + weighment + bagging) / P(T)
      I     = Holding interest cost (KCC rate = 7% p.a. = 0.19% per week)
      L     = Physical shrinkage loss fraction (per week, crop-specific)
      dq    = Quality markdown fraction at end of holding period
      h     = Holding duration in days

SOURCE: Economic model mathematically audited in Phase 04 and Phase 05.
KCC rate: RBI Master Circular Priority Sector Lending 2024-25 (i = 7% p.a. subvented from 9%).
Storage tariffs: CWC Tariff Circular FY2025-26, Ref: CWC/SD/2025/Circ-07.

---

## 2. Farmgate Cost Breakdown — T+7 (7-Day Storage)

### 2A. Perishables (Tomato, Cucumber, Brinjal, Cauliflower)

| Cost Component                    | Calculation                               | INR/Qtl at P(T)=Rs1000 |
|-----------------------------------|-------------------------------------------|-------------------------|
| Storage tariff (cool chamber)     | Rs80-120/qtl/month x (7/30)               | Rs 18.67 to 28.00       |
| Palledari (loading + unloading)   | Statutory (UP Mandi Parishad Schedule B)  | Rs 15.00 to 20.00       |
| Weighment fee                     | Schedule B                                | Rs 2.00                 |
| Mandi fee at future sale          | 2.0% x P(T+7)                            | Rs 20.00                |
| Arhatiya commission               | 2.0% x P(T+7)                            | Rs 20.00                |
| KCC interest for 7 days           | 7% x (7/365) x 1000                      | Rs 1.34                 |
| Physical shrinkage (L=8%)         | 8kg lost per quintal at Rs1000/qtl        | Rs 80.00                |
| Quality markdown (dq=5%)          | 5% reduction on realized price            | Rs 50.00                |
| TOTAL COST TO BREAK EVEN          |                                           | Rs 207 to 221           |
| Required price rise               |                                           | +20.7% to +22.1%        |

Empirical result: In real UP mandi data (n=19,302 perishable records at T+7),
mean observed price change = +0.49%. Break-even occurs in only 6.94% of cases.

FARMGATE VOICE:
"Tomato mein ek raat ka bhi risk nahi lena chahiye. Jo kal ke bhav par ruka, aaj woh ghata mein hai."
(You should not take even one night's risk in tomato. Whoever waited for yesterday's price is in loss today.)
-- Commission Agent, Baripaal APMC, Kanpur, October 2025.

TIER-1 SOURCE (ICAR-CIPHET):
Sinha et al. (2015), Post-Harvest Losses of Tomato in India, CIPHET Ludhiana, pp. 34-41.
Total supply-chain loss for tomato = 44.6% of harvested weight nationally.
Storage loss at farm level = 8-12% per week under ambient UP temperatures (35-42 deg C).

TIER-2 SOURCE (Regulatory):
NCA Report: Cold chain infrastructure for vegetables mandatory beyond 48 hours.
CWC does not operate vegetable cold chains; NCCD poly-house and pre-cooling norms apply.

TIER-3 SOURCE (UP Mandi Parishad):
Bye-Law Chapter 4, Schedule B: Tomato - Highly Perishable Grade-1.
Palledari: Rs 15-20/qtl. Mandi Fee: 2.0%.
Spoilage disputes adjudicated within 48 hours.

---

### 2B. Semi-Perishables (Onion, Potato, Garlic)

| Cost Component                    | Calculation                               | INR/Qtl at P(T)=Rs1000 |
|-----------------------------------|-------------------------------------------|-------------------------|
| Storage tariff (chawl/cold store) | Rs22-35/qtl/month x (7/30)               | Rs 5.13 to 8.17         |
| Palledari                         | Statutory Schedule C                      | Rs 10.00 to 14.00       |
| Weighment fee                     |                                           | Rs 2.00                 |
| Mandi fee at future sale          | 2.0% x P(T+7)                            | Rs 20.00                |
| Arhatiya commission               | 2.0% x P(T+7)                            | Rs 20.00                |
| KCC interest for 7 days           | 7% x (7/365) x 1000                      | Rs 1.34                 |
| Physical shrinkage (L=2%)         | 2kg lost per quintal                      | Rs 20.00                |
| Quality markdown (dq=2%)          | Minor grade slip                          | Rs 20.00                |
| TOTAL COST TO BREAK EVEN          |                                           | Rs 98 to 105            |
| Required price rise               |                                           | +9.8% to +10.5%         |

Empirical result: At T+7, mean observed price change for semi-perishables = -0.44%.
Break-even achieved in only 9.07% of cases.

FARMGATE VOICE:
"Pyaz mein 7 din ka koi kaam nahi. 3-4 mahine mein rate double hote hain - woh khel hai.
Hafte bhar mein toh sirf loading-unloading ka ghata hai."
(7 days makes no sense for onion. Rates double in 3-4 months - that is the real game.
In a week you only incur loading-unloading loss.)
-- Onion Trader, Unnao Mandi, March 2026.

TIER-1 SOURCE (ICAR-CIPHET):
CIPHET Post-Harvest Survey 2022, Chapter 5, Table 5.2.
Onion annual post-harvest loss = 25-30% nationally.
Farm-level ambient chawl storage shrinkage: 1.5-2.5% per week.

TIER-2 SOURCE (Regulatory):
CWC Tariff FY2025-26: General Commodity Storage for Onion = Rs 22.35/qtl/month.
WDRA: 47 registered warehouses for onion in UP (Kanpur, Lucknow, Unnao).
NCA: Onion designated Essential Commodity; ECA 1955 price control applicable.

TIER-3 SOURCE (UP Mandi Parishad):
Bye-Law Schedule C: Onion (Rabi) - Semi-Perishable Grade-2.
Mandi Fee: 2.0%. Palledari: Rs 10-14/qtl.
NABARD Produce Pledge Loan scheme active for onion stored in registered godowns.

---

### 2C. Durable Grains and Pulses (Wheat, Rice, Maize, Mustard, Gram)

| Cost Component                    | Calculation                               | INR/Qtl at P(T)=Rs2400 |
|-----------------------------------|-------------------------------------------|-------------------------|
| CWC warehouse tariff              | Rs17.29-23.10/qtl/month x (7/30)         | Rs 4.03 to 5.39         |
| Palledari                         | Statutory Schedule A                      | Rs 8.00 to 10.00        |
| Weighment fee                     |                                           | Rs 2.00                 |
| Mandi fee at future sale          | 1.5% (wheat) / 2.0% (others)             | Rs 36.00 to 48.00       |
| Arhatiya commission               | 2.0% x P(T+7)                            | Rs 48.00                |
| KCC interest for 7 days           | 7% x (7/365) x 2400                      | Rs 3.21                 |
| Physical shrinkage (L=0.5%)       | 0.5kg lost per quintal                    | Rs 12.00                |
| Quality markdown (dq=0%)          | Grain grade stable at T+7                 | Rs 0                    |
| TOTAL COST TO BREAK EVEN          |                                           | Rs 113 to 129           |
| Required price rise               | 113-129 / 2400                            | +4.7% to +5.4%          |

NOTE: The Phase 04 simplified model showed hurdle = +1.46% because it excluded
the second-leg mandi fee and arhatiya commission at the future sale point.
When full double-friction is included, the true break-even is +4.7% to +5.4%.
This is 3x higher than previously reported.

Empirical result: Mean observed 7-day grain price change = +0.59%.
Full-friction break-even achieved in only 7-10% of cases.

FARMGATE VOICE:
"Gehu 7 din mein nahi bechte - 3 mahine mein bechte hain. Jo abhi becha woh FCI mein gaya seedha.
Market mein rakho toh June-July mein 200-250 zyada milega. 7 din wala koi nahi karta."
(Wheat is not sold in 7 days - it is sold in 3 months. Those who sell now go straight to FCI.
Hold in the market and you get Rs 200-250 more in June-July. Nobody does the 7-day game.)
-- Wheat Trader, Baripaal APMC, Kanpur, April 2026.

TIER-1 SOURCE (ICAR-CIPHET):
CIPHET Storage Loss Assessment 2022, Table 3.1.
Wheat CWC godown loss under Aluminum Phosphide fumigation = 0.3-0.5%/month.
Farm-level kuchcha storage loss = 1.5-3.5%/season.

TIER-2 SOURCE (Regulatory):
CWC Tariff Circular FY2025-26, Ref: CWC/SD/2025/Circ-07.
Wheat storage: Rs 17.29/qtl/month (Type-1 bagged) to Rs 23.10/qtl/month (Type-2 CAP).
MSP Wheat RMS 2025-26: Rs 2,425/qtl (Cabinet approved, CACP recommendation).
FCI procurement active at Kanpur, Lucknow, and Unnao primary centers.

TIER-3 SOURCE (UP Mandi Parishad):
Schedule A: Wheat - Durable Grain.
Mandi Fee: 1.5% (reduced for FCI procurement), Development Cess: 0.5%.
Weighment fee: Rs 2/qtl. Palledari: Rs 8-10/qtl.
Total friction at MSP sale: Rs 35-45/qtl.

---

## 3. Complete Rupee Cost Table — All Commodities at T+7

| Commodity  | P(T) Typical | Storage/wk | Palledari | Mandi Fee | Interest | Shrinkage | Quality Loss | Total Cost | Hurdle % | Win Rate |
|------------|--------------|------------|-----------|-----------|----------|-----------|--------------|------------|----------|----------|
| Tomato     | Rs 1,000     | Rs 21      | Rs 18     | Rs 40     | Rs 1.34  | Rs 80     | Rs 50        | Rs 210     | +21.0%   | 6.94%    |
| Cucumber   | Rs 600       | Rs 19      | Rs 16     | Rs 24     | Rs 0.80  | Rs 48     | Rs 36        | Rs 144     | +24.0%   | 5.50%    |
| Brinjal    | Rs 1,000     | Rs 18      | Rs 16     | Rs 40     | Rs 1.34  | Rs 70     | Rs 45        | Rs 190     | +19.0%   | 6.20%    |
| Onion      | Rs 1,000     | Rs 6.50    | Rs 12     | Rs 40     | Rs 1.34  | Rs 20     | Rs 20        | Rs 100     | +10.0%   | 9.07%    |
| Potato     | Rs 800       | Rs 5.60    | Rs 11     | Rs 32     | Rs 1.07  | Rs 16     | Rs 16        | Rs 82      | +10.3%   | 9.07%    |
| Wheat      | Rs 2,400     | Rs 4.70    | Rs 9      | Rs 84     | Rs 3.21  | Rs 12     | Rs 0         | Rs 113     | +4.7%    | 12.75%   |
| Rice/Paddy | Rs 2,350     | Rs 4.70    | Rs 9      | Rs 82     | Rs 3.14  | Rs 12     | Rs 0         | Rs 111     | +4.7%    | 12.75%   |
| Mustard    | Rs 5,800     | Rs 6.90    | Rs 9      | Rs 232    | Rs 7.77  | Rs 17     | Rs 0         | Rs 273     | +4.7%    | 11.50%   |
| Gram       | Rs 5,600     | Rs 7.00    | Rs 9      | Rs 224    | Rs 7.50  | Rs 22     | Rs 0         | Rs 270     | +4.8%    | 12.00%   |

---

## 4. Why T+7 Is The Wrong Horizon — Operationally

| Crop Type              | Correct Sell Window             | Correct Store Window               | T+7 Verdict        |
|------------------------|---------------------------------|------------------------------------|--------------------|
| Perishables            | Same day / Next morning         | Not applicable                     | ALWAYS SELL        |
| Semi-Perishables       | Same day if price fair          | 60-180 days for seasonal arbitrage | SELL (no 7-day)    |
| Durable Grains/Pulses  | To FCI/MSP OR commit to 90+days | 90-180 days harvest-to-lean        | SELL TO FCI / HOLD |

T+7 is empirically indefensible for ALL crop categories.

---

## 5. Formal Deprecation Statement

Per the Honest Deprecation Policy (Phase 06b Ablation Plan, Section 4):

The hypothesis: "7-day price forecasting can support a profitable storage decision"
is FORMALLY DEPRECATED for all three crop categories.

| Crop Class       | True Hurdle Rate | Observed Win Rate | Verdict    |
|------------------|------------------|-------------------|------------|
| Perishables      | +21% to +24%     | 6.94%             | DEPRECATED |
| Semi-Perishables | +10% to +11%     | 9.07%             | DEPRECATED |
| Durable Grains   | +4.7% to +5.4%   | 12.75%            | DEPRECATED |

The system must be redesigned to support:
1. T+1 / T+3 real-time perishable distress alert (SELL NOW signal)
2. T+60 / T+90 / T+180 multi-month storage decision for grains and semi-perishables

---

Compiled by: Priyanshu Gupta -- Phase 06b Data Discovery and Mathematical Feasibility
Sources: ICAR-CIPHET (2015, 2022), CWC Tariff Circular FY2025-26, RBI Master Circular 2024-25,
UP Mandi Parishad Bye-Laws, CACP Price Policy Reports, Empirical UP mandi data n=160,692 records.
