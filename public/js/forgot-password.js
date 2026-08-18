(function () {
  'use strict';

  var EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  function showMsg(html) {
    var msg = document.getElementById('auth-form-msg');
    if (msg) msg.innerHTML = html;
  }

  function clearMsg() {
    showMsg('');
  }

  function errMsg(text) {
    showMsg('<div class="form-msg is-err">' + text + '</div>');
  }

  function init() {
    var wizard = document.querySelector('[data-fp-wizard]');
    if (!wizard) return;
    var root = (wizard.closest && wizard.closest('[data-auth-container]')) || wizard;

    var currentStep = 1;
    var backupMode = false;

    var emailInput = document.getElementById('fpEmail');
    var emailHidden = document.getElementById('fpEmailHidden');
    var codeHidden = document.getElementById('fpCodeHidden');
    var emailForm = document.getElementById('fp-email-form');
    var verifyForm = document.getElementById('fp-verify-form');
    var passwordForm = document.getElementById('fp-password-form');
    var otpGroup = wizard.querySelector('[data-otp-group]');
    var otpField = wizard.querySelector('[data-otp-field]');
    var backupField = wizard.querySelector('[data-fp-backup-field]');
    var backupInput = document.getElementById('fpBackupCode');
    var backupToggle = wizard.querySelector('[data-fp-toggle-backup]');
    var backupHidden = document.getElementById('fpBackupHidden');
    var homeHeader = root.querySelector('[data-fp-home-header]');
    var otp = null;

    function ensureOtpInit() {
      if (otp || !window.ImprintOtpInput || !otpGroup) return otp;
      otp = window.ImprintOtpInput.initGroup(otpGroup);
      return otp;
    }

    function readOtpCode() {
      if (backupMode) {
        return backupInput ? backupInput.value.trim() : '';
      }
      if (otp) return otp.getValue();
      if (window.ImprintOtpInput && otpGroup) {
        return window.ImprintOtpInput.readDigits(otpGroup);
      }
      return '';
    }

    function syncCodeHidden(code) {
      if (codeHidden) codeHidden.value = code;
    }

    function syncEmailHidden() {
      var email = emailInput ? emailInput.value.trim() : '';
      if (emailHidden && email) emailHidden.value = email;
      return email;
    }

    function readEmail() {
      return emailInput ? emailInput.value.trim() : '';
    }

    function syncBackupHidden() {
      if (backupHidden) backupHidden.value = backupMode ? '1' : '';
    }

    function setStep(step, keepMsg) {
      currentStep = step;
      root.querySelectorAll('[data-fp-step]').forEach(function (el) {
        el.hidden = String(el.getAttribute('data-fp-step')) !== String(step);
      });
      if (homeHeader) homeHeader.hidden = String(step) !== '1';
      if (!keepMsg) clearMsg();
      if (step === 'inbox') return;
      if (step === 2) {
        ensureOtpInit();
        if (!backupMode && otp) otp.focusFirst();
      }
      if (step === 3) {
        var pwd = document.getElementById('fpPassword');
        if (pwd) pwd.focus();
      }
    }

    function requireEmail() {
      var email = readEmail();
      if (!email) {
        setStep(1);
        errMsg('請輸入 Email。');
        if (emailInput) emailInput.focus();
        return '';
      }
      if (!EMAIL_RE.test(email)) {
        setStep(1);
        errMsg('請輸入有效的 Email 格式。');
        if (emailInput) emailInput.focus();
        return '';
      }
      if (emailHidden) emailHidden.value = email;
      return email;
    }

    function goTotp(ev) {
      if (ev) ev.preventDefault();
      if (!requireEmail()) return;
      setStep(2);
    }

    wizard.querySelectorAll('[data-fp-use-totp]').forEach(function (el) {
      el.addEventListener('click', goTotp);
    });

    wizard.querySelectorAll('[data-fp-back]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var target = btn.getAttribute('data-fp-back');
        setStep(target === 'inbox' ? 'inbox' : Number(target));
      });
    });

    if (emailForm) {
      emailForm.addEventListener('submit', function (ev) {
        var email = readEmail();
        if (!email) {
          ev.preventDefault();
          errMsg('請輸入 Email。');
          if (emailInput) emailInput.focus();
          return;
        }
        if (!EMAIL_RE.test(email)) {
          ev.preventDefault();
          errMsg('請輸入有效的 Email 格式。');
          if (emailInput) emailInput.focus();
          return;
        }
        if (emailHidden) emailHidden.value = email;
      });

      emailForm.addEventListener('htmx:afterRequest', function (ev) {
        if (!ev.detail.successful) return;
        syncEmailHidden();
        setStep('inbox', true);
      });
    }

    if (backupToggle) {
      backupToggle.addEventListener('click', function (ev) {
        ev.preventDefault();
        backupMode = !backupMode;
        syncBackupHidden();
        if (otpField) otpField.querySelector('[data-otp-group]').hidden = backupMode;
        if (backupField) backupField.hidden = !backupMode;
        backupToggle.textContent = backupMode ? '改用 6 位數驗證碼' : '使用備用碼';
        clearMsg();
        if (backupMode && backupInput) {
          backupInput.value = '';
          backupInput.focus();
        } else {
          ensureOtpInit();
          if (otp) otp.clear();
        }
      });
    }

    if (verifyForm) {
      verifyForm.addEventListener('submit', function (ev) {
        var code = readOtpCode();
        syncCodeHidden(code);
        syncBackupHidden();
        if (backupMode && !code) {
          ev.preventDefault();
          errMsg('請輸入備用碼');
          if (backupInput) backupInput.focus();
          return;
        }
        if (!backupMode && (!code || code.length !== 6)) {
          ev.preventDefault();
          errMsg('請輸入完整的 6 位數驗證碼。');
          ensureOtpInit();
          if (otp) otp.focusFirst();
          else if (otpGroup) {
            var first = otpGroup.querySelector('[data-otp-digit]');
            if (first) first.focus();
          }
        }
      });

      verifyForm.addEventListener('htmx:afterRequest', function (ev) {
        if (!ev.detail.successful) return;
        setStep(3, true);
      });
    }

    if (passwordForm) {
      passwordForm.addEventListener('submit', function (ev) {
        var pwdEl = document.getElementById('fpPassword');
        var confirmEl = document.getElementById('fpPasswordConfirm');
        var pwd = pwdEl ? pwdEl.value : '';
        var confirm = confirmEl ? confirmEl.value : '';
        if (!pwd || !confirm) {
          ev.preventDefault();
          errMsg('請輸入新密碼並再次確認。');
          if (pwdEl && !pwd) pwdEl.focus();
          else if (confirmEl) confirmEl.focus();
          return;
        }
        if (pwd.length < 8) {
          ev.preventDefault();
          errMsg('密碼至少需要 8 碼。');
          if (pwdEl) pwdEl.focus();
          return;
        }
        if (pwd !== confirm) {
          ev.preventDefault();
          errMsg('兩次密碼不一致。');
          if (confirmEl) confirmEl.focus();
        }
      });
    }

    setStep(1);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
