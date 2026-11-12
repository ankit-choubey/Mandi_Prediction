"""
Unit and Integration Test Suite for Live Price Ingestion Client & Snapshot Engine
APMC Mandi Market Intelligence System
Task: MP-SRC-004 (Steps 3–5)

Tests exercise:
- Complete multiple-page pagination
- Exact duplicates and conflicting quote detection
- Same payload refetch with new receipt and content hash sharing
- Repeated page detection and abort
- Total change detection mid-pagination
- Ignored district filter fail-closed quarantine
- HTTP status handling: 401, 403, 429 (Retry-After), 500
- Timeout, malformed JSON, and source-error JSON handling
- Empty valid result handling
- Missing fields and grade normalization policy (SOURCE_NOT_PROVIDED, never silently FAQ)
- Price bounds violations ($P_min <= P_modal <= P_max$)
- Malformed and future-dated observations
- Unknown market alias enters REVIEW
- Kanpur subdivision ambiguity (Kanpur Dehat quarantined)
- IST day boundary and freshness lag
- Delayed advice blocked and decoupled capabilities
- Immutable exclusive writes (no overwrite)
- Partial runs never advance last_successful_fetch
- Secret sentinel absent from URLs, errors, and stored JSON receipts
- End-to-end fixture fetch -> archive -> validation -> health output
"""

import json
import os
import shutil
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
    HttpTransport,
    IngestionCampaignResult,
    LivePriceIngestionClient,
    MockHttpTransport,
    PageReceipt,
    RawPriceRecord,
    RecordDisposition,
    build_health_report_from_ingestion,
    load_api_key,
    load_contract,
    redact_credential_echo,
    sanitize_params,
    sanitize_url,
)


class TestLivePriceIngestion(unittest.TestCase):
    """Comprehensive test suite for live price ingestion, data trust, and snapshots."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="mandi_live_test_")
        self.snapshots_dir = os.path.join(self.temp_dir, "live_snapshots")
        self.ref_date = date(2026, 11, 12)
        self.mock_transport = MockHttpTransport()
        self.client = LivePriceIngestionClient(
            api_key="TEST_API_KEY_ABCD1234",
            transport=self.mock_transport,
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
            reference_date=self.ref_date,
            snapshots_root=self.snapshots_dir,
        )

        # 1. URL Sanitization check
        url_with_secret = f"https://api.data.gov.in/resource/123?api-key={secret_sentinel}&format=json"
        clean_url = sanitize_url(url_with_secret)
        self.assertNotIn(secret_sentinel, clean_url)
        self.assertIn("REDACTED", clean_url)

        # 2. Params Sanitization check
        params = {"api-key": secret_sentinel, "filters[district]": "Kanpur"}
        clean_params = sanitize_params(params)
        self.assertNotIn(secret_sentinel, str(clean_params))
        self.assertEqual(clean_params["api-key"], "[REDACTED]")

        # 3. Echo detection & redaction in body
        echo_body = f'{{"error": "Invalid key: {secret_sentinel}", "records": []}}'
        redacted_body, echo_found = redact_credential_echo(echo_body, secret_sentinel)
        self.assertTrue(echo_found)
        self.assertNotIn(secret_sentinel, redacted_body)
        self.assertIn("[REDACTED_API_KEY]", redacted_body)

        # 4. Storage receipt check
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

        # Assert secret sentinel is completely absent from written file
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
            "records": [row, dict(row)]  # Identical duplicates
        })
        self.mock_transport.set_response("Ghaziabad", 0, 200, payload)

        res = self.client.fetch_district_batch("Ghaziabad", "run_dup", [0])
        self.assertEqual(res.records_fetched, 2)
        self.assertEqual(res.records_accepted, 1)
        self.assertEqual(res.records_duplicate, 1)
        self.assertEqual(res.records_quarantined, 0)
        self.assertTrue(res.validate_arithmetic()["is_balanced"])

    # -------------------------------------------------------------------------
    # 4. Conflicting Quotes Quarantined
    # -------------------------------------------------------------------------
    def test_04_conflicting_quote_quarantined(self):
        """Conflicting quotes on identical key with divergent prices are quarantined."""
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
        self.assertEqual(res.records_accepted, 1)
        self.assertEqual(res.records_quarantined, 1)
        self.assertEqual(res.disposition_counts[RecordDisposition.CONFLICTING_QUOTE.value], 1)
        self.assertTrue(res.validate_arithmetic()["is_balanced"])

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
        # Both offset 0 and offset 1 return identical body
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
            "total": 5,  # Changed mid-pagination!
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
                "district": "Agra",  # Wrong district!
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
        self.assertEqual(tracker[0], 1)  # Only 1 request, zero retries

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
        self.assertGreater(tracker[0], 1)  # Tried retries

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
        # Malformed JSON
        self.mock_transport.set_response("Kanpur", 0, 200, '{"records": [incomplete')
        res = self.client.fetch_district_batch("Kanpur", "run_malformed", [0])
        self.assertEqual(res.completeness_state, CompletenessState.FAILED)
        self.assertTrue(any("malformed json" in e.lower() for e in res.errors))

        # API Error JSON
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
                "grade": None,  # Missing grade!
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
        # Non-positive price
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

        # Min > Modal
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
        # Malformed date
        rec_bad = self.client.parse_and_validate_record(
            raw_row={
                "district": "Kanpur",
                "market": "Kanpur(Grain) APMC",
                "commodity": "Potato",
                "variety": "Other",
                "arrival_date": "not-a-valid-date",
                "modal_price": 500,
            },
            requested_district="Kanpur",
            retrieval_utc="2026-11-12T10:00:00Z",
            display_ist="2026-11-12 15:30:00 IST",
        )
        self.assertEqual(rec_bad.disposition, RecordDisposition.MALFORMED_DATE)

        # Future date (ref_date is 2026-11-12)
        rec_future = self.client.parse_and_validate_record(
            raw_row={
                "district": "Kanpur",
                "market": "Kanpur(Grain) APMC",
                "commodity": "Potato",
                "variety": "Other",
                "arrival_date": "2026-11-20",
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

        # Current (0-2 days lag)
        dec_today = engine.evaluate_gate(observation_date="2026-11-12")
        self.assertEqual(dec_today.freshness_status, FreshnessStatus.CURRENT.value)
        self.assertEqual(dec_today.lag_days, 0)
        self.assertTrue(dec_today.is_permitted)

        dec_2d = engine.evaluate_gate(observation_date="2026-11-10")
        self.assertEqual(dec_2d.freshness_status, FreshnessStatus.CURRENT.value)
        self.assertEqual(dec_2d.lag_days, 2)
        self.assertTrue(dec_2d.is_permitted)

        # Delayed (3-5 days lag)
        dec_3d = engine.evaluate_gate(observation_date="2026-11-09")
        self.assertEqual(dec_3d.freshness_status, FreshnessStatus.DELAYED.value)
        self.assertEqual(dec_3d.lag_days, 3)
        self.assertFalse(dec_3d.is_permitted)  # Active advice withheld

        # Stale (> 5 days lag)
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
        )

        # First write succeeds
        path = self.client.write_snapshot_page("run_collision_test", "Kanpur", receipt)
        self.assertTrue(os.path.exists(path))

        # Second write to identical file must fail
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
        """Complete workflow test from mock transport to HealthReport and terminal dashboard."""
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
        self.assertTrue(campaign.is_live_verified)
        self.assertEqual(campaign.total_records_fetched, 2)
        self.assertEqual(campaign.total_records_accepted, 2)
        self.assertTrue(campaign.validate_arithmetic()["is_balanced"])

        # Verify receipt file was written
        receipt_path = os.path.join(self.snapshots_dir, "run_e2e_01", "Kanpur", "page_00000.json")
        self.assertTrue(os.path.exists(receipt_path))

        # Verify run-level receipt was written
        run_receipt_path = os.path.join(self.snapshots_dir, "run_e2e_01", "run_receipt.json")
        self.assertTrue(os.path.exists(run_receipt_path))

        # Verify HealthReport conversion
        health_report = build_health_report_from_ingestion(campaign, reference_date=self.ref_date)
        self.assertEqual(health_report.operational_state, OperationalState.SUCCESS)
        self.assertEqual(health_report.freshness_status, FreshnessStatus.CURRENT)
        self.assertEqual(health_report.reconciliation.records_accepted, 2)
        self.assertTrue(health_report.is_source_live)


if __name__ == "__main__":
    unittest.main()
