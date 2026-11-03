/* Polyfills for old browser engines (in-store kiosk, 2016–2020 Chromium /
   old iPads). Loaded only when the layout's inline check finds a missing API
   (partials/legacy-polyfills.html), so modern browsers never fetch this file.
   ES5 on purpose; every shim is guarded and leaves native APIs untouched. */
(function () {
  'use strict';

  function define(obj, name, value) {
    if (obj && !(name in obj)) {
      Object.defineProperty(obj, name, { value: value, configurable: true, writable: true });
    }
  }

  /* --- Object ------------------------------------------------------------ */
  define(Object, 'entries', function (o) {
    return Object.keys(o).map(function (k) { return [k, o[k]]; });
  });
  define(Object, 'values', function (o) {
    return Object.keys(o).map(function (k) { return o[k]; });
  });
  define(Object, 'fromEntries', function (iterable) {
    var out = {};
    Array.from(iterable, function (pair) { out[pair[0]] = pair[1]; });
    return out;
  });

  /* --- String / Array ---------------------------------------------------- */
  function pad(str, len, fill, atStart) {
    str = String(str);
    len = len >> 0;
    fill = fill === undefined ? ' ' : String(fill);
    if (str.length >= len || !fill) return str;
    var need = len - str.length;
    while (fill.length < need) fill += fill;
    fill = fill.slice(0, need);
    return atStart ? fill + str : str + fill;
  }
  define(String.prototype, 'padStart', function (len, fill) { return pad(this, len, fill, true); });
  define(String.prototype, 'padEnd', function (len, fill) { return pad(this, len, fill, false); });

  function flatten(arr, depth, out) {
    for (var i = 0; i < arr.length; i++) {
      if (!(i in arr)) continue;
      if (Array.isArray(arr[i]) && depth > 0) flatten(arr[i], depth - 1, out);
      else out.push(arr[i]);
    }
    return out;
  }
  define(Array.prototype, 'flat', function (depth) {
    return flatten(this, depth === undefined ? 1 : Number(depth) || 0, []);
  });
  define(Array.prototype, 'flatMap', function (fn, thisArg) {
    return flatten(this.map(fn, thisArg), 1, []);
  });

  /* --- Promise.prototype.finally ---------------------------------------- */
  if (window.Promise) {
    define(Promise.prototype, 'finally', function (fn) {
      var P = this.constructor || Promise;
      return this.then(
        function (v) { return P.resolve(fn()).then(function () { return v; }); },
        function (e) { return P.resolve(fn()).then(function () { throw e; }); }
      );
    });
  }

  /* --- DOM: append / prepend / before / after / replaceWith --------------- */
  function toNode(args) {
    if (args.length === 1 && typeof args[0] === 'object' && args[0] !== null) return args[0];
    var frag = document.createDocumentFragment();
    for (var i = 0; i < args.length; i++) {
      var n = args[i];
      frag.appendChild(typeof n === 'object' && n !== null ? n : document.createTextNode(String(n)));
    }
    return frag;
  }
  var parents = [window.Element, window.Document, window.DocumentFragment];
  for (var p = 0; p < parents.length; p++) {
    if (!parents[p]) continue;
    define(parents[p].prototype, 'append', function () {
      this.appendChild(toNode(arguments));
    });
    define(parents[p].prototype, 'prepend', function () {
      this.insertBefore(toNode(arguments), this.firstChild);
    });
  }
  var children = [window.Element, window.CharacterData, window.DocumentType];
  for (var c = 0; c < children.length; c++) {
    if (!children[c]) continue;
    define(children[c].prototype, 'before', function () {
      if (this.parentNode) this.parentNode.insertBefore(toNode(arguments), this);
    });
    define(children[c].prototype, 'after', function () {
      if (this.parentNode) this.parentNode.insertBefore(toNode(arguments), this.nextSibling);
    });
    define(children[c].prototype, 'replaceWith', function () {
      if (this.parentNode) this.parentNode.replaceChild(toNode(arguments), this);
    });
  }

  if (window.Node && !('isConnected' in Node.prototype)) {
    Object.defineProperty(Node.prototype, 'isConnected', {
      configurable: true,
      get: function () { return document.documentElement.contains(this); }
    });
  }

  define(Element.prototype, 'toggleAttribute', function (name, force) {
    var has = this.hasAttribute(name);
    var want = force === undefined ? !has : !!force;
    if (want && !has) this.setAttribute(name, '');
    if (!want && has) this.removeAttribute(name);
    return want;
  });

  if (window.NodeList) define(NodeList.prototype, 'forEach', Array.prototype.forEach);

  /* --- scrollTo / scrollBy with an options object (Chrome < 61) --------- */
  if (!('scrollBehavior' in document.documentElement.style)) {
    var nativeScrollTo = window.scrollTo;
    var nativeScrollBy = window.scrollBy;
    var x = function () { return window.pageXOffset || 0; };
    var y = function () { return window.pageYOffset || 0; };
    window.scrollTo = function (a, b) {
      if (a && typeof a === 'object') {
        return nativeScrollTo.call(window, a.left !== undefined ? a.left : x(), a.top !== undefined ? a.top : y());
      }
      return nativeScrollTo.call(window, a, b);
    };
    window.scroll = window.scrollTo;
    window.scrollBy = function (a, b) {
      if (a && typeof a === 'object') return nativeScrollBy.call(window, a.left || 0, a.top || 0);
      return nativeScrollBy.call(window, a, b);
    };
    var elScrollTo = function (a, b) {
      if (a && typeof a === 'object') {
        if (a.left !== undefined) this.scrollLeft = a.left;
        if (a.top !== undefined) this.scrollTop = a.top;
      } else {
        this.scrollLeft = a;
        this.scrollTop = b;
      }
    };
    Element.prototype.scrollTo = elScrollTo;
    Element.prototype.scroll = elScrollTo;
    Element.prototype.scrollBy = function (a, b) {
      if (a && typeof a === 'object') {
        this.scrollLeft += a.left || 0;
        this.scrollTop += a.top || 0;
      } else {
        this.scrollLeft += a || 0;
        this.scrollTop += b || 0;
      }
    };
  }

  /* --- IntersectionObserver ---------------------------------------------- */
  if (window.IntersectionObserver && window.IntersectionObserverEntry &&
      !('isIntersecting' in IntersectionObserverEntry.prototype)) {
    /* Chrome 51–57: entries lack isIntersecting, so reveal-on-scroll never fired. */
    Object.defineProperty(IntersectionObserverEntry.prototype, 'isIntersecting', {
      configurable: true,
      get: function () { return this.intersectionRatio > 0; }
    });
  }
  if (!window.IntersectionObserver) {
    /* No observer at all: report every target as visible so content shows. */
    window.IntersectionObserver = function (callback) {
      var self = this;
      self.observe = function (target) {
        setTimeout(function () {
          var r = target.getBoundingClientRect();
          callback([{ target: target, isIntersecting: true, intersectionRatio: 1,
            boundingClientRect: r, intersectionRect: r, rootBounds: null, time: Date.now() }], self);
        }, 0);
      };
      self.unobserve = function () {};
      self.disconnect = function () {};
      self.takeRecords = function () { return []; };
    };
  }

  /* --- ResizeObserver (Chrome < 64): approximate with window resize ------- */
  if (!window.ResizeObserver) {
    window.ResizeObserver = function (callback) {
      var self = this;
      var targets = [];
      var timer = 0;
      function report() {
        timer = 0;
        if (!targets.length) return;
        callback(targets.map(function (t) {
          var r = t.getBoundingClientRect();
          return { target: t, contentRect: { x: 0, y: 0, top: 0, left: 0,
            width: r.width, height: r.height, right: r.width, bottom: r.height } };
        }), self);
      }
      function onResize() { if (!timer) timer = setTimeout(report, 100); }
      self.observe = function (t) {
        if (targets.indexOf(t) === -1) targets.push(t);
        if (targets.length === 1) window.addEventListener('resize', onResize);
        onResize();
      };
      self.unobserve = function (t) {
        var i = targets.indexOf(t);
        if (i !== -1) targets.splice(i, 1);
        if (!targets.length) window.removeEventListener('resize', onResize);
      };
      self.disconnect = function () {
        targets = [];
        window.removeEventListener('resize', onResize);
      };
    };
  }

  /* --- AbortController (Chrome < 66): abort() flags the signal only;
         old fetch ignores the signal, so requests just run to completion. */
  if (!window.AbortController) {
    var Signal = function () {
      this.aborted = false;
      this.onabort = null;
      this._listeners = [];
    };
    Signal.prototype.addEventListener = function (type, fn) {
      if (type === 'abort') this._listeners.push(fn);
    };
    Signal.prototype.removeEventListener = function (type, fn) {
      var i = this._listeners.indexOf(fn);
      if (i !== -1) this._listeners.splice(i, 1);
    };
    window.AbortController = function () { this.signal = new Signal(); };
    window.AbortController.prototype.abort = function () {
      var s = this.signal;
      if (s.aborted) return;
      s.aborted = true;
      var ev = { type: 'abort', target: s };
      if (typeof s.onabort === 'function') s.onabort(ev);
      for (var i = 0; i < s._listeners.length; i++) s._listeners[i].call(s, ev);
    };
  }
})();
