# syntax=docker/dockerfile:1
# APMC Mandi Intelligence System - Release Candidate Containerfile (MP-RELEASE-001R)
# Base: Python 3.11 Standard Library Runtime

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

# Create mount points and copy required application modules and reference artifacts
RUN mkdir -p /app/data/imported_snapshots /app/experiments/reports/FC007_VERIFIED /app/experiments/reports/FC008

COPY src/ /app/src/
COPY data/reference/ /app/data/reference/
COPY experiments/reports/FC007_VERIFIED/scorecard_overall.csv /app/experiments/reports/FC007_VERIFIED/scorecard_overall.csv
COPY experiments/reports/FC008/intervals_overall.csv /app/experiments/reports/FC008/intervals_overall.csv
COPY experiments/reports/FC008/intervals_by_fold.csv /app/experiments/reports/FC008/intervals_by_fold.csv
COPY experiments/reports/FC008/calibration_envelope_v1.json /app/experiments/reports/FC008/calibration_envelope_v1.json

# Set permissions for read-only runtime security
RUN chown -R apmc:apmc /app && \
    chmod -R 550 /app && \
    chmod -R 440 /app/data/reference/* /app/experiments/reports/FC007_VERIFIED/* /app/experiments/reports/FC008/*

USER apmc:apmc

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python3 -c "import urllib.request, sys; sys.exit(0 if getattr(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=3), 'status', None) == 200 else 1)"

ENTRYPOINT ["python3", "-m", "src.run_release_service"]
CMD ["--host", "0.0.0.0", "--port", "8000", "--allow-container-host"]
