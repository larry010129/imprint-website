/* Home hero banners — fetch /api/banners, replace #hcTrack, reinit carousel */
(function () {
  'use strict';

  var track = document.getElementById('hcTrack');
  if (!track) return;

  var MEMORIAL_MOBILE =
    '/static/images/hero/imprint-diamond-family-memorial-800w.webp 800w, ' +
    '/static/images/hero/imprint-diamond-family-memorial-960w.webp 960w, ' +
    '/static/images/hero/imprint-diamond-family-memorial-1200w.webp 1200w';
  var MEMORIAL_DESKTOP = '/static/images/hero/imprint-diamond-family-memorial.webp';
  var MEMORIAL_IMG = '/static/images/hero/imprint-diamond-family-memorial-800w.webp';

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function norm(s) {
    return String(s == null ? '' : s).replace(/\s+/g, ' ').trim();
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

  function isMemorial(b) {
    var urls = [b.image_url, b.image_webp, b.image_url_mobile].join(' ');
    return /imprint-diamond-family-memorial/i.test(urls);
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

  /* Slide 0 memorial: always local srcset — never Supabase LCP swap. */
  function memorialPicture(sourceAttr) {
    var mobile = '<source media="(max-width:900px)" ' + sourceAttr + '="' +
      esc(MEMORIAL_MOBILE) + '" type="image/webp" sizes="100vw">';
    var webp = '<source ' + sourceAttr + '="' + esc(MEMORIAL_DESKTOP) +
      '" type="image/webp" sizes="100vw">';
    var imgExtra = ' width="800" height="388" sizes="100vw" srcset="' +
      esc(MEMORIAL_MOBILE + ', ' + MEMORIAL_DESKTOP + ' 2400w') + '"';
    return { mobile: mobile, webp: webp, imgSrc: MEMORIAL_IMG, imgExtra: imgExtra };
  }

  function remotePicture(b, sourceAttr) {
    var mobileValue = String(b.image_url_mobile || '').trim();
    var mobileSrc = mobileValue || String(b.image_webp || b.image_url || '');
    var mobileIsWebp = /\.webp(\s|\?|$)/i.test(mobileSrc);
    var mobile = '<source media="(max-width:900px)" ' + sourceAttr + '="' +
      esc(mobileSrc) + '"' + (mobileIsWebp ? ' type="image/webp"' : '') + ' sizes="100vw">';
    var webp = b.image_webp
      ? '<source ' + sourceAttr + '="' + esc(b.image_webp) + '" type="image/webp" sizes="100vw">'
      : '';
    var imgSrc = b.image_url || '';
    if (b.image_webp && !mobileValue) imgSrc = b.image_webp;
    return { mobile: mobile, webp: webp, imgSrc: imgSrc, imgExtra: '' };
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
    var pic = (index === 0 && isMemorial(b))
      ? memorialPicture(sourceAttr)
      : remotePicture(b, sourceAttr);
    var primary = '';
    if (b.cta_primary_label && b.cta_primary_href) {
      primary = '<a class="gh-btn gh-btn--primary" href="' + esc(b.cta_primary_href) + '">' +
        esc(b.cta_primary_label) + '</a>';
    }
    var secondary = ctaSecondary(b);
    /* First slide: no .reveal on eyebrow/lead/actions (match SSR). */
    var rEyebrow = index === 0 ? '' : ' reveal';
    var rTitle = index === 0 ? '' : ' reveal reveal-d1';
    var rLead = index === 0 ? '' : ' reveal reveal-d2';
    var rActions = index === 0 ? '' : ' reveal reveal-d3';
    return (
      '<li class="hc-slide' + (index === 0 ? ' is-active' : '') +
        '" data-align="' + esc(align) + '" data-tone="' + esc(tone) + '">' +
        '<div class="hc-media"><picture>' +
          pic.mobile +
          pic.webp +
          '<img ' + imageAttr + '="' + esc(pic.imgSrc) + '" alt="' + esc(b.image_alt || b.title) + '"' +
          pic.imgExtra + ' ' + loading + ' decoding="async" onerror="imgFallback(this)">' +
        '</picture></div>' +
        '<div class="hc-scrim gh-hc-scrim"></div>' +
        '<div class="container hc-copy gh-hc-copy">' +
          (b.eyebrow ? '<p class="gh-script' + rEyebrow + '">' + esc(b.eyebrow) + '</p>' : '') +
          '<' + titleTag + ' class="gh-hero__title' + rTitle + '">' + formatTitle(b.title, index) + '</' + titleTag + '>' +
          (b.lead ? '<p class="gh-hero__lead' + rLead + '">' + formatLead(b.lead) + '</p>' : '') +
          ((primary || secondary)
            ? '<div class="gh-hero__actions' + rActions + '">' + primary + secondary + '</div>'
            : '') +
        '</div></li>'
    );
  }

  function bannerSig(b) {
    return [
      norm(b.title),
      norm(b.cta_primary_label),
      norm(b.cta_primary_href),
      norm(b.cta_secondary_label),
      norm(b.cta_secondary_href)
    ].join('|');
  }

  function listSig(list) {
    return list.map(bannerSig).join('||');
  }

  function secondaryHref(el) {
    if (!el) return '';
    var href = el.getAttribute('href');
    if (href) return href;
    var scroll = el.getAttribute('data-scroll-to');
    return scroll ? '#' + scroll : '';
  }

  function ssrSig() {
    var slides = track.querySelectorAll('.hc-slide');
    var parts = [];
    for (var i = 0; i < slides.length; i++) {
      var slide = slides[i];
      var title = slide.querySelector('.gh-hero__title');
      var primary = slide.querySelector('.gh-btn--primary');
      var secondary = slide.querySelector('.gh-btn--ghost');
      parts.push([
        norm(title && title.textContent),
        norm(primary && primary.textContent),
        norm(primary && primary.getAttribute('href')),
        norm(secondary && secondary.textContent),
        norm(secondaryHref(secondary))
      ].join('|'));
    }
    return parts.join('||');
  }

  /* Skip rebuild when CMS titles/CTAs/sort match SSR — keep local LCP DOM. */
  function matchesSsr(list) {
    if (!list.length) return false;
    var slides = track.querySelectorAll('.hc-slide');
    if (slides.length !== list.length) return false;
    return listSig(list) === ssrSig();
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
        if (!list.length || matchesSsr(list)) return;
        apply(list);
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
