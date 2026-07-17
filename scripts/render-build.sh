#!/usr/bin/env bash
set -o errexit
python -m pip install --upgrade pip
pip install -r requirements.txt
if command -v node >/dev/null 2>&1; then
  node scripts/build-shop-catalog-static.cjs
  node -e "const {buildSeedRows}=require('./backend/lib/catalog-seed-data'); require('fs').writeFileSync('app/data/catalog-seed-rows.json', JSON.stringify(buildSeedRows(), null, 2));"
fi
