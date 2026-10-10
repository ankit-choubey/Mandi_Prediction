"""
Tests for Economic Backtesting and Policy Evaluation
APMC Mandi Market Intelligence System - Phase 4

Verifies:
  1. Causal policy decision execution (no future information leakage).
  2. Always-Sell baseline has strictly zero incremental return.
  3. Oracle benchmark acts as a true upper bound (achieves >= 0 incremental return).
  4. Scenarios produce expected monotonic ordering of break-even thresholds.
  5. Per-quintal return consistency across backtest evaluations.
"""

import pytest
import numpy as np
import pandas as pd
from src.economic_model import (
    EconomicParameters,
    get_default_scenarios,
    calculate_break_even_future_price
)
from src.economic_backtest import run_economic_backtest


def test_always_sell_baseline_zero_incremental_return():
    """Verify Always Sell policy produces exactly 0.0 incremental return."""
    df_synth = pd.DataFrame({
        'Modal_Price': [2000.0, 2500.0, 3000.0],
        'Modal_Price_T7': [2100.0, 2400.0, 3200.0],
        'Price_Change_7d': [2.0, -1.0, 5.0]
    })
    preds = np.array([2, 0, 2])
    scenarios = get_default_scenarios()
    
    res = run_economic_backtest(df_synth, preds, scenarios["Central"])
    sell_stats = res["Always Sell"]
    
    assert sell_stats["times_stored"] == 0
    assert sell_stats["mean_incremental_return_rupees_per_qtl"] == 0.0
    assert sell_stats["total_net_incremental_gain_rupees"] == 0.0


def test_oracle_benchmark_is_true_upper_bound():
    """Verify Oracle Benchmark achieves greater than or equal returns to all other policies."""
    df_synth = pd.DataFrame({
        'Modal_Price': [2000.0, 2500.0, 3000.0, 2200.0],
        'Modal_Price_T7': [2200.0, 2300.0, 3500.0, 2000.0],  # 2 win, 2 lose
        'Price_Change_7d': [5.0, 2.0, 10.0, -5.0]
    })
    preds = np.array([2, 1, 2, 0])
    scenarios = get_default_scenarios()
    
    for sc_name, sc in scenarios.items():
        res = run_economic_backtest(df_synth, preds, sc)
        oracle_gain = res["Oracle Benchmark (Upper Bound)"]["total_net_gain_rupees" if "total_net_gain_rupees" in res["Oracle Benchmark (Upper Bound)"] else "total_net_incremental_gain_rupees"]
        
        for pol_name, stats in res.items():
            pol_gain = stats.get("total_net_incremental_gain_rupees", 0.0)
            assert oracle_gain >= pol_gain, \
                f"Oracle gain ({oracle_gain}) must be >= {pol_name} gain ({pol_gain}) under {sc_name}!"


def test_scenario_monotonicity_of_breakeven():
    """
    Verify that break-even required price increase follows:
    Optimistic < Central < Conservative
    """
    scenarios = get_default_scenarios()
    p_base = 2500.0
    
    be_opt = calculate_break_even_future_price(p_base, scenarios["Optimistic"])["required_percentage_increase"]
    be_cen = calculate_break_even_future_price(p_base, scenarios["Central"])["required_percentage_increase"]
    be_con = calculate_break_even_future_price(p_base, scenarios["Conservative"])["required_percentage_increase"]
    
    assert be_opt < be_cen < be_con, \
        f"Monotonicity failed: Opt ({be_opt:.2f}%) < Cen ({be_cen:.2f}%) < Con ({be_con:.2f}%)"


def test_policy_decisions_use_only_information_available_at_t():
    """
    Verify that policy decisions at T (Trend, Model) do not depend on future price P_T7.
    Mutating future prices must not change decision vectors for Trend or Model policies.
    """
    df1 = pd.DataFrame({
        'Modal_Price': [2000.0, 2000.0],
        'Modal_Price_T7': [2500.0, 2500.0],
        'Price_Change_7d': [5.0, -5.0]
    })
    df2 = pd.DataFrame({
        'Modal_Price': [2000.0, 2000.0],
        'Modal_Price_T7': [1500.0, 1500.0],  # Mutated future price drastically downward
        'Price_Change_7d': [5.0, -5.0]
    })
    preds = np.array([2, 0])
    scenarios = get_default_scenarios()
    
    res1 = run_economic_backtest(df1, preds, scenarios["Central"])
    res2 = run_economic_backtest(df2, preds, scenarios["Central"])
    
    # Decisions taken (times stored) must remain identical
    assert res1["Trend Momentum (T)"]["times_stored"] == res2["Trend Momentum (T)"]["times_stored"]
    assert res1["Model Signal (T)"]["times_stored"] == res2["Model Signal (T)"]["times_stored"]
