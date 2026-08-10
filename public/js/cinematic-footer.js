/**
 * Home cinematic closing stage — GSAP ScrollTrigger (local vendor).
 * Reveals brand stage + quiet legal. Loads GSAP near viewport.
 * Honors prefers-reduced-motion; skips fixed-curtain anim on ≤900px.
 */
(function () {
  "use strict";

  var footer = document.querySelector("[data-cinematic-footer]");
  var reveal = document.querySelector("[data-footer-reveal]");
  if (!footer || !reveal) return;

  var reduced =
    window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var gsapReady = false;
  var booted = false;

  function loadScript(src) {
    return new Promise(function (resolve, reject) {
      var existing = document.querySelector('script[src="' + src + '"]');
      if (existing) {
        if (existing.dataset.loaded === "1") resolve();
        else existing.addEventListener("load", function () { resolve(); }, { once: true });
        return;
      }
      var s = document.createElement("script");
      s.src = src;
      s.async = true;
      s.onload = function () {
        s.dataset.loaded = "1";
        resolve();
      };
      s.onerror = reject;
      document.body.appendChild(s);
    });
  }

  function ensureGsap() {
    if (gsapReady && window.gsap && window.ScrollTrigger) {
      return Promise.resolve();
    }
    return loadScript("/static/js/vendor/gsap.min.js")
      .then(function () {
        return loadScript("/static/js/vendor/ScrollTrigger.min.js");
      })
      .then(function () {
        if (!window.gsap || !window.ScrollTrigger) {
          throw new Error("GSAP missing after load");
        }
        window.gsap.registerPlugin(window.ScrollTrigger);
        gsapReady = true;
      });
  }

  function bindMagnetic() {
    if (reduced || window.matchMedia("(pointer: coarse)").matches) return;
    var buttons = footer.querySelectorAll(
      ".sf-cinematic__stage [data-sf-magnetic]"
    );
    var rects = new Map();
    var raf = 0;
    var pending = null;

    function refreshRects() {
      buttons.forEach(function (btn) {
        rects.set(btn, btn.getBoundingClientRect());
      });
    }

    function scheduleTransform(btn, x, y) {
      pending = { btn: btn, x: x, y: y };
      if (raf) return;
      raf = window.requestAnimationFrame(function () {
        raf = 0;
        if (!pending) return;
        var next = pending;
        pending = null;
        next.btn.style.transform =
          "translate(" + (next.x * 0.18).toFixed(1) + "px," +
          (next.y * 0.18).toFixed(1) + "px)";
      });
    }

    refreshRects();
    window.addEventListener("resize", refreshRects, { passive: true });
    buttons.forEach(function (btn) {
      btn.addEventListener("pointerenter", refreshRects);
      btn.addEventListener("pointermove", function (e) {
        var rect = rects.get(btn);
        if (!rect) return;
        var x = e.clientX - rect.left - rect.width / 2;
        var y = e.clientY - rect.top - rect.height / 2;
        scheduleTransform(btn, x, y);
      });
      btn.addEventListener("pointerleave", function () {
        pending = null;
        btn.style.transform = "";
      });
    });
  }

  function bootAnimations() {
    if (booted) return;
    booted = true;

    bindMagnetic();

    if (reduced || window.matchMedia("(max-width:900px)").matches) {
      return;
    }

    ensureGsap()
      .then(function () {
        var gsap = window.gsap;
        var giant = footer.querySelector("[data-sf-giant]");
        var stages = footer.querySelectorAll("[data-sf-reveal]");

        footer.classList.add("is-sf-ready");

        if (giant) {
          gsap.fromTo(
            giant,
            { yPercent: -6 },
            {
              yPercent: 10,
              ease: "none",
              scrollTrigger: {
                trigger: reveal,
                start: "top bottom",
                end: "bottom bottom",
                /* Soft lag — scrub:true fights native scroll and feels jumpy */
                scrub: 0.9,
              },
            }
          );
        }

        if (stages.length) {
          gsap.to(stages, {
            opacity: 1,
            y: 0,
            duration: 0.7,
            stagger: 0.12,
            ease: "power2.out",
            scrollTrigger: {
              trigger: reveal,
              start: "top 70%",
              toggleActions: "play none none reverse",
            },
          });
        }
      })
      .catch(function () {
        footer.classList.remove("is-sf-ready");
      });
  }

  if ("IntersectionObserver" in window) {
    var observer = new IntersectionObserver(function (entries) {
      if (!entries.some(function (entry) { return entry.isIntersecting; })) return;
      observer.disconnect();
      bootAnimations();
    }, { rootMargin: "35% 0px" });
    observer.observe(reveal);
  } else {
    /* Older browsers get one deferred boot instead of a geometry read per scroll. */
    window.addEventListener("load", bootAnimations, { once: true });
    setTimeout(bootAnimations, 8000);
  }
})();

