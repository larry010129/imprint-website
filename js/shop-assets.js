/* Shop product images — maps catalog ids to files under shop/image/. */
(function (global) {
  'use strict';

  /** From shop/calculator/index.html */
  var IMAGE_ROOT = (global.shopConfig && global.shopConfig.imageRoot) || '../image/';

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
    pendant: '墜子/項墜A.jpg',
    ring: '戒指/戒指A.jpg',
    earring: '耳飾/耳飾A.jpg',
    bracelet: '手鍊/手鍊A.jpg',
    chain: '鍊條/斗圓鍊.jpg',
  };

  /** Per-style thumbs for the style grid (white metal preview). */
  var STYLE_THUMB = {
    'pendant-A': '墜子/項墜A.jpg',
    'pendant-B': '墜子/項墜B.jpg',
    'pendant-C': '墜子/項墜C.jpg',
    'ring-A': '戒指/戒指A.jpg',
    'ring-B': '戒指/戒指B.jpg',
    'ring-C': '戒指/戒指C.jpg',
    'earring-A': '耳飾/耳飾A.jpg',
    'bracelet-A': '手鍊/手鍊A.jpg',
    'bracelet-B': '手鍊/手鍊B.jpg',
    'bracelet-C': '手鍊/手鍊C.jpg',
    'chain-A': '鍊條/斗圓鍊.jpg',
    'chain-B': '鍊條/斗圓鍊K玫瑰_0.jpg',
    'chain-C': '鍊條/斗圓鍊K黃_0.jpg',
  };

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

  function stylePngPath(category, style, color) {
    var c = resolveColor(color);
    var dir = COLOR_DIR[c];
    var suffix = COLOR_SUFFIX[c];
    var basename;

    if (category === 'chain') {
      basename = CHAIN_BASENAME[style];
      if (!basename) return '';
      var overrideKey = dir + '|' + basename + '|' + suffix;
      if (FILE_OVERRIDES[overrideKey]) {
        return joinPath(dir + '/' + FILE_OVERRIDES[overrideKey]);
      }
      return joinPath(dir + '/' + basename + '_' + suffix + '.png');
    }

    var zh = CATEGORY_ZH[category];
    if (!zh) return '';
    basename = zh + style;
    return joinPath(dir + '/' + basename + '_' + suffix + '.png');
  }

  function productImage(productId, color, defaultColor) {
    var parsed = parseProductId(productId);
    if (!parsed) return '';
    var path = stylePngPath(parsed.category, parsed.style, resolveColor(color, defaultColor));
    if (path) return path;
    return styleThumb(productId);
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
    var rel = STYLE_THUMB[productId];
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
    productImages: productImages,
    attachImageFallback: attachImageFallback,
  };
})(window);
