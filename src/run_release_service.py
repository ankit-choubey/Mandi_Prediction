#!/usr/bin/env python3
"""
APMC Mandi Intelligence System - Research Release Service Runner
Task: MP-RELEASE-001 Integration & Release Candidate
Standard-library WSGI loopback server with graceful shutdown and structured logging.
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
import time
from wsgiref.simple_server import make_server, WSGIServer

from src.api import create_app
from src.service import MandiMarketService

RELEASE_VERSION = "1.0.0-rc1"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [APMC-RELEASE] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger("apmc.release")


def parse_args():
    parser = argparse.ArgumentParser(
        description="APMC Mandi Intelligence System - Research Release Runner (MP-RELEASE-001)"
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("APMC_HOST", DEFAULT_HOST),
        help=f"Host interface to bind (default: {DEFAULT_HOST}, loopback only)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("APMC_PORT", DEFAULT_PORT)),
        help=f"Port number to bind (default: {DEFAULT_PORT})",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Enforce loopback binding by default for security
    if args.host not in ("127.0.0.1", "localhost", "::1"):
        logger.warning(
            f"Binding to non-loopback interface '{args.host}'. "
            "Ensure host access controls are configured before exposure."
        )

    logger.info("==================================================================")
    logger.info(f" APMC Mandi Intelligence System - Research Release Candidate {RELEASE_VERSION}")
    logger.info(" Academic Retrospective Benchmark & Cost-Aware Economics Service")
    logger.info("==================================================================")

    # Initialize service and inspect health
    service = MandiMarketService()
    health = service.get_health()

    logger.info(f"Process Status: {health.process_status}")
    logger.info(f"Server Date (IST): {health.server_time_ist}")
    for cap_name, cap in health.capabilities.items():
        logger.info(f"Capability [{cap_name}]: status={cap.status}, available={cap.available}")

    logger.info(
        "Advisory Gating Policy: FAIL_CLOSED (Advisory action strictly BLOCKED; "
        "commercial farmer advice requires prospective validation under Steps 12-13)."
    )

    app = create_app(service)

    server: WSGIServer = make_server(args.host, args.port, app)
    logger.info(f"Service listening on http://{args.host}:{args.port}/")
    logger.info("Press Ctrl+C to stop.")

    def handle_shutdown(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        server.shutdown()
        logger.info("Service cleanly shut down.")
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
