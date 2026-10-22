# Validation & Execution Log: Phase 02 Crop Suitability

**Investigator:** Suryansh  
**Execution Timestamp:** 2026-10-23T00:54:00+05:30  
**Environment:** macOS (Darwin arm64)  
**Python Runtime:** Python 3.14.0 (pandas: 3.0.2, numpy: 2.4.4)  
**Workspace Directory:** `/Users/kumarsuryansh/Desktop/Temporary/suryansh - work`  
**Reference Repository:** `/Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction`  

---

## 1. Safety and Workspace Verification Commands Executed

### Step 1.1: Git Status of Upstream Clone
```bash
git status && git rev-parse --show-toplevel && git branch -a
```
- **Exit Code:** `0`
- **Output:**
  ```text
  On branch main
  Your branch is up to date with 'origin/main'.
  nothing to commit, working tree clean
  /Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction
  * main
    remotes/origin/HEAD -> origin/main
    remotes/origin/main
  ```
- **Verification:** Repository root confirmed; working tree clean; branch is strictly `main`.

### Step 1.2: Workspace Verification
```bash
ls -la "/Users/kumarsuryansh/Desktop/Temporary/suryansh - work"
```
- **Exit Code:** `0`
- **Verification:** Directory exists outside `Mandi_Prediction`; contains existing scaffolding and `README.md`.

### Step 1.3: Creation of Dedicated Phase 02 Directory
```bash
mkdir -p "/Users/kumarsuryansh/Desktop/Temporary/suryansh - work/reports/phase_02_crop_suitability"
```
- **Exit Code:** `0`
- **Verification:** Successfully created target directory for Phase 02 deliverables.

---

## 2. Python Scripts Executed

### Step 2.1: Candidate Crop Profiling Script
- **File Path:** `/Users/kumarsuryansh/Desktop/Temporary/suryansh - work/experiments/profile_candidate_crops.py`
- **Command:**
  ```bash
  python3 "/Users/kumarsuryansh/Desktop/Temporary/suryansh - work/experiments/profile_candidate_crops.py"
  ```
- **Exit Code:** `0`
- **Output Summary:**
  ```text
  Loading raw CSVs from /Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction/data/raw...
  Total raw records loaded: 160,192
  Columns present: ['Arrival_Date', 'Commodity', 'Commodity_Code', 'District', 'Grade', 'Market', 'Max_Price', 'Min_Price', 'Modal_Price', 'State', 'Variety', 'Source_File']
  Arrival quantity field detected: False (Note: Arrival_Date contains 'arrival' substring, but zero volume/quantity columns exist)

  --- Overall Dataset Overview ---
  Unique Commodities in raw: 130
  Candidate crops present in raw:
    - Potato: 8,084 raw rows
    - Onion: 7,792 raw rows
    - Tomato: 7,585 raw rows
    - Wheat: 12,070 raw rows

  Saved measured metrics to: /Users/kumarsuryansh/Desktop/Temporary/suryansh - work/reports/phase_02_crop_suitability/measured_crop_metrics.csv
  ```

---

## 3. Files Inspected

1. `Mandi_Prediction/README.md`
2. `Mandi_Prediction/FINAL_REPORT.md`
3. `Mandi_Prediction/T7_Feasibility_Report.md`
4. `Mandi_Prediction/data/docs/T7_Feasibility_Checklist.txt`
5. `Mandi_Prediction/backing/PROJECT_AUDIT.md`
6. `Mandi_Prediction/backing/phase_04/commodity_economic_breakdown.csv`
7. `Mandi_Prediction/backing/phase_05/commodity_market_heterogeneity.md`
8. `Mandi_Prediction/backing/phase_05/test_results.txt`
9. `Mandi_Prediction/src/data_loader.py`
10. `Mandi_Prediction/src/feature_engineering.py`
11. `Mandi_Prediction/src/models.py`
12. `Mandi_Prediction/src/evaluate.py`
13. `Mandi_Prediction/src/economic_model.py`
14. `Mandi_Prediction/src/intelligence_system.py`
15. `Mandi_Prediction/run_pipeline.py`
16. `Mandi_Prediction/data/raw/*.csv` (all 5 district files inspected for schema and row counts)

---

## 4. Blocked Actions, Data Downloads, and Policy Adherence

- **Data Downloads:** **Zero** external datasets were downloaded. Only official API schemas, sample endpoints, and documentation were surveyed, adhering strictly to Prompt 2 instructions.
- **Git Modifications:** **Zero** git modifications made to `/Users/kumarsuryansh/Desktop/Temporary/Mandi_Prediction`.
- **Package Installations:** **Zero** packages installed.
- **Model Training:** **Zero** training runs or feature ablations launched.

---

## 5. Instructions for Exact Reproduction

To reproduce all measurements reported in Phase 02:

```bash
# 1. Navigate to the Suryansh workspace
cd "/Users/kumarsuryansh/Desktop/Temporary/suryansh - work"

# 2. Run the profiling script
python3 experiments/profile_candidate_crops.py

# 3. Inspect generated metrics
cat reports/phase_02_crop_suitability/measured_crop_metrics.csv
```
