/* 銘印鑽石｜首頁「客戶故事」輪播
   說明給工程師:
   - 正中間那則故事清晰置中，左右兩則模糊縮小(.st-slide.is-active 切換，CSS 負責模糊/縮放)。
   - 真無限循環：在首尾各複製一張(clone)接在真實清單前後，滑到複製張時，
     等這一次的轉場結束，再「無動畫」瞬間跳回對應的真實位置，視覺上就像一直往同一個
     方向滑、永遠不會撞牆或往回跳。
   - 每次轉場都用「一次性」的 transitionend 監聽 + 逾時保險雙保險偵測完成，兩者哪個先觸發
     就以它為準且互相清掉對方，避免分頁背景執行、轉場被中斷等情況下重複觸發或永遠卡住。
   - 動畫進行中(isAnimating)一律擋掉新的 next/prev/連點/拖曳/點側邊卡片，等目前這次轉場
     真正結束才能再切換，才不會讓 index 跑出邊界、造成清晰/模糊狀態和實際捲動位置對不上。
   - 置中位置用 JS 量測實際像素(offsetLeft + offsetWidth/2)再置中，任何裝置寬度都精準置中。
*/
(function () {
  'use strict';

  var root = document.querySelector('.st-carousel');
  if (!root) return;

  var viewport = root.querySelector('.st-viewport');
  var track = root.querySelector('.st-track');
  if (!viewport || !track) return;

  var realSlides = Array.prototype.slice.call(track.children);
  var realCount = realSlides.length;
  if (!realCount) return;

  var dots = Array.prototype.slice.call(root.querySelectorAll('.st-dot'));
  var prevBtn = root.querySelector('.st-prev');
  var nextBtn = root.querySelector('.st-next');

  /* 首尾各補一張複製投影片，撐出「無限循環」的視覺假象 */
  var firstClone = realSlides[0].cloneNode(true);
  var lastClone = realSlides[realCount - 1].cloneNode(true);
  firstClone.setAttribute('aria-hidden', 'true');
  lastClone.setAttribute('aria-hidden', 'true');
  track.insertBefore(lastClone, realSlides[0]);
  track.appendChild(firstClone);

  var slides = Array.prototype.slice.call(track.children); // [lastClone, ...real, firstClone]
  var lastIdx = slides.length - 1;
  var index = 1; // 對應 realSlides[0]
  var isAnimating = false;
  var ANIM_FALLBACK_MS = 900; // 明顯大於 CSS 轉場時間(.65s)，transitionend 沒觸發時的保險回退

  function realIndex() {
    return ((index - 1) % realCount + realCount) % realCount;
  }

  function updateActiveAndDots() {
    var ri = realIndex();
    slides.forEach(function (s, i) {
      s.classList.toggle('is-active', i === index);
    });
    dots.forEach(function (d, i) {
      d.classList.toggle('is-active', i === ri);
      d.setAttribute('aria-selected', i === ri ? 'true' : 'false');
    });
  }

  function moveTo(withTransition) {
    var active = slides[index];
    var viewportCenter = viewport.clientWidth / 2;
    var slideCenter = active.offsetLeft + active.offsetWidth / 2;
    var offset = viewportCenter - slideCenter;
    track.style.transition = withTransition === false ? 'none' : '';
    track.style.transform = 'translateX(' + offset + 'px)';
  }

  /* 滑到(或超過，若快速連續觸發)複製張的邊界時，無動畫瞬間跳回對應的真實位置；
     用 >= / <= 而非 === 判斷邊界，即使一次跨過邊界也不會漏接。
     重置 index 後一定要重新呼叫 updateActiveAndDots()：is-active 是掛在複製張(index=0或
     lastIdx)上的，若只搬動 track 位置(moveTo)而不重新標記 is-active，畫面中央會變成
     「沒有任何一張是清晰的」，看起來就像全部模糊掉。
     重新標記 is-active 這件事本身，也會讓「複製張→真實張」這兩張(視覺上長得一模一樣)
     各自重新跑一次 .5s 的模糊/縮放轉場——複製張從清晰變模糊、真實張從模糊變清晰，
     肉眼會看到中央那張閃一下。用 no-anim 暫時關掉投影片自己的轉場，跳完之後強制
     reflow 再拿掉，才會是真正無感的瞬間切換。 */
  function settleBoundary() {
    if (index >= lastIdx) {
      index = 1;
    } else if (index <= 0) {
      index = lastIdx - 1;
    } else {
      return;
    }
    slides.forEach(function (s) { s.classList.add('no-anim'); });
    updateActiveAndDots();
    moveTo(false);
    void track.offsetWidth; // 強制 reflow，確保 no-anim 移除後轉場會重新生效
    slides.forEach(function (s) { s.classList.remove('no-anim'); });
  }

  function render(withTransition) {
    updateActiveAndDots();
    moveTo(withTransition);

    if (withTransition === false) {
      isAnimating = false;
      return;
    }

    isAnimating = true;
    var settled = false;
    var fallbackTimer;

    function finish() {
      if (settled) return;
      settled = true;
      clearTimeout(fallbackTimer);
      track.removeEventListener('transitionend', onTransitionEnd);
      isAnimating = false;
      settleBoundary();
    }
    function onTransitionEnd(e) {
      if (e.target === track && e.propertyName === 'transform') finish();
    }

    track.addEventListener('transitionend', onTransitionEnd);
    fallbackTimer = setTimeout(finish, ANIM_FALLBACK_MS);
  }

  function next() { if (isAnimating) return; index++; render(); }
  function prev() { if (isAnimating) return; index--; render(); }
  function goToReal(ri) {
    if (isAnimating) return;
    index = ri + 1;
    render();
  }

  if (prevBtn) prevBtn.addEventListener('click', function () { prev(); });
  if (nextBtn) nextBtn.addEventListener('click', function () { next(); });
  dots.forEach(function (d) {
    d.addEventListener('click', function () {
      goToReal(parseInt(d.getAttribute('data-index'), 10) || 0);
    });
  });
  /* 點側邊模糊的鄰卡：一律走 next()/prev()，跟按鈕共用同一套狀態機，不直接跳 index */
  slides.forEach(function (s, i) {
    s.addEventListener('click', function () {
      if (i === index + 1) { next(); }
      else if (i === index - 1) { prev(); }
    });
  });

  viewport.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowLeft') prev();
    if (e.key === 'ArrowRight') next();
  });

  var dragging = false, startX = 0, deltaX = 0, baseOffset = 0;
  track.addEventListener('pointerdown', function (e) {
    if (isAnimating) return;
    dragging = true; startX = e.clientX; deltaX = 0;
    var active = slides[index];
    baseOffset = viewport.clientWidth / 2 - (active.offsetLeft + active.offsetWidth / 2);
    track.style.transition = 'none';
    try { track.setPointerCapture(e.pointerId); } catch (err) {}
  });
  track.addEventListener('pointermove', function (e) {
    if (!dragging) return;
    deltaX = e.clientX - startX;
    track.style.transform = 'translateX(' + (baseOffset + deltaX) + 'px)';
  });
  function dragEnd() {
    if (!dragging) return;
    dragging = false;
    var threshold = 60;
    if (Math.abs(deltaX) > threshold) {
      if (deltaX < 0) { next(); } else { prev(); }
    } else {
      render(false);
    }
    deltaX = 0;
  }
  track.addEventListener('pointerup', dragEnd);
  track.addEventListener('pointercancel', dragEnd);

  var resizeTimer = null;
  window.addEventListener('resize', function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function () { moveTo(false); }, 100);
  });

  render(false);
})();
