"""
Unit Tests for Economic Decision Support Layer
APMC Mandi Market Intelligence System - Phase 4

Tests the 15 required mathematical and behavioral properties:
 1. Immediate-sale proceeds.
 2. Storage-sale proceeds.
 3. Incremental profit or loss.
 4. Break-even future price.
 5. Zero storage cost.
 6. Zero financing or opportunity cost.
 7. Nonzero storage loss.
 8. Cases where storing is economically better.
 9. Cases where selling immediately is economically better.
 10. Exact break-even equality case.
 11. Scaling quantity Q without changing per-quintal decision.
 12. Missing or invalid economic inputs (error handling).
 13. Cost-unit conversions and daily-to-period alignment.
 14. No double counting of financing and opportunity costs.
 15. Consistent handling of costs that cancel between strategies.
"""

import pytest
import math
from src.economic_model import (
    EconomicParameters,
    calculate_immediate_sale_proceeds,
    calculate_storage_sale_proceeds,
    calculate_break_even_future_price,
    evaluate_sell_vs_store,
)


# =====================================================================
# MANDATORY SPECIFICATION FIXTURES
# =====================================================================

def test_mandatory_fixture_1_storing_better():
    """
    Mandatory Test Fixture 1:
    Q = 10 quintals
    P_T = ₹2,500 per quintal
    P_T7 = ₹2,650 per quintal
    L = 0.02
    c_s = ₹50 per initial quintal
    i = 0
    h = 7

    Expected:
    R_sell = ₹25,000
    R_store = ₹25,470
    Delta_R = +₹470
    """
    params = EconomicParameters(
        storage_cost_per_quintal=50.0,
        quantity_loss_fraction=0.02,
        annual_carrying_rate=0.0,
        holding_period_days=7,
        carrying_cost_type='none'
    )
    result = evaluate_sell_vs_store(
        quantity_quintals=10.0,
        current_price=2500.0,
        future_price=2650.0,
        params=params
    )
    assert result["r_sell_net"] == pytest.approx(25000.0)
    assert result["r_store_net"] == pytest.approx(25470.0)
    assert result["incremental_benefit"] == pytest.approx(470.0)
    assert result["action"] == "STORE"


def test_mandatory_fixture_2_selling_better():
    """
    Mandatory Test Fixture 2:
    Same as Fixture 1 except c_s = ₹120 per initial quintal.

    Expected:
    R_store = ₹24,770
    Delta_R = -₹230
    Action = SELL
    """
    params = EconomicParameters(
        storage_cost_per_quintal=120.0,
        quantity_loss_fraction=0.02,
        annual_carrying_rate=0.0,
        holding_period_days=7,
        carrying_cost_type='none'
    )
    result = evaluate_sell_vs_store(
        quantity_quintals=10.0,
        current_price=2500.0,
        future_price=2650.0,
        params=params
    )
    assert result["r_sell_net"] == pytest.approx(25000.0)
    assert result["r_store_net"] == pytest.approx(24770.0)
    assert result["incremental_benefit"] == pytest.approx(-230.0)
    assert result["action"] == "SELL"


# =====================================================================
# INDIVIDUAL MATHEMATICAL PROPERTIES (1 - 15)
# =====================================================================

def test_1_immediate_sale_proceeds():
    """Test 1: Gross and net immediate sale proceeds without and with transaction costs."""
    res1 = calculate_immediate_sale_proceeds(quantity_quintals=20.0, current_price=3000.0)
    assert res1["gross_proceeds"] == 60000.0
    assert res1["transaction_cost"] == 0.0
    assert res1["net_proceeds"] == 60000.0

    res2 = calculate_immediate_sale_proceeds(
        quantity_quintals=20.0, current_price=3000.0, transaction_cost_per_quintal=25.0
    )
    assert res2["gross_proceeds"] == 60000.0
    assert res2["transaction_cost"] == 500.0
    assert res2["net_proceeds"] == 59500.0


def test_2_storage_sale_proceeds():
    """Test 2: Verification of gross and net storage proceeds decomposition."""
    params = EconomicParameters(
        storage_cost_per_quintal=30.0,
        quantity_loss_fraction=0.01,
        annual_carrying_rate=0.10,
        holding_period_days=7,
        carrying_cost_type='financing'
    )
    # Q = 50, P_T = 2000, P_T7 = 2100
    # Remaining Q = 50 * 0.99 = 49.5 quintals
    # Gross = 49.5 * 2100 = 103,950
    # Storage cost = 50 * 30 = 1,500
    # Carrying cost = 50 * 2000 * 0.10 * 7 / 365 = 100,000 * 0.10 * 7 / 365 = 191.78082
    # Net = 103,950 - 1,500 - 191.78082 = 102,258.21918
    res = calculate_storage_sale_proceeds(50.0, 2000.0, 2100.0, params)
    assert res["remaining_quantity_quintals"] == 49.5
    assert res["gross_proceeds"] == 103950.0
    assert res["storage_and_handling_cost"] == 1500.0
    expected_carrying = 50.0 * 2000.0 * 0.10 * 7 / 365.0
    assert math.isclose(res["carrying_cost"], expected_carrying, rel_tol=1e-5)
    expected_net = 103950.0 - 1500.0 - expected_carrying
    assert math.isclose(res["net_proceeds"], expected_net, rel_tol=1e-5)


def test_3_incremental_benefit_definition():
    """Test 3: Delta_R = R_store - R_sell strictly holds."""
    params = EconomicParameters(
        storage_cost_per_quintal=40.0,
        quantity_loss_fraction=0.015,
        annual_carrying_rate=0.08,
        holding_period_days=7
    )
    res = evaluate_sell_vs_store(15.0, 2200.0, 2350.0, params)
    assert math.isclose(res["incremental_benefit"], res["r_store_net"] - res["r_sell_net"], rel_tol=1e-6)
    assert math.isclose(res["incremental_benefit_per_quintal"], res["incremental_benefit"] / 15.0, rel_tol=1e-6)


def test_4_break_even_future_price_formula():
    """
    Test 4: Break-even price formula:
    P_break_even = [P_T * (1 + i * h / 365) + c_s] / (1 - L)
    At P_Th = P_break_even, Delta_R must equal 0.0 exactly.
    """
    params = EconomicParameters(
        storage_cost_per_quintal=45.0,
        quantity_loss_fraction=0.025,
        annual_carrying_rate=0.12,
        holding_period_days=7
    )
    P_T = 2800.0
    be_res = calculate_break_even_future_price(P_T, params)
    p_be = be_res["break_even_price"]

    # Verify that evaluating at p_be yields delta_r == 0
    eval_res = evaluate_sell_vs_store(10.0, P_T, p_be, params)
    assert math.isclose(eval_res["incremental_benefit"], 0.0, abs_tol=1e-5)
    assert eval_res["action"] == "INDIFFERENT"


def test_5_zero_storage_cost():
    """Test 5: When storage cost c_s = 0, break-even is determined solely by losses and financing."""
    params = EconomicParameters(
        storage_cost_per_quintal=0.0,
        quantity_loss_fraction=0.02,
        annual_carrying_rate=0.0,
        holding_period_days=7,
        carrying_cost_type='none'
    )
    # P_break_even = P_T / (1 - L) = 2000 / 0.98 = 2040.8163
    be = calculate_break_even_future_price(2000.0, params)
    assert math.isclose(be["break_even_price"], 2000.0 / 0.98, rel_tol=1e-6)


def test_6_zero_financing_cost():
    """Test 6: When carrying rate i = 0, no carrying cost is deducted."""
    params = EconomicParameters(
        storage_cost_per_quintal=50.0,
        quantity_loss_fraction=0.01,
        annual_carrying_rate=0.0,
        holding_period_days=7,
        carrying_cost_type='none'
    )
    res = calculate_storage_sale_proceeds(10.0, 2500.0, 2600.0, params)
    assert res["carrying_cost"] == 0.0


def test_7_nonzero_storage_loss():
    """Test 7: Physical loss reduces saleable quantity directly and cannot be negative."""
    params = EconomicParameters(
        storage_cost_per_quintal=0.0,
        quantity_loss_fraction=0.05,  # 5% physical loss
        annual_carrying_rate=0.0,
        holding_period_days=7
    )
    res = calculate_storage_sale_proceeds(100.0, 2000.0, 2000.0, params)
    assert res["remaining_quantity_quintals"] == 95.0
    # Sold at same price P_T = 2000:
    # Gross proceeds = 95 * 2000 = 190,000 vs immediate 200,000 -> Loss of 10,000
    assert res["gross_proceeds"] == 190000.0


def test_8_case_where_storing_is_economically_better():
    """Test 8: High price increase overcomes storage, loss, and carrying costs."""
    params = EconomicParameters(
        storage_cost_per_quintal=30.0,
        quantity_loss_fraction=0.01,
        annual_carrying_rate=0.07,
        holding_period_days=7
    )
    # P_T = 2000, P_Th = 2300 (+15% surge)
    res = evaluate_sell_vs_store(10.0, 2000.0, 2300.0, params)
    assert res["action"] == "STORE"
    assert res["incremental_benefit"] > 0.0


def test_9_case_where_selling_immediately_is_economically_better():
    """Test 9: Modest price increase does not cover costs; sell immediately preferred."""
    params = EconomicParameters(
        storage_cost_per_quintal=50.0,
        quantity_loss_fraction=0.02,
        annual_carrying_rate=0.10,
        holding_period_days=7
    )
    # P_T = 2000, P_Th = 2020 (+1.0% change, below break-even)
    res = evaluate_sell_vs_store(10.0, 2000.0, 2020.0, params)
    assert res["action"] == "SELL"
    assert res["incremental_benefit"] < 0.0


def test_10_exact_break_even_equality():
    """Test 10: At exact break-even, net proceeds match within tolerance and action is INDIFFERENT."""
    params = EconomicParameters(
        storage_cost_per_quintal=60.0,
        quantity_loss_fraction=0.03,
        annual_carrying_rate=0.05,
        holding_period_days=7
    )
    P_T = 2400.0
    be = calculate_break_even_future_price(P_T, params)["break_even_price"]
    res = evaluate_sell_vs_store(25.0, P_T, be, params)
    assert res["action"] == "INDIFFERENT"
    assert math.isclose(res["r_sell_net"], res["r_store_net"], abs_tol=1e-5)


def test_11_scaling_quantity_preserves_per_quintal_decision():
    """Test 11: Scaling Q from 1 to 10,000 does not alter per-quintal return or action."""
    params = EconomicParameters(
        storage_cost_per_quintal=40.0,
        quantity_loss_fraction=0.015,
        annual_carrying_rate=0.08,
        holding_period_days=7
    )
    P_T, P_Th = 2500.0, 2600.0
    res_1 = evaluate_sell_vs_store(1.0, P_T, P_Th, params)
    res_100 = evaluate_sell_vs_store(100.0, P_T, P_Th, params)
    res_5000 = evaluate_sell_vs_store(5000.0, P_T, P_Th, params)

    assert res_1["action"] == res_100["action"] == res_5000["action"]
    assert math.isclose(
        res_1["incremental_benefit_per_quintal"],
        res_100["incremental_benefit_per_quintal"],
        rel_tol=1e-6
    )
    assert math.isclose(
        res_1["incremental_benefit_per_quintal"],
        res_5000["incremental_benefit_per_quintal"],
        rel_tol=1e-6
    )


def test_12_invalid_or_missing_inputs_handled_safely():
    """Test 12: Invalid parameters (negative prices, L >= 1, negative costs) raise ValueError."""
    # Negative price
    with pytest.raises(ValueError, match="Current price P_T must be positive"):
        calculate_immediate_sale_proceeds(10.0, -2500.0)

    with pytest.raises(ValueError, match="Future price P_Th must be positive"):
        params = EconomicParameters()
        calculate_storage_sale_proceeds(10.0, 2500.0, -100.0, params)

    # Quantity zero or negative
    with pytest.raises(ValueError, match="Quantity Q must be positive"):
        calculate_immediate_sale_proceeds(0.0, 2500.0)

    # Loss fraction >= 1
    with pytest.raises(ValueError, match="Loss fraction L must be in"):
        EconomicParameters(quantity_loss_fraction=1.0)

    with pytest.raises(ValueError, match="Loss fraction L must be in"):
        EconomicParameters(quantity_loss_fraction=-0.05)

    # Negative costs
    with pytest.raises(ValueError, match="Storage cost c_s must be non-negative"):
        EconomicParameters(storage_cost_per_quintal=-10.0)


def test_13_cost_unit_conversions():
    """Test 13: Per-day rates correctly compound to period costs (e.g. ₹2.5/qtl/day for 7 days = ₹17.5/qtl)."""
    daily_rate = 2.5
    h = 7
    total_c_s = daily_rate * h
    params = EconomicParameters(
        storage_cost_per_quintal=total_c_s,
        quantity_loss_fraction=0.01,
        holding_period_days=h
    )
    res = calculate_storage_sale_proceeds(10.0, 2000.0, 2100.0, params)
    assert res["storage_and_handling_cost"] == 10.0 * 17.5


def test_14_no_double_counting_carrying_cost():
    """
    Test 14: Safeguard A & B:
    Carrying cost type must be EITHER financing OR opportunity, not both.
    When set to 'none', carrying cost is zero.
    """
    params_opp = EconomicParameters(
        annual_carrying_rate=0.10, holding_period_days=7, carrying_cost_type='opportunity'
    )
    params_fin = EconomicParameters(
        annual_carrying_rate=0.10, holding_period_days=7, carrying_cost_type='financing'
    )
    params_none = EconomicParameters(
        annual_carrying_rate=0.10, holding_period_days=7, carrying_cost_type='none'
    )

    res_opp = calculate_storage_sale_proceeds(10.0, 2000.0, 2100.0, params_opp)
    res_fin = calculate_storage_sale_proceeds(10.0, 2000.0, 2100.0, params_fin)
    res_none = calculate_storage_sale_proceeds(10.0, 2000.0, 2100.0, params_none)

    # Opportunity and Financing yield identical single carrying cost
    assert math.isclose(res_opp["carrying_cost"], res_fin["carrying_cost"], rel_tol=1e-6)
    assert res_none["carrying_cost"] == 0.0
    # No additive double counting
    assert res_opp["carrying_cost"] < (10.0 * 2000.0 * 0.10 * 7 / 365.0) * 1.5


def test_15_costs_that_cancel_between_strategies():
    """
    Test 15: If an identical transaction cost applies at Date T and Date T+h (with L=0),
    it cancels out in Delta_R.
    """
    params_no_trans = EconomicParameters(
        storage_cost_per_quintal=50.0,
        quantity_loss_fraction=0.0,
        holding_period_days=7,
        transaction_cost_now=0.0,
        transaction_cost_later=0.0
    )
    params_trans_cancel = EconomicParameters(
        storage_cost_per_quintal=50.0,
        quantity_loss_fraction=0.0,
        holding_period_days=7,
        transaction_cost_now=30.0,
        transaction_cost_later=30.0
    )
    res_no = evaluate_sell_vs_store(10.0, 2000.0, 2100.0, params_no_trans)
    res_cancel = evaluate_sell_vs_store(10.0, 2000.0, 2100.0, params_trans_cancel)

    assert math.isclose(res_no["incremental_benefit"], res_cancel["incremental_benefit"], rel_tol=1e-6)
