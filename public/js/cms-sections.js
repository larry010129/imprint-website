/* Lightweight public interactions for modular CMS blocks. */
(function () {
  'use strict';

  var sections = document.querySelectorAll('[data-cms-reveal]');
  if (!sections.length) return;
  var reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduced || !('IntersectionObserver' in window)) {
    sections.forEach(function (section) { section.classList.add('is-visible'); });
    return;
  }

  document.documentElement.classList.add('cms-reveal-ready');
  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) return;
      entry.target.classList.add('is-visible');
      observer.unobserve(entry.target);
    });
  }, { rootMargin: '120px 0px', threshold: 0.06 });
  sections.forEach(function (section) { observer.observe(section); });
})();
