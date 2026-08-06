/**
 * admin1 settings — profile, password, notification prefs.
 * Uses shared imprintAPI; sign-out stays on admin1-shell.js.
 */
(function () {
  'use strict';

  var PREFS_PREFIX = 'admin1-notify-prefs:';
  var userId = null;
  var totpEnabled = false;

  function api() {
    return window.imprintAPI;
  }

  function els() {
    return {
      name: document.getElementById('a1Name'),
      email: document.getElementById('a1Email'),
      phone: document.getElementById('a1Phone'),
      profileMsg: document.getElementById('a1ProfileMsg'),
      profileSave: document.getElementById('a1ProfileSave'),
      pwCurrent: document.getElementById('a1PwCurrent'),
      pw: document.getElementById('a1Pw'),
      pw2: document.getElementById('a1Pw2'),
      pwTotp: document.getElementById('a1PwTotp'),
      totpWrap: document.getElementById('a1TotpWrap'),
      securityMsg: document.getElementById('a1SecurityMsg'),
      securitySave: document.getElementById('a1SecuritySave'),
      prefOrders: document.getElementById('a1PrefOrders'),
      prefSystem: document.getElementById('a1PrefSystem'),
      prefMarketing: document.getElementById('a1PrefMarketing'),
      prefsMsg: document.getElementById('a1PrefsMsg'),
      prefsSave: document.getElementById('a1PrefsSave'),
      topMeta: document.getElementById('topMeta'),
    };
  }

  function setMsg(el, text, ok) {
    if (!el) return;
    el.textContent = text || '';
    el.style.color = ok === false ? '#b91c1c' : 'var(--a1-muted-fg)';
  }

  function errText(res) {
    var client = api();
    if (client && typeof client.apiErrorMessage === 'function') {
      return client.apiErrorMessage(res);
    }
    return (res && res.error) || '操作失敗，請稍後再試';
  }

  function redirectLogin() {
    window.location.href =
      '/login.html?next=' + encodeURIComponent('/admin1-settings.html');
  }

  function avatarInitial(name, email) {
    var raw = String(name || email || '管').trim();
    return raw ? raw.charAt(0) : '管';
  }

  function fillAvatar(name, email) {
    var initial = avatarInitial(name, email);
    document.querySelectorAll('.admin1-avatar').forEach(function (el) {
      el.textContent = initial;
    });
  }

  function prefsKey() {
    return PREFS_PREFIX + (userId || 'anon');
  }

  function defaultPrefs() {
    return { orders: true, system: true, marketing: false };
  }

  function loadPrefs() {
    var fallback = defaultPrefs();
    try {
      var raw = localStorage.getItem(prefsKey());
      if (!raw) return fallback;
      var parsed = JSON.parse(raw);
      return {
        orders: parsed.orders !== false,
        system: parsed.system !== false,
        marketing: !!parsed.marketing,
      };
    } catch (e) {
      return fallback;
    }
  }

  function applyPrefs(prefs) {
    var e = els();
    if (e.prefOrders) {
      e.prefOrders.disabled = false;
      e.prefOrders.checked = !!prefs.orders;
    }
    if (e.prefSystem) {
      e.prefSystem.disabled = false;
      e.prefSystem.checked = !!prefs.system;
    }
    if (e.prefMarketing) {
      e.prefMarketing.disabled = false;
      e.prefMarketing.checked = !!prefs.marketing;
    }
  }

  function savePrefs() {
    var e = els();
    var prefs = {
      orders: !!(e.prefOrders && e.prefOrders.checked),
      system: !!(e.prefSystem && e.prefSystem.checked),
      marketing: !!(e.prefMarketing && e.prefMarketing.checked),
    };
    try {
      localStorage.setItem(prefsKey(), JSON.stringify(prefs));
      setMsg(e.prefsMsg, '通知偏好已儲存', true);
    } catch (err) {
      setMsg(e.prefsMsg, '無法寫入本機偏好', false);
    }
  }

  function enableProfileFields() {
    var e = els();
    if (e.name) e.name.disabled = false;
    if (e.phone) e.phone.disabled = false;
    if (e.email) e.email.disabled = true;
    if (e.profileSave) e.profileSave.disabled = false;
  }

  function enableSecurityFields() {
    var e = els();
    [e.pwCurrent, e.pw, e.pw2, e.pwTotp, e.securitySave].forEach(function (el) {
      if (el) el.disabled = false;
    });
    if (e.totpWrap) e.totpWrap.hidden = !totpEnabled;
  }

  function fillProfile(session) {
    var e = els();
    var user = session.user || {};
    var profile = session.profile || {};
    var name = profile.full_name || profile.fullName || '';
    if (e.name) e.name.value = name;
    if (e.email) e.email.value = user.email || '';
    if (e.phone) e.phone.value = profile.phone || '';
    if (e.topMeta) e.topMeta.textContent = user.email || '設定';
    fillAvatar(name, user.email);
  }

  function saveProfile() {
    var e = els();
    var client = api();
    if (!client || typeof client.updateProfile !== 'function') {
      setMsg(e.profileMsg, '無法連線 API', false);
      return;
    }
    var fullName = (e.name && e.name.value || '').trim();
    var phone = (e.phone && e.phone.value || '').trim();
    if (!fullName) {
      setMsg(e.profileMsg, '請填寫顯示名稱', false);
      return;
    }
    if (!phone) {
      setMsg(e.profileMsg, '請填寫聯絡電話', false);
      return;
    }
    if (e.profileSave) e.profileSave.disabled = true;
    setMsg(e.profileMsg, '儲存中…');
    client.updateProfile({ fullName: fullName, phone: phone }).then(function (res) {
      if (e.profileSave) e.profileSave.disabled = false;
      if (res && res._httpStatus === 401) {
        redirectLogin();
        return;
      }
      if (!res || res.error || !res.ok) {
        setMsg(e.profileMsg, errText(res), false);
        return;
      }
      setMsg(e.profileMsg, '個人資料已儲存', true);
      fillAvatar(fullName, e.email && e.email.value);
    });
  }

  function savePassword() {
    var e = els();
    var client = api();
    if (!client || typeof client.changePassword !== 'function') {
      setMsg(e.securityMsg, '無法連線 API', false);
      return;
    }
    var current = (e.pwCurrent && e.pwCurrent.value) || '';
    var next = (e.pw && e.pw.value) || '';
    var confirm = (e.pw2 && e.pw2.value) || '';
    var totp = (e.pwTotp && e.pwTotp.value || '').trim();
    if (!current) {
      setMsg(e.securityMsg, '請輸入目前密碼', false);
      return;
    }
    if (next.length < 8) {
      setMsg(e.securityMsg, '新密碼至少需要 8 碼', false);
      return;
    }
    if (next !== confirm) {
      setMsg(e.securityMsg, '兩次新密碼不一致', false);
      return;
    }
    if (totpEnabled && !totp) {
      setMsg(e.securityMsg, '請輸入 Authenticator 驗證碼', false);
      return;
    }
    if (e.securitySave) e.securitySave.disabled = true;
    setMsg(e.securityMsg, '更新中…');
    var body = { currentPassword: current, newPassword: next };
    if (totp) body.totpCode = totp;
    client.changePassword(body).then(function (res) {
      if (e.securitySave) e.securitySave.disabled = false;
      if (res && res._httpStatus === 401 && res.error === '請先登入') {
        redirectLogin();
        return;
      }
      if (!res || res.error || !res.ok) {
        setMsg(e.securityMsg, errText(res), false);
        return;
      }
      if (e.pwCurrent) e.pwCurrent.value = '';
      if (e.pw) e.pw.value = '';
      if (e.pw2) e.pw2.value = '';
      if (e.pwTotp) e.pwTotp.value = '';
      setMsg(e.securityMsg, '密碼已更新', true);
    });
  }

  function bindActions() {
    var e = els();
    if (e.profileSave) {
      e.profileSave.addEventListener('click', saveProfile);
    }
    if (e.securitySave) {
      e.securitySave.addEventListener('click', savePassword);
    }
    if (e.prefsSave) {
      e.prefsSave.addEventListener('click', savePrefs);
    }
  }

  function onSession(session) {
    if (!session || !session.user) {
      redirectLogin();
      return;
    }
    if (!session.isAdmin) {
      setMsg(els().profileMsg, '此帳號沒有後台權限', false);
      return;
    }
    userId = session.user.id;
    totpEnabled = !!session.totpEnabled;
    fillProfile(session);
    enableProfileFields();
    enableSecurityFields();
    applyPrefs(loadPrefs());
    if (els().prefsSave) els().prefsSave.disabled = false;
  }

  function boot() {
    var client = api();
    if (!client || typeof client.getSession !== 'function') {
      setMsg(els().profileMsg, '無法連線 API', false);
      return;
    }
    bindActions();
    client.getSession().then(onSession);
  }

  boot();
})();
