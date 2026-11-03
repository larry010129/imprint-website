#!/usr/bin/env bash
set -o errexit
pip install -r requirements.txt

# Old-browser build (in-store kiosk / old iPads): lowers public/js + public/css
# in the build output; see scripts/legacy-build.cjs. Never blocks a deploy —
# on any failure the modern assets ship unchanged.
if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
  if npm install --no-save --no-package-lock --no-audit --no-fund esbuild@0.28.2 \
    && node scripts/legacy-build.cjs; then
    echo "legacy-build: done"
  else
    echo "legacy-build: FAILED - deploying modern-only assets"
  fi
else
  echo "legacy-build: node/npm not found - skipping old-browser build"
fi
