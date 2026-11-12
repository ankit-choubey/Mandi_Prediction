#!/usr/bin/env python3
"""
APMC Mandi Intelligence System - Research Release Service Runner
Task: MP-RELEASE-001R Integration & Release Lifecycle
Standard-library WSGI loopback server with non-deadlocking graceful shutdown and UTC logging.
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
import signal
import sys
import threading
import time
from wsgiref.simple_server import make_server, WSGIServer

# Dynamically resolve and prepend repository root to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.api import create_app
from src.service import MandiMarketService

RELEASE_VERSION = "1.0.0-rc1"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000

# Enforce true UTC timestamps in Python standard library logging
logging.Formatter.converter = time.gmtime
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [APMC-RELEASE] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger("apmc.release")


def parse_args(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        prog="python3 -m src.run_release_service",
        description="APMC Mandi Intelligence System - Research Release Runner (MP-RELEASE-001R)",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("APMC_HOST", DEFAULT_HOST),
        help=f"Host interface to bind (default: {DEFAULT_HOST}, loopback enforced)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("APMC_PORT", DEFAULT_PORT)),
        help=f"Port number to bind (default: {DEFAULT_PORT}, 0 for ephemeral)",
    )
    parser.add_argument(
        "--index-path",
        default=os.environ.get("APMC_LATEST_INDEX_PATH"),
        help="Optional path to price observation index snapshot JSON",
    )
    parser.add_argument(
        "--allow-container-host",
        action="store_true",
        default=os.environ.get("APMC_ALLOW_CONTAINER_HOST", "0") in ("1", "true", "TRUE"),
        help="Allow binding to 0.0.0.0 strictly for verified container network isolation",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None):
    args = parse_args(argv)

    # Enforce loopback binding policy
    allowed_loopback = ("127.0.0.1", "localhost", "::1")
    if args.host not in allowed_loopback:
        if args.allow_container_host and args.host == "0.0.0.0":
            logger.warning(
                "Binding to container interface 0.0.0.0 under container execution policy. "
                "Host port publication must remain mapped strictly to 127.0.0.1."
            )
        else:
            logger.error(
                f"Refusing to bind to non-loopback host '{args.host}'. "
                "Loopback binding (127.0.0.1) is enforced by release policy. "
                "Use --allow-container-host inside verified container environments."
            )
            sys.exit(1)

    logger.info("==================================================================")
    logger.info(f" APMC Mandi Intelligence System - Research Release Candidate {RELEASE_VERSION}")
    logger.info(" Academic Retrospective Benchmark & Cost-Aware Economics Service")
    logger.info("==================================================================")

    # Initialize service and inspect health
    service = MandiMarketService(latest_index_path=args.index_path)
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
    actual_port = server.server_port
    logger.info(f"Service listening on http://{args.host}:{actual_port}/")
    logger.info("Press Ctrl+C to stop.")

    shutdown_event = threading.Event()

    def handle_shutdown(signum, frame):
        sig_name = "SIGTERM" if signum == signal.SIGTERM else ("SIGINT" if signum == signal.SIGINT else str(signum))
        logger.info(f"Received signal {sig_name} ({signum}), initiating graceful shutdown...")
        # server.shutdown() must be initiated from a separate thread so serve_forever() unblocks on the main thread
        shutdown_event.set()
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
    finally:
        server.server_close()
        logger.info("Service cleanly shut down.")


if __name__ == "__main__":
    main()
