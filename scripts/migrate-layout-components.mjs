#!/usr/bin/env node
/**
 * Migrate static HTML pages to component-based layout (partials/ + site-layout.js).
 * Run: node scripts/migrate-layout-components.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');

const SKIP_FILES = new Set(['admin.html', 'template.html', 'index.html']);
const SKIP_DIRS = ['partials', 'shop/partials', 'scripts', 'node_modules'];

const LAYOUT_VERSION = '1.1';
const MAIN_VERSION = '1.9';

function shouldSkip(filePath) {
  const rel = path.relative(ROOT, filePath).replace(/\\/g, '/');
  if (SKIP_FILES.has(path.basename(filePath))) return true;
  return SKIP_DIRS.some((d) => rel === d || rel.startsWith(d + '/'));
}

function siteRootFor(filePath) {
  const dir = path.dirname(path.relative(ROOT, filePath));
  if (!dir || dir === '.') return '';
  const depth = dir.split(path.sep).length;
  return '../'.repeat(depth);
}

function siteActiveFor(relPath) {
  const p = relPath.replace(/\\/g, '/').toLowerCase();
  if (p.includes('shop/calculator')) return 'shop';
  if (p === 'price.html' || p === 'gold-price.html') return 'shop';
  if (p === 'diamonds.html' || p.startsWith('series/')) return 'diamonds';
  if (p.startsWith('jewelry/')) return 'jewelry';
  if (p === 'what-is-dna-diamond.html' || p === 'faq.html') return 'knowledge';
  if (p === 'about.html' || p === 'stories.html' || p === 'contact.html') return 'about';
  if (p === 'track-order.html') return 'track-order';
  if (['account.html', 'login.html', 'register.html', 'reset-password.html'].includes(p)) {
    return 'account';
  }
  return '';
}

function headStylesBlock(root) {
  return [
    '<!-- @component partials/head-common.html -->',
    `<link rel="icon" type="image/svg+xml" href="${root}favicon.svg">`,
    `<link rel="stylesheet" href="${root}css/base.css?v=3.7">`,
    `<link rel="stylesheet" href="${root}css/nav.css?v=3.7">`,
    `<link rel="stylesheet" href="${root}css/home.css?v=3.7">`,
    `<link rel="stylesheet" href="${root}css/pages.css?v=3.7">`,
    `<link rel="stylesheet" href="${root}css/responsive.css?v=3.7">`,
  ].join('\n');
}

function stripLayout(html) {
  if (html.includes('data-site-include="nav"')) return html;
  html = html.replace(/<!--\s*@component partials\/topbar\.html\s*-->\s*/gi, '');
  html = html.replace(/<!--\s*@component partials\/nav\.html\s*-->\s*/gi, '');
  html = html.replace(/<!--\s*@component partials\/footer\.html\s*-->\s*/gi, '');
  html = html.replace(/<!--\s*頂部公告列\s*-->\s*/gi, '');
  html = html.replace(/<!--\s*Footer\s*-->\s*/gi, '');
  html = html.replace(/<!--\s*導覽列[^]*?-->\s*/gi, '');
  html = html.replace(/<div class="topbar">[\s\S]*?<\/div>\s*/i, '');
  html = html.replace(/<header class="nav">[\s\S]*?<\/header>\s*/i, '');
  html = html.replace(/<footer class="footer">[\s\S]*?<\/footer>\s*/i, '');
  return html;
}

function normalizeHead(html, root) {
  const block = headStylesBlock(root);
  html = html.replace(
    /<!-- @component partials\/head-common\.html -->[\s\S]*?<link rel="stylesheet" href="[^"]*responsive\.css[^"]*">\s*/i,
    block + '\n',
  );
  html = html.replace(
    /<link rel="icon" type="image\/svg\+xml" href="[^"]*">\s*<link rel="stylesheet" href="[^"]*base\.css[^"]*">[\s\S]*?<link rel="stylesheet" href="[^"]*responsive\.css[^"]*">\s*/i,
    block + '\n',
  );
  return html;
}

function setBodyAttrs(html, root, active) {
  return html.replace(/<body([^>]*)>/i, (_m, attrs) => {
    let next = attrs || '';
    next = next.replace(/\sdata-site-root="[^"]*"/i, '');
    next = next.replace(/\sdata-site-active="[^"]*"/i, '');
    next = next.replace(/\sclass="site-layout"/i, '');
    next += ` data-site-root="${root}"`;
    if (active) next += ` data-site-active="${active}"`;
    if (!/\sclass="/i.test(next)) next += ' class="site-layout"';
    return `<body${next}>`;
  });
}

function injectLayoutSlots(html) {
  const slots = [
    '<!-- @component partials/layout-topbar.html -->',
    '<div data-site-include="layout-topbar"></div>',
    '<!-- @component partials/layout-nav.html -->',
    '<div data-site-include="layout-nav"></div>',
    '',
  ].join('\n');

  if (/<div data-site-include="topbar"><\/div>/i.test(html)) {
    return html.replace(
      /<!-- @component partials\/(?:layout-topbar|topbar)\.html -->[\s\S]*?<div data-site-include="(?:layout-nav|nav)"><\/div>\s*/i,
      slots,
    );
  }

  return html.replace(/(<body[^>]*>)\s*/i, `$1\n${slots}`);
}

function injectFooterSlot(html) {
  const slot = [
    '',
    '<!-- @component partials/layout-footer.html -->',
    '<div data-site-include="layout-footer"></div>',
    '',
  ].join('\n');

  if (/<div data-site-include="footer"><\/div>/i.test(html)) {
    return html;
  }

  if (/<\/main>/i.test(html)) {
    return html.replace(/<\/main>\s*/i, `</main>\n${slot}`);
  }
  return html.replace(/<\/body>/i, `${slot}</body>`);
}

function ensureLayoutScripts(html, root) {
  const layoutSrc = `${root}js/site-layout.js?v=${LAYOUT_VERSION}`;
  const mainSrc = `${root}js/main.js?v=${MAIN_VERSION}`;

  html = html.replace(/\s*<script src="[^"]*site-layout\.js[^"]*"><\/script>\s*/gi, '\n');
  html = html.replace(/\s*<script src="[^"]*main\.js[^"]*"><\/script>\s*/gi, '\n');

  const bundle = [
    `<script src="${layoutSrc}"></script>`,
    `<script src="${mainSrc}"></script>`,
  ].join('\n');

  if (/<script src="[^"]*main\.js/i.test(html)) {
    return html.replace(/<script src="[^"]*main\.js[^"]*"><\/script>/i, bundle);
  }

  return html.replace(/<\/body>/i, `${bundle}\n</body>`);
}

function migrateFile(filePath) {
  const rel = path.relative(ROOT, filePath);
  const root = siteRootFor(filePath);
  const active = siteActiveFor(rel);

  let html = fs.readFileSync(filePath, 'utf8');
  if (!/<body/i.test(html)) return false;

  html = stripLayout(html);
  html = normalizeHead(html, root);
  html = setBodyAttrs(html, root, active);
  html = injectLayoutSlots(html);
  html = injectFooterSlot(html);
  html = ensureLayoutScripts(html, root);

  fs.writeFileSync(filePath, html, 'utf8');
  return true;
}

function walk(dir, out = []) {
  for (const name of fs.readdirSync(dir)) {
    const full = path.join(dir, name);
    const stat = fs.statSync(full);
    if (stat.isDirectory()) {
      walk(full, out);
    } else if (name.endsWith('.html')) {
      out.push(full);
    }
  }
  return out;
}

let count = 0;
for (const file of walk(ROOT)) {
  if (shouldSkip(file)) continue;
  if (migrateFile(file)) {
    count += 1;
    console.log('  migrated:', path.relative(ROOT, file));
  }
}
console.log(`Done — ${count} page(s) use component layout.`);
