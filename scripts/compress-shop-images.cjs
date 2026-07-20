#!/usr/bin/env node
/** @deprecated Use `.venv/Scripts/python.exe scripts/compress_shop_images.py` (Pillow). Requires ImageMagick. */
/** Compress shop-product images >700KB to ≤1000KB (≥50% reduction when possible). */
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const ROOT = path.join(__dirname, '..', 'public', 'images', 'shop-product');
const MIN_BYTES = 700 * 1024;
const MAX_BYTES = 1000 * 1024;
const EXT = new Set(['.png', '.jpg', '.jpeg']);

function walk(dir, out = []) {
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, ent.name);
    if (ent.isDirectory()) walk(p, out);
    else if (EXT.has(path.extname(ent.name).toLowerCase())) out.push(p);
  }
  return out;
}

function identify(file) {
  const out = execFileSync('magick', ['identify', '-format', '%w %h %m', file], { encoding: 'utf8' }).trim();
  const [w, h, fmt] = out.split(/\s+/);
  return { w: +w, h: +h, fmt: (fmt || '').toLowerCase() };
}

function runMagick(args) {
  execFileSync('magick', args, { stdio: 'pipe' });
}

function compress(file) {
  const before = fs.statSync(file).size;
  if (before <= MIN_BYTES) return null;

  const { w, h, fmt } = identify(file);
  const tmp = file + '.compress.tmp';
  const maxDim = Math.max(w, h);
  const isPng = fmt === 'png' || file.toLowerCase().endsWith('.png');
  const isJpeg = !isPng;

  const attempts = [];
  if (maxDim > 1024) {
    attempts.push(['-resize', '1024x1024>']);
  }
  attempts.push(['-strip']);
  if (isPng) {
    attempts.push(['-define', 'png:compression-level=9', '-define', 'png:compression-filter=5']);
  } else {
    attempts.push(['-quality', '85']);
  }

  const flat = attempts.flat();
  runMagick([file, ...flat, tmp]);
  let after = fs.statSync(tmp).size;

  if (after > MAX_BYTES && isPng) {
    fs.unlinkSync(tmp);
    runMagick([file, ...flat, '-colors', '256', 'PNG8:' + tmp]);
    after = fs.statSync(tmp).size;
  }

  if (after > MAX_BYTES && isJpeg) {
    for (const q of [78, 72, 65, 58]) {
      fs.unlinkSync(tmp);
      runMagick([file, ...(maxDim > 1024 ? ['-resize', '1024x1024>'] : []), '-strip', '-quality', String(q), tmp]);
      after = fs.statSync(tmp).size;
      if (after <= MAX_BYTES) break;
    }
  }

  const saved = before - after;
  const ratio = saved / before;
  if (after >= before || (ratio < 0.5 && after > MAX_BYTES)) {
    fs.unlinkSync(tmp);
    return { file, before, after: before, skipped: true, reason: 'no sufficient gain' };
  }

  fs.renameSync(tmp, file);
  return { file: path.relative(path.join(__dirname, '..'), file), before, after, ratio };
}

const files = walk(ROOT);
const results = [];
for (const f of files) {
  try {
    const r = compress(f);
    if (r) results.push(r);
  } catch (e) {
    results.push({ file: f, error: e.message });
  }
}

const done = results.filter((r) => !r.skipped && !r.error);
const skipped = results.filter((r) => r.skipped);
const errors = results.filter((r) => r.error);
const totalBefore = done.reduce((n, r) => n + r.before, 0);
const totalAfter = done.reduce((n, r) => n + r.after, 0);

console.log(JSON.stringify({
  scanned: files.length,
  compressed: done.length,
  skipped,
  errors: errors.length,
  savedMB: +((totalBefore - totalAfter) / 1024 / 1024).toFixed(2),
  items: done.map((r) => ({
    file: r.file,
    beforeKB: Math.round(r.before / 1024),
    afterKB: Math.round(r.after / 1024),
    pct: Math.round(r.ratio * 100),
  })),
}, null, 2));
