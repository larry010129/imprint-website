/* 銘印鑽石｜會員登入／註冊頁共用互動效果
   （粒子背景、深色模式切換、密碼顯示切換、Email 網域「其他」欄位）—
   純 vanilla JS，取代原本的 React 版本(animated-sign-in/up.tsx)。 */
(function (global) {
  'use strict';

  function initParticles(canvas, container, isDarkFn) {
    var ctx = canvas.getContext('2d');
    if (!ctx) return null;
    var particles = [];

    function setSize() {
      var rect = container.getBoundingClientRect();
      canvas.width = rect.width;
      canvas.height = rect.height;
    }

    function Particle(w, h, dark) {
      this.x = Math.random() * w;
      this.y = Math.random() * h;
      this.size = Math.random() * 3 + 1;
      this.speedX = (Math.random() - 0.5) * 0.5;
      this.speedY = (Math.random() - 0.5) * 0.5;
      this.color = dark
        ? 'rgba(156, 239, 239, ' + (Math.random() * 0.25) + ')'
        : 'rgba(94, 207, 207, ' + (Math.random() * 0.35) + ')';
    }
    Particle.prototype.update = function (w, h) {
      this.x += this.speedX;
      this.y += this.speedY;
      if (this.x > w) this.x = 0;
      if (this.x < 0) this.x = w;
      if (this.y > h) this.y = 0;
      if (this.y < 0) this.y = h;
    };
    Particle.prototype.draw = function (context) {
      context.fillStyle = this.color;
      context.beginPath();
      context.arc(this.x, this.y, this.size, 0, Math.PI * 2);
      context.fill();
    };

    function count() {
      return Math.min(80, Math.floor((canvas.width * canvas.height) / 12000));
    }

    function initList() {
      particles.length = 0;
      var dark = isDarkFn();
      for (var i = 0; i < count(); i++) {
        particles.push(new Particle(canvas.width, canvas.height, dark));
      }
    }

    setSize();
    initList();

    function animate() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      for (var i = 0; i < particles.length; i++) {
        particles[i].update(canvas.width, canvas.height);
        particles[i].draw(ctx);
      }
      global.requestAnimationFrame(animate);
    }
    animate();

    if (global.ResizeObserver) {
      new ResizeObserver(setSize).observe(container);
    } else {
      global.addEventListener('resize', setSize);
    }

    return { refreshColors: initList };
  }

  function initTheme(container, particles) {
    var toggle = container.querySelector('[data-auth-theme-toggle]');
    var moonIcon = container.querySelector('[data-auth-theme-icon-moon]');
    var sunIcon = container.querySelector('[data-auth-theme-icon-sun]');
    if (!toggle) return;

    toggle.addEventListener('click', function () {
      var isDark = container.classList.toggle('dark');
      container.classList.toggle('light', !isDark);
      if (moonIcon) moonIcon.toggleAttribute('hidden', isDark);
      if (sunIcon) sunIcon.toggleAttribute('hidden', !isDark);
      toggle.setAttribute('aria-label', isDark ? '切換淺色模式' : '切換深色模式');
      if (particles) particles.refreshColors();
    });
  }

  function initPasswordToggles(root) {
    root.querySelectorAll('[data-auth-toggle-password]').forEach(function (btn) {
      var field = btn.closest('.form-field');
      var input = field ? field.querySelector('input') : null;
      var eyeIcon = btn.querySelector('[data-auth-eye-icon]');
      var eyeOffIcon = btn.querySelector('[data-auth-eye-off-icon]');
      if (!input) return;
      btn.addEventListener('click', function () {
        var showing = input.type === 'text';
        input.type = showing ? 'password' : 'text';
        if (eyeIcon) eyeIcon.toggleAttribute('hidden', !showing);
        if (eyeOffIcon) eyeOffIcon.toggleAttribute('hidden', showing);
        btn.setAttribute('aria-label', showing ? '顯示密碼' : '隱藏密碼');
      });
    });
  }

  function initPhoneNumeric(root) {
    root.querySelectorAll('input[type="tel"]').forEach(function (input) {
      input.addEventListener('input', function () {
        var digitsOnly = input.value.replace(/\D/g, '');
        if (digitsOnly !== input.value) input.value = digitsOnly;
      });
    });
  }

  function initPartnerToggle(root) {
    var toggle = root.querySelector('[data-auth-partner-toggle]');
    var field = root.querySelector('[data-auth-invite-code-field]');
    if (!toggle || !field) return;
    var input = field.querySelector('input');
    toggle.addEventListener('change', function () {
      field.hidden = !toggle.checked;
      if (input) input.required = toggle.checked;
      if (toggle.checked && input) input.focus();
    });
  }

  var REGISTER_EMAIL_RE = /^[^\s@]+@[^\s@]+\.[a-zA-Z]{2,}$/;

  function isValidRegisterEmail(email) {
    if (!email || email.length > 254) return false;
    if (/\s/.test(email)) return false;
    var at = email.indexOf('@');
    if (at <= 0 || at !== email.lastIndexOf('@')) return false;
    var local = email.slice(0, at);
    var domain = email.slice(at + 1);
    if (!local || !domain || domain.indexOf('.') === -1) return false;
    if (/^\./.test(local) || /\.$/.test(local) || /\.\./.test(local)) return false;
    if (/^\./.test(domain) || /\.$/.test(domain) || /\.\./.test(domain)) return false;
    var tld = domain.slice(domain.lastIndexOf('.') + 1);
    if (tld.length < 2 || !/^[a-zA-Z]+$/.test(tld)) return false;
    return REGISTER_EMAIL_RE.test(email);
  }

  function initHtmxAuthFormErrors() {
    document.body.addEventListener('htmx:beforeSwap', function (ev) {
      var xhr = ev.detail.xhr;
      if (!xhr || xhr.status < 400 || xhr.status >= 600) return;
      var elt = ev.detail.elt;
      if (!elt || !elt.closest) return;
      var form = elt.closest('form');
      if (!form || form.getAttribute('hx-target') !== '#auth-form-msg') return;
      ev.detail.shouldSwap = true;
      ev.detail.isError = false;
    });
  }

  function findFieldWrap(input) {
    if (!input) return null;
    if (
      input.classList &&
      (input.classList.contains('terms-check') || input.classList.contains('recaptcha-field'))
    ) {
      return input;
    }
    return (
      input.closest('.form-field') ||
      input.closest('.terms-check') ||
      input.closest('[data-auth-recaptcha]')
    );
  }

  function getRecaptchaResponse(form) {
    var ta = form ? form.querySelector('[name="g-recaptcha-response"]') : null;
    return ta ? String(ta.value || '').trim() : '';
  }

  function setRecaptchaResponse(form, token) {
    var ta = form ? form.querySelector('[name="g-recaptcha-response"]') : null;
    if (ta) ta.value = token || '';
  }

  function setAuthFormMsg(text) {
    var box = document.getElementById('auth-form-msg');
    if (!box) return;
    box.innerHTML = '';
    if (!text) return;
    var p = document.createElement('p');
    p.className = 'form-msg is-err';
    p.setAttribute('role', 'alert');
    p.textContent = text;
    box.appendChild(p);
  }

  function resetRecaptcha(form) {
    setRecaptchaResponse(form || document.getElementById('registerForm'), '');
  }

  function executeRecaptchaV3(form) {
    var siteKey = form ? String(form.getAttribute('data-recaptcha-sitekey') || '').trim() : '';
    var action = form ? String(form.getAttribute('data-recaptcha-action') || 'register').trim() : 'register';
    if (!siteKey) {
      return Promise.reject(new Error('missing site key'));
    }
    if (typeof global.grecaptcha === 'undefined' || typeof global.grecaptcha.execute !== 'function') {
      return Promise.reject(new Error('grecaptcha not loaded'));
    }
    return new Promise(function (resolve, reject) {
      global.grecaptcha.ready(function () {
        global.grecaptcha
          .execute(siteKey, { action: action || 'register' })
          .then(function (token) {
            resolve(token);
          })
          .catch(reject);
      });
    });
  }

  function ensureErrorMessage(wrap) {
    var msgEl = wrap.querySelector('.error-message');
    if (msgEl) return msgEl;
    msgEl = document.createElement('span');
    msgEl.className = 'error-message';
    msgEl.setAttribute('role', 'alert');
    wrap.appendChild(msgEl);
    return msgEl;
  }

  function setFieldInvalid(input, message) {
    var wrap = findFieldWrap(input);
    if (!wrap) return;
    wrap.classList.add('invalid');
    var msgEl = ensureErrorMessage(wrap);
    msgEl.textContent = message || '';
    msgEl.hidden = !message;
  }

  function clearFieldInvalid(input) {
    var wrap = findFieldWrap(input);
    if (!wrap) return;
    wrap.classList.remove('invalid');
    var msgEl = wrap.querySelector('.error-message');
    if (msgEl) {
      msgEl.textContent = '';
      msgEl.hidden = true;
    }
  }

  function isValidPhone(phone) {
    return /^\d{8,15}$/.test(phone);
  }

  function extractAuthErrorMessage() {
    var msg = document.getElementById('auth-form-msg');
    if (!msg) return '';
    var el = msg.querySelector('.form-msg.is-err');
    return el ? el.textContent.trim() : msg.textContent.trim();
  }

  function mapRegisterServerError(errorText, form) {
    if (!errorText || !form) return;
    if (errorText.indexOf('完整填寫') !== -1) {
      var required = [
        { sel: '[name="fullName"]', msg: '請填寫姓名' },
        { sel: '[name="phone"]', msg: '請填寫電話' },
        { sel: '[name="email"]', msg: '請填寫 Email' },
        { sel: '[name="password"]', msg: '請填寫密碼' },
      ];
      required.forEach(function (item) {
        var input = form.querySelector(item.sel);
        if (input && !String(input.value || '').trim()) {
          setFieldInvalid(input, item.msg);
        }
      });
      return;
    }
    if (errorText.indexOf('兩次密碼不一致') !== -1) {
      setFieldInvalid(form.querySelector('[name="passwordConfirm"]'), errorText);
      return;
    }
    if (errorText.indexOf('密碼至少需要') !== -1) {
      setFieldInvalid(form.querySelector('[name="password"]'), errorText);
      return;
    }
    if (errorText.indexOf('服務條款') !== -1 || errorText.indexOf('隱私權') !== -1) {
      setFieldInvalid(form.querySelector('[name="acceptTerms"]'), errorText);
      return;
    }
    if (errorText.indexOf('邀請碼') !== -1) {
      setFieldInvalid(form.querySelector('[name="inviteCode"]'), errorText);
      return;
    }
    if (
      errorText.indexOf('請完成驗證') !== -1 ||
      errorText.indexOf('驗證尚未設定') !== -1 ||
      errorText.indexOf('驗證碼') !== -1
    ) {
      var recaptchaWrap = form.querySelector('[data-auth-recaptcha]');
      setFieldInvalid(recaptchaWrap, errorText);
      resetRecaptcha(form);
      return;
    }
    if (
      errorText.indexOf('Email') !== -1 ||
      errorText.indexOf('email') !== -1 ||
      errorText.indexOf('網域') !== -1 ||
      errorText.indexOf('已被註冊') !== -1
    ) {
      setFieldInvalid(form.querySelector('[name="email"]'), errorText);
    }
  }

  function validateRegisterForm(form, emailCheck, inviteCheck) {
    var firstBad = null;
    var ok = true;

    function fail(input, message) {
      setFieldInvalid(input, message);
      if (!firstBad) firstBad = input;
      ok = false;
    }

    var nameInput = form.querySelector('[name="fullName"]');
    if (!nameInput || !nameInput.value.trim()) {
      fail(nameInput, '請填寫姓名');
    } else {
      clearFieldInvalid(nameInput);
    }

    var phoneInput = form.querySelector('[name="phone"]');
    var phone = phoneInput ? phoneInput.value.trim() : '';
    if (!phone) {
      fail(phoneInput, '請填寫電話');
    } else if (!isValidPhone(phone)) {
      fail(phoneInput, '請輸入有效的電話號碼');
    } else {
      clearFieldInvalid(phoneInput);
    }

    var emailInput = form.querySelector('[name="email"]');
    var email = emailInput ? emailInput.value.trim() : '';
    if (!email) {
      fail(emailInput, '請填寫 Email');
    } else if (!isValidRegisterEmail(email)) {
      fail(emailInput, '請輸入有效的 Email 格式');
    } else if (emailCheck && emailCheck.email === email && emailCheck.ok === false) {
      fail(emailInput, emailCheck.error || '請輸入有效的 Email 格式');
    } else {
      clearFieldInvalid(emailInput);
    }

    var passwordInput = form.querySelector('[name="password"]');
    var password = passwordInput ? passwordInput.value : '';
    if (!password) {
      fail(passwordInput, '請填寫密碼');
    } else if (password.length < 8) {
      fail(passwordInput, '密碼至少需要 8 碼');
    } else {
      clearFieldInvalid(passwordInput);
    }

    var confirmInput = form.querySelector('[name="passwordConfirm"]');
    if (!confirmInput || !confirmInput.value) {
      fail(confirmInput, '請再次確認密碼');
    } else if (confirmInput.value !== password) {
      fail(confirmInput, '兩次密碼不一致');
    } else {
      clearFieldInvalid(confirmInput);
    }

    var partnerToggle = form.querySelector('[data-auth-partner-toggle]');
    var inviteInput = form.querySelector('[name="inviteCode"]');
    if (partnerToggle && partnerToggle.checked) {
      if (!inviteInput || !inviteInput.value.trim()) {
        fail(inviteInput, '請輸入合作廠商邀請碼');
      } else if (inviteCheck && inviteCheck.code === inviteInput.value.trim() && inviteCheck.ok === false) {
        fail(inviteInput, inviteCheck.error || '邀請碼無效或已過期');
      } else {
        clearFieldInvalid(inviteInput);
      }
    } else if (inviteInput) {
      clearFieldInvalid(inviteInput);
    }

    var recaptchaWrap = form.querySelector('[data-auth-recaptcha]');
    if (recaptchaWrap) {
      clearFieldInvalid(recaptchaWrap);
    }

    var termsInput = form.querySelector('[name="acceptTerms"]');
    if (!termsInput || !termsInput.checked) {
      fail(termsInput, '請先閱讀並同意服務條款與隱私權政策');
    } else {
      clearFieldInvalid(termsInput);
    }

    return { ok: ok, firstBad: firstBad };
  }

  function initRegisterFieldClear(root) {
    root.querySelectorAll('#registerForm input').forEach(function (input) {
      // passwordConfirm owns its own state in initPasswordMatch — blindly clearing
      // on every keystroke here is what hid the mismatch error.
      if (input.name === 'passwordConfirm') return;
      var evt = input.type === 'checkbox' ? 'change' : 'input';
      input.addEventListener(evt, function () {
        if (input.type === 'checkbox' && input.name === 'acceptTerms' && !input.checked) return;
        if (input.type === 'checkbox' || String(input.value || '').trim()) {
          clearFieldInvalid(input);
        }
      });
    });
  }

  function initPasswordMatch(form) {
    var pw = form.querySelector('[name="password"]');
    var confirm = form.querySelector('[name="passwordConfirm"]');
    if (!pw || !confirm) return;
    function check() {
      if (!confirm.value) clearFieldInvalid(confirm);
      else if (confirm.value === pw.value) clearFieldInvalid(confirm);
      else setFieldInvalid(confirm, '兩次密碼不一致');
    }
    pw.addEventListener('input', check);
    confirm.addEventListener('input', check);
    confirm.addEventListener('blur', check);
  }

  function initRegisterEmailCheck(form) {
    var emailInput = form.querySelector('[name="email"]');
    if (!emailInput) return { get: function () { return null; } };

    var debounceTimer = null;
    var lastCheck = null;
    var pending = null;

    function applyCheckResult(email, data) {
      lastCheck = { email: email, ok: data.ok, error: data.error || '' };
      if (data.ok) {
        clearFieldInvalid(emailInput);
        return;
      }
      if (emailInput.value.trim() === email) {
        setFieldInvalid(emailInput, data.error || '請輸入有效的 Email 格式');
      }
    }

    function runCheck() {
      var email = emailInput.value.trim();
      if (!email || !isValidRegisterEmail(email)) return;
      if (pending && pending.email === email) return;
      pending = { email: email };
      fetch('/htmx/auth/check-email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded', Accept: 'application/json' },
        body: 'email=' + encodeURIComponent(email),
      })
        .then(function (resp) {
          return resp.json().then(function (data) {
            return { status: resp.status, data: data };
          });
        })
        .then(function (result) {
          pending = null;
          if (emailInput.value.trim() !== email) return;
          applyCheckResult(email, {
            ok: result.status === 200 && result.data.ok === true,
            error: result.data.error,
          });
        })
        .catch(function () {
          pending = null;
        });
    }

    function scheduleCheck() {
      if (debounceTimer) global.clearTimeout(debounceTimer);
      debounceTimer = global.setTimeout(runCheck, 500);
    }

    emailInput.addEventListener('blur', function () {
      if (emailInput.value.trim()) runCheck();
    });

    emailInput.addEventListener('input', function () {
      lastCheck = null;
      if (!isValidRegisterEmail(emailInput.value.trim())) {
        if (debounceTimer) global.clearTimeout(debounceTimer);
        return;
      }
      scheduleCheck();
    });

    return {
      get: function () {
        return lastCheck;
      },
    };
  }

  function initRegisterInviteCheck(form) {
    var inviteInput = form.querySelector('[name="inviteCode"]');
    var partnerToggle = form.querySelector('[data-auth-partner-toggle]');
    if (!inviteInput) return { get: function () { return null; } };

    var lastCheck = null;
    var pending = null;

    function runCheck() {
      if (!partnerToggle || !partnerToggle.checked) return;
      var code = inviteInput.value.trim();
      if (!code) return;
      if (pending && pending.code === code) return;
      pending = { code: code };
      fetch('/htmx/auth/check-invite', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded', Accept: 'application/json' },
        body: 'inviteCode=' + encodeURIComponent(code),
      })
        .then(function (resp) {
          return resp.json().then(function (data) {
            return { status: resp.status, data: data };
          });
        })
        .then(function (result) {
          pending = null;
          if (inviteInput.value.trim() !== code) return;
          lastCheck = {
            code: code,
            ok: result.status === 200 && result.data.ok === true,
            error: result.data.error || '',
          };
          if (lastCheck.ok) clearFieldInvalid(inviteInput);
          else setFieldInvalid(inviteInput, lastCheck.error || '邀請碼無效或已過期');
        })
        .catch(function () {
          pending = null;
        });
    }

    inviteInput.addEventListener('blur', function () {
      if (inviteInput.value.trim()) runCheck();
    });
    inviteInput.addEventListener('input', function () {
      lastCheck = null;
    });

    return {
      get: function () {
        return lastCheck;
      },
    };
  }

  function initRegisterFormValidation(root) {
    var form = root.querySelector('#registerForm');
    if (!form) return;

    var emailCheck = initRegisterEmailCheck(form);
    var inviteCheck = initRegisterInviteCheck(form);
    initRegisterFieldClear(root);
    initPasswordMatch(form);

    form.addEventListener('submit', function (ev) {
      var result = validateRegisterForm(form, emailCheck.get(), inviteCheck.get());
      if (result.ok) return;
      ev.preventDefault();
      if (result.firstBad && result.firstBad.focus) result.firstBad.focus();
    });

    form.addEventListener('htmx:confirm', function (ev) {
      if (!form.getAttribute('data-recaptcha-sitekey')) return;
      var result = validateRegisterForm(form, emailCheck.get(), inviteCheck.get());
      if (!result.ok) {
        ev.preventDefault();
        if (result.firstBad && result.firstBad.focus) result.firstBad.focus();
        return;
      }
      ev.preventDefault();
      var issueRequest = ev.detail && ev.detail.issueRequest;
      // ponytail: recaptcha may never resolve (script blocked / offline). Fail loud
      // instead of dropping the submit — the server still fails closed on a bad token.
      function captchaFailed() {
        setFieldInvalid(form.querySelector('[data-auth-recaptcha]'), '請完成驗證');
        setAuthFormMsg('無法完成安全驗證，請確認網路連線或關閉廣告攔截後重試。');
      }
      executeRecaptchaV3(form)
        .then(function (token) {
          if (!token) {
            captchaFailed();
            return;
          }
          setRecaptchaResponse(form, token);
          clearFieldInvalid(form.querySelector('[data-auth-recaptcha]'));
          setAuthFormMsg('');
          if (typeof issueRequest === 'function') issueRequest(true);
        })
        .catch(captchaFailed);
    });

    form.addEventListener('htmx:afterSwap', function () {
      var errorText = extractAuthErrorMessage();
      if (errorText) mapRegisterServerError(errorText, form);
    });
  }

  function initRegisterEmailValidation(root) {
    initRegisterFormValidation(root);
  }

  global.imprintAuthShell = global.imprintAuthShell || {};
  global.imprintAuthShell.isValidRegisterEmail = isValidRegisterEmail;
  global.imprintAuthShell.setFieldInvalid = setFieldInvalid;
  global.imprintAuthShell.clearFieldInvalid = clearFieldInvalid;
  global.imprintAuthShell.validateRegisterForm = validateRegisterForm;
  global.imprintAuthShell.mapRegisterServerError = mapRegisterServerError;
  global.imprintAuthShell.executeRecaptchaV3 = executeRecaptchaV3;

  function init() {
    var container = document.querySelector('[data-auth-container]');
    if (!container) return;

    var particles = null;
    var canvas = container.querySelector('[data-auth-particles]');
    if (canvas) {
      particles = initParticles(canvas, container, function () {
        return container.classList.contains('dark');
      });
    }

    initTheme(container, particles);
    initHtmxAuthFormErrors();
    initPasswordToggles(container);
    initPhoneNumeric(container);
    initPartnerToggle(container);
    initRegisterEmailValidation(container);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})(window);
