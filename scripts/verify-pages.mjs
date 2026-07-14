#!/usr/bin/env node
/** Quick smoke test: layout chrome + main content present on key pages. */
const BASE = process.argv[2] || 'http://localhost:3456';

const PAGES = [
  { path: '/index.html', checks: ['class="nav"', 'hero-carousel', 'class="footer"', 'hcViewport'] },
  { path: '/account.html', checks: ['class="nav"', 'ordersList', 'class="footer"', 'site-layout.js'] },
  { path: '/shop/calculator/index.html', checks: ['class="nav"', 'shop-wizard', 'class="footer"'] },
  { path: '/jewelry/rings/classic-solitaire/index.html', checks: ['class="nav"', 'configurator', 'class="footer"'] },
];

let failed = 0;
for (const page of PAGES) {
  const url = BASE + page.path;
  const res = await fetch(url);
  if (!res.ok) {
    console.error('FAIL', page.path, res.status);
    failed += 1;
    continue;
  }
  const html = await res.text();
  const missing = page.checks.filter((c) => !html.includes(c));
  if (missing.length) {
    console.error('FAIL', page.path, 'missing:', missing.join(', '));
    failed += 1;
  } else {
    console.log('OK  ', page.path);
  }
}
process.exit(failed ? 1 : 0);
