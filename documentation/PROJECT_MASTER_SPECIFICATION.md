# Mandi Prediction
## Master Project Specification and Implementation Roadmap

**Document type:** Master project specification  
**Project:** Mandi Prediction  
**Repository:** `ankit-choubey/Mandi_Prediction`  
**Primary owner:** Ankit Choubey  
**Quality target:** Academically defensible and production-oriented  
**Documentation audience:** Academic evaluators, technical reviewers, future developers, and AI coding agents  
**Initial geographic scope:** Ghaziabad, Jhansi, Kanpur, Lucknow, and Unnao, Uttar Pradesh  
**Document status:** Proposed master specification — pending repository-owner approval

---

# PART I — PROJECT MASTER SPECIFICATION

## 1. Executive Summary

Mandi Prediction is an agricultural market intelligence and farmer decision-support project designed to help users understand historical mandi prices, examine current reported prices, evaluate future price movements, and eventually compare alternative selling decisions.

The project is not simply a price-prediction notebook, classification model, or data-visualisation dashboard.

Its intended development has two major releases:

### Release 1: Market intelligence and evaluated forecasting

The first release will provide:

- Latest verified reported mandi prices for supported market–commodity combinations.
- Historical price trends.
- Forecasts for selected commodities and markets.
- Forecast uncertainty wherever it can be estimated and validated.
- Historical model-performance evidence.
- Source, observation date, freshness, and data-quality information.
- Clear explanations when data or a forecasting capability is unavailable.

### Release 2: Qualified economic decision support

The second release will introduce, subject to evidence and validation:

- Alternative mandi comparisons.
- Sell-now versus wait comparisons.
- Storage-versus-immediate-sale comparisons.
- Estimated net proceeds after relevant costs and losses.
- Sensitivity analysis for uncertain inputs.
- Eligibility and safety checks before displaying actionable guidance.

The system must never equate a predicted increase in market price with a recommendation to store agricultural produce.

## 2. Problem Statement

Farmers and agricultural stakeholders need understandable information about market prices and the potential financial consequences of selling at different times or markets.

Historical price records alone do not answer all relevant questions:

- What is the latest reported price for a particular commodity and market?
- How has that price changed over time?
- What price might be observed at a specified future horizon?
- How reliable has the forecasting system been historically?
- What uncertainty surrounds a forecast?
- Would transporting produce to another mandi improve expected net proceeds?
- Would storing a crop produce a better financial outcome after storage losses, handling costs, transport, financing, and other relevant expenses?

Mandi Prediction aims to build a traceable information and decision-support system that addresses these questions progressively.

The system must communicate uncertainty and data limitations instead of creating an impression of certainty that the evidence cannot support.

## 3. Project Objectives

### 3.1 Primary objectives

1. Establish a reliable historical and current mandi-price data foundation.
2. Build reproducible data-ingestion and validation workflows.
3. Analyse price behaviour across selected markets and commodities.
4. Evaluate forecasting methods using appropriate time-series validation.
5. Develop a usable application for accessing supported market information.
6. Quantify forecasting performance and limitations.
7. Build a separate, evidence-based economic decision engine.
8. Maintain complete technical and research documentation.

### 3.2 Academic objectives

- Conduct a structured literature review.
- Identify appropriate statistical and machine-learning methods.
- Establish meaningful baseline comparisons.
- Use leakage-resistant evaluation.
- Analyse model errors and differences across markets and commodities.
- Report negative results and limitations.
- Make experiments reproducible.
- Support conclusions with traceable evidence.

### 3.3 Engineering objectives

- Maintain modular, understandable code.
- Separate raw data, processed data, models, APIs, and presentation layers.
- Establish explicit interfaces between system components.
- Implement automated validation and testing.
- Maintain versioned experiment configurations and artefact manifests.
- Provide reliable application behaviour when data sources or models are unavailable.
- Establish deployment and maintenance procedures.

## 4. Scope and Geographic Coverage

### 4.1 Initial geography

The documented initial scope is limited to these five districts:

1. Ghaziabad
2. Jhansi
3. Kanpur
4. Lucknow
5. Unnao

The application must not imply complete Uttar Pradesh coverage.

### 4.2 Commodity coverage

The repository has previously been reported to contain approximately 130 commodities across its broader historical price collection. That number must be reverified against the current repository and validated data.

Initial candidate commodities for focused investigation include:

- Wheat
- Potato
- Onion
- Tomato
- Paddy
- Rice

Paddy and rice must remain separate where the source distinguishes them.

The actual supported commodity list must be selected using:

- Historical observation coverage.
- Market coverage.
- Data completeness.
- Consistency of commodity identity.
- Sufficient observations for evaluation.
- Practical relevance.
- Availability of supporting information for the intended product features.

The project must not promise forecasting for every commodity simply because historical records exist.

### 4.3 Market coverage

The system must maintain explicit market identities.

Market aliases may be mapped only where evidence supports the equivalence. Similar market names must not automatically be treated as identical.

Each supported market should have a stable internal identifier and documented source identity.

## 5. User Groups

The intended user groups are:

### Farmers

Need understandable price information, historical trends, and eventually qualified selling-decision support.

### Traders and agricultural market participants

May use historical trends and comparisons between supported markets.

### Researchers and academic evaluators

Need access to methods, datasets, experimental design, performance results, and limitations.

### Project administrators and developers

Need tools for monitoring data freshness, validation failures, model versions, and system reliability.

These are intended user groups. Actual usability and usefulness must be established through testing and stakeholder feedback.

## 6. Product Requirements

### 6.1 Release 1 — Functional requirements

**FR-001: Commodity selection**

Users must be able to select a supported commodity.

**FR-002: Market selection**

Users must be able to select a supported mandi or market.

**FR-003: Latest reported price**

The application must display the latest verified reported price for the selected market and commodity.

The display must include:

- Modal price.
- Price unit.
- Observation date.
- Market name.
- Commodity name.
- Source or source reference.
- Freshness status.

The system must not silently replace unavailable data with another market's observation.

**FR-004: Historical trends**

Users must be able to examine historical price observations over a selectable period.

The application must clearly distinguish missing observations from zero prices.

**FR-005: Forecast display**

The application must display forecasts only for supported combinations and approved models.

Each forecast must identify:

- Forecast issue date.
- Target date.
- Forecast horizon.
- Predicted price and unit.
- Model identifier and version.
- Relevant uncertainty information.
- Evaluation status.

**FR-006: Model performance transparency**

Users and reviewers must be able to inspect the historical evaluation results supporting the forecasting capability.

**FR-007: Data availability**

The application must display appropriate messages when observations are missing, stale, invalid, or unsupported.

**FR-008: Data-quality status**

The application must distinguish validated data from data that is incomplete or under investigation.

**FR-009: Historical versus forecast distinction**

Historical observations and model-generated forecasts must be visually and semantically distinguishable.

**FR-010: Unsupported combinations**

The system must not fabricate forecasts for unsupported commodity–market combinations.

### 6.2 Release 2 — Economic decision-support requirements

**FR-011: Alternative market comparison**

Compare expected net proceeds across supported markets using relevant transport and transaction costs.

**FR-012: Sell-now versus wait**

Compare immediate sale proceeds with estimated future sale proceeds, accounting for the uncertainty and applicable costs.

**FR-013: Storage comparison**

Compare immediate sale with storage followed by future sale, using validated crop-specific storage assumptions and cost inputs.

**FR-014: Sensitivity analysis**

Allow the economic result to be examined under different price, cost, loss, and duration assumptions.

**FR-015: Decision eligibility**

Do not produce an actionable storage suggestion when crop suitability, storage availability, cost information, or other required inputs are missing.

**FR-016: Explanation**

Every economic comparison must expose its assumptions, calculation method, input dates, and limitations.

## 7. Non-Functional Requirements

### Reliability

- Missing data must not cause fabricated output.
- Failed model execution must not be represented as a successful forecast.
- Source failures must be recorded.
- The application must handle unavailable external services gracefully.

### Reproducibility

- Data versions must be identifiable.
- Experiment configurations must be retained.
- Random seeds must be recorded where applicable.
- Training and evaluation procedures must be documented.
- Important artefacts must have checksums or equivalent integrity records.

### Maintainability

- Separate ingestion, validation, feature generation, modelling, API, and UI responsibilities.
- Avoid unnecessary duplication.
- Keep data transformations documented.
- Use explicit configuration rather than hidden assumptions.

### Usability

- Use understandable terminology.
- Display units and observation dates.
- Avoid unexplained model scores.
- Make unavailable or uncertain information clear.
- Design for mobile use as an important target, subject to usability testing.

### Security

- Never commit API credentials or passwords.
- Do not expose private Kaggle credentials.
- Do not publish identifiable interview information without appropriate permission.
- Validate files before loading model artefacts.
- Use appropriate authentication and access controls if private administrative features are introduced.

### Performance

Performance targets must be established after the first application architecture and representative data volumes are measured. Do not invent latency or availability guarantees before benchmarking.

## 8. Data Strategy and Governance

### 8.1 Data categories

The project may use the following data categories:

1. Historical mandi prices.
2. Daily or otherwise appropriately granular arrivals.
3. Weather observations.
4. District-level agricultural production statistics.
5. Storage tariffs and crop-storage parameters.
6. Transport and handling costs.
7. Research reports and academic literature.
8. Stakeholder research, subject to consent and privacy requirements.

Not every category is mandatory for every model.

A feature must not be included merely because it is available. Its temporal availability, reliability, relevance, and potential leakage must be examined.

### 8.2 Data-source register

Each source must have a record containing:

- Source identifier.
- Organisation.
- Dataset or resource name.
- Original URL or API endpoint.
- Download timestamp.
- Coverage period.
- Geographic coverage.
- Commodity coverage.
- Units and field definitions.
- Licence and usage restrictions.
- File path.
- Checksum.
- Processing history.
- Known limitations.
- Verification status.

### 8.3 Source verification states

Use these states consistently:

- VERIFIED: checked against the original source and relevant quality requirements.
- PARTIALLY VERIFIED: some checks passed, but relevant coverage or quality checks remain.
- UNVERIFIED: source or data quality has not been sufficiently established.
- RESTRICTED: access or usage conditions restrict intended use.
- NOT AVAILABLE: the required source or evidence has not been obtained.
- ASSUMPTION: an explicitly documented modelling or scenario assumption, not an observed measurement.

### 8.4 Series identity rule

A distinct agricultural market price series is defined strictly by the natural tuple:
$$\text{Series Identity} = (\text{Source Market}, \text{Commodity}, \text{Variety}, \text{Grade}, \text{Price Unit})$$
*(e.g. `Kanpur Grain + Wheat + Dara + FAQ + INR/Quintal`)*

Rules:
- Preservation of Grade in series identity is mandatory to prevent collapsing distinct quality and price tiers occurring on the same market date.
- Aggregation across markets, varieties, or grades into a composite district series is permitted only under an approved, documented, and tested weighting or averaging rule. Series must never be silently or arbitrarily collapsed.

### 8.5 Ingestion and publication contract

All automated and batch data ingestion workflows must comply with the following architectural contract:
1. **Immutable Raw Archive:** Raw source files in `data/raw/`, `5 year dataset/`, and external arrival archives are read-only and permanently preserved.
2. **Separate Input and Output Paths:** Output files must never be written into the directory scanned for raw inputs.
3. **No Re-Reading of Generated Outputs:** Ingestion pipelines must explicitly isolate raw inputs so generated city-crop files are never re-read on subsequent runs.
4. **Deterministic Reruns:** Executing ingestion multiple times on the same input data must yield bit-for-bit identical outputs without duplicate accumulation.
5. **Revision History & Integrity Tracking:** Changes to published tables must be accompanied by versioned manifest entries with cryptographic checksums. Checksums verify local file integrity, not origin authenticity.
6. **Pagination-Completion Evidence:** Network API ingestion must record page counts, records fetched per page, and end-of-feed markers before marking retrieval as complete.
7. **Atomic Publication:** Staging datasets must be validated completely before atomic publication (e.g. atomic file swap) to ensure downstream consumers never read partially written or corrupted states.
8. **Distinct Timestamp Contract:** Systems must distinctly separate and record:
   - `observation_time`: When the transaction physically occurred at the mandi.
   - `retrieval_time`: When the record was fetched over the network from the upstream provider.
   - `processing_time`: When the record was validated and normalized.
   - `publication_time`: When the artifact was committed and published for consumption.

### 8.6 Scenario cost policy

All cost, tariff, freight, and post-harvest deterioration parameters in economic comparisons must adhere to the scenario cost policy:
1. **`SCENARIO_ASSUMPTION` Class:** Every unverified cost, loss, or tariff input must be explicitly tagged as `SCENARIO_ASSUMPTION`.
2. **Range:** Must specify a low, base, and high range.
3. **Anchor:** Must cite an authoritative published anchor document (e.g. MoFPI/NABCONS 2022, ICAR-CIPHET 2015, statutory CWC tariffs).
4. **Empirical Override:** Scenario assumptions must be overridden immediately when verified actual quotes from active local facilities or haulage surveys are obtained.
5. **Operational Safety Gating:** If any parameter in a net-proceeds evaluation relies on a `SCENARIO_ASSUMPTION`, downstream application outputs must be strictly capped as `INFORMATIONAL / DEMO MODE ONLY`. Actionable farmer storage advice is blocked by the recommendation safety gate.
6. **Synthetic Data Constraint:** Synthetic data is strictly permitted for labelled scenario cost assumptions only; synthetic prices, synthetic arrivals, and synthetic production data are strictly forbidden in empirical modeling.

### 8.7 Data integrity rules

- Preserve original source files.
- Never overwrite raw source files with processed outputs.
- Maintain source checksums. Checksums prove file integrity, not origin authenticity; authenticity requires signed receipts or direct query logs.
- Separate raw, intermediate, processed, and reference data.
- Record every important transformation.
- Keep synthetic or generated data out of empirical evaluation unless explicitly labelled and used only for a clearly defined test.
- Keep quarantined data quarantined until independently approved.
- Do not invent missing source records.
- Do not assume a catalogue's update date is the date of its latest observation.

### 8.8 Data-quality checks

Every major dataset must undergo:

- Schema validation.
- Date validation.
- Duplicate detection.
- Unit validation.
- Missingness analysis.
- Value-range checks.
- Geographic identity checks.
- Commodity and variety identity checks.
- Coverage analysis.
- Source-to-processed reconciliation.
- Temporal consistency checks.

Suspicious observations should be flagged and investigated rather than automatically deleted.

### 8.6 Temporal availability and leakage

Every feature must be evaluated according to when it would actually have become available to a prediction system.

A variable that is recorded for a future target date cannot be used as a feature at an earlier forecast issue date unless a legitimate forecast or known-ahead source exists.

This applies particularly to arrivals, weather, production revisions, and other externally collected variables.

## 9. Forecasting Methodology

### 9.1 Forecast target

The first price-forecasting target should be defined as the reported modal mandi price for a specific commodity–market series at a specified future date or horizon.

The exact target definition must specify:

- Price field.
- Price unit.
- Market identity.
- Commodity identity.
- Observation-date treatment.
- Missing-date treatment.
- Forecast issue date.
- Target date.
- Forecast horizon.

The existing T+7 classification task must be documented separately.

### 9.2 Existing classifier

The existing implementation has previously been reported as a T+7 market-condition classifier.

It must be inspected and documented before any modification.

Its output classes and probabilities must not be presented as continuous rupee-price predictions or price prediction intervals.

The classifier may be retained if its methodology, performance, and intended use are defensible.

### 9.3 Candidate forecasting baselines

Evaluate simple baselines before complex models:

- Last-observation naive baseline.
- Seasonal naive baseline, where seasonal structure is justified.
- Moving-average baseline.
- Suitable statistical time-series models.
- Suitable machine-learning models, such as Random Forest or gradient boosting.

Candidate methods are not mandatory winners. Their suitability must be established empirically.

### 9.4 Evaluation design

Use chronological validation and walk-forward backtesting.

The evaluation protocol must specify:

- Training window.
- Validation window.
- Test window.
- Forecast origin.
- Forecast horizon.
- Retraining frequency.
- Missing-observation treatment.
- Baseline comparison.
- Model-selection procedure.

Random row-level splitting must not be used as the primary evidence for future forecasting performance.

### 9.5 Evaluation metrics

Consider:

- MAE.
- RMSE.
- WAPE or an appropriate aggregate metric.
- MAPE only where its mathematical limitations are addressed.
- Directional accuracy where direction prediction is relevant.
- Prediction interval coverage and width where uncertainty intervals are provided.

Report results:

- Per commodity.
- Per market.
- Per forecast horizon.
- Across time periods.
- Against baseline models.

Do not report only a single aggregate accuracy number.

### 9.6 Model approval

A model may be approved for application use only after:

1. Its data pipeline is validated.
2. Its evaluation is leakage-resistant.
3. It is compared against suitable baselines.
4. Its errors have been analysed.
5. Its limitations are documented.
6. Its intended deployment inputs are available at prediction time.
7. Its inference output is reproducible.

A model that fails to outperform a reasonable baseline should not automatically be selected.

### 9.7 Uncertainty

Forecast uncertainty must be evaluated rather than added decoratively.

Where intervals are presented, document:

- Interval construction method.
- Nominal coverage.
- Empirical coverage.
- Interval width.
- Evaluation period.
- Limitations.

Do not label a model's classification probabilities as price uncertainty.

### 9.8 Prospective logging and abstention reporting

To guarantee leakage-free evaluation and evaluate true real-time performance:
1. **Prospective Logging:** Forecast predictions must be timestamped, logged, and cryptographically preserved before the outcome window opens (before observation date $T+h$ physically occurs).
2. **Abstention Reporting:** When models abstain from predicting due to stale data (> 5 days lag), out-of-distribution inputs, missing series history, or safety gate blocks, the exact abstention reason and coverage rate must be logged and reported alongside accuracy metrics. Evaluating accuracy solely on the predicted subset without reporting abstention coverage is academically invalid.

## 10. Economic Decision Methodology

Forecasting and economic decision support are separate components.

A forecast estimates a future price. The decision engine estimates financial outcomes using price information, quantities, losses, costs, and constraints.

### 10.1 Immediate sale

A simplified formulation is:

N_sell = Q × P_now − C_immediate

Where:

- Q is the saleable quantity.
- P_now is the applicable current sale price.
- C_immediate includes applicable immediate costs.

### 10.2 Storage and later sale

A simplified formulation is:

N_store = Q × (1 − L) × P_future − C_storage − C_handling − C_transport − C_finance − C_other

Where:

- Q is the starting quantity.
- L is a clearly defined proportional quantity loss.
- P_future is the expected future sale price.
- C_storage is the storage cost.
- Other costs represent applicable expenses.

If quality loss affects the achievable sale price separately from physical quantity loss, it must be modelled separately.

Do not count the same deterioration twice.

### 10.3 Required checks

Before presenting storage comparisons, check:

- Crop suitability.
- Storage type.
- Storage duration.
- Storage availability.
- Crop-specific loss evidence.
- Applicable tariff.
- Transport costs.
- Handling and loading costs.
- Financing and opportunity costs where relevant.
- Future market access.
- Relevant quality deterioration.

National cumulative post-harvest loss estimates must not be converted mechanically into weekly storage-loss assumptions.

### 10.4 Uncertainty and sensitivity

The economic engine must examine how conclusions change under plausible variations in:

- Future market price.
- Quantity loss.
- Quality deterioration.
- Storage duration.
- Storage tariffs.
- Transport expenses.
- Financing costs.

The system must distinguish an estimated outcome from a guaranteed financial result.

### 10.5 Decision safety

If required evidence is missing, display an informational comparison or an explicit unavailable status rather than an unsupported recommendation.

The project must not claim that its recommendations guarantee profit or eliminate market risk.

## 11. System Architecture

The architecture must be selected after inspecting the existing repository and implementation.

The target logical components are:

1. Data acquisition.
2. Raw data storage.
3. Data validation.
4. Data processing and feature generation.
5. Forecasting and evaluation.
6. Model artefact management.
7. Forecast inference.
8. Economic calculation engine.
9. Backend/API.
10. Frontend application.
11. Monitoring and reporting.

### 11.1 Separation of responsibilities

- Kaggle is the designated environment for heavy computation.
- Local development is used for editing, orchestration, and lightweight bounded checks.
- The deployed application requires a separately approved serving environment.
- Kaggle must not be assumed to provide an always-on production API.
- The application must not depend on a manually opened notebook for routine serving.

### 11.2 API and data contracts

The API specification must define:

- Supported markets.
- Supported commodities.
- Latest-price response.
- Historical-series response.
- Forecast response.
- Data-quality and freshness metadata.
- Unsupported-series responses.
- Error responses.
- Model-version information.

All returned price values must include units and observation or target dates.

### 11.3 Model artefacts

A deployed model must have:

- Model identifier.
- Model version.
- Training-data version.
- Preprocessing version.
- Feature specification.
- Training configuration.
- Evaluation report.
- Inference contract.
- Artefact checksum.

Model and preprocessing artefacts must be version-compatible.

### 11.4 Serving options and model deployment architecture

The application serving layer must adhere to the following constraints:
1. **Serving Options:**
   - *Precomputed batch forecasts:* Forecasts generated during scheduled batch runs on Kaggle or offline workers, validated through safety gates, and stored for fast key-value lookups.
   - *Lightweight hosted model inference:* Real-time inference using lightweight, versioned pipelines (e.g. tree classifiers or regression baselines) loaded from verified checkpoints.
2. **Zero Request-Time Retraining:** Models must never be trained, fitted, or fine-tuned in response to user requests or real-time web traffic.
3. **Version-Mismatch Handling:** When the deployed model version does not match the active feature matrix schema, or if required features are missing, the system must fail safe, emit a clear version-mismatch explanation, and refuse to serve unvalidated predictions.

## 12. Compute and Experimentation Policy

### 12.1 Heavy computation

Kaggle is required for:

- Full-panel profiling.
- Large joins and reconciliations.
- Expensive feature generation.
- Model training and retraining.
- Hyperparameter search.
- Full walk-forward backtesting.
- Large-scale inference.
- Bootstrap and robustness experiments.
- Large-scale calibration experiments.

### 12.2 Permitted local tasks

Local work is permitted for:

- Repository inspection.
- Code editing.
- Small fixture-based tests.
- Static analysis.
- Lightweight metadata inspection.
- Kaggle CLI orchestration.
- Approved artefact downloads.
- File-integrity checks.
- Clearly lightweight inference tests.

If a workload's resource demand is uncertain, do not attempt the heavy workload locally.

### 12.3 Kaggle experiment requirements

Each approved experiment must record:

- Experiment identifier.
- Task identifier.
- Approval reference.
- Notebook or kernel identifier.
- Notebook version.
- Dataset identifiers and versions.
- Checksums where available.
- Environment and dependencies.
- Resource configuration.
- Random seeds.
- Submission and completion timestamps.
- Logs.
- Metrics.
- Relevant predictions.
- Relevant charts.
- Model and preprocessing artefacts, if required.
- Output manifest.
- Download and verification status.

A successful Kaggle job status alone does not establish scientific validity.

Downloaded artefacts must be inspected and verified before use.

Large temporary artefacts should not automatically be committed to Git.

## 13. Testing Strategy

### Unit testing

Test:

- Data parsing.
- Unit conversion.
- Date handling.
- Market mapping.
- Commodity mapping.
- Price calculations.
- Forecast response formatting.
- Economic calculations.

### Integration testing

Test:

- Ingestion to processed-data flow.
- Processed data to model inference.
- Model inference to API.
- API to frontend.
- Data freshness and failure handling.

### Model testing

Test:

- Reproducibility.
- Baseline comparisons.
- Leakage prevention.
- Missing-data behaviour.
- Series-specific evaluation.
- Inference consistency.

### Economic testing

Test:

- Immediate sale calculations.
- Storage calculations.
- Unit conversions.
- Loss handling.
- Cost aggregation.
- Sensitivity analysis.
- Missing-input rejection.
- Double-counting prevention.

### Application acceptance testing

Test representative supported and unsupported combinations, stale records, missing records, model failures, and unavailable services.

The testing report must identify exactly which tests passed, failed, or were not run.

## 14. Security, Privacy and Responsible Use

- Never commit secrets.
- Never print credentials in logs.
- Keep private participant information out of public repositories.
- Obtain appropriate consent before collecting stakeholder information.
- Keep interview identifiers anonymous in public outputs.
- Check data-source licensing and redistribution conditions.
- Validate downloaded files and model artefacts.
- Document assumptions and limitations.
- Do not create fabricated evidence or results.
- Do not represent forecasts as guaranteed future prices.
- Do not represent informational outputs as personalised financial guarantees.

## 15. Monitoring and Maintenance

The eventual deployed system should monitor:

- Data-source availability.
- Latest observation date.
- Ingestion failures.
- Schema changes.
- Data-quality failures.
- Model version.
- Forecast generation failures.
- Prediction errors when actual outcomes become available.
- Application errors.
- API response performance.

Retraining must follow a documented policy, not an arbitrary schedule.

Model degradation should be measured before changing the production model.

## 16. Academic Research Requirements

The research component must include:

- Literature review.
- Dataset and source descriptions.
- Data preparation methodology.
- Feature definitions.
- Model selection rationale.
- Experimental design.
- Baseline comparisons.
- Results.
- Error analysis.
- Limitations.
- Ethical and responsible-use considerations.
- Reproducibility information.

A literature review must be based on papers actually located and reviewed. Abstract-only reading must be identified as such.

The project must not invent papers, metrics, interviews, source permissions, or experimental results.

## 17. Final Project Deliverables

The completed project should produce:

1. Working market-intelligence application.
2. Reproducible data acquisition and processing workflows.
3. Audited and documented datasets.
4. Data dictionaries and reference tables.
5. Dataset provenance and licensing records.
6. Data-quality reports.
7. Reproducible forecasting experiments.
8. Baseline and model-comparison reports.
9. Forecast uncertainty evaluation.
10. Versioned model and preprocessing artefacts.
11. Documented API and application architecture.
12. Economic decision-support engine, once qualified.
13. Storage and transport evidence register.
14. Complete technical documentation.
15. Academic literature review.
16. Automated testing suite.
17. Deployment and operations guide.
18. Demonstration scenarios.
19. Stakeholder feedback evidence, if a pilot is conducted.
20. Final academic project report and presentation.

---

# PART II — VERIFIED REPOSITORY BASELINE

## 18. Verified Repository Baseline Snapshot

**Audit Reference:** Tasks MP-AUDIT-001 & MP-AUDIT-001R  
**Audit Timestamp:** 2026-11-12T02:10:00+05:30 (Asia/Kolkata)  
**Audit Commit SHA:** `82a0e8bb423d1e6a7b9e7a197d6e0441ffd903b3` (on `main`)  
**Commit Message:** `feat(data): add CEDA Ashoka historical price and quantity arrivals dataset for Wheat`  

### 18.1 Empirical Dataset & Verification Ledger (Reported by Audit)

| Dataset / Component | File Path | Raw Rows | Unique Commodities | Date Range | Audit Status |
|---|---|---|---|---|---|
| **2-Year Raw Price Panel** | `data/raw/*.csv` (5 files) | **160,192** | **130** | 2024-09-01 to 2026-09-01 | **VERIFIED (reported by audit)**; 100% key subset of 5-yr |
| **5-Year Raw Price Panel** | `5 year dataset/*.csv` (5 files) | **472,385** | **139** | 2021-09-01 to 2026-09-30 | **VERIFIED (reported by audit)**; authoritative historical raw |
| **Published Validated Panel** | `data/processed/mandi_5year_validated.csv` | **462,350** | **108** | 2021-09-01 to 2026-09-30 | **VERIFIED (reported by audit)**; Strategy 2 cleaned & filtered |
| **Single-Day Nationwide Snapshot** | `data/raw_external/9ef84268...csv` | **11,720** | **201** | 2026-11-11 | **VERIFIED (reported by audit)**; unauthenticated OGD dump |
| **Automated Test Suite** | `tests/` (12 modules) | **122 tests** | — | — | **VERIFIED (reported run)**; 122 passed in 3.81s |

### 18.2 Categorised Baseline Evidence

1. **Remote Baseline (`origin`):**
   * Remote URL: `https://github.com/ankit-choubey/Mandi_Prediction.git`.
   * Verified by `git ls-remote --heads origin`: Exposes **only one branch: `refs/heads/main`** at commit `82a0e8bb423d1e6a7b9e7a197d6e0441ffd903b3`.
   * The `dev` branch does not exist on remote GitHub (consolidated into `main` via merge commit `a4ef191`), explaining HTTP 404 errors encountered by external connectors explicitly querying `dev`.
2. **Local Baseline:**
   * Working branch is `main` pointing to commit `82a0e8bb423d1e6a7b9e7a197d6e0441ffd903b3`.
   * All tracked files match HEAD cleanly.
   * Untracked local files exist and are strictly preserved: `data/manifests/`, `documentation/` (IMD references), local CEDA downloads, DES production data, and storage survey quotation templates.
3. **Executed Evidence:**
   * Automated test suite executed under Python 3.14.0 on macOS Darwin arm64.
   * Exactly 122 tests collected from `tests/`, 122 executed, **122 passed** (0 failures, 0 errors, 0 warnings) in 3.81 seconds.
   * Recommendation Safety Gate verified operational: correctly blocks commercial advice due to 43-day data lag (latest data is 2026-09-30 vs current date).
4. **Independent-Review Status:**
   * Read-only audits MP-AUDIT-001 and MP-AUDIT-001R completed and delivered.
   * Next implementation steps pending technical lead review and owner workflow confirmation.

## 19. Existing Data and Research Evidence

### 19.1 Price data

The repository contains two historical price cohorts:
- The **2-Year Panel** (`data/raw/`, 160,192 rows, 130 commodities), representing a clean 731-day temporal window (September 2024 to September 2026).
- The **5-Year Panel** (`5 year dataset/`, 472,385 rows, 139 commodities), representing 1,856 calendar days (September 2021 to September 2026).
- The **Validated 5-Year Panel** (`data/processed/mandi_5year_validated.csv`, 462,350 rows, 108 commodities), resulting from Strategy 2 deduplication (-2,936 conflict rows), sanity filtering (-27 invalid rows), and historical depth filtering (-7,072 low-observation rows).
- A single-day nationwide API snapshot (`data/raw_external/9ef84268...csv`, 11,720 rows) for 11 November 2026 across 385 districts.

Important outstanding work:
- Reconcile live API access for continuous daily ingestion from data.gov.in.
- Establish verified download session receipts for raw historical datasets.
- Address the 43-day data staleness gap (September 30, 2026 to present).

### 19.2 Arrivals data

The previous audit found:

- 25 district–crop CSVs covering five districts and five crops.
- A consolidated arrivals file.
- Five original AGMARKNET Excel reports in `data/raw/arrivals/historical/raw_downloads/`.
- CEDA wheat price and quantity CSVs.
- Arrival data fields including `Arrivals_Tonnes`, `Arrival_Unit`, date, district, market, commodity, variety, and grade.

The CEDA files are not proof of complete coverage across every district and crop.

Critical issue identified:

`src/ingest_agmarknet_arrivals.py` may read generated CSV outputs alongside original source files when its input glob includes all files in the historical folder.

Before rerunning ingestion, separate immutable raw inputs from generated outputs and make the pipeline idempotent.

Required verification:

- Source-to-output reconciliation.
- Unit validation.
- Duplicate detection.
- Date coverage.
- District–market–crop coverage.
- Raw Excel totals versus processed totals.
- Repeated-run reproducibility.

### 19.3 Weather

Previously found:

- NASA POWER historical weather CSV under `suryansh - work/dataset_research/raw_external/`.
- Corresponding checksum text file.
- Acquisition script.

Outstanding:

- Validate the dataset and its exact source parameters.
- Record geographic coordinates and weather variables.
- Document time standard and units.
- Establish the appropriate canonical data location only after path-impact inspection.
- Investigate IMD historical observations and access conditions.

### 19.4 Production

Previously found:

- A synthetic UP district–crop production CSV in quarantine.
- No verified real UP DES production dataset in the audited tree.
- No actual official UPAg APY data file in the audited tree.

The synthetic dataset must remain quarantined.

Do not use it as empirical production evidence.

### 19.5 Storage and transport

Previously found:

- CWC FY 2026–27 tariff PDF.
- Post-harvest loss reference documents.
- `data/reference/crop_storage_parameters.csv`.
- Existing freight-haulage modelling and summary material.

Outstanding:

- Verify the exact scope and applicability of each tariff.
- Collect actual private/cooperative warehouse rate evidence where possible.
- Collect representative transport quotations.
- Distinguish actual quotations from modelled transport estimates.
- Validate crop-specific storage assumptions.

### 19.6 Official reports

Previously found:

- `research/official_reports/mofpi_post_harvest_loss_study.pdf`
- `research/official_reports/README.md`
- Additional CWC and PIB reference PDFs.

The exact completeness and applicability of the MoFPI report require inspection. Its existence must not be confused with confirmation that all required post-harvest studies have been collected.

### 19.7 Academic research and fieldwork

The previous audit established:

- A scoped academic literature review is required covering time-series forecasting, agricultural price formation, and post-harvest supply chain economics (replacing rigid paper count quotas with topic-relevant depth).
- Stakeholder interview templates exist in research folders but live field interview records are uncollected.
- Consent and privacy protocols for fieldwork remain pending.
- Source and licence registration is partially complete.

Templates and survey forms must not be treated as completed empirical research.

# PART III — PHASED IMPLEMENTATION ROADMAP

## 21. Roadmap Overview

The project progresses through 10 controlled phases (Phases 0 through 9).

> **Supersession & Task Mapping Note:**  
> This 10-phase roadmap supersedes all prior project execution roadmaps (including the legacy 9-phase framework). The initial discovery, audit, and setup tasks map directly into this roadmap as follows:
> - **Phase 0 (Governance & Baseline):**
>   - `MP-AUDIT-001` (Completed 2026-11-12): Verified repository baseline, branch/remote state (only `main` exists), HEAD SHA `82a0e8bb`, 122 passing tests, and 472,385/462,350 row reconciliation.
>   - `MP-AUDIT-001R` (Completed 2026-11-12): Resolved commodity counts (130 raw 2-yr, 139 raw 5-yr, 108 processed), qualified multiset overlap, date interpretation, and arrivals ingestion risks.
>   - `MP-SETUP-002` (Completed 2026-11-12): Established local journal (`brain/context.md`), `.gitignore` isolation, mathematical validation protocol (`MODEL_AND_MATH_VALIDATION.md`), and Kaggle CLI readiness.
>   - `MP-SETUP-003` (Current): Corrects master specification, codifies capability-specific readiness gates, and pushes baseline docs to `origin main`.
> - **Phase 1 (Data Organization & Arrivals Ingestion):**
>   - `MP-DATA-002` (Next Bounded Task): Refactors `src/ingest_agmarknet_arrivals.py` to make offline arrivals processing non-destructive, immutable, and idempotent.

| Phase | Name | Primary outcome |
|---|---|---|
| 0 | Project governance and baseline | Approved specification, verified starting point, local journal, and Kaggle readiness |
| 1 | Data collection & raw preservation | Non-destructive raw archives, source evidence, and capability-specific ingestion |
| 2 | Data validation and dataset freeze | Trusted, versioned dataset foundation and provenance registers |
| 3 | Research and requirements | Academic foundation, literature review, and evaluated product requirements |
| 4 | Forecasting benchmark | Reproducible, evaluated forecasting system (L0 to L3 baselines) on Kaggle |
| 5 | Application architecture and Release 1 | Usable market-intelligence and price-tracking application |
| 6 | Economic decision-support research | Validated cost and loss methodology and double-friction accounting |
| 7 | Release 2 implementation | Qualified economic comparison features and safety-gated advice |
| 8 | Prospective pilot and evaluation | Demonstrated usability, logged prospective performance, and limitation disclosure |
| 9 | Final academic and engineering handover | Reproducible, fully documented codebase and academic thesis deliverables |

Phases proceed based on **capability-specific readiness** rather than monolithic project-wide blockers.

## 22. Phase 0 — Governance and Baseline

### Objectives

- Approve this master specification.
- Verify the current repository state.
- Establish project journal rules.
- Confirm the Kaggle compute workflow.
- Record current implementation status.

### Tasks

1. Inspect the current branch and HEAD.
2. Inspect tracked and untracked changes.
3. Review current project documentation.
4. Establish `context.md/` safely.
5. Record the compute policy.
6. Inspect Kaggle CLI readiness without exposing credentials.
7. Establish task IDs and approval gates.

### Deliverables

- Approved master specification.
- Initial project status report.
- Local-only project journal.
- Kaggle readiness report.
- Implementation roadmap.

### Exit criteria

- No unexplained repository changes.
- Current branch and HEAD recorded.
- Journal rules verified.
- Compute policy recorded.
- No unapproved heavy computation started.

## 23. Phase 1 — Data Collection & Capability-Specific Readiness

### Objectives

Establish a source-backed inventory of the data needed by the project, enforcing **capability-specific readiness gates**:
- **Release 1 Price-Only Forecasting Gate:** Requires only validated historical price panels and fresh daily price ingestion. Price-only forecasting evaluation must NOT be blocked waiting for production statistics, private storage quotations, IMD weather archives, or completed literature reviews.
- **Ablation Studies Gate (L4):** Requires arrival volumes and NASA POWER weather to evaluate incremental feature uplift against pure price baselines.
- **Release 2 Economic Gate:** Requires validated post-harvest loss parameters, CWC statutory tariffs, and localized freight costs before enabling qualified storage comparisons.

### Tasks

**Prices**

- Verify OGD source access.
- Obtain complete paginated snapshots.
- Record resource identifiers and query parameters.
- Confirm latest observation dates.
- Validate variety and grade handling.

**Arrivals**

- Audit AGMARKNET original reports.
- Audit CEDA downloads.
- Reconcile source and derived records.
- Verify daily or monthly granularity.
- Establish unit consistency.

**Weather**

- Validate NASA POWER acquisition.
- Document coordinates, variables, units, and time standards.
- Investigate IMD access and historical availability.

**Production**

- Investigate official UP DES and UPAg data.
- Obtain actual files only where available and legally usable.
- Keep synthetic data quarantined.

**Storage**

- Inspect official CWC tariff evidence.
- Collect applicable local storage rates.
- Record crop, facility, tariff period, and conditions.

**Transport**

- Obtain actual route quotations where feasible.
- Distinguish quotes from modelled estimates.
- Record route, distance, date, vehicle, and applicable charges.

**Post-harvest research**

- Inspect existing MoFPI and other reports.
- Identify crop-specific evidence.
- Record exact page references.
- Investigate ICAR-CIPHET and NABCONS material.

**Academic literature review**

- Execute a scoped literature review structured around four core academic pillars:
  1. Time-series econometrics and machine learning for agricultural price forecasting (ARIMA, GBDT, tree ensembles).
  2. Mandi price formation dynamics, spatial price arbitrage, and spatial cointegration across regional markets.
  3. Multi-horizon forecasting methodology and leakage-resistant chronological evaluation protocols.
  4. Post-harvest supply chain economics, storage biology hurdles, and farmer decision support.
- Record title, authors, publication venue, DOI, methodology, findings, and direct relevance to Mandi Prediction.
- Replace arbitrary paper count targets with thematic depth and methodology defensibility.

**Stakeholder research**

- Prepare an ethical interview protocol.
- Obtain consent before collecting information.
- Anonymise records.
- Report actual sample size and limitations.

### Deliverables

- Source registry.
- Collection tracker.
- Download log.
- Checksums.
- Research source inventory.
- Data access and licensing assessment.
- Outstanding source investigation report.

### Exit criteria & Capability-Specific Readiness

- **Capability-Specific Decoupling:** Release 1 forecasting experiments (Phases 4 & 5) are unblocked as soon as price series validation and baseline datasets are frozen. They must NOT wait for production data, cold storage quotations, or stakeholder fieldwork.
- Every source acquired has an explicit verification status across the 6 dimensions (provenance, quality, availability, usage rights, data nature, freshness).
- Available data has documented provenance; checksums prove local file integrity.
- Missing data streams are explicitly identified without fabricated substitutes.

## 24. Phase 2 — Data Validation and Dataset Freeze

### Objectives

Establish the first approved dataset versions for modelling and application development.

### Tasks

1. Audit every raw dataset.
2. Validate schemas and data types.
3. Standardise units without destroying original values.
4. Resolve market identity using evidence-backed mappings.
5. Resolve commodity and variety identities.
6. Analyse missing observations.
7. Detect duplicates and suspicious values.
8. Reconcile processed outputs with original sources.
9. Document transformations.
10. Generate dataset manifests and checksums.
11. Produce coverage reports.

### Important rules

- Do not silently delete suspicious data.
- Do not assume absent records mean zero.
- Do not fill historical gaps with invented values.
- Do not mix incompatible price units.
- Do not merge markets merely because names appear similar.
- Do not use synthetic data as empirical training evidence.
- Preserve original source files.

### Deliverables

- Data dictionary.
- Validated reference tables.
- Dataset validation reports.
- Dataset version manifests.
- Approved modelling dataset versions.
- Quarantine and exclusion register.

### Exit criteria

Every dataset used in a modelling experiment must have passed its relevant validation checks and have a reproducible version identifier.

## 25. Phase 3 — Research and Product Requirements

### Objectives

Establish the academic rationale and detailed user-facing requirements.

### Tasks

1. Review relevant academic literature.
2. Write the literature review.
3. Document the forecasting problem.
4. Define supported markets and commodities.
5. Define forecast horizons.
6. Define user journeys.
7. Write functional requirements.
8. Write non-functional requirements.
9. Create application wireframes or an interface specification.
10. Document known limitations.

### Deliverables

- Literature review.
- Project requirements.
- Data dictionary.
- Forecasting methodology proposal.
- Product user journeys.
- First-release scope matrix.
- Risk and limitation register.

### Exit criteria

The first release has a precise scope and acceptance criteria, supported by evidence from the validated datasets.

## 26. Phase 4 — Forecasting Benchmark

### Objectives

Evaluate the existing classifier and develop a defensible continuous-price forecasting benchmark.

### Tasks

1. Inspect the existing classifier.
2. Document its target, labels, features, and training procedure.
3. Audit possible leakage.
4. Establish chronological train, validation, and test windows.
5. Implement baseline models.
6. Evaluate candidate forecasting models.
7. Conduct walk-forward backtesting.
8. Report performance per series and horizon.
9. Analyse errors and difficult market conditions.
10. Evaluate uncertainty methods.
11. Select approved models.
12. Package preprocessing and inference artefacts.

### Execution

Full-panel profiling, training, backtesting, and expensive experiments must run on Kaggle.

Small, bounded tests and static checks may run locally.

### Deliverables

- Executed Kaggle notebooks.
- Experiment configurations.
- Baseline reports.
- Model comparison report.
- Walk-forward evaluation results.
- Error analysis.
- Uncertainty evaluation.
- Approved model artefact manifests.

### Exit criteria

- The evaluation design is leakage-resistant.
- Results are reproducible.
- Baselines are reported.
- Model performance is acceptable for its declared use.
- Limitations are documented.
- Approved artefacts can be used by the intended inference interface.

A model must not be approved merely because it has a high score on one test split.

## 27. Phase 5 — Release 1 Application

### Objectives

Deliver a functional market-intelligence and forecasting application.

### Tasks

1. Inspect and approve the application architecture.
2. Define the backend API.
3. Define data-serving contracts.
4. Implement latest-price retrieval.
5. Implement historical trend retrieval.
6. Integrate approved forecast artefacts.
7. Add forecast issue and target dates.
8. Add freshness and source indicators.
9. Add unsupported-data handling.
10. Build the user interface.
11. Implement automated tests.
12. Conduct end-to-end validation.
13. Prepare deployment.

### Deliverables

- Working application.
- Backend/API.
- Frontend.
- Data-serving layer.
- Forecast inference integration.
- Automated tests.
- User guide.
- Deployment guide.
- Release validation report.

### Exit criteria

A user can select supported markets and commodities and obtain correct, traceable price information and approved forecast outputs.

Unsupported, stale, missing, or failed results are handled explicitly.

## 28. Phase 6 — Economic Decision-Support Research

### Objectives

Determine whether sufficient evidence exists to calculate meaningful sell-now, wait, and storage outcomes.

### Tasks

1. Review crop-specific storage evidence.
2. Validate CWC tariff applicability.
3. Collect actual local storage rates where feasible.
4. Collect transport quotations.
5. Define handling and financing cost treatment.
6. Define quantity-loss methodology.
7. Define quality-loss methodology.
8. Validate crop-storage suitability.
9. Build economic calculation test cases.
10. Perform sensitivity analysis.
11. Define decision eligibility checks.
12. Review economic conclusions with relevant domain expertise where possible.

### Deliverables

- Economic methodology.
- Cost evidence register.
- Crop-storage parameter evidence.
- Economic calculation tests.
- Sensitivity reports.
- Decision eligibility rules.
- Documented limitations.

### Exit criteria

The calculations have valid input definitions, traceable assumptions, tested formulas, and explicit safeguards.

If sufficient evidence cannot be obtained, the feature remains informational or is deferred.

## 29. Phase 7 — Release 2 Economic Decision Support

### Objectives

Implement qualified economic comparisons.

### Tasks

1. Implement immediate-sale calculation.
2. Implement alternative mandi net-proceeds calculation.
3. Implement waiting-period comparison.
4. Implement storage calculation.
5. Add quantity and quality deterioration treatment.
6. Add applicable cost calculations.
7. Add uncertainty and sensitivity displays.
8. Add eligibility checks.
9. Add explanatory outputs.
10. Test representative scenarios.
11. Review usability and clarity.

### Deliverables

- Economic decision engine.
- Economic API contracts.
- Updated application.
- Test suite.
- Scenario evaluation report.
- User explanation and limitations.

### Exit criteria

The application explains its inputs and assumptions and refuses unsupported recommendations.

## 30. Phase 8 — Pilot and Final Evaluation

### Objectives

Establish whether the product is understandable, reliable, and useful in its intended context.

### Tasks

1. Prepare a pilot protocol.
2. Identify participants.
3. Obtain consent.
4. Test supported workflows.
5. Record user feedback.
6. Measure usability.
7. Record data and forecast issues.
8. Analyse failures.
9. Improve the application.
10. Document pilot limitations.

### Deliverables

- Pilot protocol.
- Anonymised feedback summary.
- Usability findings.
- Defect register.
- Final validation report.
- Updated risk and limitation register.

### Exit criteria

The project can accurately explain what has been validated, what has not, and what evidence supports its claims.

A demonstration with a small group must not be represented as proof of large-scale farmer impact.

## 31. Phase 9 — Final Academic and Engineering Handover

### Objectives

Prepare the project for evaluation, future maintenance, and further development.

### Deliverables

- Complete source code.
- Reproducible workflows.
- Approved dataset manifests.
- Experiment notebooks.
- Model evaluation reports.
- Application.
- Technical documentation.
- User documentation.
- Deployment instructions.
- Literature review.
- Final academic report.
- Presentation.
- Demonstration scenarios.
- Known limitations.
- Future-work roadmap.

### Exit criteria

A technically competent reviewer can understand the system, reproduce the documented experiments, inspect the evidence, run the supported workflows, and identify the limitations without relying on undocumented knowledge from the project owner.

---

# PART IV — TASK CONTROL AND AGENT OPERATING RULES

## 32. Mandatory AI-Agent Workflow

All coding agents must follow this workflow:

1. Inspect the relevant files and current repository state.
2. Read the applicable project documentation.
3. Identify the task ID and approval scope.
4. Explain dependencies and risks.
5. Propose a bounded implementation.
6. Wait for approval when required.
7. Implement only the approved task.
8. Run the appropriate tests.
9. Record exact results.
10. Update relevant documentation.
11. Report files changed.
12. Wait for authorisation before committing or pushing when not explicitly authorised.

Agents must not assume that a task authorises unrelated cleanup, architectural changes, dataset movement, or model replacement.

## 33. Repository Safety Rules

- Inspect the current branch and HEAD before changes.
- Preserve existing user modifications.
- Never discard uncommitted changes without explicit permission.
- Do not reset, clean, or overwrite user work.
- Do not blindly move data files.
- Do not delete source data after processing.
- Do not rewrite functioning model logic without an approved task.
- Do not modify existing evaluation logic merely to improve a reported metric.
- Do not invent data or research.
- Do not push without appropriate authorisation.

## 34. Documentation Update Rules

Update the relevant documentation whenever:

- A data source is added or removed.
- A dataset is processed or versioned.
- A validation rule changes.
- A model is trained or approved.
- A model evaluation result changes.
- An API contract changes.
- A feature is added or removed.
- An architectural decision is made.
- A known limitation is discovered.
- A deployment configuration changes.

Documentation must distinguish:

- Planned.
- In progress.
- Implemented.
- Tested.
- Verified.
- Released.
- Deferred.
- Blocked.

A feature must not be marked complete merely because source code has been written.

## 35. Local Project Journal

The exact requested local-only directory is:

```text
context.md/
├── README.md
├── CURRENT_STATE.md
├── PROGRESS_LOG.md
├── DECISIONS.md
└── KAGGLE_RUNS.md
```

The root `.gitignore` must contain:

```gitignore
/context.md/
```

The journal must record actual timestamps and must never contain credentials.

Historical entries reconstructed from reports must be labelled as backfilled.

This local journal supplements rather than replaces version-controlled documentation.

## 36. Kaggle Policy

Heavy work must run on Kaggle.

A Kaggle experiment is complete only when its outputs have been retrieved where required, verified, and documented.

The project must distinguish:

- Submitted.
- Running.
- Completed.
- Failed.
- Output retrieved.
- Output verified.
- Experiment reviewed.
- Model approved.

A successful execution status is not equivalent to a successful experiment.

---

# PART V — PROJECT ACCEPTANCE AND COMPLETION

## 37. Overall Completion Standard

The project is complete only when the applicable release scope has passed its acceptance criteria.

### Academic completion

- Problem statement is clear.
- Literature review is supported by actual reviewed sources.
- Data sources and limitations are documented.
- Experimental design is defensible.
- Models are evaluated against baselines.
- Results are reproducible.
- Negative results and limitations are reported.
- Conclusions are supported by evidence.

### Engineering completion

- Application works for supported cases.
- Data pipelines are reproducible.
- Data validation is automated where appropriate.
- APIs and interfaces are documented.
- Tests pass.
- Errors and missing data are handled safely.
- Deployment instructions work.
- Security and privacy requirements are addressed.
- Monitoring and maintenance are documented.

### Economic decision-support completion

- Costs and assumptions have provenance.
- Crop-specific loss treatment is defensible.
- Financial calculations are tested.
- Uncertainty and sensitivity are considered.
- Unsupported recommendations are blocked.
- Outputs are understandable to intended users.

## 38. Definition of Done for an Individual Task

A task is complete only if:

1. Its objective was met.
2. Its scope was respected.
3. Its implementation is present.
4. Its relevant tests were run.
5. Results are recorded accurately.
6. Documentation is updated.
7. Limitations are disclosed.
8. No unrelated changes were introduced without approval.
9. The owner has reviewed the output where approval is required.

## 39. Current Project Status — Initial Assessment

Based on the last verified repository audit:

| Area | Status at last audit |
|---|---|
| Historical price data | Substantial data present; completeness and provenance work remains |
| Complete OGD snapshots | Incomplete |
| Arrivals | Substantial data present; reconciliation and ingestion reproducibility need verification |
| NASA weather | Dataset and acquisition script present; canonical organisation and validation incomplete |
| IMD historical weather | Not established |
| Verified UP production data | Not found in audited tree |
| UPAg production data | Not found in audited tree |
| Synthetic production data | Quarantined; must remain excluded from empirical modelling |
| CWC tariff evidence | Present |
| Private storage quotations | Not established |
| Transport quotations | Not established |
| Crop-storage parameters | Present; evidence and assumptions require review |
| MoFPI research | A PDF exists; completeness and relevance require inspection |
| Academic literature review | In progress (scoped review framework established) |
| Stakeholder interview evidence | Not found |
| Source and licence register | Incomplete |
| Forecasting methodology documentation | Formalized in MODEL_AND_MATH_VALIDATION.md |
| Application acceptance specification | Requires formalisation |
| Testing evidence | 122 tests passing in tests/ (verified 2026-11-12) |
| Deployment readiness | Not established |

This table is a baseline assessment, not a current execution report. Recheck the repository before acting on it.

## 40. Immediate Next Actions

The approved implementation sequence maps to the capability-specific roadmap:

**Task MP-001 (Completed):** Reverify repository baseline and reconcile documentation with master specification (delivered via MP-AUDIT-001/001R).

**Task MP-002 (Completed):** Establish local journal and math validation records (delivered via MP-SETUP-002).

**Task MP-003 (Current):** Close Step 1 gaps, correct master specification, and push baseline documentation (MP-SETUP-003).

**Task MP-DATA-002 (Next Bounded Task):** Refactor `src/ingest_agmarknet_arrivals.py` for immutable, deterministic offline arrivals organization.

**Task MP-DATA-003:** Live API client implementation with backoff retries for daily data.gov.in price ingestion.

**Task MP-MODEL-001:** Launch remote Kaggle benchmark for L0–L3 forecasting baselines on validated price panel.

Progress proceeds according to capability readiness: Release 1 forecasting is evaluated as soon as price data is frozen and does not wait on downstream storage or production survey closures.

---

## Final Project Principle

Mandi Prediction must prioritise correctness, traceability, reproducibility, and practical usefulness over the appearance of technical sophistication.

A simple model with honest evaluation is preferable to a complex model with unreliable evidence.

A clear unavailable-data message is preferable to a fabricated value.

An economic comparison with disclosed assumptions is preferable to an unsupported storage recommendation.

A working, documented, evaluated application is the intended outcome—not merely a collection of notebooks and charts.