# Feature Selection & Ablation Results — Provisional Status

> [!WARNING]
> **PROVISIONAL STATUS — REQUIRES FRESH EXPERIMENT**  
> The results stored in this directory (`candidate_feature_selection_tests.csv`, `feature_ablation_overall_comparison.csv`, and `feature_ablation_crop_comparison.csv`) were computed prior to the Workstream C data foundation repairs.

### Identified Methodological Flaws in Prior Run:
1. **Row-Shift Weather Bug:** The weather lags in the original run were computed as `df.groupby('District')['Precipitation_mm'].shift(1)` directly on the multi-row price dataset (which contains multiple commodities and markets per district per date). As a result, `shift(1)` shifted across adjacent rows of different commodities/markets rather than a single calendar day.
2. **Missing Precipitation Conflation:** The NASA POWER fill value (-999.0) was previously mapped to `0.0 mm` (treating unmeasured days identically to verified dry days).
3. **Same-Day Diurnal Spread:** `Temp_Diurnal_Range` utilized same-day `Temp_Max_C - Temp_Min_C`, which is not available at morning APMC mandi trading cutoff.

### Required Next Action:
In accordance with Workstream C acceptance criteria, these ablation numbers must **not** be cited as empirical ground truth. They are retained strictly for audit traceability. A fresh experiment must be conducted with the repaired weather pipeline and split procedure before evaluating model performance.
