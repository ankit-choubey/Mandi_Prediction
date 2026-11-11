# Decisions Pending Approval: Phase 02 Crop Suitability

**Investigator:** Suryansh  
**Target:** User Approval Checkpoint  
**Date:** October 23, 2026  

---

## 1. Proposed Crop Selection

Based on empirical data quality, exact calendar $T+7$ continuity, class balance under DEC-015, and real-world storage relevance, the candidate crops are classified as follows:

| Crop | Classification Status | Suitability Assessment | Recommendation for Phase 3 |
|---|---|---|---|
| **Onion** | **Promising** | • **Best multi-class balance** in dataset (Normal: 44.4%, Unfavorable: 33.1%, Favorable: 22.5%).<br>• High continuous coverage (7,728 clean rows, 78.6% T+7 availability across 36 mandis).<br>• Demonstrated commercial decision relevance (55.3% storage win rate in historical test with positive return +₹46.47/qtl). | **PRIMARY SELECTION (Highly Recommended)** |
| **Potato** | **Promising with Limitations** | • **Highest T+7 continuity** (79.5% availability across 35 mandis; 8,017 clean rows).<br>• Moderate class balance (Normal: 55.2%, Unfavorable: 28.3%, Favorable: 16.5%).<br>• Key limitation: Economic viability depends strictly on cold-storage access and accounting for institutional tariffs. | **SECONDARY SELECTION (Recommended)** |
| **Tomato** | **Promising with Limitations** | • Highest price volatility ($\sigma = 19.2\%$) creates active class breakouts (Unfavorable: 41.1%, Favorable: 33.6%, Normal: 25.3%).<br>• Good data coverage (7,520 clean rows, 76.3% T+7 availability across 35 mandis).<br>• **Major operational limitation:** High perishability (ambient shelf life 3–7 days). 7-day holding without cold-chain causes severe physical decay and negative economic returns (-₹3.14/qtl). | **OPTIONAL / BENCHMARK ONLY (Directional classification only; not suitable for ambient storage holding)** |
| **Wheat** | **Not Suitable for This Phase** | • High row volume (11,727 clean rows) and 100% daily continuity.<br>• **CRITICAL CLASSIFICATION DEFECT:** Severe majority-class stickiness under static $\pm 2.5\%$ thresholds (**87.13% Normal**; minority classes starved at 6.5% and 6.3%). Any baseline model predicting "Normal" achieves 87.1% accuracy without learning patterns.<br>• Weekly price changes rarely exceed storage tariffs (₹20/qtl), resulting in a 15.4% storage win rate and negative returns. | **EXCLUDE FROM PHASE 3 CLASSIFICATION** (Unless dynamic volatility thresholds or multi-month horizons are introduced) |

---

## 2. Recommended Initial Crop Set

### **Proposed Focus: Onion and Potato (2-Crop Portfolio)**
- **Why Onion + Potato?**
  1. **Behavioral Diversity:** Pairs an active, volatile commercial bulb (**Onion**) with a staple seasonal tuber (**Potato**).
  2. **High Label Purity & Continuity:** Both exhibit $\sim 79\%$ exact calendar $T+7$ availability across 35+ mandis in all 5 districts.
  3. **Classification Integrity:** Both have sufficient minority-class frequencies (Favorable and Unfavorable each have $>1,000$ examples) allowing classifiers to learn meaningful decision boundaries instead of defaulting to the majority class.
  4. **Post-Harvest Feasibility:** Both represent realistic holding candidates for Uttar Pradesh farmers (Onion via ventilated farm storage; Potato via the state's extensive cold storage grid).
  5. **Avoids Wheat's Pathological 87% Normal Bias and Tomato's Extreme Spoilage Decay.**

---

## 3. Remaining Uncertainties

1. **Absence of Arrival Volumes:**  
   The current project data lacks supply volume metrics. While CEDA Agri-Market and Agmarknet provide arrival volumes, integrating them requires resolving mandi name string variations and handling historical missingness.
2. **Weather Feature Latency:**  
   NASA POWER provides free daily agroclimatology data, but MERRA-2 assimilation introduces a 2- to 4-day publication delay. We must verify whether preliminary near-real-time estimates can be used at prediction time $T$ without lookahead bias.
3. **Farmgate vs Institutional Storage Tariffs:**  
   CWC tariffs provide a verified institutional ceiling (₹17–₹20/qtl/week), but informal village-level cold-storage charges across UP vary from ₹120 to ₹250 per bag (50 kg) per season.

---

## 4. Formal Decisions Requiring User Approval

1. **Approval of Candidate Crop Selection:**
   - **Option A (Recommended):** Approve **Onion and Potato** as the focused two-crop research set for feature engineering and model evaluation.
   - **Option B:** Approve **Onion, Potato, and Tomato** (with Tomato restricted strictly to directional price classification, excluding ambient storage advisory).
   - **Option C:** Include all four crops (with Wheat evaluated using commodity-specific dynamic thresholds rather than the fixed $\pm 2.5\%$ band).
2. **Approval to Proceed with Dataset Research & Feature Design:**
   - Authorization to query and integrate small, clean external sample series (CEDA arrival volumes and NASA POWER weather variables) in `suryansh - work/dataset_research/`.
