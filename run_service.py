#!/usr/bin/env python3
"""
APMC Mandi Intelligence System - Development Server Launcher
Task: MP-APP-001A (Step 10 Backend Architecture)

NOTICE: DEVELOPMENT-ONLY SERVER
This server is intended exclusively for local development, inspection, and verification.
It binds strictly to loopback (127.0.0.1) and must NOT be deployed as an unauthenticated
public service or exposed on external network interfaces.
"""

from __future__ import annotations

import argparse
import sys
from wsgiref.simple_server import make_server

from src.api import create_app
from src.service import MandiMarketService


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Launch APMC Mandi Intelligence Development Server (Loopback Only)."
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host address to bind to (Default: 127.0.0.1 - loopback only).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to listen on (Default: 8000).",
    )
    args = parser.parse_args()

    # Safety constraint: enforce loopback binding only
    if args.host not in ("127.0.0.1", "localhost"):
        print(
            f"ERROR: Refusing to bind to non-loopback host '{args.host}'. "
            "This development server must only bind to 127.0.0.1 or localhost.",
            file=sys.stderr,
        )
        sys.exit(1)

    service = MandiMarketService()
    app = create_app(service)

    print("==================================================================")
    print(" APMC Mandi Intelligence System — Step 10 Backend API")
    print(" STATUS: DEVELOPMENT-ONLY (Loopback Serving)")
    print(f" URL:    http://{args.host}:{args.port}")
    print("==================================================================")
    print("Available Endpoints:")
    print("  GET  /api/v1/health")
    print("  GET  /api/v1/catalog")
    print("  GET  /api/v1/prices/latest?commodity=Wheat&district=Lucknow")
    print("  GET  /api/v1/prices/history")
    print("  GET  /api/v1/models/benchmark")
    print("  POST /api/v1/forecast")
    print("  POST /api/v1/economics/evaluate")
    print("==================================================================")
    print("Press Ctrl+C to shut down.")

    try:
        with make_server(args.host, args.port, app) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer shut down cleanly.")


if __name__ == "__main__":
    main()
