/* Additive CSS fallbacks for old engines (in-store kiosk, 2016–2020 Chromium).
   Used by legacy-build.cjs on esbuild's pretty-printed output (one declaration
   per line). A fallback line is inserted *before* each declaration that old
   engines drop as invalid (min/max/clamp, color-mix, env, dvh, gap on grid):
   modern browsers still apply the original because it comes later; old
   engines discard the original and keep the fallback. Never removes anything. */
'use strict';

/* Reference viewport for resolving min()/max()/clamp() to one static value:
   roughly the portrait kiosk / an old iPad. */
const REF = { w: 1024, h: 1280, rem: 16 };

const FN_RE = /(?<![\w-])(min|max|clamp|color-mix|env)\(/;
const UNSUPPORTED_RE = /(?<![\w-])(?:min|max|clamp|color-mix|env)\(|\d(?:dvh|svh|lvh|dvw|svw|lvw)\b/;

/* ---- tiny helpers ----------------------------------------------------- */

function matchParen(str, open) {
  let depth = 0;
  for (let i = open; i < str.length; i++) {
    if (str[i] === '(') depth++;
    else if (str[i] === ')' && --depth === 0) return i;
  }
  return -1;
}

function splitArgs(str) {
  const out = [];
  let depth = 0;
  let cur = '';
  for (const ch of str) {
    if (ch === '(') depth++;
    if (ch === ')') depth--;
    if (ch === ',' && depth === 0) {
      out.push(cur.trim());
      cur = '';
    } else cur += ch;
  }
  if (cur.trim()) out.push(cur.trim());
  return out;
}

/* ---- lengths: evaluate simple calc expressions to px ------------------- */

function evalLength(expr) {
  const src = expr.replace(/calc\(/g, '(');
  const tokens = src.match(/-?\d*\.?\d+(?:e-?\d+)?[a-z%]*|[-+*/()]/gi);
  if (!tokens || tokens.join('').replace(/\s/g, '') !== src.replace(/\s/g, '')) return null;
  let i = 0;
  const unitPx = { px: 1, rem: REF.rem, em: REF.rem, vw: REF.w / 100, vh: REF.h / 100,
    vmin: Math.min(REF.w, REF.h) / 100, vmax: Math.max(REF.w, REF.h) / 100 };
  function atom() {
    const t = tokens[i++];
    if (t === '(') {
      const v = sum();
      if (tokens[i++] !== ')') throw new Error('paren');
      return v;
    }
    if (t === '-') {
      const r = atom();
      return { n: -r.n, len: r.len };
    }
    const m = /^(-?\d*\.?\d+(?:e-?\d+)?)([a-z%]*)$/i.exec(t || '');
    if (!m) throw new Error('token');
    const n = parseFloat(m[1]);
    const unit = m[2].toLowerCase();
    if (!unit) return { n, len: false };
    if (!(unit in unitPx)) throw new Error('unit');
    return { n: n * unitPx[unit], len: true };
  }
  function product() {
    let v = atom();
    while (tokens[i] === '*' || tokens[i] === '/') {
      const op = tokens[i++];
      const r = atom();
      if (op === '*') v = { n: v.n * r.n, len: v.len || r.len };
      else v = { n: v.n / r.n, len: v.len };
    }
    return v;
  }
  function sum() {
    let v = product();
    while (tokens[i] === '+' || tokens[i] === '-') {
      const op = tokens[i++];
      const r = product();
      v = { n: op === '+' ? v.n + r.n : v.n - r.n, len: v.len || r.len };
    }
    return v;
  }
  try {
    const v = sum();
    if (i !== tokens.length) return null;
    return v.len || v.n === 0 ? v.n : null;
  } catch (_) {
    return null;
  }
}

function asValue(arg) {
  const a = arg.trim();
  if (/^calc\(/.test(a) || !/\s[-+*/]\s|[*/]/.test(a)) return a;
  return `calc(${a})`;
}

function pickMinMaxClamp(name, args) {
  const px = args.map(evalLength);
  if (px.every((v) => v !== null)) {
    let v;
    if (name === 'min') v = Math.min(...px);
    else if (name === 'max') v = Math.max(...px);
    else v = Math.min(Math.max(px[1], px[0]), px[2]);
    return `${Math.round(v * 100) / 100}px`;
  }
  if (name === 'clamp') return asValue(args[1]);
  const relative = (a) => /%|v[wh]\b|vmin|vmax/.test(a);
  if (name === 'min') return asValue(args.find(relative) || args[0]);
  return asValue(args.find((a) => !relative(a)) || args[0]);
}

/* ---- colors ------------------------------------------------------------ */

const NAMED = { white: [255, 255, 255, 1], black: [0, 0, 0, 1], transparent: [0, 0, 0, 0] };

function parseColor(str, vars, seen = new Set()) {
  const s = str.trim().toLowerCase();
  const v = /^var\(\s*(--[\w-]+)\s*(?:,\s*(.+))?\)$/.exec(s);
  if (v) {
    if (vars.has(v[1]) && !seen.has(v[1])) {
      seen.add(v[1]);
      return parseColor(vars.get(v[1]), vars, seen);
    }
    return v[2] ? parseColor(v[2], vars, seen) : null;
  }
  if (NAMED[s]) return NAMED[s].slice();
  let m = /^#([0-9a-f]{3,8})$/.exec(s);
  if (m) {
    let h = m[1];
    if (h.length === 3 || h.length === 4) h = h.split('').map((c) => c + c).join('');
    if (h.length !== 6 && h.length !== 8) return null;
    const n = (k) => parseInt(h.slice(k, k + 2), 16);
    return [n(0), n(2), n(4), h.length === 8 ? n(6) / 255 : 1];
  }
  m = /^rgba?\(([^)]+)\)$/.exec(s);
  if (m) {
    const parts = m[1].split(/[\s,/]+/).filter(Boolean);
    if (parts.length < 3) return null;
    const ch = parts.slice(0, 3).map((p) => (p.endsWith('%') ? parseFloat(p) * 2.55 : parseFloat(p)));
    let a = parts[3] === undefined ? 1 : parts[3].endsWith('%') ? parseFloat(parts[3]) / 100 : parseFloat(parts[3]);
    if ([...ch, a].some(Number.isNaN)) return null;
    return [...ch, a];
  }
  return null;
}

function colorMix(args, vars) {
  if (args.length !== 3 || !/^in\s+srgb$/i.test(args[0])) return null;
  const parse = (a) => {
    const m = /^(.*?)(?:\s+(\d*\.?\d+)%)?$/.exec(a.trim());
    const pct = /^(\d*\.?\d+)%\s+(.*)$/.exec(a.trim());
    if (pct) return { c: parseColor(pct[2], vars), p: parseFloat(pct[1]) };
    return { c: parseColor(m[1], vars), p: m[2] === undefined ? null : parseFloat(m[2]) };
  };
  const a = parse(args[1]);
  const b = parse(args[2]);
  if (!a.c || !b.c) return null;
  let p1 = a.p;
  let p2 = b.p;
  if (p1 === null && p2 === null) p1 = p2 = 50;
  else if (p1 === null) p1 = 100 - p2;
  else if (p2 === null) p2 = 100 - p1;
  const total = p1 + p2;
  if (total <= 0) return null;
  const w1 = p1 / total;
  const w2 = p2 / total;
  const alpha = a.c[3] * w1 + b.c[3] * w2;
  const out = [0, 1, 2].map((k) =>
    alpha === 0 ? 0 : Math.round((a.c[k] * a.c[3] * w1 + b.c[k] * b.c[3] * w2) / alpha));
  const finalA = Math.round(alpha * Math.min(total, 100) / 100 * 1000) / 1000;
  return finalA >= 1 ? `rgb(${out.join(', ')})` : `rgba(${out.join(', ')}, ${finalA})`;
}

/* Custom properties that hold one plain colour everywhere they are set. */
function collectColorVars(cssTexts) {
  const seen = new Map();
  for (const css of cssTexts) {
    for (const m of css.matchAll(/(--[\w-]+)\s*:\s*([^;{}]+);/g)) {
      const name = m[1];
      const val = m[2].trim();
      if (!seen.has(name)) seen.set(name, new Set());
      seen.get(name).add(val.toLowerCase());
    }
  }
  const vars = new Map();
  for (const [name, vals] of seen) if (vals.size === 1) vars.set(name, [...vals][0]);
  for (const [name, val] of [...vars]) if (!parseColor(val, vars)) vars.delete(name);
  return vars;
}

/* ---- value rewriting --------------------------------------------------- */

function rewriteValue(value, vars) {
  let out = value.replace(/(\d)(?:d|s|l)v([hw])\b/g, '$1v$2');
  for (let guard = 0; guard < 50; guard++) {
    const m = FN_RE.exec(out);
    if (!m) break;
    const start = m.index;
    const open = start + m[1].length;
    const close = matchParen(out, open);
    if (close < 0) return null;
    const inner = rewriteValue(out.slice(open + 1, close), vars);
    if (inner === null) return null;
    const args = splitArgs(inner);
    let rep;
    if (m[1] === 'env') rep = args[1] !== undefined ? args.slice(1).join(', ') : '0px';
    else if (m[1] === 'color-mix') rep = colorMix(args, vars);
    else rep = args.length >= (m[1] === 'clamp' ? 3 : 1) ? pickMinMaxClamp(m[1], args) : null;
    if (rep === null) return null;
    out = out.slice(0, start) + rep + out.slice(close + 1);
  }
  return UNSUPPORTED_RE.test(out) ? null : out;
}

const GAP_ALIAS = { gap: 'grid-gap', 'row-gap': 'grid-row-gap', 'column-gap': 'grid-column-gap' };
const DECL_RE = /^(\s+)([a-z][a-z-]*)\s*:\s*(.*?);\s*$/;

/* Returns { css, added } with fallback declarations inserted. */
function addFallbacks(css, vars) {
  let added = 0;
  const lines = css.split('\n');
  const out = [];
  for (const line of lines) {
    const m = DECL_RE.exec(line);
    if (m) {
      const [, indent, prop, value] = m;
      let fallback = value;
      if (UNSUPPORTED_RE.test(value)) {
        fallback = rewriteValue(value, vars);
        if (fallback !== null && fallback !== value) {
          out.push(`${indent}${prop}: ${fallback};`);
          added++;
        }
      }
      if (GAP_ALIAS[prop] && fallback !== null && !UNSUPPORTED_RE.test(fallback)) {
        out.push(`${indent}${GAP_ALIAS[prop]}: ${fallback};`);
        added++;
      }
    }
    out.push(line);
  }
  return { css: out.join('\n'), added };
}

module.exports = { addFallbacks, collectColorVars, rewriteValue, evalLength, colorMix };
