const fs = require('fs');
const path = require('path');

const src = fs.readFileSync(
  'c:/Users/user/Documents/diamond calculator/imprint-calculator/shop/templates/partials/shop_markup.html',
  'utf8',
);
const ringGuide = fs.readFileSync(
  'c:/Users/user/Documents/diamond calculator/imprint-calculator/shop/templates/partials/ring_size_guide_inline.html',
  'utf8',
);

const chart = [
  [4, 1.30, 4.10], [5, 1.35, 4.25], [6, 1.40, 4.39], [7, 1.45, 4.55], [8, 1.50, 4.71], [9, 1.55, 4.87],
  [10, 1.60, 5.02], [11, 1.65, 5.18], [12, 1.70, 5.34], [13, 1.75, 5.50], [14, 1.80, 5.65], [15, 1.85, 5.81],
  [16, 1.90, 5.97], [17, 1.95, 6.12], [18, 2.00, 6.28], [19, 2.05, 6.44], [20, 2.10, 6.59], [21, 2.15, 6.75],
  [22, 2.20, 6.91],
];

let ringInline = ringGuide.replace(/\{%[\s\S]*?%\}/g, '').replace(/\{\{[\s\S]*?\}\}/g, '');
const rows = chart.map(([size, d, c]) =>
  `          <tr><th scope="row">#${size}</th><td>${d.toFixed(2)}</td><td>${c.toFixed(2)}</td></tr>`,
).join('\n');
ringInline = ringInline.replace(/<tbody>[\s\S]*?<\/tbody>/, `<tbody>\n${rows}\n        </tbody>`);

let body = src
  .replace(/\{% set shop_mode[^%]+%\}/g, '')
  .replace(/\{% if edit_sub %\}[\s\S]*?\{% endif %\}/g, '')
  .replace(/\{% if shop_mode == 'guest' %\}[\s\S]*?\{% endif %\}/g, '')
  .replace(/\{% if preview_mode %\}[\s\S]*?\{% endif %\}/g, '')
  .replace(/\{% include ['"]shop\/partials\/ring_size_guide_inline.html['"] %\}/, ringInline)
  .replace(/\{% set studio_credit_modifier[^%]+%\}/g, '')
  .replace(/\{% include ['"]layout\/studio_credit.html['"] %\}/g, '')
  .replace(/\{% if shop_mode == 'order' %\}/g, '')
  .replace(/\{% elif shop_mode == 'guest' %\}[\s\S]*?(?=\{% endif %\})/g, '')
  .replace(/\{% if not edit_sub and not cart_edit_config %\}/g, '')
  .replace(/\{% if shop_mode != 'preview' %\}/g, '')
  .replace(/\{% if not edit_sub and not cart_edit_config %} data-i18n="btn_add_order"{% endif %\}/g, ' data-i18n="btn_add_order"')
  .replace(/\{% if cart_edit_config %\}更新購物車{% elif edit_sub %\}更新訂單{% else %\}訂購{% endif %\}/g, '訂購')
  .replace(/\{% if cart_edit_config %\}更新{% elif edit_sub %\}更新{% else %\}訂購{% endif %\}/g, '訂購')
  .replace(/\{% endif %\}/g, '');

const outDir = path.join(__dirname, '..', 'shop', 'partials');
fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(path.join(outDir, 'shop-markup.html'), body.trim());
console.log('Wrote shop-markup.html');
