/* Minify public/js/*.js and public/css/*.css in place for production builds.
   Runs during render-build.sh, after the repo checkout — public/ in git stays
   human-readable; only the deployed build output gets minified.
   esbuild's non-bundling transform() never renames top-level/global names, so
   it's safe even though these are classic <script> tags sharing global scope
   (not ES modules) and some cross-file calls rely on bare global names.
   Run manually with: node scripts/minify-static.cjs */
const fs = require('fs');
const path = require('path');
const esbuild = require('esbuild');

const ROOT = path.join(__dirname, '..');
const JS_DIR = path.join(ROOT, 'public', 'js');
const CSS_DIR = path.join(ROOT, 'public', 'css');

function listFiles(dir, ext) {
  return fs.readdirSync(dir, { withFileTypes: true })
    .filter((e) => e.isFile() && e.name.endsWith(ext) && !e.name.endsWith(`.min${ext}`))
    .map((e) => path.join(dir, e.name));
}

async function minifyFile(file, loader) {
  const src = fs.readFileSync(file, 'utf8');
  const { code, warnings } = await esbuild.transform(src, { loader, minify: true });
  for (const w of warnings) console.warn(`[minify-static] ${path.basename(file)}: ${w.text}`);
  fs.writeFileSync(file, code);
  return { before: Buffer.byteLength(src), after: Buffer.byteLength(code) };
}

async function main() {
  const jsFiles = listFiles(JS_DIR, '.js');
  const cssFiles = listFiles(CSS_DIR, '.css');

  let beforeTotal = 0;
  let afterTotal = 0;

  for (const file of jsFiles) {
    const { before, after } = await minifyFile(file, 'js');
    beforeTotal += before;
    afterTotal += after;
  }
  for (const file of cssFiles) {
    const { before, after } = await minifyFile(file, 'css');
    beforeTotal += before;
    afterTotal += after;
  }

  const saved = beforeTotal - afterTotal;
  const pct = beforeTotal ? ((saved / beforeTotal) * 100).toFixed(1) : '0.0';
  console.log(
    `[minify-static] ${jsFiles.length} JS + ${cssFiles.length} CSS files: ` +
    `${beforeTotal} -> ${afterTotal} bytes (saved ${saved}, ${pct}%)`,
  );
}

main().catch((err) => {
  console.error('[minify-static] failed:', err);
  process.exit(1);
});
