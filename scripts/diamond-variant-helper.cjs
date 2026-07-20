#!/usr/bin/env node
/** Helpers for diamond variant generation progress + downloads. */
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const https = require('https');

const ROOT = path.join(__dirname, '..');
const BATCHES = path.join(__dirname, 'diamond-variant-batches.json');
const PROGRESS = path.join(__dirname, 'diamond-variant-progress.json');

function loadProgress() {
  if (!fs.existsSync(PROGRESS)) {
    return { generated: [], skipped: [], failed: [] };
  }
  return JSON.parse(fs.readFileSync(PROGRESS, 'utf8'));
}

function saveProgress(prog) {
  fs.writeFileSync(PROGRESS, JSON.stringify(prog, null, 2));
}

function appendGenerated(outPaths) {
  const prog = loadProgress();
  for (const out of outPaths) {
    if (!prog.generated.includes(out)) prog.generated.push(out);
  }
  saveProgress(prog);
  return prog;
}

function appendSkipped(outPaths) {
  const prog = loadProgress();
  for (const out of outPaths) {
    if (!prog.skipped.includes(out)) prog.skipped.push(out);
  }
  saveProgress(prog);
  return prog;
}

function appendFailed(out, reason) {
  const prog = loadProgress();
  prog.failed.push({ out, reason, at: new Date().toISOString() });
  saveProgress(prog);
  return prog;
}

function pendingGroups() {
  const batches = JSON.parse(fs.readFileSync(BATCHES, 'utf8'));
  const prog = loadProgress();
  const done = new Set([...prog.generated, ...prog.skipped]);
  return batches.groups
    .map((g, i) => ({ index: i, ...g, pending: g.variants.filter((v) => !done.has(v.out) && !fs.existsSync(path.join(ROOT, v.out))) }))
    .filter((g) => g.pending.length > 0);
}

function nextGroup() {
  const groups = pendingGroups();
  if (!groups.length) return null;
  const g = groups[0];
  return {
    index: g.index,
    base: g.base,
    filename: path.basename(g.base),
    mediaConfirmDelaySec: 2,
    variants: g.pending,
  };
}

function curlPut(localPath, uploadUrl) {
  const q = process.platform === 'win32' ? '"' : "'";
  execSync(
    `curl.exe -sS -X PUT -H "Content-Type: image/png" --data-binary @${q}${localPath}${q} ${q}${uploadUrl}${q}`,
    { stdio: 'inherit' }
  );
}

function download(url, outRel) {
  const outAbs = path.join(ROOT, outRel);
  fs.mkdirSync(path.dirname(outAbs), { recursive: true });
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(outAbs);
    https
      .get(url, (res) => {
        if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
          file.close();
          fs.unlinkSync(outAbs);
          return download(res.headers.location, outRel).then(resolve).catch(reject);
        }
        if (res.statusCode !== 200) {
          file.close();
          reject(new Error(`HTTP ${res.statusCode} for ${url}`));
          return;
        }
        res.pipe(file);
        file.on('finish', () => file.close(() => resolve(outAbs)));
      })
      .on('error', reject);
  });
}

async function downloadBatch(items) {
  const saved = [];
  for (const { url, out } of items) {
    await download(url, out);
    saved.push(out);
  }
  appendGenerated(saved);
  return saved;
}

const cmd = process.argv[2];
if (cmd === 'pending') {
  const groups = pendingGroups();
  console.log(JSON.stringify({ count: groups.length, groups: groups.map((g) => ({ index: g.index, base: g.base, pending: g.pending.map((v) => v.out) })) }, null, 2));
} else if (cmd === 'next') {
  console.log(JSON.stringify(nextGroup(), null, 2));
} else if (cmd === 'put') {
  curlPut(path.join(ROOT, process.argv[3]), process.argv[4]);
} else if (cmd === 'download') {
  const arg = process.argv[3];
  const json = arg === '--file' ? fs.readFileSync(process.argv[4], 'utf8').replace(/^\uFEFF/, '') : arg;
  downloadBatch(JSON.parse(json)).then((s) => console.log('saved', s.length)).catch((e) => { console.error(e); process.exit(1); });
} else if (cmd === 'summary') {
  const batches = JSON.parse(fs.readFileSync(BATCHES, 'utf8'));
  const prog = loadProgress();
  let existSkip = 0;
  for (const g of batches.groups) {
    for (const v of g.variants) {
      if (fs.existsSync(path.join(ROOT, v.out)) && !prog.generated.includes(v.out) && !prog.skipped.includes(v.out)) existSkip++;
    }
  }
  console.log(JSON.stringify({
    totalVariants: batches.totalVariants,
    generated: prog.generated.length,
    skipped: prog.skipped.length + existSkip,
    failed: prog.failed.length,
    pending: pendingGroups().reduce((n, g) => n + g.pending.length, 0),
  }, null, 2));
} else {
  console.log('Usage: pending | next | put <baseRel> <uploadUrl> | download <json>|--file <path> | summary');
}
