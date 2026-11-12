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

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, Literal, Union, List, Tuple
from datetime import date, datetime
import math
import numpy as np

from src.health_status import (
    RecommendationSafetyGate,
    SafetyGateDecision,
    RecommendationStatus,
    OperationalState,
    FreshnessStatus,
    BLOCKED_RECOMMENDATION_MESSAGE
)


def _validate_numeric(
    val: Any,
    field_name: str,
    *,
    min_val: Optional[float] = None,
    max_val: Optional[float] = None,
    strictly_positive: bool = False,
    strictly_less_than_max: bool = False,
    integer_only: bool = False,
) -> None:
    """
    Validates that a field is numeric, not a boolean, finite, and within valid domain bounds.
    Does not rely on assert or Literal annotations.
    """
    if type(val) is bool or isinstance(val, bool):
        raise ValueError(f"Field '{field_name}' cannot be a boolean: {val}")
    if integer_only:
        if not isinstance(val, int):
            raise ValueError(f"Field '{field_name}' must be an integer, got {type(val).__name__}: {val}")
    else:
        if not isinstance(val, (int, float)):
            raise ValueError(f"Field '{field_name}' must be numeric (int or float), got {type(val).__name__}: {val}")
    if math.isnan(val) or math.isinf(val):
        raise ValueError(f"Field '{field_name}' must be finite, got {val}")
    if strictly_positive and val <= 0:
        raise ValueError(f"Field '{field_name}' must be strictly positive (> 0), got {val}")
    if min_val is not None:
        if val < min_val:
            raise ValueError(f"Field '{field_name}' cannot be less than {min_val}, got {val}")
    if max_val is not None:
        if strictly_less_than_max:
            if val >= max_val:
                raise ValueError(f"Field '{field_name}' must be strictly less than {max_val}, got {val}")
        else:
            if val > max_val:
                raise ValueError(f"Field '{field_name}' cannot exceed {max_val}, got {val}")


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
    incremental_transport_cost: float = 0.0      # incremental transport (₹ / initial quintal)
    scenario_name: str = "custom"

    def __post_init__(self):
        _validate_numeric(self.holding_period_days, "holding_period_days", integer_only=True, strictly_positive=True)
        _validate_numeric(self.quantity_loss_fraction, "quantity_loss_fraction")
        if not (0.0 <= self.quantity_loss_fraction < 1.0):
            raise ValueError(f"Loss fraction L must be in [0, 1), got {self.quantity_loss_fraction}")
        _validate_numeric(self.quality_discount_fraction, "quality_discount_fraction")
        if not (0.0 <= self.quality_discount_fraction < 1.0):
            raise ValueError(f"Quality discount d_q must be in [0, 1), got {self.quality_discount_fraction}")
        _validate_numeric(self.storage_cost_per_quintal, "storage_cost_per_quintal")
        if self.storage_cost_per_quintal < 0.0:
            raise ValueError(f"Storage cost c_s must be non-negative, got {self.storage_cost_per_quintal}")
        _validate_numeric(self.handling_cost_per_quintal, "handling_cost_per_quintal", min_val=0.0)
        _validate_numeric(self.incremental_transport_cost, "incremental_transport_cost", min_val=0.0)
        _validate_numeric(self.transaction_cost_now, "transaction_cost_now", min_val=0.0)
        _validate_numeric(self.transaction_cost_later, "transaction_cost_later", min_val=0.0)
        _validate_numeric(self.annual_carrying_rate, "annual_carrying_rate", min_val=0.0)

        if self.carrying_cost_type not in ('opportunity', 'financing', 'none'):
            raise ValueError(
                f"Invalid carrying_cost_type: '{self.carrying_cost_type}'. "
                "Must be one of 'opportunity', 'financing', or 'none'."
            )

    @property
    def direct_cost_c(self) -> float:
        """Total direct cost per initial quintal: c = c_storage + c_handling + c_transport."""
        return self.storage_cost_per_quintal + self.handling_cost_per_quintal + self.incremental_transport_cost


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
    _validate_numeric(quantity_quintals, "quantity_quintals")
    _validate_numeric(current_price, "current_price")
    _validate_numeric(transaction_cost_per_quintal, "transaction_cost_per_quintal", min_val=0.0)

    if quantity_quintals <= 0.0:
        raise ValueError(f"Quantity Q must be positive, got {quantity_quintals}")
    if current_price <= 0.0:
        raise ValueError(f"Current price P_T must be positive, got {current_price}")

    gross = float(quantity_quintals) * float(current_price)
    trans = float(quantity_quintals) * float(transaction_cost_per_quintal)
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
    _validate_numeric(quantity_quintals, "quantity_quintals")
    _validate_numeric(current_price, "current_price")
    _validate_numeric(future_price, "future_price")

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

    # Total incremental direct storage, handling, and transport cost
    total_unit_storage_cost = (
        params.storage_cost_per_quintal
        + params.handling_cost_per_quintal
        + getattr(params, "incremental_transport_cost", 0.0)
    )
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

    total_direct_costs = (
        params.storage_cost_per_quintal
        + params.handling_cost_per_quintal
        + getattr(params, "incremental_transport_cost", 0.0)
    )

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
    total_direct_costs = (
        params.storage_cost_per_quintal
        + params.handling_cost_per_quintal
        + getattr(params, "incremental_transport_cost", 0.0)
    )
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


# =====================================================================
# TASK MP-ECON-001: CANONICAL RESEARCH ECONOMICS CONTRACT & GATING
# =====================================================================

@dataclass
class InputProvenance:
    """
    Provenance record for individual economic model inputs.
    Distinguishes observed measurements from illustrative defaults or missing values.
    """
    value: Any
    unit: str
    status: Literal["OBSERVED", "USER_ENTERED", "ILLUSTRATIVE", "DEFAULT", "UNKNOWN", "MISSING"]
    source: str = ""
    effective_date: Optional[str] = None
    market: Optional[str] = None
    commodity: Optional[str] = None
    horizon_days: Optional[int] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "unit": self.unit,
            "status": self.status,
            "source": self.source,
            "effective_date": self.effective_date,
            "market": self.market,
            "commodity": self.commodity,
            "horizon_days": self.horizon_days,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> InputProvenance:
        return cls(**d)


def calculate_canonical_accounting(
    quantity_quintals: float,
    current_price: float,
    future_price: float,
    params: EconomicParameters,
) -> Dict[str, float]:
    """
    Evaluates canonical economic accounting equations:
      R_sell = Q * (p0 - tn)
      R_hold = Q * ((1-L)*((1-d)*pH - tl) - c - p0*f)
      delta_per_initial_quintal = (1-L)*(1-d)*pH - p0*(1+f) - c - (1-L)*tl + tn
      Delta_R = Q * delta_per_initial_quintal
      p_break_even = (p0*(1+f) + c + (1-L)*tl - tn) / ((1-L)*(1-d))

    Enforces exact algebraic equivalence:
      |R_hold - R_sell - Delta_R| < 1e-7
      |delta(p_break_even)| < 1e-7
    """
    _validate_numeric(quantity_quintals, "quantity_quintals", strictly_positive=True)
    _validate_numeric(current_price, "current_price", strictly_positive=True)
    _validate_numeric(future_price, "future_price", min_val=0.0)

    q = float(quantity_quintals)
    p0 = float(current_price)
    ph = float(future_price)
    l = float(params.quantity_loss_fraction)
    d = float(params.quality_discount_fraction)
    c = float(params.direct_cost_c)
    tn = float(params.transaction_cost_now)
    tl = float(params.transaction_cost_later)

    if params.carrying_cost_type in ('financing', 'opportunity') and params.annual_carrying_rate > 0.0:
        f = float(params.annual_carrying_rate * params.holding_period_days / 365.0)
    else:
        f = 0.0

    retention = (1.0 - l) * (1.0 - d)
    if retention <= 0.0:
        raise ZeroDivisionError("Effective produce retention (1-L)*(1-d) is zero or negative.")

    # Canonical equations
    r_sell = q * (p0 - tn)
    r_hold = q * ((1.0 - l) * ((1.0 - d) * ph - tl) - c - p0 * f)
    delta_per_quintal = (1.0 - l) * (1.0 - d) * ph - p0 * (1.0 + f) - c - (1.0 - l) * tl + tn
    delta_r = q * delta_per_quintal

    p_break_even = (p0 * (1.0 + f) + c + (1.0 - l) * tl - tn) / retention
    required_pct_change = ((p_break_even - p0) / p0) * 100.0

    # Strict algebraic reconciliation check (scale-aware tolerance <= 1e-7)
    diff_accounting = abs(r_hold - r_sell - delta_r)
    if diff_accounting >= 1e-7:
        raise ValueError(f"Algebraic reconciliation violation: |R_hold - R_sell - Delta_R| = {diff_accounting}")

    # Break-even zero check
    delta_at_be = (1.0 - l) * (1.0 - d) * p_break_even - p0 * (1.0 + f) - c - (1.0 - l) * tl + tn
    if abs(delta_at_be) >= 1e-7:
        raise ValueError(f"Break-even zero violation: delta(p_be) = {delta_at_be}")

    return {
        "quantity_quintals": q,
        "current_price": p0,
        "future_price": ph,
        "loss_fraction": l,
        "quality_discount": d,
        "direct_cost_c": c,
        "trans_cost_now_tn": tn,
        "trans_cost_later_tl": tl,
        "carrying_rate_factor_f": f,
        "r_sell": r_sell,
        "r_hold": r_hold,
        "delta_per_quintal": delta_per_quintal,
        "delta_r": delta_r,
        "p_break_even": p_break_even,
        "required_pct_change": required_pct_change,
    }


@dataclass
class ResearchEconomicRequest:
    """
    Serializable request contract for research economics evaluation.
    Accepts point price and/or interval bounds (lower, upper).
    """
    quantity_quintals: float
    current_price: float
    future_price_point: Optional[float] = None
    future_price_lower: Optional[float] = None
    future_price_upper: Optional[float] = None
    holding_period_days: int = 7
    commodity: str = "Unknown"
    district: str = "Unknown"
    market: str = "Unknown"
    variety: str = "Unknown"
    grade: str = "Unknown"
    origin_date: Optional[str] = None
    target_date: Optional[str] = None
    params: Optional[EconomicParameters] = None
    provenance_map: Optional[Dict[str, InputProvenance]] = None
    is_reporting_normalization: bool = False
    units: str = "INR/quintal"

    def __post_init__(self):
        _validate_numeric(self.quantity_quintals, "quantity_quintals", strictly_positive=True)
        _validate_numeric(self.current_price, "current_price", strictly_positive=True)
        _validate_numeric(self.holding_period_days, "holding_period_days", integer_only=True, strictly_positive=True)

        if self.units not in ("INR/quintal", "INR/q", "₹/quintal", "Rs/quintal"):
            raise ValueError(f"Unsupported units: '{self.units}'. Must be INR/quintal equivalent.")

        if self.future_price_point is not None:
            _validate_numeric(self.future_price_point, "future_price_point", min_val=0.0)
        if self.future_price_lower is not None:
            _validate_numeric(self.future_price_lower, "future_price_lower", min_val=0.0)
        if self.future_price_upper is not None:
            _validate_numeric(self.future_price_upper, "future_price_upper", min_val=0.0)

        # Ordering check
        if self.future_price_lower is not None and self.future_price_upper is not None:
            if self.future_price_lower > self.future_price_upper:
                raise ValueError(
                    f"future_price_lower ({self.future_price_lower}) cannot exceed future_price_upper ({self.future_price_upper})"
                )
            if self.future_price_point is not None:
                if not (self.future_price_lower <= self.future_price_point <= self.future_price_upper):
                    raise ValueError(
                        f"future_price_point ({self.future_price_point}) must be within [lower ({self.future_price_lower}), upper ({self.future_price_upper})]"
                    )

        # Horizon reconciliation
        if self.params is not None:
            if self.params.holding_period_days != self.holding_period_days:
                raise ValueError(
                    f"Horizon mismatch: request holding_period_days ({self.holding_period_days}) != "
                    f"params.holding_period_days ({self.params.holding_period_days})"
                )

        if self.origin_date and self.target_date:
            try:
                od = datetime.strptime(str(self.origin_date)[:10], "%Y-%m-%d").date()
                td = datetime.strptime(str(self.target_date)[:10], "%Y-%m-%d").date()
            except ValueError as e:
                raise ValueError(f"Invalid origin_date or target_date format (%Y-%m-%d required): {e}")

            calendar_diff = (td - od).days
            if calendar_diff <= 0:
                raise ValueError(f"target_date ({td}) must be strictly after origin_date ({od})")
            if calendar_diff != self.holding_period_days:
                raise ValueError(
                    f"Horizon mismatch: calendar difference (target {td} - origin {od}) = {calendar_diff} days "
                    f"does not match declared holding_period_days ({self.holding_period_days})"
                )

    def to_dict(self) -> Dict[str, Any]:
        params_dict = None
        if self.params is not None:
            params_dict = {
                "storage_cost_per_quintal": self.params.storage_cost_per_quintal,
                "quantity_loss_fraction": self.params.quantity_loss_fraction,
                "annual_carrying_rate": self.params.annual_carrying_rate,
                "holding_period_days": self.params.holding_period_days,
                "carrying_cost_type": self.params.carrying_cost_type,
                "quality_discount_fraction": self.params.quality_discount_fraction,
                "handling_cost_per_quintal": self.params.handling_cost_per_quintal,
                "transaction_cost_now": self.params.transaction_cost_now,
                "transaction_cost_later": self.params.transaction_cost_later,
                "incremental_transport_cost": self.params.incremental_transport_cost,
                "scenario_name": self.params.scenario_name,
            }
        prov_dict = None
        if self.provenance_map is not None:
            prov_dict = {k: v.to_dict() if hasattr(v, "to_dict") else v for k, v in self.provenance_map.items()}

        return {
            "quantity_quintals": self.quantity_quintals,
            "current_price": self.current_price,
            "future_price_point": self.future_price_point,
            "future_price_lower": self.future_price_lower,
            "future_price_upper": self.future_price_upper,
            "holding_period_days": self.holding_period_days,
            "commodity": self.commodity,
            "district": self.district,
            "market": self.market,
            "variety": self.variety,
            "grade": self.grade,
            "origin_date": self.origin_date,
            "target_date": self.target_date,
            "params": params_dict,
            "provenance_map": prov_dict,
            "is_reporting_normalization": self.is_reporting_normalization,
            "units": self.units,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ResearchEconomicRequest:
        params_obj = None
        if d.get("params"):
            params_obj = EconomicParameters(**d["params"])
        prov_obj = None
        if d.get("provenance_map"):
            prov_obj = {k: InputProvenance.from_dict(v) if isinstance(v, dict) else v for k, v in d["provenance_map"].items()}

        return cls(
            quantity_quintals=d["quantity_quintals"],
            current_price=d["current_price"],
            future_price_point=d.get("future_price_point"),
            future_price_lower=d.get("future_price_lower"),
            future_price_upper=d.get("future_price_upper"),
            holding_period_days=d.get("holding_period_days", 7),
            commodity=d.get("commodity", "Unknown"),
            district=d.get("district", "Unknown"),
            market=d.get("market", "Unknown"),
            variety=d.get("variety", "Unknown"),
            grade=d.get("grade", "Unknown"),
            origin_date=d.get("origin_date"),
            target_date=d.get("target_date"),
            params=params_obj,
            provenance_map=prov_obj,
            is_reporting_normalization=d.get("is_reporting_normalization", False),
            units=d.get("units", "INR/quintal"),
        )


@dataclass
class ResearchEconomicResult:
    """
    Serializable result contract for research economics evaluation.
    Contains affine-propagated lower/point/upper bounds, break-even relations,
    and fail-closed advisory gating.
    """
    r_sell_net: Optional[float]
    r_hold_point_net: Optional[float]
    r_hold_lower_net: Optional[float]
    r_hold_upper_net: Optional[float]
    delta_r_point: Optional[float]
    delta_r_lower: Optional[float]
    delta_r_upper: Optional[float]
    delta_per_quintal_point: Optional[float]
    delta_per_quintal_lower: Optional[float]
    delta_per_quintal_upper: Optional[float]
    p_break_even: Optional[float]
    required_pct_change_break_even: Optional[float]
    break_even_relation: Literal[
        "ENTIRELY_ABOVE_BREAK_EVEN",
        "STRADDLES_BREAK_EVEN",
        "ENTIRELY_BELOW_BREAK_EVEN",
        "POINT_ONLY_ABOVE_BREAK_EVEN",
        "POINT_ONLY_BELOW_BREAK_EVEN",
        "UNDEFINED_BREAK_EVEN",
        "NO_FUTURE_PRICE",
        "INCOMPLETE_PARAMETERS",
    ]
    operational_status: Literal["RESEARCH_ONLY", "ADVICE_BLOCKED", "SIMULATION_ONLY"]
    advisory_action: Literal["BLOCKED"]
    advisory_permitted: bool
    gate_reasons: List[str]
    quantity_quintals: float
    is_reporting_normalization: bool
    params_used: Dict[str, Any]
    provenance_summary: Dict[str, Any]
    missing_cost_inputs: List[str]
    disclaimer: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "r_sell_net": self.r_sell_net,
            "r_hold_point_net": self.r_hold_point_net,
            "r_hold_lower_net": self.r_hold_lower_net,
            "r_hold_upper_net": self.r_hold_upper_net,
            "delta_r_point": self.delta_r_point,
            "delta_r_lower": self.delta_r_lower,
            "delta_r_upper": self.delta_r_upper,
            "delta_per_quintal_point": self.delta_per_quintal_point,
            "delta_per_quintal_lower": self.delta_per_quintal_lower,
            "delta_per_quintal_upper": self.delta_per_quintal_upper,
            "p_break_even": self.p_break_even,
            "required_pct_change_break_even": self.required_pct_change_break_even,
            "break_even_relation": self.break_even_relation,
            "operational_status": self.operational_status,
            "advisory_action": self.advisory_action,
            "advisory_permitted": self.advisory_permitted,
            "gate_reasons": self.gate_reasons,
            "quantity_quintals": self.quantity_quintals,
            "is_reporting_normalization": self.is_reporting_normalization,
            "params_used": self.params_used,
            "provenance_summary": self.provenance_summary,
            "missing_cost_inputs": self.missing_cost_inputs,
            "disclaimer": self.disclaimer,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ResearchEconomicResult:
        return cls(**d)


def evaluate_research_economics(request: ResearchEconomicRequest) -> ResearchEconomicResult:
    """
    Evaluates cost-aware research economics with affine uncertainty propagation
    and fail-closed capability gating.

    Invariants:
    - Delta is an increasing affine function of pH: delta_lower <= delta_point <= delta_upper.
    - Break-even relation is purely descriptive and cannot bypass advisory gating.
    - Advisory status is strictly RESEARCH_ONLY / ADVICE_BLOCKED under unverified commercial costs.
    """
    q = float(request.quantity_quintals)
    p0 = float(request.current_price)

    # Missing parameters contract: when params is omitted, return incomplete holding/gain fields
    if request.params is None:
        missing_costs = [
            "storage_cost_per_quintal",
            "handling_cost_per_quintal",
            "incremental_transport_cost",
            "quantity_loss_fraction",
            "quality_discount_fraction",
            "annual_carrying_rate",
            "carrying_cost_type",
            "transaction_cost_now",
            "transaction_cost_later",
        ]
        gate_reasons = [
            "MISSING_ECONOMIC_PARAMETERS",
            "NO_PARAMETERS_SUPPLIED_HOLDING_FIELDS_UNAVAILABLE",
            "UNVERIFIED_COMMERCIAL_COST_FEED",
            "RETROSPECTIVE_RESEARCH_ONLY_NO_LIVE_ADVICE",
        ]
        prov_summary = {"status": "NO_PARAMETERS_SUPPLIED"}
        if request.provenance_map:
            prov_summary["client_provenance"] = {
                k: (v.status if hasattr(v, "status") else str(v))
                for k, v in request.provenance_map.items()
            }

        disclaimer = (
            "RESEARCH ONLY. Missing economic cost parameters prevent calculation of storage proceeds "
            "and incremental return. Advisory action is strictly blocked pending approved prospective validation."
        )

        return ResearchEconomicResult(
            r_sell_net=q * p0,
            r_hold_point_net=None,
            r_hold_lower_net=None,
            r_hold_upper_net=None,
            delta_r_point=None,
            delta_r_lower=None,
            delta_r_upper=None,
            delta_per_quintal_point=None,
            delta_per_quintal_lower=None,
            delta_per_quintal_upper=None,
            p_break_even=None,
            required_pct_change_break_even=None,
            break_even_relation="INCOMPLETE_PARAMETERS",
            operational_status="RESEARCH_ONLY",
            advisory_action="BLOCKED",
            advisory_permitted=False,
            gate_reasons=gate_reasons,
            quantity_quintals=q,
            is_reporting_normalization=request.is_reporting_normalization,
            params_used={},
            provenance_summary=prov_summary,
            missing_cost_inputs=missing_costs,
            disclaimer=disclaimer,
        )

    params = request.params

    # Provenance binding validation: if provenance_map is provided, verify amounts match params
    if request.provenance_map:
        param_mapping = {
            "storage_cost": (params.storage_cost_per_quintal, "storage_cost_per_quintal"),
            "handling_cost": (params.handling_cost_per_quintal, "handling_cost_per_quintal"),
            "incremental_transport": (params.incremental_transport_cost, "incremental_transport_cost"),
            "quantity_loss": (params.quantity_loss_fraction, "quantity_loss_fraction"),
            "quality_discount": (params.quality_discount_fraction, "quality_discount_fraction"),
            "annual_carrying_rate": (params.annual_carrying_rate, "annual_carrying_rate"),
            "transaction_cost_now": (params.transaction_cost_now, "transaction_cost_now"),
            "transaction_cost_later": (params.transaction_cost_later, "transaction_cost_later"),
        }
        for prov_k, (param_val, field_name) in param_mapping.items():
            if prov_k in request.provenance_map:
                prov_item = request.provenance_map[prov_k]
                prov_val = prov_item.value if hasattr(prov_item, "value") else (prov_item.get("value") if isinstance(prov_item, dict) else None)
                if prov_val is not None and isinstance(prov_val, (int, float)) and not isinstance(prov_val, bool):
                    if abs(float(prov_val) - float(param_val)) > 1e-6:
                        raise ValueError(
                            f"Provenance value mismatch for '{prov_k}': provenance record declares {prov_val}, "
                            f"but params.{field_name} is {param_val}"
                        )

    # 2. Immediate Sale Accounting
    r_sell = q * (p0 - params.transaction_cost_now)

    # 3. Future Price Accounting (Point, Lower, Upper)
    has_point = request.future_price_point is not None and math.isfinite(request.future_price_point)
    has_lower = request.future_price_lower is not None and math.isfinite(request.future_price_lower)
    has_upper = request.future_price_upper is not None and math.isfinite(request.future_price_upper)

    acct_point = calculate_canonical_accounting(q, p0, request.future_price_point, params) if has_point else None
    acct_lower = calculate_canonical_accounting(q, p0, request.future_price_lower, params) if has_lower else None
    acct_upper = calculate_canonical_accounting(q, p0, request.future_price_upper, params) if has_upper else None

    # Affine Monotonicity Check
    if has_lower and has_upper:
        if request.future_price_lower > request.future_price_upper + 1e-6:
            raise ValueError(f"Lower bound ({request.future_price_lower}) exceeds upper bound ({request.future_price_upper})")
        if acct_lower["delta_per_quintal"] > acct_upper["delta_per_quintal"] + 1e-6:
            raise ValueError("Affine monotonicity violation: delta_lower > delta_upper")
    if has_lower and has_point and has_upper:
        if acct_lower["delta_per_quintal"] > acct_point["delta_per_quintal"] + 1e-6:
            raise ValueError("Affine monotonicity violation: delta_lower > delta_point")
        if acct_point["delta_per_quintal"] > acct_upper["delta_per_quintal"] + 1e-6:
            raise ValueError("Affine monotonicity violation: delta_point > delta_upper")

    # Break-even threshold
    p_be = (acct_point or acct_lower or acct_upper or calculate_canonical_accounting(q, p0, p0, params))["p_break_even"]
    req_pct = ((p_be - p0) / p0) * 100.0

    # 4. Break-even Relation Classification
    tol = 1e-6
    if has_lower and has_upper:
        if request.future_price_lower > p_be + tol:
            be_relation = "ENTIRELY_ABOVE_BREAK_EVEN"
        elif request.future_price_upper < p_be - tol:
            be_relation = "ENTIRELY_BELOW_BREAK_EVEN"
        else:
            be_relation = "STRADDLES_BREAK_EVEN"
    elif has_point:
        if request.future_price_point > p_be + tol:
            be_relation = "POINT_ONLY_ABOVE_BREAK_EVEN"
        else:
            be_relation = "POINT_ONLY_BELOW_BREAK_EVEN"
    else:
        be_relation = "NO_FUTURE_PRICE"

    # 5. Missing Input Audit and Gating Reasons
    missing_costs = []
    prov_summary = {}
    gate_reasons = []

    expected_cost_keys = ["storage_cost", "quantity_loss", "annual_rate", "handling_cost", "transaction_costs"]
    if request.provenance_map:
        for k in expected_cost_keys:
            rec = request.provenance_map.get(k)
            if not rec or rec.status in ("MISSING", "UNKNOWN"):
                missing_costs.append(k)
                prov_summary[k] = "MISSING_OR_UNKNOWN"
            elif rec.status in ("ILLUSTRATIVE", "DEFAULT"):
                missing_costs.append(f"{k}_(UNVERIFIED_{rec.status})")
                prov_summary[k] = rec.status
            else:
                prov_summary[k] = rec.status
    else:
        missing_costs = ["NO_PROVENANCE_MAP_SUPPLIED_USER_OR_DEFAULT_PARAMETERS"]
        prov_summary = {"status": "UNVERIFIED_PARAMETERS"}

    gate_reasons.append("RETROSPECTIVE_RESEARCH_ONLY_NO_LIVE_ADVICE")
    gate_reasons.append("POSITIVE_LOWER_BOUND_CANNOT_AUTHORIZE_FARMER_ADVICE")
    if missing_costs:
        gate_reasons.append("UNVERIFIED_COMMERCIAL_COST_FEED")

    if request.is_reporting_normalization:
        prov_summary["quantity_note"] = "Declared reporting normalization (1.0 quintal), not an observed farmer holding."

    disclaimer = (
        "RESEARCH ONLY. Mathematical calculations are conditional on declared parameters. "
        "Interval coverage does not cover uncertain storage costs or physical shrinkage. "
        "Advisory action is strictly blocked pending approved prospective validation."
    )

    return ResearchEconomicResult(
        r_sell_net=r_sell,
        r_hold_point_net=acct_point["r_hold"] if acct_point else None,
        r_hold_lower_net=acct_lower["r_hold"] if acct_lower else None,
        r_hold_upper_net=acct_upper["r_hold"] if acct_upper else None,
        delta_r_point=acct_point["delta_r"] if acct_point else None,
        delta_r_lower=acct_lower["delta_r"] if acct_lower else None,
        delta_r_upper=acct_upper["delta_r"] if acct_upper else None,
        delta_per_quintal_point=acct_point["delta_per_quintal"] if acct_point else None,
        delta_per_quintal_lower=acct_lower["delta_per_quintal"] if acct_lower else None,
        delta_per_quintal_upper=acct_upper["delta_per_quintal"] if acct_upper else None,
        p_break_even=p_be,
        required_pct_change_break_even=req_pct,
        break_even_relation=be_relation,
        operational_status="RESEARCH_ONLY",
        advisory_action="BLOCKED",
        advisory_permitted=False,
        gate_reasons=gate_reasons,
        quantity_quintals=q,
        is_reporting_normalization=request.is_reporting_normalization,
        params_used={
            "storage_cost_per_quintal": params.storage_cost_per_quintal,
            "handling_cost_per_quintal": params.handling_cost_per_quintal,
            "incremental_transport_cost": params.incremental_transport_cost,
            "direct_cost_c": params.direct_cost_c,
            "quantity_loss_fraction": params.quantity_loss_fraction,
            "quality_discount_fraction": params.quality_discount_fraction,
            "annual_carrying_rate": params.annual_carrying_rate,
            "holding_period_days": params.holding_period_days,
            "carrying_cost_type": params.carrying_cost_type,
            "transaction_cost_now": params.transaction_cost_now,
            "transaction_cost_later": params.transaction_cost_later,
            "scenario_name": params.scenario_name,
        },
        provenance_summary=prov_summary,
        missing_cost_inputs=missing_costs,
        disclaimer=disclaimer,
    )
