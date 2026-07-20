/* Shared product image URL resolver for admin panels */
(function (global) {
  'use strict';

  var CATEGORIES = { pendant: 1, ring: 1, earring: 1, bracelet: 1, chain: 1 };
  var STYLE_ID = /^([a-z]+)-([A-C])$/i;
  var UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

  function resolve(path) {
    if (!path) return '';
    var p = String(path).trim();
    if (p.indexOf('http') === 0) return p;
    if (p.indexOf('/static/') === 0) return p;
    if (p.indexOf('/') === 0) return p;

    if (p.indexOf('images/shop/') === 0) return '/static/' + p;
    if (p.indexOf('static/') === 0) return '/' + p;
    if (p.indexOf('images/') === 0) return '/static/' + p;
    return '/' + p;
  }

  function categoryFallback(category) {
    var cat = String(category || '').toLowerCase();
    if (global.ShopAssets) {
      var thumb = global.ShopAssets.categoryThumb(cat);
      if (thumb) return thumb;
    }
    // Real thumbs live under shop-product/; legacy shop/categories/*.svg removed
    return CATEGORIES[cat] ? '/static/images/shop-product/thumbs/' + cat + '/A.jpg' : '';
  }

  function orderFallback(category, styleType) {
    var cat = String(category || '').toLowerCase();
    if (!styleType) return categoryFallback(cat);
    var style = String(styleType).trim();
    if (UUID.test(style)) return categoryFallback(cat);
    if (style.length === 1 && 'ABC'.indexOf(style) >= 0 && cat) {
      return '/static/images/shop/styles/' + cat + '-' + style + '.svg';
    }
    var m = style.match(STYLE_ID);
    if (m) return '/static/images/shop/styles/' + m[1].toLowerCase() + '-' + m[2].toUpperCase() + '.svg';
    return categoryFallback(cat);
  }

  var STYLE_KEY = /(?:^|\/)(pendant|ring|earring|bracelet|chain)-([A-C])\.(?:svg|png|jpe?g|webp)$/i;

  function styleKeyFromPath(path) {
    var m = String(path || '').match(STYLE_KEY);
    if (!m) return '';
    return m[1].toLowerCase() + '-' + m[2].toUpperCase();
  }

  /** Prefer uploaded/photo assets; map SVG catalog paths to shop-product renders. */
  function productPhoto(path, color) {
    var url = resolve(path);
    if (!url) return '';
    if (/\.(png|jpe?g|webp)$/i.test(url)) return url;
    var styleKey = styleKeyFromPath(path) || styleKeyFromPath(url);
    if (styleKey && global.ShopAssets) {
      var real = global.ShopAssets.productImage(styleKey, color, color);
      if (real) return real;
    }
    return url;
  }

  function styleKeyFromCategoryStyle(category, styleType) {
    var cat = String(category || '').toLowerCase();
    var style = String(styleType || '').trim();
    if (!cat || !style || UUID.test(style)) return '';
    if (style.length === 1 && 'ABC'.indexOf(style) >= 0) return cat + '-' + style;
    var m = style.match(STYLE_ID);
    if (m) return m[1].toLowerCase() + '-' + m[2].toUpperCase();
    return '';
  }

  /** Order thumbs — same real-image rules as 商品上架 productPhoto. */
  function orderPhoto(imageUrl, category, styleType, color) {
    var c = color || 'white';
    if (imageUrl) {
      var photo = productPhoto(imageUrl, c);
      if (!/\.svg($|\?)/i.test(photo)) return photo;
    }
    var styleKey = styleKeyFromPath(imageUrl) || styleKeyFromCategoryStyle(category, styleType);
    if (styleKey && global.ShopAssets) {
      var real = global.ShopAssets.productImage(styleKey, c, c);
      if (real) return real;
    }
    if (global.ShopAssets) {
      var thumb = global.ShopAssets.categoryThumb(category);
      if (thumb) return thumb;
    }
    return imageUrl ? resolve(imageUrl) : categoryFallback(category);
  }

  global.AdminImageUrls = {
    resolve: resolve,
    orderFallback: orderFallback,
    categoryFallback: categoryFallback,
    productPhoto: productPhoto,
    orderPhoto: orderPhoto,
  };
})(window);
