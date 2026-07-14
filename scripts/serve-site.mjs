#!/usr/bin/env node
/**
 * Static site + GET /api/bot-gold for live BOT gold quotes.
 * Render: npm start  |  Local: npm run dev
 */
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import { exec } from 'node:child_process';

const require = createRequire(import.meta.url);
const handleBotGold = require('../api/bot-gold.js');

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');
const START_PORT = Number(process.env.PORT) || 8080;

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
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
};

function safePath(urlPath) {
  const decoded = decodeURIComponent(urlPath.split('?')[0]);
  const relative = decoded.replace(/^\/+/, '');
  if (!relative) return null;
  const normalized = path.normalize(relative).replace(/^(\.\.([/\\]|$))+/, '');
  const rootResolved = path.resolve(ROOT);
  const full = path.resolve(rootResolved, normalized);
  if (full !== rootResolved && !full.startsWith(rootResolved + path.sep)) return null;
  return full;
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

    if (url.pathname === '/api/bot-gold') {
      handleBotGold(req, res);
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

const base = isProduction
  ? (process.env.RENDER_EXTERNAL_URL ? `https://${process.env.RENDER_EXTERNAL_URL}` : `http://127.0.0.1:${port}`)
  : `http://127.0.0.1:${port}`;

console.log('');
console.log(isProduction ? '  Diamond v3 on Render' : '  Diamond v3 local dev');
console.log('  Site:', base + '/');
console.log('  Gold:', base + '/gold-price.html');
console.log('  API: ', base + '/api/bot-gold');
console.log('');

if (!isProduction && process.env.NO_OPEN !== '1') {
  openBrowser(base + '/gold-price.html');
}
