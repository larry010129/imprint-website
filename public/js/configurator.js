/* 銘印鑽石｜五大系列客製選單邏輯
   說明給工程師:
   - 這是純前端試算工具,沒有串接後端或金流,不會送出訂單。
   - 價格資料統一從 js/pricing-config.js 的 window.ImprintPricing 讀取,
     後台「價格設定」頁調整過的金額(存在瀏覽器 localStorage)會自動套用。
   - 鑽石金額只有在「顏色×克拉」有資料時才會顯示(例如彩鑽 0.10/0.20 目前
     無法製作,就不會生出數字);非圓形切工會在此基礎上加價(預設 10%,
     可在後台調整),且需 0.30 克拉以上才允許選取。
   - 飾品戒台費用依「飾品款式 × 材質」查表相加,裸鑽則為 0。
   - 總金額 = 鑽石金額 + 戒台費用 + 刻字費用,三項都是可在後台調整的數字。
*/
(function () {
  'use strict';

  var form = document.getElementById('cfgForm');
  if (!form) return;

  var pricing = (window.ImprintPricing ? window.ImprintPricing.getAll() : null);
  if (!pricing) {
    console.warn('ImprintPricing 未載入,請確認 pricing-config.js 有在 configurator.js 之前引入。');
    return;
  }

  var seriesName = form.dataset.seriesName || 'DNA 紀念鑽石';
  var NON_ROUND_MIN_CARAT = 0.30;

  var els = {
    carat: form.querySelectorAll('input[name="carat"]'),
    color: form.querySelectorAll('input[name="color"]'),
    shape: form.querySelectorAll('input[name="shape"]'),
    jewelry: form.querySelectorAll('input[name="jewelry"]'),
    metal: form.querySelectorAll('input[name="metal"]'),
    finish: form.querySelectorAll('input[name="finish"]'),
    engrave: document.getElementById('cfgEngrave'),
    engraveCount: document.getElementById('cfgEngraveCount'),
    engravePreview: document.getElementById('cfgEngravePreview'),
    shapeWarning: document.getElementById('cfgShapeWarning'),
    qty: document.getElementById('cfgQty'),
    finishNote: document.getElementById('cfgFinishNote'),
  };

  var ringSizeEl = null;
  var ringSizeSummary = null;

  function isRingJewelryForm() {
    var jewelryInput = checkedValue(els.jewelry);
    return jewelryInput && jewelryInput.value === 'ring';
  }

  function ensureRingSizeUI() {
    if (!isRingJewelryForm()) return;
    if (ringSizeEl) return;

    var finishGroup = form.querySelector('input[name="finish"]');
    finishGroup = finishGroup ? finishGroup.closest('.cfg-group') : null;
    var wrap = document.createElement('div');
    wrap.className = 'cfg-group';
    wrap.id = 'cfgRingSizeGroup';
    wrap.innerHTML =
      '<div class="cfg-group-head"><h3>國際戒圍</h3><span class="cfg-note">#9 以上每大半號加 NT$500（未稅）</span></div>' +
      '<div class="cfg-options cfg-options--select">' +
      '<label class="cfg-select-label" for="cfgRingSize">戒圍</label>' +
      '<select id="cfgRingSize" name="ringSize" aria-label="國際戒圍">' +
      '<option value="">請選擇</option>' +
      [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18].map(function (n) {
        return '<option value="' + n + '">#' + n + '</option>';
      }).join('') +
      '</select></div>';

    if (finishGroup && finishGroup.parentNode) {
      finishGroup.parentNode.insertBefore(wrap, finishGroup.nextSibling);
    } else {
      form.appendChild(wrap);
    }
    ringSizeEl = document.getElementById('cfgRingSize');
    ringSizeEl.addEventListener('change', render);

    var summaryHost = document.querySelector('.cfg-summary');
    if (summaryHost) {
      var row = document.createElement('div');
      row.className = 'cfg-summary-row';
      row.innerHTML = '<span class="k">戒圍</span><span class="v" id="sumRingSize">未選擇</span>';
      var anchor = document.getElementById('sumFinish');
      anchor = anchor ? anchor.closest('.cfg-summary-row') : null;
      if (anchor && anchor.parentNode) {
        anchor.parentNode.insertBefore(row, anchor.nextSibling);
      } else {
        summaryHost.appendChild(row);
      }
      ringSizeSummary = document.getElementById('sumRingSize');
    }
  }

  ensureRingSizeUI();

  var summary = {
    series: document.getElementById('sumSeries'),
    carat: document.getElementById('sumCarat'),
    color: document.getElementById('sumColor'),
    shape: document.getElementById('sumShape'),
    jewelry: document.getElementById('sumJewelry'),
    metal: document.getElementById('sumMetal'),
    finish: document.getElementById('sumFinish'),
    engrave: document.getElementById('sumEngrave'),
    qty: document.getElementById('sumQty'),
    diamondPrice: document.getElementById('sumDiamondPrice'),
    mountingNote: document.getElementById('sumMountingNote'),
    breakdown: document.getElementById('sumBreakdown'),
    diamondLine: document.getElementById('sumLineDiamond'),
    mountingLine: document.getElementById('sumLineMounting'),
    engraveLine: document.getElementById('sumLineEngrave'),
    totalLine: document.getElementById('sumLineTotal'),
  };

  var copyBtn = document.getElementById('cfgCopyBtn');
  var copyHint = document.getElementById('cfgCopyHint');

  function checkedValue(list) {
    for (var i = 0; i < list.length; i++) { if (list[i].checked) return list[i]; }
    return null;
  }
  function labelText(input) {
    if (!input) return '未選擇';
    var label = form.querySelector('label[for="' + input.id + '"]');
    if (!label) return input.value;
    var t = label.querySelector('.t');
    return t ? t.textContent : label.textContent.trim();
  }

  function formatMoney(n) {
    return 'NT$ ' + n.toLocaleString('en-US');
  }

  /* 9K金／PT950鉑金／純銀只提供白色成色：鎖定並強制切到白K金，18K／14K仍可任選三色 */
  var FINISH_WHITE_ONLY_METALS = { '9k': true, 'pt950': true, 'silver': true };

  function applyFinishConstraint(metalVal) {
    if (!els.finish || !els.finish.length) return;
    var onlyWhite = !!FINISH_WHITE_ONLY_METALS[metalVal];
    Array.prototype.forEach.call(els.finish, function (input) {
      var isWhite = input.value === 'white';
      var disable = onlyWhite && !isWhite;
      input.disabled = disable;
      var opt = input.closest('.cfg-opt');
      if (opt) opt.classList.toggle('is-disabled', disable);
    });
    if (onlyWhite) {
      var whiteInput = form.querySelector('input[name="finish"][value="white"]');
      if (whiteInput && !whiteInput.checked) { whiteInput.checked = true; }
    }
    if (els.finishNote) {
      els.finishNote.classList.toggle('hidden', !onlyWhite);
    }
  }

  var lastState = null;

  function render() {
    var caratInput = checkedValue(els.carat);
    var colorInput = checkedValue(els.color);
    var shapeInput = checkedValue(els.shape);
    var jewelryInput = checkedValue(els.jewelry);
    var metalInput = checkedValue(els.metal);
    var metalVal = metalInput ? metalInput.value : '18k';

    applyFinishConstraint(metalVal);
    var finishInput = checkedValue(els.finish);

    var caratVal = caratInput ? caratInput.value : null;
    var colorVal = colorInput ? colorInput.value : 'white';
    var shapeVal = shapeInput ? shapeInput.value : 'round';
    var jewelryVal = jewelryInput ? jewelryInput.value : 'loose';
    var isRound = shapeVal === 'round';

    /* 非圓形切工需 0.30 克拉以上（官網公開規則），否則提示並視為不合規格 */
    var caratNum = caratVal ? parseFloat(caratVal) : 0;
    var isCustomCarat = caratVal === 'custom';
    var shapeInvalid = !isRound && caratVal && !isCustomCarat && caratNum < NON_ROUND_MIN_CARAT;
    if (els.shapeWarning) {
      els.shapeWarning.classList.toggle('hidden', !shapeInvalid);
    }

    if (summary.series) summary.series.textContent = seriesName;
    if (summary.carat) summary.carat.textContent = caratInput ? labelText(caratInput) : '未選擇';
    if (summary.color) summary.color.textContent = colorInput ? labelText(colorInput) : '未選擇';
    if (summary.shape) summary.shape.textContent = shapeInput ? labelText(shapeInput) : '未選擇';
    if (summary.jewelry) summary.jewelry.textContent = jewelryInput ? labelText(jewelryInput) : '未選擇';
    if (summary.metal) summary.metal.textContent = metalInput ? labelText(metalInput) : '未選擇';
    if (summary.finish) summary.finish.textContent = finishInput ? labelText(finishInput) : '未選擇';
    if (ringSizeSummary) {
      ringSizeSummary.textContent = ringSizeEl && ringSizeEl.value
        ? ('#' + ringSizeEl.value)
        : '未選擇';
    }
    var engraveVal = els.engrave ? engraveReadable() : '';
    if (summary.engrave) {
      summary.engrave.textContent = engraveVal ? engraveVal : '無';
    }

    var qtyVal = els.qty ? (parseInt(els.qty.value, 10) || 1) : 1;
    if (qtyVal < 1) qtyVal = 1;
    if (summary.qty) summary.qty.textContent = qtyVal + ' 顆';

    /* ---- 試算 ---- */
    /* 鑽石總價(含多顆珍藏方案查表、非圓形切工加價)統一交給 pricing-config.js
       的 computeDiamondPrice 處理，邏輯移植自 imprint-calculator 正式報價系統。 */
    var diamondPrice = null;
    var canCompute = false;

    if (!shapeInvalid && caratVal && !isCustomCarat) {
      diamondPrice = window.ImprintPricing.computeDiamondPrice(pricing, colorVal, caratVal, shapeVal, qtyVal);
      canCompute = diamondPrice != null;
    }

    /* 戒台費用(mounting)是未稅金額,比照鑽石牌價已含稅的慣例,顯示/加總時另外加 5% 稅
       (稅率規則移植自 imprint-calculator 的 order_pricing.py：金屬+工錢加稅,鑽石牌價不再加稅)。
       戒指另計戒圍加價（#9 以上每大半號 NT$500 未稅），邏輯與 diamond-calculator 同步。 */
    var mountingFeePreTax = 0;
    var ringSizeVal = ringSizeEl ? parseFloat(ringSizeEl.value) : NaN;
    if (jewelryVal !== 'loose') {
      if (window.ImprintJewelryMounting && jewelryVal === 'ring') {
        mountingFeePreTax = window.ImprintJewelryMounting.mountingFeePreTax(
          pricing, jewelryVal, metalVal, isNaN(ringSizeVal) ? null : ringSizeVal
        );
      } else {
        var mTable = pricing.mounting[jewelryVal] || {};
        mountingFeePreTax = mTable[metalVal] != null ? mTable[metalVal] : 0;
      }
    }
    var mountingFee = jewelryVal !== 'loose'
      ? Math.round(mountingFeePreTax * (1 + (pricing.taxRate || 0)))
      : 0;
    var engraveFee = engraveVal ? (pricing.engraveFee || 0) : 0;
    var total = canCompute ? diamondPrice + mountingFee + engraveFee : null;

    if (summary.diamondPrice) {
      if (shapeInvalid) {
        summary.diamondPrice.textContent = '請先調整克拉數或形狀';
      } else if (isCustomCarat) {
        summary.diamondPrice.textContent = '請洽顧問專屬報價';
      } else if (canCompute) {
        summary.diamondPrice.textContent = formatMoney(total);
      } else {
        summary.diamondPrice.textContent = '此規格暫無法製作，請洽顧問';
      }
    }

    if (summary.breakdown) {
      summary.breakdown.classList.toggle('hidden', !canCompute);
    }
    if (summary.diamondLine) {
      if (diamondPrice == null) {
        summary.diamondLine.textContent = '-';
      } else {
        summary.diamondLine.textContent = qtyVal > 1
          ? formatMoney(diamondPrice) + '（共 ' + qtyVal + ' 顆）'
          : formatMoney(diamondPrice);
      }
    }
    if (summary.mountingLine) {
      summary.mountingLine.textContent = jewelryVal === 'loose' ? '不適用（裸鑽）' : formatMoney(mountingFee);
    }
    if (summary.engraveLine) {
      summary.engraveLine.textContent = engraveVal ? formatMoney(engraveFee) : '未刻字';
    }
    if (summary.totalLine) {
      summary.totalLine.textContent = total != null ? formatMoney(total) : '-';
    }

    if (summary.mountingNote) {
      summary.mountingNote.textContent = '以上為系統試算金額，僅供參考，正式報價請與顧問確認';
    }

    lastState = {
      series: seriesName,
      carat: caratVal,
      caratLabel: caratInput ? labelText(caratInput) : null,
      color: colorVal,
      shape: shapeVal,
      jewelry: jewelryVal,
      jewelryLabel: jewelryInput ? labelText(jewelryInput) : null,
      metal: metalVal,
      finish: finishInput ? finishInput.value : null,
      ringSize: ringSizeEl && ringSizeEl.value ? parseFloat(ringSizeEl.value) : null,
      quantity: qtyVal,
      engrave: engraveVal || null,
      estimatedPrice: total
    };
  }

  /* 給「送出估價需求」等其他前端功能讀取目前試算狀態用 */
  window.ImprintConfigurator = window.ImprintConfigurator || {};
  window.ImprintConfigurator.getState = function () {
    return lastState;
  };

  [].concat(
    Array.prototype.slice.call(els.carat),
    Array.prototype.slice.call(els.color),
    Array.prototype.slice.call(els.shape),
    Array.prototype.slice.call(els.jewelry),
    Array.prototype.slice.call(els.metal),
    Array.prototype.slice.call(els.finish)
  ).forEach(function (input) {
    input.addEventListener('change', render);
  });

  if (els.qty) {
    /* 多顆珍藏方案只支援 2/3/4 顆整組報價(官網未公開 5 顆以上，見 pricing-config.js)。 */
    var MAX_QTY = 4;
    els.qty.addEventListener('input', function () {
      var n = parseInt(els.qty.value, 10);
      if (!isNaN(n) && n > MAX_QTY) { els.qty.value = String(MAX_QTY); }
      render();
    });
    els.qty.addEventListener('change', function () {
      var n = parseInt(els.qty.value, 10);
      if (isNaN(n) || n < 1) { els.qty.value = '1'; }
      render();
    });
  }

  var MAX_ENGRAVE = 12;
  var engraveCtrl = null;

  function engraveReadable() {
    if (engraveCtrl) return engraveCtrl.readable();
    if (els.engrave && window.GirdleEngrave) return window.GirdleEngrave.readable(els.engrave);
    return '';
  }

  if (els.engrave && window.GirdleEngrave) {
    engraveCtrl = window.GirdleEngrave.init({
      input: els.engrave,
      countEl: els.engraveCount,
      previewEl: els.engravePreview,
      emblemsRoot: form,
      max: MAX_ENGRAVE,
      onChange: function () { render(); }
    });
  }

  if (copyBtn) {
    copyBtn.addEventListener('click', function () {
      var lines = ['【銘印鑽石｜客製規格】', '系列：' + (summary.series ? summary.series.textContent : seriesName)];
      lines.push('克拉數：' + (summary.carat ? summary.carat.textContent : '-'));
      lines.push('鑽石顏色：' + (summary.color ? summary.color.textContent : '-'));
      lines.push('鑽石形狀：' + (summary.shape ? summary.shape.textContent : '-'));
      if (summary.qty) lines.push('顆數：' + summary.qty.textContent);
      if (summary.jewelry) lines.push('飾品選擇：' + summary.jewelry.textContent);
      if (summary.metal) lines.push('材質：' + summary.metal.textContent);
      if (summary.finish) lines.push('成色：' + summary.finish.textContent);
      lines.push('腰圍刻字：' + (summary.engrave ? summary.engrave.textContent : '無'));
      lines.push('系統試算總額：' + (summary.diamondPrice ? summary.diamondPrice.textContent : '-') + '（僅供參考）');
      lines = lines.join('\n');
      var done = function () {
        if (copyHint) {
          copyHint.textContent = '已複製！貼到 LINE 傳給顧問即可';
          setTimeout(function () { copyHint.textContent = ''; }, 4000);
        }
      };
      var fail = function () {
        if (copyHint) copyHint.textContent = '複製失敗，請手動截圖畫面';
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(lines).then(done, fail);
      } else {
        fail();
      }
    });
  }

  render();

  /* 頁面先用快取價格立刻顯示，等 Supabase 的最新價格回來後(通常一瞬間)
     再重新整理一次試算，確保最後看到的是全站同步的正式價格。 */
  if (window.ImprintPricing && window.ImprintPricing.ready && typeof window.ImprintPricing.ready.then === 'function') {
    window.ImprintPricing.ready.then(function () {
      pricing = window.ImprintPricing.getAll();
      render();
    });
  }
})();
