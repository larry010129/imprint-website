#!/usr/bin/env node
/**
 * Generate MVC member/auth pages from scripts/mvc-registry.mjs
 * Run: npm run generate:pages && npm run build:layout
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { MVC_PAGES, MEMBER_CSS } from './mvc-registry.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');

function pageHtml(cfg) {
  const scripts = (cfg.scripts || [])
    .map((src) => `<script src="${src}"></script>`)
    .join('\n');

  return `<!DOCTYPE html>
<html lang="zh-Hant-TW">
<head>
<meta charset="utf-8">
<script>window.imgFallback=function(img){var s=img.dataset.fbStep?parseInt(img.dataset.fbStep,10):0;var e=["jpg","png","jpeg"];var pic=img.parentElement&&img.parentElement.tagName==="PICTURE"?img.parentElement:null;if(s<e.length-1){s++;img.dataset.fbStep=String(s);if(pic){var srcs=pic.querySelectorAll("source");for(var i=0;i<srcs.length;i++){srcs[i].remove();}}img.src=img.src.replace(/\\.(jpg|jpeg|png)(\\?.*)?$/i,"."+e[s]+"$2");}else{(pic||img).remove();}};</script>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${cfg.title}｜銘印鑽石 IMPRINT DIAMOND</title>
<meta name="robots" content="noindex">
<link rel="icon" type="image/svg+xml" href="favicon.svg">
<link rel="stylesheet" href="css/base.css?v=3.7">
<link rel="stylesheet" href="css/nav.css?v=3.7">
<link rel="stylesheet" href="css/home.css?v=3.7">
<link rel="stylesheet" href="css/pages.css?v=3.7">
<link rel="stylesheet" href="css/responsive.css?v=3.7">
<link rel="stylesheet" href="${MEMBER_CSS}">
</head>
<body data-site-root="" data-site-active="${cfg.navActive}" data-mvc="${cfg.mvc}" class="site-layout">

<!-- @component partials/layout-topbar.html -->
<div data-site-include="layout-topbar"></div>
<!-- @component partials/layout-nav.html -->
<div data-site-include="layout-nav"></div>

<main>
<!-- @component partials/${cfg.view}.html -->
<div data-site-include="${cfg.view}"></div>
</main>

<!-- @component partials/layout-footer.html -->
<div data-site-include="layout-footer"></div>

<script src="js/site-layout.js?v=1.2"></script>
<script src="js/main.js?v=2.1"></script>
${scripts}
</body>
</html>
`;
}

for (const cfg of MVC_PAGES) {
  fs.writeFileSync(path.join(ROOT, cfg.file), pageHtml(cfg), 'utf8');
  console.log('  wrote', cfg.file);
}

console.log('Done — run npm run build:layout');
