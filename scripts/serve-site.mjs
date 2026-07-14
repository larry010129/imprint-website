#!/usr/bin/env node
/**
 * Local dev server with /api/bot-gold for live BOT gold quotes.
 * Usage: npm run dev  (or node scripts/serve-site.mjs)
 */
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import { exec } from 'node:child_process';

const require = createRequire(import.meta.url);
const { findGoldBarPrices, isBotChallenge } = require('../backend/lib/parseBotGold.js');

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');
const START_PORT = Number(process.env.PORT) || 8080;
const BOT_HOST = 'rate.bot.com.tw';
const BOT_HEADERS = {
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
  Accept: 'text/html,application/xhtml+xml',
};
const PURITY_MULTIPLIER = { '9k': 0.5, '14k': 0.75, '18k': 0.85, pt950: 1.1, s925: 0.925 };
const METAL_BASE = { '9k': 'XAU', '14k': 'XAU', '18k': 'XAU', pt950: 'XPT', s925: 'XAG' };

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.ico': 'image/x-icon',
  '.xml': 'application/xml',
  '.woff2': 'font/woff2',
};

function safePath(urlPath) {
  const decoded = decodeURIComponent(urlPath.split('?')[0]);
  const normalized = path.normalize(decoded).replace(/^(\.\.[/\\])+/, '');
  const full = path.join(ROOT, normalized);
  if (!full.startsWith(ROOT)) return null;
  return full;
}

function buildAlloyRates(raw) {
  const alloy = {};
  for (const gold of Object.keys(PURITY_MULTIPLIER)) {
    const symbol = METAL_BASE[gold];
    if (raw[symbol] != null) alloy[gold] = raw[symbol] * PURITY_MULTIPLIER[gold];
  }
  return alloy;
}

async function scrapeBotJson() {
  const urls = [
    'https://rate.bot.com.tw/gold/quote/recent',
    'https://rate.bot.com.tw/gold?Lang=zh-TW',
  ];
  let lastError = null;
  for (const url of urls) {
    try {
      const res = await fetch(url, { headers: BOT_HEADERS, redirect: 'follow' });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const html = await res.text();
      if (isBotChallenge(html)) throw new Error('BOT challenge');
      const parsed = findGoldBarPrices(html);
      if (!parsed) throw new Error('parse failed');
      const now = new Date();
      const raw = { XAU: parsed.perGram, XPT: 1050, XAG: 30 };
      return {
        refreshed: true,
        quote: {
          available: true,
          sell: parsed.perGram,
          source: 'bot',
          bot_posted_at: parsed.stamp || null,
          fetched_at: now.toISOString(),
          fetched_at_display: now.toLocaleString('zh-TW', { timeZone: 'Asia/Taipei', hour12: false }),
          is_stale: false,
          source_url: url,
        },
        alloyRates: buildAlloyRates(raw),
      };
    } catch (err) {
      lastError = err;
    }
  }
  throw lastError || new Error('BOT scrape failed');
}

function proxyBot(res, botPath) {
  const url = 'https://' + BOT_HOST + botPath;
  fetch(url, { redirect: 'follow', headers: BOT_HEADERS })
    .then((upstream) => upstream.text().then((html) => {
      res.writeHead(upstream.status || 200, {
        'Content-Type': upstream.headers.get('content-type') || 'text/html; charset=utf-8',
        'Cache-Control': 'no-store',
      });
      res.end(html);
    }))
    .catch((err) => {
      res.writeHead(502, { 'Content-Type': 'text/plain; charset=utf-8' });
      res.end('BOT proxy error: ' + err.message);
    });
}

function serveFile(res, filePath) {
  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(err.code === 'ENOENT' ? 404 : 500);
      res.end(err.code === 'ENOENT' ? 'Not found' : 'Read error');
      return;
    }
    res.writeHead(200, { 'Content-Type': MIME[path.extname(filePath)] || 'application/octet-stream' });
    res.end(data);
  });
}

function createHandler(port) {
  return (req, res) => {
    const url = new URL(req.url, `http://127.0.0.1:${port}`);

    if (url.pathname === '/api/bot-gold' && req.method === 'GET') {
      scrapeBotJson()
        .then((payload) => {
          res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' });
          res.end(JSON.stringify(payload));
        })
        .catch((err) => {
          res.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' });
          res.end(JSON.stringify({ error: String(err.message || err) }));
        });
      return;
    }

    if (url.pathname.startsWith('/bot-gold')) {
      const botPath = url.pathname.slice('/bot-gold'.length) || '/';
      proxyBot(res, botPath + url.search);
      return;
    }

    let filePath = safePath(url.pathname === '/' ? '/index.html' : url.pathname);
    if (!filePath) {
      res.writeHead(403);
      res.end('Forbidden');
      return;
    }

    fs.stat(filePath, (err, stat) => {
      if (!err && stat.isDirectory()) filePath = path.join(filePath, 'index.html');
      serveFile(res, filePath);
    });
  };
}

function listen(port, host) {
  return new Promise((resolve, reject) => {
    const server = http.createServer(createHandler(port));
    server.on('error', (err) => reject(err));
    server.listen(port, host, () => resolve({ server, port }));
  });
}

async function findPort(start) {
  for (let port = start; port < start + 20; port += 1) {
    try {
      return await listen(port, '127.0.0.1');
    } catch (err) {
      if (err.code !== 'EADDRINUSE') throw err;
    }
  }
  throw new Error('No free port found');
}

function openBrowser(url) {
  const cmd = process.platform === 'win32' ? `start "" "${url}"`
    : process.platform === 'darwin' ? `open "${url}"`
      : `xdg-open "${url}"`;
  exec(cmd, () => {});
}

const isRender = process.env.RENDER === 'true' || Boolean(process.env.RENDER_SERVICE_ID);
const isProduction = isRender || process.env.NODE_ENV === 'production';
let port;

if (process.env.PORT) {
  port = Number(process.env.PORT);
  await listen(port, '0.0.0.0');
} else {
  ({ port } = await findPort(START_PORT));
}

const hostLabel = isProduction ? '0.0.0.0' : '127.0.0.1';
const siteUrl = isProduction
  ? `https://${process.env.RENDER_EXTERNAL_URL || 'your-app.onrender.com'}/`
  : `http://127.0.0.1:${port}/`;

console.log('');
console.log(isProduction ? '  Diamond v3 — production server' : '  Diamond v3 dev server (live BOT gold enabled)');
console.log('  Listening:', hostLabel + ':' + port);
console.log('  Site: ', siteUrl);
console.log('  Gold: ', (isProduction ? siteUrl.replace(/\/$/, '') : `http://127.0.0.1:${port}`) + '/gold-price.html');
console.log('  Live: ', (isProduction ? siteUrl.replace(/\/$/, '') : `http://127.0.0.1:${port}`) + '/api/bot-gold');
console.log('');

if (!isProduction && process.env.NO_OPEN !== '1') {
  openBrowser(`http://127.0.0.1:${port}/gold-price.html`);
}
