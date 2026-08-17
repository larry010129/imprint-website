(function () {
  'use strict';

  var EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  var STEP_TEXT = {
    1: '請輸入您的 Email。我們將寄送重設密碼信件。',
    inbox: '請至信箱查看重設密碼信件。',
    2: '請在 Authenticator 應用程式中查看 6 位數驗證碼。',
    3: '請設定新密碼（至少 8 碼）。',
  };

  function showMsg(html) {
    var msg = document.getElementById('auth-form-msg');
    if (msg) msg.innerHTML = html;
  }

  function clearMsg() {
    showMsg('');
  }

  function init() {
    var wizard = document.querySelector('[data-fp-wizard]');
    if (!wizard) return;

    var currentStep = 1;
    var backupMode = false;

    var emailInput = document.getElementById('fpEmail');
    var emailHidden = document.getElementById('fpEmailHidden');
    var codeHidden = document.getElementById('fpCodeHidden');
    var stepDesc = document.querySelector('[data-fp-step-desc]');
    var emailForm = document.getElementById('fp-email-form');
    var verifyForm = document.getElementById('fp-verify-form');
    var passwordForm = document.getElementById('fp-password-form');
    var otpGroup = wizard.querySelector('[data-otp-group]');
    var otpField = wizard.querySelector('[data-otp-field]');
    var backupField = wizard.querySelector('[data-fp-backup-field]');
    var backupInput = document.getElementById('fpBackupCode');
    var backupToggle = wizard.querySelector('[data-fp-toggle-backup]');
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

    function setStep(step) {
      currentStep = step;
      wizard.querySelectorAll('[data-fp-step]').forEach(function (el) {
        el.hidden = String(el.getAttribute('data-fp-step')) !== String(step);
      });
      var indicatorN = step === 'inbox' ? 1 : Number(step);
      wizard.querySelectorAll('[data-fp-indicator]').forEach(function (el) {
        var n = Number(el.getAttribute('data-fp-indicator'));
        el.classList.toggle('is-active', n === indicatorN);
        el.classList.toggle('is-done', n < indicatorN || (step === 'inbox' && n === 1));
      });
      if (stepDesc && STEP_TEXT[step]) stepDesc.textContent = STEP_TEXT[step];
      clearMsg();
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

    function goTotp(ev) {
      if (ev) ev.preventDefault();
      var email = syncEmailHidden();
      if (!EMAIL_RE.test(email)) {
        showMsg('<div class="form-msg is-err">請輸入有效的 Email 格式。</div>');
        setStep(1);
        if (emailInput) emailInput.focus();
        return;
      }
      setStep(2);
    }

    wizard.querySelectorAll('[data-fp-use-totp]').forEach(function (el) {
      el.addEventListener('click', goTotp);
    });

    wizard.querySelectorAll('[data-fp-back]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        setStep(Number(btn.getAttribute('data-fp-back')));
      });
    });

    if (emailForm) {
      emailForm.addEventListener('submit', function (ev) {
        var email = emailInput ? emailInput.value.trim() : '';
        if (!EMAIL_RE.test(email)) {
          ev.preventDefault();
          showMsg('<div class="form-msg is-err">請輸入有效的 Email 格式。</div>');
          if (emailInput) emailInput.focus();
          return;
        }
        if (emailHidden) emailHidden.value = email;
      });

      emailForm.addEventListener('htmx:afterRequest', function (ev) {
        if (!ev.detail.successful) return;
        syncEmailHidden();
        setStep('inbox');
      });
    }

    if (backupToggle) {
      backupToggle.addEventListener('click', function (ev) {
        ev.preventDefault();
        backupMode = !backupMode;
        if (otpField) otpField.querySelector('[data-otp-group]').hidden = backupMode;
        if (backupField) backupField.hidden = !backupMode;
        backupToggle.textContent = backupMode ? '使用 6 位數驗證碼' : '使用備用碼';
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
        if (!code || (!backupMode && code.length !== 6)) {
          ev.preventDefault();
          showMsg('<div class="form-msg is-err">請輸入完整的 6 位數驗證碼。</div>');
          if (backupMode && backupInput) backupInput.focus();
          else {
            ensureOtpInit();
            if (otp) otp.focusFirst();
            else if (otpGroup) {
              var first = otpGroup.querySelector('[data-otp-digit]');
              if (first) first.focus();
            }
          }
          return;
        }
      });

      verifyForm.addEventListener('htmx:afterRequest', function (ev) {
        if (!ev.detail.successful) return;
        setStep(3);
      });
    }

    if (passwordForm) {
      passwordForm.addEventListener('submit', function (ev) {
        var pwdEl = document.getElementById('fpPassword');
        var confirmEl = document.getElementById('fpPasswordConfirm');
        var pwd = pwdEl ? pwdEl.value : '';
        var confirm = confirmEl ? confirmEl.value : '';
        if (pwd.length < 8) {
          ev.preventDefault();
          showMsg('<div class="form-msg is-err">密碼至少需要 8 碼。</div>');
          if (pwdEl) pwdEl.focus();
          return;
        }
        if (pwd !== confirm) {
          ev.preventDefault();
          showMsg('<div class="form-msg is-err">兩次密碼不一致。</div>');
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
