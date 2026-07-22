/* 銘印鑽石官網前端互動
   window.imgFallback（圖片載入失敗的後備方案）刻意寫在每頁 <head> 的 inline <script> 裡，
   而不是這支檔案：main.js 在 </body> 前才載入，圖片卻在 <head> 解析完就開始下載，
   若失敗事件在 main.js 執行前就先觸發，這裡才定義會來不及。 */
(function () {
  'use strict';

  function whenSiteReady(fn) {
    if (window.__siteLayoutReady) {
      window.__siteLayoutReady.then(fn);
      return;
    }
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', fn);
    } else {
      fn();
    }
  }

  whenSiteReady(function () {

  /* ---------- 同頁錨點平滑捲動（首頁 hero CTA 等） ---------- */
  function scrollToPageSection(id) {
    var target = document.getElementById(id);
    if (!target) return false;
    var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var nav = document.querySelector('.nav');
    var offset = (nav ? nav.offsetHeight : 0) + 16;
    var top = target.getBoundingClientRect().top + window.pageYOffset - offset;
    window.scrollTo({ top: Math.max(0, top), behavior: reduceMotion ? 'auto' : 'smooth' });
    if (history.replaceState) history.replaceState(null, '', '#' + id);
    return true;
  }

  document.addEventListener('click', function (e) {
    var scrollBtn = e.target.closest('[data-scroll-to]');
    if (scrollBtn) {
      e.preventDefault();
      e.stopImmediatePropagation();
      scrollToPageSection(scrollBtn.getAttribute('data-scroll-to'));
      return;
    }
    var hashLink = e.target.closest('a[href^="#"]');
    if (!hashLink) return;
    var hash = hashLink.getAttribute('href');
    if (!hash || hash.length < 2) return;
    var id = hash.slice(1);
    if (!document.getElementById(id)) return;
    e.preventDefault();
    e.stopImmediatePropagation();
    scrollToPageSection(id);
  }, true);

  /* ---------- 導覽列:捲動陰影（React SiteNav 已處理；略過有 data-site-nav-root 的頁面） ---------- */
  if (!document.querySelector('[data-site-nav-root]')) {
    var nav = document.querySelector('.nav');
    function onNavScroll() {
      if (!nav) return;
      nav.classList.toggle('is-scrolled', window.scrollY > 10);
    }
    if (nav) {
      window.addEventListener('scroll', onNavScroll, { passive: true });
      onNavScroll();
    }
  }

  /* ---------- 手機選單 ---------- */
  var burger = document.querySelector('.nav-burger');
  var menu = document.querySelector('.nav-menu');
  if (burger && menu) {
    burger.addEventListener('click', function () {
      burger.classList.toggle('is-open');
      menu.classList.toggle('is-open');
      document.body.style.overflow = menu.classList.contains('is-open') ? 'hidden' : '';
    });
    // 手機版:主選單文字本身是連結，點了直接跳轉；
    // 子選單改由旁邊獨立的展開鈕(.dd-toggle)收合，兩者互不干擾
    menu.querySelectorAll('.nav-item').forEach(function (item) {
      var toggle = item.querySelector(':scope > .dd-toggle');
      if (!toggle) return;
      toggle.addEventListener('click', function () {
        var willOpen = !item.classList.contains('is-open');
        item.classList.toggle('is-open', willOpen);
        toggle.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
      });
    });
    menu.querySelectorAll('.dropdown a').forEach(function (a) {
      a.addEventListener('click', function () {
        if (window.innerWidth <= 860 && a.getAttribute('href') && a.getAttribute('href') !== '#') {
          burger.classList.remove('is-open');
          menu.classList.remove('is-open');
          document.body.style.overflow = '';
        }
      });
    });
  }

  /* ---------- 進場顯示 ---------- */
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) {
          en.target.classList.add('is-in');
          io.unobserve(en.target);
        }
      });
    }, { threshold: 0.12 });
    document.querySelectorAll('.reveal').forEach(function (el) { io.observe(el); });
  } else {
    document.querySelectorAll('.reveal').forEach(function (el) { el.classList.add('is-in'); });
  }

  /* ---------- FAQ 手風琴（略過 React 島） ---------- */
  if (!document.querySelector('[data-faq-root]')) {
  document.querySelectorAll('.faq-item').forEach(function (item) {
    var q = item.querySelector('.faq-q');
    var a = item.querySelector('.faq-a');
    q.addEventListener('click', function () {
      var open = item.classList.contains('is-open');
      document.querySelectorAll('.faq-item.is-open').forEach(function (other) {
        other.classList.remove('is-open');
        other.querySelector('.faq-a').style.maxHeight = null;
        other.querySelector('.faq-q').setAttribute('aria-expanded', 'false');
      });
      if (!open) {
        item.classList.add('is-open');
        a.style.maxHeight = a.scrollHeight + 'px';
        q.setAttribute('aria-expanded', 'true');
      }
    });
  });
  }

  /* ---------- Hero 輪播:箭頭/圓點/拖曳滑動/自動播放 ---------- */
  /* CMS 可動態替換 #hcTrack 後呼叫 ImprintHeroCarousel.reinit() */
  window.ImprintHeroCarousel = (function () {
    var abortCtrl = null;
    var hcTimer = null;

    function destroy() {
      if (hcTimer) { clearInterval(hcTimer); hcTimer = null; }
      if (abortCtrl) { abortCtrl.abort(); abortCtrl = null; }
    }

    function init() {
      var hcViewport = document.getElementById('hcViewport');
      var hcTrack = document.getElementById('hcTrack');
      if (!hcViewport || !hcTrack) return;

      destroy();
      abortCtrl = new AbortController();
      var signal = abortCtrl.signal;

      var hcSlides = Array.prototype.slice.call(hcTrack.children);
      var dotsWrap = hcViewport.querySelector('.hc-dots');
      var hcPrev = document.getElementById('hcPrev');
      var hcNext = document.getElementById('hcNext');
      var hcCount = hcSlides.length;
      var hcIndex = 0;
      var hcAutoplayMs = 6500;
      var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

      if (!hcCount) return;

      if (dotsWrap) {
        dotsWrap.innerHTML = hcSlides.map(function (s, i) {
          var label = (s.querySelector('.gh-hero__title') || {}).textContent || ('投影片 ' + (i + 1));
          label = String(label).replace(/\s+/g, ' ').trim() || ('投影片 ' + (i + 1));
          return '<button type="button" class="hc-dot' + (i === 0 ? ' is-active' : '') +
            '" data-index="' + i + '" role="tab" aria-label="' + label.replace(/"/g, '') +
            '" aria-selected="' + (i === 0 ? 'true' : 'false') + '"></button>';
        }).join('');
      }
      var hcDots = Array.prototype.slice.call(hcViewport.querySelectorAll('.hc-dot'));

      function hcRender(withTransition) {
        hcSlides.forEach(function (s, i) {
          var wasActive = s.classList.contains('is-active');
          var willBeActive = i === hcIndex;
          var img = s.querySelector('.hc-media img');
          if (withTransition === false) { s.classList.add('no-anim'); }
          s.classList.toggle('is-active', willBeActive);

          var isFirstRender = withTransition === false;
          var reveals = s.querySelectorAll('.reveal');
          if (willBeActive && (!wasActive || isFirstRender)) {
            reveals.forEach(function (el) { el.classList.remove('is-in'); });
            void s.offsetWidth;
            reveals.forEach(function (el) { el.classList.add('is-in'); });
            if (img) {
              img.classList.add('kb-reset');
              img.style.transform = 'scale(1)';
              void img.offsetWidth;
              img.classList.remove('kb-reset');
              img.style.transform = 'scale(1.09)';
            }
          } else if (!willBeActive && wasActive) {
            reveals.forEach(function (el) { el.classList.remove('is-in'); });
          }
        });
        if (withTransition === false) {
          void hcTrack.offsetWidth;
          hcSlides.forEach(function (s) { s.classList.remove('no-anim'); });
        }
        hcDots.forEach(function (d, i) {
          d.classList.toggle('is-active', i === hcIndex);
          d.setAttribute('aria-selected', i === hcIndex ? 'true' : 'false');
        });
      }

      function hcGoTo(i) {
        hcIndex = (i + hcCount) % hcCount;
        hcRender();
      }
      function hcNextSlide() { hcGoTo(hcIndex + 1); }
      function hcPrevSlide() { hcGoTo(hcIndex - 1); }

      function hcStopAuto() { if (hcTimer) { clearInterval(hcTimer); hcTimer = null; } }
      function hcStartAuto() {
        if (reduceMotion) return;
        hcStopAuto();
        hcTimer = setInterval(hcNextSlide, hcAutoplayMs);
      }

      if (hcPrev) hcPrev.addEventListener('click', function () { hcPrevSlide(); hcStartAuto(); }, { signal: signal });
      if (hcNext) hcNext.addEventListener('click', function () { hcNextSlide(); hcStartAuto(); }, { signal: signal });
      hcDots.forEach(function (d) {
        d.addEventListener('click', function () { hcGoTo(parseInt(d.dataset.index, 10)); hcStartAuto(); }, { signal: signal });
      });
      hcViewport.addEventListener('keydown', function (e) {
        if (e.key === 'ArrowLeft') { hcPrevSlide(); hcStartAuto(); }
        if (e.key === 'ArrowRight') { hcNextSlide(); hcStartAuto(); }
      }, { signal: signal });
      hcViewport.addEventListener('mouseenter', hcStopAuto, { signal: signal });
      hcViewport.addEventListener('mouseleave', hcStartAuto, { signal: signal });

      var dragging = false, dragStartX = 0, dragDeltaX = 0, dragSuppressClick = false;
      hcTrack.addEventListener('pointerdown', function (e) {
        if (e.target.closest('a, button, input, select, textarea, label, [data-scroll-to]')) return;
        dragging = true; dragStartX = e.clientX; dragDeltaX = 0;
        hcTrack.setPointerCapture(e.pointerId);
        hcStopAuto();
      }, { signal: signal });
      hcTrack.addEventListener('pointermove', function (e) {
        if (!dragging) return;
        dragDeltaX = e.clientX - dragStartX;
      }, { signal: signal });
      function hcDragEnd() {
        if (!dragging) return;
        dragging = false;
        var threshold = hcViewport.offsetWidth * 0.12;
        if (Math.abs(dragDeltaX) > threshold) {
          dragSuppressClick = true;
          if (dragDeltaX < 0) { hcNextSlide(); } else { hcPrevSlide(); }
        } else {
          hcRender();
        }
        hcStartAuto();
      }
      hcTrack.addEventListener('pointerup', hcDragEnd, { signal: signal });
      hcTrack.addEventListener('pointercancel', hcDragEnd, { signal: signal });
      hcTrack.addEventListener('click', function (e) {
        if (e.target.closest('a, button, input, select, textarea, label, [data-scroll-to]')) return;
        if (dragSuppressClick) { e.preventDefault(); e.stopPropagation(); dragSuppressClick = false; }
      }, { capture: true, signal: signal });

      hcRender(false);
      hcStartAuto();
    }

    return { init: init, reinit: init, destroy: destroy };
  })();

  window.ImprintHeroCarousel.init();

  /* ---------- 鑽戒滾動翻轉(兩幕精簡版) ---------- */
  var track = document.getElementById('rfTrack');
  if (track && !(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches)) {
    var ring = document.getElementById('rfRing');
    var shine = document.getElementById('rfShine');
    var caps = track.querySelectorAll('.ringflip-caption');
    var current = 0, target = 0, ticking = false;

    var clamp = function (v, a, b) { return v < a ? a : v > b ? b : v; };
    var ease = function (t) { return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t; };

    var progress = function () {
      var r = track.getBoundingClientRect();
      var total = r.height - window.innerHeight;
      return total > 0 ? clamp(-r.top / total, 0, 1) : 0;
    };

    var render = function () {
      current += (target - current) * 0.09;
      if (Math.abs(target - current) < 0.0005) current = target;
      var p = current, rx = 0, ry = 0, scale = 1, t;

      if (p < 0.5) {          /* 第一幕:左右翻轉一圈 */
        t = ease(p / 0.5);
        ry = 360 * t;
        scale = 1 + 0.08 * Math.sin(Math.PI * t);
      } else {                 /* 第二幕:上下翻轉一圈 */
        t = ease((p - 0.5) / 0.5);
        rx = 360 * t;
        scale = 1 + 0.08 * Math.sin(Math.PI * t);
      }
      ring.style.transform = 'rotateX(' + rx.toFixed(2) + 'deg) rotateY(' + ry.toFixed(2) + 'deg) scale(' + scale.toFixed(3) + ')';

      var seg = (p * 2) % 1;
      shine.style.transform = 'translateX(' + (-120 + 240 * ease(seg)) + '%)';
      shine.style.opacity = Math.sin(Math.PI * seg).toFixed(2);

      var step = p < 0.5 ? 0 : 1;
      caps.forEach(function (c, i) {
        c.classList.toggle('is-on', i === step && p > 0.02);
      });

      if (current !== target) { requestAnimationFrame(render); } else { ticking = false; }
    };

    var onScroll = function () {
      target = progress();
      if (!ticking) { ticking = true; requestAnimationFrame(render); }
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);
    onScroll();
  }

  }); /* whenSiteReady */
})();
