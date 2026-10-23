# Om — Agricultural Supply Chain & Economic Feasibility Workspace

**Investigator:** Om Awasthi  
**Track:** Track D — Agricultural Supply Chain, Storage Biology, and Economic Feasibility  
**Reference Codebase:** [`../Mandi_Prediction`](file:///Users/omawasthi/Developer/ml%20project/Mandi_Prediction)  
**Status:** Complete — Master Research Report & Cited Parameter Registries Established  

---

## 1. Track D Scope & Mandate

While **Track A (Ankit)** audited the 5-district price benchmark, **Track B (Suryansh)** catalogued nationwide datasets and arrival volumes, and **Track C (Priyanshu)** established mathematical validity and disqualified regression, **Track D (Om)** determines whether any model forecast can actually be executed by a smallholder farmer in Uttar Pradesh without causing financial distress.

### Delivered Core Artifacts:
1. 📄 **[`Track_D_Agricultural_Supply_Chain_Feasibility.md`](Track_D_Agricultural_Supply_Chain_Feasibility.md)**: The comprehensive, cited master report detailing the 18-crop feasibility matrix, the six structural supply chain bottlenecks, the double-friction economic equation, and operational decision trees.
2. 📊 **[`crop_storage_feasibility_matrix.csv`](crop_storage_feasibility_matrix.csv)**: Machine-readable 18-crop biological feasibility table mapping physiological shelf-life, storage biology, optimal temperatures/humidity, and 7-day vs multi-month viability.
3. 📋 **[`storage_and_supply_chain_parameters.csv`](storage_and_supply_chain_parameters.csv)**: Complete 22-parameter registry categorized into the strict **4-Tier Evidence Hierarchy** (`[OFFICIAL SOURCE]`, `[PUBLISHED STUDY]`, `[LOCAL QUOTE]`, `[ILLUSTRATIVE ASSUMPTION]`) with statutory citations and operational context.
4. ⚙️ **[`verify_track_d.py`](verify_track_d.py)**: Reproducible validation script verifying parameter consistency and hurdle rate calculations across all crops.

---

## 2. Key Empirical Findings from Track D

1. **The 7-Day Temporal Mismatch:**
   * **Perishables (Tomato):** Ambient shelf-life is only 2–4 days. 7-day holding causes 8%–12% rotting; break-even requires a **+21.0% price surge**, which occurs in only 6.94% of market sessions (93.1% loss rate).
   * **Tubers (Potato):** UP cold storages operate strictly on full-season rental contracts (₹120–₹160 per 50 kg bag from March to October). 7-day tactical cold storage is commercially non-existent.
   * **Grains (Wheat):** Low weekly price volatility (+0.59%) cannot overcome fixed loading, bagging, and double mandi friction (₹113/qtl). Tactical 7-day holding loses money 87.25% of the time. Grains require **90 to 180-day seasonal holding**.
2. **The Double-Friction Penalty:**
   * Selling on day $T+7$ requires paying APMC mandi cess ($1.5\% - 2.0\%$) and commission agent (*arhatiya*) cuts ($2.0\%$) **a second time**, raising true break-even hurdle rates by 3x–4x over naive single-leg models.
3. **Smallholder Institutional Exclusion:**
   * Smallholders (averaging 0.73 ha landholding) harvest 5 to 15 quintals, physically excluding them from accredited CWC warehouses (50–100 qtl minimum deposit) and bank warehouse receipt financing.
4. **Debt Distress & Harvest Settlement:**
   * Over 60% of smallholders borrow from local moneylenders/arhatiyas at 24%–36% p.a. Harvest-gate liquidation is mandatory to settle debt, precluding speculative holding.

---

## 3. Directory Layout

```text
Om/
├── README.md                                          # Track D navigation & executive summary
├── Track_D_Agricultural_Supply_Chain_Feasibility.md   # Master research report & operational protocol
├── crop_storage_feasibility_matrix.csv               # 18-crop storage biology & viability matrix
├── storage_and_supply_chain_parameters.csv           # 4-tier source-backed parameters & citations
└── verify_track_d.py                                 # Automated hurdle rate & consistency verifier
```

---

## 4. Verification & Reproducibility

To run the automated verification script and reproduce all crop hurdle calculations:
```bash
python Om/verify_track_d.py
```
Outputs print directly to console verifying 0 discrepancies across all 18 commodities.
