#!/usr/bin/env bash
set -o errexit
exec gunicorn server.main:app -k uvicorn.workers.UvicornWorker --bind "0.0.0.0:${PORT:-8080}"
