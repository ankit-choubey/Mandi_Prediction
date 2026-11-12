# MP-UI-002: Agricultural Price Research Instrument Interface

## 1. Executive Summary & Design System

The research web interface of the **APMC Mandi Intelligence System** has been elevated from a functional prototype into a professor-ready **Agricultural Price Research Instrument**. The visual language rejects both generic corporate administrative templates and fictional high-frequency trading terminals in favor of an **editorial field notebook, statistical report, and precision measurement instrument**.

### Visual Language & Aesthetic Tokens
- **Warm Paper Canvas**: Soft, low-fatigue paper backgrounds (`#fcfbf8` canvas, `#f6f3eb` card surface, `#ede8dc` borders and structural rules) reminiscent of agricultural bulletins and economic working papers.
- **Deep Ink Typography**: High-contrast, publication-grade ink (`#1a1c1e` primary text, `#475569` secondary captions) paired with classical system serif headers (`Charter`, `Georgia`, `Palatino`) and crisp system sans-serif data hierarchies (`-apple-system`, `BlinkMacSystemFont`, `Segoe UI`, `Roboto`).
- **Restrained Semantic Palette**:
  - **Crop Foliage Green** (`#235834`): Verified series and positive net benefits ($\Delta R > 0$).
  - **Turmeric Gold** (`#b36605`): Review series withheld, cautionary warnings, and model selection trade-offs.
  - **Soil Rust / Brick** (`#883a21`): Negative net benefits ($\Delta R < 0$), fail-closed advisory blocks, and empirical undercoverage.
  - **Slate Blue** (`#475569`): Retrospective benchmarks and structural metadata.
- **Tabular Numeral Alignment**: Every numerical figure uses `font-variant-numeric: tabular-nums` to guarantee strict vertical column alignment across scorecards, metrics grids, and breakdown tables.
- **Zero External Dependencies**: Zero npm packages, zero external CDNs, zero third-party fonts or trackers. 100% vanilla HTML5, CSS3, and ES6+ JavaScript. Total uncompressed client assets: **120.98 KB** across HTML, CSS, JS, and SVG favicon.

---

## 2. Order of Legibility Architecture

The interface structures the researcher and practitioner experience through six strict epistemic layers:

1. **What was actually observed**:
   - Primary hero card displaying exact Agmarknet modal price (e.g. ₹ 2,721.00 / quintal), reported min/max spread (₹ 2,670.00 – ₹ 2,750.00), and verified arrival date.
   - Relative observation age dynamically calculated in India Standard Time calendar days (e.g. `2 days old (India Calendar) (2026-11-11)`).
2. **How trustworthy and fresh that observation is**:
   - Real-time catalog status indicators (30 total tracked series: 26 accepted, 4 review-withheld).
   - Distinct, unbreachable card states for verified vs. review-withheld series (Baripaal Paddy hides all prices and displays clear unapproved market status).
   - Dataset mode badge (`Dataset mode (Imported snapshot)`) and expandable Reproducibility Drawer disclosing Git commit SHA, dataset SHA-256 (`45c9dd75...`), composite source SHA-256 (`3d3bc047...`), and standard-library runtime guarantees.
3. **What the frozen retrospective models achieved**:
   - Model Evidence Studio rendering audited out-of-sample benchmark metrics across 64,776 point origins.
   - Naive Persistence selected as primary winner on MAE (106.96 vs HGB 109.75 vs Ridge 110.32 INR/q).
   - HistGradientBoosting highlighted for RMSE variance reduction (281.16 vs 298.83 INR/q, 5.91% improvement).
   - Accessible CSS horizontal comparison bar charts anchored to an explicit zero-origin baseline (0 to 300 INR/q scale) with tabular numeric readouts so meaning is never conveyed by color alone.
4. **How uncertainty behaved across folds**:
   - Uncertainty Laboratory detailing empirical 90% prediction intervals across 26,918 evaluation origins.
   - Prominent 90% target reference graphic contrasting against realized out-of-sample coverage (50.81% overall).
   - Complete fold breakdown cards (Fold 2: 56.41%, Fold 3: 45.47%, Fold 4: 50.81%) with candid scientific disclosure of severe undercoverage caused by volatile agricultural price shocks.
5. **What the user-entered hold-versus-sell mathematics computes**:
   - Prominent research economics banner displaying accepted canonical equations ($R_{\text{sell}}$, $R_{\text{hold}}$, $\Delta R$, $P^*$).
   - Explicit distinction between observed prices transferred from the catalog (`OBSERVED_PRICE_TRANSFER`) and manual assumptions (`USER_ENTERED`).
   - One-click reference fixture preset verifying the canonical +470 INR fixture ($Q=10$, $P_0=2500$, $P_{\text{future}}=2650$, $C_s=1000$, $\Delta R=+470.00$, Break-even $P^*=2602.04$).
   - 10-step arithmetic waterfall decomposition table rendering the exact path from Gross Spot Value through Net Hold Benefit.
   - Carrying cost financing controls (7% annual rate yielding +436.44 INR) and conditional price range bounds (-20.00 / +470.00 / +960.00 INR).
   - Machine-readable receipt export generating cryptographic audit payloads.
6. **What is unavailable or still scientifically unproven**:
   - Fail-closed operational advisory blocked badge (`OPERATIONAL_ADVISORY_BLOCKED`).
   - System capability status panel disclosing `FORECAST_UNAVAILABLE` and `HISTORY_UNAVAILABLE_RESTRICTED`.
   - Truth-preserving price movement component displaying honest state: `Price change unavailable — a second verified observation is required.`
   - Commercial tariff disclosure explaining $0/22$ warehouse quotations received and zero synthetic proxies.
   - Comprehensive appendix detailing prospective Step 13 shadow validation prerequisites.

---

## 3. Responsive, Print & Accessibility Evidence

The interface was systematically validated across five viewport tiers and print media emulation using headless Chromium:

| Viewport Category | Resolution (CSS px) | Horizontal Overflow | Screenshot Artifact |
| :--- | :--- | :---: | :--- |
| **Desktop Ultra** | $1440 \times 900$ | **Zero** (`scrollWidth == clientWidth`) | `screenshot_desktop_1440x900.png` |
| **Desktop Standard** | $1280 \times 800$ | **Zero** (`scrollWidth == clientWidth`) | `screenshot_desktop_1280x800.png` |
| **Tablet Portrait** | $768 \times 1024$ | **Zero** (`scrollWidth == clientWidth`) | `screenshot_tablet_768x1024.png` |
| **Modern Smartphone** | $390 \times 844$ | **Zero** (`scrollWidth == clientWidth`) | `screenshot_mobile_390x844.png` |
| **Compact Smartphone** | $375 \times 667$ | **Zero** (`scrollWidth == clientWidth`) | `screenshot_mobile_375x667.png` |
| **Academic Print** | Emulated Print Page | Clean layout, hidden controls | `screenshot_print_preview.png` |

### Accessibility & Assistive Technology Highlights
- **Keyboard Navigation**: Full tab index hierarchy, WAI-ARIA tab list controls with ArrowLeft / ArrowRight keyboard navigation, and explicit `:focus-visible` ink rings.
- **Motion Reduction**: Comprehensive `@media (prefers-reduced-motion: reduce)` media query disabling all CSS transitions, animations, and smooth scrolling for motion-sensitive users.
- **Print Optimization**: High-contrast monochrome rules, interactive form controls/buttons automatically omitted (`display: none !important`), and research tables expanded for clean archival PDF generation.

---

## 4. Verification Gate Results

All test suites and review gates passed with 100% compliance:

- **UI002 End-to-End Browser Acceptance** (`experiments/reviews/test_ui002_browser_acceptance.js`): **24 / 24 passed**.
- **Interactive Browser Flows** (`experiments/reviews/test_interactive_browser_flows.js`): **21 / 21 passed**.
- **UI Static Asset Serving** (`tests/test_ui_serving.py`): **6 / 6 passed**.
- **APP-001A Review Gates** (`experiments/reviews/check_app001a_review_gates.py`): **29 / 29 passed**.
- **Release Integration Suite** (`tests/test_integration_release.py`): **10 / 10 passed**.
- **Full Test Suite** (`tests/`): **379 passed**, 18 mathematical warnings in 11.40s.
- **Backing Methodology Suite** (`backing/`): **45 passed**, 0 warnings in 5.14s.
- **Combined Test Count**: **424 passed**, 0 failures.

---

## 5. Milestone Accounting & Scope Integrity

- **Task Status**: MP-UI-002 complete.
- **Nature of Work**: Presentation refinement under accepted Step 11; does not alter underlying mathematical foundations or verified metrics.
- **Zero Retraining / Zero Synthetic Data**: Preserved all accepted models, benchmark scorecards, and calibration intervals.
- **Next Milestone**: **Step 13 (Prospective Shadow Validation & Usability)** remains the sole unfinished canonical research milestone. Optional engineering checks include Docker container smoke tests and arrivals/weather ablation explorations.
