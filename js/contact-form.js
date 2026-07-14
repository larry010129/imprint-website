/* 銘印鑽石｜聯絡表單送出邏輯 */
(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    var form = document.getElementById('contactForm');
    if (!form) return;

    try {
      var draft = sessionStorage.getItem('shopInquiryDraft');
      if (draft && form.message && !form.message.value.trim()) {
        form.message.value = draft;
        sessionStorage.removeItem('shopInquiryDraft');
      }
    } catch (e) { /* ignore */ }

    var btn = document.getElementById('contactSubmitBtn');
    var msg = document.getElementById('contactFormMsg');

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      msg.textContent = '';
      msg.className = 'form-msg';

      if (!window.imprintAPI) {
        msg.textContent = '系統連線異常，請直接透過 LINE 或電話聯繫我們。';
        msg.className = 'form-msg is-err';
        return;
      }

      var name = form.name.value.trim();
      var phone = form.phone.value.trim();
      var email = form.email.value.trim();
      var message = form.message.value.trim();

      if (!name || !phone || !message) {
        msg.textContent = '請填寫姓名、電話與您的需求。';
        msg.className = 'form-msg is-err';
        return;
      }

      btn.disabled = true;
      btn.textContent = '送出中…';

      window.imprintAPI
        .submitContact({ name: name, phone: phone, email: email || null, message: message, sourcePage: 'contact.html' })
        .then(function (res) {
          btn.disabled = false;
          btn.textContent = '送出留言';
          if (res.error) {
            console.error('[contact-form]', res.error);
            msg.textContent = '送出失敗，請稍後再試，或直接透過 LINE／電話聯繫我們。';
            msg.className = 'form-msg is-err';
            return;
          }
          form.reset();
          msg.textContent = '已收到您的留言，顧問會盡快與您聯繫，謝謝！';
          msg.className = 'form-msg is-ok';
        });
    });
  });
})();
