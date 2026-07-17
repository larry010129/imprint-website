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
    initPasswordToggles(container);
    initPhoneNumeric(container);
    initPartnerToggle(container);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})(window);
