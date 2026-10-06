/* 銘印鑽石｜隱藏頁面的通行碼閘門：輸入正確通行碼後重新載入同一頁。 */
(function () {
  'use strict';

  var form = document.getElementById('unlockForm');
  var input = document.getElementById('unlockCode');
  var errorEl = document.getElementById('unlockError');
  var submit = document.getElementById('unlockSubmit');
  if (!form || !input) return;

  function showError(text) {
    errorEl.textContent = text || '';
    errorEl.hidden = !text;
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var code = input.value.trim();
    if (!code) { showError('請輸入通行碼'); return; }
    showError('');
    submit.disabled = true;
    fetch('/api/admin/release-notes/unlock', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code: code })
    }).then(function (res) {
      return res.json().catch(function () { return {}; }).then(function (data) {
        if (res.ok) {
          /* Same URL (including #plugins); the server now sees the unlock cookie. */
          window.location.reload();
          return;
        }
        submit.disabled = false;
        showError(data.error || (res.status === 401 ? '通行碼錯誤' : '無法驗證，請稍後再試'));
        input.select();
      });
    }).catch(function () {
      submit.disabled = false;
      showError('連線異常，請稍後再試');
    });
  });
})();
