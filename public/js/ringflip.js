/* Jewelry ringflip scroll scene — only loaded where #rfTrack exists. */
(function () {
  'use strict';

  function boot() {
    var track = document.getElementById('rfTrack');
    if (!track) return;
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    var ring = document.getElementById('rfRing');
    var shine = document.getElementById('rfShine');
    if (!ring || !shine) return;

    var caps = track.querySelectorAll('.ringflip-caption');
    var current = 0;
    var target = 0;
    var ticking = false;

    var clamp = function (v, a, b) { return v < a ? a : v > b ? b : v; };
    var ease = function (t) { return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t; };

    var progress = function () {
      var r = track.getBoundingClientRect();
      var total = r.height - window.innerHeight;
      return total > 0 ? clamp(-r.top / total, 0, 1) : 0;
    };

    var render = function () {
      current += (target - current) * 0.09;
      if (Math.abs(target - current) < 0.0005) current = target;
      var p = current;
      var rx = 0;
      var ry = 0;
      var scale = 1;
      var t;

      if (p < 0.5) {
        t = ease(p / 0.5);
        ry = 360 * t;
        scale = 1 + 0.08 * Math.sin(Math.PI * t);
      } else {
        t = ease((p - 0.5) / 0.5);
        rx = 360 * t;
        scale = 1 + 0.08 * Math.sin(Math.PI * t);
      }
      ring.style.transform = 'rotateX(' + rx.toFixed(2) + 'deg) rotateY(' + ry.toFixed(2) + 'deg) scale(' + scale.toFixed(3) + ')';

      var seg = (p * 2) % 1;
      shine.style.transform = 'translateX(' + (-120 + 240 * ease(seg)) + '%)';
      shine.style.opacity = Math.sin(Math.PI * seg).toFixed(2);

      var step = p < 0.5 ? 0 : 1;
      caps.forEach(function (c, i) {
        c.classList.toggle('is-on', i === step && p > 0.02);
      });

      if (current !== target) {
        requestAnimationFrame(render);
      } else {
        ticking = false;
      }
    };

    var onScroll = function () {
      target = progress();
      if (!ticking) {
        ticking = true;
        requestAnimationFrame(render);
      }
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);
    onScroll();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
