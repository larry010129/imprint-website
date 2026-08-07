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
    buttons.forEach(function (btn) {
      btn.addEventListener("pointermove", function (e) {
        var rect = btn.getBoundingClientRect();
        var x = e.clientX - rect.left - rect.width / 2;
        var y = e.clientY - rect.top - rect.height / 2;
        btn.style.transform =
          "translate(" + (x * 0.18).toFixed(1) + "px," + (y * 0.18).toFixed(1) + "px)";
      });
      btn.addEventListener("pointerleave", function () {
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

  function nearFooter() {
    var rect = reveal.getBoundingClientRect();
    return rect.top < window.innerHeight * 1.35;
  }

  function onScrollOrIdle() {
    if (nearFooter()) {
      bootAnimations();
      window.removeEventListener("scroll", onScrollOrIdle);
    }
  }

  window.addEventListener("scroll", onScrollOrIdle, { passive: true });
  if (document.readyState === "complete") {
    onScrollOrIdle();
  } else {
    window.addEventListener("load", onScrollOrIdle, { once: true });
  }
  setTimeout(onScrollOrIdle, 8000);
})();

