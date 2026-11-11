"""
Economic Decision Support Module
APMC Mandi Market Intelligence System - Phase 4 Research

Implements economic modeling for comparing immediate harvest sale at Date T
against short-term storage and sale at Date T+h (default h = 7 calendar days).

Notation and Definitions:
  Q       = Quantity of produce harvested, in quintals (1 quintal = 100 kg)
  P_T     = Spot modal price at date T, in rupees per quintal (₹ / quintal)
  P_Th    = Price observed exactly h calendar days later (₹ / quintal)
  L       = Fraction of original quantity lost during storage (0 <= L < 1)
  c_s     = Incremental storage and handling cost per initial quintal (₹ / quintal)
  i       = Annual financing or opportunity-cost rate, as a decimal (e.g. 0.07 = 7% p.a.)
  h       = Holding period in calendar days (typically h = 7)
  d_q     = Quality discount factor on realized sale price (0 <= d_q < 1)

Mathematical Formulations:
  Immediate sale:
    R_sell = Q * P_T - Q * c_trans_now

  Gross storage proceeds:
    R_store_gross = Q * (1 - L) * (1 - d_q) * P_Th

  Net storage proceeds:
    R_store = R_store_gross - Q * c_s - Carrying_Cost - Q * (1 - L) * c_trans_later

  Incremental benefit of storing:
    Delta_R = R_store - R_sell

  Break-even future price:
    P_break_even = [P_T * (1 + i * h / 365) + c_s] / [(1 - L) * (1 - d_q)]

CRITICAL SAFEGUARDS:
  1. No double counting: carrying cost represents EITHER borrowing interest OR opportunity cost.
  2. Physical loss (L) is strictly distinct from price markdown (d_q).
  3. Costs that cancel between strategies are not counted as storage-specific.
  4. Explicit error handling for L >= 1, non-positive prices, negative costs, or division-by-zero.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, Literal, Union
from datetime import date, datetime
import numpy as np

from src.health_status import (
    RecommendationSafetyGate,
    SafetyGateDecision,
    RecommendationStatus,
    OperationalState,
    FreshnessStatus,
    BLOCKED_RECOMMENDATION_MESSAGE
)


@dataclass(frozen=True)
class EconomicParameters:
    """
    Configurable parameters for sell-versus-store economic evaluation.
    All costs and rates must be non-negative and explicitly documented.
    """
    storage_cost_per_quintal: float = 0.0        # c_s: ₹ / quintal for holding period h
    quantity_loss_fraction: float = 0.0          # L: fractional loss (0 <= L < 1)
    annual_carrying_rate: float = 0.0            # i: decimal per annum (e.g., 0.07 for 7%)
    holding_period_days: int = 7                 # h: holding period in calendar days
    carrying_cost_type: Literal['opportunity', 'financing', 'none'] = 'opportunity'
    quality_discount_fraction: float = 0.0       # d_q: markdown fraction (0 <= d_q < 1)
    handling_cost_per_quintal: float = 0.0       # incremental handling (in ₹ / quintal)
    transaction_cost_now: float = 0.0            # selling cost now (₹ / quintal)
    transaction_cost_later: float = 0.0          # selling cost later (₹ / quintal)
    scenario_name: str = "custom"

    def __post_init__(self):
        if self.holding_period_days <= 0:
            raise ValueError(f"Holding period h must be positive, got {self.holding_period_days}")
        if not (0.0 <= self.quantity_loss_fraction < 1.0):
            raise ValueError(
                f"Loss fraction L must be in [0, 1), got {self.quantity_loss_fraction}"
            )
        if not (0.0 <= self.quality_discount_fraction < 1.0):
            raise ValueError(
                f"Quality discount d_q must be in [0, 1), got {self.quality_discount_fraction}"
            )
        if self.storage_cost_per_quintal < 0.0:
            raise ValueError(
                f"Storage cost c_s must be non-negative, got {self.storage_cost_per_quintal}"
            )
        if self.annual_carrying_rate < 0.0:
            raise ValueError(
                f"Annual rate i must be non-negative, got {self.annual_carrying_rate}"
            )
        if self.handling_cost_per_quintal < 0.0:
            raise ValueError(
                f"Handling cost must be non-negative, got {self.handling_cost_per_quintal}"
            )


def calculate_immediate_sale_proceeds(
    quantity_quintals: float,
    current_price: float,
    transaction_cost_per_quintal: float = 0.0
) -> Dict[str, float]:
    """
    Calculate immediate sale gross and net proceeds at Date T.

    Returns:
      gross_proceeds: Q * P_T
      transaction_cost: Q * transaction_cost_per_quintal
      net_proceeds: gross_proceeds - transaction_cost
    """
    if quantity_quintals <= 0.0:
        raise ValueError(f"Quantity Q must be positive, got {quantity_quintals}")
    if current_price <= 0.0:
        raise ValueError(f"Current price P_T must be positive, got {current_price}")
    if transaction_cost_per_quintal < 0.0:
        raise ValueError(f"Transaction cost cannot be negative, got {transaction_cost_per_quintal}")

    gross = quantity_quintals * current_price
    trans = quantity_quintals * transaction_cost_per_quintal
    net = gross - trans
    return {
        "gross_proceeds": gross,
        "transaction_cost": trans,
        "net_proceeds": net
    }


def calculate_storage_sale_proceeds(
    quantity_quintals: float,
    current_price: float,
    future_price: float,
    params: EconomicParameters
) -> Dict[str, float]:
    """
    Calculate net storage proceeds for produce stored and sold at Date T+h.

    Carrying cost is calculated as:
      Q * P_T * (i * h / 365)
    and strictly represents EITHER financing interest OR opportunity cost of cash,
    never both simultaneously (Safeguard A & B).
    """
    if quantity_quintals <= 0.0:
        raise ValueError(f"Quantity Q must be positive, got {quantity_quintals}")
    if current_price <= 0.0:
        raise ValueError(f"Current price P_T must be positive, got {current_price}")
    if future_price <= 0.0:
        raise ValueError(f"Future price P_Th must be positive, got {future_price}")

    # Physical quantity remaining after loss
    remaining_quantity = quantity_quintals * (1.0 - params.quantity_loss_fraction)

    # Realized unit price after quality discount
    effective_future_price = future_price * (1.0 - params.quality_discount_fraction)

    # Gross storage revenue
    gross_proceeds = remaining_quantity * effective_future_price

    # Total incremental direct storage and handling cost
    total_unit_storage_cost = params.storage_cost_per_quintal + params.handling_cost_per_quintal
    storage_and_handling_cost = quantity_quintals * total_unit_storage_cost

    # Financing / Opportunity carrying cost
    if params.carrying_cost_type in ('financing', 'opportunity') and params.annual_carrying_rate > 0.0:
        carrying_cost = (
            quantity_quintals * current_price * params.annual_carrying_rate * params.holding_period_days / 365.0
        )
    else:
        carrying_cost = 0.0

    # Transaction cost at future sale
    future_trans_cost = remaining_quantity * params.transaction_cost_later

    net_proceeds = gross_proceeds - storage_and_handling_cost - carrying_cost - future_trans_cost

    return {
        "remaining_quantity_quintals": remaining_quantity,
        "effective_future_price": effective_future_price,
        "gross_proceeds": gross_proceeds,
        "storage_and_handling_cost": storage_and_handling_cost,
        "carrying_cost": carrying_cost,
        "future_transaction_cost": future_trans_cost,
        "net_proceeds": net_proceeds
    }


def calculate_break_even_future_price(
    current_price: Union[float, np.ndarray],
    params: EconomicParameters
) -> Dict[str, Any]:
    """
    Calculate the exact future price P_break_even required for storage to match immediate sale.

    Formula:
      P_break_even = [P_T * (1 + i * h / 365) + c_s + c_handling + Delta_trans] / [(1 - L) * (1 - d_q)]
      where Delta_trans = c_trans_later * (1 - L) - c_trans_now
            rate_factor = (i * h / 365) if carrying_cost_type in ('financing', 'opportunity') else 0.0

    Supports both scalar float and numpy array inputs.
    """
    current_price_arr = np.asarray(current_price)
    if np.any(current_price_arr <= 0.0):
        raise ValueError(f"Current price P_T must be positive, got {current_price}")

    effective_loss_multiplier = (1.0 - params.quantity_loss_fraction) * (1.0 - params.quality_discount_fraction)
    if effective_loss_multiplier <= 0.0:
        raise ZeroDivisionError("Effective quantity retention after loss is zero; break-even is impossible.")

    rate_factor = (
        (params.annual_carrying_rate * params.holding_period_days / 365.0)
        if params.carrying_cost_type in ('financing', 'opportunity') else 0.0
    )

    total_direct_costs = params.storage_cost_per_quintal + params.handling_cost_per_quintal

    # Net transaction cost differential per initial quintal
    trans_diff = (
        params.transaction_cost_later * (1.0 - params.quantity_loss_fraction)
        - params.transaction_cost_now
    )

    numerator = current_price_arr * (1.0 + rate_factor) + total_direct_costs + trans_diff
    p_break_even = numerator / effective_loss_multiplier

    required_pct_change = ((p_break_even - current_price_arr) / current_price_arr) * 100.0

    if np.isscalar(current_price):
        return {
            "break_even_price": float(p_break_even),
            "required_percentage_increase": float(required_pct_change),
            "current_price": float(current_price)
        }
    else:
        return {
            "break_even_price": p_break_even,
            "required_percentage_increase": required_pct_change,
            "current_price": current_price_arr
        }


def calculate_incremental_benefit_per_quintal(
    current_price: Union[float, np.ndarray],
    future_price: Union[float, np.ndarray],
    params: EconomicParameters
) -> Union[float, np.ndarray]:
    """
    Calculate the net incremental benefit of storage per initial quintal (Delta_R / Q).
    Canonical formula strictly matching evaluate_sell_vs_store:
      Delta_r = R_store/Q - R_sell/Q
              = (1 - L)(1 - d_q) * P_Th - P_T * (1 + rate_factor) - (c_s + c_handling) - trans_diff
      where trans_diff = c_trans_later * (1 - L) - c_trans_now
            rate_factor = (i * h / 365) if carrying_cost_type in ('financing', 'opportunity') else 0.0

    Supports both scalar float and numpy array inputs.
    """
    p_t = np.asarray(current_price)
    p_th = np.asarray(future_price)
    if np.any(p_t <= 0.0):
        raise ValueError(f"Current price P_T must be positive, got {current_price}")
    if np.any(p_th <= 0.0):
        raise ValueError(f"Future price P_Th must be positive, got {future_price}")

    l_eff = (1.0 - params.quantity_loss_fraction) * (1.0 - params.quality_discount_fraction)
    rate_factor = (
        (params.annual_carrying_rate * params.holding_period_days / 365.0)
        if params.carrying_cost_type in ('financing', 'opportunity') else 0.0
    )
    total_direct_costs = params.storage_cost_per_quintal + params.handling_cost_per_quintal
    trans_diff = (
        params.transaction_cost_later * (1.0 - params.quantity_loss_fraction)
        - params.transaction_cost_now
    )

    delta_r = l_eff * p_th - p_t * (1.0 + rate_factor) - total_direct_costs - trans_diff
    if np.isscalar(current_price) and np.isscalar(future_price):
        return float(delta_r)
    return delta_r


def evaluate_sell_vs_store(
    quantity_quintals: float,
    current_price: float,
    future_price: float,
    params: EconomicParameters,
    observation_date: Optional[Union[str, date, datetime]] = None,
    reference_date: Optional[Union[str, date, datetime]] = None,
    operational_state: Optional[Any] = None,
    is_demo: bool = False,
    is_historical_analysis: bool = False,
    source_available: bool = True,
    has_verified_fresh_alternative: bool = False,
    safety_gate: Optional[RecommendationSafetyGate] = None,
) -> Dict[str, Any]:
    """
    Complete sell-versus-store economic evaluation for a single decision point.

    Returns structured results including incremental net benefit (Delta_R),
    per-quintal benefit (delta_r), break-even price, and economic recommendation.

    When observation_date, operational_state, is_demo, or is_historical_analysis is supplied,
    the operational safety gate is evaluated. If data is STALE (>5 days), missing, malformed, future-dated,
    down without fresh alternatives, uninitialized, partial, or quarantined:
    - action is set to 'BLOCKED'
    - recommendation_status is set to 'BLOCKED'
    - message is set to BLOCKED_RECOMMENDATION_MESSAGE
    """
    sell_res = calculate_immediate_sale_proceeds(
        quantity_quintals=quantity_quintals,
        current_price=current_price,
        transaction_cost_per_quintal=params.transaction_cost_now
    )

    store_res = calculate_storage_sale_proceeds(
        quantity_quintals=quantity_quintals,
        current_price=current_price,
        future_price=future_price,
        params=params
    )

    break_even = calculate_break_even_future_price(
        current_price=current_price,
        params=params
    )

    r_sell = sell_res["net_proceeds"]
    r_store = store_res["net_proceeds"]
    delta_r = r_store - r_sell
    delta_r_per_quintal = delta_r / quantity_quintals

    # Determine default unconstrained economic action
    tolerance = 1e-6
    if delta_r > tolerance:
        raw_action = "STORE"
    elif delta_r < -tolerance:
        raw_action = "SELL"
    else:
        raw_action = "INDIFFERENT"

    actual_pct_change = ((future_price - current_price) / current_price) * 100.0

    # Evaluate safety gate if context or gate is provided
    gate_applied = (
        observation_date is not None
        or reference_date is not None
        or operational_state is not None
        or is_demo
        or is_historical_analysis
        or not source_available
        or safety_gate is not None
    )

    gate_decision: Optional[SafetyGateDecision] = None
    if gate_applied:
        # Convert string or datetime reference_date if needed
        ref_d: Optional[date] = None
        if reference_date is not None:
            if isinstance(reference_date, datetime):
                ref_d = reference_date.date()
            elif isinstance(reference_date, date):
                ref_d = reference_date
            elif isinstance(reference_date, str):
                try:
                    ref_d = datetime.strptime(reference_date[:10], "%Y-%m-%d").date()
                except ValueError:
                    ref_d = None

        gate = safety_gate or RecommendationSafetyGate(current_ref_date=ref_d)
        gate_decision = gate.evaluate_gate(
            observation_date=observation_date,
            operational_state=operational_state,
            is_demo=is_demo,
            is_historical_analysis=is_historical_analysis,
            source_available=source_available,
            has_verified_fresh_alternative=has_verified_fresh_alternative
        )

    if gate_decision and not gate_decision.is_permitted:
        action = "BLOCKED"
        rec_status = gate_decision.recommendation_status
        message = gate_decision.message
        blocked_reason = gate_decision.blocked_reason or BLOCKED_RECOMMENDATION_MESSAGE
        is_actionable_advisory = False
    elif gate_decision:
        action = raw_action
        rec_status = gate_decision.recommendation_status
        message = gate_decision.message
        blocked_reason = None
        is_actionable_advisory = (rec_status in (RecommendationStatus.ACTIVE.value, RecommendationStatus.DELAYED.value))
    else:
        # Pure mathematical simulation without verified observation context
        action = raw_action
        rec_status = RecommendationStatus.SIMULATION_ONLY.value
        message = (
            "Pure mathematical simulation without verified observation date or market freshness. "
            "This output is for research/parameter testing and cannot be presented as an active farmer recommendation."
        )
        blocked_reason = None
        is_actionable_advisory = False

    payload: Dict[str, Any] = {
        "action": action,
        "raw_economic_action": raw_action,
        "is_actionable_advisory": is_actionable_advisory,
        "quantity_quintals": quantity_quintals,
        "current_price": current_price,
        "future_price": future_price,
        "actual_percentage_change": actual_pct_change,
        "r_sell_net": r_sell,
        "r_store_net": r_store,
        "incremental_benefit": delta_r,
        "incremental_benefit_per_quintal": delta_r_per_quintal,
        "break_even_price": break_even["break_even_price"],
        "required_percentage_increase": break_even["required_percentage_increase"],
        "storage_cost_incurred": store_res["storage_and_handling_cost"],
        "carrying_cost_incurred": store_res["carrying_cost"],
        "physical_loss_quintals": quantity_quintals * params.quantity_loss_fraction,
        "params": params,
        "recommendation_status": rec_status,
        "message": message,
    }

    if blocked_reason:
        payload["blocked_reason"] = blocked_reason
    if gate_decision:
        payload["safety_gate"] = gate_decision.to_dict()

    return payload


def evaluate_farmer_storage_recommendation(
    quantity_quintals: float,
    current_price: float,
    future_price: float,
    params: EconomicParameters,
    observation_date: Optional[Union[str, date, datetime]] = None,
    reference_date: Optional[Union[str, date, datetime]] = None,
    operational_state: Optional[Any] = None,
    is_demo: bool = False,
    is_historical_analysis: bool = False,
    source_available: bool = True,
    has_verified_fresh_alternative: bool = False,
    safety_gate: Optional[RecommendationSafetyGate] = None,
) -> Dict[str, Any]:
    """
    Primary farmer-facing storage recommendation interface with mandatory safety gating.

    Requires an explicit observation date. If observation date is omitted,
    malformed, stale (>5 days), future-dated, or if the pipeline is down, uninitialized,
    partial, or quarantined, the recommendation is hard-blocked with action='BLOCKED'
    and recommendation_status='BLOCKED':
    "Insufficient information to recommend storage. Latest market-price data is stale or unavailable."
    """
    ref_d: Optional[date] = None
    if reference_date is not None:
        if isinstance(reference_date, datetime):
            ref_d = reference_date.date()
        elif isinstance(reference_date, date):
            ref_d = reference_date
        elif isinstance(reference_date, str):
            try:
                ref_d = datetime.strptime(reference_date[:10], "%Y-%m-%d").date()
            except ValueError:
                ref_d = None

    gate = safety_gate or RecommendationSafetyGate(current_ref_date=ref_d)
    gate_decision = gate.evaluate_gate(
        observation_date=observation_date,
        operational_state=operational_state,
        is_demo=is_demo,
        is_historical_analysis=is_historical_analysis,
        source_available=source_available,
        has_verified_fresh_alternative=has_verified_fresh_alternative
    )

    return evaluate_sell_vs_store(
        quantity_quintals=quantity_quintals,
        current_price=current_price,
        future_price=future_price,
        params=params,
        observation_date=observation_date,
        reference_date=reference_date,
        operational_state=operational_state,
        is_demo=is_demo,
        is_historical_analysis=is_historical_analysis,
        source_available=source_available,
        has_verified_fresh_alternative=has_verified_fresh_alternative,
        safety_gate=gate
    )


def get_default_scenarios() -> Dict[str, EconomicParameters]:
    """
    Illustrative reference-informed scenarios.

    IMPORTANT PROVENANCE CAVEAT:
    These parameter values represent illustrative research assumptions informed by
    official benchmarks (CWC RWC tariffs FY 2026-27, MoFPI/ICAR-CIPHET post-harvest
    loss reports 2022, and Indian agricultural credit benchmarks).
    They are NOT locally validated farmgate measurements and should not be construed
    as empirical farmer-level parameters for individual APMC mandis.
    """
    return {
        "Conservative": EconomicParameters(
            storage_cost_per_quintal=35.0,        # Illustrative: ₹17.3 CWC slab benchmark + ₹17.7 local handling/porterage
            quantity_loss_fraction=0.020,         # Illustrative: 2.0% 7-day shrinkage assumption for vulnerable produce
            annual_carrying_rate=0.12,            # Illustrative: 12% p.a. informal/micro-credit borrowing rate benchmark
            holding_period_days=7,
            carrying_cost_type='financing',
            quality_discount_fraction=0.010,      # Illustrative: 1% quality markdown on sale
            scenario_name="Conservative"
        ),
        "Central": EconomicParameters(
            storage_cost_per_quintal=20.0,        # Illustrative: ₹17.3 CWC standard warehouse reference + ₹2.7 basic handling
            quantity_loss_fraction=0.010,         # Illustrative: 1.0% physical shrinkage assumption over 7 days
            annual_carrying_rate=0.07,            # Illustrative: 7% p.a. Kisan Credit Card (KCC) rate benchmark
            holding_period_days=7,
            carrying_cost_type='opportunity',
            quality_discount_fraction=0.000,
            scenario_name="Central"
        ),
        "Optimistic": EconomicParameters(
            storage_cost_per_quintal=10.0,        # Illustrative: Low-cost on-farm / cooperative PACS storage assumption
            quantity_loss_fraction=0.005,         # Illustrative: 0.5% physical loss assumption for durable grains
            annual_carrying_rate=0.04,            # Illustrative: 4% p.a. prompt-repayment subvention KCC rate benchmark
            holding_period_days=7,
            carrying_cost_type='opportunity',
            quality_discount_fraction=0.000,
            scenario_name="Optimistic"
        )
    }


def generate_sensitivity_matrix(
    base_prices=(1500.0, 2500.0, 3500.0),
    storage_costs=(10.0, 20.0, 35.0, 50.0),
    loss_fractions=(0.005, 0.010, 0.020, 0.050),
    annual_rates=(0.04, 0.07, 0.12)
) -> list:
    """
    Generate sensitivity records exploring required break-even future prices
    and required percentage price increases across variations in costs, losses, and rates,
    holding quality markdown d_q = 0.0.
    """
    records = []
    for p_base in base_prices:
        for c_s in storage_costs:
            for l in loss_fractions:
                for r in annual_rates:
                    params = EconomicParameters(
                        storage_cost_per_quintal=c_s,
                        quantity_loss_fraction=l,
                        annual_carrying_rate=r,
                        holding_period_days=7,
                        carrying_cost_type='opportunity',
                        quality_discount_fraction=0.0
                    )
                    be = calculate_break_even_future_price(p_base, params)
                    records.append({
                        "Base_Price_Rupees_Per_Qtl": p_base,
                        "Storage_Cost_Rupees_Per_Qtl": c_s,
                        "Loss_Fraction": l,
                        "Loss_Percent": l * 100.0,
                        "Quality_Discount_Fraction": 0.0,
                        "Quality_Discount_Percent": 0.0,
                        "Annual_Carrying_Rate": r,
                        "Annual_Carrying_Rate_Percent": r * 100.0,
                        "Holding_Period_Days": 7,
                        "Break_Even_Future_Price_Rupees_Per_Qtl": round(be["break_even_price"], 2),
                        "Required_Price_Increase_Percent": round(be["required_percentage_increase"], 2)
                    })
    return records


def generate_sensitivity_matrix_with_quality_discount(
    base_prices=(1500.0, 2500.0, 3500.0),
    storage_costs=(10.0, 20.0, 35.0, 50.0),
    loss_fractions=(0.005, 0.010, 0.020, 0.050),
    annual_rates=(0.04, 0.07, 0.12),
    quality_discounts=(0.0, 0.010, 0.030, 0.050)
) -> list:
    """
    Generate an expanded sensitivity matrix varying quality discount d_q
    alongside storage costs, losses, and carrying rates.
    """
    records = []
    for p_base in base_prices:
        for c_s in storage_costs:
            for l in loss_fractions:
                for r in annual_rates:
                    for dq in quality_discounts:
                        params = EconomicParameters(
                            storage_cost_per_quintal=c_s,
                            quantity_loss_fraction=l,
                            annual_carrying_rate=r,
                            holding_period_days=7,
                            carrying_cost_type='opportunity',
                            quality_discount_fraction=dq
                        )
                        be = calculate_break_even_future_price(p_base, params)
                        records.append({
                            "Base_Price_Rupees_Per_Qtl": p_base,
                            "Storage_Cost_Rupees_Per_Qtl": c_s,
                            "Loss_Fraction": l,
                            "Loss_Percent": l * 100.0,
                            "Quality_Discount_Fraction": dq,
                            "Quality_Discount_Percent": dq * 100.0,
                            "Annual_Carrying_Rate": r,
                            "Annual_Carrying_Rate_Percent": r * 100.0,
                            "Holding_Period_Days": 7,
                            "Break_Even_Future_Price_Rupees_Per_Qtl": round(be["break_even_price"], 2),
                            "Required_Price_Increase_Percent": round(be["required_percentage_increase"], 2)
                        })
    return records

