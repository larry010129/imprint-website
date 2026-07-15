#!/usr/bin/env node
/**
 * Bake partials/ into HTML pages so nav/footer render without fetch.
 * Re-run after editing partials/:  npm run build:layout
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { PARTIALS } from './mvc-registry.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');
const PARTIALS_DIR = path.join(ROOT, 'partials');

const SKIP = new Set(['admin.html', 'template.html']);
const SKIP_DIRS = ['partials', 'shop/partials', 'scripts', 'node_modules', 'server'];

/** Legacy slot comment names before MVC rearrange */
const LEGACY_SLOT = {
  'layout-topbar': 'topbar',
  'layout-nav': 'nav',
  'layout-footer': 'footer',
  'layout-head': 'head-common',
  'view-home': 'home-main',
  'view-price-ref': 'price-reference',
  'view-gold-price': 'gold-price-main',
  'view-cart': 'mvc-cart',
  'view-favorites': 'mvc-favorites',
  'view-notifications': 'mvc-notifications',
  'view-history': 'mvc-history',
  'view-success': 'mvc-success',
  'view-profile': 'mvc-profile',
  'view-404': 'mvc-404',
};

const IMG_FALLBACK = `<script>window.imgFallback=function(img){var s=img.dataset.fbStep?parseInt(img.dataset.fbStep,10):0;var e=["jpg","png","jpeg"];var pic=img.parentElement&&img.parentElement.tagName==="PICTURE"?img.parentElement:null;if(s<e.length-1){s++;img.dataset.fbStep=String(s);if(pic){var srcs=pic.querySelectorAll("source");for(var i=0;i<srcs.length;i++){srcs[i].remove();}}img.src=img.src.replace(/\\.(jpg|jpeg|png)(\\?.*)?$/i,"."+e[s]+"$2");}else{(pic||img).remove();}};</script>`;

function shouldSkip(filePath) {
  const rel = path.relative(ROOT, filePath).replace(/\\/g, '/');
  if (SKIP.has(path.basename(filePath))) return true;
  return SKIP_DIRS.some((d) => rel === d || rel.startsWith(d + '/'));
}

function readPartial(slotId) {
  const file = PARTIALS[slotId];
  if (!file) throw new Error('Unknown partial: ' + slotId);
  return fs.readFileSync(path.join(PARTIALS_DIR, file), 'utf8');
}

function applyRoot(html, root) {
  return html.split('{{ROOT}}').join(root);
}

function siteRootFromHtml(html) {
  const m = html.match(/<body[^>]*\sdata-site-root="([^"]*)"/i);
  return m ? m[1] : '';
}

function commentNames(slotId) {
  const names = [slotId];
  if (LEGACY_SLOT[slotId]) names.push(LEGACY_SLOT[slotId]);
  return names;
}

function commentPattern(slotId) {
  const names = commentNames(slotId).map((n) => n.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  return new RegExp(`<!-- @component partials/(?:${names.join('|')})\\.html -->`, 'i');
}

function ensureImgFallback(html) {
  if (html.includes('window.imgFallback')) return html;
  return html.replace(/(<meta charset="utf-8">\s*)/i, `$1${IMG_FALLBACK}\n`);
}

function inlineIncludes(html, root) {
  let out = html;
  for (const slotId of Object.keys(PARTIALS)) {
    const rendered = applyRoot(readPartial(slotId), root).trim();
    const slotRe = new RegExp(
      `(<!--\\s*@component partials/(?:${commentNames(slotId).join('|')})\\.html\\s*-->\\s*)?<div data-site-include="${slotId}"><\\/div>`,
      'i',
    );
    if (!slotRe.test(out)) continue;
    out = out.replace(slotRe, `<!-- @component partials/${slotId}.html -->\n${rendered}\n`);
  }
  return out;
}

const REFRESH_END = {
  'layout-topbar': /<!-- @component partials\/(?:layout-topbar|topbar)\.html -->[\s\S]*?<\/div>(?=\s*\n<!-- @component partials\/(?:layout-nav|nav)\.html -->)/,
  'layout-nav': /<!-- @component partials\/(?:layout-nav|nav)\.html -->[\s\S]*?<script type="module" src="[^"]*nav\.js[^"]*"><\/script>/,
  'layout-footer': /<!-- @component partials\/(?:layout-footer|footer)\.html -->[\s\S]*?(?=\n<script src=)/,
  'layout-head': /<!-- @component partials\/(?:layout-head|head-common)\.html -->[\s\S]*?(?=\n<link rel="icon"|\n<link rel="stylesheet")/,
  'view-home': /<!-- @component partials\/(?:view-home|home-main)\.html -->[\s\S]*?(?=\n<\/main>)/,
  'view-price-ref': /<!-- @component partials\/(?:view-price-ref|price-reference)\.html -->[\s\S]*?(?=\n\s*<\/section>\s*\n<\/main>|\n\s*<\/div>\s*\n<\/section>\s*\n<\/main>)/,
  'view-gold-price': /<!-- @component partials\/(?:view-gold-price|gold-price-main)\.html -->[\s\S]*?(?=\n\s*<\/div>\s*\n<\/section>\s*\n<\/main>)/,
  'view-contact-form': /<!-- @component partials\/(?:view-contact-form)\.html -->[\s\S]*?(?=\n<\/main>)/,
};

function refreshComponents(html, root) {
  let out = html;
  for (const [slotId, pattern] of Object.entries(REFRESH_END)) {
    if (!PARTIALS[slotId]) continue;
    if (!pattern.test(out)) continue;
    const rendered = applyRoot(readPartial(slotId), root).trim();
    out = out.replace(pattern, `<!-- @component partials/${slotId}.html -->\n${rendered}`);
  }
  return out;
}

function normalizeLayoutScripts(html, root) {
  const layoutSrc = `${root}js/site-layout.js?v=1.2`;
  const mainSrc = `${root}js/main.js?v=2.1`;

  html = html.replace(/\s*<script src="[^"]*site-layout\.js[^"]*"><\/script>\s*/gi, '\n');
  html = html.replace(/\s*<script src="[^"]*main\.js[^"]*"><\/script>\s*/gi, '\n');

  const bundle = `<script src="${layoutSrc}"></script>\n<script src="${mainSrc}"></script>\n`;

  const footerIslandRe =
    /<!-- @component partials\/(?:layout-footer|footer)\.html -->[\s\S]*?<script type="module" src="[^"]*footer\.js[^"]*"><\/script>/;
  const footerMatch = html.match(footerIslandRe);
  if (footerMatch) {
    const insertAt = html.indexOf(footerMatch[0]) + footerMatch[0].length;
    return html.slice(0, insertAt) + '\n\n' + bundle + html.slice(insertAt).trimStart();
  }

  const bodyClose = html.lastIndexOf('</body>');
  if (bodyClose === -1) return html;

  const before = html.slice(0, bodyClose).trimEnd();
  const after = html.slice(bodyClose);
  return `${before}\n${bundle}${after}`;
}

function processFile(filePath) {
  let html = fs.readFileSync(filePath, 'utf8');
  const hasSlots = html.includes('data-site-include=');
  const hasLayout = /\bsite-layout\b/.test(html);
  const hasLegacy = Object.values(LEGACY_SLOT).some((legacy) =>
    html.includes(`@component partials/${legacy}.html`),
  );
  if (!hasSlots && !hasLayout && !hasLegacy) {
    return false;
  }

  const root = siteRootFromHtml(html);
  html = ensureImgFallback(html);
  html = refreshComponents(html, root);
  html = inlineIncludes(html, root);
  html = normalizeLayoutScripts(html, root);
  fs.writeFileSync(filePath, html, 'utf8');
  return true;
}

function walk(dir, out = []) {
  for (const name of fs.readdirSync(dir)) {
    const full = path.join(dir, name);
    if (fs.statSync(full).isDirectory()) walk(full, out);
    else if (name.endsWith('.html')) out.push(full);
  }
  return out;
}

let count = 0;
for (const file of walk(ROOT)) {
  if (shouldSkip(file)) continue;
  if (processFile(file)) {
    count += 1;
    console.log('  built:', path.relative(ROOT, file));
  }
}
console.log(`Done — inlined layout into ${count} page(s).`);
