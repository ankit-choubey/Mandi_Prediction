"""
Unit and Regression Tests for Gate A Contracts (MP-APP-001A)
Covers:
- Gate A1: Missing-input, numeric and horizon contracts
- Gate A2: Artifact validation, pinned historical scopes, and corrupt quantile rejection
"""

from datetime import date, datetime
import math
import pytest

from src.economic_model import (
    EconomicParameters,
    ResearchEconomicRequest,
    ResearchEconomicResult,
    InputProvenance,
    evaluate_research_economics,
    calculate_canonical_accounting,
    calculate_immediate_sale_proceeds,
    calculate_storage_sale_proceeds,
)


class TestGateA1EconomicContracts:
    """Verifies all Gate A1 contract repairs and edge-case rejections."""

    def test_missing_params_returns_incomplete_holding_and_gain_fields(self):
        """
        Defect 1 Reproduction & Fix:
        Request with params omitted previously selected Central defaults and returned gain 155.31.
        Must now return incomplete holding proceeds (None), gain (None), p_break_even (None),
        and explicit missing cost reasons.
        """
        req = ResearchEconomicRequest(
            quantity_quintals=1.0,
            current_price=2000.0,
            future_price_point=2200.0,
        )
        res = evaluate_research_economics(req)

        # Incomplete / unavailable fields
        assert res.r_hold_point_net is None, "Holding proceeds must be None when params omitted"
        assert res.r_hold_lower_net is None
        assert res.r_hold_upper_net is None
        assert res.delta_r_point is None, "Holding gain must be None when params omitted"
        assert res.delta_r_lower is None
        assert res.delta_r_upper is None
        assert res.delta_per_quintal_point is None
        assert res.delta_per_quintal_lower is None
        assert res.delta_per_quintal_upper is None
        assert res.p_break_even is None
        assert res.required_pct_change_break_even is None
        assert res.break_even_relation == "INCOMPLETE_PARAMETERS"
        assert res.operational_status == "RESEARCH_ONLY"
        assert res.advisory_action == "BLOCKED"
        assert res.advisory_permitted is False

        # Explicit missing cost reasons
        assert len(res.missing_cost_inputs) > 0
        assert "storage_cost_per_quintal" in res.missing_cost_inputs
        assert "quantity_loss_fraction" in res.missing_cost_inputs
        assert "annual_carrying_rate" in res.missing_cost_inputs
        assert "MISSING_ECONOMIC_PARAMETERS" in res.gate_reasons
        assert "NO_PARAMETERS_SUPPLIED_HOLDING_FIELDS_UNAVAILABLE" in res.gate_reasons

        # Spot proceeds without parameters should simply be Q * p0
        assert res.r_sell_net == 2000.0

    def test_horizon_mismatch_rejected(self):
        """
        Defect 2 Reproduction & Fix:
        Request horizon, parameter horizon, and dated origin-to-target calendar difference
        must strictly agree. Discrepancies must raise ValueError.
        """
        params_7d = EconomicParameters(holding_period_days=7)

        # 1. Request horizon vs Parameter horizon mismatch
        with pytest.raises(ValueError, match="Horizon mismatch: request holding_period_days"):
            ResearchEconomicRequest(
                quantity_quintals=1.0,
                current_price=2000.0,
                future_price_point=2200.0,
                holding_period_days=30,
                params=params_7d,
            )

        # 2. Calendar dates difference vs Request horizon mismatch
        with pytest.raises(ValueError, match="Horizon mismatch: calendar difference"):
            ResearchEconomicRequest(
                quantity_quintals=1.0,
                current_price=2000.0,
                future_price_point=2200.0,
                holding_period_days=30,
                origin_date="2026-11-13",
                target_date="2026-11-20",  # 7 days apart != 30 days
            )

        # 3. Calendar dates target not strictly after origin
        with pytest.raises(ValueError, match="must be strictly after origin_date"):
            ResearchEconomicRequest(
                quantity_quintals=1.0,
                current_price=2000.0,
                future_price_point=2200.0,
                holding_period_days=7,
                origin_date="2026-11-20",
                target_date="2026-11-13",
            )

        # 4. Valid consistent horizon passes
        valid_req = ResearchEconomicRequest(
            quantity_quintals=1.0,
            current_price=2000.0,
            future_price_point=2200.0,
            holding_period_days=7,
            origin_date="2026-11-13",
            target_date="2026-11-20",
            params=params_7d,
        )
        assert valid_req.holding_period_days == 7

    def test_numeric_domain_and_type_validations(self):
        """
        Defect 3 Reproduction & Fix:
        Validate finite domain, non-negativity, valid ranges, and disallow booleans.
        """
        # Negative later transaction cost
        with pytest.raises(ValueError, match="Field 'transaction_cost_later' cannot be less than 0.0"):
            EconomicParameters(transaction_cost_later=-10.0)

        # Invalid carrying cost type
        with pytest.raises(ValueError, match="Invalid carrying_cost_type"):
            EconomicParameters(carrying_cost_type="invalid")  # type: ignore

        # NaN storage cost
        with pytest.raises(ValueError, match="Field 'storage_cost_per_quintal' must be finite"):
            EconomicParameters(storage_cost_per_quintal=float("nan"))

        # Inf handling cost
        with pytest.raises(ValueError, match="Field 'handling_cost_per_quintal' must be finite"):
            EconomicParameters(handling_cost_per_quintal=float("inf"))

        # Boolean passed as numeric cost
        with pytest.raises(ValueError, match="cannot be a boolean"):
            EconomicParameters(transaction_cost_now=True)  # type: ignore

        # Boolean passed as request quantity
        with pytest.raises(ValueError, match="cannot be a boolean"):
            ResearchEconomicRequest(quantity_quintals=True, current_price=2000.0)  # type: ignore

        # Boolean passed as holding days
        with pytest.raises(ValueError, match="cannot be a boolean"):
            EconomicParameters(holding_period_days=True)  # type: ignore

        # Non-positive quantity
        with pytest.raises(ValueError, match="must be strictly positive"):
            ResearchEconomicRequest(quantity_quintals=0.0, current_price=2000.0)

        # Non-positive current price
        with pytest.raises(ValueError, match="must be strictly positive"):
            ResearchEconomicRequest(quantity_quintals=10.0, current_price=-100.0)

        # Unsupported units
        with pytest.raises(ValueError, match="Unsupported units"):
            ResearchEconomicRequest(quantity_quintals=10.0, current_price=2000.0, units="USD/barrel")

        # Future price bounds ordering violation (lower > upper)
        with pytest.raises(ValueError, match="future_price_lower .* cannot exceed future_price_upper"):
            ResearchEconomicRequest(
                quantity_quintals=10.0,
                current_price=2000.0,
                future_price_lower=2500.0,
                future_price_upper=2400.0,
            )

        # Future price bounds ordering violation (point outside [lower, upper])
        with pytest.raises(ValueError, match="future_price_point .* must be within"):
            ResearchEconomicRequest(
                quantity_quintals=10.0,
                current_price=2000.0,
                future_price_lower=2100.0,
                future_price_point=2050.0,
                future_price_upper=2300.0,
            )

    def test_provenance_binding_discrepancy_rejected(self):
        """
        Verify that provenance values, when declared, are checked against amounts actually used.
        """
        params = EconomicParameters(
            storage_cost_per_quintal=20.0,
            holding_period_days=7,
        )
        prov_map = {
            "storage_cost": InputProvenance(
                value=35.0,  # Mismatch with params.storage_cost_per_quintal (20.0)
                unit="INR/quintal",
                status="OBSERVED",
            )
        }
        req = ResearchEconomicRequest(
            quantity_quintals=1.0,
            current_price=2000.0,
            future_price_point=2200.0,
            holding_period_days=7,
            params=params,
            provenance_map=prov_map,
        )
        with pytest.raises(ValueError, match="Provenance value mismatch for 'storage_cost'"):
            evaluate_research_economics(req)


class TestGateA2ArtifactValidation:
    """Verifies all Gate A2 artifact validation, pinned scopes, and watchdog constraints."""

    @pytest.fixture
    def base_envelope(self):
        from pathlib import Path
        from src.forecast_intervals import validate_and_load_calibration_envelope
        envelope_path = Path("experiments/reports/FC008/calibration_envelope_v1.json")
        return validate_and_load_calibration_envelope(envelope_path)

    def test_altered_code_hash_rejected(self, base_envelope):
        """Reviewer defect 2: Altered code identity must be rejected by validator."""
        import copy
        from src.forecast_intervals import validate_and_load_calibration_envelope
        bad_env = copy.deepcopy(base_envelope)
        bad_env["code_sha256"] = "altered_code_hash_1234567890abcdef1234567890abcdef1234567890abcdef"
        with pytest.raises(ValueError, match="Untrusted or altered code_sha256"):
            validate_and_load_calibration_envelope(bad_env)

    def test_missing_f2_payload_rejected(self, base_envelope):
        """Reviewer defect 2: Missing F2 payload in quantiles must be rejected."""
        import copy
        from src.forecast_intervals import validate_and_load_calibration_envelope
        bad_env = copy.deepcopy(base_envelope)
        del bad_env["quantiles"]["F2"]
        with pytest.raises(ValueError, match="Missing required canonical fold payload: F2"):
            validate_and_load_calibration_envelope(bad_env)

    def test_future_max_calibration_target_rejected(self, base_envelope):
        """Reviewer defect 2: Future maximum calibration target date must be rejected."""
        import copy
        from src.forecast_intervals import validate_and_load_calibration_envelope
        bad_env = copy.deepcopy(base_envelope)
        bad_env["fold_scopes"]["F2"]["max_calibration_target_date"] = "2099-01-01"
        with pytest.raises(ValueError, match="Future maximum calibration target date in F2"):
            validate_and_load_calibration_envelope(bad_env)

    def test_nan_wheat_quantile_rejected(self, base_envelope):
        """Reviewer defect 2: NaN Wheat quantile must be rejected, not silently ignored."""
        import copy
        from src.forecast_intervals import validate_and_load_calibration_envelope
        bad_env = copy.deepcopy(base_envelope)
        naive_quants = bad_env["quantiles"]["F2"]["naive"]["quantiles"]
        k90 = "0.9" if "0.9" in naive_quants else "0.90"
        # Set Wheat quantile to NaN
        bad_env["quantiles"]["F2"]["naive"]["quantiles"][k90]["by_commodity"]["Wheat"]["quantile"] = float("nan")
        with pytest.raises(ValueError, match="Corrupt, non-finite or negative quantile for crop 'Wheat'"):
            validate_and_load_calibration_envelope(bad_env)

    def test_envelope_scope_cannot_override_pinned_historical_scope(self, base_envelope):
        """
        Reviewer defect 2: Modifying envelope's F2 validity scope to Nov 2026 cannot authorize
        origin 2026-11-13. Must be rejected using pinned historical scopes.
        """
        import copy
        from src.forecast_intervals import predict_interval
        tampered_env = copy.deepcopy(base_envelope)
        tampered_env["fold_scopes"]["F2"]["validity_start"] = "2026-11-01"
        tampered_env["fold_scopes"]["F2"]["validity_end"] = "2026-11-30"

        # Predict interval for F2 with origin in Nov 2026
        res = predict_interval(
            model_name="naive",
            point_pred=2200.0,
            y_t=2000.0,
            commodity="Wheat",
            fold_id="F2",
            nominal_level=0.90,
            calibration_artifacts=tampered_env,
            origin_date="2026-11-13",
            envelope=tampered_env,
        )
        assert res["status"] == "ORIGIN_DATE_OUTSIDE_VALIDITY_SCOPE"
        assert "OUTSIDE_F2_SCOPE" in res["advisory_blocked_reason"]

    def test_corrupt_crop_quantile_does_not_silently_fallback_to_pooled(self, base_envelope):
        """
        A corrupt commodity quantile must NOT silently become pooled fallback.
        It must fail-closed with NO_CALIBRATION status.
        """
        from src.forecast_intervals import predict_interval
        raw_quants = {
            "F2": {
                "naive": {
                    "status": "CALIBRATED",
                    "quantiles": {
                        "0.90": {
                            "pooled": {"quantile": 0.15, "group_type": "POOLED_FALLBACK"},
                            "by_commodity": {
                                "Wheat": {"quantile": float("nan")},  # Corrupt
                            },
                        },
                    },
                }
            }
        }
        res = predict_interval(
            model_name="naive",
            point_pred=2200.0,
            y_t=2000.0,
            commodity="Wheat",
            fold_id="F2",
            nominal_level=0.90,
            calibration_artifacts=raw_quants,
            origin_date="2025-08-01",  # Within F2 pinned scope
        )
        assert res["status"] == "NO_CALIBRATION"
        assert "CORRUPT_COMMODITY_QUANTILE_FOR_Wheat" in res["reason"]
        assert res["group_type"] == "NO_CALIBRATION"

    def test_resource_watchdogs_enforce_timeout_and_rss(self):
        """Verify incremental watchdog functions raise appropriate errors on limit breach."""
        import time
        from src.forecast_intervals import check_resource_watchdogs

        # Immediate timeout check with elapsed > max_duration
        with pytest.raises(TimeoutError, match="Pipeline exceeded total timeout limit"):
            check_resource_watchdogs(
                t_start=time.time() - 100.0,
                max_duration_seconds=10.0,
                stage_name="Test Stage Timeout",
                max_rss_mb=1024.0,
            )

        # Immediate memory check with artificial 0.01 MB RSS limit
        with pytest.raises(MemoryError, match="Peak RSS .* exceeded limit"):
            check_resource_watchdogs(
                t_start=time.time(),
                max_duration_seconds=600.0,
                stage_name="Test Stage Memory",
                max_rss_mb=0.01,
            )
