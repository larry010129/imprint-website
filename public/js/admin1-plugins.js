/**
 * admin1 plugin store — VS Code style browse list + detail pane.
 * Catalog is static: these features are planned and not built yet.
 */
(function () {
  'use strict';

  var CATEGORIES = ['全部', '訂單', '溝通', '通知', '行銷', '分析', '系統'];

  var CATALOG = [
    {
      id: 'progress-notify', name: '訂製進度通知', icon: '進', category: '通知',
      desc: '培育各階段自動通知客戶',
      long: '訂單進入培育、切磨、鑲嵌、可取貨等階段時，自動以 Email 通知客戶，並帶上查詢進度連結。',
      features: ['階段變更自動發送', '可自訂通知文案', '附「查詢訂製進度」連結'],
    },
    {
      id: 'booking', name: '預約諮詢日曆', icon: '約', category: '行銷',
      desc: '後台月曆管理門市諮詢預約，一個時段一組客人',
      long: '客人在聯絡表單建議的時段會顯示在後台月曆上；管理員可一鍵「安排預約」，也能手動新增、改期、標示完成或取消。同一時段不會被重複預約。',
      features: ['月曆檢視已約／待確認時段', '從諮詢名單一鍵安排預約', '公休日與特別公休設定', '同一時段不重複預約'],
      live: '/admin/booking',
    },
    {
      id: 'review-invite', name: '客戶見證邀請', icon: '評', category: '行銷',
      desc: '交件後自動邀請客戶留下見證',
      long: '訂單完成一段時間後，自動寄出邀請，客戶同意後見證可直接進入「見證」待審清單。',
      features: ['交件後 N 天自動邀請', '客戶可上傳照片', '審核後才上線'],
    },
    {
      id: 'newsletter', name: '電子報', icon: '報', category: '行銷',
      desc: '向諮詢名單與會員發送最新消息',
      long: '整合日誌文章，一鍵整理成電子報寄給訂閱者，並提供退訂連結。',
      features: ['從日誌文章生成', '訂閱／退訂管理', '寄送紀錄'],
    },
    {
      id: 'audit-log', name: '修改紀錄', icon: '錄', category: '系統',
      desc: '記錄誰在何時改了什麼，可還原',
      long: '所有後台的內容修改都留下紀錄，內容改壞時可以一鍵回到先前版本。',
      features: ['變更前後對照', '依人員與頁面篩選', '一鍵還原'],
    },
    {
      id: 'backup', name: '資料備份匯出', icon: '備', category: '系統',
      desc: '定期匯出訂單、會員與內容',
      long: '每週自動產生備份檔，也可以手動匯出訂單與名單成試算表。',
      features: ['排程備份', 'CSV／Excel 匯出', '保留最近 N 份'],
    },
    {
      id: 'order-timeline', name: '訂製流程時間軸', icon: '軸', category: '訂單',
      desc: '每個階段附上照片與影片更新',
      long: '在訂單各階段上傳培育、切磨、鑲嵌的照片或短片，客戶在查詢進度頁就能看到完整時間軸。',
      features: ['階段照片／影片上傳', '客戶端時間軸顯示', '可設定哪些內容對客戶隱藏'],
    },
    {
      id: 'sample-kit', name: '樣本寄送追蹤', icon: '樣', category: '訂單',
      desc: '追蹤毛髮、骨灰樣本的寄送與簽收',
      long: '記錄樣本包何時寄出、何時收到、是否合格，避免樣本遺失或責任不清。',
      features: ['寄送與簽收紀錄', '樣本合格檢查表', '收件自動通知客戶'],
    },
    {
      id: 'quote-pdf', name: '報價單 PDF', icon: '單', category: '訂單',
      desc: '從試算結果一鍵產生正式報價單',
      long: '把客戶的試算配置整理成有品牌版面的 PDF 報價單，可下載或直接寄出，並記錄版本。',
      features: ['品牌版面模板', '報價有效期限', '版本紀錄'],
    },
    {
      id: 'shipping-track', name: '物流追蹤整合', icon: '運', category: '訂單',
      desc: '貨運單號與配送狀態同步到訂單',
      long: '輸入貨運單號後自動抓取配送狀態，客戶在查詢進度頁能看到，取貨完成也會更新訂單。',
      features: ['多家物流支援', '狀態自動同步', '配送異常提醒'],
    },
    {
      id: 'deposit-reminder', name: '訂金與尾款提醒', icon: '款', category: '訂單',
      desc: '訂金、尾款到期自動提醒',
      long: '客製訂單常分訂金與尾款兩階段，此插件記錄應收金額與期限，快到期時提醒你與客戶。',
      features: ['分期金額設定', '到期提醒', '未付款清單'],
    },
    {
      id: 'analytics-dash', name: '流量與轉換儀表板', icon: '析', category: '分析',
      desc: '一頁看懂訪客、諮詢與訂單',
      long: '整合網站流量、諮詢留言與訂單，顯示每週趨勢，讓你知道哪些頁面真的帶來詢問。',
      features: ['每週與每月趨勢', '熱門頁面排行', '可與上期比較'],
    },
    {
      id: 'calc-funnel', name: '試算漏斗分析', icon: '漏', category: '分析',
      desc: '看客戶在試算流程哪一步離開',
      long: '追蹤從選系列、選款式、設定克拉到送出諮詢的每一步，找出最容易流失的環節。',
      features: ['每步驟流失率', '依裝置分開看', '熱門配置排行'],
    },
    {
      id: 'lead-source', name: '諮詢來源追蹤', icon: '源', category: '分析',
      desc: '知道每筆諮詢從哪裡來',
      long: '記錄客戶是從 Google、Instagram、LINE 或推薦連結進站，在諮詢名單上直接顯示來源。',
      features: ['UTM 參數記錄', '來源別諮詢數', '匯出報表'],
    },
    {
      id: 'weekly-report', name: '每週營運週報', icon: '週', category: '分析',
      desc: '每週一自動寄出營運摘要',
      long: '每週固定寄一封摘要：新訂單、新諮詢、待處理事項與熱門頁面，不用登入後台也能掌握。',
      features: ['自動排程寄送', '可選收件人', '自訂摘要項目'],
    },
    {
      id: 'referral', name: '推薦好友獎勵', icon: '薦', category: '行銷',
      desc: '老客戶推薦新客戶可獲得回饋',
      long: '每位會員有專屬推薦連結，新客戶完成訂製後，推薦人獲得優惠券或折抵。',
      features: ['專屬推薦連結', '自動發放回饋', '推薦成效統計'],
    },
    {
      id: 'anniversary', name: '紀念日提醒', icon: '念', category: '行銷',
      desc: '交件週年與生日自動問候客戶',
      long: '記錄客戶的紀念日與交件日，在週年或生日時自動寄出溫暖的問候，維繫長期關係。',
      features: ['週年與生日提醒', '可自訂問候內容', '搭配專屬優惠'],
    },
    {
      id: 'promo-banner', name: '活動彈窗與公告', icon: '告', category: '行銷',
      desc: '排程顯示活動公告與彈窗',
      long: '在指定日期自動顯示或隱藏站內公告橫幅與彈窗，例如展會、公休或優惠活動。',
      features: ['排程上下線', '指定頁面顯示', '關閉後不再打擾'],
    },
    {
      id: 'order-thread', name: '訂單訊息串', icon: '訊', category: '溝通',
      desc: '客戶與門市在訂單旁留言往來',
      long: '客戶在查詢訂製進度頁或會員專區留言，門市在後台訂單旁回覆，所有往來集中在同一處；回覆後客戶會收到 Email 通知並連回訊息串。',
      features: ['訂單與諮詢各自的訊息串', '可傳送照片與檔案', '回覆後 Email 通知客戶'],
    },
    {
      id: 'live-chat', name: '即時線上客服', icon: '聊', category: '溝通',
      desc: '營業時段內的網站即時對話',
      long: '在設定的營業時段顯示對話視窗,由顧問即時回覆;非營業時段自動切換成留言,不會讓客戶空等。',
      features: ['營業時段設定', '離線自動轉留言', '對話紀錄保存與刪除規則'],
    },
    {
      id: 'reply-templates', name: '常用回覆範本', icon: '範', category: '溝通',
      desc: '樣本份量、時程、價格說明一鍵帶入',
      long: '把常被問的問題整理成範本，回覆訊息或諮詢時一鍵帶入並可修改，讓回覆速度與說法保持一致。',
      features: ['範本分類與搜尋', '可插入客戶姓名與訂單資訊', '使用次數統計'],
    },
    {
      id: 'auto-reply', name: '站內自動回覆', icon: '答', category: '溝通',
      desc: '常見問題先由網站自動回答',
      long: '客戶在對話或留言時，先依 FAQ 自動提供答案，找不到答案再轉給顧問，並記錄哪些問題沒有答案。',
      features: ['依 FAQ 自動回答', '轉接真人顧問', '未回答問題清單'],
    },
    {
      id: 'internal-notes', name: '內部備註與交班', icon: '註', category: '溝通',
      desc: '員工之間的訂單備註與交班紀錄',
      long: '在訂單與諮詢旁留下只有員工看得到的備註，並標記需要誰跟進，交班時不遺漏重點。',
      features: ['僅員工可見', '@提及同事', '待跟進清單'],
    },
    {
      id: 'roles', name: '權限與角色', icon: '權', category: '系統',
      desc: '不同員工只能看到需要的功能',
      long: '建立客服、編輯、店長等角色，決定誰能看訂單、改價格或編輯頁面，降低誤操作的風險。',
      features: ['自訂角色', '分頁層級權限', '登入與操作紀錄'],
    },
    {
      id: 'maintenance', name: '維護模式', icon: '修', category: '系統',
      desc: '維護時顯示友善的公告頁',
      long: '更新或維修時一鍵開啟維護頁，顯示預計恢復時間與 LINE 聯絡方式，後台仍可正常登入。',
      features: ['一鍵開關', '自訂公告與恢復時間', '管理員不受影響'],
    },
  ];

  var listEl = document.getElementById('storeList');
  var detailEl = document.getElementById('storeDetail');
  var searchEl = document.getElementById('storeSearch');
  var filtersEl = document.getElementById('storeFilters');
  if (!listEl || !detailEl) return;

  var state = { q: '', category: '全部', selected: CATALOG[0].id };
  /* Live plugin states from the server: { booking: 'disabled' | 'off' | 'on' }; null until loaded. */
  var pluginStates = null;
  var STATE_LABEL = { disabled: '未啟用', off: '已啟用・關閉', on: '已啟用・開啟' };
  var busy = false;

  function stateLabel(p) {
    if (!p.live) return '即將推出';
    if (!pluginStates || !pluginStates[p.id]) return '載入中…';
    return STATE_LABEL[pluginStates[p.id]] || '未知';
  }

  function pluginControlsHtml(p) {
    var s = pluginStates && pluginStates[p.id];
    if (!s) return '<p class="a1-store-lock">載入狀態中…</p>';
    var html;
    if (s === 'disabled') {
      html = '<button type="button" class="a1-store-btn" data-plugin-state="off"' + (busy ? ' disabled' : '') + '>啟用</button>';
    } else {
      html =
        '<label class="a1-switch"><input type="checkbox" role="switch" data-plugin-toggle' +
          (s === 'on' ? ' checked' : '') + (busy ? ' disabled' : '') + '>' +
          '<span class="a1-switch-track" aria-hidden="true"></span>' +
          '<span class="a1-switch-label">' + (s === 'on' ? '開啟中' : '已關閉') + '</span></label>' +
        (s === 'on' ? '<a class="a1-store-btn" href="' + esc(p.live) + '">前往使用</a>' : '') +
        '<button type="button" class="a1-store-btn a1-store-btn--ghost" data-plugin-state="disabled"' +
          (busy ? ' disabled' : '') + '>停用</button>';
    }
    return '<div class="a1-store-actions">' + html + '</div>' +
      '<p class="a1-store-lock">🔒 變更插件狀態需要通行碼</p>' +
      '<p class="a1-store-msg" id="pluginMsg" role="status" hidden></p>';
  }

  function showPluginMsg(text) {
    var el = document.getElementById('pluginMsg');
    if (!el) return;
    el.textContent = text || '';
    el.hidden = !text;
  }

  /* Ask for the 通行碼 (same one as the release-notes editor); resolves true once unlocked. */
  function askPassword() {
    return new Promise(function (resolve) {
      var overlay = document.createElement('div');
      overlay.className = 'a1-modal-overlay';
      overlay.innerHTML =
        '<form class="a1-modal" role="dialog" aria-modal="true" aria-labelledby="a1PwTitle">' +
          '<h3 id="a1PwTitle">輸入通行碼</h3>' +
          '<p>變更插件狀態需要通行碼。</p>' +
          '<input type="password" id="a1PwInput" maxlength="6" autocomplete="off" inputmode="text" aria-label="通行碼">' +
          '<p class="a1-modal-error" id="a1PwError" role="alert" hidden></p>' +
          '<div class="a1-modal-actions">' +
            '<button type="button" class="a1-store-btn a1-store-btn--ghost" data-pw-cancel>取消</button>' +
            '<button type="submit" class="a1-store-btn">確認</button>' +
          '</div>' +
        '</form>';
      document.body.appendChild(overlay);
      var form = overlay.querySelector('form');
      var input = overlay.querySelector('#a1PwInput');
      var err = overlay.querySelector('#a1PwError');
      input.focus();
      function close(result) { overlay.remove(); resolve(result); }
      overlay.querySelector('[data-pw-cancel]').addEventListener('click', function () { close(false); });
      overlay.addEventListener('mousedown', function (e) { if (e.target === overlay) close(false); });
      overlay.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(false); });
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        var code = input.value.trim();
        if (!code) { err.textContent = '請輸入通行碼'; err.hidden = false; return; }
        fetch('/api/admin/release-notes/unlock', {
          method: 'POST', credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ code: code })
        }).then(function (res) {
          return res.json().catch(function () { return {}; }).then(function (data) {
            if (res.ok) return close(true);
            err.textContent = data.error || '通行碼錯誤';
            err.hidden = false;
            input.select();
          });
        }).catch(function () { err.textContent = '連線異常，請稍後再試'; err.hidden = false; });
      });
    });
  }

  function sendState(slug, next) {
    return fetch('/api/admin/plugins/' + encodeURIComponent(slug), {
      method: 'PATCH', credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ state: next })
    }).then(function (res) {
      return res.json().catch(function () { return {}; }).then(function (data) {
        return { ok: res.ok, status: res.status, data: data };
      });
    });
  }

  function changeState(slug, next) {
    if (busy) return;
    busy = true;
    renderDetail();
    function finish(result) {
      busy = false;
      if (result && result.ok && result.data.plugins) pluginStates = result.data.plugins;
      renderList(); /* list badge + detail */
      if (result && !result.ok) showPluginMsg(result.data.error || '變更失敗，請稍後再試');
    }
    sendState(slug, next).then(function (result) {
      if (result.status === 403 && result.data.error === 'unlock required') {
        return askPassword().then(function (unlocked) {
          if (!unlocked) return finish(null);
          return sendState(slug, next).then(finish);
        });
      }
      finish(result);
    }).catch(function () {
      busy = false;
      renderDetail();
      showPluginMsg('連線異常，請稍後再試');
    });
  }

  fetch('/api/admin/plugins', { credentials: 'include' })
    .then(function (res) { return res.ok ? res.json() : null; })
    .then(function (data) {
      if (data && data.plugins) { pluginStates = data.plugins; renderList(); }
    })
    .catch(function () { /* controls stay on 「載入狀態中」 */ });

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function visible() {
    var q = state.q.trim().toLowerCase();
    return CATALOG.filter(function (p) {
      if (state.category !== '全部' && p.category !== state.category) return false;
      if (!q) return true;
      return (p.name + ' ' + p.desc + ' ' + p.category).toLowerCase().indexOf(q) >= 0;
    });
  }

  function renderFilters() {
    filtersEl.innerHTML = CATEGORIES.map(function (c) {
      return '<button type="button" class="a1-store-chip' + (c === state.category ? ' is-active' : '') +
        '" data-cat="' + esc(c) + '">' + esc(c) + '</button>';
    }).join('');
  }

  function renderDetail() {
    var p = CATALOG.filter(function (x) { return x.id === state.selected; })[0];
    if (!p) return;
    detailEl.innerHTML =
      '<div class="a1-store-detail-head">' +
        '<span class="a1-store-icon a1-store-icon--lg" aria-hidden="true">' + esc(p.icon) + '</span>' +
        '<div><h3>' + esc(p.name) + '</h3><p>' + esc(p.desc) + '</p>' +
        (p.live
          ? pluginControlsHtml(p)
          : '<button type="button" class="a1-store-btn" disabled>即將推出</button>') + '</div>' +
      '</div>' +
      '<h4>簡介</h4><p class="a1-store-long">' + esc(p.long) + '</p>' +
      '<h4>' + (p.live ? '功能' : '預計功能') + '</h4><ul>' + p.features.map(function (f) { return '<li>' + esc(f) + '</li>'; }).join('') + '</ul>' +
      '<h4>資訊</h4><ul><li>分類：' + esc(p.category) + '</li><li>狀態：' +
        (p.live ? esc(stateLabel(p)) : '規劃中，尚未上線') + '</li></ul>';
  }

  function renderList() {
    var items = visible();
    if (!items.length) {
      listEl.innerHTML = '<li class="a1-store-empty">找不到符合的插件</li>';
      detailEl.innerHTML = '<p class="a1-store-empty">請調整搜尋或分類。</p>';
      return;
    }
    if (!items.some(function (p) { return p.id === state.selected; })) state.selected = items[0].id;
    listEl.innerHTML = items.map(function (p) {
      return '<li class="a1-store-item' + (p.id === state.selected ? ' is-selected' : '') +
        '" role="option" aria-selected="' + (p.id === state.selected) + '" tabindex="0" data-id="' + esc(p.id) + '">' +
        '<span class="a1-store-icon" aria-hidden="true">' + esc(p.icon) + '</span>' +
        '<div class="a1-store-item-body">' +
          '<h3 class="a1-store-item-name">' + esc(p.name) + '</h3>' +
          '<p class="a1-store-item-desc">' + esc(p.desc) + '</p>' +
          '<p class="a1-store-item-meta"><span class="a1-store-badge">' + esc(stateLabel(p)) + '</span> · ' + esc(p.category) + '</p>' +
        '</div></li>';
    }).join('');
    renderDetail();
  }

  function select(id) {
    if (!id || id === state.selected) return;
    state.selected = id;
    renderList();
  }

  listEl.addEventListener('click', function (e) {
    var li = e.target.closest('.a1-store-item');
    if (li) select(li.getAttribute('data-id'));
  });
  listEl.addEventListener('keydown', function (e) {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    var li = e.target.closest('.a1-store-item');
    if (li) { e.preventDefault(); select(li.getAttribute('data-id')); }
  });
  filtersEl.addEventListener('click', function (e) {
    var b = e.target.closest('[data-cat]');
    if (!b) return;
    state.category = b.getAttribute('data-cat');
    renderFilters();
    renderList();
  });
  searchEl.addEventListener('input', function () {
    state.q = searchEl.value;
    renderList();
  });
  detailEl.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-plugin-state]');
    if (!btn || btn.disabled) return;
    var next = btn.getAttribute('data-plugin-state');
    if (next === 'disabled' && !window.confirm('確定要停用這個插件嗎？停用後選單與功能都會關閉（資料會保留）。')) return;
    changeState(state.selected, next);
  });
  detailEl.addEventListener('change', function (e) {
    if (!e.target.matches('[data-plugin-toggle]')) return;
    changeState(state.selected, e.target.checked ? 'on' : 'off');
  });

  renderFilters();
  renderList();
})();
