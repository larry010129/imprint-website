#!/usr/bin/env node
/** Build girdle-matrix generation prompts (v2 — distinct side silhouettes). */
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const manifest = JSON.parse(fs.readFileSync(path.join(__dirname, 'diamond-girdle-matrix-manifest.json'), 'utf8'));

const STYLE_SUFFIX =
  'Photorealistic 3D CGI jewelry catalog render, side profile at 15 degrees from above, crown table and frosted matte girdle band clearly visible, sharp pavilion facets, realistic internal light refraction and fire, soft diffused studio lighting, subtle soft shadow beneath culet, solid pure white background, no setting no ring no necklace, no text no watermark no logo.';

const SHAPE_SIDE = {
  round: 'round brilliant cut with circular girdle outline in side profile',
  marquise: 'marquise navette cut with two sharp pointed ends, elongated football silhouette in side profile, NOT round NOT oval',
  oval: 'oval brilliant cut with smooth elongated oval girdle outline in side profile, NOT round NOT marquise',
  princess: 'square princess cut with flat top and sharp square corners visible in side profile, NOT round',
  trilliant: 'equilateral triangular trilliant cut with three pointed corners visible in side profile, NOT round',
  emerald: 'rectangular emerald step cut with cropped corners and step facets visible in side profile, hall-of-mirrors, NOT round',
  heart: 'heart brilliant cut with cleft notch at top and pointed tip at bottom visible in side profile, NOT round',
  radiant: 'rectangular radiant cut with cropped corners and brilliant facet pattern in side profile, NOT emerald step cut NOT round',
  pear: 'pear teardrop cut with one rounded end and one pointed tip in side profile, NOT marquise NOT round',
  cushion: 'cushion modified brilliant cut with pillow-shaped rounded square outline in side profile, NOT round',
};

const ALL_SHAPES = [
  { id: 'round', cut: 'round brilliant cut', silhouette: SHAPE_SIDE.round },
  ...manifest.shapes.map((s) => ({ id: s.id, cut: s.cut, silhouette: SHAPE_SIDE[s.id] || s.silhouette })),
];

function buildPrompt(shape, color) {
  return [
    `Photorealistic 3D CGI render of a single loose ${shape.cut} diamond gemstone.`,
    shape.silhouette + '.',
    color.prompt + '.',
    'CRITICAL: the side-profile girdle silhouette must be unmistakably ' + shape.id + ' shape.',
    STYLE_SUFFIX,
  ].join(' ');
}

const jobs = [];
for (const shape of ALL_SHAPES) {
  for (const color of manifest.colors) {
    const out = `public/images/diamonds/girdle-matrix/${shape.id}-${color.id}.png`;
    const topDown = `public/images/diamonds/matrix/${shape.id}-${color.id}.png`;
    jobs.push({
      out,
      filename: `${shape.id}-${color.id}.png`,
      topDownRef: fs.existsSync(path.join(ROOT, topDown)) ? topDown : null,
      prompt: buildPrompt(shape, color),
      aspect_ratio: manifest.aspect_ratio,
      model: manifest.model,
      styleRef: manifest.referenceMediaId,
    });
  }
}

const cmd = process.argv[2];
if (cmd === 'list') {
  console.log(JSON.stringify(jobs, null, 2));
} else if (cmd === 'count') {
  console.log(jobs.length);
} else {
  console.log('Usage: list | count');
}
