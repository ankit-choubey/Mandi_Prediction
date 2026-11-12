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
    calculate_canonical_accounting,
    InputProvenance,
    ResearchEconomicRequest,
    ResearchEconomicResult,
    evaluate_research_economics,
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


def test_16_quality_markdown_discount():
    """
    Test 16: Nonzero quality markdown d_q reduces realized sale price and increases break-even.
    Formula: P_break_even = [P_T * (1 + i * h / 365) + c_s] / [(1 - L) * (1 - d_q)]

    Hand-calculated fixture:
    P_T = 2500, c_s = 20, i = 0.07, h = 7, L = 0.01, d_q = 0.01
    Numerator = 2500 * (1 + 0.07 * 7 / 365) + 20 = 2503.356164 + 20 = 2523.356164
    Denominator = (1 - 0.01) * (1 - 0.01) = 0.99 * 0.99 = 0.9801
    Expected P_break_even = 2523.356164 / 0.9801 = 2574.5905
    Expected req pct increase = ((2574.5905 - 2500) / 2500) * 100 = 2.9836%
    """
    params_no_dq = EconomicParameters(
        storage_cost_per_quintal=20.0,
        quantity_loss_fraction=0.01,
        annual_carrying_rate=0.07,
        holding_period_days=7,
        quality_discount_fraction=0.0
    )
    params_with_dq = EconomicParameters(
        storage_cost_per_quintal=20.0,
        quantity_loss_fraction=0.01,
        annual_carrying_rate=0.07,
        holding_period_days=7,
        quality_discount_fraction=0.01
    )

    be_no_dq = calculate_break_even_future_price(2500.0, params_no_dq)
    be_with_dq = calculate_break_even_future_price(2500.0, params_with_dq)

    # d_q must strictly increase break-even price
    assert be_with_dq["break_even_price"] > be_no_dq["break_even_price"]
    assert math.isclose(be_with_dq["break_even_price"], 2574.5905, rel_tol=1e-4)
    assert math.isclose(be_with_dq["required_percentage_increase"], 2.9836, rel_tol=1e-3)


def test_17_sensitivity_matrix_schemas_and_quality_discount():
    """
    Test 17: Schema verification for baseline and expanded sensitivity grids.
    Both must include Quality_Discount_Fraction and round appropriately.
    """
    from src.economic_model import (
        generate_sensitivity_matrix,
        generate_sensitivity_matrix_with_quality_discount
    )
    sens_base = generate_sensitivity_matrix(
        base_prices=(2000.0,), storage_costs=(20.0,), loss_fractions=(0.01,), annual_rates=(0.07,)
    )
    assert len(sens_base) == 1
    row_base = sens_base[0]
    assert "Quality_Discount_Fraction" in row_base
    assert row_base["Quality_Discount_Fraction"] == 0.0

    sens_dq = generate_sensitivity_matrix_with_quality_discount(
        base_prices=(2000.0,), storage_costs=(20.0,), loss_fractions=(0.01,),
        annual_rates=(0.07,), quality_discounts=(0.0, 0.02)
    )
    assert len(sens_dq) == 2
    assert sens_dq[0]["Quality_Discount_Fraction"] == 0.0
    assert sens_dq[1]["Quality_Discount_Fraction"] == 0.02
    assert sens_dq[1]["Break_Even_Future_Price_Rupees_Per_Qtl"] > sens_dq[0]["Break_Even_Future_Price_Rupees_Per_Qtl"]


# =====================================================================
# TASK MP-ECON-001: RESEARCH ECONOMICS CONTRACT & GATING TESTS
# =====================================================================

def test_canonical_accounting_reconciliation_and_invariants():
    """
    Test MP-ECON-001 Section B:
    Reconciles R_hold - R_sell == Delta_R and delta(p_break_even) == 0.
    Verifies quantity scaling preserves per-quintal delta.
    """
    import random
    rng = random.Random(42)

    # Hand-computed fixture 1
    p1 = EconomicParameters(storage_cost_per_quintal=50.0, quantity_loss_fraction=0.02, carrying_cost_type='none')
    r1 = calculate_canonical_accounting(10.0, 2500.0, 2650.0, p1)
    assert r1["r_sell"] == 25000.0
    assert r1["r_hold"] == 25470.0
    assert r1["delta_r"] == 470.0
    assert math.isclose(r1["p_break_even"], 2602.0408, rel_tol=1e-4)

    # Hand-computed fixture 2
    p2 = EconomicParameters(storage_cost_per_quintal=120.0, quantity_loss_fraction=0.02, carrying_cost_type='none')
    r2 = calculate_canonical_accounting(10.0, 2500.0, 2650.0, p2)
    assert r2["r_sell"] == 25000.0
    assert r2["r_hold"] == 24770.0
    assert r2["delta_r"] == -230.0
    assert math.isclose(r2["p_break_even"], 2673.4693, rel_tol=1e-4)

    # 100 Randomized parameter trials
    for _ in range(100):
        q = rng.uniform(1.0, 500.0)
        p0 = rng.uniform(500.0, 5000.0)
        ph = rng.uniform(500.0, 6000.0)
        cs = rng.uniform(0.0, 100.0)
        ch = rng.uniform(0.0, 20.0)
        ct = rng.uniform(0.0, 30.0)
        l = rng.uniform(0.0, 0.10)
        d = rng.uniform(0.0, 0.10)
        rate = rng.uniform(0.0, 0.20)
        tn = rng.uniform(0.0, 25.0)
        tl = rng.uniform(0.0, 25.0)

        params = EconomicParameters(
            storage_cost_per_quintal=cs,
            handling_cost_per_quintal=ch,
            incremental_transport_cost=ct,
            quantity_loss_fraction=l,
            quality_discount_fraction=d,
            annual_carrying_rate=rate,
            holding_period_days=7,
            transaction_cost_now=tn,
            transaction_cost_later=tl,
        )
        res = calculate_canonical_accounting(q, p0, ph, params)
        assert abs(res["r_hold"] - res["r_sell"] - res["delta_r"]) < 1e-7
        assert abs(res["delta_r"] - q * res["delta_per_quintal"]) < 1e-7

        # Invariance to Q scaling
        res_scaled = calculate_canonical_accounting(q * 10.0, p0, ph, params)
        assert abs(res_scaled["delta_per_quintal"] - res["delta_per_quintal"]) < 1e-7
        assert abs(res_scaled["p_break_even"] - res["p_break_even"]) < 1e-7
        assert abs(res_scaled["delta_r"] - 10.0 * res["delta_r"]) < 1e-6


def test_affine_uncertainty_propagation_and_break_even_relations():
    """
    Test MP-ECON-001 Section C:
    Verifies increasing affine property delta_lower <= delta_point <= delta_upper
    and correct classification of break_even_relation.
    """
    params = EconomicParameters(
        storage_cost_per_quintal=20.0,
        quantity_loss_fraction=0.01,
        annual_carrying_rate=0.07,
        holding_period_days=7,
    )
    p0 = 2000.0
    acct = calculate_canonical_accounting(10.0, p0, p0, params)
    p_be = acct["p_break_even"]

    # 1. Entirely above break-even
    req_above = ResearchEconomicRequest(
        quantity_quintals=10.0,
        current_price=p0,
        future_price_point=p_be + 100.0,
        future_price_lower=p_be + 20.0,
        future_price_upper=p_be + 150.0,
        params=params,
    )
    res_above = evaluate_research_economics(req_above)
    assert res_above.break_even_relation == "ENTIRELY_ABOVE_BREAK_EVEN"
    assert res_above.delta_per_quintal_lower <= res_above.delta_per_quintal_point <= res_above.delta_per_quintal_upper
    assert res_above.delta_per_quintal_lower > 0.0

    # 2. Entirely below break-even
    req_below = ResearchEconomicRequest(
        quantity_quintals=10.0,
        current_price=p0,
        future_price_point=p_be - 50.0,
        future_price_lower=p_be - 100.0,
        future_price_upper=p_be - 10.0,
        params=params,
    )
    res_below = evaluate_research_economics(req_below)
    assert res_below.break_even_relation == "ENTIRELY_BELOW_BREAK_EVEN"
    assert res_below.delta_per_quintal_lower <= res_below.delta_per_quintal_point <= res_below.delta_per_quintal_upper
    assert res_below.delta_per_quintal_upper < 0.0

    # 3. Straddles break-even
    req_straddle = ResearchEconomicRequest(
        quantity_quintals=10.0,
        current_price=p0,
        future_price_point=p_be + 10.0,
        future_price_lower=p_be - 30.0,
        future_price_upper=p_be + 50.0,
        params=params,
    )
    res_straddle = evaluate_research_economics(req_straddle)
    assert res_straddle.break_even_relation == "STRADDLES_BREAK_EVEN"
    assert res_straddle.delta_per_quintal_lower <= 0.0 <= res_straddle.delta_per_quintal_upper


def test_advisory_safety_gating_fail_closed():
    """
    Test MP-ECON-001 Section C & D:
    Ensures positive lower bound alone CANNOT authorize live advice.
    Operational status must be RESEARCH_ONLY, advisory_action BLOCKED, advisory_permitted False.
    """
    params = EconomicParameters(
        storage_cost_per_quintal=20.0,
        quantity_loss_fraction=0.01,
        annual_carrying_rate=0.07,
        holding_period_days=7,
    )
    # Even with huge gain (p_lower = 3000 vs p0 = 2000)
    req = ResearchEconomicRequest(
        quantity_quintals=10.0,
        current_price=2000.0,
        future_price_point=3200.0,
        future_price_lower=3000.0,
        future_price_upper=3400.0,
        params=params,
        provenance_map={
            "storage_cost": InputProvenance(20.0, "INR/quintal", "ILLUSTRATIVE", "Central Scenario"),
        }
    )
    res = evaluate_research_economics(req)
    assert res.break_even_relation == "ENTIRELY_ABOVE_BREAK_EVEN"
    assert res.operational_status == "RESEARCH_ONLY"
    assert res.advisory_action == "BLOCKED"
    assert res.advisory_permitted is False
    assert "POSITIVE_LOWER_BOUND_CANNOT_AUTHORIZE_FARMER_ADVICE" in res.gate_reasons
    assert "RETROSPECTIVE_RESEARCH_ONLY_NO_LIVE_ADVICE" in res.gate_reasons
    assert "UNVERIFIED_COMMERCIAL_COST_FEED" in res.gate_reasons


def test_research_economics_serialization_roundtrip():
    """Verify request and result dataclass serialization to dict and reconstruction."""
    req = ResearchEconomicRequest(
        quantity_quintals=50.0,
        current_price=2100.0,
        future_price_point=2250.0,
        future_price_lower=2180.0,
        future_price_upper=2320.0,
        holding_period_days=7,
        commodity="Wheat",
        district="Lucknow",
        market="Lucknow",
        is_reporting_normalization=True,
        provenance_map={
            "storage_cost": InputProvenance(17.30, "INR/quintal", "OBSERVED", "CWC Lucknow Tariff"),
            "quantity_loss": InputProvenance(0.01, "fraction", "ILLUSTRATIVE", "CIPHET"),
        }
    )
    d_req = req.to_dict()
    reloaded_req = ResearchEconomicRequest.from_dict(d_req)
    assert reloaded_req.quantity_quintals == req.quantity_quintals
    assert reloaded_req.commodity == req.commodity
    assert reloaded_req.is_reporting_normalization is True
    assert reloaded_req.provenance_map["storage_cost"].value == 17.30

    res = evaluate_research_economics(reloaded_req)
    d_res = res.to_dict()
    reloaded_res = ResearchEconomicResult.from_dict(d_res)
    assert reloaded_res.operational_status == res.operational_status
    assert reloaded_res.advisory_action == res.advisory_action
    assert reloaded_res.break_even_relation == res.break_even_relation
    assert abs(reloaded_res.p_break_even - res.p_break_even) < 1e-9
