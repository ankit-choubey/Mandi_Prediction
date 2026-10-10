# Phase 4: Operational and Economic Limitations

**Project:** Mandi_Prediction
**Repository:** `ankit-choubey/Mandi_Prediction`
**Phase:** 4 — Economic Decision Support and Sell-versus-Store Validation
**Date:** October 10, 2026

---

## 1. Executive Caveat: NOT Production-Ready for Farmer Advice

The economic decision-support model developed in Phase 4 is a **research and testing prototype**.

> **MANDATORY POLICY DIRECTIVE:**
> **Under NO circumstances should the current system be deployed as an operational farmer advisory system or used to recommend that smallholder farmers hold produce rather than sell immediately.**

While the model-based policy achieves a positive *mean* incremental return (+₹33.55 to +₹42.21 / quintal) under central assumptions, detailed risk analysis reveals acute structural barriers that make operational adoption premature and potentially harmful to smallholders.

---

## 2. Key Empirical Risk Findings

### 2.1 The "Win-Rate" Deficit (62% Loss Rate on Storage)
- Under the Central Scenario, when the model advises storage, **storage beats immediate selling in only 37.8% – 37.9% of cases**.
- Conversely, in **62.1% – 62.2% of instances where storage was triggered, immediate selling yielded higher net proceeds than 7-day storage**.
- While positive expectation with a ~38% win rate can be tolerated in diversified trading contexts where large gains offset frequent losses, an unhedged decision rule with a ~62% loss frequency carries severe downside exposure for discrete, infrequent agricultural sales. Individual farmers' actual risk tolerances and cash flow constraints cannot be inferred from aggregate mandi price series, but this high loss frequency represents an objective obstacle to deploying unhedged binary recommendations.

### 2.2 Severe Downside Tail Risk
- Agricultural commodity prices exhibit fat-tailed negative price shocks during seasonal price drops.
- For stored batches, the **5th percentile outcome is -₹232.36 / quintal (Validation)** and **-₹331.75 / quintal (Exploratory Test)**.
- Extreme worst-case losses identify acute downside tail risk in specific market partitions and cost scenarios:
  - Validation Partition: **-₹3,674.71 / quintal (Central)**, **-₹3,776.20 / quintal (Conservative)**.
  - Exploratory Test Partition: **-₹18,741.94 / quintal (Central)**, **-₹18,914.28 / quintal (Conservative)**.
- A hypothetical producer storing 10 quintals of produce would face downside losses of ₹2,300 to ₹3,300 at the 5th percentile, and acute tail losses several orders of magnitude higher during market crashes. Household cash-flow margins and liquidity preferences cannot be measured directly from APMC trade records, but the simulated loss magnitudes demonstrate severe downside tail risk.

---

## 3. Structural and Commodity Limitations

### 3.1 Commodity Heterogeneity
- **Wheat & Paddy (Cereals):** Weekly price volatility is relatively low ($\sigma \approx 10\%$). Storage costs (₹20/qtl) plus 1% shrinkage almost always exceed weekly price gains. The model policy achieves -₹0.22/qtl on Wheat; blind storage loses -₹44.41/qtl. Storing wheat for only 7 days is economically unviable under the tested tactical horizon and cost parameters in this sample.
- **Tomato & Green Vegetables (Perishables):** Highly perishable produce cannot be stored ambiently without substantial physical spoilage ($> 2\% - 5\%$ per week) and quality decay. Storing tomatoes produces negative average returns (-₹3.14 to -₹14.63/qtl).
- **Onion & Potato (Semi-Perishables):** Exhibit higher price swings, but require specialized climate-controlled cold storage. Off-mandi cold storage requires seasonal lock-in contracts, making 7-day tactical in-and-out holding physically unfeasible in rural UP.

### 3.2 Modal Prices vs Executable Realized Prices
- Mandi price archives report the daily **Modal Price** (the most frequently recorded transaction price in the APMC yard).
- Realized farmgate or mandi-gate prices depend heavily on:
  - Transaction timing within trading hours (morning transactions often command premiums over late-session sales).
  - Commission agent (*arhatiya*) cuts (typically 1.5% – 2.5%).
  - Local mandi taxes and cess (1% – 2%).
  - Unloading and porterage charges (*palledari*).
  - Subjective visual grading by buyers.
- Historical modal price appreciation cannot be interpreted as guaranteed executable profit.

### 3.3 Storage Access and Transaction Friction
- The model assumes frictionless storage availability at ₹20/quintal.
- In reality, public CWC warehouses primarily serve bulk procurement agencies and corporate depositors, not smallholders bringing 10 quintals on a tractor-trolley.
- Local rural private cold storages require transport to the facility, deposit fees, advance registration, and unloading charges that easily exceed ₹50–₹100/quintal for short-term holding.

### 3.4 Liquidity and Distress Selling Pressures
- Smallholder farmers frequently have urgent cash requirements at harvest time to repay informal moneylenders, pay harvest laborers, or meet household consumption needs.
- Holding produce for 7 days incurs an unmodeled liquidity stress that cannot be captured solely by a 7% KCC opportunity interest rate.

---

## 4. Test Partition Status

- The historical test window (May 9, 2026 to August 25, 2026) has been previously inspected during Phase 3 and Phase 4 research passes.
- It is explicitly treated as an **exploratory historical evaluation window**, NOT an untouched blind holdout.
- Decision policies and candidate model selections were strictly frozen on the Validation partition.
