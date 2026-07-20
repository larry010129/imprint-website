#!/usr/bin/env node
/** List shop-product PNGs missing fancy-diamond suffix variants (_yellow/_blue/_pink). */
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..', 'public', 'images', 'shop-product');
const FANCY = ['yellow', 'blue', 'pink'];
const CATEGORY_ZH = {
  pendant: '項墜',
  ring: '戒指',
  earring: '耳飾',
  bracelet: '手鍊',
};
const COLOR_DIR = { white: 'silver', yellow: 'gold', rose: 'rose_gold' };
const COLOR_SUFFIX = { white: 'silver', yellow: 'gold', rose: 'rose' };
const CHAIN_BASENAME = { A: '斗圓鍊', B: '斗圓鍊K玫瑰', C: '斗圓鍊K黃' };
const FILE_OVERRIDES = {
  'rose_gold|斗圓鍊K玫瑰|rose': '斗圓鍊K玫瑰_silver2.png',
};

const products = [];
for (const [cat, zh] of Object.entries(CATEGORY_ZH)) {
  for (const style of ['A', 'B', 'C']) {
    if (cat === 'earring' && style !== 'A') continue;
    products.push({ id: `${cat}-${style}`, category: cat, style });
  }
}
for (const style of ['A', 'B', 'C']) {
  products.push({ id: `chain-${style}`, category: 'chain', style });
}

function basePath(category, style, metal) {
  const dir = COLOR_DIR[metal];
  const suffix = COLOR_SUFFIX[metal];
  if (category === 'chain') {
    const base = CHAIN_BASENAME[style];
    const key = `${dir}|${base}|${suffix}`;
    const file = FILE_OVERRIDES[key] || `${base}_${suffix}.png`;
    return path.join(ROOT, dir, file);
  }
  const zh = CATEGORY_ZH[category];
  return path.join(ROOT, dir, `${zh}${style}_${suffix}.png`);
}

function variantPath(category, style, metal, diamond) {
  const dir = COLOR_DIR[metal];
  const suffix = COLOR_SUFFIX[metal];
  if (category === 'chain') {
    const base = CHAIN_BASENAME[style];
    const key = `${dir}|${base}|${suffix}`;
    const stem = (FILE_OVERRIDES[key] || `${base}_${suffix}.png`).replace(/\.png$/i, '');
    return path.join(ROOT, dir, `${stem}_${diamond}.png`);
  }
  const zh = CATEGORY_ZH[category];
  return path.join(ROOT, dir, `${zh}${style}_${suffix}_${diamond}.png`);
}

const allFlag = process.argv.includes('--all');
const entries = [];
for (const p of products) {
  for (const metal of ['white', 'yellow', 'rose']) {
    const base = basePath(p.category, p.style, metal);
    if (!fs.existsSync(base)) continue;
    for (const diamond of FANCY) {
      const out = variantPath(p.category, p.style, metal, diamond);
      const exists = fs.existsSync(out);
      if (allFlag || !exists) {
        entries.push({
          productId: p.id,
          category: p.category,
          style: p.style,
          metal,
          diamond,
          base: path.relative(path.join(__dirname, '..'), base).replace(/\\/g, '/'),
          out: path.relative(path.join(__dirname, '..'), out).replace(/\\/g, '/'),
        });
      }
    }
  }
}

const outFile = path.join(__dirname, allFlag ? 'all-diamond-variants.json' : 'missing-diamond-variants.json');
fs.writeFileSync(outFile, JSON.stringify(entries, null, 2));
console.log(`${entries.length} ${allFlag ? 'total' : 'missing'} variant(s) → ${path.relative(process.cwd(), outFile)}`);
if (process.argv.includes('--print')) {
  entries.forEach((m) => console.log(m.out));
}
