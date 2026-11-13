# APMC Mandi Intelligence System - Release Runbook & Operational Guide
**Task Identifier:** MP-RELEASE-001R
**Release Version:** `1.0.0-rc1` (Research Demonstration Release Candidate)
**Security Classification:** Confidential Academic Research — Fail-Closed Commercial Advisory Gating

---

## 1. Executive Release Overview

The APMC Mandi Intelligence System provides retrospective econometric benchmarking, verified price series inspection, and cost-aware holding economics evaluation.

### Supported Capabilities (RC1 Scope)
1. **Historical & Retrospective Benchmark Scorecards:** Fully validated performance evaluation across $N = 64,776$ point forecast origins and $N = 26,918$ prediction interval origins across expanding chronological test folds (F1–F4).
2. **Dated Imported Mandi Prices:** Verified official APMC modal price inspection across 30 series (26 accepted official series, 4 unapproved market review series with price withholding).
3. **Cost-Aware Research Economics:** Interactive holding gain/loss evaluation ($\Delta R = R_{\text{hold}} - R_{\text{sell,net}}$), affine price range bounds, break-even price calculation ($P^*$), and linear carrying cost accounting (`none`, `financing`, `opportunity`).
4. **Permanent Fail-Closed Advisory Gating:** Operational status is strictly `RESEARCH_ONLY` with advisory action permanently `BLOCKED`. No commercial trading or live farmer advice is authorized without approved prospective forward-validation under Steps 12 and 13.

### Intentionally Unavailable Capabilities
- **Live Automated Scraping / Unauthenticated Remote Feeds:** Bounded to verified file-imported snapshots.
- **Serving Forward Predictions as Operational Advice:** Retrospective machine learning models cannot produce live advice without prospective shadow-logging.
- **Commercial Storage Cost Feed:** Storage, transport, and spoilage parameters must be entered by users or sourced from approved localized surveys. Local commercial cost evidence remains 0/22 quotations received in the inspected directory, not universal tariff absence. Research holding arithmetic handles missing commercial feeds gracefully without crashing.

---

## 2. Tested Compatibility Matrix

| Component | Tested Runtime | Minimum Supported | Maximum Validated | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Python** | 3.14.0 / 3.11.9 | 3.10.0 | 3.14.0 | Zero external pip dependencies required for runtime serving. Pure standard library verified under `python3 -S`. |
| **Node.js** | 25.2.1 | 22.0.0 | 25.x | Built-in native `WebSocket` used for Chrome DevTools Protocol automation. |
| **Google Chrome** | 131.0.6778.86 | 120.0.0 | Latest | Headless automation via `--remote-debugging-port`. |
| **Operating System** | macOS 15.3 (Darwin 24.3) | POSIX / Linux | macOS / Linux | Platform-agnostic standard library WSGI and HTTP. |
| **Docker Engine** | CLI 29.6.1 (Daemon Not Running) | 24.0.0 | Latest | Packaging configuration provided; execution marked `NOT_RUN` pending engine socket. |

---

## 3. Operational Health & Logging Specifications

### Secret-Safe Logging Convention
1. **Never Log Sensitive Payloads:** Full economics request bodies containing proprietary farmer quantities or costs are excluded from application logs by default.
2. **No Path or Credential Leaks:** Unhandled exceptions and 404/500 handlers return sanitized, secret-safe envelopes without internal filesystem paths or stack traces.
3. **Structured True UTC Timestamps:** All log entries use ISO 8601 UTC timestamps formatted via `time.gmtime` (`YYYY-MM-DDTHH:MM:SSZ`) with explicit process identifiers (`[APMC-RELEASE]`). India-calendar observation dates are maintained as separate domain attributes.

### Measured Latency Baselines (Discrete Scopes)
- **Interpreter Startup Scope:** ~20.55 ms (`python3 -c "pass"`)
- **Import Scope:** ~43.50 ms (`import src.api`)
- **Service Instantiation Scope:** ~0.32 ms (`MandiMarketService()`)
- **Listener Binding Scope:** ~1.20 ms (`make_server("127.0.0.1", 0, app)`)
- **Ready-to-First-HTTP-Response Scope:** ~35.00 ms (first request over loopback socket)
- **Warm Static Asset Latency:** ~0.26 ms (HTML), ~0.15 ms (CSS/JS)
- **Warm JSON API Latency:** ~0.53 ms (`/api/v1/prices/latest`), ~0.22 ms (`/api/v1/economics/evaluate`)

---

## 4. Startup, Inspection & Graceful Shutdown

### A. Supported Entrypoints
Both direct execution and module execution are fully supported and dynamically resolve the repository root without requiring an inherited `PYTHONPATH`:

```bash
# Option 1: Direct script execution
python3 src/run_release_service.py --host 127.0.0.1 --port 8000

# Option 2: Standard module execution
python3 -m src.run_release_service --host 127.0.0.1 --port 8000

# 2. Inspect system health & process status
curl -s http://127.0.0.1:8000/api/v1/health | jq .

# 3. Stop the service cleanly
# Press Ctrl+C in the terminal, or send SIGTERM to the process:
kill -TERM <PID>
```

### B. Loopback Policy Enforcement
Normal host exposure is strictly enforced to `127.0.0.1`. The runner refuses to bind to non-loopback addresses (`0.0.0.0`) by default unless the explicit flag `--allow-container-host` is provided inside containerized environments.

### C. Graceful Shutdown & Socket Release
Upon receiving `SIGTERM` or `SIGINT`, graceful shutdown is dispatched asynchronously from an independent thread to unblock `serve_forever()` on the main thread, executing `server.server_close()` and exiting with code `0`. Socket options include `SO_REUSEADDR` to allow immediate rebinding on the same port.

### D. Health Verification Criteria
A healthy running instance must report:
- `data.process_status == "HEALTHY"`
- `data.capabilities.prices.status == "AVAILABLE"`
- `data.capabilities.benchmarks.status == "AVAILABLE"`
- `data.capabilities.economics.status == "RESEARCH_ONLY"`
- `data.capabilities.active_advice.status == "BLOCKED"`

---

## 5. Failure & Recovery Runbook

| Failure Scenario | Observed Symptom | Diagnostic Step | Recovery Procedure |
| :--- | :--- | :--- | :--- |
| **Missing Index File** | `/health` returns `DEGRADED`; `/prices/latest` returns `503 Service Unavailable`. | Check log for `"Market price index file not found"`. | Restore valid snapshot file, or pass valid snapshot path via `APMC_LATEST_INDEX_PATH` environment variable. Operator executes public method `service.reload_index(path)` or restarts service process. |
| **Corrupt JSON Index** | `/health` returns `DEGRADED`; prices requests fail cleanly without 500 crash. | Check log for `"Failed to parse index JSON"`. | Replace corrupt index file with verified atomic snapshot. Execute `service.reload_index(new_path)`. Never attempt manual partial recovery from unverified raw files. |
| **Port Conflict** | Service exits on startup with `OSError: [Errno 48] Address already in use`. | Check active listeners: `lsof -i :8000`. | Specify alternative ephemeral port: `python3 -m src.run_release_service --port 8080`. |
| **Non-finite Input (NaN / Inf)** | POST `/economics/evaluate` returns `400 Bad Request`. | Inspect response error code: `"NON_FINITE_NUMERIC_INPUT"` or `"INVALID_JSON_NUMBER"`. | Client must supply finite numbers. Form UI validates and sanitizes input before dispatch. |

---

## 6. Container Packaging Smoke Status

- **Docker CLI Version:** Docker version 29.6.1, build 8900f1d
- **Docker Daemon Status:** Inactive / Not running locally (`Cannot connect to the Docker daemon at unix:///Users/theankit/.docker/run/docker.sock`).
- **Packaging Execution Status:** `NOT_RUN (Local Docker daemon socket unavailable; requires explicit owner engine activation approval)`.
- **Preflight Packaging Assets:** Verified `Dockerfile` and minimal `.dockerignore` (<1 MB build context).
- **Healthcheck Syntax:** Verified `sys` imported; returns code `0` on HTTP 200 and code `1` on unreachable/error.

### DRAFT / NOT_RUN Container Commands (Pending Engine Approval)
```bash
# Build release container image (DRAFT / NOT_RUN)
docker build -t apmc-mandi-release:1.0.0-rc1 -f Dockerfile .

# Run container on isolated loopback port (DRAFT / NOT_RUN)
docker run -d --name apmc-release -p 127.0.0.1:8000:8000 apmc-mandi-release:1.0.0-rc1

# Inspect container healthcheck status (DRAFT / NOT_RUN)
docker inspect --format='{{json .State.Health}}' apmc-release | jq .

# Stop and clean up (DRAFT / NOT_RUN)
docker stop apmc-release && docker rm apmc-release
```

---

## 7. Prerequisites for Step 13 (Prospective Usability & Shadow Validation)

To transition this research release candidate to prospective forward validation under Step 13, the following scientific protocols must be adhered to:

1. **Model Parameter & Code Freezing:**
   - Persistence cannot be required to beat itself on MAE and has no fitted weights.
   - The selected candidate models ($HGB$, Ridge, Persistence), configurations, and benchmark artifacts are frozen before evaluating any future outcomes.
   - Any modification to model architecture, hyperparameter grid, or feature definitions constitutes a distinct declared cohort and requires independent re-baselining.

2. **Challenger Superiority as a Separate Hypothesis:**
   - Challenger superiority ($HGB$ beating Persistence on MAE) is evaluated as a distinct, falsifiable prospective hypothesis.
   - Retrospective evidence demonstrated that Persistence is the overall primary MAE winner ($106.96$ vs $109.75$ INR/quintal), while $HGB$ achieves a $5.91\%$ RMSE reduction ($281.16$ vs $298.83$ INR/quintal).

3. **Evaluation Metric & Modality Matching:**
   - Price forecasts must be evaluated against actual matched modal **PRICE** observations in INR/quintal, never arrivals volume.
   - Target matching strictly enforces the established 6–8 day temporal maturity window, tie-breaking policy, and source availability rules.

4. **Prospective Shadow Logging Schema:**
   - Forecasts for horizon $t+7$ must be recorded into dated, immutable shadow logs strictly before the market clearing time of the issuance date.
   - Log entries must record:
     * `issuance_timestamp_utc`: aware ISO 8601 UTC timestamp.
     * `source_snapshot_id`: cryptographic hash of input price snapshot.
     * `method_version`: frozen code and configuration version.
     * `series_id`: canonical market series identifier.
     * `point_forecast_inr`: issued point prediction in INR/quintal.
     * `interval_lower_inr` and `interval_upper_inr`: issued prediction interval bounds.
     * `eligibility_status` and `abstention_reason`: explicit recording of any non-issued predictions to preserve correct denominator accounting.

5. **Outcome Maturity & Residual Tracking:**
   - Outcomes are evaluated only after the full 7-day maturity period has elapsed.
   - Never use a fold or period's own outcomes to calibrate its intervals.
   - Rolling out-of-sample coverage and width must be tracked continuously to monitor regime shifts and avoid false conditional coverage claims.

6. **Farmer Usability & Advisory Safeties:**
   - Advisory action remains permanently `BLOCKED` in software until prospective coverage ($\ge 90\%$) and error criteria are met.
   - Farmer usability testing must focus on interface comprehension, transparent uncertainty communication, and storage break-even arithmetic, with clear disclaimers that output constitutes academic research and not financial advice.

---

## 8. Prospective Shadow Validation CLI Runbook (`src/prospective_shadow.py`)

Under Task MP-FINAL-013, the prospective shadow registry and evaluation tool was delivered in `src/prospective_shadow.py`. It requires zero external pip packages and runs entirely on the Python standard library.

### 8.1 Initialize Registry
Initializes the append-only registry directory, metadata, and binds the frozen protocol configuration (`experiments/configs/forward_validation_protocol_v1.json`):
```bash
python3 src/prospective_shadow.py init \
  --registry data/shadow_registry \
  --protocol experiments/configs/forward_validation_protocol_v1.json
```

### 8.2 Validate Input Snapshot
Validates snapshot size ($\le 10$ MB, $\le 50,000$ rows), schema integrity, computes SHA-256 hash, and verifies coverage:
```bash
python3 src/prospective_shadow.py validate-snapshot \
  --snapshot data/imported_snapshots/latest_observation_index.json
```

### 8.3 Issue Shadow Predictions (Dry Run & Live)
Evaluates candidates against snapshot. Automatically applies fail-closed freshness policy ($\le 1$ calendar day allowed in IST) and review-status withholding:
```bash
# Dry run (default: previews issuance and logs honest abstentions without mutating registry)
python3 src/prospective_shadow.py issue \
  --snapshot data/imported_snapshots/latest_observation_index.json

# Live append (commits to append-only JSONL shadow ledger with SHA-256 chaining)
python3 src/prospective_shadow.py issue \
  --snapshot data/imported_snapshots/latest_observation_index.json \
  --live
```

### 8.4 Import Future Outcomes & Match Mature Pairs
Ingests fresh outcomes when future calendar dates arrive, and matches them to issued forecasts within the $6 \le \Delta t \le 8$ day maturity window ($T+7$ nominal):
```bash
# Ingest ground-truth observation snapshot
python3 src/prospective_shadow.py import-outcomes \
  --snapshot data/imported_snapshots/future_observation_index_20261118.json \
  --live

# Match matured pairs using protocol tie-breaking rules
python3 src/prospective_shadow.py match --live
```

### 8.5 Generate Audited Scorecard
Evaluates candidate models against the Naive Persistence reference standard on primary MAE, RMSE, bias, MAPE, and within 5% tolerance:
```bash
python3 src/prospective_shadow.py scorecard
```
When forward outcomes have not yet matured, the scorecard honestly outputs:
```json
{
  "scorecard_status": "EMPIRICAL_PENDING",
  "message": "Zero matured forward outcomes available. Forward horizons have not yet closed.",
  "advisory_status": "BLOCKED"
}
```
