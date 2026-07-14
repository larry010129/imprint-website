#!/usr/bin/env node
/**
 * Copy 金屬戒指 renders from diamond-calculator into V3 product image paths.
 *
 * Maps calculator metal_ring-{A,B,C,D}.png (per metal color folder) to the
 * four jewelry ring product slugs used on the V3 site:
 *
 *   A → ring-classic-solitaire
 *   B → ring-pave-halo
 *   C → ring-vintage-vine
 *   D → ring-modern-band
 *
 * Gallery slots 1–3 use K白 / K黃 / K玫瑰 renders; slot 4 repeats K白.
 *
 * Run from repo root:
 *   cd scripts && npm install && npm run sync:ring-images
 *
 * Or once after install:
 *   node scripts/sync_ring_images_from_calculator.mjs
 *
 * Env:
 *   DIAMOND_CALCULATOR_ROOT=C:\Users\...\diamond-calculator
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import sharp from 'sharp';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');
const CALC_ROOT = process.env.DIAMOND_CALCULATOR_ROOT
  ? path.resolve(process.env.DIAMOND_CALCULATOR_ROOT)
  : path.join(process.env.USERPROFILE || process.env.HOME || '', 'Documents', 'diamond-calculator');
const SRC = path.join(CALC_ROOT, 'static', 'images');
const DEST = path.join(ROOT, 'images', 'products');

const STYLE_MAP = {
  A: 'ring-classic-solitaire',
  B: 'ring-pave-halo',
  C: 'ring-vintage-vine',
  D: 'ring-modern-band',
};

const COLOR_SLOTS = [
  ['white', 1],
  ['yellow', 2],
  ['rose', 3],
];

async function saveJpgWebp(src, destJpg, destWebp) {
  fs.mkdirSync(path.dirname(destJpg), { recursive: true });
  const pipeline = sharp(src).flatten({ background: { r: 253, g: 252, b: 250 } });
  await pipeline.clone().jpeg({ quality: 88, mozjpeg: true }).toFile(destJpg);
  await pipeline.clone().webp({ quality: 85, effort: 6 }).toFile(destWebp);
}

async function main() {
  if (!fs.existsSync(SRC)) {
    console.error(`Calculator images not found: ${SRC}`);
    process.exit(1);
  }

  let count = 0;

  for (const [slug, prefix] of Object.entries(STYLE_MAP)) {
    for (const [color, slot] of COLOR_SLOTS) {
      const src = path.join(SRC, color, `metal_ring-${slug}.png`);
      if (!fs.existsSync(src)) {
        console.log(`  skip missing: ${src}`);
        continue;
      }
      await saveJpgWebp(
        src,
        path.join(DEST, `${prefix}-${slot}.jpg`),
        path.join(DEST, `${prefix}-${slot}.webp`),
      );
      count += 2;
      console.log(`  ${prefix}-${slot} ← ${path.basename(src)} (${color})`);
    }

    const whiteSrc = path.join(SRC, 'white', `metal_ring-${slug}.png`);
    if (fs.existsSync(whiteSrc)) {
      await saveJpgWebp(
        whiteSrc,
        path.join(DEST, `${prefix}-4.jpg`),
        path.join(DEST, `${prefix}-4.webp`),
      );
      count += 2;
      console.log(`  ${prefix}-4 ← ${path.basename(whiteSrc)} (white repeat)`);
    }
  }

  const heroSrc = path.join(SRC, 'white', 'metal_ring-A.png');
  if (fs.existsSync(heroSrc)) {
    await saveJpgWebp(
      heroSrc,
      path.join(DEST, 'category-ring.jpg'),
      path.join(DEST, 'category-ring.webp'),
    );
    count += 2;
    console.log('  category-ring ← metal_ring-A (white)');
  }

  console.log(`Done — wrote ${count} product image file(s) to ${DEST}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
