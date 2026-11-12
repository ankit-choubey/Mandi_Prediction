# syntax=docker/dockerfile:1
# APMC Mandi Intelligence System - Release Candidate Containerfile (MP-RELEASE-001)
# Base: Python 3.11/3.14 Standard Library Runtime

FROM python:3.11-slim-bullseye AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    APMC_HOST=0.0.0.0 \
    APMC_PORT=8000

WORKDIR /app

# Create unprivileged service user
RUN groupadd -g 10001 apmc && \
    useradd -u 10001 -g apmc -s /bin/bash -m apmc

# Copy required application modules and reference artifacts
COPY src/ /app/src/
COPY data/reference/ /app/data/reference/
COPY data/imported_snapshots/ /app/data/imported_snapshots/

# Set permissions for read-only runtime security
RUN chown -R apmc:apmc /app && \
    chmod -R 550 /app && \
    chmod -R 440 /app/data/reference/* /app/data/imported_snapshots/*

USER apmc:apmc

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python3 -c "import urllib.request; res = urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health'); sys.exit(0 if res.status == 200 else 1)"

ENTRYPOINT ["python3", "/app/src/run_release_service.py"]
CMD ["--host", "0.0.0.0", "--port", "8000"]
