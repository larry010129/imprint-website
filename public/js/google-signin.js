/* 銘印鑽石｜Google 登入（Google Identity Services）
   後端在 /api/auth/google 驗證 credential 簽章後才建立 session，
   這裡送出的 profile 資訊全部不受信任，僅由後端驗證結果決定登入結果。 */
(function () {
  'use strict';

  var thisScript = document.currentScript;
  var slot = document.getElementById('google-signin-slot');
  var clientId =
    (thisScript && thisScript.dataset.clientId) ||
    (slot && slot.dataset.googleClientId) ||
    '';
  if (!clientId) return;

  function setMsg(text, isError) {
    var el = document.getElementById('googleSignInMsg');
    if (!el) return;
    el.textContent = text || '';
    el.classList.toggle('is-err', !!isError);
  }

  function apiBase() {
    var api = window.imprintAPI;
    return (api && api.getBase) ? (api.getBase() || '') : '';
  }

  /** Mirror server `safe_next_url`: same-origin relative path only. */
  function safeNextUrl(raw, fallback) {
    var next = (raw || '').trim();
    if (!next) return fallback;
    try {
      next = decodeURIComponent(next);
    } catch (_e) {
      return fallback;
    }
    if (next.charAt(0) !== '/' || next.indexOf('//') === 0) return fallback;
    return next;
  }

  function handleCredentialResponse(response) {
    setMsg('登入中…', false);
    var params = new URLSearchParams(window.location.search);
    var nextSafe = safeNextUrl(params.get('next'), '/account.html');
    fetch(apiBase() + '/api/auth/google', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ credential: response.credential, next: nextSafe }),
    })
      .then(function (res) {
        return res.json().catch(function () { return {}; }).then(function (data) {
          return { ok: res.ok, data: data };
        });
      })
      .then(function (result) {
        if (!result.ok || result.data.error) {
          setMsg((result.data && result.data.error) || 'Google 登入失敗，請再試一次。', true);
          return;
        }
        // Server `next` wins; query fallback still same-origin path only.
        window.location.href = safeNextUrl(result.data.next, nextSafe);
      })
      .catch(function () {
        setMsg('連線異常，請稍後再試。', true);
      });
  }

  function renderButton() {
    var target = document.getElementById('googleSignInBtn') || slot;
    if (!target) return;
    google.accounts.id.initialize({ client_id: clientId, callback: handleCredentialResponse });
    google.accounts.id.renderButton(target, {
      theme: 'outline',
      size: 'large',
      width: 320,
      locale: 'zh_TW',
    });
  }

  var tries = 0;
  (function waitForGis() {
    if (window.google && window.google.accounts && window.google.accounts.id) {
      renderButton();
      return;
    }
    tries += 1;
    if (tries > 80) return; // ~20s — give up quietly, the button area just stays empty
    setTimeout(waitForGis, 250);
  })();
})();
