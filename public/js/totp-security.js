(function () {
  'use strict';

  function apiBase() {
    var api = window.imprintAPI;
    return (api && api.getBase) ? (api.getBase() || '') : '';
  }

  function setMsg(el, text, isError) {
    if (!el) return;
    el.textContent = text || '';
    el.classList.toggle('is-error', !!isError);
    el.classList.toggle('is-err', !!isError);
  }

  function postJson(path, body) {
    return fetch(apiBase() + path, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {}),
    }).then(function (res) {
      return res.json().catch(function () { return {}; }).then(function (data) {
        return { ok: res.ok, data: data };
      });
    });
  }

  function setupTotpPanel(panel) {
    if (!panel || panel.dataset.totpBound === '1') return;
    panel.dataset.totpBound = '1';

    var startBtn = panel.querySelector('#totp-start-btn');
    var setupPanel = panel.querySelector('#totp-setup-panel');
    var backupPanel = panel.querySelector('#totp-backup-panel');
    var setupMsg = panel.querySelector('#totp-setup-msg');
    var confirmForm = panel.querySelector('#totp-confirm-form');
    var disableForm = panel.querySelector('#totp-disable-form');
    var disableMsg = panel.querySelector('#totp-disable-msg');
    var backupDone = panel.querySelector('#totp-backup-done');

    if (startBtn) {
      startBtn.addEventListener('click', function () {
        startBtn.disabled = true;
        if (setupPanel) setupPanel.hidden = false;
        setMsg(setupMsg, '載入中…', false);
        postJson('/api/auth/totp/setup/start', {}).then(function (result) {
          if (!result.ok || result.data.error) {
            setMsg(setupMsg, (result.data && result.data.error) || '無法開始設定', true);
            startBtn.disabled = false;
            return;
          }
          var qr = panel.querySelector('#totp-qr');
          var secret = panel.querySelector('#totp-secret');
          if (qr) qr.src = result.data.qrDataUrl || '';
          if (secret) secret.textContent = result.data.secret || '';
          setMsg(setupMsg, '', false);
          startBtn.hidden = true;
        }).catch(function () {
          setMsg(setupMsg, '連線異常，請稍後再試', true);
          startBtn.disabled = false;
        });
      });
    }

    if (confirmForm) {
      confirmForm.addEventListener('submit', function (e) {
        e.preventDefault();
        var codeInput = panel.querySelector('#totpConfirmCode');
        var code = codeInput ? codeInput.value.trim() : '';
        setMsg(setupMsg, '驗證中…', false);
        postJson('/api/auth/totp/setup/confirm', { code: code }).then(function (result) {
          if (!result.ok || result.data.error) {
            setMsg(setupMsg, (result.data && result.data.error) || '驗證失敗', true);
            return;
          }
          var list = panel.querySelector('#totp-backup-list');
          if (list && result.data.backupCodes) {
            list.innerHTML = result.data.backupCodes.map(function (c) {
              return '<li><code>' + c + '</code></li>';
            }).join('');
          }
          if (setupPanel) setupPanel.hidden = true;
          if (backupPanel) backupPanel.hidden = false;
          setMsg(setupMsg, '', false);
        }).catch(function () {
          setMsg(setupMsg, '連線異常，請稍後再試', true);
        });
      });
    }

    if (backupDone) {
      backupDone.addEventListener('click', function () {
        window.location.href = '/account-security';
      });
    }

    if (disableForm) {
      disableForm.addEventListener('submit', function (e) {
        e.preventDefault();
        var password = (panel.querySelector('#totpDisablePassword') || {}).value || '';
        var code = (panel.querySelector('#totpDisableCode') || {}).value || '';
        setMsg(disableMsg, '處理中…', false);
        postJson('/api/auth/totp/disable', { password: password, code: code }).then(function (result) {
          if (!result.ok || result.data.error) {
            setMsg(disableMsg, (result.data && result.data.error) || '無法關閉', true);
            return;
          }
          window.location.reload();
        }).catch(function () {
          setMsg(disableMsg, '連線異常，請稍後再試', true);
        });
      });
    }
  }

  function initTotpSecurity(scope) {
    (scope || document).querySelectorAll('.totp-security-panel').forEach(setupTotpPanel);
  }

  document.addEventListener('DOMContentLoaded', function () {
    initTotpSecurity(document);
  });

  document.body.addEventListener('htmx:afterSwap', function (e) {
    initTotpSecurity(e.target);
  });
})();
