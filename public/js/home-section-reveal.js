/**
 * Home section scroll — same GSAP stagger as cinematic footer stage.
 * Desktop only; sticky peel CSS handles section stacking.
 * Mobile / reduced-motion: leave IntersectionObserver in main.js.
 */
(function () {
  "use strict";

  if (!document.body.classList.contains("page-home")) return;

  var reduced =
    window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var desktop =
    window.matchMedia && window.matchMedia("(min-width:901px)").matches;
  if (reduced || !desktop) return;

  var stacks = document.querySelectorAll("[data-home-stack]");
  if (!stacks.length) return;

  stacks.forEach(function (section, i) {
    section.style.setProperty("--home-stack-i", String(i + 1));
  });

  document.documentElement.classList.add("home-gsap-sections");

  function loadScript(src) {
    return new Promise(function (resolve, reject) {
      var existing = document.querySelector('script[src="' + src + '"]');
      if (existing) {
        if (existing.dataset.loaded === "1") resolve();
        else
          existing.addEventListener(
            "load",
            function () {
              resolve();
            },
            { once: true }
          );
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
    if (window.gsap && window.ScrollTrigger) {
      window.gsap.registerPlugin(window.ScrollTrigger);
      return Promise.resolve();
    }
    return loadScript("/static/js/vendor/gsap.min.js").then(function () {
      return loadScript("/static/js/vendor/ScrollTrigger.min.js");
    }).then(function () {
      if (!window.gsap || !window.ScrollTrigger) {
        throw new Error("GSAP missing");
      }
      window.gsap.registerPlugin(window.ScrollTrigger);
    });
  }

  function boot() {
    ensureGsap()
      .then(function () {
        var gsap = window.gsap;
        stacks.forEach(function (section) {
          var targets = section.querySelectorAll(".reveal, .reveal-media");
          if (!targets.length) return;

          gsap.set(targets, { opacity: 0, y: 28 });

          gsap.to(targets, {
            opacity: 1,
            y: 0,
            duration: 0.7,
            stagger: 0.12,
            ease: "power2.out",
            scrollTrigger: {
              trigger: section,
              start: "top 70%",
              toggleActions: "play none none reverse",
            },
            onStart: function () {
              targets.forEach(function (el) {
                el.classList.add("is-in");
              });
            },
          });
        });
      })
      .catch(function () {
        document.documentElement.classList.remove("home-gsap-sections");
        document.querySelectorAll(".reveal, .reveal-media").forEach(function (el) {
          el.classList.add("is-in");
        });
      });
  }

  if (document.readyState === "complete") boot();
  else window.addEventListener("load", boot, { once: true });
})();
