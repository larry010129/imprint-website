#!/usr/bin/env bash
set -o errexit
cd "$(dirname "$0")/.."
# Vite islands → public/static/react (still loaded by Next SiteShell)
if command -v node >/dev/null 2>&1; then
  npm ci --prefix frontend
  npm run build --prefix frontend
fi
npm ci --prefix apps/web
# Ensure page registry + bodies exist for SSR fallback
if [[ ! -f content/site/page-registry.json ]]; then
  echo "Missing content/site/page-registry.json — run python scripts/export_site_content.py before deploy"
  exit 1
fi
npm run build --prefix apps/web
