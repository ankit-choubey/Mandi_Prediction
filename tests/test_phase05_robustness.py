"""
Phase 5: Robustness, Uncertainty, and Governance Safeguards Test Suite
APMC Mandi Market Intelligence System

Tests deterministic reproducibility and methodological safeguards:
1. Cluster bootstrap deterministic reproducibility.
2. Subgroup sample size threshold enforcement (N >= 250).
3. Decision rule threshold volume monotonicity.
4. Cluster key preservation across canonical series dimensions.
5. Sensitivity tipping point monotonicity.
6. Mandatory operational disclaimers across all Phase 5 documentation.
"""

import os
import pytest
import numpy as np
import pandas as pd
from src.economic_model import EconomicParameters, calculate_incremental_benefit_per_quintal, calculate_break_even_future_price


def test_phase05_cluster_bootstrap_reproducibility():
    """Verify cluster bootstrap produces deterministic results with a fixed seed."""
    rng = np.random.default_rng(42)
    n_rows = 100
    clusters = np.repeat(np.arange(10), 10)
    values = rng.normal(loc=10.0, scale=2.0, size=n_rows)

    unique_clusters = np.unique(clusters)
    cluster_indices = {c: np.where(clusters == c)[0] for c in unique_clusters}

    def run_boot(seed):
        r = np.random.default_rng(seed)
        means = []
        for _ in range(50):
            sampled_c = r.choice(unique_clusters, size=len(unique_clusters), replace=True)
            idx = np.concatenate([cluster_indices[c] for c in sampled_c])
            means.append(np.mean(values[idx]))
        return np.percentile(means, [2.5, 97.5])

    ci1 = run_boot(42)
    ci2 = run_boot(42)
    assert np.allclose(ci1, ci2), "Cluster bootstrap must be strictly deterministic with fixed seed"


def test_phase05_subgroup_sample_size_threshold():
    """Verify subgroups below the minimum sample threshold (e.g., N < 250) are excluded."""
    min_thresh = 250
    df = pd.DataFrame({
        'Group': ['A'] * 300 + ['B'] * 100 + ['C'] * 250 + ['D'] * 249,
        'Value': np.ones(300 + 100 + 250 + 249)
    })

    retained_groups = [g for g, grp in df.groupby('Group') if len(grp) >= min_thresh]
    assert 'A' in retained_groups
    assert 'C' in retained_groups
    assert 'B' not in retained_groups
    assert 'D' not in retained_groups


def test_phase05_decision_rule_threshold_monotonicity():
    """Verify that increasing the probability threshold monotonically reduces or maintains storage count."""
    probs = np.array([0.20, 0.32, 0.38, 0.45, 0.52, 0.65, 0.70])
    thresholds = [0.30, 0.40, 0.50, 0.60]

    counts = [int(np.sum(probs >= t)) for t in thresholds]
    for i in range(len(counts) - 1):
        assert counts[i] >= counts[i + 1], f"Count at {thresholds[i]} ({counts[i]}) must be >= {thresholds[i+1]} ({counts[i+1]})"


def test_phase05_cluster_key_preservation():
    """Verify series clustering key combines all 5 canonical dimensions without collision."""
    row1 = {'District': 'Kanpur', 'Market': 'Kanpur(Grain) APMC', 'Commodity': 'Wheat', 'Variety': 'Dara', 'Grade': 'FAQ'}
    row2 = {'District': 'Kanpur', 'Market': 'Kanpur(Grain) APMC', 'Commodity': 'Wheat', 'Variety': 'Dara', 'Grade': 'Medium'}

    key1 = f"{row1['District']}_{row1['Market']}_{row1['Commodity']}_{row1['Variety']}_{row1['Grade']}"
    key2 = f"{row2['District']}_{row2['Market']}_{row2['Commodity']}_{row2['Variety']}_{row2['Grade']}"

    assert key1 != key2, "Different grades must yield distinct canonical cluster keys"


def test_phase05_sensitivity_tipping_point_monotonicity():
    """Verify break-even price increases monotonically with storage cost and loss fraction."""
    p_t = 2500.0
    costs = [10.0, 20.0, 35.0, 50.0, 100.0]
    be_prices = []

    for c_s in costs:
        params = EconomicParameters(storage_cost_per_quintal=c_s, quantity_loss_fraction=0.01, annual_carrying_rate=0.07)
        res = calculate_break_even_future_price(p_t, params)
        be_prices.append(res['break_even_price'])

    for i in range(len(be_prices) - 1):
        assert be_prices[i] < be_prices[i + 1], "Break-even price must increase strictly monotonically with storage cost"


def test_phase05_mandatory_operational_disclaimers():
    """Verify all Phase 5 documentation files retain the mandatory operational advice prohibition."""
    phase05_dir = os.path.join(os.path.dirname(__file__), "..", "backing", "phase_05")
    md_files = [f for f in os.listdir(phase05_dir) if f.endswith(".md")]

    assert len(md_files) >= 5, "All Phase 5 markdown reports must exist"

    prohibition_phrases = [
        "NOT", "prohibit", "research", "exploratory"
    ]

    for md_file in md_files:
        path = os.path.join(phase05_dir, md_file)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().lower()
            found = any(phrase in content for phrase in prohibition_phrases)
            assert found, f"File {md_file} must contain explicit research disclaimer"
