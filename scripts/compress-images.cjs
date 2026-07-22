#!/usr/bin/env node
/** Compress PNG/JPEG/WebP under public/images to <= max KB (default 700). */
const fs = require('fs');
const path = require('path');
const sharp = require('sharp');

const ROOT = path.join(__dirname, '..', 'public', 'images');
const MAX_BYTES = (parseInt(process.argv.find((a) => a.startsWith('--max-kb='))?.split('=')[1], 10) || 700) * 1024;
const EXT = new Set(['.png', '.jpg', '.jpeg', '.webp']);

async function encode(file, width) {
  const ext = path.extname(file).toLowerCase();
  let pipeline = sharp(file);
  if (width) {
    pipeline = pipeline.resize(width, null, { fit: 'inside', withoutEnlargement: true });
  }
  if (ext === '.png') {
    return pipeline.png({ compressionLevel: 9, effort: 10 }).toBuffer();
  }
  if (ext === '.webp') {
    return pipeline.webp({ quality: 82, effort: 6 }).toBuffer();
  }
  return pipeline.jpeg({ quality: 82, mozjpeg: true }).toBuffer();
}

async function compressFile(file) {
  const before = fs.statSync(file).size;
  if (before <= MAX_BYTES) {
    return { file, skipped: true, before, after: before };
  }

  const meta = await sharp(file).metadata();
  const fullWidth = meta.width || 1;

  let data = await encode(file, null);
  if (data.length <= MAX_BYTES) {
    fs.writeFileSync(file, data);
    return { file, before, after: data.length };
  }

  let lo = 0.25;
  let hi = 1.0;
  let best = null;
  for (let i = 0; i < 14; i++) {
    const mid = (lo + hi) / 2;
    const width = Math.max(1, Math.round(fullWidth * mid));
    data = await encode(file, width);
    if (data.length <= MAX_BYTES) {
      best = data;
      lo = mid;
    } else {
      hi = mid;
    }
  }

  if (!best) {
    data = await encode(file, Math.max(1, Math.round(fullWidth * 0.25)));
    if (data.length > MAX_BYTES) {
      throw new Error(`cannot compress under ${MAX_BYTES} bytes (got ${data.length})`);
    }
    best = data;
  }

  fs.writeFileSync(file, best);
  return { file, before, after: best.length };
}

function walk(dir) {
  const out = [];
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, ent.name);
    if (ent.isDirectory()) out.push(...walk(p));
    else if (EXT.has(path.extname(ent.name).toLowerCase())) out.push(p);
  }
  return out;
}

async function main() {
  const rootArg = process.argv.find((a) => a.startsWith('--root='));
  const root = rootArg ? path.resolve(rootArg.split('=')[1]) : ROOT;
  const files = walk(root);
  const done = [];
  const errors = [];

  for (const file of files) {
    try {
      const result = await compressFile(file);
      if (!result.skipped) {
        done.push(result);
        const name = path.relative(root, file);
        console.log(`${Math.round(result.before / 1024)}KB -> ${Math.round(result.after / 1024)}KB  ${name}`);
      }
    } catch (err) {
      errors.push({ file, error: err.message });
      console.error(`ERROR ${file}: ${err.message}`);
    }
  }

  const saved = done.reduce((sum, r) => sum + r.before - r.after, 0);
  console.log(
    `scanned=${files.length} compressed=${done.length} errors=${errors.length} saved_mb=${(saved / 1024 / 1024).toFixed(2)}`,
  );
  process.exit(errors.length ? 1 : 0);
}

main();
