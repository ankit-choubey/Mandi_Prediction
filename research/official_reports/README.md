# Official Post-Harvest Loss Studies & Government Reports Repository
## APMC Mandi Market Intelligence System — Reference Archive

**Directory:** `research/official_reports/`  
**Purpose:** Stores primary, unedited PDF copies of official government studies and institutional research reports on post-harvest losses and storage tariffs.

---

## 1. Verified Official Documents in this Folder

| File Name | Document Title & Issuing Authority | Publication Year | Verification Status | Source Link / Provenance |
|---|---|---|---|---|
| [`mofpi_post_harvest_loss_study.pdf`](mofpi_post_harvest_loss_study.pdf) | **Post Harvest Food Loss** (PIB Delhi, PRID 1885038), Ministry of Food Processing Industries (MoFPI), Government of India | 2022 | **VERIFIED & PRESENT** (126 KB) | Official Lok Sabha written reply by MoFPI Minister comparing ICAR-CIPHET (2015) & NABCONS (2022) |
| `mofpi_quantitative_loss_assessment.pdf` | **Assessment of Quantitative Harvest and Post Harvest Losses of Major Crops and Commodities in India**, ICAR-CIPHET / MoFPI | 2015 | Awaiting external download | Full technical volume (200+ pages) |
| `nabcons_report_001.pdf` | **Study to Determine Post-Harvest Losses of Agri Produce in India**, NABARD Consultancy Services (NABCONS) / MoFPI | 2022 | Awaiting external download | Full 54-commodity empirical survey report |
| `icar_ciphet_report_001.pdf` | **Post-Harvest Losses of Major Crops and Commodities in India**, ICAR-CIPHET Ludhiana | 2015 / 2022 | Awaiting external download | Research bulletin / technical study |

---

## 2. Key Loss Figures Extracted into `data/reference/crop_storage_parameters.csv`

| Crop Category | Specific Crop | ICAR-CIPHET (2015) Loss (%) | NABCONS (2022) Loss (%) | Calibrated 7-Day Physical Loss ($L$) | Quality Markdown ($d_q$) |
|---|---|---|---|---|---|
| **Cereals** | **Wheat** | 4.93% | 3.73% | 0.50% (7 days) | 0.0% (Stable) |
| **Cereals** | **Paddy / Rice** | 5.53% | 5.46% | 0.50% (7 days) | 0.0% (Stable) |
| **Vegetables** | **Potato** | 7.32% | 5.92% | 1.50% (7 days pro-rata) | 1.50% (Greening/bruising) |
| **Vegetables** | **Onion** | 8.20% | 7.02% | 3.50% (7 days chawl) | 2.50% (Sprouting) |
| **Vegetables** | **Tomato** | 12.44% | 11.61% | 8.00% (7 days ambient) | 6.00% (Softening/decay) |

*Full machine-readable ledger with page numbers, conditions, and duration available at [`data/reference/crop_storage_parameters.csv`](../../data/reference/crop_storage_parameters.csv).*
