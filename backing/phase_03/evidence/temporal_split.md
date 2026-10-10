# Phase 3 Temporal Partitioning and Horizon-Aware Embargo Specification

## Overview
A critical flaw in standard machine learning pipelines for time-series and forecasting problems is random train/test splitting. In mandi price prediction, random splitting causes severe lookahead leakage because future observations leak into training features, and overlapping forward-looking target outcomes ($T+7$) cross between partitions.

Phase 3 enforces a strictly chronological, horizon-aware train / validation / test partition with purged embargo buffers.

---

## Partition Boundaries

| Partition | Origin Date Range | Target Realization Date Range ($T+7$) | Eligible Origins | Valid Matched $T+7$ Examples | Normal (%) | Favorable (%) | Unfavorable (%) | Embargo Purged Count |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TRAIN** | 2024-09-01 to 2026-01-17 | 2024-09-08 to 2026-01-24 | 134,706 | 100,650 | 60.26% | 18.07% | 21.68% | 72 |
| **VALIDATION** | 2026-01-25 to 2026-03-31 | 2026-02-01 to 2026-04-07 | 4,213 | 2,914 | 47.15% | 26.66% | 26.18% | 565 |
| **FINAL TEST** | 2026-04-08 to 2026-08-25 | 2026-04-15 to 2026-09-01 | 18,599 | 12,625 | 55.90% | 23.50% | 20.59% | 0 (Held-out) |
| **TOTAL** | **2024-09-01 to 2026-08-25** | **2024-09-08 to 2026-09-01** | **157,518** | **116,189** | — | — | — | **637** |

*Note: Total matched targets before purging = 116,826. 100,650 + 72 + 2,914 + 565 + 12,625 = 116,826 exactly.*

---

## Purging and Embargo Mechanism

Because our primary prediction task is $T+7$ calendar-day forward return:
$$\Delta P_{T+7} = \frac{P_{T+7} - P_T}{P_T} \times 100$$
The outcome of a prediction made at origin date $T$ is not realized until calendar date $T+7$.

### 1. Training Boundary Purge (Train Embargo)
- Training origin boundary ends on **2026-01-17**.
- Its target realization date falls on $2026-01-17 + 7 = \textbf{2026-01-24}$.
- Any observation with origin between **2026-01-18 and 2026-01-24** would have its target outcome realized on or after **2026-01-25** (the start of the validation period).
- **Rule**: All 72 observations originating between 2026-01-18 and 2026-01-24 are purged from training to prevent future validation prices from entering training labels.

### 2. Validation Boundary Purge (Validation Embargo)
- Validation origin boundary ends on **2026-03-31**.
- Its target realization date falls on $2026-03-31 + 7 = \textbf{2026-04-07}$.
- Any observation with origin between **2026-04-01 and 2026-04-07** would have its target outcome realized on or after **2026-04-08** (the start of the final test period).
- **Rule**: All 565 observations originating between 2026-04-01 and 2026-04-07 are purged from validation to prevent future test-period prices from entering validation labels.

### 3. Final Test Holdout Integrity
- The Final Test period begins on **2026-04-08** and runs through **2026-08-25** (with target realizations extending to 2026-09-01, the master dataset endpoint).
- It remains completely untouched during model selection, hyperparameter decisions, feature design, and transformer fitting.
- Only a single frozen candidate model was evaluated once on this holdout partition.

---

## Cross-Series Consistency
All mandi series share these exact chronological calendar boundaries simultaneously. No series is partitioned on different dates, guaranteeing zero time-travel across markets or commodities.
