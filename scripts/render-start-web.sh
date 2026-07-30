#!/usr/bin/env bash
set -o errexit
cd "$(dirname "$0")/../apps/web"
# Normalize API targets from Render host-only values
if [[ -n "${API_PROXY_TARGET:-}" && "${API_PROXY_TARGET}" != http* ]]; then
  export API_PROXY_TARGET="https://${API_PROXY_TARGET}"
fi
if [[ -n "${API_INTERNAL_BASE:-}" && "${API_INTERNAL_BASE}" != http* ]]; then
  export API_INTERNAL_BASE="https://${API_INTERNAL_BASE}"
fi
exec npx next start --hostname 0.0.0.0 --port "${PORT:-3000}"
