#!/usr/bin/env node
/**
 * Bake partials/ into HTML pages so nav/footer render without fetch.
 * Re-run after editing partials/:  node scripts/build-site-layout.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');
const PARTIALS_DIR = path.join(ROOT, 'partials');

const SKIP = new Set(['admin.html', 'template.html']);
const SKIP_DIRS = ['partials', 'shop/partials', 'scripts', 'node_modules'];

const PARTIALS = {
  topbar: 'topbar.html',
  nav: 'nav.html',
  footer: 'footer.html',
  'home-main': 'home-main.html',
  'price-reference': 'price-reference.html',
  'gold-price-main': 'gold-price-main.html',
};

const IMG_FALLBACK = `<script>window.imgFallback=function(img){var s=img.dataset.fbStep?parseInt(img.dataset.fbStep,10):0;var e=["jpg","png","jpeg"];var pic=img.parentElement&&img.parentElement.tagName==="PICTURE"?img.parentElement:null;if(s<e.length-1){s++;img.dataset.fbStep=String(s);if(pic){var srcs=pic.querySelectorAll("source");for(var i=0;i<srcs.length;i++){srcs[i].remove();}}img.src=img.src.replace(/\\.(jpg|jpeg|png)(\\?.*)?$/i,"."+e[s]+"$2");}else{(pic||img).remove();}};</script>`;

function shouldSkip(filePath) {
  const rel = path.relative(ROOT, filePath).replace(/\\/g, '/');
  if (SKIP.has(path.basename(filePath))) return true;
  return SKIP_DIRS.some((d) => rel === d || rel.startsWith(d + '/'));
}

function readPartial(name) {
  const file = PARTIALS[name];
  if (!file) throw new Error('Unknown partial: ' + name);
  return fs.readFileSync(path.join(PARTIALS_DIR, file), 'utf8');
}

function applyRoot(html, root) {
  return html.split('{{ROOT}}').join(root);
}

function siteRootFromHtml(html) {
  const m = html.match(/<body[^>]*\sdata-site-root="([^"]*)"/i);
  return m ? m[1] : '';
}

function ensureImgFallback(html) {
  if (html.includes('window.imgFallback')) return html;
  return html.replace(/(<meta charset="utf-8">\s*)/i, `$1${IMG_FALLBACK}\n`);
}

function inlineIncludes(html, root) {
  let out = html;
  for (const name of Object.keys(PARTIALS)) {
    const rendered = applyRoot(readPartial(name), root).trim();
    const slotRe = new RegExp(
      `(<!--\\s*@component partials/${name}\\.html\\s*-->\\s*)?<div data-site-include="${name}"><\\/div>`,
      'i',
    );
    if (!slotRe.test(out)) continue;
    out = out.replace(slotRe, `<!-- @component partials/${name}.html -->\n${rendered}\n`);
  }
  return out;
}

const REFRESH_PATTERNS = {
  topbar: /<!-- @component partials\/topbar\.html -->[\s\S]*?<\/div>(?=\s*\n<!-- @component partials\/nav\.html -->)/,
  nav: /<!-- @component partials\/nav\.html -->[\s\S]*?<\/header>/,
  footer: /<!-- @component partials\/footer\.html -->[\s\S]*?<\/footer>/,
  'home-main': /<!-- @component partials\/home-main\.html -->[\s\S]*?(?=\n<\/main>)/,
  'price-reference': /<!-- @component partials\/price-reference\.html -->[\s\S]*?(?=\n\s*<\/section>\s*\n<\/main>|\n\s*<\/div>\s*\n<\/section>\s*\n<\/main>)/,
  'gold-price-main': /<!-- @component partials\/gold-price-main\.html -->[\s\S]*?(?=\n\s*<\/div>\s*\n<\/section>\s*\n<\/main>)/,
};

function refreshComponents(html, root) {
  let out = html;
  for (const [name, pattern] of Object.entries(REFRESH_PATTERNS)) {
    if (!pattern.test(out)) continue;
    const rendered = applyRoot(readPartial(name), root).trim();
    out = out.replace(pattern, `<!-- @component partials/${name}.html -->\n${rendered}`);
  }
  return out;
}

function normalizeLayoutScripts(html, root) {
  const layoutSrc = `${root}js/site-layout.js?v=1.2`;
  const mainSrc = `${root}js/main.js?v=2.1`;

  html = html.replace(/\s*<script src="[^"]*site-layout\.js[^"]*"><\/script>\s*/gi, '\n');
  html = html.replace(/\s*<script src="[^"]*main\.js[^"]*"><\/script>\s*/gi, '\n');

  const bundle = `<script src="${layoutSrc}"></script>\n<script src="${mainSrc}"></script>\n`;

  const footerEnd = html.lastIndexOf('</footer>');
  if (footerEnd !== -1) {
    const insertAt = footerEnd + '</footer>'.length;
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
  if (!html.includes('data-site-include=') && !/\bsite-layout\b/.test(html)) {
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
