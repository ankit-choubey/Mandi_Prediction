# Kaggle & Local Execution Environment Policy

**Authoritative Record:** Task MP-DATA-005  
**Last Updated:** 2026-11-12T08:15:00+05:30  
**Scope:** Remote Kaggle Compute Environments, Local Development Boundaries, and Trained Artifact Serialization Contracts.

---

## 1. Environment Comparison Matrix

All heavy compute workloads (model training, cross-validation, parameter grids, extensive scans) execute strictly on Kaggle CPU/GPU kernels. Code authoring, static inspection, small unit tests, and orchestration execute locally.

| Component / Library | Kaggle Remote Kernel | Local Development Machine | Cross-Platform Compatibility Status |
|---|---|---|---|
| **Operating System** | Linux 6.6.137+ (`x86_64`, GCC 13.3.0) | macOS Darwin (`arm64`, Apple Silicon) | Differing host OS & architecture |
| **Python Runtime** | `3.13.18` (Oct 26 2026) | `3.14.0` (Pinned in `requirements.txt`) | Minor Python version delta |
| **pandas** | `2.3.3` | `2.3.3` | Exact match |
| **numpy** | `2.1.3` | `2.2.6` | Minor version delta (C-API / ABI caution) |
| **scikit-learn** | `1.6.1` | `1.7.2` | Minor version delta (pickle serialization risk) |
| **scipy** | `1.16.3` | `1.16.3` | Exact match |
| **openpyxl** | `3.1.5` | `3.1.5` | Exact match |
| **Random Seed** | `42` (Global) | `42` (Global) | Deterministic pseudo-random generation |

---

## 2. Trained Artifact Serialization & Deserialization Policy

Cross-platform serialization (e.g. `pickle` or `joblib` dumps produced on Linux `x86_64` and loaded on macOS `arm64`, or vice versa) poses severe risks of silent numerical drift or deserialization failures due to C-extension ABI differences between `numpy 2.1.3` / `scikit-learn 1.6.1` and `numpy 2.2.6` / `scikit-learn 1.7.2`.

### Mandatory Contract for All Persisted Models & Preprocessors
1. **Companion Metadata Record:** Every saved model file (`.joblib`, `.pkl`, `.pt`, `.onnx`) MUST be accompanied by an immutable companion manifest (`<model_name>_metadata.json`) or an embedded schema containing:
   - `python_version`: Full `sys.version` string
   - `platform`: `sys.platform` and hardware architecture
   - `library_versions`: Exact pinned versions of `numpy`, `scipy`, `scikit-learn`, `pandas`, and relevant frameworks derived via `importlib.metadata`
   - `training_commit`: Exact 40-character Git commit hash of the training code
   - `dataset_checksum`: SHA-256 digest of the training dataset
   - `random_seed`: Seed used for training initialization
   - `created_at_utc`: ISO-8601 creation timestamp
2. **Fail-Fast Deserialization Check:**
   When loading a model in any inference or serving pipeline:
   - If the runtime library major/minor version differs from the artifact metadata (e.g. loading a `scikit-learn 1.6.1` model in `scikit-learn 1.7.2`), the loader MUST log a clear warning or raise an explicit `EnvironmentMismatchError` if strict mode is enabled.
   - Pickled pipelines must never be unpickled across environments without verifying companion metadata.

---

## 3. Measurable Local-Compute Rule

To preserve developer velocity and prevent unmonitored compute loads or memory exhaustion on local development machines, local operations are strictly bounded by:
* **File Size:** $\le 10\text{ MB}$
* **Row Count:** $\le 50,000\text{ rows}$
* **Runtime Duration:** $\le 30\text{ seconds}$

Any computation, join, scan, or model execution exceeding any one of these three metrics MUST be delegated to Kaggle kernels via the Kaggle CLI. Local testing of notebook or pipeline logic must be performed on synthetic fixtures or small samples strictly adhering to these thresholds.

