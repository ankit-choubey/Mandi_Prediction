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
    assert sell_stats["mean_incremental_return_rupees_per_eligible_qtl"] == 0.0
    assert sell_stats["mean_incremental_gain_rupees_10qtl_per_eligible_decision"] == 0.0
    assert sell_stats["mean_incremental_return_rupees_per_stored_qtl"] == 0.0
    assert sell_stats["aggregate_net_incremental_gain_rupees_10qtl_all_decisions"] == 0.0


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
        oracle_gain = res["Oracle Benchmark (Upper Bound)"]["aggregate_net_incremental_gain_rupees_10qtl_all_decisions"]

        for pol_name, stats in res.items():
            pol_gain = stats.get("aggregate_net_incremental_gain_rupees_10qtl_all_decisions", 0.0)
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


def test_aggregate_gain_versus_mean_gain_relationship():
    """
    Deterministic regression test:
    Verify that Aggregate Net Incremental Gain across all decisions equals
    Eligible_Decisions * Mean_Incremental_Gain_10Qtl_Per_Eligible_Decision,
    and that Mean_Incremental_Gain_10Qtl == 10 * Mean_Incremental_Return_Per_Eligible_Qtl.
    """
    df_synth = pd.DataFrame({
        'Modal_Price': [2000.0, 2200.0, 2400.0, 2600.0, 2800.0],
        'Modal_Price_T7': [2150.0, 2100.0, 2650.0, 2550.0, 3100.0],
        'Price_Change_7d': [3.0, -2.0, 6.0, -1.0, 8.0]
    })
    preds = np.array([2, 0, 2, 0, 2])
    scenarios = get_default_scenarios()
    res = run_economic_backtest(df_synth, preds, scenarios["Central"], quantity_per_decision=10.0)

    for pol_name, stats in res.items():
        n = stats["decisions_evaluated"]
        mean_ret_qtl = stats["mean_incremental_return_rupees_per_eligible_qtl"]
        mean_gain_10qtl = stats["mean_incremental_gain_rupees_10qtl_per_eligible_decision"]
        agg_gain = stats["aggregate_net_incremental_gain_rupees_10qtl_all_decisions"]

        # Mean 10-qtl gain must equal 10 * per-qtl return within 0.05 rounding tolerance
        assert pytest.approx(mean_gain_10qtl, abs=0.05) == mean_ret_qtl * 10.0
        # Aggregate gain must equal n * mean_gain_10qtl within 0.50 rounding tolerance
        assert pytest.approx(agg_gain, abs=0.50) == n * mean_gain_10qtl


def test_conditional_versus_unconditional_mean_returns():
    """
    Deterministic regression test:
    Verify that unconditional return equals (Times_Stored / Eligible_Decisions) * conditional return:
      mu_eligible = (N_stored / N) * mu_stored
    Also verify:
      - Always Sell: Times_Stored == 0, mu_eligible == 0.0, mu_stored == 0.0
      - Always Store: Times_Stored == N, mu_eligible == mu_stored
      - Storage win rate is calculated strictly over Times_Stored decisions.
    """
    df_synth = pd.DataFrame({
        'Modal_Price': [2000.0, 2200.0, 2400.0, 2600.0],
        'Modal_Price_T7': [2300.0, 2100.0, 2700.0, 2400.0],
        'Price_Change_7d': [5.0, -3.0, 7.0, -4.0]
    })
    preds = np.array([2, 0, 2, 0])
    scenarios = get_default_scenarios()
    res = run_economic_backtest(df_synth, preds, scenarios["Central"], quantity_per_decision=10.0)

    # 1. Always Sell
    sell_stats = res["Always Sell"]
    assert sell_stats["times_stored"] == 0
    assert sell_stats["mean_incremental_return_rupees_per_eligible_qtl"] == 0.0
    assert sell_stats["mean_incremental_return_rupees_per_stored_qtl"] == 0.0

    # 2. Always Store
    store_stats = res["Always Store"]
    assert store_stats["times_stored"] == store_stats["decisions_evaluated"]
    assert pytest.approx(
        store_stats["mean_incremental_return_rupees_per_eligible_qtl"], abs=0.01
    ) == store_stats["mean_incremental_return_rupees_per_stored_qtl"]

    # 3. Model Signal (Subset stored)
    model_stats = res["Model Signal (T)"]
    n = model_stats["decisions_evaluated"]
    n_stored = model_stats["times_stored"]
    assert n_stored > 0
    mu_eligible = model_stats["mean_incremental_return_rupees_per_eligible_qtl"]
    mu_stored = model_stats["mean_incremental_return_rupees_per_stored_qtl"]
    expected_mu_eligible = (n_stored / n) * mu_stored
    assert pytest.approx(mu_eligible, abs=0.05) == expected_mu_eligible


def test_absence_of_unsupported_arrival_causality_claims():
    """
    Deterministic regression test:
    Verify that Phase 4 reporting text files do not make unsupported causal claims
    about 'arrival crashes', 'arrival gluts', or 'arrival surges' when the dataset has no
    volume/arrivals metric.
    """
    import os
    import re
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    files_to_check = [
        os.path.join(base_dir, "backing", "phase_04", "findings.md"),
        os.path.join(base_dir, "backing", "phase_04", "limitations.md"),
    ]

    unsupported_patterns = [
        re.compile(r"arrival\s+crash", re.IGNORECASE),
        re.compile(r"arrival\s+glut", re.IGNORECASE),
        re.compile(r"arrival\s+surge", re.IGNORECASE),
    ]

    for filepath in files_to_check:
        if not os.path.exists(filepath):
            continue
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        for pat in unsupported_patterns:
            matches = pat.findall(content)
            assert len(matches) == 0, f"Found forbidden causal arrival phrase {matches} in {filepath}"


def test_backtest_with_nonzero_transaction_costs():
    """
    Verify backtest accounts for nonzero transaction_cost_now and transaction_cost_later,
    consistently with evaluate_sell_vs_store:
      - immediate transaction costs reduce immediate-sale proceeds
      - later transaction costs are charged on remaining physical quantity Q * (1 - L)
    """
    from src.economic_model import evaluate_sell_vs_store
    df_synth = pd.DataFrame({
        'Modal_Price': [2000.0, 2500.0, 3000.0],
        'Modal_Price_T7': [2100.0, 2600.0, 3100.0],
        'Price_Change_7d': [2.0, 3.0, 1.0]
    })
    preds = np.array([2, 2, 2])
    scenario = EconomicParameters(
        storage_cost_per_quintal=20.0,
        quantity_loss_fraction=0.02,
        annual_carrying_rate=0.07,
        holding_period_days=7,
        transaction_cost_now=15.0,
        transaction_cost_later=20.0,
        carrying_cost_type='opportunity'
    )
    res = run_economic_backtest(df_synth, preds, scenario, quantity_per_decision=10.0)

    # Evaluate each row individually using canonical evaluate_sell_vs_store
    for i, row in df_synth.iterrows():
        eval_row = evaluate_sell_vs_store(10.0, row['Modal_Price'], row['Modal_Price_T7'], scenario)
        be_row = calculate_break_even_future_price(row['Modal_Price'], scenario)
        assert eval_row['break_even_price'] == pytest.approx(be_row['break_even_price'])

    # Backtest mean return stored must match average of individual evaluate_sell_vs_store
    model_stats = res["Model Signal (T)"]
    individual_delta_rs = [
        evaluate_sell_vs_store(10.0, r['Modal_Price'], r['Modal_Price_T7'], scenario)['incremental_benefit_per_quintal']
        for _, r in df_synth.iterrows()
    ]
    assert pytest.approx(model_stats["mean_incremental_return_rupees_per_stored_qtl"], abs=0.01) == np.mean(individual_delta_rs)


def test_backtest_carrying_cost_type_none_with_positive_rate():
    """
    Verify that when carrying_cost_type='none', carrying cost is strictly zero,
    even if annual_carrying_rate is positive (Task 1 & 2).
    """
    df_synth = pd.DataFrame({
        'Modal_Price': [2000.0, 2500.0],
        'Modal_Price_T7': [2200.0, 2700.0],
        'Price_Change_7d': [5.0, 5.0]
    })
    preds = np.array([2, 2])
    sc_none = EconomicParameters(
        storage_cost_per_quintal=20.0,
        quantity_loss_fraction=0.01,
        annual_carrying_rate=0.15,
        holding_period_days=7,
        carrying_cost_type='none'
    )
    sc_opp = EconomicParameters(
        storage_cost_per_quintal=20.0,
        quantity_loss_fraction=0.01,
        annual_carrying_rate=0.15,
        holding_period_days=7,
        carrying_cost_type='opportunity'
    )
    res_none = run_economic_backtest(df_synth, preds, sc_none)
    res_opp = run_economic_backtest(df_synth, preds, sc_opp)

    # When carrying_cost_type='none', returns must be strictly higher than when carrying cost is charged
    ret_none = res_none["Always Store"]["mean_incremental_return_rupees_per_stored_qtl"]
    ret_opp = res_opp["Always Store"]["mean_incremental_return_rupees_per_stored_qtl"]
    assert ret_none > ret_opp
    # Difference must equal exactly the carrying cost per quintal
    expected_carrying_diff = np.mean([p * 0.15 * 7 / 365.0 for p in [2000.0, 2500.0]])
    assert pytest.approx(ret_none - ret_opp, abs=0.05) == expected_carrying_diff


def test_backtest_quality_markdown_affects_breakeven_and_return():
    """
    Verify quality markdown d_q is applied exactly once to future price,
    strictly increases break-even price, and lowers realized return.
    """
    df_synth = pd.DataFrame({
        'Modal_Price': [2500.0],
        'Modal_Price_T7': [2650.0],
        'Price_Change_7d': [6.0]
    })
    preds = np.array([2])
    sc_no_dq = EconomicParameters(
        storage_cost_per_quintal=20.0,
        quantity_loss_fraction=0.01,
        annual_carrying_rate=0.07,
        quality_discount_fraction=0.0
    )
    sc_with_dq = EconomicParameters(
        storage_cost_per_quintal=20.0,
        quantity_loss_fraction=0.01,
        annual_carrying_rate=0.07,
        quality_discount_fraction=0.03  # 3% markdown
    )
    res_no = run_economic_backtest(df_synth, preds, sc_no_dq)
    res_dq = run_economic_backtest(df_synth, preds, sc_with_dq)

    ret_no = res_no["Always Store"]["mean_incremental_return_rupees_per_stored_qtl"]
    ret_dq = res_dq["Always Store"]["mean_incremental_return_rupees_per_stored_qtl"]
    assert ret_no > ret_dq
    # Check exact gross markdown: (1 - 0.01) * 2650 * 0.03 = 0.99 * 79.5 = 78.705
    assert pytest.approx(ret_no - ret_dq, abs=0.05) == 0.99 * 2650.0 * 0.03


def test_backtest_oracle_upper_bound_with_complex_costs():
    """
    Verify oracle remains upper bound across complex configurations
    (nonzero transaction costs, quality markdown, positive carry rate).
    """
    df_synth = pd.DataFrame({
        'Modal_Price': [1500.0, 2000.0, 2500.0, 3000.0, 3500.0],
        'Modal_Price_T7': [1450.0, 2150.0, 2400.0, 3300.0, 3200.0],
        'Price_Change_7d': [-2.0, 7.0, -1.0, 9.0, -5.0]
    })
    preds = np.array([0, 2, 0, 2, 0])
    scenario = EconomicParameters(
        storage_cost_per_quintal=30.0,
        handling_cost_per_quintal=5.0,
        quantity_loss_fraction=0.02,
        annual_carrying_rate=0.10,
        holding_period_days=7,
        transaction_cost_now=10.0,
        transaction_cost_later=15.0,
        quality_discount_fraction=0.02,
        carrying_cost_type='financing'
    )
    res = run_economic_backtest(df_synth, preds, scenario, quantity_per_decision=10.0)
    oracle_gain = res["Oracle Benchmark (Upper Bound)"]["aggregate_net_incremental_gain_rupees_10qtl_all_decisions"]
    for pol_name, stats in res.items():
        pol_gain = stats["aggregate_net_incremental_gain_rupees_10qtl_all_decisions"]
        assert oracle_gain >= pol_gain, f"Oracle {oracle_gain} failed to beat {pol_name} {pol_gain}"


def test_backtest_canonical_model_per_row_equivalence():
    """
    Regression test verifying exact equivalence between run_economic_backtest
    and evaluate_sell_vs_store on each individual decision row.
    """
    from src.economic_model import calculate_incremental_benefit_per_quintal, evaluate_sell_vs_store
    prices_t = np.array([1800.0, 2200.0, 2600.0, 3100.0])
    prices_t7 = np.array([1950.0, 2100.0, 2850.0, 3000.0])
    scenario = EconomicParameters(
        storage_cost_per_quintal=25.0,
        handling_cost_per_quintal=5.0,
        quantity_loss_fraction=0.015,
        annual_carrying_rate=0.08,
        holding_period_days=7,
        transaction_cost_now=8.0,
        transaction_cost_later=12.0,
        quality_discount_fraction=0.01,
        carrying_cost_type='opportunity'
    )
    # Vectorized incremental benefit
    vec_delta_r = calculate_incremental_benefit_per_quintal(prices_t, prices_t7, scenario)

    # Loop each row via evaluate_sell_vs_store
    for i in range(len(prices_t)):
        single_eval = evaluate_sell_vs_store(10.0, prices_t[i], prices_t7[i], scenario)
        assert pytest.approx(vec_delta_r[i], rel=1e-6) == single_eval["incremental_benefit_per_quintal"]
