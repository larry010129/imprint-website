#!/usr/bin/env bash
set -o errexit
# Sole public origin: FastAPI + Jinja SSR (HTML, /api, /static).
echo "Starting imprint-api (FastAPI + Jinja). Health: /health  Site: /"
exec gunicorn server.main:app -k uvicorn.workers.UvicornWorker --bind "0.0.0.0:${PORT:-8080}"
