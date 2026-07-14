/* Generate per-style placeholder SVGs for the shop calculator. */
const fs = require('fs');
const path = require('path');
const { buildSeedRows } = require('../backend/lib/catalog-seed-data');

const OUT = path.join(__dirname, '..', 'images', 'shop', 'styles');
const ACCENTS = ['#9CEFEF', '#EFE8DC', '#DCF2F2'];
const STROKE = '#2B2320';
const MINT = '#5ECFCF';

function styleSvg(row, index) {
  const accent = ACCENTS[index % ACCENTS.length];
  const label = row.style;
  const variant = index % 3;
  let motif = '';
  if (variant === 0) {
    motif = `<circle cx="100" cy="96" r="28" stroke="${STROKE}" stroke-width="3" fill="#fff"/>
      <path d="M100 62 L90 96 L100 112 L110 96 Z" fill="${accent}" stroke="${MINT}" stroke-width="1.5"/>`;
  } else if (variant === 1) {
    motif = `<rect x="72" y="72" width="56" height="56" rx="12" stroke="${STROKE}" stroke-width="3" fill="#fff"/>
      <circle cx="100" cy="100" r="14" fill="${accent}" stroke="${MINT}" stroke-width="1.5"/>`;
  } else {
    motif = `<ellipse cx="100" cy="100" rx="40" ry="30" stroke="${STROKE}" stroke-width="3" fill="#fff"/>
      <path d="M100 68 L86 100 L100 118 L114 100 Z" fill="${accent}" stroke="${MINT}" stroke-width="1.5"/>`;
  }
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" fill="none" aria-hidden="true">
  <rect width="200" height="200" fill="#F4FBFB"/>
  ${motif}
  <text x="100" y="168" text-anchor="middle" font-family="Georgia, serif" font-size="13" fill="#8A817B" letter-spacing="0.12em">${label}</text>
</svg>`;
}

fs.mkdirSync(OUT, { recursive: true });
const rows = buildSeedRows();
rows.forEach((row, i) => {
  const id = `${row.category}-${row.style}`;
  fs.writeFileSync(path.join(OUT, `${id}.svg`), styleSvg(row, i));
});
console.log(`Wrote ${rows.length} style SVGs to images/shop/styles/`);
