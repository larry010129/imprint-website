"""Merge white/fancy price-tab panels into single tables with extra columns."""
from pathlib import Path
import re

path = Path(__file__).resolve().parent.parent / "app/views/partials/price-page-body.html"
text = path.read_text(encoding="utf-8")

white_label = re.search(
    r'<label for="ptWhite" class="price-tab">(.+?)</label>',
    text,
    re.S,
).group(1)
fancy_label = re.search(
    r'<label for="ptFancy" class="price-tab">(.+?)</label>',
    text,
    re.S,
).group(1)

single_rows = [
    ("0.10 克拉", "0.10–0.15ct", "NT$ 24,000", "無法製作", False, False),
    ("0.20 克拉", "0.20–0.25ct", "NT$ 48,000", "無法製作", False, False),
    ("0.30 克拉", "0.30–0.35ct", "NT$ 79,000", "NT$ 102,000", True, True),
    ("0.50 克拉", "0.50–0.55ct", "NT$ 98,000", "NT$ 127,000", True, True),
    ("0.60 克拉", "0.60–0.65ct", "NT$ 113,000", "NT$ 147,000", True, True),
    ("0.70 克拉", "0.70–0.75ct", "NT$ 133,000", "NT$ 172,000", True, True),
    ("0.80 克拉", "0.80–0.85ct", "NT$ 159,000", "NT$ 206,000", True, True),
    ("0.90 克拉", "0.90–0.95ct", "NT$ 200,000", "NT$ 260,000", True, True),
    ("1.00 克拉", "1.00–1.25ct", "NT$ 250,000", "NT$ 325,000", True, True),
    ("1.50 克拉", "1.50–1.75ct", "NT$ 380,000", "NT$ 494,000", True, True),
    ("2.00 克拉", "2.00–2.50ct", "NT$ 700,000", "NT$ 910,000", True, True),
    ("3.00 克拉", "3.00–3.50ct", "NT$ 990,000", "NT$ 1,287,000", True, True),
]


def cell(val: str, *, amt: bool) -> str:
    if val == "無法製作":
        return '<td class="na">無法製作</td>'
    cls = "amt" if amt else ""
    return f'<td class="{cls}">{val}</td>' if cls else f"<td>{val}</td>"


def row(carat, rng, white, fancy, w_amt, f_amt) -> str:
    return (
        f"<tr><td>{carat}</td><td>{rng}</td>"
        f'{cell(white, amt=w_amt)}{cell(fancy, amt=f_amt)}</tr>'
    )


single_body = "\n                ".join(row(*r) for r in single_rows)
single_table = f"""      <div class="price-scroll reveal reveal-d3">
        <table class="price-full-table price-full-table--dual">
          <thead><tr>
            <th>克拉</th>
            <th>實際區間</th>
            <th class="price-col-head"><span class="price-col-label">{white_label}</span></th>
            <th class="price-col-head"><span class="price-col-label">{fancy_label}</span></th>
          </tr></thead>
          <tbody>
                {single_body}
                <tr class="is-note"><td colspan="4">彩鑽最低製作規格 0.30 克拉；3.00 克拉以上或特殊克拉數，請洽官方 LINE 專屬報價</td></tr>
          </tbody>
        </table>
      </div>"""

multi_table = f"""      <div class="price-scroll reveal reveal-d3">
        <table class="price-full-table price-full-table--multi-dual">
          <thead>
            <tr>
              <th rowspan="2">克拉</th>
              <th colspan="3" class="price-col-head"><span class="price-col-label">{white_label}</span></th>
              <th colspan="3" class="price-col-head"><span class="price-col-label">{fancy_label}</span></th>
            </tr>
            <tr>
              <th>2 顆</th><th>3 顆</th><th>4 顆</th>
              <th>2 顆</th><th>3 顆</th><th>4 顆</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>0.10 克拉<br><small style="color:var(--ink-faint);">0.08–0.14ct</small></td>
              <td class="amt">NT$ 45,600</td><td class="amt">NT$ 61,200</td><td class="amt">NT$ 81,000</td>
              <td class="na" colspan="3">彩鑽 0.30 克拉以上</td>
            </tr>
            <tr>
              <td>0.20 克拉<br><small style="color:var(--ink-faint);">0.15–0.24ct</small></td>
              <td class="amt">NT$ 86,400</td><td class="amt">NT$ 122,400</td><td class="amt">NT$ 162,000</td>
              <td class="na" colspan="3">彩鑽 0.30 克拉以上</td>
            </tr>
            <tr>
              <td>0.30 克拉<br><small style="color:var(--ink-faint);">0.25–0.34ct</small></td>
              <td class="amt">NT$ 142,200</td><td class="amt">NT$ 189,600</td><td class="amt">NT$ 250,000</td>
              <td class="amt">NT$ 173,400</td><td class="amt">NT$ 244,800</td><td class="amt">NT$ 322,300</td>
            </tr>
            <tr class="is-note">
              <td>0.30 克拉以上</td>
              <td>單顆價 × 顆數・85 折</td><td>單顆價 × 顆數・8 折</td><td>單顆價 × 顆數・75 折</td>
              <td>單顆價 × 顆數・85 折</td><td>單顆價 × 顆數・8 折</td><td>單顆價 × 顆數・75 折</td>
            </tr>
          </tbody>
        </table>
      </div>"""

# First price-tabset (single diamond)
text = re.sub(
    r'<div class="price-tabset reveal reveal-d3">.*?</div>\s*</div>\s*\n\s*<div class="price-block">',
    single_table + '\n    </div>\n\n    <div class="price-block">',
    text,
    count=1,
    flags=re.S,
)

# Second price-tabset (multi stone) — ends before shapes include
text = re.sub(
    r'<div class="price-tabset reveal reveal-d3">.*?</div>\s*</div>\s*\n\s*\{% include "partials/diamond-shapes-inline.html" %\}',
    multi_table + '\n    </div>\n\n    {% include "partials/diamond-shapes-inline.html" %}',
    text,
    count=1,
    flags=re.S,
)

text = text.replace(
    "完整克拉價格表：白鑽／彩鑽切換",
    "完整克拉價格表：白鑽／彩鑽並列",
)
path.write_text(text, encoding="utf-8")
print("merged price columns")
