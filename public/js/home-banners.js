/* Home hero banners — fetch /api/banners, replace #hcTrack, reinit carousel */
(function () {
  'use strict';

  var track = document.getElementById('hcTrack');
  if (!track) return;

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function formatLead(lead) {
    var t = esc(lead);
    return t.replace(/\bDNA\b/g, '<span class="gh-dna">DNA</span>');
  }

  function formatTitle(title, index) {
    var text = esc(title);
    var splitAt = text.indexOf('，');
    if (index !== 0 || splitAt < 0) return text;
    return text.slice(0, splitAt + 1) + '<em>' + text.slice(splitAt + 1) + '</em>';
  }

  function ctaSecondary(b) {
    var label = String(b.cta_secondary_label || '').trim();
    var href = String(b.cta_secondary_href || '').trim();
    if (!label || !href) return '';
    if (href.charAt(0) === '#') {
      return '<button type="button" class="gh-btn gh-btn--ghost" data-scroll-to="' +
        esc(href.slice(1)) + '">' + esc(label) + '</button>';
    }
    return '<a class="gh-btn gh-btn--ghost" href="' + esc(href) + '">' + esc(label) + '</a>';
  }

  function slideHtml(b, index) {
    var tone = b.tone || 'warm';
    var align = b.align || (index === 3 ? 'right' : 'left');
    var titleTag = index === 0 ? 'h1' : 'h2';
    var loading = index === 0
      ? 'loading="eager" fetchpriority="high"'
      : 'loading="lazy"';
    var sourceAttr = index === 0 ? 'srcset' : 'data-srcset';
    var imageAttr = index === 0 ? 'src' : 'data-src';

    /* Mobile ≤900px: prefer CMS mobile crop, else local optimized memorial, else webp, else jpg. */
    var mobileValue = String(b.image_url_mobile || '').trim();
    var mappedLocal = '';
    if (index === 0 && /imprint-diamond-family-memorial\.(jpe?g|webp)/i.test(String(b.image_url || b.image_webp || ''))) {
      mappedLocal = '/static/images/hero/imprint-diamond-family-memorial-800w.webp 800w, /static/images/hero/imprint-diamond-family-memorial-960w.webp 960w, /static/images/hero/imprint-diamond-family-memorial-1200w.webp 1200w';
    }
    var mobileSrc = mobileValue || mappedLocal || String(b.image_webp || b.image_url || '');
    var mobileIsWebp = /\.webp(\s|\?|$)/i.test(mobileSrc);
    var mobileSource = '<source media="(max-width:900px)" ' + sourceAttr + '="' + esc(mobileSrc) + '"' +
      (mobileIsWebp ? ' type="image/webp"' : '') + ' sizes="100vw">';

    var webp = b.image_webp
      ? '<source ' + sourceAttr + '="' + esc(b.image_webp) + '" type="image/webp" sizes="100vw">'
      : '';
    var primary = '';
    if (b.cta_primary_label && b.cta_primary_href) {
      primary = '<a class="gh-btn gh-btn--primary" href="' + esc(b.cta_primary_href) + '">' +
        esc(b.cta_primary_label) + '</a>';
    }
    var secondary = ctaSecondary(b);
    var imgSrc = b.image_url || '';
    var imgExtra = '';
    if (index === 0 && mappedLocal) {
      imgSrc = '/static/images/hero/imprint-diamond-family-memorial-800w.webp';
      imgExtra = ' width="800" height="388" sizes="100vw" srcset="' +
        esc(mappedLocal + ', /static/images/hero/imprint-diamond-family-memorial.webp 2400w') + '"';
    } else if (b.image_webp && !mobileValue) {
      imgSrc = b.image_webp;
    }
    return (
      '<li class="hc-slide' + (index === 0 ? ' is-active' : '') +
        '" data-align="' + esc(align) + '" data-tone="' + esc(tone) + '">' +
        '<div class="hc-media"><picture>' +
          mobileSource +
          webp +
          '<img ' + imageAttr + '="' + esc(imgSrc) + '" alt="' + esc(b.image_alt || b.title) + '"' +
          imgExtra + ' ' + loading + ' decoding="async" onerror="imgFallback(this)">' +
        '</picture></div>' +
        '<div class="hc-scrim gh-hc-scrim"></div>' +
        '<div class="container hc-copy gh-hc-copy">' +
          (b.eyebrow ? '<p class="gh-script reveal">' + esc(b.eyebrow) + '</p>' : '') +
          '<' + titleTag + ' class="gh-hero__title' + (index === 0 ? '' : ' reveal reveal-d1') + '">' + formatTitle(b.title, index) + '</' + titleTag + '>' +
          (b.lead ? '<p class="gh-hero__lead reveal reveal-d2">' + formatLead(b.lead) + '</p>' : '') +
          ((primary || secondary)
            ? '<div class="gh-hero__actions reveal reveal-d3">' + primary + secondary + '</div>'
            : '') +
        '</div></li>'
    );
  }

  function apply(list) {
    if (!list.length) return;
    track.innerHTML = list.map(slideHtml).join('');
    if (window.ImprintHeroCarousel && window.ImprintHeroCarousel.reinit) {
      window.ImprintHeroCarousel.reinit();
    }
  }

  function refreshBanners() {
    var base = (typeof window.IMPRINT_API_BASE === 'string' && window.IMPRINT_API_BASE) || '';
    fetch(base + '/api/banners', { credentials: 'same-origin' })
      .then(function (res) { return res.ok ? res.json() : null; })
      .then(function (data) {
        var list = data && Array.isArray(data.banners) ? data.banners : [];
        if (list.length) apply(list);
      })
      .catch(function () { /* keep SSR slides */ });
  }

  function scheduleRefresh() {
    window.setTimeout(function () {
      if ('requestIdleCallback' in window) {
        window.requestIdleCallback(refreshBanners, { timeout: 5000 });
      } else {
        refreshBanners();
      }
    }, 2000);
  }

  if (document.readyState === 'complete') {
    scheduleRefresh();
  } else {
    window.addEventListener('load', scheduleRefresh, { once: true });
  }
})();
