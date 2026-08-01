(function (global) {

  'use strict';



  function readDigitsFromGroup(group) {

    if (!group) return '';

    return Array.prototype.slice.call(group.querySelectorAll('[data-otp-digit]'))

      .map(function (input) {

        return input.value;

      })

      .join('');

  }



  function syncHiddenTarget(group, inputs) {

    var targetId = group.getAttribute('data-otp-target');

    if (!targetId) return;

    var hidden = document.getElementById(targetId);

    if (hidden) {

      hidden.value = inputs.map(function (input) {

        return input.value;

      }).join('');

    }

  }



  function initOtpGroup(group) {

    if (!group) return null;

    if (group.dataset.otpBound === '1') {

      return group._imprintOtpApi || null;

    }

    group.dataset.otpBound = '1';



    var inputs = Array.prototype.slice.call(group.querySelectorAll('[data-otp-digit]'));

    if (inputs.length === 0) return;



    function valueAt(index) {

      return (inputs[index] && inputs[index].value) || '';

    }



    function setFilledState() {

      inputs.forEach(function (input) {

        input.classList.toggle('is-filled', input.value.length > 0);

      });

      var complete = inputs.every(function (input) {

        return input.value.length === 1;

      });

      group.classList.toggle('is-complete', complete);

      var field = group.closest('[data-otp-field]');

      if (field) field.classList.toggle('is-complete', complete);

      syncHiddenTarget(group, inputs);

    }



    function focusAt(index) {

      if (index < 0) index = 0;

      if (index >= inputs.length) index = inputs.length - 1;

      inputs[index].focus();

      inputs[index].select();

    }



    function fillFromString(str, startIndex) {

      var digits = String(str || '').replace(/\D/g, '');

      if (!digits) return startIndex;

      var idx = startIndex;

      for (var i = 0; i < digits.length && idx < inputs.length; i += 1) {

        inputs[idx].value = digits.charAt(i);

        idx += 1;

      }

      setFilledState();

      if (idx < inputs.length) focusAt(idx);

      else focusAt(inputs.length - 1);

      return idx;

    }



    function clearAll() {

      inputs.forEach(function (input) {

        input.value = '';

      });

      setFilledState();

      focusAt(0);

    }



    inputs.forEach(function (input, index) {

      input.addEventListener('input', function () {

        var digit = input.value.replace(/\D/g, '').slice(-1);

        input.value = digit;

        setFilledState();

        if (digit && index < inputs.length - 1) {

          focusAt(index + 1);

        }

      });



      input.addEventListener('keydown', function (ev) {

        if (ev.key === 'Backspace') {

          if (input.value) {

            input.value = '';

            setFilledState();

            return;

          }

          if (index > 0) {

            ev.preventDefault();

            inputs[index - 1].value = '';

            setFilledState();

            focusAt(index - 1);

          }

          return;

        }

        if (ev.key === 'ArrowLeft' && index > 0) {

          ev.preventDefault();

          focusAt(index - 1);

          return;

        }

        if (ev.key === 'ArrowRight' && index < inputs.length - 1) {

          ev.preventDefault();

          focusAt(index + 1);

          return;

        }

        if (ev.key === 'Delete') {

          input.value = '';

          setFilledState();

        }

      });



      input.addEventListener('paste', function (ev) {

        ev.preventDefault();

        var text = (ev.clipboardData || global.clipboardData).getData('text');

        fillFromString(text, index);

      });



      input.addEventListener('focus', function () {

        inputs.forEach(function (el, i) {

          el.classList.toggle('is-active', i === index);

        });

      });



      input.addEventListener('blur', function () {

        input.classList.remove('is-active');

      });

    });



    var api = {

      getValue: function () {

        return readDigitsFromGroup(group);

      },

      clear: clearAll,

      focusFirst: function () {

        focusAt(0);

      },

      isComplete: function () {

        return inputs.every(function (input) {

          return input.value.length === 1;

        });

      },

    };

    group._imprintOtpApi = api;

    return api;

  }



  function initOtpFields(root) {

    (root || document).querySelectorAll('[data-otp-group]').forEach(initOtpGroup);

  }



  global.ImprintOtpInput = {

    init: initOtpFields,

    initGroup: initOtpGroup,

    readDigits: readDigitsFromGroup,

  };



  if (document.readyState === 'loading') {

    document.addEventListener('DOMContentLoaded', function () {

      initOtpFields(document);

    });

  } else {

    initOtpFields(document);

  }

})(window);


