/* Nav dropdown — "safe triangle" hover intent.
   Progressive enhancement over the CSS :hover/:focus-within fallback in nav.css.
   Without this script the menu still works, just closes the instant the
   pointer leaves the trigger. With it, moving the pointer diagonally from
   the nav link toward the open panel (through the gap between them) keeps
   the panel open, instead of it snapping shut mid-move. */
(function () {
  'use strict';

  if (!window.matchMedia || !window.matchMedia('(hover: hover) and (pointer: fine)').matches) {
    return;
  }

  var CLOSE_DELAY = 300; // ms grace window to finish crossing into the panel
  var POLL_STEPS = 20;
  var mouseX = 0;
  var mouseY = 0;

  document.addEventListener('mousemove', function (e) {
    mouseX = e.clientX;
    mouseY = e.clientY;
  }, { passive: true });

  function sign(x1, y1, x2, y2, x3, y3) {
    return (x1 - x3) * (y2 - y3) - (x2 - x3) * (y1 - y3);
  }

  function pointInTriangle(px, py, ax, ay, bx, by, cx, cy) {
    var d1 = sign(px, py, ax, ay, bx, by);
    var d2 = sign(px, py, bx, by, cx, cy);
    var d3 = sign(px, py, cx, cy, ax, ay);
    var hasNeg = d1 < 0 || d2 < 0 || d3 < 0;
    var hasPos = d1 > 0 || d2 > 0 || d3 > 0;
    return !(hasNeg && hasPos);
  }

  function setup(item) {
    var dropdown = item.querySelector(':scope > .dropdown');
    if (!dropdown) return;

    var toggle = item.querySelector(':scope > .dd-toggle');
    var closeTimer = null;

    function open() {
      if (closeTimer) {
        clearTimeout(closeTimer);
        closeTimer = null;
      }
      document.querySelectorAll('.nav-item.is-open').forEach(function (other) {
        if (other !== item) other.classList.remove('is-open');
      });
      item.classList.add('is-open');
      if (toggle) toggle.setAttribute('aria-expanded', 'true');
    }

    function close() {
      item.classList.remove('is-open');
      if (toggle) toggle.setAttribute('aria-expanded', 'false');
    }

    function scheduleClose() {
      if (closeTimer) clearTimeout(closeTimer);

      // The "safe triangle": the point where the cursor left the trigger,
      // plus the dropdown panel's top-left/top-right corners. As long as the
      // cursor keeps moving inside that triangle, treat it as heading for
      // the panel and hold the menu open.
      var rect = dropdown.getBoundingClientRect();
      var apexX = mouseX;
      var apexY = mouseY;
      var topLeftX = rect.left;
      var topLeftY = rect.top;
      var topRightX = rect.right;
      var topRightY = rect.top;

      var steps = 0;
      function poll() {
        steps += 1;
        if (item.matches(':hover') || dropdown.matches(':hover')) {
          closeTimer = null;
          return;
        }
        var stillHeading = pointInTriangle(
          mouseX, mouseY,
          apexX, apexY,
          topLeftX, topLeftY,
          topRightX, topRightY
        );
        if (stillHeading && steps < POLL_STEPS) {
          closeTimer = setTimeout(poll, CLOSE_DELAY / POLL_STEPS);
          return;
        }
        close();
        closeTimer = null;
      }
      // Grace period before the first check too, so a pointer already in
      // transit toward the panel isn't judged on a single stale sample.
      closeTimer = setTimeout(poll, CLOSE_DELAY / POLL_STEPS);
    }

    item.addEventListener('mouseenter', open);
    item.addEventListener('mouseleave', scheduleClose);
    dropdown.addEventListener('mouseenter', open);
    dropdown.addEventListener('mouseleave', scheduleClose);

    item.addEventListener('focusin', open);
    item.addEventListener('focusout', function (e) {
      if (!item.contains(e.relatedTarget)) close();
    });
  }

  function init() {
    document.querySelectorAll('.nav-menu[data-safe-triangle-menu] > .nav-item').forEach(setup);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
}());
