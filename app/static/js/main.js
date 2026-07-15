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

  /* ---------- 導覽列:捲動陰影 ---------- */
  var nav = document.querySelector('.nav');
  function onNavScroll() {
    if (!nav) return;
    nav.classList.toggle('is-scrolled', window.scrollY > 10);
  }
  if (nav) {
    window.addEventListener('scroll', onNavScroll, { passive: true });
    onNavScroll();
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

  /* ---------- FAQ 手風琴 ---------- */
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

  /* ---------- Hero 輪播:箭頭/圓點/拖曳滑動/自動播放 ---------- */
  var hcViewport = document.getElementById('hcViewport');
  if (hcViewport) {
    var hcTrack = document.getElementById('hcTrack');
    var hcSlides = Array.prototype.slice.call(hcTrack.children);
    var hcDots = Array.prototype.slice.call(document.querySelectorAll('.hc-dot'));
    var hcPrev = document.getElementById('hcPrev');
    var hcNext = document.getElementById('hcNext');
    var hcCount = hcSlides.length;
    var hcIndex = 0;
    var hcTimer = null;
    var hcAutoplayMs = 6500;
    var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    function hcRender(withTransition) {
      hcSlides.forEach(function (s, i) {
        var wasActive = s.classList.contains('is-active');
        var willBeActive = i === hcIndex;
        var img = s.querySelector('.hc-media img');
        if (withTransition === false) { s.classList.add('no-anim'); }
        s.classList.toggle('is-active', willBeActive);

        /* 文字進場動畫(.reveal/.is-in)每次「變成中央那張」都要重新播一次，
           不是只在頁面第一次載入時播過就沒了，才會有一直輪播都很有質感的感覺。
           第一張投影片的 is-active 是寫死在 HTML 裡的(沒有 JS 時的優雅降級)，所以第一次
           執行 hcRender 時 wasActive 一定是 true，若只看 !wasActive 會誤判成「本來就是
           使用中」而跳過進場動畫和 Ken Burns 啟動；withTransition === false 只有頁面剛
           載入這一次會是 false，用它來補這個判斷。 */
        var isFirstRender = withTransition === false;
        var reveals = s.querySelectorAll('.reveal');
        if (willBeActive && (!wasActive || isFirstRender)) {
          reveals.forEach(function (el) { el.classList.remove('is-in'); });
          void s.offsetWidth;
          reveals.forEach(function (el) { el.classList.add('is-in'); });

          /* Ken Burns 縮放：每次「變成中央那張」才把圖片瞬間歸零重新放大，
             不然一直輪播下去，圖片會停在上一輪已經放大過的大小，越轉越大。 */
          if (img) {
            img.classList.add('kb-reset');
            img.style.transform = 'scale(1)';
            void img.offsetWidth;
            img.classList.remove('kb-reset');
            img.style.transform = 'scale(1.09)';
          }
        } else if (!willBeActive && wasActive) {
          reveals.forEach(function (el) { el.classList.remove('is-in'); });
          /* 圖片刻意「不」重置 transform：讓它維持淡出當下已經放大到的大小繼續淡出，
             不然一失去 is-active 就會瞬間跳回原始尺寸，變成「先跳回原圖才淡出」。 */
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

    hcPrev.addEventListener('click', function () { hcPrevSlide(); hcStartAuto(); });
    hcNext.addEventListener('click', function () { hcNextSlide(); hcStartAuto(); });
    hcDots.forEach(function (d) {
      d.addEventListener('click', function () { hcGoTo(parseInt(d.dataset.index, 10)); hcStartAuto(); });
    });
    hcViewport.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowLeft') { hcPrevSlide(); hcStartAuto(); }
      if (e.key === 'ArrowRight') { hcNextSlide(); hcStartAuto(); }
    });
    hcViewport.addEventListener('mouseenter', hcStopAuto);
    hcViewport.addEventListener('mouseleave', hcStartAuto);

    // 拖曳/觸控左右滑動：疊圖淡入淡出不適合跟手即時預覽位移，只偵測滑動距離達門檻就切換
    var dragging = false, dragStartX = 0, dragDeltaX = 0, dragSuppressClick = false;
    hcTrack.addEventListener('pointerdown', function (e) {
      if (e.target.closest('a, button, input, select, textarea, label, [data-scroll-to]')) return;
      dragging = true; dragStartX = e.clientX; dragDeltaX = 0;
      hcTrack.setPointerCapture(e.pointerId);
      hcStopAuto();
    });
    hcTrack.addEventListener('pointermove', function (e) {
      if (!dragging) return;
      dragDeltaX = e.clientX - dragStartX;
    });
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
    hcTrack.addEventListener('pointerup', hcDragEnd);
    hcTrack.addEventListener('pointercancel', hcDragEnd);
    hcTrack.addEventListener('click', function (e) {
      if (e.target.closest('a, button, input, select, textarea, label, [data-scroll-to]')) return;
      if (dragSuppressClick) { e.preventDefault(); e.stopPropagation(); dragSuppressClick = false; }
    }, true);

    hcRender(false);
    hcStartAuto();
  }

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
