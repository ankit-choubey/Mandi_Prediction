"""Executable independent review gates. No fits, network calls or operational data writes.

Run from any directory: python3 experiments/reviews/check_app001a_review_gates.py
Exit 1 means a specified contract failed. These targeted cases are not project accuracy.
"""
from __future__ import annotations

import copy
import csv
import io
import json
import math
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.api import create_app
from src.forecast_intervals import validate_and_load_calibration_envelope
from src.service import MandiMarketService


def main() -> int:
    checks = []

    def check(name, passed, actual, expected):
        checks.append(dict(name=name, passed=bool(passed), actual=actual, expected=expected))

    def request(app, path, body, *, content_type="application/json", raw=None):
        payload = raw if raw is not None else json.dumps(body).encode()
        statuses = []
        environ = dict(REQUEST_METHOD="POST", PATH_INFO=path, QUERY_STRING="",
                       CONTENT_LENGTH=str(len(payload)), CONTENT_TYPE=content_type,
                       SERVER_NAME="localhost", SERVER_PORT="80")
        environ["wsgi.input"] = io.BytesIO(payload)
        environ["wsgi.version"] = (1, 0)
        environ["wsgi.url_scheme"] = "http"

        def start_response(status, headers, exc_info=None):
            statuses.append(int(status.split()[0]))

        result = json.loads(b"".join(app(environ, start_response)))
        return statuses[-1], result

    service = MandiMarketService()
    app = create_app(service)
    point_file = ROOT / "experiments/reports/FC007_VERIFIED/scorecard_overall.csv"
    interval_file = ROOT / "experiments/reports/FC008/intervals_overall.csv"
    with point_file.open() as stream:
        points = {row["model"]: row for row in csv.DictReader(stream)}
    with interval_file.open() as stream:
        intervals = {(row["model"], float(row["nominal_level"])): row
                     for row in csv.DictReader(stream)}
    benchmark = service.get_benchmark_scorecards()
    aliases = {"naive_persistence": "naive", "ridge_regression": "ridge"}
    for row in benchmark["model_performance_summary"]:
        model = aliases.get(row["model"], row["model"])
        for field in ("mae", "rmse"):
            expected = float(points[model][field])
            check(f"benchmark:{model}:{field}", math.isclose(row[field], expected, abs_tol=.005),
                  row[field], expected)
        for level, field in ((.9, "coverage_90_pct"), (.95, "coverage_95_pct")):
            expected = float(intervals[model, level]["empirical_coverage_pct"])
            check(f"benchmark:{model}:{field}", math.isclose(row[field], expected, abs_tol=.005),
                  row[field], expected)
        expected = 100 * float(points[model]["skill"])
        check(f"benchmark:{model}:skill", math.isclose(row["skill_vs_persistence_mae_pct"], expected, abs_tol=.005),
              row["skill_vs_persistence_mae_pct"], expected)

    with (ROOT / "experiments/reports/FC008/intervals_by_fold.csv").open() as stream:
        fold_row = next(row for row in csv.DictReader(stream)
                        if row["slice_name"] == "Fold_F2" and row["model"] == "naive"
                        and float(row["nominal_level"]) == .9)
    expected = float(fold_row["empirical_coverage_pct"])
    actual = benchmark["fold_level_breakdown_naive_90"]["F2"]["coverage_pct"]
    check("benchmark:naive:F2_coverage", math.isclose(actual, expected, abs_tol=.005), actual, expected)

    base = dict(quantity_quintals=1, current_price=2000, future_price_point=2200)
    for name, body in (("omitted", base), ("partial", {**base, "params": {"storage_cost_per_quintal": 50}})):
        status, result = request(app, "/api/v1/economics/evaluate", body)
        data = result.get("data") or {}
        check(f"economics:{name}:gain", status < 500 and data.get("delta_r_point") is None,
              dict(status=status, gain=data.get("delta_r_point")), "null without complete costs")
        check(f"economics:{name}:net_sale", data.get("r_sell_net") is None,
              data.get("r_sell_net"), "net unknown when transaction cost omitted; gross may be separate")

    complete = dict(quantity_quintals=10, current_price=2500, future_price_point=2650,
                    holding_period_days=7, params=dict(
                        storage_cost_per_quintal=50, handling_cost_per_quintal=0,
                        incremental_transport_cost=0, transaction_cost_now=0,
                        transaction_cost_later=0, quantity_loss_fraction=.02,
                        quality_discount_fraction=0, annual_carrying_rate=0,
                        carrying_cost_type="none", holding_period_days=7))
    status, result = request(app, "/api/v1/economics/evaluate", complete)
    data = result.get("data") or {}
    check("economics:complete:valid_control", status == 200 and data.get("delta_r_point") == 470
          and data.get("advisory_permitted") is False,
          dict(status=status, gain=data.get("delta_r_point"), advisory=data.get("advisory_permitted")),
          "valid full inputs -> gain470, blocked advice")

    forecast = dict(district="Lucknow", market="Lucknow", commodity="Wheat", horizon_days=-7)
    cases = [
        ("missing_required", "/api/v1/economics/evaluate", {}, "application/json", None),
        ("content_type", "/api/v1/economics/evaluate", base, "text/plain", None),
        ("negative_horizon", "/api/v1/forecast", forecast, "application/json", None),
        ("invalid_json_number", "/api/v1/forecast", {}, "application/json",
         b'{"district":"Lucknow","market":"Lucknow","commodity":"Wheat","extra":NaN}'),
    ]
    for name, path, body, media, raw in cases:
        status, result = request(app, path, body, content_type=media, raw=raw)
        check(f"http:{name}", 400 <= status < 500, status, "documented 4xx")

    envelope_file = ROOT / "experiments/reports/FC008/calibration_envelope_v1.json"
    envelope = json.loads(envelope_file.read_text())
    mutations = [
        ("positive_quantile", lambda e: e["quantiles"]["F2"]["naive"]["quantiles"]["0.9"]["pooled"].update(
            quantile=e["quantiles"]["F2"]["naive"]["quantiles"]["0.9"]["pooled"]["quantile"] * .9)),
        ("missing_model", lambda e: e["quantiles"]["F2"].pop("naive")),
        ("missing_config", lambda e: e.pop("config_sha256_semantic", None)),
    ]
    for name, mutate in mutations:
        altered = copy.deepcopy(envelope)
        mutate(altered)
        try:
            validate_and_load_calibration_envelope(altered)
            rejected = False
        except (ValueError, TypeError, KeyError):
            rejected = True
        check(f"artifact:{name}", rejected, rejected, "altered payload rejected")

    # Isolated malformed unit fixture, never a served or empirical operational dataset.
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "fixture_index.json"
        path.write_text(json.dumps({"series": []}))
        unhealthy = MandiMarketService(latest_index_path=path).get_health()
        check("index:shape", not unhealthy.capabilities["prices"].available,
              unhealthy.capabilities["prices"].available, False)

    output = ROOT / "experiments/reports/APP001A_REVIEW/executable_gate_receipt.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    report = dict(method="Independent executable contract assertions, not a project score",
                  checks=checks, passed=sum(c["passed"] for c in checks), total=len(checks))
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    failures = [c["name"] for c in checks if not c["passed"]]
    print(json.dumps(dict(passed=report["passed"], total=report["total"], failures=failures), indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
