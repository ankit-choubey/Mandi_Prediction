"""
Current-Data Output & Real-Time Operational Dashboard
APMC Mandi Market Intelligence System
Author: Om Awasthi (Owner 4: Current-Data Output & Operational Reliability)

This module produces the user-facing operational report, terminal dashboard,
and machine-readable JSON health status for verified APMC mandi market data.

Key Capabilities:
1. Displays source provenance, resource ID, and operational state.
2. Distinctly separates 'Latest Observation Date' from 'Retrieval Timestamp'.
3. Formats full reconciliation table (records fetched, accepted, quarantined, unchanged, unique keys).
4. Provides interactive market snapshot lookups (e.g. Potato in Kanpur).
5. Exposes --demo flag for instant integration verification by Ankit.
6. Exposes --json flag for programmatic monitoring and CI assertion.
"""

import os
import sys
import json
import argparse
from datetime import datetime, date, timezone
from typing import Optional, Dict, Any, List
import pandas as pd

from src.health_status import (
    HealthStatusEngine,
    HealthReport,
    OperationalState,
    FreshnessStatus,
    ReconciliationLedger,
    RecommendationSafetyGate,
    SafetyGateDecision,
    RecommendationStatus,
    BLOCKED_RECOMMENDATION_MESSAGE,
    DEFAULT_SOURCE_NAME,
    DEFAULT_RESOURCE_ID
)


class CurrentDataReporter:
    """Renderer and CLI controller for APMC Mandi current data output."""

    def __init__(
        self,
        validated_csv_path: Optional[str] = None,
        summary_json_path: Optional[str] = None,
        reference_date: Optional[date] = None
    ):
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.csv_path = validated_csv_path or os.path.join(repo_root, "data", "processed", "mandi_5year_validated.csv")
        self.summary_path = summary_json_path or os.path.join(repo_root, "data", "processed", "validation_summary.json")
        self.ref_date = reference_date
        self.engine = HealthStatusEngine(current_ref_date=reference_date)
        self.safety_gate = RecommendationSafetyGate(current_ref_date=reference_date)

    def load_report(
        self,
        simulated_state: Optional[OperationalState] = None,
        is_partial: bool = False,
        source_available: bool = True
    ) -> HealthReport:
        """Load health report from summary file or generate mock report."""
        if not os.path.exists(self.summary_path):
            return HealthReport(
                operational_state=OperationalState.UNINITIALIZED,
                freshness_status=FreshnessStatus.UNKNOWN,
                errors=[f"Summary manifest missing: {self.summary_path}"]
            )

        with open(self.summary_path, "r", encoding="utf-8") as f:
            summary_dict = json.load(f)

        report = self.engine.build_report_from_summary(
            summary_dict,
            is_source_live=False,
            source_available=source_available,
            is_partial=is_partial
        )

        if simulated_state:
            report.operational_state = simulated_state

        return report

    def query_latest_observation(
        self,
        commodity: Optional[str] = None,
        district: Optional[str] = None,
        market: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Query the most recent observation matching specified filters."""
        if not os.path.exists(self.csv_path):
            return None

        # Load minimal subset or recent rows
        df = pd.read_csv(self.csv_path, parse_dates=["Arrival_Date"], low_memory=False)

        if commodity:
            df = df[df["Commodity"].str.lower() == commodity.strip().lower()]
        if district:
            df = df[df["District"].str.lower() == district.strip().lower()]
        if market:
            df = df[df["Market"].str.lower() == market.strip().lower()]

        if df.empty:
            return None

        # Sort descending by date
        df_sorted = df.sort_values(by="Arrival_Date", ascending=False)
        latest_row = df_sorted.iloc[0]

        return {
            "Commodity": latest_row["Commodity"],
            "Variety": latest_row["Variety"],
            "Grade": latest_row["Grade"],
            "District": latest_row["District"],
            "Market": latest_row["Market"],
            "Arrival_Date": latest_row["Arrival_Date"].strftime("%Y-%m-%d"),
            "Modal_Price": float(latest_row["Modal_Price"]),
            "Min_Price": float(latest_row["Min_Price"]),
            "Max_Price": float(latest_row["Max_Price"]),
        }

    def evaluate_safety_gate(
        self,
        report: Optional[HealthReport] = None,
        observation_date: Optional[str] = None,
        is_demo: bool = False,
        is_historical: bool = False
    ) -> SafetyGateDecision:
        """Evaluate recommendation safety gate for this reporter instance."""
        rep = report or self.load_report()
        obs_d = observation_date or rep.latest_observation_date
        return self.safety_gate.evaluate_gate(
            observation_date=obs_d,
            operational_state=rep.operational_state,
            is_demo=is_demo,
            is_historical_analysis=is_historical,
            source_available=(not rep.is_fallback_active)
        )

    def render_ascii_dashboard(
        self,
        report: HealthReport,
        sample_query: Optional[Dict[str, Any]] = None,
        is_demo: bool = False,
        is_historical: bool = False
    ) -> str:
        """Render a clean, high-impact terminal dashboard."""
        lines = []
        width = 86

        gate_decision = self.safety_gate.evaluate_gate(
            observation_date=report.latest_observation_date,
            operational_state=report.operational_state,
            is_demo=is_demo,
            is_historical_analysis=is_historical,
            source_available=(not report.is_fallback_active)
        )

        if is_demo:
            lines.append("*" * width)
            lines.append("  [DEMO MODE] SIMULATED INTEGRATION DEMONSTRATION RUN")
            lines.append("  • Illustrative test run only; NOT a real mandi market data feed.")
            lines.append("  • Commercial and operational farmer recommendations are strictly disabled.")
            lines.append("*" * width)
        elif report.freshness_status == FreshnessStatus.STALE:
            lines.append("*" * width)
            lines.append("  ⚠️  STALE DATA WARNING — NOT A CURRENT PRICE (Illustrative display only)")
            lines.append(f"  • Latest Mandi Observation : {report.latest_observation_date} ({report.freshness_lag_days} calendar days lag)")
            lines.append("  • Active Advisory Status   : BLOCKED — HISTORICAL SNAPSHOT ONLY")
            lines.append("  • Directive                : Insufficient information to recommend storage.")
            lines.append("                               Latest market-price data is stale or unavailable.")
            lines.append("*" * width)
        elif report.freshness_status == FreshnessStatus.DELAYED:
            lines.append("-" * width)
            lines.append(f"  ⚠️  DELAYED DATA NOTICE: Observation is {report.freshness_lag_days} calendar days old ({report.latest_observation_date}).")
            lines.append("  • Not a live or today's price quote.")
            lines.append("-" * width)

        lines.append("=" * width)
        lines.append("           APMC MANDI MARKET INTELLIGENCE — CURRENT DATA & HEALTH REPORT           ")
        lines.append("=" * width)

        # Source Identity & Status
        lines.append(f"Source Name               : {report.source_name}")
        lines.append(f"Resource ID               : {report.resource_id}")

        # State badge
        state_badge = f"[{report.operational_state.value}]"
        lines.append(f"Operational Pipeline State: {state_badge:<25} (Source Live: {'YES' if report.is_source_live else 'OFFLINE SNAPSHOT'})")

        # Freshness badge
        fresh_str = f"[{report.freshness_status.value}]"
        if report.freshness_lag_days is not None:
            fresh_str += f" ({report.freshness_lag_days} calendar days lag from reference)"
        lines.append(f"Observation Freshness     : {fresh_str}")

        lines.append("-" * width)
        lines.append("TIMESTAMPS & AUDIT PROVENANCE:")
        lines.append(f"  • Latest Market Observation : {report.latest_observation_date or 'UNKNOWN'} (Date of Mandi Clearing)")
        lines.append(f"  • Last Retrieval (UTC)      : {report.last_successful_fetch_utc or 'UNKNOWN'}")
        lines.append(f"  • Last Retrieval (Local)    : {report.last_successful_fetch_local or 'UNKNOWN'}")
        lines.append(f"  • Current Report Generated  : {report.system_execution_time_local}")

        lines.append("-" * width)
        lines.append("RECONCILIATION LEDGER (SECTION 8 CONTRACT):")
        rec = report.reconciliation
        lines.append(f"  • Source Total Records    : {rec.source_total_records:>10,}")
        lines.append(f"  • Records Fetched         : {rec.records_fetched:>10,}")
        lines.append(f"  • Records Accepted (Clean): {rec.records_accepted:>10,}")
        lines.append(f"  • Records Quarantined     : {rec.records_quarantined:>10,} (Invalid / Conflicting)")
        lines.append(f"  • Exact Unchanged Dups    : {rec.records_unchanged:>10,}")
        lines.append(f"  • Active Unique Series    : {rec.current_unique_keys:>10,}")
        if rec.snapshot_sha256:
            lines.append(f"  • Snapshot SHA-256 Checksum: {rec.snapshot_sha256[:32]}...")

        lines.append("-" * width)
        lines.append("FARMER ADVISORY SAFETY GATE:")
        status_tag = f"[{gate_decision.recommendation_status}]"
        lines.append(f"  • Recommendation Status   : {status_tag:<20} (Advice Permitted: {'YES' if gate_decision.is_permitted else 'NO (BLOCKED)'})")
        lines.append(f"  • Safety Gate Directive   : {gate_decision.message}")
        if gate_decision.blocked_reason:
            lines.append(f"  • Blocking Detail         : {gate_decision.blocked_reason}")

        lines.append("-" * width)
        lines.append("GEOGRAPHIC & COMMODITY COVERAGE:")
        districts_str = ", ".join(report.districts_represented) if report.districts_represented else "None"
        lines.append(f"  • Active Districts ({len(report.districts_represented)}) : {districts_str}")
        lines.append(f"  • Distinct APMC Markets   : {report.markets_count}")
        lines.append(f"  • Distinct Commodities    : {report.commodities_count}")

        if sample_query:
            lines.append("-" * width)
            lines.append("LATEST MARKET OBSERVATION LOOKUP:")
            lines.append(f"  Crop / Variety : {sample_query['Commodity']} ({sample_query['Variety']} | {sample_query['Grade']})")
            lines.append(f"  Mandi Yard     : {sample_query['Market']} ({sample_query['District']})")
            lines.append(f"  Date of Trade  : {sample_query['Arrival_Date']}")
            lines.append(f"  Wholesale Price: Modal ₹{sample_query['Modal_Price']:,.2f}/qtl  |  Min ₹{sample_query['Min_Price']:,.2f}  |  Max ₹{sample_query['Max_Price']:,.2f}")

        # Active Warnings / Failures
        if report.warnings or report.errors:
            lines.append("-" * width)
            lines.append("SYSTEM ALERTS & DATA QUALITY WARNINGS:")
            for w in report.warnings:
                lines.append(f"  [WARN] {w}")
            for e in report.errors:
                lines.append(f"  [ERROR] {e}")

        lines.append("=" * width)
        lines.append("OPERATIONAL NOTE: Always verify Observation Date prior to executing commercial advice.")
        lines.append("=" * width)

        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="APMC Mandi Current-Data Operational Dashboard")
    parser.add_argument("--data-file", type=str, default=None, help="Path to validated CSV dataset")
    parser.add_argument("--summary-file", type=str, default=None, help="Path to validation summary JSON")
    parser.add_argument("--commodity", type=str, default="Potato", help="Target commodity lookup (default: Potato)")
    parser.add_argument("--district", type=str, default="Kanpur", help="Target district lookup (default: Kanpur)")
    parser.add_argument("--market", type=str, default=None, help="Target market lookup")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON format")
    parser.add_argument("--demo", action="store_true", help="Run end-to-end integration demo")
    parser.add_argument("--sim-state", type=str, choices=[s.value for s in OperationalState], help="Simulate a specific operational state")

    args = parser.parse_args()

    reporter = CurrentDataReporter(
        validated_csv_path=args.data_file,
        summary_json_path=args.summary_file
    )

    sim_state_enum = OperationalState(args.sim_state) if args.sim_state else None
    report = reporter.load_report(simulated_state=sim_state_enum)

    # Perform sample lookup if CSV is present
    lookup_sample = None
    if os.path.exists(reporter.csv_path):
        lookup_sample = reporter.query_latest_observation(
            commodity=args.commodity,
            district=args.district,
            market=args.market
        )

    gate_decision = reporter.evaluate_safety_gate(report=report, is_demo=args.demo)

    if args.json:
        output_payload = report.to_dict()
        output_payload["is_demo"] = args.demo
        output_payload["recommendation_safety_gate"] = gate_decision.to_dict()
        if lookup_sample:
            output_payload["sample_observation_lookup"] = lookup_sample
        print(json.dumps(output_payload, indent=2))
    else:
        dashboard = reporter.render_ascii_dashboard(report, sample_query=lookup_sample, is_demo=args.demo)
        print(dashboard)


if __name__ == "__main__":
    main()
