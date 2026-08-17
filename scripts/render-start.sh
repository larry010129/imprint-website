#!/usr/bin/env bash
set -o errexit
# Sole public origin: FastAPI + Jinja SSR (HTML, /api, /static).
echo "Starting imprint-api (FastAPI + Jinja). Health: /health  Site: /"
# --timeout 120: default 30s SIGABRTs UvicornWorker if Allbeauty scrape
# (or other sync work) blocks the event loop and gunicorn gets no heartbeat.
exec gunicorn server.main:app -k uvicorn.workers.UvicornWorker \
  --bind "0.0.0.0:${PORT:-8080}" \
  --timeout 120
