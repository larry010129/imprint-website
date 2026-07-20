#!/usr/bin/env node
/**
 * Group missing diamond variants by base PNG so each base is uploaded once.
 * Usage: node scripts/group-diamond-variant-bases.cjs
 */
const fs = require('fs');
const path = require('path');

const allManifest = path.join(__dirname, 'all-diamond-variants.json');
const manifestFile = process.argv.includes('--all') || fs.existsSync(allManifest)
  ? 'all-diamond-variants.json'
  : 'missing-diamond-variants.json';
const manifest = JSON.parse(fs.readFileSync(path.join(__dirname, manifestFile), 'utf8'));

const DIAMOND_PROMPT = {
  yellow: 'vivid yellow fancy colored diamond',
  blue: 'light blue fancy colored diamond',
  pink: 'soft pink fancy colored diamond',
};

const CLEAN =
  'Do NOT add any text, red boxes, labels, product codes, carat annotations, or watermarks — jewelry only on a clean pure white background.';

const groups = new Map();
for (const item of manifest) {
  if (!groups.has(item.base)) {
    groups.set(item.base, {
      base: item.base,
      productId: item.productId,
      category: item.category,
      variants: [],
    });
  }
  groups.get(item.base).variants.push({
    diamond: item.diamond,
    out: item.out,
    prompt: `Edit this exact jewelry product photo: keep the same design, metal, angle, lighting and pure white background unchanged. Only replace the center diamond or main gemstone with a ${DIAMOND_PROMPT[item.diamond]}. ${CLEAN} Photorealistic e-commerce product shot.`,
  });
}

const out = {
  model: 'nano_banana_pro',
  aspect_ratio: '1:1',
  totalVariants: manifest.length,
  totalBases: groups.size,
  groups: Array.from(groups.values()),
};

fs.writeFileSync(path.join(__dirname, 'diamond-variant-batches.json'), JSON.stringify(out, null, 2));
console.log(`${out.totalBases} base image(s), ${out.totalVariants} variant(s) → scripts/diamond-variant-batches.json`);
