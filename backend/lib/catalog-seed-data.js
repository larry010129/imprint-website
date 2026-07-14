/* Legacy catalog weights and labels — ported from imprint-calculator
 * diamond_calculator/application/catalog_seed.py (one-time seed source). */

const IMAGE_COLORS = ['white', 'yellow', 'rose'];

const VALID_GOLDS = ['9k', '14k', '18k', 'pt950', 's925'];

const STYLE_LABELS = {
  pendant: { A: '四爪項墜', B: '兔耳項墜', C: '水滴項墜' },
  ring: { A: '經典六爪', B: '低語之光', C: '羽翼' },
  earring: { A: '六爪耳釘', B: '款式B', C: '款式C' },
  bracelet: { A: '微笑單鑽', B: '銘印手鍊', C: '單鑽手鍊' },
  chain: { A: '斗圓鍊 K白', B: '斗圓鍊 K玫瑰', C: '斗圓鍊 K黃' },
};

const CHAIN_COLORS = { A: 'white', B: 'rose', C: 'yellow' };

const DENSITY_CHIN_PER_CM3 = {
  '9k': 3.07,
  '14k': 3.6,
  '18k': 4.16,
  pt950: 5.57,
  s925: 2.76,
};

const LEGACY_WEIGHT_TABLE = {
  pendant: {
    A: {
      '9k': { '0.1': 0.09, '0.3': 0.12, '0.5': 0.15, '1.0': 0.2 },
      '14k': { '0.1': 0.1, '0.3': 0.14, '0.5': 0.17, '1.0': 0.23 },
      '18k': { '0.1': 0.12, '0.3': 0.16, '0.5': 0.2, '1.0': 0.27 },
      pt950: { '0.1': 0.15, '0.3': 0.2, '0.5': 0.25, '1.0': 0.35 },
      s925: { '0.1': 0.08, '0.3': 0.11, '0.5': 0.13, '1.0': 0.18 },
    },
    B: {
      '9k': { '0.1': 0.1, '0.3': 0.15, '0.5': 0.19, '1.0': 0.28 },
      '14k': { '0.1': 0.11, '0.3': 0.17, '0.5': 0.22, '1.0': 0.33 },
      '18k': { '0.1': 0.13, '0.3': 0.2, '0.5': 0.26, '1.0': 0.39 },
      pt950: { '0.1': 0.16, '0.3': 0.25, '0.5': 0.34, '1.0': 0.52 },
      s925: { '0.1': 0.09, '0.3': 0.13, '0.5': 0.17, '1.0': 0.25 },
    },
    C: {
      '9k': { '0.1': 0.14, '0.3': 0.21, '0.5': 0.28, '1.0': 0.46 },
      '14k': { '0.1': 0.16, '0.3': 0.24, '0.5': 0.32, '1.0': 0.52 },
      '18k': { '0.1': 0.19, '0.3': 0.28, '0.5': 0.37, '1.0': 0.6 },
      pt950: { '0.1': 0.25, '0.3': 0.37, '0.5': 0.49, '1.0': 0.8 },
      s925: { '0.1': 0.13, '0.3': 0.19, '0.5': 0.25, '1.0': 0.4 },
    },
  },
  ring: {
    A: {
      '9k': { '0.1': 0.39, '0.3': 0.48, '0.5': 0.57, '1.0': 0.74 },
      '14k': { '0.1': 0.46, '0.3': 0.57, '0.5': 0.67, '1.0': 0.87 },
      '18k': { '0.1': 0.53, '0.3': 0.65, '0.5': 0.77, '1.0': 1.01 },
      pt950: { '0.1': 0.7, '0.3': 0.86, '0.5': 1.02, '1.0': 1.33 },
      s925: { '0.1': 0.35, '0.3': 0.44, '0.5': 0.52, '1.0': 0.68 },
    },
    B: {
      '9k': { '0.1': 0.4, '0.3': 0.62, '0.5': 0.84, '1.0': 1.39 },
      '14k': { '0.1': 0.47, '0.3': 0.75, '0.5': 1.03, '1.0': 1.73 },
      '18k': { '0.1': 0.54, '0.3': 0.86, '0.5': 1.18, '1.0': 1.98 },
      pt950: { '0.1': 0.71, '0.3': 1.13, '0.5': 1.55, '1.0': 2.6 },
      s925: { '0.1': 0.36, '0.3': 0.58, '0.5': 0.8, '1.0': 1.35 },
    },
    C: {
      '9k': { '0.1': 0.4, '0.3': 0.69, '0.5': 0.97, '1.0': 1.54 },
      '14k': { '0.1': 0.48, '0.3': 0.82, '0.5': 1.15, '1.0': 1.82 },
      '18k': { '0.1': 0.55, '0.3': 0.92, '0.5': 1.33, '1.0': 2.11 },
      pt950: { '0.1': 0.72, '0.3': 1.24, '0.5': 1.75, '1.0': 2.78 },
      s925: { '0.1': 0.36, '0.3': 0.62, '0.5': 0.88, '1.0': 1.4 },
    },
  },
  earring: {
    A: {
      '9k': { '0.1': 0.09, '0.3': 0.14, '0.5': 0.18, '1.0': 0.27 },
      '14k': { '0.1': 0.1, '0.3': 0.15, '0.5': 0.2, '1.0': 0.3 },
      '18k': { '0.1': 0.12, '0.3': 0.18, '0.5': 0.24, '1.0': 0.36 },
    },
  },
  bracelet: {
    A: {
      '9k': { '0.1': 0.66, '0.3': 0.88, '0.5': 1.1, '1.0': 1.47 },
      '14k': { '0.1': 0.78, '0.3': 1.09, '0.5': 1.33, '1.0': 1.79 },
      '18k': { '0.1': 0.91, '0.3': 1.21, '0.5': 1.52, '1.0': 2.05 },
      pt950: { '0.1': 1.19, '0.3': 1.59, '0.5': 1.98, '1.0': 2.78 },
      s925: { '0.1': 0.6, '0.3': 0.83, '0.5': 0.97, '1.0': 1.35 },
    },
    B: {
      '9k': { '0.1': 0.46, '0.3': 0.61, '0.5': 0.77, '1.0': 1.02 },
      '14k': { '0.1': 0.55, '0.3': 0.77, '0.5': 0.94, '1.0': 1.27 },
      '18k': { '0.1': 0.64, '0.3': 0.85, '0.5': 1.07, '1.0': 1.44 },
      pt950: { '0.1': 0.84, '0.3': 1.12, '0.5': 1.4, '1.0': 1.96 },
      s925: { '0.1': 0.77, '0.3': 1.06, '0.5': 1.25, '1.0': 1.73 },
    },
    C: {
      '9k': { '0.1': 0.3, '0.3': 0.4, '0.5': 0.5, '1.0': 0.67 },
      '14k': { '0.1': 0.36, '0.3': 0.5, '0.5': 0.61, '1.0': 0.83 },
      '18k': { '0.1': 0.42, '0.3': 0.56, '0.5': 0.7, '1.0': 0.95 },
      pt950: { '0.1': 0.55, '0.3': 0.73, '0.5': 0.92, '1.0': 1.28 },
      s925: { '0.1': 0.28, '0.3': 0.39, '0.5': 0.46, '1.0': 0.63 },
    },
  },
};

const CHAIN_WEIGHT_CHIN = { '3fen': 0.3, '4fen': 0.4 };

function carat02Weight(w01, w03) {
  return Math.round((w01 + (w03 - w01) * 0.5) * 10000) / 10000;
}

function applyBraceletCaratRules(table) {
  const bracelet = table.bracelet;
  if (!bracelet) return;
  for (const [style, golds] of Object.entries(bracelet)) {
    for (const [gold, carats] of Object.entries(golds)) {
      const w01 = carats['0.1'];
      const w03 = carats['0.3'] ?? w01;
      if (style === 'B') {
        golds[gold] = { '0.1': w01 };
      } else {
        golds[gold] = { '0.1': w01, '0.2': carat02Weight(w01, w03) };
      }
    }
  }
}

function buildWeightTable() {
  const legacy = JSON.parse(JSON.stringify(LEGACY_WEIGHT_TABLE));
  applyBraceletCaratRules(legacy);

  const volumeTable = {};
  for (const [category, types] of Object.entries(legacy)) {
    volumeTable[category] = {};
    for (const [style, styles] of Object.entries(types)) {
      volumeTable[category][style] = {};
      const chin14k = styles['14k'] || styles['18k'] || Object.values(styles)[0];
      for (const [carat, weightChin] of Object.entries(chin14k)) {
        volumeTable[category][style][carat] =
          Math.round((weightChin / DENSITY_CHIN_PER_CM3['14k']) * 10000) / 10000;
      }
    }
  }

  const weightTable = {};
  for (const [category, types] of Object.entries(volumeTable)) {
    weightTable[category] = {};
    for (const [style, carats] of Object.entries(types)) {
      weightTable[category][style] = {};
      const legacyGolds = legacy[category][style];
      for (const gold of Object.keys(legacyGolds)) {
        weightTable[category][style][gold] = {};
        for (const [carat, volume] of Object.entries(carats)) {
          weightTable[category][style][gold][carat] =
            Math.round(volume * DENSITY_CHIN_PER_CM3[gold] * 10000) / 10000;
        }
      }
    }
  }
  return weightTable;
}

/** Relative URL served from the static site (shop/calculator uses ../../images/shop/). */
function imagePath(category, style, color) {
  void color;
  return `images/shop/styles/${category}-${style}.svg`;
}

function styleSortOrder(style) {
  return style.charCodeAt(0) - 'A'.charCodeAt(0);
}

function buildSeedRows() {
  const weightTable = buildWeightTable();
  const rows = [];

  for (const [category, styles] of Object.entries(weightTable)) {
    for (const [style, golds] of Object.entries(styles)) {
      const variants = [];
      for (const [gold, carats] of Object.entries(golds)) {
        for (const [carat, weightChin] of Object.entries(carats)) {
          variants.push({ gold, carat, weightChin });
        }
      }
      const images = IMAGE_COLORS.map((color) => ({
        color,
        filePath: imagePath(category, style, color),
      }));
      rows.push({
        category,
        style,
        nameZh: STYLE_LABELS[category]?.[style] || style,
        defaultColor: 'white',
        sortOrder: styleSortOrder(style),
        variants,
        images,
      });
    }
  }

  for (const [style, defaultColor] of Object.entries(CHAIN_COLORS)) {
    const variants = [];
    for (const gold of VALID_GOLDS) {
      for (const [carat, weightChin] of Object.entries(CHAIN_WEIGHT_CHIN)) {
        variants.push({ gold, carat, weightChin });
      }
    }
    const images = IMAGE_COLORS.map((color) => ({
      color,
      filePath: imagePath('chain', style, color),
    }));
    rows.push({
      category: 'chain',
      style,
      nameZh: STYLE_LABELS.chain[style] || style,
      defaultColor,
      sortOrder: styleSortOrder(style),
      variants,
      images,
    });
  }

  return rows;
}

module.exports = {
  IMAGE_COLORS,
  VALID_GOLDS,
  STYLE_LABELS,
  buildSeedRows,
  imagePath,
};
