/* 銘印鑽石｜商品詳情頁主圖 + 縮圖選擇 + 滑鼠移入放大
   說明給工程師:
   - 點下方縮圖，換主圖 <img src>。主圖故意不用 <picture><source webp>：這張圖會被
     動態換 src，若留著 source，瀏覽器會一直鎖定那個 source 網址不放，改 img.src 也
     不會生效。
   - 每次換圖前都要重置 dataset.fbStep，讓 imgFallback(見各頁 <head>)的
     jpg→png→jpeg 嘗試順序重新從頭開始；若不重置，沿用上一張圖片試到一半的進度，
     很容易在切到另一張「副檔名其實不同」的圖片時，直接跳過正確的副檔名而失敗，
     造成「縮圖點了卻切不回來」的狀況。
   - 滑鼠移到主圖上時，依游標在圖片中的相對位置設定 transform-origin，
     再放大(scale)圖片，做出「放大鏡跟著游標」的效果；滑出時還原。
*/
(function () {
  'use strict';

  Array.prototype.forEach.call(document.querySelectorAll('[data-pd-gallery]'), function (root) {
    var main = root.querySelector('.pd-main');
    var mainImg = root.querySelector('#pdMainImg') || root.querySelector('.pd-main img');
    var thumbs = Array.prototype.slice.call(root.querySelectorAll('.pd-thumb'));
    if (!main || !mainImg) return;

    thumbs.forEach(function (thumb) {
      thumb.addEventListener('click', function () {
        var jpg = thumb.getAttribute('data-jpg');
        if (!jpg) return;
        delete mainImg.dataset.fbStep;
        mainImg.src = jpg;
        var thumbImg = thumb.querySelector('img');
        if (thumbImg) mainImg.alt = thumbImg.alt;
        thumbs.forEach(function (t) { t.classList.toggle('is-active', t === thumb); });
      });
    });

    main.addEventListener('mousemove', function (e) {
      var rect = main.getBoundingClientRect();
      var x = ((e.clientX - rect.left) / rect.width) * 100;
      var y = ((e.clientY - rect.top) / rect.height) * 100;
      mainImg.style.transformOrigin = x + '% ' + y + '%';
      main.classList.add('is-zoomed');
    });
    main.addEventListener('mouseleave', function () {
      main.classList.remove('is-zoomed');
      mainImg.style.transformOrigin = 'center';
    });
  });
})();
