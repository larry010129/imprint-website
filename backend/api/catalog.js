/* GET: public product catalog grouped by category — format matches the
 * imprint-calculator shop frontend (script.js expects { categories, categoryOrder }). */
const { sql } = require('../lib/db');
const { applyCors } = require('../lib/cors');

const CATEGORY_DISPLAY_ORDER = ['pendant', 'ring', 'earring', 'bracelet', 'chain'];
const METAL_DISPLAY_ORDER = ['9k', '14k', '18k', 'pt950', 's925'];

function sortGolds(golds) {
  const order = Object.fromEntries(METAL_DISPLAY_ORDER.map((g, i) => [g, i]));
  return [...golds].sort((a, b) => (order[a] ?? 99) - (order[b] ?? 99));
}

function resolveImageUrl(filePath) {
  if (!filePath) return '';
  if (filePath.startsWith('http://') || filePath.startsWith('https://')) return filePath;
  if (filePath.startsWith('/')) return filePath;
  return '/' + filePath;
}

function buildCatalogProduct(product, variants, images) {
  const golds = sortGolds(new Set(variants.map((v) => v.gold)));
  const carats = [...new Set(variants.map((v) => v.carat))].sort();

  const weights = {};
  const manualPrices = {};
  for (const v of variants) {
    (weights[v.gold] ||= {})[v.carat] = Number(v.weight_chin);
    if (v.manual_price_twd != null) {
      (manualPrices[v.gold] ||= {})[v.carat] = Number(v.manual_price_twd);
    }
  }

  const imagesByColor = {};
  for (const img of images) {
    (imagesByColor[img.color] ||= []).push(resolveImageUrl(img.file_path));
  }

  return {
    id: product.id,
    nameZh: product.name_zh,
    nameEn: product.name_en,
    descriptionZh: product.description_zh,
    descriptionEn: product.description_en,
    defaultColor: product.default_color,
    golds,
    carats,
    colors: Object.keys(imagesByColor).sort(),
    images: imagesByColor,
    weights,
    manualPrices,
    draft: !product.is_published,
  };
}

module.exports = async function handler(req, res) {
  if (applyCors(req, res)) return;
  if (req.method !== 'GET') return res.status(405).json({ error: 'method not allowed' });

  const category = req.query && req.query.category;

  try {
    const products = category
      ? await sql`select * from products where is_published = true and category = ${category} order by sort_order, created_at`
      : await sql`select * from products where is_published = true order by sort_order, created_at`;

    if (!products.length) {
      return res.status(200).json({ categories: {}, categoryOrder: [] });
    }

    const productIds = products.map((p) => p.id);
    const [variants, images] = await Promise.all([
      sql`select * from product_variants where product_id = any(${productIds})`,
      sql`select * from product_images where product_id = any(${productIds}) order by sort_order`,
    ]);

    const variantsByProduct = {};
    for (const v of variants) (variantsByProduct[v.product_id] ||= []).push(v);
    const imagesByProduct = {};
    for (const img of images) (imagesByProduct[img.product_id] ||= []).push(img);

    const categories = {};
    for (const p of products) {
      const entry = buildCatalogProduct(
        p,
        variantsByProduct[p.id] || [],
        imagesByProduct[p.id] || [],
      );
      (categories[p.category] ||= []).push(entry);
    }

    const present = Object.keys(categories);
    const categoryOrder = CATEGORY_DISPLAY_ORDER.filter((c) => present.includes(c))
      .concat(present.filter((c) => !CATEGORY_DISPLAY_ORDER.includes(c)));

    res.status(200).json({ categories, categoryOrder });
  } catch (err) {
    console.error('[catalog]', err);
    res.status(500).json({ error: '載入商品失敗' });
  }
};
