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
    // chain-B has no 斗圓鍊K玫瑰_rose.png — reuse the correct rose cable shot
    'rose_gold|斗圓鍊K玫瑰|rose': '斗圓鍊_rose.png',
  };

  var CATEGORY_THUMB = {
    diamond: '/static/images/diamonds/colors/catalog-cluster.png',
    pendant: 'thumbs/pendant/A.jpg',
    ring: 'thumbs/ring/A.jpg',
    earring: 'thumbs/earring/A.jpg',
    bracelet: 'thumbs/bracelet/A.jpg',
    chain: 'thumbs/chain/A.jpg',
  };

  function categoryThumb(category) {
    var rel = CATEGORY_THUMB[category];
    if (!rel) return '';
    if (/^https?:\/\//i.test(rel) || rel.charAt(0) === '/') return rel;
    return joinPath(rel);
  }

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
    var rel = String(relative || '').replace(/^\//, '').replace(/\\/g, '/');
    var slash = rel.lastIndexOf('/');
    var dir = slash >= 0 ? rel.slice(0, slash + 1) : '';
    var file = slash >= 0 ? rel.slice(slash + 1) : rel;
    return IMAGE_ROOT + dir + encodeURIComponent(file);
  }

  function stylePngPath(category, style, color, diamondColor, opts) {
    opts = opts || {};
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
    var chainC = opts.chainColor ? resolveColor(opts.chainColor) : null;
    var chainSuffix = chainC ? COLOR_SUFFIX[chainC] : null;
    if (chainSuffix && chainC !== c && !opts.pendantOnly && !opts.chainOnly) {
      var combo = basename + '_' + suffix + '_chain_' + chainSuffix + (d !== 'white' ? '_' + d : '') + '.png';
      return joinPath(dir + '/' + combo);
    }
    var file = basename + '_' + suffix + (d !== 'white' ? '_' + d : '') + (opts.pendantOnly ? '_only' : '') + (opts.chainOnly ? '_chain' : '') + '.png';
    return joinPath(dir + '/' + file);
  }

  function productImage(productId, color, defaultColor, diamondColor, opts) {
    opts = opts || {};
    var parsed = parseProductId(productId);
    if (!parsed) return '';
    var resolved = resolveColor(color, defaultColor);
    var d = diamondColor;
    if (opts.chainOnly) d = 'white';
    var path = stylePngPath(parsed.category, parsed.style, resolved, d, opts);
    if (path) return path;
    if (opts.pendantOnly) {
      // Missing `_only` — still prefer same-metal full PNG over wrong cross-metal combo
      path = stylePngPath(parsed.category, parsed.style, resolved, diamondColor, {});
      if (path) return path;
      return styleThumb(productId);
    }
    if (opts.chainOnly) {
      // ponytail: layer asset missing — fall back to full necklace PNG
      path = stylePngPath(parsed.category, parsed.style, resolved, diamondColor, {});
      if (path) return path;
    }
    return styleThumb(productId);
  }

  function productImageWithFallback(productId, color, defaultColor, diamondColor, opts) {
    var d = diamondColor && DIAMOND_COLORS.indexOf(diamondColor) >= 0 ? diamondColor : 'white';
    var primary = productImage(productId, color, defaultColor, d, opts);
    if (!primary || d === 'white') return primary;
    var fallback = productImage(productId, color, defaultColor, 'white', opts);
    return { primary: primary, fallback: fallback };
  }

  function productImages(productId, defaultColor) {
    var parsed = parseProductId(productId);
    if (!parsed) return [];
    return ['white', 'yellow', 'rose']
      .map(function (c) { return stylePngPath(parsed.category, parsed.style, c); })
      .filter(Boolean);
  }

  function styleThumb(productId) {
    var parsed = parseProductId(productId);
    // Chain A/B/C are color-locked styles — prefer the matching metal PNG over stale JPG thumbs
    if (parsed && parsed.category === 'chain') {
      var chainColor = { A: 'white', B: 'rose', C: 'yellow' }[parsed.style] || 'white';
      var chainPng = stylePngPath('chain', parsed.style, chainColor);
      if (chainPng) return chainPng;
    }
    var rel = styleThumbRel(productId);
    if (rel) return joinPath(rel);
    if (!parsed) return categoryThumb('');
    return stylePngPath(parsed.category, parsed.style, 'white')
      || categoryThumb(parsed.category);
  }

  /** Ordered PNG candidates: metal+fancy → silver+fancy → metal+white → thumb */
  function productImageResolve(productId, color, defaultColor, diamondColor, opts) {
    opts = opts || {};
    var parsed = parseProductId(productId);
    if (!parsed) return { src: '', fallbacks: [] };
    var resolved = resolveColor(color, defaultColor);
    var d = diamondColor && DIAMOND_COLORS.indexOf(diamondColor) >= 0 ? diamondColor : 'white';
    if (opts.chainOnly) d = 'white';
    var chain = [];

    function push(path) {
      if (path && chain.indexOf(path) < 0) chain.push(path);
    }

    push(stylePngPath(parsed.category, parsed.style, resolved, d, opts));
    if (opts.pendantOnly) {
      if (d !== 'white') {
        push(stylePngPath(parsed.category, parsed.style, resolved, 'white', { pendantOnly: true }));
      }
      // Do not fall back to full necklace / cross-metal combo for 「僅墜子」
      return { src: chain[0] || '', fallbacks: chain.slice(1) };
    }
    if (d !== 'white') {
      if (resolved !== 'white') {
        // ponytail: rose/yellow metal fancy PNG missing (e.g. 耳飾) — show silver fancy until assets exist
        push(stylePngPath(parsed.category, parsed.style, 'white', d, opts));
      }
      push(stylePngPath(parsed.category, parsed.style, resolved, 'white', opts));
    }
    // Cross-metal chain combo missing → same-metal full necklace, then thumb.
    // Never fall back to bare "_chain.png" / "_only.png" layer crops here.
    if (opts.chainColor && resolveColor(opts.chainColor) !== resolved) {
      push(stylePngPath(parsed.category, parsed.style, resolved, d, {}));
      if (d !== 'white') {
        push(stylePngPath(parsed.category, parsed.style, resolved, 'white', {}));
      }
    }
    if (!chain.length) {
      var thumb = styleThumb(productId);
      if (thumb) push(thumb);
    }
    return { src: chain[0] || '', fallbacks: chain.slice(1) };
  }

  function attachImageFallback(img, fallbackUrl) {
    if (!img || !fallbackUrl) return;
    img.addEventListener('error', function onErr() {
      img.removeEventListener('error', onErr);
      if (img.src !== fallbackUrl) img.src = fallbackUrl;
    }, { once: true });
  }

  function attachImageFallbackChain(img, fallbackUrls) {
    if (!img || !fallbackUrls || !fallbackUrls.length) return;
    var queue = fallbackUrls.filter(Boolean);
    if (!queue.length) return;
    var idx = 0;
    img.onerror = function onErr() {
      if (idx >= queue.length) {
        img.onerror = null;
        return;
      }
      img.src = queue[idx++];
    };
  }

  global.ShopAssets = {
    imageRoot: IMAGE_ROOT,
    categoryThumb: categoryThumb,
    styleThumb: styleThumb,
    productImage: productImage,
    productImageResolve: productImageResolve,
    productImageWithFallback: productImageWithFallback,
    productImages: productImages,
    attachImageFallback: attachImageFallback,
    attachImageFallbackChain: attachImageFallbackChain,
    buildImageSlotKey: buildImageSlotKey,
    parseImageSlotKey: parseImageSlotKey,
    imageSlotKeysForLookup: imageSlotKeysForLookup,
    DIAMOND_COLORS: DIAMOND_COLORS,
  };
})(window);
