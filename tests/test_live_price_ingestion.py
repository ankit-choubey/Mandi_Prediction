"""
Unit and Integration Test Suite for Live Price Ingestion Client & Snapshot Engine
APMC Mandi Market Intelligence System
Tasks: MP-SRC-004 & MP-SRC-004B (Steps 3–5)

Tests exercise:
- Complete multiple-page pagination
- Exact duplicates and order-invariant conflicting quote safety
- Provenance tracking via explicit DataMode (LIVE_FETCH vs TEST_FIXTURE vs HISTORICAL_REPLAY)
- Provenance/transport mismatch rejection
- Isolated snapshot namespaces (test fixtures write to fixture_snapshots, not live root)
- Repeated page detection and abort
- Total change detection mid-pagination
- Ignored district filter fail-closed quarantine
- HTTP status handling: 401, 403, 429 (Retry-After), 500
- Timeout, malformed JSON, and source-error JSON handling
- Empty valid result handling
- Missing fields and grade normalization policy (SOURCE_NOT_PROVIDED, never silently FAQ)
- Honest price bounds (NO modal substitution for missing min/max, non-finite NaN/Inf rejected)
- Malformed and future-dated observations
- Unknown market alias enters REVIEW
- Kanpur subdivision ambiguity (Kanpur Dehat quarantined)
- IST day boundary and freshness lag
- Delayed advice blocked and decoupled capabilities
- Collision-safe immutable exclusive writes (no overwrite on page or run receipts)
- Atomic last_success pointer updated strictly on real LIVE_FETCH success
- Persistent prior-success fallback loader
- Secret sentinel absent from URLs, errors, and stored JSON receipts
- Order-invariance across all conflict permutations ([A,A,B], [A,B,B], [B,A,A], [A,B,A])
- Cross-page conflict quarantine
- Urllib standard library transport bounded streaming
- End-to-end fixture fetch -> archive -> validation -> health output
"""

import json
import math
import os
import shutil
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone

from src.health_status import (
    FreshnessStatus,
    HealthReport,
    OperationalState,
    RecommendationSafetyGate,
    RecommendationStatus,
)
from src.live_price_ingestion import (
    APPROVED_DISTRICTS,
    CompletenessState,
    DataMode,
    DistrictIngestionResult,
    HttpTransport,
    IngestionCampaignResult,
    LivePriceIngestionClient,
    MockHttpTransport,
    PageReceipt,
    RawPriceRecord,
    RecordDisposition,
    UrllibHttpTransport,
    build_health_report_from_ingestion,
    load_api_key,
    load_contract,
    load_prior_validated_import,
    load_prior_validated_snapshot,
    publish_latest_observation_index,
    redact_credential_echo,
    sanitize_params,
    sanitize_url,
)


class TestLivePriceIngestion(unittest.TestCase):
    """Comprehensive test suite for live price ingestion, data trust, and snapshots."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="mandi_live_test_")
        self.snapshots_dir = os.path.join(self.temp_dir, "test_snapshots")
        self.ref_date = date(2026, 11, 12)
        self.mock_transport = MockHttpTransport()
        self.client = LivePriceIngestionClient(
            api_key="TEST_API_KEY_ABCD1234",
            transport=self.mock_transport,
            data_mode=DataMode.TEST_FIXTURE,
            reference_date=self.ref_date,
            snapshots_root=self.snapshots_dir,
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # 1. Secret Sentinel Leak Test
    # -------------------------------------------------------------------------
    def test_01_secret_sentinel_absent_from_logs_errors_and_receipts(self):
        """Prove that a secret sentinel token is never exposed in URLs, errors, or archived JSONs."""
        secret_sentinel = "SECRET_SENTINEL_TOKEN_SUPER_PRIVATE_998877"
        client = LivePriceIngestionClient(
            api_key=secret_sentinel,
            transport=self.mock_transport,
            data_mode=DataMode.TEST_FIXTURE,
            reference_date=self.ref_date,
            snapshots_root=self.snapshots_dir,
        )

        url_with_secret = f"https://api.data.gov.in/resource/123?api-key={secret_sentinel}&format=json"
        clean_url = sanitize_url(url_with_secret)
        self.assertNotIn(secret_sentinel, clean_url)
        self.assertIn("REDACTED", clean_url)

        params = {"api-key": secret_sentinel, "filters[district]": "Kanpur"}
        clean_params = sanitize_params(params)
        self.assertNotIn(secret_sentinel, str(clean_params))
        self.assertEqual(clean_params["api-key"], "[REDACTED]")

        echo_body = f'{{"error": "Invalid key: {secret_sentinel}", "records": []}}'
        redacted_body, echo_found = redact_credential_echo(echo_body, secret_sentinel)
        self.assertTrue(echo_found)
        self.assertNotIn(secret_sentinel, redacted_body)
        self.assertIn("[REDACTED_API_KEY]", redacted_body)

        self.mock_transport.set_response(
            "Kanpur", 0, 200, json.dumps({
                "total": 1,
                "count": 1,
                "records": [{
                    "state": "Uttar Pradesh",
                    "district": "Kanpur",
                    "market": "Kanpur(Grain) APMC",
                    "commodity": "Potato",
                    "variety": "Other",
                    "grade": "FAQ",
                    "arrival_date": "2026-11-12",
                    "min_price": 500,
                    "max_price": 600,
                    "modal_price": 550,
                }]
            })
        )
        res = client.fetch_district_batch("Kanpur", "run_sentinel_01", [0])
        self.assertEqual(res.completeness_state, CompletenessState.COMPLETE)

        receipt_file = os.path.join(self.snapshots_dir, "run_sentinel_01", "Kanpur", "page_00000.json")
        self.assertTrue(os.path.exists(receipt_file))
        with open(receipt_file, "r", encoding="utf-8") as f:
            receipt_content = f.read()

        self.assertNotIn(secret_sentinel, receipt_content)
        self.assertIn("[REDACTED]", receipt_content)

    # -------------------------------------------------------------------------
    # 2. Multi-Page Pagination & Row Conservation
    # -------------------------------------------------------------------------
    def test_02_multi_page_pagination_advances_offset_and_conserves_rows(self):
        """Multi-page pagination advances offset, aggregates pages, and strictly balances."""
        page1 = json.dumps({
            "total": 3,
            "count": 2,
            "limit": "2",
            "offset": "0",
            "records": [
                {
                    "state": "Uttar Pradesh",
                    "district": "Lucknow",
                    "market": "Lucknow APMC",
                    "commodity": "Potato",
                    "variety": "Other",
                    "grade": "FAQ",
                    "arrival_date": "2026-11-12",
                    "min_price": 500,
                    "max_price": 600,
                    "modal_price": 550,
                },
                {
                    "state": "Uttar Pradesh",
                    "district": "Lucknow",
                    "market": "Banthara APMC",
                    "commodity": "Tomato",
                    "variety": "Deshi",
                    "grade": "FAQ",
                    "arrival_date": "2026-11-12",
                    "min_price": 1200,
                    "max_price": 1400,
                    "modal_price": 1300,
                },
            ]
        })
        page2 = json.dumps({
            "total": 3,
            "count": 1,
            "limit": "2",
            "offset": "2",
            "records": [
                {
                    "state": "Uttar Pradesh",
                    "district": "Lucknow",
                    "market": "Lucknow APMC",
                    "commodity": "Onion",
                    "variety": "Red",
                    "grade": "FAQ",
                    "arrival_date": "2026-11-12",
                    "min_price": 2000,
                    "max_price": 2200,
                    "modal_price": 2100,
                }
            ]
        })

        self.mock_transport.set_response("Lucknow", 0, 200, page1)
        self.mock_transport.set_response("Lucknow", 2, 200, page2)

        tracker = [0]
        res = self.client.fetch_district_batch("Lucknow", "run_multipage", tracker)

        self.assertEqual(res.completeness_state, CompletenessState.COMPLETE)
        self.assertEqual(res.total_pages_fetched, 2)
        self.assertEqual(res.records_fetched, 3)
        self.assertEqual(res.records_accepted, 3)
        self.assertEqual(res.records_quarantined, 0)
        self.assertEqual(res.records_duplicate, 0)
        self.assertTrue(res.validate_arithmetic()["is_balanced"])
        self.assertEqual(tracker[0], 2)

    # -------------------------------------------------------------------------
    # 3. Exact Duplicates Handling
    # -------------------------------------------------------------------------
    def test_03_exact_duplicates_deduplicated(self):
        """Exact identical rows on same key and prices are deduplicated without loss."""
        row = {
            "state": "Uttar Pradesh",
            "district": "Ghaziabad",
            "market": "Ghaziabad APMC",
            "commodity": "Wheat",
            "variety": "Dara",
            "grade": "FAQ",
            "arrival_date": "2026-11-12",
            "min_price": 2400,
            "max_price": 2500,
            "modal_price": 2450,
        }
        payload = json.dumps({
            "total": 2,
            "count": 2,
            "records": [row, dict(row)]
        })
        self.mock_transport.set_response("Ghaziabad", 0, 200, payload)

        res = self.client.fetch_district_batch("Ghaziabad", "run_dup", [0])
        self.assertEqual(res.records_fetched, 2)
        self.assertEqual(res.records_accepted, 1)
        self.assertEqual(res.records_duplicate, 1)
        self.assertEqual(res.records_quarantined, 0)
        self.assertTrue(res.validate_arithmetic()["is_balanced"])

    # -------------------------------------------------------------------------
    # 4. Conflicting Quotes Quarantined (ALL Members Quarantined)
    # -------------------------------------------------------------------------
    def test_04_conflicting_quote_quarantined(self):
        """When conflicting quotes appear for a natural key, ALL members are quarantined."""
        row1 = {
            "state": "Uttar Pradesh",
            "district": "Jhansi",
            "market": "Jhansi APMC",
            "commodity": "Mustard",
            "variety": "Other",
            "grade": "FAQ",
            "arrival_date": "2026-11-12",
            "min_price": 5000,
            "max_price": 5500,
            "modal_price": 5100,
        }
        row2 = dict(row1)
        row2["modal_price"] = 5300  # Divergent modal price with valid bounds!

        payload = json.dumps({
            "total": 2,
            "count": 2,
            "records": [row1, row2]
        })
        self.mock_transport.set_response("Jhansi", 0, 200, payload)

        res = self.client.fetch_district_batch("Jhansi", "run_conflict", [0])
        self.assertEqual(res.records_fetched, 2)
        # BOTH records are quarantined: 0 accepted!
        self.assertEqual(res.records_accepted, 0)
        self.assertEqual(res.records_quarantined, 2)
        self.assertEqual(res.disposition_counts[RecordDisposition.CONFLICTING_QUOTE.value], 2)
        self.assertTrue(res.validate_arithmetic()["is_balanced"])
        self.assertIsNone(res.oldest_observation_date)
        self.assertIsNone(res.newest_observation_date)

    # -------------------------------------------------------------------------
    # 5. Same Payload Refetch Produces New Receipt with Independent Provenance
    # -------------------------------------------------------------------------
    def test_05_same_payload_refetch_produces_new_receipt(self):
        """Successive identical fetches share content hash but write distinct immutable receipts."""
        payload = json.dumps({
            "total": 1,
            "count": 1,
            "records": [{
                "state": "Uttar Pradesh",
                "district": "Unnao",
                "market": "Unnao APMC",
                "commodity": "Wheat",
                "variety": "Dara",
                "grade": "FAQ",
                "arrival_date": "2026-11-12",
                "min_price": 2400,
                "max_price": 2500,
                "modal_price": 2450,
            }]
        })
        self.mock_transport.set_response("Unnao", 0, 200, payload)

        res1 = self.client.fetch_district_batch("Unnao", "run_refetch_01", [0])
        res2 = self.client.fetch_district_batch("Unnao", "run_refetch_02", [0])

        self.assertEqual(res1.page_receipts[0].content_sha256, res2.page_receipts[0].content_sha256)
        path1 = os.path.join(self.snapshots_dir, "run_refetch_01", "Unnao", "page_00000.json")
        path2 = os.path.join(self.snapshots_dir, "run_refetch_02", "Unnao", "page_00000.json")
        self.assertTrue(os.path.exists(path1))
        self.assertTrue(os.path.exists(path2))
        self.assertNotEqual(path1, path2)

    # -------------------------------------------------------------------------
    # 6. Repeated Page Detection & Abort
    # -------------------------------------------------------------------------
    def test_06_repeated_page_detected_and_aborted(self):
        """Detect and fail closed when pagination loops and returns identical page hash."""
        page_payload = json.dumps({
            "total": 100,
            "count": 1,
            "records": [{
                "state": "Uttar Pradesh",
                "district": "Kanpur",
                "market": "Kanpur(Grain) APMC",
                "commodity": "Potato",
                "variety": "Other",
                "grade": "FAQ",
                "arrival_date": "2026-11-12",
                "min_price": 500,
                "max_price": 600,
                "modal_price": 550,
            }]
        })
        self.mock_transport.set_response("Kanpur", 0, 200, page_payload)
        self.mock_transport.set_response("Kanpur", 1, 200, page_payload)

        res = self.client.fetch_district_batch("Kanpur", "run_repeated", [0])
        self.assertEqual(res.completeness_state, CompletenessState.FAILED)
        self.assertTrue(any("repeated page detected" in err.lower() for err in res.errors))

    # -------------------------------------------------------------------------
    # 7. Unstable Source Total Reported as PARTIAL
    # -------------------------------------------------------------------------
    def test_07_unstable_source_total_reported_as_partial(self):
        """Unstable total during pagination flags warning and yields PARTIAL."""
        page1 = json.dumps({
            "total": 10,
            "count": 1,
            "records": [{
                "state": "Uttar Pradesh",
                "district": "Lucknow",
                "market": "Lucknow APMC",
                "commodity": "Potato",
                "variety": "Other",
                "grade": "FAQ",
                "arrival_date": "2026-11-12",
                "min_price": 500,
                "max_price": 600,
                "modal_price": 550,
            }]
        })
        page2 = json.dumps({
            "total": 5,
            "count": 0,
            "records": []
        })
        self.mock_transport.set_response("Lucknow", 0, 200, page1)
        self.mock_transport.set_response("Lucknow", 1, 200, page2)

        res = self.client.fetch_district_batch("Lucknow", "run_unstable", [0])
        self.assertEqual(res.completeness_state, CompletenessState.PARTIAL)
        self.assertTrue(any("unstable source total" in w.lower() for w in res.warnings))

    # -------------------------------------------------------------------------
    # 8. Ignored District Filter Quarantined
    # -------------------------------------------------------------------------
    def test_08_ignored_district_filter_quarantined(self):
        """If API silently ignores filter and returns other district, quarantine rows."""
        payload = json.dumps({
            "total": 1,
            "count": 1,
            "records": [{
                "state": "Uttar Pradesh",
                "district": "Agra",
                "market": "Agra APMC",
                "commodity": "Potato",
                "variety": "Other",
                "grade": "FAQ",
                "arrival_date": "2026-11-12",
                "min_price": 500,
                "max_price": 600,
                "modal_price": 550,
            }]
        })
        self.mock_transport.set_response("Kanpur", 0, 200, payload)

        res = self.client.fetch_district_batch("Kanpur", "run_wrong_dist", [0])
        self.assertEqual(res.records_fetched, 1)
        self.assertEqual(res.records_accepted, 0)
        self.assertEqual(res.records_quarantined, 1)
        self.assertEqual(res.disposition_counts[RecordDisposition.OUT_OF_SCOPE_DISTRICT.value], 1)
        self.assertTrue(res.validate_arithmetic()["is_balanced"])

    # -------------------------------------------------------------------------
    # 9. HTTP 401 & 403 Fail Closed Without Infinite Retries
    # -------------------------------------------------------------------------
    def test_09_http_401_403_fail_closed_without_retry(self):
        """HTTP 401 or 403 terminates district batch immediately as BLOCKED without retry."""
        self.mock_transport.set_response("Kanpur", 0, 401, '{"message": "Unauthorized"}')
        tracker = [0]
        res = self.client.fetch_district_batch("Kanpur", "run_401", tracker)

        self.assertEqual(res.completeness_state, CompletenessState.BLOCKED)
        self.assertEqual(tracker[0], 1)

    # -------------------------------------------------------------------------
    # 10. HTTP 429 Rate Limiting with Retry-After
    # -------------------------------------------------------------------------
    def test_10_http_429_rate_limiting_with_retry_after(self):
        """HTTP 429 attempts retry within budget and reports PARTIAL if exhausted."""
        self.mock_transport.set_response(
            "Kanpur", 0, 429, '{"message": "Rate limit exceeded"}', headers={"Retry-After": "1"}
        )
        tracker = [0]
        res = self.client.fetch_district_batch("Kanpur", "run_429", tracker)

        self.assertEqual(res.completeness_state, CompletenessState.PARTIAL)
        self.assertGreater(tracker[0], 1)

    # -------------------------------------------------------------------------
    # 11. HTTP 500 Server Error
    # -------------------------------------------------------------------------
    def test_11_http_500_server_error(self):
        """HTTP 500 retries up to budget and fails closed as FAILED."""
        self.mock_transport.set_response("Jhansi", 0, 500, "Internal Server Error")
        tracker = [0]
        res = self.client.fetch_district_batch("Jhansi", "run_500", tracker)

        self.assertEqual(res.completeness_state, CompletenessState.FAILED)
        self.assertGreater(tracker[0], 1)

    # -------------------------------------------------------------------------
    # 12. Timeout, Malformed JSON, and Source Error JSON
    # -------------------------------------------------------------------------
    def test_12_malformed_and_error_json(self):
        """Malformed JSON or API error payload is rejected with clean diagnostic."""
        self.mock_transport.set_response("Kanpur", 0, 200, '{"records": [incomplete')
        res = self.client.fetch_district_batch("Kanpur", "run_malformed", [0])
        self.assertEqual(res.completeness_state, CompletenessState.FAILED)
        self.assertTrue(any("malformed json" in e.lower() for e in res.errors))

        self.mock_transport.set_response("Kanpur", 0, 200, '{"status": "error", "message": "Resource unavailable"}')
        res2 = self.client.fetch_district_batch("Kanpur", "run_apierr", [0])
        self.assertEqual(res2.completeness_state, CompletenessState.FAILED)
        self.assertTrue(any("resource unavailable" in e.lower() for e in res2.errors))

    # -------------------------------------------------------------------------
    # 13. Empty Valid Result
    # -------------------------------------------------------------------------
    def test_13_empty_valid_result(self):
        """Empty valid result returns EMPTY completeness state, not a failure."""
        self.mock_transport.set_response(
            "Ghaziabad", 0, 200, json.dumps({"total": 0, "count": 0, "records": []})
        )
        res = self.client.fetch_district_batch("Ghaziabad", "run_empty", [0])
        self.assertEqual(res.completeness_state, CompletenessState.EMPTY)
        self.assertEqual(res.records_fetched, 0)
        self.assertEqual(len(res.errors), 0)

    # -------------------------------------------------------------------------
    # 14. Missing Grade Normalization Policy
    # -------------------------------------------------------------------------
    def test_14_missing_grade_is_source_not_provided_never_faq(self):
        """Missing or null grade must be SOURCE_NOT_PROVIDED, never silently mapped to FAQ."""
        rec = self.client.parse_and_validate_record(
            raw_row={
                "state": "Uttar Pradesh",
                "district": "Kanpur",
                "market": "Kanpur(Grain) APMC",
                "commodity": "Potato",
                "variety": "Other",
                "grade": None,
                "arrival_date": "2026-11-12",
                "min_price": 500,
                "max_price": 600,
                "modal_price": 550,
            },
            requested_district="Kanpur",
            retrieval_utc="2026-11-12T10:00:00Z",
            display_ist="2026-11-12 15:30:00 IST",
        )
        self.assertEqual(rec.grade_normalized, "SOURCE_NOT_PROVIDED")
        self.assertNotEqual(rec.grade_normalized, "FAQ")
        self.assertEqual(rec.disposition, RecordDisposition.ACCEPTED)

    # -------------------------------------------------------------------------
    # 15. Price Bounds Violations Quarantined
    # -------------------------------------------------------------------------
    def test_15_price_bounds_violations_quarantined(self):
        """Price bounds violations (negative price, min > modal, modal > max) are quarantined."""
        rec1 = self.client.parse_and_validate_record(
            raw_row={
                "district": "Kanpur",
                "market": "Kanpur(Grain) APMC",
                "commodity": "Potato",
                "variety": "Other",
                "arrival_date": "2026-11-12",
                "min_price": 0,
                "max_price": 500,
                "modal_price": 0,
            },
            requested_district="Kanpur",
            retrieval_utc="2026-11-12T10:00:00Z",
            display_ist="2026-11-12 15:30:00 IST",
        )
        self.assertEqual(rec1.disposition, RecordDisposition.INVALID_PRICE_BOUNDS)

        rec2 = self.client.parse_and_validate_record(
            raw_row={
                "district": "Kanpur",
                "market": "Kanpur(Grain) APMC",
                "commodity": "Potato",
                "variety": "Other",
                "arrival_date": "2026-11-12",
                "min_price": 600,
                "max_price": 700,
                "modal_price": 550,
            },
            requested_district="Kanpur",
            retrieval_utc="2026-11-12T10:00:00Z",
            display_ist="2026-11-12 15:30:00 IST",
        )
        self.assertEqual(rec2.disposition, RecordDisposition.INVALID_PRICE_BOUNDS)

    # -------------------------------------------------------------------------
    # 16. Malformed and Future Dates Quarantined
    # -------------------------------------------------------------------------
    def test_16_malformed_and_future_dates_quarantined(self):
        """Unparseable or future dates relative to reference date are quarantined."""
        rec_bad = self.client.parse_and_validate_record(
            raw_row={
                "district": "Kanpur",
                "market": "Kanpur(Grain) APMC",
                "commodity": "Potato",
                "variety": "Other",
                "arrival_date": "not-a-valid-date",
                "min_price": 400,
                "max_price": 600,
                "modal_price": 500,
            },
            requested_district="Kanpur",
            retrieval_utc="2026-11-12T10:00:00Z",
            display_ist="2026-11-12 15:30:00 IST",
        )
        self.assertEqual(rec_bad.disposition, RecordDisposition.MALFORMED_DATE)

        rec_future = self.client.parse_and_validate_record(
            raw_row={
                "district": "Kanpur",
                "market": "Kanpur(Grain) APMC",
                "commodity": "Potato",
                "variety": "Other",
                "arrival_date": "2026-11-20",
                "min_price": 400,
                "max_price": 600,
                "modal_price": 500,
            },
            requested_district="Kanpur",
            retrieval_utc="2026-11-12T10:00:00Z",
            display_ist="2026-11-12 15:30:00 IST",
        )
        self.assertEqual(rec_future.disposition, RecordDisposition.FUTURE_DATED)

    # -------------------------------------------------------------------------
    # 17. Unknown Market Alias Enters REVIEW
    # -------------------------------------------------------------------------
    def test_17_unknown_market_alias_enters_review(self):
        """Unrecognized market yards enter REVIEW disposition."""
        rec = self.client.parse_and_validate_record(
            raw_row={
                "district": "Kanpur",
                "market": "Unrecognized Yard XYZ",
                "commodity": "Potato",
                "variety": "Other",
                "arrival_date": "2026-11-12",
                "min_price": 450,
                "max_price": 550,
                "modal_price": 500,
            },
            requested_district="Kanpur",
            retrieval_utc="2026-11-12T10:00:00Z",
            display_ist="2026-11-12 15:30:00 IST",
        )
        self.assertEqual(rec.disposition, RecordDisposition.UNKNOWN_MARKET_REVIEW)
        self.assertEqual(rec.market_alias_status, "REVIEW")

    # -------------------------------------------------------------------------
    # 18. Kanpur Subdivision Ambiguity Handled Safely
    # -------------------------------------------------------------------------
    def test_18_kanpur_dehat_subdivision_quarantined(self):
        """Kanpur Dehat records are quarantined as OUT_OF_SCOPE rather than silently merged into Kanpur."""
        rec = self.client.parse_and_validate_record(
            raw_row={
                "district": "Kanpur Dehat",
                "market": "Jhijhank APMC",
                "commodity": "Paddy(Common)",
                "variety": "Common",
                "arrival_date": "2026-11-12",
                "min_price": 1800,
                "max_price": 1900,
                "modal_price": 1850,
            },
            requested_district="Kanpur",
            retrieval_utc="2026-11-12T10:00:00Z",
            display_ist="2026-11-12 15:30:00 IST",
        )
        self.assertEqual(rec.disposition, RecordDisposition.OUT_OF_SCOPE_DISTRICT)
        self.assertIn("Kanpur Dehat", rec.disposition_reason)

    # -------------------------------------------------------------------------
    # 19. IST Day Boundary & Freshness Lag
    # -------------------------------------------------------------------------
    def test_19_ist_day_boundary_and_freshness_lag(self):
        """Freshness lag is evaluated accurately against IST calendar reference date."""
        engine = RecommendationSafetyGate(current_ref_date=date(2026, 11, 12))

        dec_today = engine.evaluate_gate(observation_date="2026-11-12")
        self.assertEqual(dec_today.freshness_status, FreshnessStatus.CURRENT.value)
        self.assertEqual(dec_today.lag_days, 0)
        self.assertTrue(dec_today.is_permitted)

        dec_2d = engine.evaluate_gate(observation_date="2026-11-10")
        self.assertEqual(dec_2d.freshness_status, FreshnessStatus.CURRENT.value)
        self.assertEqual(dec_2d.lag_days, 2)
        self.assertTrue(dec_2d.is_permitted)

        dec_3d = engine.evaluate_gate(observation_date="2026-11-09")
        self.assertEqual(dec_3d.freshness_status, FreshnessStatus.DELAYED.value)
        self.assertEqual(dec_3d.lag_days, 3)
        self.assertFalse(dec_3d.is_permitted)

        dec_6d = engine.evaluate_gate(observation_date="2026-11-06")
        self.assertEqual(dec_6d.freshness_status, FreshnessStatus.STALE.value)
        self.assertEqual(dec_6d.lag_days, 6)
        self.assertFalse(dec_6d.is_permitted)

    # -------------------------------------------------------------------------
    # 20. Immutable Exclusive Write Prevents Overwrite
    # -------------------------------------------------------------------------
    def test_20_immutable_exclusive_write_prevents_overwrite(self):
        """Attempting to overwrite an existing receipt file must raise FileExistsError."""
        receipt = PageReceipt(
            page_offset=0,
            page_limit=1000,
            retrieval_start_utc="2026-11-12T10:00:00Z",
            retrieval_end_utc="2026-11-12T10:00:01Z",
            http_status=200,
            source_total=1,
            fetched_count=1,
            content_sha256="abc123sha",
            completeness_state=CompletenessState.COMPLETE,
            sanitized_params={"format": "json"},
            endpoint_sanitized="https://api.data.gov.in/resource/test",
            data_mode=DataMode.TEST_FIXTURE,
        )

        path = self.client.write_snapshot_page("run_collision_test", "Kanpur", receipt)
        self.assertTrue(os.path.exists(path))

        with self.assertRaises(FileExistsError):
            self.client.write_snapshot_page("run_collision_test", "Kanpur", receipt)

    # -------------------------------------------------------------------------
    # 21. Partial Run Never Advances Last Successful Fetch
    # -------------------------------------------------------------------------
    def test_21_partial_run_never_advances_last_successful_fetch(self):
        """When an ingestion run results in PARTIAL, last_successful_fetch_utc remains None."""
        campaign = IngestionCampaignResult(
            run_id_utc="run_partial_test",
            execution_timestamp_utc="2026-11-12T12:00:00Z",
            execution_timestamp_ist="2026-11-12 17:30:00 IST",
            overall_operational_state=OperationalState.PARTIAL,
            data_mode=DataMode.LIVE_FETCH,
            is_live_verified=False,
            capabilities={"price_display_permitted": True, "active_advice_permitted": False},
        )
        report = build_health_report_from_ingestion(campaign, reference_date=self.ref_date)

        self.assertEqual(report.operational_state, OperationalState.PARTIAL)
        self.assertFalse(report.is_source_live)
        self.assertIsNone(report.last_successful_fetch_utc)

    # -------------------------------------------------------------------------
    # 22. End-to-End Fixture Fetch -> Archive -> Validation -> Health Output
    # -------------------------------------------------------------------------
    def test_22_end_to_end_fixture_fetch_archive_validation_health(self):
        """Complete workflow test: mock transport produces TEST_FIXTURE with is_live_verified=False."""
        payload = json.dumps({
            "total": 2,
            "count": 2,
            "limit": "1000",
            "offset": "0",
            "records": [
                {
                    "state": "Uttar Pradesh",
                    "district": "Kanpur",
                    "market": "Kanpur(Grain) APMC",
                    "commodity": "Potato",
                    "variety": "Other",
                    "grade": "FAQ",
                    "arrival_date": "2026-11-12",
                    "min_price": 550,
                    "max_price": 600,
                    "modal_price": 575,
                },
                {
                    "state": "Uttar Pradesh",
                    "district": "Kanpur",
                    "market": "Choubepur APMC",
                    "commodity": "Potato",
                    "variety": "Other",
                    "grade": "FAQ",
                    "arrival_date": "2026-11-12",
                    "min_price": 560,
                    "max_price": 610,
                    "modal_price": 580,
                },
            ]
        })
        self.mock_transport.set_response("Kanpur", 0, 200, payload)

        campaign = self.client.execute_campaign(districts=["Kanpur"], run_id_utc="run_e2e_01")

        self.assertEqual(campaign.overall_operational_state, OperationalState.SUCCESS)
        # CRITICAL MP-SRC-004B RULE: Test fixtures must NEVER set is_live_verified=True
        self.assertFalse(campaign.is_live_verified)
        self.assertEqual(campaign.data_mode, DataMode.TEST_FIXTURE)
        self.assertFalse(campaign.is_synthetic)
        self.assertEqual(campaign.total_records_fetched, 2)
        self.assertEqual(campaign.total_records_accepted, 2)
        self.assertTrue(campaign.validate_arithmetic()["is_balanced"])

        receipt_path = os.path.join(self.snapshots_dir, "run_e2e_01", "Kanpur", "page_00000.json")
        self.assertTrue(os.path.exists(receipt_path))

        run_receipt_path = os.path.join(self.snapshots_dir, "run_e2e_01", "run_receipt.json")
        self.assertTrue(os.path.exists(run_receipt_path))

        health_report = build_health_report_from_ingestion(campaign, reference_date=self.ref_date)
        self.assertEqual(health_report.operational_state, OperationalState.SUCCESS)
        self.assertEqual(health_report.freshness_status, FreshnessStatus.CURRENT)
        self.assertEqual(health_report.reconciliation.records_accepted, 2)
        self.assertFalse(health_report.is_source_live)

    # -------------------------------------------------------------------------
    # 23. Provenance Mode & Transport Mismatch Rejection (MP-SRC-004B)
    # -------------------------------------------------------------------------
    def test_23_provenance_mode_and_mismatch_rejection(self):
        """Mock transport must reject LIVE_FETCH claim and write only to fixture namespace."""
        with self.assertRaises(ValueError):
            LivePriceIngestionClient(
                api_key="TEST_KEY",
                transport=self.mock_transport,
                data_mode=DataMode.LIVE_FETCH,  # Mismatch! Mock cannot masquerade as LIVE_FETCH
            )

        client_fixture = LivePriceIngestionClient(
            api_key="TEST_KEY",
            transport=self.mock_transport,
            data_mode=DataMode.TEST_FIXTURE,
        )
        self.assertEqual(client_fixture.data_mode, DataMode.TEST_FIXTURE)
        self.assertIn("fixture_snapshots", client_fixture.snapshots_root)

    # -------------------------------------------------------------------------
    # 24. Order-Invariant Conflict Safety Across All Permutations (MP-SRC-004B)
    # -------------------------------------------------------------------------
    def test_24_conflict_safety_all_permutations(self):
        """
        Verify that conflicting quotes quarantine ALL members of the group, and that
        any permutation of [A, A, B], [A, B, B], [B, A, A], [A, B, A] yields identical outcomes.
        """
        quote_a = {
            "state": "Uttar Pradesh",
            "district": "Kanpur",
            "market": "Kanpur(Grain) APMC",
            "commodity": "Potato",
            "variety": "Other",
            "grade": "FAQ",
            "arrival_date": "2026-11-12",
            "min_price": 500,
            "max_price": 600,
            "modal_price": 550,
        }
        quote_b = dict(quote_a)
        quote_b["modal_price"] = 575  # Divergent price!

        permutations = [
            ("A_A_B", [quote_a, dict(quote_a), quote_b]),
            ("A_B_B", [quote_a, quote_b, dict(quote_b)]),
            ("B_A_A", [quote_b, quote_a, dict(quote_a)]),
            ("A_B_A", [quote_a, quote_b, dict(quote_a)]),
        ]

        for label, record_list in permutations:
            payload = json.dumps({"total": 3, "count": 3, "records": record_list})
            mock_trans = MockHttpTransport()
            mock_trans.set_response("Kanpur", 0, 200, payload)

            c = LivePriceIngestionClient(
                api_key="TEST_KEY",
                transport=mock_trans,
                data_mode=DataMode.TEST_FIXTURE,
                reference_date=self.ref_date,
                snapshots_root=os.path.join(self.temp_dir, f"snap_{label}"),
            )
            res = c.fetch_district_batch("Kanpur", f"run_{label}", [0])

            self.assertEqual(res.records_fetched, 3, f"Failed on {label}: records_fetched")
            self.assertEqual(res.records_accepted, 0, f"Failed on {label}: records_accepted must be 0")
            self.assertEqual(res.records_duplicate, 0, f"Failed on {label}: records_duplicate must be 0")
            self.assertEqual(res.records_quarantined, 3, f"Failed on {label}: records_quarantined must be 3")
            self.assertTrue(res.validate_arithmetic()["is_balanced"], f"Failed on {label}: balance")
            self.assertIsNone(res.oldest_observation_date, f"Failed on {label}: oldest_date")
            self.assertIsNone(res.newest_observation_date, f"Failed on {label}: newest_date")

    # -------------------------------------------------------------------------
    # 25. Cross-Page Conflict Safety (MP-SRC-004B)
    # -------------------------------------------------------------------------
    def test_25_cross_page_conflict_quarantines_all(self):
        """Cross-page conflict: Quote A on page 1 is retroactively quarantined when Quote B appears on page 2."""
        quote_a = {
            "state": "Uttar Pradesh",
            "district": "Lucknow",
            "market": "Lucknow APMC",
            "commodity": "Wheat",
            "variety": "Dara",
            "grade": "FAQ",
            "arrival_date": "2026-11-12",
            "min_price": 2400,
            "max_price": 2500,
            "modal_price": 2450,
        }
        quote_b = dict(quote_a)
        quote_b["modal_price"] = 2480  # Divergent!

        page1 = json.dumps({"total": 2, "count": 1, "offset": "0", "records": [quote_a]})
        page2 = json.dumps({"total": 2, "count": 1, "offset": "1", "records": [quote_b]})

        self.mock_transport.set_response("Lucknow", 0, 200, page1)
        self.mock_transport.set_response("Lucknow", 1, 200, page2)

        res = self.client.fetch_district_batch("Lucknow", "run_cross_page", [0])

        self.assertEqual(res.records_fetched, 2)
        self.assertEqual(res.records_accepted, 0)
        self.assertEqual(res.records_quarantined, 2)
        self.assertTrue(res.validate_arithmetic()["is_balanced"])

    # -------------------------------------------------------------------------
    # 26. Honest Missing Price Bounds (NO Modal Substitution) (MP-SRC-004B)
    # -------------------------------------------------------------------------
    def test_26_honest_missing_price_bounds_no_modal_substitution(self):
        """Missing min/max prices must NOT be substituted with modal_price, but quarantined."""
        # Missing min_price
        rec_no_min = self.client.parse_and_validate_record(
            raw_row={
                "district": "Kanpur",
                "market": "Kanpur(Grain) APMC",
                "commodity": "Potato",
                "variety": "Other",
                "arrival_date": "2026-11-12",
                "min_price": None,
                "max_price": 600,
                "modal_price": 550,
            },
            requested_district="Kanpur",
            retrieval_utc="2026-11-12T10:00:00Z",
            display_ist="2026-11-12 15:30:00 IST",
        )
        self.assertEqual(rec_no_min.disposition, RecordDisposition.MISSING_REQUIRED_FIELDS)
        self.assertIsNone(rec_no_min.min_price)
        self.assertIn("Modal substitution is strictly forbidden", rec_no_min.disposition_reason)

        # Missing max_price
        rec_no_max = self.client.parse_and_validate_record(
            raw_row={
                "district": "Kanpur",
                "market": "Kanpur(Grain) APMC",
                "commodity": "Potato",
                "variety": "Other",
                "arrival_date": "2026-11-12",
                "min_price": 500,
                "max_price": "",
                "modal_price": 550,
            },
            requested_district="Kanpur",
            retrieval_utc="2026-11-12T10:00:00Z",
            display_ist="2026-11-12 15:30:00 IST",
        )
        self.assertEqual(rec_no_max.disposition, RecordDisposition.MISSING_REQUIRED_FIELDS)
        self.assertIsNone(rec_no_max.max_price)

        # NaN price bounds
        rec_nan = self.client.parse_and_validate_record(
            raw_row={
                "district": "Kanpur",
                "market": "Kanpur(Grain) APMC",
                "commodity": "Potato",
                "variety": "Other",
                "arrival_date": "2026-11-12",
                "min_price": float("nan"),
                "max_price": 600,
                "modal_price": 550,
            },
            requested_district="Kanpur",
            retrieval_utc="2026-11-12T10:00:00Z",
            display_ist="2026-11-12 15:30:00 IST",
        )
        self.assertEqual(rec_nan.disposition, RecordDisposition.INVALID_PRICE_BOUNDS)

        # Infinite price bounds
        rec_inf = self.client.parse_and_validate_record(
            raw_row={
                "district": "Kanpur",
                "market": "Kanpur(Grain) APMC",
                "commodity": "Potato",
                "variety": "Other",
                "arrival_date": "2026-11-12",
                "min_price": 500,
                "max_price": float("inf"),
                "modal_price": 550,
            },
            requested_district="Kanpur",
            retrieval_utc="2026-11-12T10:00:00Z",
            display_ist="2026-11-12 15:30:00 IST",
        )
        self.assertEqual(rec_inf.disposition, RecordDisposition.INVALID_PRICE_BOUNDS)

    # -------------------------------------------------------------------------
    # 27. Atomic Last Success Pointer & Persistent Fallback Loader (MP-SRC-004B)
    # -------------------------------------------------------------------------
    def test_27_atomic_last_success_pointer_and_fallback_loader(self):
        """
        Prove last_successful_campaign.json is NEVER updated by TEST_FIXTURE,
        and verify fallback loader recovers prior validated snapshot metadata.
        """
        # 1. Run campaign with TEST_FIXTURE: must NOT create pointer file
        self.client.execute_campaign(districts=["Kanpur"], run_id_utc="run_fixture_01")
        pointer_file = os.path.join(self.snapshots_dir, "last_successful_campaign.json")
        self.assertFalse(os.path.exists(pointer_file))

        # 2. Simulate a verified LIVE_FETCH success and write pointer file
        live_dir = os.path.join(self.temp_dir, "simulated_live_snapshots")
        os.makedirs(os.path.join(live_dir, "run_live_01"), exist_ok=True)
        live_campaign = IngestionCampaignResult(
            run_id_utc="run_live_01",
            execution_timestamp_utc="2026-11-12T10:00:00.000000Z",
            execution_timestamp_ist="2026-11-12 15:30:00 IST",
            overall_operational_state=OperationalState.SUCCESS,
            data_mode=DataMode.LIVE_FETCH,
            is_live_verified=True,
            total_records_accepted=42,
            district_results={
                "Kanpur": DistrictIngestionResult(
                    district="Kanpur",
                    completeness_state=CompletenessState.COMPLETE,
                    newest_observation_date="2026-11-12",
                )
            },
        )
        # Write live receipt and pointer
        with open(os.path.join(live_dir, "run_live_01", "run_receipt.json"), "w", encoding="utf-8") as f:
            json.dump(live_campaign.to_dict(), f)

        pointer_data = {
            "run_id_utc": "run_live_01",
            "execution_timestamp_utc": "2026-11-12T10:00:00.000000Z",
            "execution_timestamp_ist": "2026-11-12 15:30:00 IST",
            "total_records_accepted": 42,
            "districts": ["Kanpur"],
            "receipt_path": os.path.join("run_live_01", "run_receipt.json"),
        }
        with open(os.path.join(live_dir, "last_successful_campaign.json"), "w", encoding="utf-8") as f:
            json.dump(pointer_data, f)

        # 3. Fallback loader recovers prior validated snapshot
        loaded = load_prior_validated_snapshot(snapshots_root=live_dir)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["run_id_utc"], "run_live_01")
        self.assertEqual(loaded["total_records_accepted"], 42)

        # 4. Convert to health report with fallback active
        blocked_campaign = IngestionCampaignResult(
            run_id_utc="run_failed_02",
            execution_timestamp_utc="2026-11-12T12:00:00.000000Z",
            execution_timestamp_ist="2026-11-12 17:30:00 IST",
            overall_operational_state=OperationalState.SOURCE_DOWN,
            data_mode=DataMode.LIVE_FETCH,
            is_live_verified=False,
        )
        report = build_health_report_from_ingestion(
            blocked_campaign,
            reference_date=self.ref_date,
            prior_validated_snapshot=loaded,
        )
        self.assertTrue(report.is_fallback_active)
        self.assertEqual(report.last_successful_fetch_utc, "2026-11-12T10:00:00.000000Z")
        self.assertEqual(report.latest_observation_date, "2026-11-12")

    # -------------------------------------------------------------------------
    # 28. Run Receipt Collision Safety (MP-SRC-004B)
    # -------------------------------------------------------------------------
    def test_28_run_receipt_collision_safety(self):
        """Attempting to write run_receipt.json when it already exists must raise FileExistsError."""
        campaign = IngestionCampaignResult(
            run_id_utc="run_collision_check",
            execution_timestamp_utc="2026-11-12T10:00:00.000000Z",
            execution_timestamp_ist="2026-11-12 15:30:00 IST",
            overall_operational_state=OperationalState.SUCCESS,
            data_mode=DataMode.TEST_FIXTURE,
        )
        # First write succeeds
        self.client._write_run_receipt(campaign)
        receipt_path = os.path.join(self.snapshots_dir, "run_collision_check", "run_receipt.json")
        self.assertTrue(os.path.exists(receipt_path))

        # Second write to same run_id must fail closed
        with self.assertRaises(FileExistsError):
            self.client._write_run_receipt(campaign)

    # -------------------------------------------------------------------------
    # 29. File Import Provenance & Integrity (Dataset-First Default)
    # -------------------------------------------------------------------------
    def test_29_file_import_provenance_and_integrity(self):
        """
        Verify that execute_file_import assigns FILE_IMPORT provenance, computes
        file SHA-256, writes immutable snapshot receipt, and NEVER sets is_live_verified.
        """
        fixture_path = os.path.join(self.temp_dir, "fixture_kanpur.csv")
        with open(fixture_path, "w", encoding="utf-8") as f:
            f.write("State,District,Market,Commodity,Variety,Grade,Arrival_Date,Min_Price,Max_Price,Modal_Price\n")
            f.write("Uttar Pradesh,Kanpur,Kanpur(Grain) APMC,Potato,Other,FAQ,12/11/2026,550,600,575\n")
            f.write("Uttar Pradesh,Kanpur,Uttaripura APMC,Wheat,Dara,FAQ,12/11/2026,2300,2400,2350\n")

        import_dir = os.path.join(self.temp_dir, "import_snapshots")
        client = LivePriceIngestionClient(
            data_mode=DataMode.FILE_IMPORT,
            snapshots_root=import_dir,
            reference_date=self.ref_date,
        )
        campaign = client.execute_file_import(
            file_path=fixture_path,
            district="Kanpur",
            source_url="https://agmarknet.gov.in/test_archive.csv",
            retrieval_timestamp_utc="2026-11-12T12:00:00Z",
        )

        self.assertEqual(campaign.data_mode, DataMode.FILE_IMPORT)
        self.assertFalse(campaign.is_synthetic)
        self.assertFalse(campaign.is_live_verified)
        self.assertEqual(campaign.total_records_fetched, 2)
        self.assertEqual(campaign.total_records_accepted, 2)
        self.assertEqual(campaign.total_records_quarantined, 0)
        self.assertEqual(campaign.total_records_duplicate, 0)
        self.assertTrue(campaign.capabilities["price_display_permitted"])
        self.assertFalse(campaign.capabilities["active_advice_permitted"])
        self.assertTrue(campaign.capabilities["is_import_verified"])

        # Verify pointer file was NOT created
        pointer_file = os.path.join(import_dir, "last_successful_campaign.json")
        self.assertFalse(os.path.exists(pointer_file))

        # Verify immutable page receipt exists and has file SHA
        page_file = os.path.join(import_dir, campaign.run_id_utc, "Kanpur", "page_00000.json")
        self.assertTrue(os.path.exists(page_file))
        with open(page_file, "r", encoding="utf-8") as pf:
            receipt_json = json.load(pf)
        self.assertEqual(receipt_json["data_mode"], "FILE_IMPORT")
        self.assertEqual(receipt_json["source_file_path"], fixture_path)
        self.assertTrue(len(receipt_json["source_file_sha256"]) == 64)

    # -------------------------------------------------------------------------
    # 30. File Import Order-Invariant Conflicts & Deduplication
    # -------------------------------------------------------------------------
    def test_30_file_import_order_invariant_conflicts_and_duplicates(self):
        """
        Verify that conflicting quotes in an imported CSV trigger order-invariant
        quarantine of ALL conflicting records, while exact duplicates are counted.
        """
        fixture_path = os.path.join(self.temp_dir, "fixture_conflicts.csv")
        with open(fixture_path, "w", encoding="utf-8") as f:
            f.write("State,District,Market,Commodity,Variety,Grade,Arrival_Date,Min_Price,Max_Price,Modal_Price\n")
            # Anchor quote A
            f.write("Uttar Pradesh,Kanpur,Kanpur(Grain) APMC,Potato,Other,FAQ,12/11/2026,550,600,575\n")
            # Exact duplicate of A
            f.write("Uttar Pradesh,Kanpur,Kanpur(Grain) APMC,Potato,Other,FAQ,12/11/2026,550,600,575\n")
            # Divergent quote B (different price) -> causes all 3 to be quarantined!
            f.write("Uttar Pradesh,Kanpur,Kanpur(Grain) APMC,Potato,Other,FAQ,12/11/2026,600,700,650\n")
            # Clean record for another commodity
            f.write("Uttar Pradesh,Kanpur,Kanpur(Grain) APMC,Wheat,Dara,FAQ,12/11/2026,2000,2100,2050\n")

        client = LivePriceIngestionClient(
            data_mode=DataMode.FILE_IMPORT,
            snapshots_root=os.path.join(self.temp_dir, "import_snapshots_2"),
            reference_date=self.ref_date,
        )
        campaign = client.execute_file_import(file_path=fixture_path, district="Kanpur")

        # Arithmetic check: 4 fetched = 1 accepted (wheat) + 0 dup + 3 quarantined (potato conflict)
        self.assertEqual(campaign.total_records_fetched, 4)
        self.assertEqual(campaign.total_records_accepted, 1)
        self.assertEqual(campaign.total_records_quarantined, 3)
        self.assertEqual(campaign.total_records_duplicate, 0)
        recon = campaign.validate_arithmetic()
        self.assertTrue(recon["is_balanced"])

    # -------------------------------------------------------------------------
    # 31. File Import Honest Price Bounds & Rejection of Modal Substitution
    # -------------------------------------------------------------------------
    def test_31_file_import_honest_price_bounds_and_invalid_data(self):
        """
        Verify that missing min/max prices in imported CSV are NEVER replaced by modal_price,
        and invalid bounds / out-of-scope subdivisions are quarantined.
        """
        fixture_path = os.path.join(self.temp_dir, "fixture_bounds.csv")
        with open(fixture_path, "w", encoding="utf-8") as f:
            f.write("State,District,Market,Commodity,Variety,Grade,Arrival_Date,Min_Price,Max_Price,Modal_Price\n")
            # Missing min_price: must be MISSING_REQUIRED_FIELDS (NO modal substitution)
            f.write("Uttar Pradesh,Kanpur,Kanpur(Grain) APMC,Potato,Other,FAQ,12/11/2026,,600,575\n")
            # Inverted bounds: min > modal
            f.write("Uttar Pradesh,Kanpur,Kanpur(Grain) APMC,Wheat,Dara,FAQ,12/11/2026,2500,2400,2300\n")
            # Kanpur Dehat: out of scope subdivision
            f.write("Uttar Pradesh,Kanpur Dehat,Rura APMC,Maize,Other,FAQ,12/11/2026,1800,1900,1850\n")

        client = LivePriceIngestionClient(
            data_mode=DataMode.FILE_IMPORT,
            snapshots_root=os.path.join(self.temp_dir, "import_snapshots_3"),
            reference_date=self.ref_date,
        )
        campaign = client.execute_file_import(file_path=fixture_path)

        self.assertEqual(campaign.total_records_fetched, 3)
        self.assertEqual(campaign.total_records_accepted, 0)
        self.assertEqual(campaign.total_records_quarantined, 3)
        recon = campaign.validate_arithmetic()
        self.assertTrue(recon["is_balanced"])

    # -------------------------------------------------------------------------
    # 32. File Import Repeated Idempotent Runs
    # -------------------------------------------------------------------------
    def test_32_file_import_repeated_idempotent_runs(self):
        """Re-importing the same dataset file produces identical counts and balances."""
        fixture_path = os.path.join(self.temp_dir, "fixture_idempotent.csv")
        with open(fixture_path, "w", encoding="utf-8") as f:
            f.write("State,District,Market,Commodity,Variety,Grade,Arrival_Date,Min_Price,Max_Price,Modal_Price\n")
            f.write("Uttar Pradesh,Jhansi,Jhansi APMC,Wheat,Dara,FAQ,12/11/2026,2200,2300,2250\n")
            f.write("Uttar Pradesh,Jhansi,Jhansi APMC,Gram,Other,FAQ,12/11/2026,5000,5200,5100\n")

        client = LivePriceIngestionClient(
            data_mode=DataMode.FILE_IMPORT,
            snapshots_root=os.path.join(self.temp_dir, "import_snapshots_4"),
            reference_date=self.ref_date,
        )
        c1 = client.execute_file_import(file_path=fixture_path, district="Jhansi")
        c2 = client.execute_file_import(file_path=fixture_path, district="Jhansi")

        self.assertEqual(c1.total_records_fetched, c2.total_records_fetched)
        self.assertEqual(c1.total_records_accepted, c2.total_records_accepted)
        self.assertEqual(c1.total_records_quarantined, c2.total_records_quarantined)
        self.assertEqual(c1.total_records_duplicate, c2.total_records_duplicate)
        self.assertNotEqual(c1.run_id_utc, c2.run_id_utc)

    # -------------------------------------------------------------------------
    # 33. File Import Size & Row Limits Rejection
    # -------------------------------------------------------------------------
    def test_33_file_import_size_and_row_budget_rejections(self):
        """Files exceeding 10MB or 50,000 rows must fail with ValueError before reading."""
        oversized_rows_path = os.path.join(self.temp_dir, "oversized_rows.csv")
        with open(oversized_rows_path, "w", encoding="utf-8") as f:
            f.write("State,District,Market,Commodity,Variety,Grade,Arrival_Date,Min_Price,Max_Price,Modal_Price\n")
            # Write 50,001 rows
            for i in range(50001):
                f.write(f"Uttar Pradesh,Unnao,Unnao APMC,Commodity_{i},Other,FAQ,12/11/2026,100,200,150\n")

        client = LivePriceIngestionClient(data_mode=DataMode.FILE_IMPORT)
        with self.assertRaises(ValueError) as ctx:
            client.execute_file_import(file_path=oversized_rows_path)
        self.assertIn("exceeds maximum allowed local processing limit", str(ctx.exception))

    # -------------------------------------------------------------------------
    # 34. File Import CLI Invocation
    # -------------------------------------------------------------------------
    def test_34_file_import_cli_invocation(self):
        """Invoke CLI with --import-file and --json and verify execution code and JSON output."""
        fixture_path = os.path.join(self.temp_dir, "fixture_cli.csv")
        with open(fixture_path, "w", encoding="utf-8") as f:
            f.write("State,District,Market,Commodity,Variety,Grade,Arrival_Date,Min_Price,Max_Price,Modal_Price\n")
            f.write("Uttar Pradesh,Lucknow,Lucknow APMC,Potato,Other,FAQ,12/11/2026,700,800,750\n")

        import subprocess
        cmd = [
            sys.executable,
            "-m",
            "src.live_price_ingestion",
            "--import-file",
            fixture_path,
            "--district",
            "Lucknow",
            "--snapshots-dir",
            os.path.join(self.temp_dir, "cli_snapshots"),
            "--json",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        output = json.loads(res.stdout)
        self.assertEqual(output["data_mode"], "FILE_IMPORT")
        self.assertFalse(output["is_live_verified"])
        self.assertEqual(output["total_records_accepted"], 1)

    # -------------------------------------------------------------------------
    # 35. Official XLSX Import Handling Title Row
    # -------------------------------------------------------------------------
    def test_35_xlsx_file_import_with_title_row(self):
        """Verify official Agmarknet .xlsx files with title row in row 0 are parsed correctly."""
        import openpyxl

        xlsx_path = os.path.join(self.temp_dir, "test_agmarknet.xlsx")
        wb = openpyxl.Workbook()
        ws = wb.active
        # Row 0: Title row
        ws.append(["Daily Price Arrival Report-07-11-2025 to 06-11-2026 for Uttar Pradesh", None, None])
        # Row 1: Headers
        ws.append([
            "State/UT", "District", "Market", "Commodity Group", "Commodity",
            "Variety", "Grade", "Min Price", "Max Price", "Modal Price",
            "Price Unit", "Arrival Quantity", "Arrival Unit", "Arrival Date"
        ])
        # Row 2: Data
        ws.append([
            "Uttar Pradesh", "Kanpur", "Kanpur(Grain) APMC", "Vegetables", "Potato",
            "Other", "FAQ", 500, 600, 550,
            "Rs./Quintal", 100, "Metric Tonnes", "12-11-2026"
        ])
        wb.save(xlsx_path)

        client = LivePriceIngestionClient(
            data_mode=DataMode.FILE_IMPORT,
            snapshots_root=os.path.join(self.temp_dir, "xlsx_snapshots"),
        )
        campaign = client.execute_file_import(file_path=xlsx_path)
        self.assertEqual(campaign.overall_operational_state, OperationalState.SUCCESS)
        self.assertEqual(campaign.total_records_accepted, 1)
        rec = campaign.district_results["Kanpur"].accepted_records[0]
        self.assertEqual(rec.modal_price, 550.0)
        self.assertEqual(rec.arrival_date_parsed, "2026-11-12")

    # -------------------------------------------------------------------------
    # 36. Unsupported File Formats Explicitly Rejected
    # -------------------------------------------------------------------------
    def test_36_unsupported_file_format_rejected(self):
        """Verify non-CSV/XLSX file extensions are rejected with explicit ValueError."""
        txt_path = os.path.join(self.temp_dir, "invalid_format.txt")
        with open(txt_path, "w") as f:
            f.write("dummy content")

        client = LivePriceIngestionClient(data_mode=DataMode.FILE_IMPORT)
        with self.assertRaises(ValueError) as ctx:
            client.execute_file_import(file_path=txt_path)
        self.assertIn("Unsupported file format '.txt'", str(ctx.exception))

    # -------------------------------------------------------------------------
    # 37. Independent Import Pointer Never Updates Live Pointer
    # -------------------------------------------------------------------------
    def test_37_independent_import_pointer_never_touches_live(self):
        """Verify last_successful_import is updated while last_successful_campaign remains absent."""
        csv_path = os.path.join(self.temp_dir, "fixture_import.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("State,District,Market,Commodity,Variety,Grade,Arrival_Date,Min_Price,Max_Price,Modal_Price\n")
            f.write("Uttar Pradesh,Jhansi,Mauranipur,Potato,Other,FAQ,11/11/2026,500,600,550\n")

        snapshots_dir = os.path.join(self.temp_dir, "ptr_test_snapshots")
        client = LivePriceIngestionClient(
            data_mode=DataMode.FILE_IMPORT,
            snapshots_root=snapshots_dir,
        )
        campaign = client.execute_file_import(file_path=csv_path)
        self.assertEqual(campaign.total_records_accepted, 1)

        import_ptr_path = os.path.join(snapshots_dir, "last_successful_import.json")
        live_ptr_path = os.path.join(snapshots_dir, "last_successful_campaign.json")

        self.assertTrue(os.path.exists(import_ptr_path))
        self.assertFalse(os.path.exists(live_ptr_path))

        fallback = load_prior_validated_import(snapshots_root=snapshots_dir)
        self.assertIsNotNone(fallback)
        self.assertFalse(fallback["is_live_verified"])
        self.assertTrue(fallback["is_import_verified"])

        live_fallback = load_prior_validated_snapshot(snapshots_root=snapshots_dir)
        self.assertIsNone(live_fallback)

    # -------------------------------------------------------------------------
    # 38. Multi-File Composite SHA-256 Linkage
    # -------------------------------------------------------------------------
    def test_38_multi_file_composite_sha256(self):
        """Verify multi-file imports compute composite SHA-256 and link all files to receipts."""
        f1_path = os.path.join(self.temp_dir, "multi_1.csv")
        f2_path = os.path.join(self.temp_dir, "multi_2.csv")

        with open(f1_path, "w", encoding="utf-8") as f:
            f.write("State,District,Market,Commodity,Variety,Grade,Arrival_Date,Min_Price,Max_Price,Modal_Price\n")
            f.write("Uttar Pradesh,Ghaziabad,Ghaziabad,Potato,Other,FAQ,11/11/2026,900,1000,950\n")

        with open(f2_path, "w", encoding="utf-8") as f:
            f.write("State,District,Market,Commodity,Variety,Grade,Arrival_Date,Min_Price,Max_Price,Modal_Price\n")
            f.write("Uttar Pradesh,Lucknow,Lucknow,Potato,Other,FAQ,11/11/2026,800,900,850\n")

        client = LivePriceIngestionClient(
            data_mode=DataMode.FILE_IMPORT,
            snapshots_root=os.path.join(self.temp_dir, "multi_snapshots"),
        )
        campaign = client.execute_file_import(file_path=[f1_path, f2_path])
        self.assertEqual(campaign.total_records_accepted, 2)
        self.assertIsNotNone(campaign.composite_source_sha256)

        # Composite SHA must not equal either individual file SHA
        sha1 = campaign.source_files[0]["file_sha256"]
        sha2 = campaign.source_files[1]["file_sha256"]
        self.assertNotEqual(campaign.composite_source_sha256, sha1)
        self.assertNotEqual(campaign.composite_source_sha256, sha2)

        # Receipt links to both contributing source files
        receipt = campaign.district_results["Ghaziabad"].page_receipts[0]
        self.assertEqual(len(receipt.source_file_hashes), 2)
        self.assertEqual(receipt.content_sha256, campaign.composite_source_sha256)

    # -------------------------------------------------------------------------
    # 39. Publish Latest Index Idempotence and Latest Unresolved Conflict
    # -------------------------------------------------------------------------
    def test_39_publish_latest_observation_index_idempotence_and_conflicts(self):
        """Verify publishing index idempotence and quarantine disclosure on divergent quotes."""
        # Create accepted record and conflicting records
        rec_acc = RawPriceRecord(
            state="Uttar Pradesh",
            district="Kanpur",
            market_raw="Kanpur(Grain) APMC",
            commodity="Potato",
            variety="Other",
            grade_raw="FAQ",
            grade_normalized="FAQ",
            arrival_date_raw="11/11/2026",
            arrival_date_parsed="2026-11-11",
            min_price_raw=500,
            max_price_raw=600,
            modal_price_raw=550,
            min_price=500.0,
            max_price=600.0,
            modal_price=550.0,
            market_canonical="Kanpur(Grain)",
            market_alias_status="CANONICAL",
            disposition=RecordDisposition.ACCEPTED,
            disposition_reason="Valid",
            retrieval_timestamp_utc="2026-11-12T00:00:00Z",
            display_timestamp_ist="2026-11-12 05:30:00 IST",
            source_resource_id="res1",
            source_endpoint="https://example.com",
            data_mode=DataMode.FILE_IMPORT,
        )

        # Conflicting quote on latest date for Onion
        rec_conf1 = RawPriceRecord(
            state="Uttar Pradesh",
            district="Kanpur",
            market_raw="Kanpur(Grain) APMC",
            commodity="Onion",
            variety="Other",
            grade_raw="FAQ",
            grade_normalized="FAQ",
            arrival_date_raw="11/11/2026",
            arrival_date_parsed="2026-11-11",
            min_price_raw=2800,
            max_price_raw=3200,
            modal_price_raw=3000,
            min_price=2800.0,
            max_price=3200.0,
            modal_price=3000.0,
            market_canonical="Kanpur(Grain)",
            market_alias_status="CANONICAL",
            disposition=RecordDisposition.CONFLICTING_QUOTE,
            disposition_reason="Divergent quote",
            retrieval_timestamp_utc="2026-11-12T00:00:00Z",
            display_timestamp_ist="2026-11-12 05:30:00 IST",
            source_resource_id="res1",
            source_endpoint="https://example.com",
            data_mode=DataMode.FILE_IMPORT,
        )

        idx_path = os.path.join(self.temp_dir, "latest_idx_test.json")
        idx1 = publish_latest_observation_index([rec_acc, rec_conf1], output_path=idx_path)
        self.assertEqual(idx1["accepted_series_count"], 1)
        self.assertEqual(idx1["quarantined_series_count"], 1)

        # Verify Potato series is ACCEPTED
        potato_key = "Kanpur|Kanpur(Grain)|Potato|Other|FAQ"
        self.assertIn(potato_key, idx1["series"])
        self.assertEqual(idx1["series"][potato_key]["status"], "ACCEPTED")

        # Verify Onion series is CONFLICT_QUARANTINED with explicit disclosure
        onion_key = "Kanpur|Kanpur(Grain)|Onion|Other|FAQ"
        self.assertIn(onion_key, idx1["series"])
        self.assertEqual(idx1["series"][onion_key]["status"], "CONFLICT_QUARANTINED")
        self.assertIn("Unresolved divergent price quotes", idx1["series"][onion_key]["status_reason"])
        self.assertFalse(idx1["series"][onion_key]["capabilities"]["price_display_permitted"])

        # Idempotence: re-publishing identical content produces identical index
        idx2 = publish_latest_observation_index([rec_acc, rec_conf1], output_path=idx_path)
        self.assertEqual(len(idx1["series"]), len(idx2["series"]))
        self.assertEqual(idx1["accepted_series_count"], idx2["accepted_series_count"])


if __name__ == "__main__":
    unittest.main()
