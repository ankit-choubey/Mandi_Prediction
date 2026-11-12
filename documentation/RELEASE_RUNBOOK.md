# APMC Mandi Intelligence System - Release Runbook & Operational Guide
**Task Identifier:** MP-RELEASE-001
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
- **Commercial Storage Cost Feed:** Storage, transport, and spoilage parameters must be entered by users or sourced from approved localized surveys.

---

## 2. Tested Compatibility Matrix

| Component | Tested Runtime | Minimum Supported | Maximum Validated | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Python** | 3.14.0 / 3.11.9 | 3.10.0 | 3.14.0 | Zero external pip dependencies required for runtime serving. |
| **Node.js** | 25.2.1 | 22.0.0 | 25.x | Built-in native `WebSocket` used for Chrome DevTools Protocol automation. |
| **Google Chrome** | 131.0.6778.86 | 120.0.0 | Latest | Headless automation via `--remote-debugging-port`. |
| **Operating System** | macOS 15.3 (Darwin 24.3) | POSIX / Linux | macOS / Linux | Platform-agnostic standard library WSGI and HTTP. |
| **Docker Engine** | CLI 29.6.1 (Daemon Not Running) | 24.0.0 | Latest | Packaging configuration provided; execution marked `NOT_RUN`. |

---

## 3. Operational Health & Logging Specifications

### Secret-Safe Logging Convention
1. **Never Log Sensitive Payloads:** Full economics request bodies containing proprietary farmer quantities or costs are excluded from application logs by default.
2. **No Path or Credential Leaks:** Unhandled exceptions and 404/500 handlers return sanitized, secret-safe envelopes without internal filesystem paths or stack traces.
3. **Structured Timestamps:** All log entries use ISO 8601 UTC timestamps with microsecond precision and explicit process identifiers (`[APMC-RELEASE]`).

### Measured Latency Baselines
- **Full Python Process Startup:** ~72 ms
- **Ready-to-First-Response:** ~1.2 ms
- **Warm Static Asset Latency:** ~0.26 ms (HTML), ~0.15 ms (CSS/JS)
- **Warm JSON API Latency:** ~0.53 ms (`/api/v1/prices/latest`), ~0.22 ms (`/api/v1/economics/evaluate`)

---

## 4. Startup, Inspection & Graceful Shutdown

### A. Local Standalone WSGI Service
```bash
# 1. Start the service on loopback port 8000
python3 src/run_release_service.py --host 127.0.0.1 --port 8000

# 2. Inspect system health & process status
curl -s http://127.0.0.1:8000/api/v1/health | jq .

# 3. Stop the service cleanly
# Press Ctrl+C in the terminal, or send SIGTERM to the process:
kill -TERM <PID>
```

### B. Health Verification Criteria
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
| **Missing Index File** | `/health` returns `DEGRADED`; `/prices/latest` returns `503 Service Unavailable`. | Check log for `"Market price index file not found"`. | Verify snapshot file exists at `data/imported_snapshots/latest_observation_index.json`. Restore from backup or run import pipeline. Call `service._load_latest_index()`. |
| **Corrupt JSON Index** | `/health` returns `DEGRADED`; prices requests fail cleanly without 500 crash. | Check log for `"Failed to parse index JSON"`. | Replace corrupt index file with verified atomic snapshot. Never attempt manual partial recovery from unverified raw files. |
| **Port Conflict** | Service exits on startup with `OSError: [Errno 48] Address already in use`. | Check active listeners: `lsof -i :8000`. | Specify alternative ephemeral port: `python3 src/run_release_service.py --port 8080`. |
| **Non-finite Input (NaN / Inf)** | POST `/economics/evaluate` returns `400 Bad Request`. | Inspect response error code: `"NON_FINITE_NUMERIC_INPUT"`. | Client must supply finite numbers. Form UI validates and sanitizes input before dispatch. |

---

## 6. Container Packaging Smoke Status

- **Docker CLI Version:** Docker version 29.6.1, build d252e0d
- **Docker Daemon Status:** Inactive / Not running locally (`Cannot connect to the Docker daemon at unix:///var/run/docker.sock`).
- **Packaging Execution Status:** `NOT_RUN (Docker daemon not running locally)`.
- **Deployment Acceptance:** Open (pending user infrastructure decision & container environment provisioning).

### Verified Container Commands (For Authorized Execution When Daemon Is Active)
```bash
# Build release container image
docker build -t apmc-mandi-release:1.0.0-rc1 -f Dockerfile .

# Run container on isolated loopback port
docker run -d --name apmc-release -p 127.0.0.1:8000:8000 apmc-mandi-release:1.0.0-rc1

# Inspect container healthcheck status
docker inspect --format='{{json .State.Health}}' apmc-release | jq .

# Stop and clean up
docker stop apmc-release && docker rm apmc-release
```

---

## 7. Prerequisites for Step 13 (Prospective Usability & Shadow Validation)

To transition this research release candidate to prospective evaluation in Step 13:
1. **Prospective Shadow Forecast Logging:** Forecasts for horizon $t+7$ must be logged into immutable audit storage *strictly before* the market clearing time of the target date.
2. **No Post-Hoc Model Retuning:** Models evaluated prospectively must retain bit-for-bit identical weights and parameters as evaluated in Step 7 ($HGB$ / $Persistence$).
3. **Continuous Residual Tracking:** Rolling residuals must be recorded against verified market arrivals to monitor regime breakdown under volatile conditions.
4. **Advisory Gate Remains Closed:** Advisory blocking must remain active until prospective validation criteria ($MAE < Persistence$, coverage $\ge 90\%$ conditionally across regimes) are formally verified.
