/* Register terms — force-read dialog before checkbox can be checked. */
(function (global) {
  'use strict';

  function scrollNearBottom(el) {
    if (!el) return true;
    var max = el.scrollHeight - el.clientHeight;
    return max <= 8 || el.scrollTop / max >= 0.98;
  }

  function openRegisterTermsDialog(onAgree) {
    var dialog = document.getElementById('register-terms-dialog');
    if (!dialog || typeof dialog.showModal !== 'function') {
      onAgree(true);
      return;
    }
    // Clicking the checkbox bubbles to the wrapping label, so this runs twice —
    // a second showModal() on an open dialog throws and kills the handler.
    if (dialog.open) return;

    var scroll = dialog.querySelector('.register-terms-scroll');
    var agreeBtn = dialog.querySelector('#register-terms-agree');
    var hint = dialog.querySelector('#register-terms-scroll-hint');
    var readBottom = false;

    function setReadBottom(ok) {
      readBottom = ok;
      if (agreeBtn) agreeBtn.disabled = !ok;
      if (hint) hint.hidden = ok;
      dialog.querySelector('.register-terms-footer')?.classList.toggle('register-terms-footer--ready', ok);
    }

    function onScroll() {
      if (readBottom) return;
      if (scrollNearBottom(scroll)) setReadBottom(true);
    }

    function cleanup() {
      scroll?.removeEventListener('scroll', onScroll);
      dialog.removeEventListener('cancel', onCancel);
      declineBtn?.removeEventListener('click', onDecline);
      agreeBtn?.removeEventListener('click', onAgreeClick);
    }

    function onCancel(e) {
      e.preventDefault();
    }

    function onDecline() {
      cleanup();
      dialog.close();
      onAgree(false);
    }

    function onAgreeClick() {
      if (!readBottom) return;
      cleanup();
      dialog.close();
      onAgree(true);
    }

    var declineBtn = dialog.querySelector('#register-terms-decline');
    declineBtn?.addEventListener('click', onDecline);
    agreeBtn?.addEventListener('click', onAgreeClick);
    scroll?.addEventListener('scroll', onScroll, { passive: true });
    dialog.addEventListener('cancel', onCancel);

    if (scroll) scroll.scrollTop = 0;
    setReadBottom(false);
    dialog.showModal();
    requestAnimationFrame(onScroll);
  }

  function bindRegisterTermsCheckbox() {
    var checkbox = document.getElementById('rAcceptTerms');
    var trigger = document.getElementById('registerTermsTrigger');
    if (!checkbox || !trigger) return;

    function requestTerms() {
      openRegisterTermsDialog(function (agreed) {
        checkbox.checked = !!agreed;
        checkbox.dispatchEvent(new Event('change', { bubbles: true }));
      });
    }

    // Force-read: user cannot tick the box without opening the dialog.
    checkbox.addEventListener('click', function (ev) {
      ev.preventDefault();
      if (checkbox.checked) {
        checkbox.checked = false;
        return;
      }
      requestTerms();
    });

    trigger.addEventListener('click', function (ev) {
      ev.preventDefault();
      requestTerms();
    });

    document.querySelectorAll('[data-register-terms-open]').forEach(function (el) {
      el.addEventListener('click', function (ev) {
        ev.preventDefault();
        requestTerms();
      });
    });
  }

  global.imprintRegisterTerms = {
    open: openRegisterTermsDialog,
    bind: bindRegisterTermsCheckbox,
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindRegisterTermsCheckbox);
  } else {
    bindRegisterTermsCheckbox();
  }
})(window);
