/* Shop product images — maps catalog ids to files under shop-product/.
 *
 * Layout:
 *   shop-product/silver|gold|rose_gold/  — PNG renders ({品項}{style}_{metal}[_diamond].png)
 *   shop-product/thumbs/{category}/      — JPG grid previews (A.jpg, B.jpg, C.jpg)
 */
(function (global) {
  'use strict';

  var IMAGE_ROOT = (global.shopConfig && global.shopConfig.imageRoot) || '/static/images/shop-product/';

  var CATEGORY_ZH = {
    pendant: '項墜',
    ring: '戒指',
    earring: '耳飾',
    bracelet: '手鍊',
  };

  var COLOR_DIR = {
    white: 'silver',
    yellow: 'gold',
    rose: 'rose_gold',
  };

  var COLOR_SUFFIX = {
    white: 'silver',
    yellow: 'gold',
    rose: 'rose',
  };

  var DIAMOND_COLORS = ['white', 'yellow', 'blue', 'pink'];

  function buildImageSlotKey(metal, diamond) {
    return String(metal) + '-' + String(diamond);
  }

  /** Parse admin/catalog image slot key → { metal, diamond } or null for legacy/custom. */
  function parseImageSlotKey(key) {
    var parts = String(key || '').split('-');
    if (parts.length >= 2 && COLOR_DIR[parts[0]] && DIAMOND_COLORS.indexOf(parts[1]) >= 0) {
      return { metal: parts[0], diamond: parts[1] };
    }
    if (COLOR_DIR[key]) return { metal: key, diamond: 'white' };
    return null;
  }

  /** Lookup order: metal-diamond → metal (legacy white diamond). */
  function imageSlotKeysForLookup(metal, diamond) {
    var m = resolveColor(metal);
    var d = diamond && DIAMOND_COLORS.indexOf(diamond) >= 0 ? diamond : 'white';
    var keys = [];
    if (d !== 'white') keys.push(buildImageSlotKey(m, d));
    keys.push(m);
    if (d === 'white') keys.push(buildImageSlotKey(m, 'white'));
    return keys;
  }

  /** chain-A = 斗圓鍊 K白, chain-B = K玫瑰, chain-C = K黃 */
  var CHAIN_BASENAME = {
    A: '斗圓鍊',
    B: '斗圓鍊K玫瑰',
    C: '斗圓鍊K黃',
  };

  /** Known filename quirks in shop/image */
  var FILE_OVERRIDES = {
    'rose_gold|斗圓鍊K玫瑰|rose': '斗圓鍊K玫瑰_silver2.png',
  };

  var CATEGORY_THUMB = {
    pendant: 'thumbs/pendant/A.jpg',
    ring: 'thumbs/ring/A.jpg',
    earring: 'thumbs/earring/A.jpg',
    bracelet: 'thumbs/bracelet/A.jpg',
    chain: 'thumbs/chain/A.jpg',
  };

  function styleThumbRel(productId) {
    var parsed = parseProductId(productId);
    if (!parsed) return '';
    return 'thumbs/' + parsed.category + '/' + parsed.style + '.jpg';
  }

  function parseProductId(productId) {
    var m = String(productId || '').match(/^([a-z]+)-([A-C])$/i);
    if (!m) return null;
    return { category: m[1].toLowerCase(), style: m[2].toUpperCase() };
  }

  function resolveColor(color, fallback) {
    if (color && COLOR_DIR[color]) return color;
    if (fallback && COLOR_DIR[fallback]) return fallback;
    return 'white';
  }

  function joinPath(relative) {
    return IMAGE_ROOT + relative.replace(/^\//, '');
  }

  function stylePngPath(category, style, color, diamondColor) {
    var c = resolveColor(color);
    var dir = COLOR_DIR[c];
    var suffix = COLOR_SUFFIX[c];
    var d = diamondColor && DIAMOND_COLORS.indexOf(diamondColor) >= 0 ? diamondColor : 'white';
    var basename;

    if (category === 'chain') {
      basename = CHAIN_BASENAME[style];
      if (!basename) return '';
      var overrideKey = dir + '|' + basename + '|' + suffix;
      if (FILE_OVERRIDES[overrideKey]) {
        return joinPath(dir + '/' + FILE_OVERRIDES[overrideKey]);
      }
      var chainFile = basename + '_' + suffix + (d !== 'white' ? '_' + d : '') + '.png';
      return joinPath(dir + '/' + chainFile);
    }

    var zh = CATEGORY_ZH[category];
    if (!zh) return '';
    basename = zh + style;
    var file = basename + '_' + suffix + (d !== 'white' ? '_' + d : '') + '.png';
    return joinPath(dir + '/' + file);
  }

  function productImage(productId, color, defaultColor, diamondColor) {
    var parsed = parseProductId(productId);
    if (!parsed) return '';
    var path = stylePngPath(
      parsed.category,
      parsed.style,
      resolveColor(color, defaultColor),
      diamondColor,
    );
    if (path) return path;
    return styleThumb(productId);
  }

  function productImageWithFallback(productId, color, defaultColor, diamondColor) {
    var d = diamondColor && DIAMOND_COLORS.indexOf(diamondColor) >= 0 ? diamondColor : 'white';
    var primary = productImage(productId, color, defaultColor, d);
    if (!primary || d === 'white') return primary;
    var fallback = productImage(productId, color, defaultColor, 'white');
    return { primary: primary, fallback: fallback };
  }

  function productImages(productId, defaultColor) {
    var parsed = parseProductId(productId);
    if (!parsed) return [];
    return ['white', 'yellow', 'rose']
      .map(function (c) { return stylePngPath(parsed.category, parsed.style, c); })
      .filter(Boolean);
  }

  function categoryThumb(category) {
    var rel = CATEGORY_THUMB[category];
    return rel ? joinPath(rel) : '';
  }

  function styleThumb(productId) {
    var rel = styleThumbRel(productId);
    if (rel) return joinPath(rel);
    var parsed = parseProductId(productId);
    if (!parsed) return categoryThumb('');
    return stylePngPath(parsed.category, parsed.style, 'white')
      || categoryThumb(parsed.category);
  }

  function attachImageFallback(img, fallbackUrl) {
    if (!img || !fallbackUrl) return;
    img.addEventListener('error', function onErr() {
      img.removeEventListener('error', onErr);
      if (img.src !== fallbackUrl) img.src = fallbackUrl;
    }, { once: true });
  }

  global.ShopAssets = {
    imageRoot: IMAGE_ROOT,
    categoryThumb: categoryThumb,
    styleThumb: styleThumb,
    productImage: productImage,
    productImageWithFallback: productImageWithFallback,
    productImages: productImages,
    attachImageFallback: attachImageFallback,
    buildImageSlotKey: buildImageSlotKey,
    parseImageSlotKey: parseImageSlotKey,
    imageSlotKeysForLookup: imageSlotKeysForLookup,
    DIAMOND_COLORS: DIAMOND_COLORS,
  };
})(window);
