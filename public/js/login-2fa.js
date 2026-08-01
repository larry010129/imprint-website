(function () {
  'use strict';
  var toggle = document.getElementById('toggle-backup-mode');
  var input = document.getElementById('l2faCode');
  var label = document.querySelector('label[for="l2faCode"]');
  if (!toggle || !input) return;
  var backupMode = false;
  toggle.addEventListener('click', function (e) {
    e.preventDefault();
    backupMode = !backupMode;
    if (backupMode) {
      input.removeAttribute('pattern');
      input.setAttribute('maxlength', '16');
      input.setAttribute('autocomplete', 'off');
      if (label) label.textContent = '備用碼';
      toggle.textContent = '使用 6 位數驗證碼';
    } else {
      input.setAttribute('pattern', '[0-9\\s-]*');
      input.setAttribute('maxlength', '12');
      input.setAttribute('autocomplete', 'one-time-code');
      if (label) label.textContent = '6 位數驗證碼';
      toggle.textContent = '使用備用碼';
    }
    input.value = '';
    input.focus();
  });
})();
