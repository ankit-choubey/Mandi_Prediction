# APMC Mandi Market Intelligence System
### District-Level Agricultural Market Condition Classification

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-1.8-orange.svg)](https://scikit-learn.org/)
[![Domain](https://img.shields.io/badge/Domain-Agriculture%20%26%20Mandi%20Fintech-green.svg)]()
[![Method](https://img.shields.io/badge/ML%20Task-Multi--Class%20Classification-purple.svg)]()

An end-to-end Machine Learning Market Intelligence System for agricultural wholesale mandis (APMC) across Uttar Pradesh. The system replaces noisy point price regression with an actionable **3-state market condition classification model** predicting whether future market conditions in **7 calendar days ($T+7$)** will be **Favorable**, **Normal**, or **Unfavorable**.

---

## 🌟 Key Highlights

- **The Problem Solved**: Replaced decimal point price regression (which fails due to daily agricultural volatility) with an actionable, reliable market condition advisory.
- **Feasibility Checklist Audited**: 100% compliance with `T7_Feasibility_Checklist.txt` (Sections A through O), verifying **75.24% exact calendar T+7 availability** (117,176 valid paired records).
- **Dedicated EDA Module**: Detailed statistical profiling across 5 districts, 42 mandis, 130 commodities, and 3 Indian crop seasons (*Kharif*, *Rabi*, *Zaid*).
- **Spatial Market Intelligence**: Leveraged price arbitrage signals across neighboring districts (Kanpur $\leftrightarrow$ Unnao $\leftrightarrow$ Lucknow).
- **Zero-Leakage Validation**: Strict chronological train (70%) / validation (15%) / test (15%) partitioning.
- **100% Pure Classification Suite**: Benchmarked **Decision Tree**, **Random Forest**, **Extra Trees**, **Gradient Boosting**, and a **Soft-Voting Ensemble** (zero regression algorithms).

---

## 📁 Repository Structure

```text
ML Project End Term/
│
├── data/
│   ├── raw/                             # Original 5 District APMC CSV files
│   │   ├── Gaziabaad.csv
│   │   ├── Jhansi.csv
│   │   ├── Kanpur.csv
│   │   ├── Lukhnow.csv
│   │   └── Unnao.csv
│   └── docs/                            # Original reference documentation
│       ├── District_Level_Project_Overview.pdf
│       └── T7_Feasibility_Checklist.txt
│
├── eda/                                 # Dedicated Exploratory Data Analysis
│   ├── eda_analysis.py                  # Standalone EDA execution script
│   ├── EDA_REPORT.md                    # Detailed statistical distributions & insights
│   └── plots/                           # 6 High-resolution EDA visual charts
│       ├── target_class_balance.png
│       ├── price_change_distribution.png
│       ├── top_commodities_volume.png
│       ├── district_price_comparison.png
│       ├── seasonal_price_dynamics.png
│       └── feature_correlation_heatmap.png
│
├── src/                                 # Core Modular ML Pipeline
│   ├── __init__.py
│   ├── data_loader.py                   # Data ingestion, deduplication, series filtering
│   ├── feasibility.py                   # T+7 Checklist Sections A-O automated audit
│   ├── feature_engineering.py           # 27 spatial & temporal features, T+7 target
│   ├── models.py                        # 100% pure classifiers & Soft-Voting ensemble
│   ├── evaluate.py                      # Chronological split, metrics & confusion matrices
│   └── intelligence_system.py           # District-level market advisory engine
│
├── results/                             # Model Visualizations & Artifacts
│   ├── system_workflow_diagram.png      # End-to-end pipeline flowchart
│   ├── model_performance_chart.png      # Test set comparison bar chart
│   ├── feature_importance_rf.png        # Feature ranking chart
│   ├── confusion_matrix_*.png           # Per-model confusion matrices
│   └── sample_engineered_features.csv   # Sample of processed features
│
├── reports/                             # Formal Output Reports
│   ├── FINAL_REPORT.docx                # Professional Word document (645 KB, embedded charts)
│   ├── FINAL_REPORT.md                  # Comprehensive Markdown final report
│   └── T7_Feasibility_Report.md         # Completed feasibility checklist report
│
├── run_pipeline.py                      # Master execution script (runs everything end-to-end)
├── convert_report_to_docx.py            # Word report compilation script
└── README.md                            # Repository documentation
```

---

## 🎯 Target Definition: What We Are Predicting

For any observation at Date $T$, the system predicts the market condition exactly **7 calendar days later ($T+7$)**:

$$\text{Percentage Change} = \left( \frac{\text{Modal Price}_{T+7} - \text{Modal Price}_T}{\text{Modal Price}_T} \right) \times 100$$

| Condition | Threshold | Meaning in Simple English | Farmer / Mandi Action |
|---|---|---|---|
| 📈 **Favorable** | $\Delta P \ge +2.5\%$ | Bullish market; prices trending upward. | Hold harvest or bring produce to capture premium rates. |
| ⚖️ **Normal** | $-2.5\% < \Delta P < +2.5\%$ | Steady, balanced daily market conditions. | Safe to harvest and sell on routine schedule. |
| 📉 **Unfavorable** | $\Delta P \le -2.5\%$ | Bearish market; significant price drop. | Warning to sell immediately or divert to nearby mandis. |

---

## 📊 Model Performance on Chronological Test Set

The models were evaluated on the held-out **chronological test set** (May 9, 2026 to August 25, 2026; 10,397 records) with zero lookahead leakage:

| Model Architecture | Test Accuracy | Precision (Macro) | Recall (Macro) | F1-Score (Macro) | F1-Score (Weighted) |
|---|---|---|---|---|---|
| **Decision Tree Classifier** | 49.34% | 49.28% | 48.51% | 0.4616 | 0.5090 |
| **Extra Trees Classifier** | 52.84% | 52.10% | 52.35% | 0.5052 | 0.5448 |
| **Random Forest Classifier** | 53.12% | 52.51% | **52.71%** | 0.5086 | 0.5490 |
| **Gradient Boosting Classifier** | **58.76%** | 52.87% | 51.69% | 0.5209 | **0.5832** |
| **Soft-Voting Ensemble** | 58.42% | **53.15%** | 52.40% | **0.5245** | 0.5826 |

* **Gradient Boosting** achieved the highest overall accuracy (58.76%).
* **Soft-Voting Ensemble** (combining Gradient Boosting, Random Forest, and Extra Trees) achieved the highest Macro Precision (53.15%) and Macro F1-Score (0.5245), providing maximum prediction consensus.
* **Random Forest** provided the highest balanced Macro Recall (52.71%), accurately detecting market breakouts.

---

## 🚀 Quickstart & Execution

### 1. Requirements
Ensure Python 3.9+ and required packages are installed:
```bash
pip install pandas numpy scikit-learn matplotlib seaborn python-docx
```

### 2. Run the Master Pipeline
To run the full workflow (EDA $\to$ Feasibility Audit $\to$ Feature Engineering $\to$ Model Training $\to$ Inferences $\to$ DOCX Generation):
```bash
python3 run_pipeline.py
```

### 3. Run Standalone Modules
* **Exploratory Data Analysis**:
  ```bash
  python3 eda/eda_analysis.py
  ```
* **Feasibility Audit (Sections A–O)**:
  ```bash
  python3 src/feasibility.py
  ```
* **Compile DOCX Report**:
  ```bash
  python3 convert_report_to_docx.py
  ```

---

## 📋 Sample Advisory Output

```text
╔══════════════════════════════════════════════════════════════════════╗
║               APMC MANDI MARKET INTELLIGENCE SYSTEM                  ║
║           District-Level Future Market Condition Advisory            ║
╚══════════════════════════════════════════════════════════════════════╝
  LOCATION & COMMODITY:
    • District           : Lucknow
    • Mandi / Market     : Banthara APMC
    • Commodity          : Wheat (Dara)
    • Observation Date   : 2026-08-25

  CURRENT MARKET STATUS (T):
    • Modal Price        : Rs. 2,625.54 / Quintal
    • Price Range        : Rs. 2,500.00 - 2,780.00 (Spread: Rs. 280.00)
    • 7-Day Rolling Avg  : Rs. 2,588.71
    • 7-Day Price Change : +1.24%
    • 7-Day Volatility   : Rs. 25.16

  REGIONAL & NEIGHBOURING INTELLIGENCE:
    • District Mean Price: Rs. 2,522.64 across 4 mandi(s)
    • Mandi Premium/Disc : +4.08% vs District Average
    • Neighbour Mean Price: Rs. 2,498.51
    • Neighbour Diff     : Rs. +127.03 (Higher than neighbours (Inflow likely))

  ----------------------------------------------------------------------
  EXPECTED T+7 MARKET CONDITION: >>> NORMAL <<<
  Confidence Probability: 47.47%
  Class Probabilities  : {'Unfavorable': 29.85, 'Normal': 47.47, 'Favorable': 22.68}
  Ground Truth Outcome : Normal (Actual: Rs. 2,686.69 [+2.33%])
  ----------------------------------------------------------------------
```

---

## 📄 License & Attribution
Developed for academic and applied research in agricultural market intelligence across APMC wholesale mandis in Uttar Pradesh.
