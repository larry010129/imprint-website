#!/usr/bin/env node
/**
 * Move shop-product JPG previews into thumbs/{category}/{style}.jpg
 * and populate shop/categories/*.svg from shop/styles/*-A.svg.
 *
 * Usage: node scripts/reorganize-shop-images.cjs [--dry-run]
 */
'use strict';

const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const SHOP_PRODUCT = path.join(ROOT, 'public/images/shop-product');
const SHOP = path.join(ROOT, 'public/images/shop');
const DRY = process.argv.includes('--dry-run');

const THUMB_MOVES = [
  ['墜子/項墜A.jpg', 'thumbs/pendant/A.jpg'],
  ['墜子/項墜B.jpg', 'thumbs/pendant/B.jpg'],
  ['墜子/項墜C.jpg', 'thumbs/pendant/C.jpg'],
  ['戒指/戒指A.jpg', 'thumbs/ring/A.jpg'],
  ['戒指/戒指B.jpg', 'thumbs/ring/B.jpg'],
  ['戒指/戒指C.jpg', 'thumbs/ring/C.jpg'],
  ['手鍊/手鍊A.jpg', 'thumbs/bracelet/A.jpg'],
  ['手鍊/手鍊B.jpg', 'thumbs/bracelet/B.jpg'],
  ['手鍊/手鍊C.jpg', 'thumbs/bracelet/C.jpg'],
  ['耳飾/耳飾A.jpg', 'thumbs/earring/A.jpg'],
  ['鍊條/斗圓鍊.jpg', 'thumbs/chain/A.jpg'],
  ['鍊條/斗圓鍊K玫瑰_0.jpg', 'thumbs/chain/B.jpg'],
  ['鍊條/斗圓鍊K黃_0.jpg', 'thumbs/chain/C.jpg'],
];

const OLD_DIRS = ['墜子', '戒指', '手鍊', '耳飾', '鍊條'];

const CATEGORY_SVGS = [
  ['pendant-A.svg', 'pendant.svg'],
  ['ring-A.svg', 'ring.svg'],
  ['earring-A.svg', 'earring.svg'],
  ['bracelet-A.svg', 'bracelet.svg'],
  ['chain-A.svg', 'chain.svg'],
];

function moveFile(fromRel, toRel) {
  const from = path.join(SHOP_PRODUCT, fromRel);
  const to = path.join(SHOP_PRODUCT, toRel);
  if (!fs.existsSync(from)) {
    console.warn('skip missing:', fromRel);
    return false;
  }
  if (fs.existsSync(to)) {
    console.warn('skip exists:', toRel);
    return false;
  }
  if (DRY) {
    console.log('would move', fromRel, '→', toRel);
    return true;
  }
  fs.mkdirSync(path.dirname(to), { recursive: true });
  fs.renameSync(from, to);
  console.log('moved', fromRel, '→', toRel);
  return true;
}

function copyCategorySvg(fromName, toName) {
  const from = path.join(SHOP, 'styles', fromName);
  const to = path.join(SHOP, 'categories', toName);
  if (!fs.existsSync(from)) {
    console.warn('skip missing svg:', fromName);
    return;
  }
  if (DRY) {
    console.log('would copy styles/' + fromName, '→ categories/' + toName);
    return;
  }
  fs.mkdirSync(path.dirname(to), { recursive: true });
  fs.copyFileSync(from, to);
  console.log('copied styles/' + fromName, '→ categories/' + toName);
}

function removeEmptyDirs() {
  for (const dir of OLD_DIRS) {
    const full = path.join(SHOP_PRODUCT, dir);
    if (!fs.existsSync(full)) continue;
    const left = fs.readdirSync(full);
    if (left.length === 0) {
      if (DRY) console.log('would remove empty dir:', dir);
      else fs.rmdirSync(full);
    } else {
      console.warn('dir not empty, keeping:', dir, left);
    }
  }
}

let moved = 0;
for (const [from, to] of THUMB_MOVES) {
  if (moveFile(from, to)) moved++;
}
for (const [from, to] of CATEGORY_SVGS) copyCategorySvg(from, to);
removeEmptyDirs();

console.log(DRY ? `[dry-run] ${moved} thumb moves planned` : `Done. ${moved} thumbs reorganized.`);
