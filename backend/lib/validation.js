/* 銘印鑽石｜表單驗證 — JS 版本，邏輯移植自 imprint-calculator 的 validation.py。
 * JSON 版本的 validate_submission_fields（原本是 Flask form-encoded，這裡
 * API 收 JSON body，邏輯一致）。validate_product_fields 簡化為 JSON 版本：
 * 圖片改收「已上傳好的圖檔網址」而非原本的 multipart 檔案上傳，因為 serverless
 * function 的檔案上傳需要物件儲存（S3、R2 等），尚未串接
 * (見 backend/README.md「尚未完成」章節)。
 */

const VALID_CATEGORIES = new Set(['pendant', 'ring', 'earring', 'bracelet', 'chain']);
const VALID_CARATS = new Set(['0.1', '0.2', '0.3', '0.5', '1.0']);
const VALID_CARATS_CHAIN = new Set(['3fen', '4fen']);
const VALID_GOLDS = new Set(['9k', '14k', '18k', 'pt950', 's925']);
const GOLDS_REQUIRING_COLOR = new Set(['14k', '18k']);
const GOLD_WHITE_ONLY = new Set(['9k']);
const VALID_COLORS = new Set(['white', 'yellow', 'rose']);
const RING_SIZE_MIN = 5;
const RING_SIZE_MAX = 18;
const ENGRAVING_MAX_LENGTH = 10;
const GIRDLE_MAX_SLOTS = 12;
const GIRDLE_EMBLEM_SLOT_COST = 2;
const GIRDLE_EMBLEM_LABELS = new Set(['蝴蝶結', '幸運草', '無限', '愛心', '雙愛心', '肉球', '骨頭', '戒圈']);
const GIRDLE_ENGRAVING_CATEGORIES = new Set(['pendant', 'ring', 'earring', 'bracelet']);
const CHAIN_LENGTH_OPTIONS_CM = new Set([35, 40, 46, 50, 56, 60, 66, 70, 76, 90, 102]);
const BRACELET_LENGTH_OPTIONS_CM = new Set([15, 16, 17, 18, 19, 20, 21]);
const VALID_DIAMOND_KINDS = new Set(['white', 'fancy']);
const VALID_DIAMOND_SHAPES = new Set([
  'round', 'marquise', 'oval', 'princess', 'trilliant', 'emerald', 'heart', 'radiant', 'pear', 'cushion',
]);
const VALID_FANCY_COLORS = new Set(['yellow', 'pink', 'blue']);
const VALID_STONE_COUNTS = new Set([2, 3, 4]);
const DEFAULT_STONE_COUNT_BY_CATEGORY = { earring: 2, ring: 2, pendant: 2 };
const STONE_COUNT_CATEGORIES = new Set(['earring']);

function isFancyCaratAllowed(caratKey) {
  const n = parseFloat(caratKey);
  return !Number.isNaN(n) && n >= 0.3;
}

function isShapeCaratAllowed(caratKey, shape) {
  if ((shape || 'round') === 'round') return true;
  return isFancyCaratAllowed(caratKey);
}

/** Validates + normalizes a shop configuration (quote / cart / favorite / order).
 * Returns { cleaned, error }. `partial=true` skips required-field checks
 * (used for live quote-as-you-type; full checks apply at cart/checkout time).
 */
function validateSubmissionFields(data, { partial = false } = {}) {
  const errors = [];
  const cleaned = {};
  data = data || {};

  function checkChoice(key, valid, required = true) {
    const val = data[key];
    if (val == null) {
      if (required && !partial) errors.push(`${key} is required`);
    } else if (!valid.has(String(val))) {
      errors.push(`invalid ${key}`);
    } else {
      cleaned[key] = String(val);
    }
  }

  checkChoice('category', VALID_CATEGORIES);
  checkChoice('gold', VALID_GOLDS);

  if (data.type == null) {
    if (!partial) errors.push('type is required');
  } else {
    cleaned.type = String(data.type);
  }

  const cat = cleaned.category || String(data.category || '');
  if (data.carat == null) {
    if (!partial) errors.push('carat is required');
  } else {
    const validCarats = cat === 'chain' ? VALID_CARATS_CHAIN : VALID_CARATS;
    if (!validCarats.has(String(data.carat))) errors.push('invalid carat');
    else cleaned.carat = String(data.carat);
  }

  if (data.color != null) {
    if (!VALID_COLORS.has(String(data.color))) errors.push('invalid color');
    else cleaned.color = String(data.color);
  }

  if (!partial) {
    const gold = cleaned.gold;
    if (GOLD_WHITE_ONLY.has(gold)) {
      if (cleaned.color != null && cleaned.color !== 'white') errors.push('9k only supports white');
      else cleaned.color = 'white';
    } else if (GOLDS_REQUIRING_COLOR.has(gold) && cleaned.color === undefined) {
      errors.push('color is required for gold alloys');
    }
  }

  if (data.ringSize != null) {
    const n = Number(data.ringSize);
    const ringSize = Number.isNaN(n) ? -1 : n;
    if (ringSize < RING_SIZE_MIN || ringSize > RING_SIZE_MAX) errors.push('invalid ringSize');
    else cleaned.ringSize = ringSize;
  }
  if (!partial && cleaned.category === 'ring' && cleaned.ringSize === undefined) {
    errors.push('ringSize is required for rings');
  }

  function girdleEngraveSlotCount(value) {
    let i = 0;
    let slots = 0;
    const s = String(value);
    while (i < s.length) {
      if (s[i] === '〔') {
        const end = s.indexOf('〕', i);
        if (end === -1) return -1;
        const label = s.slice(i + 1, end);
        if (!GIRDLE_EMBLEM_LABELS.has(label)) return -1;
        slots += GIRDLE_EMBLEM_SLOT_COST;
        i = end + 1;
      } else if (/[A-Za-z0-9]/.test(s[i])) {
        slots += 1;
        i += 1;
      } else {
        return -1;
      }
    }
    return slots;
  }

  function cleanEngraving(key, permittedCategories) {
    const raw = data[key];
    if (raw == null) return;
    const value = key === 'engravingGirdle'
      ? String(raw).trim()
      : String(raw).trim().replace(/[^\x20-\x7E\u00A0-\uFFFF]/g, '');
    if (!permittedCategories.has(cleaned.category)) {
      if (value) errors.push(`${key} is not available for this category`);
    } else if (key !== 'engravingGirdle' && value.length > ENGRAVING_MAX_LENGTH) {
      errors.push(`${key} must be at most ${ENGRAVING_MAX_LENGTH} characters`);
    } else if (value && key === 'engravingGirdle') {
      const slotCount = girdleEngraveSlotCount(value);
      if (slotCount < 1 || slotCount > GIRDLE_MAX_SLOTS) {
        errors.push(`${key} must be 1-${GIRDLE_MAX_SLOTS} A-Z/a-z/0-9 chars or emblem tokens only`);
      } else {
        cleaned[key] = value;
      }
    } else if (value) {
      cleaned[key] = value;
    }
  }
  cleanEngraving('engravingBand', new Set(['ring']));
  cleanEngraving('engravingGirdle', GIRDLE_ENGRAVING_CATEGORIES);

  function cleanChainLength(key, { required = false, allowed = CHAIN_LENGTH_OPTIONS_CM } = {}) {
    const raw = data[key];
    if (raw == null) {
      if (required) errors.push(`${key} is required`);
      return null;
    }
    const n = parseInt(raw, 10);
    const value = Number.isNaN(n) ? -1 : n;
    if (!allowed.has(value)) { errors.push(`invalid ${key}`); return null; }
    return value;
  }

  if (cleaned.category === 'chain') {
    const length = cleanChainLength('lengthCm', { required: !partial });
    if (length != null) cleaned.lengthCm = length;
  }
  if (cleaned.category === 'bracelet') {
    const length = cleanChainLength('lengthCm', { required: !partial, allowed: BRACELET_LENGTH_OPTIONS_CM });
    if (length != null) cleaned.lengthCm = length;
  }

  const includeChain = !!data.includeChain;

  if (data.diamondKind != null) {
    const dk = String(data.diamondKind);
    if (!VALID_DIAMOND_KINDS.has(dk)) errors.push('invalid diamondKind');
    else cleaned.diamondKind = dk;
  }
  if (data.diamondShape != null) {
    const ds = String(data.diamondShape);
    if (!VALID_DIAMOND_SHAPES.has(ds)) errors.push('invalid diamondShape');
    else cleaned.diamondShape = ds;
  } else {
    cleaned.diamondShape = 'round';
  }

  if (cat === 'chain') {
    cleaned.diamondKind = 'white';
    cleaned.diamondShape = 'round';
  } else if (cleaned.diamondKind === 'fancy') {
    if (data.fancyColor == null) {
      if (!partial) errors.push('fancyColor is required for fancy diamonds');
    } else if (!VALID_FANCY_COLORS.has(String(data.fancyColor))) {
      errors.push('invalid fancyColor');
    } else {
      cleaned.fancyColor = String(data.fancyColor);
    }

    if (cleaned.carat && !partial && !isFancyCaratAllowed(cleaned.carat)) {
      errors.push('fancy diamonds require carat 0.30 or above');
    }

    if (STONE_COUNT_CATEGORIES.has(cat)) {
      if (data.stoneCount == null) {
        if (!partial) cleaned.stoneCount = DEFAULT_STONE_COUNT_BY_CATEGORY[cat] || 2;
      } else {
        const n = parseInt(data.stoneCount, 10);
        const sc = Number.isNaN(n) ? -1 : n;
        if (!VALID_STONE_COUNTS.has(sc)) errors.push('invalid stoneCount');
        else cleaned.stoneCount = sc;
      }
    }
  } else {
    if (cleaned.diamondKind === undefined) cleaned.diamondKind = 'white';
    if (cleaned.diamondShape === undefined) cleaned.diamondShape = 'round';
  }

  if (cat === 'earring') cleaned.stoneCount = 2;
  else if (cat === 'bracelet') delete cleaned.stoneCount;

  if (cat !== 'chain' && !partial) {
    const shape = cleaned.diamondShape || 'round';
    if (cleaned.carat && shape !== 'round' && !isShapeCaratAllowed(cleaned.carat, shape)) {
      errors.push('non-round diamond shapes require carat 0.30 or above');
    }
  }

  if (cleaned.category === 'pendant') {
    cleaned.includeChain = includeChain;
    if (includeChain) {
      if (!data.chainProductId) {
        if (!partial) errors.push('chainProductId is required');
      } else {
        cleaned.chainProductId = String(data.chainProductId);
      }
      if (data.chainGold == null || data.chainGold === '') {
        if (!partial) errors.push('chainGold is required');
      } else if (!VALID_GOLDS.has(String(data.chainGold))) {
        errors.push('invalid chainGold');
      } else {
        cleaned.chainGold = String(data.chainGold);
      }
      if (data.chainColor == null || data.chainColor === '') {
        if (!partial) errors.push('chainColor is required');
      } else if (!VALID_COLORS.has(String(data.chainColor))) {
        errors.push('invalid chainColor');
      } else {
        cleaned.chainColor = String(data.chainColor);
      }
      const length = cleanChainLength('chainLength', { required: !partial });
      if (length != null) cleaned.chainLength = length;
    }
  }

  return { cleaned, error: errors.length ? errors.join('; ') : null };
}

const PRODUCT_NAME_MAX = 150;
const PRODUCT_DESC_MAX = 2000;

/** Validates an admin product create/edit JSON payload.
 * variants: [{gold, carat, weightChin, manualPriceTwd?}], images: [{color, url}].
 */
function validateProductFields(body) {
  const errors = [];
  const cleaned = {};
  body = body || {};

  const category = String(body.category || '').trim();
  if (!VALID_CATEGORIES.has(category)) errors.push('invalid category');
  else cleaned.category = category;

  const nameZh = String(body.nameZh || '').trim();
  if (!nameZh) errors.push('nameZh is required');
  else if (nameZh.length > PRODUCT_NAME_MAX) errors.push(`nameZh must be at most ${PRODUCT_NAME_MAX} characters`);
  else cleaned.nameZh = nameZh;

  const nameEn = String(body.nameEn || '').trim();
  if (nameEn.length > PRODUCT_NAME_MAX) errors.push(`nameEn must be at most ${PRODUCT_NAME_MAX} characters`);
  cleaned.nameEn = nameEn.slice(0, PRODUCT_NAME_MAX) || null;

  const descZh = String(body.descriptionZh || '').trim();
  const descEn = String(body.descriptionEn || '').trim();
  if (descZh.length > PRODUCT_DESC_MAX || descEn.length > PRODUCT_DESC_MAX) {
    errors.push(`description must be at most ${PRODUCT_DESC_MAX} characters`);
  }
  cleaned.descriptionZh = descZh || null;
  cleaned.descriptionEn = descEn || null;

  const defaultColor = String(body.defaultColor || 'white').trim();
  if (!VALID_COLORS.has(defaultColor)) errors.push('invalid defaultColor');
  else cleaned.defaultColor = defaultColor;

  cleaned.isPublished = !!body.isPublished;

  const validCarats = category === 'chain' ? VALID_CARATS_CHAIN : VALID_CARATS;
  const variants = [];
  const seenKeys = new Set();
  for (const v of (body.variants || [])) {
    const gold = String(v.gold || '').trim();
    const carat = String(v.carat || '').trim();
    if (!VALID_GOLDS.has(gold)) { errors.push(`invalid variant metal: ${gold || '(empty)'}`); continue; }
    if (!validCarats.has(carat)) { errors.push(`invalid variant carat: ${carat || '(empty)'}`); continue; }
    const weightChin = Number(v.weightChin);
    if (!(weightChin > 0)) { errors.push(`invalid weight for ${gold}/${carat}`); continue; }
    let manualPriceTwd = null;
    if (v.manualPriceTwd != null && v.manualPriceTwd !== '') {
      const p = Number(v.manualPriceTwd);
      if (!(p >= 0)) { errors.push(`invalid manual price for ${gold}/${carat}`); continue; }
      manualPriceTwd = p;
    }
    const key = `${gold}:${carat}`;
    if (seenKeys.has(key)) { errors.push(`duplicate variant: ${gold} / ${carat}`); continue; }
    seenKeys.add(key);
    variants.push({ gold, carat, weightChin, manualPriceTwd });
  }
  if (!variants.length) errors.push('at least one variant is required');
  cleaned.variants = variants;

  const images = (body.images || []).filter((img) => img && img.color && img.url);
  const finalColors = new Set(images.map((img) => img.color));
  if (!finalColors.size) errors.push('at least one product image is required');
  else if (VALID_COLORS.has(cleaned.defaultColor) && !finalColors.has(cleaned.defaultColor)) {
    errors.push('default color must have at least one image');
  }
  cleaned.images = images;

  return { cleaned, error: errors.length ? errors.join('; ') : null };
}

module.exports = {
  VALID_CATEGORIES, VALID_CARATS, VALID_CARATS_CHAIN, VALID_GOLDS, VALID_COLORS,
  CHAIN_LENGTH_OPTIONS_CM, BRACELET_LENGTH_OPTIONS_CM,
  validateSubmissionFields, validateProductFields,
};
