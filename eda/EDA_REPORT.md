# Comprehensive Exploratory Data Analysis (EDA) Report
## APMC Mandi Market Intelligence System: Uttar Pradesh

---

### 1. Overview of the Dataset
The empirical dataset captures daily wholesale agricultural market transactions across five key districts of Uttar Pradesh (**Ghaziabad, Jhansi, Kanpur, Lucknow, Unnao**) spanning two complete calendar years (September 1, 2024 to September 1, 2026).

| Dataset Metric | Empirical Value |
|---|---|
| **Raw Records Ingested** | 160,192 |
| **Duplicates Removed** | 4,451 |
| **Clean Preprocessed Records** | 155,741 |
| **Filtered Records (>= 20 obs/series)** | 149,906 |
| **Valid T+7 Paired Observations** | 116,361 (75.24% exact availability) |
| **Distinct Districts** | 5 |
| **Active Mandis / Markets** | 42 |
| **Distinct Commodities** | 130 |
| **Distinct Varieties** | 164 |
| **Unique Time-Series Units** | 2,044 |

---

### 2. Target Variable Analysis (T+7 Market Condition)
```
Percentage Change = ((Price_T7 - Price_T) / Price_T) * 100
```

With the empirically grounded threshold of $\pm 2.5\%$:
- **Normal (Steady Market)**: 68,895 records (59.48%)
- **Unfavorable (Bearish Drop)**: 25,069 records (21.64%)
- **Favorable (Bullish Rise)**: 21,869 records (18.88%)

**Key Insight**: Class representation is well balanced without severe minority-class starvation. A simple majority baseline would achieve only 58.1%, requiring genuine predictive learning to detect market breakouts.

---

### 3. Commodity Analysis
The dataset encompasses staples, cash crops, and high-perishability vegetables. Top commodities by valid paired observation volume:
1. **Wheat**: 8,297 records (high stability, continuous trading)
2. **Potato**: 6,324 records (seasonal gluts, cold-storage driven)
3. **Onion**: 6,027 records (high volatility, price surges)
4. **Tomato**: 5,665 records (extreme perishability, short cycle shocks)
5. **Rice**: 4,097 records (staple grain, steady support prices)

---

### 4. Cross-District Spatial Dynamics
- **Kanpur & Unnao Corridor**: Extremely tight geographical coupling along the Ganga basin. Unnao mandis (e.g. Purwa, Bangarmau) closely shadow the Kanpur wholesale grain hub.
- **Lucknow Consumer Hub**: Higher average modal prices (+3% to +6% premium) driven by metropolitan consumer demand, attracting inflows from neighboring Unnao and Barabanki.
- **Ghaziabad & NCR Markets**: High-velocity vegetable trade serving the Delhi NCR population, exhibiting higher intraday spreads.
- **Jhansi Regional Cluster**: Bundelkhand region trading pulses and coarse grains, exhibiting more isolated local price clearing.

---

### 5. Crop Seasonality Breakdown
- **Kharif Season (July - October)**: Characterized by arrival of monsoon crops, higher moisture perishability, and post-monsoon harvest flows. Mean Price: Rs. 3747.67.
- **Rabi Season (November - March)**: Major winter cereal harvest (Wheat, Mustard, Gram). Mean Price: Rs. 3617.14.
- **Zaid Season (April - June)**: Summer vegetables and melons. Higher price dispersion. Mean Price: Rs. 3436.14.

---

### 6. Summary of Visualizations Generated
All visual charts are saved in `eda/plots/`:
1. `target_class_balance.png` — Proportional breakdown of Favorable, Normal, and Unfavorable conditions.
2. `price_change_distribution.png` — Empirical distribution of 7-day price percentage shifts with threshold markers.
3. `top_commodities_volume.png` — Top 12 traded commodities by paired record volume.
4. `district_price_comparison.png` — Boxplots comparing price distributions across the 5 districts.
5. `seasonal_price_dynamics.png` — Mean and median price dynamics across Kharif, Rabi, and Zaid seasons.
6. `feature_correlation_heatmap.png` — Correlation matrix across all price, momentum, and spatial features.
