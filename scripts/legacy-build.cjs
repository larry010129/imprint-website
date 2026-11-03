/* Old-browser build for the deployed site (in-store kiosk on a 2016–2020
   Chromium WebView, old iPads). Runs from render-build.sh after checkout and
   edits the *build output* in place; the files in git stay modern.

   1. public/js/*.js   — esbuild lowers syntax to JS_TARGET (?., ??, async,
                         object spread, class fields …). APIs are covered by
                         public/js/legacy-polyfills.js, loaded only when needed.
   2. public/css/*.css — esbuild lowers CSS (inset → longhands, nesting …), then
                         legacy-css.cjs inserts fallbacks before declarations
                         old engines drop (min/max/clamp, color-mix, dvh, gap).
   3. Cache busting    — ?v=N asset URLs are immutable for a year, so they get a
                         "-<ASSET_REV>" suffix (one-time bust; bump ASSET_REV
                         when this build's output changes); unversioned ones get
                         ?v=<commit>. Templates/tests in git keep plain ?v=N.

   All-or-nothing: every output is computed first and written only if all
   succeed, so a failure leaves the modern files untouched. */
'use strict';

const fs = require('fs');
const path = require('path');
const esbuild = require('esbuild');
const { addFallbacks, collectColorVars } = require('./legacy-css.cjs');

const ROOT = path.join(__dirname, '..');
const JS_DIR = path.join(ROOT, 'public', 'js');
const CSS_DIR = path.join(ROOT, 'public', 'css');
const TEMPLATE_DIR = path.join(ROOT, 'content', 'site', 'templates');

/* Chrome 51 (mid-2016) is the oldest target esbuild can lower all site JS to.
   It lacks more syntax than Safari 11 does, so it also covers old iPads (a
   Safari target is rejected: esbuild can't lower Safari's destructuring). */
const JS_TARGET = ['chrome51'];
const CSS_TARGET = ['chrome51', 'safari11'];
const ASSET_REV = 'l1';
const DEPLOY_REV = (process.env.RENDER_GIT_COMMIT || '').slice(0, 8) || Date.now().toString(36);

const ASSET_RE = /(\/(?:static\/)?(js|css)\/([\w.-]+\.(?:js|css)))(\?v=[\w.-]+)?(?=["'`)\s])/g;

function list(dir, ext) {
  return fs.readdirSync(dir, { withFileTypes: true })
    .filter((e) => e.isFile() && e.name.endsWith(ext))
    .map((e) => path.join(dir, e.name));
}

function walkHtml(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) return walkHtml(p);
    return e.name.endsWith('.html') ? [p] : [];
  });
}

function bustAssetUrls(text, known) {
  let count = 0;
  const out = text.replace(ASSET_RE, (all, url, kind, name, query) => {
    if (!known[kind].has(name)) return all;
    if (query && query.endsWith(`-${ASSET_REV}`)) return all;
    count++;
    return query ? `${url}${query}-${ASSET_REV}` : `${url}?v=${DEPLOY_REV}`;
  });
  return { text: out, count };
}

/* Marker so an accidental second run can't double-lower or double-bust. */
const DONE_MARKER = path.join(ROOT, '.legacy-build-done');

async function main() {
  if (fs.existsSync(DONE_MARKER)) {
    console.log('[legacy-build] already applied to this checkout, skipping');
    return;
  }
  const jsFiles = list(JS_DIR, '.js');
  const cssFiles = list(CSS_DIR, '.css');
  const known = {
    js: new Set(jsFiles.map((f) => path.basename(f))),
    css: new Set(cssFiles.map((f) => path.basename(f))),
  };
  const writes = new Map();
  let fallbacks = 0;
  let busted = 0;

  for (const file of jsFiles) {
    const src = fs.readFileSync(file, 'utf8');
    const { code } = await esbuild.transform(src, { loader: 'js', target: JS_TARGET, charset: 'utf8' });
    const b = bustAssetUrls(code, known);
    busted += b.count;
    writes.set(file, b.text);
  }

  const cssSources = cssFiles.map((f) => fs.readFileSync(f, 'utf8'));
  const vars = collectColorVars(cssSources);
  for (let i = 0; i < cssFiles.length; i++) {
    const { code } = await esbuild.transform(cssSources[i], { loader: 'css', target: CSS_TARGET, charset: 'utf8' });
    const r = addFallbacks(code, vars);
    fallbacks += r.added;
    writes.set(cssFiles[i], r.css);
  }

  const pages = [...walkHtml(TEMPLATE_DIR), ...list(ROOT, '.html')];
  for (const file of pages) {
    const src = fs.readFileSync(file, 'utf8');
    const b = bustAssetUrls(src, known);
    if (b.count) {
      busted += b.count;
      writes.set(file, b.text);
    }
  }

  for (const [file, text] of writes) fs.writeFileSync(file, text);
  fs.writeFileSync(DONE_MARKER, `${new Date().toISOString()} ${DEPLOY_REV}\n`);
  console.log(
    `[legacy-build] ${jsFiles.length} JS -> ${JS_TARGET.join('+')}, ${cssFiles.length} CSS ` +
    `(+${fallbacks} fallbacks, ${vars.size} colour vars), ${busted} asset URLs cache-busted`,
  );
}

main().catch((err) => {
  console.error('[legacy-build] failed, no files changed:', err.message || err);
  process.exit(1);
});
