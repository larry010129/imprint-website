#!/usr/bin/env node
/* Verify shop/image files match ShopAssets mapping. */
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..', 'shop', 'image');

const CATEGORY_ZH = {
  pendant: '項墜', ring: '戒指', earring: '耳飾', bracelet: '手鍊',
};
const COLOR_DIR = { white: 'silver', yellow: 'gold', rose: 'rose_gold' };
const COLOR_SUFFIX = { white: 'silver', yellow: 'gold', rose: 'rose' };
const CHAIN_BASENAME = { A: '斗圓鍊', B: '斗圓鍊K玫瑰', C: '斗圓鍊K黃' };
const FILE_OVERRIDES = {
  'rose_gold|斗圓鍊K玫瑰|rose': '斗圓鍊K玫瑰_silver2.png',
};

const PRODUCTS = [];
for (const [cat, zh] of Object.entries(CATEGORY_ZH)) {
  for (const style of ['A', 'B', 'C']) {
    if (cat === 'earring' && style !== 'A') continue;
    PRODUCTS.push({ id: `${cat}-${style}`, category: cat, style });
  }
}
for (const style of ['A', 'B', 'C']) {
  PRODUCTS.push({ id: `chain-${style}`, category: 'chain', style });
}

function pngPath(category, style, color) {
  const dir = COLOR_DIR[color];
  const suffix = COLOR_SUFFIX[color];
  if (category === 'chain') {
    const base = CHAIN_BASENAME[style];
    const key = `${dir}|${base}|${suffix}`;
    const file = FILE_OVERRIDES[key] || `${base}_${suffix}.png`;
    return path.join(ROOT, dir, file);
  }
  return path.join(ROOT, dir, `${CATEGORY_ZH[category]}${style}_${suffix}.png`);
}

let missing = 0;
for (const p of PRODUCTS) {
  for (const color of ['white', 'yellow', 'rose']) {
    const fp = pngPath(p.category, p.style, color);
    if (!fs.existsSync(fp)) {
      console.log('MISSING', path.relative(ROOT, fp));
      missing++;
    }
  }
}
console.log(missing ? `${missing} missing file(s)` : 'All mapped PNGs present.');
