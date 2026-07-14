const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');

function walk(dir, files = []) {
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    if (ent.name === 'node_modules' || ent.name === 'shop') continue;
    const p = path.join(dir, ent.name);
    if (ent.isDirectory()) walk(p, files);
    else if (ent.name.endsWith('.html')) files.push(p);
  }
  return files;
}

const catFromPath = (rel) => {
  if (rel.includes('jewelry\\rings\\') || rel.includes('jewelry/rings/')) return 'ring';
  if (rel.includes('jewelry\\necklaces\\') || rel.includes('jewelry/necklaces/')) return 'pendant';
  if (rel.includes('jewelry\\earrings\\') || rel.includes('jewelry/earrings/')) return 'earring';
  if (rel.includes('jewelry\\bracelets\\') || rel.includes('jewelry/bracelets/')) return 'bracelet';
  return null;
};

let count = 0;
for (const file of walk(root)) {
  if (file.includes(`${path.sep}shop${path.sep}calculator${path.sep}`)) continue;
  let html = fs.readFileSync(file, 'utf8');
  const orig = html;
  const rel = path.relative(root, file).replace(/\\/g, '/');
  const depth = rel.split('/').length - 1;
  const prefix = depth ? '../'.repeat(depth) : '';
  const cat = catFromPath(rel);
  const shopHref = cat
    ? `${prefix}shop/calculator/index.html?category=${cat}`
    : `${prefix}shop/calculator/index.html`;

  html = html.replace(
    /class="btn btn-mint btn-calc" href="[^"]*price\.html">價格試算/g,
    `class="btn btn-mint btn-calc" href="${shopHref}">開始訂製`,
  );

  if (html !== orig) {
    fs.writeFileSync(file, html, 'utf8');
    count++;
    console.log(rel);
  }
}
console.log('Updated', count, 'files');
