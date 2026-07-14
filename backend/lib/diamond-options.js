/* Diamond color/shape metadata for the shop UI — ported from diamond_options.py */

const {
  DIAMOND_PRICE,
  COLORED_SINGLE_DIAMOND_PRICE,
  WHITE_MULTI_DIAMOND_PRICE,
  COLORED_MULTI_DIAMOND_PRICE,
  MULTI_STONE_ABOVE_03_MULTIPLIER,
} = require('./pricing');

const VALID_STONE_COUNTS = new Set([2, 3, 4]);
const FANCY_MIN_CARAT = '0.3';
const NON_ROUND_SHAPE_MIN_CARAT = '0.3';
const NON_ROUND_SHAPE_SURCHARGE = 0.10;
const STONE_COUNT_CATEGORIES = new Set(['earring']);
const DEFAULT_STONE_COUNT_BY_CATEGORY = { earring: 2, ring: 2, pendant: 2 };

const DIAMOND_COLOR_META = [
  { id: 'white', kind: 'white', labelZh: '白鑽', labelEn: 'White', swatch: '#e8e8e8', image: 'diamonds/shapes/round.svg' },
  { id: 'yellow', kind: 'fancy', labelZh: '黃鑽', labelEn: 'Yellow', swatch: '#e6c200', image: 'diamonds/fancy/yellow.svg' },
  { id: 'pink', kind: 'fancy', labelZh: '粉鑽', labelEn: 'Pink', swatch: '#f4a6c8', image: 'diamonds/fancy/pink.svg' },
  { id: 'blue', kind: 'fancy', labelZh: '藍鑽', labelEn: 'Blue', swatch: '#7ec8e3', image: 'diamonds/fancy/blue.svg' },
];

const FANCY_COLOR_META = DIAMOND_COLOR_META.filter((c) => c.kind === 'fancy');

const DIAMOND_KIND_META = [
  { id: 'white', labelZh: '白鑽', labelEn: 'White' },
  { id: 'fancy', labelZh: '彩鑽', labelEn: 'Fancy Color' },
];

const DIAMOND_SHAPE_META = [
  { id: 'round', labelZh: '圓鑽', labelEn: 'Round', image: 'diamonds/shapes/round.svg' },
];

function diamondOptionsPayload() {
  return {
    kinds: DIAMOND_KIND_META,
    diamondColors: DIAMOND_COLOR_META,
    fancyColors: FANCY_COLOR_META,
    shapes: DIAMOND_SHAPE_META,
    stoneCounts: [...VALID_STONE_COUNTS].sort(),
    defaultStoneCountByCategory: DEFAULT_STONE_COUNT_BY_CATEGORY,
    stoneCountCategories: [...STONE_COUNT_CATEGORIES].sort(),
    fancyMinCarat: FANCY_MIN_CARAT,
    nonRoundShapeMinCarat: NON_ROUND_SHAPE_MIN_CARAT,
    nonRoundShapeSurcharge: NON_ROUND_SHAPE_SURCHARGE,
    coloredDiamondPrice: COLORED_MULTI_DIAMOND_PRICE,
    coloredSingleDiamondPrice: COLORED_SINGLE_DIAMOND_PRICE,
    whiteMultiDiamondPrice: WHITE_MULTI_DIAMOND_PRICE,
    coloredAbove03Multiplier: MULTI_STONE_ABOVE_03_MULTIPLIER,
    shapeSurcharge: {},
    diamond: DIAMOND_PRICE,
  };
}

module.exports = { diamondOptionsPayload };
