#!/usr/bin/env node
/** Print next base group that still has missing variant files. */
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const force = process.argv.includes('--force');
const PROGRESS = path.join(__dirname, 'diamond-variant-progress.json');
const prog = fs.existsSync(PROGRESS) ? JSON.parse(fs.readFileSync(PROGRESS, 'utf8')) : { generated: [] };
const done = new Set(prog.generated || []);
const batches = JSON.parse(fs.readFileSync(path.join(__dirname, 'diamond-variant-batches.json'), 'utf8'));

for (let i = 0; i < batches.groups.length; i++) {
  const g = batches.groups[i];
  const pending = force
    ? g.variants.filter((v) => !done.has(v.out))
    : g.variants.filter((v) => !fs.existsSync(path.join(ROOT, v.out)));
  if (!pending.length) continue;
  console.log(JSON.stringify({ index: i, base: g.base, productId: g.productId, pending }, null, 2));
  process.exit(0);
}
console.log('ALL_DONE');
