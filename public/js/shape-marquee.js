/** Horizontal shape marquee — auto-scroll, drag, hover slow. No deps. */
(function () {
  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  document.querySelectorAll("[data-shape-marquee]").forEach(function (root) {
    var inner = root.querySelector(".shape-marquee-inner");
    var row = root.querySelector(".shape-marquee-row");
    if (!inner || !row) return;

    var clone = row.cloneNode(true);
    clone.setAttribute("aria-hidden", "true");
    inner.appendChild(clone);

    var x = 0;
    var base = reduced ? 0 : 36;
    var hoverFactor = 1;
    var dragVel = 0;
    var dragging = false;
    var lastX = 0;
    var rowW = 0;

    function measure() {
      rowW = row.getBoundingClientRect().width;
    }
    measure();
    window.addEventListener("resize", measure);

    root.addEventListener("mouseenter", function () {
      hoverFactor = 0.3;
    });
    root.addEventListener("mouseleave", function () {
      hoverFactor = 1;
    });

    root.addEventListener("pointerdown", function (e) {
      if (e.button !== 0) return;
      dragging = true;
      lastX = e.clientX;
      dragVel = 0;
      root.setPointerCapture(e.pointerId);
      root.classList.add("is-dragging");
    });

    root.addEventListener("pointermove", function (e) {
      if (!dragging) return;
      var dx = e.clientX - lastX;
      lastX = e.clientX;
      dragVel = dx * 2.5;
      x += dx;
    });

    function endDrag(e) {
      if (!dragging) return;
      dragging = false;
      root.classList.remove("is-dragging");
      try {
        root.releasePointerCapture(e.pointerId);
      } catch (_err) {
        /* pointer already released */
      }
    }
    root.addEventListener("pointerup", endDrag);
    root.addEventListener("pointercancel", endDrag);

    var prev = performance.now();
    function tick(now) {
      var dt = Math.min((now - prev) / 1000, 0.05);
      prev = now;

      if (!dragging) {
        x += (-base * hoverFactor + dragVel) * dt;
        dragVel *= 0.94;
        if (Math.abs(dragVel) < 0.3) dragVel = 0;
      }

      if (rowW > 0) {
        while (x <= -rowW) x += rowW;
        while (x > 0) x -= rowW;
      }

      inner.style.transform = "translate3d(" + x + "px,0,0)";
      requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  });
})();
