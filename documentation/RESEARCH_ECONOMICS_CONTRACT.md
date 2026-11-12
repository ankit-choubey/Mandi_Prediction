# Research Economics Contract & Integration Runbook

**Task ID:** `MP-ECON-001`
**Version:** `1.0.0`
**Status:** Backend-Ready Contract (Research Economics & Advisory Gating)
**Effective Date:** 2026-11-13

---

## 1. Architectural Scope & Principles

This document defines the interface contract, mathematical foundations, data structures, and safety gating rules for the APMC Mandi Market Intelligence System's economic decision support layer (`src/economic_model.py`).

### Core Design Principles
1. **Strict Separation of Calculator and Policy:** The pure mathematical accounting calculator evaluates sell-versus-hold proceeds for complete explicit user parameters without enforcing operational policy. The advisory policy boundary strictly evaluates whether the calculation can be presented as an active farmer recommendation.
2. **Fail-Closed Advisory Boundary:** In the absence of verified commercial cost feeds, or under stale/review/future data or recent interval undercoverage, the advisory policy strictly sets `advisory_action = "BLOCKED"`, `operational_status = "RESEARCH_ONLY"`, and `advisory_permitted = False`.
3. **Affine Monotonicity:** Holding proceeds and incremental gains are strictly increasing affine functions of the future price $p_H$. Conformal prediction intervals $[\hat{p}_{\text{lower}}, \hat{p}_{\text{upper}}]$ propagate monotonically to net benefit bounds $[\delta_{\text{lower}}, \delta_{\text{upper}}]$.
4. **Honest Input Provenance:** Every input parameter records its observation status (`OBSERVED`, `USER_ENTERED`, `ILLUSTRATIVE`, `DEFAULT`, `UNKNOWN`, `MISSING`). Missing costs are treated as UNKNOWN, never silently set to zero. A quantity of 1.0 quintal is an explicitly declared reporting normalization, never an observed farmer holding.

---

## 2. Canonical Accounting Equations

Let:
- $Q$: Produce quantity in quintals ($Q > 0$).
- $p_0$: Spot modal price at origin date $t$ (INR/quintal, $p_0 > 0$).
- $p_H$: Modal price $h$ calendar days later at target date $t+h$ (INR/quintal, $p_H \ge 0$).
- $L$: Physical quantity shrinkage fraction during storage ($0 \le L < 1$).
- $d$: Quality discount / price markdown fraction upon later sale ($0 \le d < 1$).
- $c$: Direct incremental storage, handling, and transport cost per initial quintal over $h$ days (INR/quintal, $c \ge 0$).
- $t_n$: Transaction/marketing cost per initial quintal for immediate sale (INR/quintal, $t_n \ge 0$).
- $t_l$: Transaction/marketing cost per remaining quintal for later sale (INR/quintal, $t_l \ge 0$).
- $f$: Carrying rate factor over $h$ days: $f = \frac{\text{annual rate} \times h}{365}$ if carrying type is financing or opportunity, else $0$ (dimensionless).

### Formulations:
$$\begin{aligned}
R_{\text{sell}} &= Q \cdot (p_0 - t_n) \\
R_{\text{hold}} &= Q \cdot \left((1-L)((1-d)p_H - t_l) - c - p_0 f\right) \\
\delta_{\text{per initial quintal}} &= (1-L)(1-d)p_H - p_0(1+f) - c - (1-L)t_l + t_n \\
\Delta_R &= Q \cdot \delta_{\text{per initial quintal}} \\
p_{\text{break-even}} &= \frac{p_0(1+f) + c + (1-L)t_l - t_n}{(1-L)(1-d)}
\end{aligned}$$

### Invariant Checks Enforced:
1. $|R_{\text{hold}} - R_{\text{sell}} - \Delta_R| < 10^{-7}$
2. $|\delta(p_{\text{break-even}})| < 10^{-7}$
3. $\frac{\partial \delta}{\partial p_H} = (1-L)(1-d) > 0$

---

## 3. Data Contracts & Schemas

### 3.1 Input Provenance Dataclass
```python
@dataclass
class InputProvenance:
    value: Any
    unit: str
    status: Literal["OBSERVED", "USER_ENTERED", "ILLUSTRATIVE", "DEFAULT", "UNKNOWN", "MISSING"]
    source: str = ""
    effective_date: Optional[str] = None
    market: Optional[str] = None
    commodity: Optional[str] = None
    horizon_days: Optional[int] = None
    notes: Optional[str] = None
```

### 3.2 Request Contract: `ResearchEconomicRequest`
```python
@dataclass
class ResearchEconomicRequest:
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
```

### 3.3 Result Contract: `ResearchEconomicResult`
```python
@dataclass
class ResearchEconomicResult:
    # Immediate sale proceeds
    r_sell_net: float

    # Holding net proceeds
    r_hold_point_net: Optional[float]
    r_hold_lower_net: Optional[float]
    r_hold_upper_net: Optional[float]

    # Incremental holding benefit (Total INR)
    delta_r_point: Optional[float]
    delta_r_lower: Optional[float]
    delta_r_upper: Optional[float]

    # Incremental benefit per initial quintal (INR/quintal)
    delta_per_quintal_point: Optional[float]
    delta_per_quintal_lower: Optional[float]
    delta_per_quintal_upper: Optional[float]

    # Break-even price and required % change
    p_break_even: float
    required_pct_change_break_even: float

    # Break-even classification
    break_even_relation: Literal[
        "ENTIRELY_ABOVE_BREAK_EVEN",
        "STRADDLES_BREAK_EVEN",
        "ENTIRELY_BELOW_BREAK_EVEN",
        "POINT_ONLY_ABOVE_BREAK_EVEN",
        "POINT_ONLY_BELOW_BREAK_EVEN",
        "UNDEFINED_BREAK_EVEN",
        "NO_FUTURE_PRICE",
    ]

    # Advisory & Capability Gating
    operational_status: Literal["RESEARCH_ONLY", "ADVICE_BLOCKED", "SIMULATION_ONLY"]
    advisory_action: Literal["BLOCKED"]
    advisory_permitted: bool  # False
    gate_reasons: List[str]

    # Context & Parameters
    quantity_quintals: float
    is_reporting_normalization: bool
    params_used: Dict[str, Any]
    provenance_summary: Dict[str, Any]
    missing_cost_inputs: List[str]
    disclaimer: str
```

---

## 4. Capability Safety Gating Rules

| Gate Trigger | Operational Action | Advisory Permitted | Gate Reason |
| :--- | :--- | :--- | :--- |
| **Unverified Commercial Costs** | `BLOCKED` | `False` | `UNVERIFIED_COMMERCIAL_COST_FEED` |
| **Illustrative / Default Parameters** | `BLOCKED` | `False` | `ILLUSTRATIVE_PARAMETERS_ONLY` |
| **Positive Lower Bound Alone** | `BLOCKED` | `False` | `POSITIVE_LOWER_BOUND_CANNOT_AUTHORIZE_FARMER_ADVICE` |
| **Recent Interval Undercoverage** | `BLOCKED` | `False` | `RECENT_INTERVAL_UNDERCOVERAGE_DISCLOSED` |
| **Stale / Missing Observation Date** | `BLOCKED` | `False` | `STALE_OR_MISSING_OBSERVATION_DATE` |
| **Future-Dated Observation** | `BLOCKED` | `False` | `FUTURE_DATED_OBSERVATION_REJECTED` |

---

## 5. Backend Integration Guidelines (Steps 10–13)

1. **REST / RPC Service Architecture:**
   - Expose endpoint `POST /api/v1/economics/evaluate`.
   - Accept JSON serialized `ResearchEconomicRequest`.
   - Validate payload schema using `ResearchEconomicRequest.from_dict()`.
   - Call `evaluate_research_economics(request)`.
   - Return HTTP 200 with JSON serialized `ResearchEconomicResult.to_dict()`.
2. **Farmer UI Presentation Rules:**
   - Never render a green "STORE" or red "SELL" advisory banner if `advisory_permitted == False`.
   - Display conditional arithmetic clearly labeled: "Research Simulation Conditional on Declared Parameters".
   - Always display break-even threshold and sensitivity ranges alongside the disclaimer.
3. **Data Logging:**
   - Log all requests and results for auditability before returning responses.
   - Record `is_reporting_normalization` status in all telemetry.
