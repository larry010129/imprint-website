#!/usr/bin/env node
/**
 * Process ALL missing diamond variants via Higgsfield nano_banana_pro + reference edit.
 * Requires: run from repo root with Higgsfield MCP available to the agent, OR use as
 * a manifest driver while the agent calls MCP per group.
 *
 * This script uploads base PNGs and prints generate_image payloads for the agent.
 * Ponytail: agent loop calls next-diamond-batch.cjs + MCP tools per group.
 */
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const ROOT = path.join(__dirname, '..');
const LOG = path.join(__dirname, 'higgsfield-job-log.txt');
const PROGRESS = path.join(__dirname, 'diamond-variant-progress.json');

function loadProgress() {
  if (!fs.existsSync(PROGRESS)) return { generated: [], failed: [] };
  return JSON.parse(fs.readFileSync(PROGRESS, 'utf8'));
}

function saveProgress(p) {
  fs.writeFileSync(PROGRESS, JSON.stringify(p, null, 2));
}

function log(msg) {
  const line = `[${new Date().toISOString()}] ${msg}\n`;
  fs.appendFileSync(LOG, line);
  console.log(msg);
}

function nextGroup() {
  const out = execSync(`node "${path.join(__dirname, 'next-diamond-batch.cjs')}"`, { encoding: 'utf8' }).trim();
  if (out === 'ALL_DONE') return null;
  return JSON.parse(out);
}

// Print status only when run directly
if (require.main === module) {
  const p = loadProgress();
  const missing = execSync(`node "${path.join(__dirname, 'list-missing-diamond-variants.cjs')}"`, { encoding: 'utf8' });
  console.log(missing.trim());
  console.log(`Generated so far: ${p.generated.length}, failed: ${p.failed.length}`);
  const n = nextGroup();
  if (n) console.log(`Next group: ${n.productId} ${n.base} (${n.pending.length} variants)`);
}

module.exports = { nextGroup, loadProgress, saveProgress, log, ROOT, LOG, PROGRESS };
