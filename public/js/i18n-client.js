/* Translates text that JavaScript adds after load, using the same catalog as the
   server. Loaded only on /en, /ja and /ko pages. Nothing is sent anywhere. */
(function () {
  'use strict';
  var data = window.IMPRINT_I18N;
  if (!data) return;

  var HAN = /[　-〿一-鿿＀-￯]/;
  var ATTRS = ['alt', 'title', 'placeholder', 'aria-label', 'data-label',
    'data-marquee-phrase'];
  var SKIP = 'script,style,svg,textarea,[translate="no"],[contenteditable="true"]';
  var routes = {};
  data.routes.forEach(function (r) { routes[r] = true; });

  function normalize(s) { return s.replace(/\s+/g, ' ').trim(); }
  function escapeRegex(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }

  var patterns = [];
  Object.keys(data.catalog).forEach(function (key) {
    var literal = key.split('{}').join('');
    if (key.indexOf('{}') < 0 || (literal.match(/[一-鿿]/g) || []).length < 2) return;
    patterns.push({
      short: (literal.match(/[\u4e00-\u9fff]/g) || []).length <= 3,
      size: literal.length,
      regex: new RegExp('^' + key.split('{}').map(escapeRegex).join('(.+?)') + '$'),
      target: data.catalog[key]
    });
  });
  patterns.sort(function (a, b) { return b.size - a.size; });

  // A short pattern may not swallow Chinese that has no translation.
  function unknownChinese(value) {
    return /[\u4e00-\u9fff]/.test(value) &&
      !Object.prototype.hasOwnProperty.call(data.catalog, value);
  }

  function lookup(raw) {
    if (!raw || !HAN.test(raw)) return null;
    var key = normalize(raw);
    if (Object.prototype.hasOwnProperty.call(data.catalog, key)) return data.catalog[key];
    if (key.length > 2 && key.charAt(0) === '「' && key.slice(-1) === '」') {
      var inner = lookup(key.slice(1, -1));
      if (inner !== null) return '\u201c' + inner + '\u201d';
    }
    for (var i = 0; i < patterns.length; i += 1) {
      var match = patterns[i].regex.exec(key);
      if (!match || (patterns[i].short && match.slice(1).some(unknownChinese))) continue;
      var pieces = patterns[i].target.split('{}');
      var out = pieces[0];
      for (var j = 1; j < pieces.length; j += 1) {
        var value = match[j] || '';
        out += (data.catalog[value] || value) + pieces[j];
      }
      return out;
    }
    return null;
  }

  function t(text) {
    var found = lookup(String(text));
    return found === null ? text : found;
  }

  // What we wrote, so our own changes are never translated again. Japanese output
  // and unchanged names still contain Han characters and would loop forever.
  var writtenText = new WeakMap();
  var writtenAttrs = new WeakMap();

  function translateText(node) {
    if (writtenText.get(node) === node.nodeValue) return;
    var parent = node.parentElement;
    if (!parent || parent.closest(SKIP)) return;
    var found = lookup(node.nodeValue);
    if (found === null || normalize(found) === normalize(node.nodeValue)) return;
    // An <option> without value= submits its text: keep the Chinese value.
    if (parent.tagName === 'OPTION' && !parent.hasAttribute('value')) {
      parent.setAttribute('value', normalize(node.nodeValue));
    }
    var lead = /^\s/.test(node.nodeValue) ? ' ' : '';
    var tail = /\s$/.test(node.nodeValue) ? ' ' : '';
    writtenText.set(node, lead + found + tail);
    node.nodeValue = lead + found + tail;
  }

  // Banner text split by styling (coloured "DNA", italic half of a title) is
  // saved as one sentence: translate the block, then put the styling back.
  var STYLED = '.gh-hero__lead, .gh-hero__title';

  function isOnlyStyling(child) {
    return (child.tagName === 'EM' || child.className === 'gh-dna') &&
      Array.prototype.every.call(child.children, isOnlyStyling);
  }

  function translateStyled(el) {
    if (!el.matches(STYLED) || !el.children.length ||
        !Array.prototype.every.call(el.children, isOnlyStyling)) return;
    var found = lookup(el.textContent);
    if (found === null || normalize(found) === normalize(el.textContent)) return;
    var italic = !!el.querySelector('em');
    var html = found.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    var comma = italic ? /[,，、]\s*/.exec(html) : null;
    if (comma && comma.index + comma[0].length < html.length) {
      var at = comma.index + comma[0].length;
      html = html.slice(0, at) + '<em>' + html.slice(at) + '</em>';
    }
    el.innerHTML = html.replace(/\bDNA\b/g, '<span class="gh-dna">DNA</span>');
    // Mark the new text as ours so it is never translated a second time.
    var walker = document.createTreeWalker(el, 4 /* text */);
    for (var node = walker.nextNode(); node; node = walker.nextNode()) {
      writtenText.set(node, node.nodeValue);
    }
  }

  function translateElement(el) {
    if (el.closest('[translate="no"]')) return;
    translateStyled(el);
    ATTRS.forEach(function (name) {
      var current = el.getAttribute(name);
      var mine = writtenAttrs.get(el) || {};
      if (mine[name] === current) return;
      var found = lookup(current);
      if (found === null || found === current) return;
      mine[name] = found;
      writtenAttrs.set(el, mine);
      el.setAttribute(name, found);
    });
    var href = el.tagName === 'A' ? el.getAttribute('href') : null;
    if (href && href.charAt(0) === '/' && routes[href.split(/[?#]/)[0]]) {
      el.setAttribute('href', '/' + data.lang + href);
    }
  }

  function walk(root) {
    if (root.nodeType === 3) { translateText(root); return; }
    if (root.nodeType !== 1) return;
    translateElement(root);
    var walker = document.createTreeWalker(root, 5 /* elements and text */);
    var node = walker.nextNode();
    while (node) {
      if (node.nodeType === 3) translateText(node);
      else translateElement(node);
      node = walker.nextNode();
    }
  }

  ['alert', 'confirm'].forEach(function (name) {
    var original = window[name].bind(window);
    window[name] = function (message) { return original(t(message)); };
  });
  data.t = t;

  var observer = new MutationObserver(function (changes) {
    changes.forEach(function (change) {
      if (change.type === 'characterData') translateText(change.target);
      else if (change.type === 'attributes') translateElement(change.target);
      else Array.prototype.forEach.call(change.addedNodes, walk);
    });
  });
  observer.observe(document.documentElement, {
    childList: true,
    subtree: true,
    characterData: true,
    attributes: true,
    attributeFilter: ATTRS.concat('href')
  });
  document.addEventListener('DOMContentLoaded', function () { walk(document.body); });
})();
