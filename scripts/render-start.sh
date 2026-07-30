#!/usr/bin/env bash
set -o errexit
# imprint-api only. Public pages: deploy imprint-web (scripts/render-start-web.sh).
echo "Starting imprint-api (FastAPI). Health: /health  Site HTML: imprint-web service."
exec gunicorn server.main:app -k uvicorn.workers.UvicornWorker --bind "0.0.0.0:${PORT:-8080}"
