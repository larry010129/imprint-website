"""Port site/price.html main content into imprint partial."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
src = Path(r"c:\Users\yuzi0\Documents\site\price.html").read_text(encoding="utf-8")

start = src.index('<section class="pricing"')
end = src.index('<section class="prose-section"', start)
body = src[start:end]

# Drop hero — pricing section starts without page-hero
body = body.replace('style="padding-top:90px;"', 'class="pricing pricing--solo"')
body = re.sub(r'<section class="pricing"[^>]*>', '<section class="pricing pricing--solo">', body, count=1)

# Imprint URL paths
replacements = {
    "series-first-love.html": "/series/first-love/",
    "series-pet.html": "/series/pet/",
    "series-love.html": "/series/love/",
    "series-family.html": "/series/family/",
    "series-heirloom.html": "/series/heirloom/",
    "price.html": "/price.html",
    "what-is-dna-diamond.html": "/what-is-dna-diamond.html",
}
for old, new in replacements.items():
    body = body.replace(f'href="{old}"', f'href="{new}"')

# Shapes block → shared partial (no per-card +10%)
shape_start = body.index('<div class="price-block" style="margin-bottom:0;">')
shape_end = body.index("\n\n  </div>\n</section>", shape_start)
body = (
    body[:shape_start]
    + '{% include "partials/diamond-shapes-inline.html" %}\n\n'
    + body[shape_end:]
)

# Include prose section from site
prose_start = src.index('<section class="prose-section"')
prose_end = src.index("</section>", prose_start) + len("</section>")
body += "\n" + src[prose_start:prose_end]
for old, new in replacements.items():
    body = body.replace(f'href="{old}"', f'href="{new}"')

dest = ROOT / "app/views/partials/price-page-body.html"
dest.write_text(body, encoding="utf-8")
print(f"wrote {dest} ({len(body)} chars)")

# Inline shapes (inside price-detail container, not full-page section)
shapes_src = (ROOT / "app/views/partials/diamond-shapes-inline.html").read_text(encoding="utf-8")
inline = re.search(
    r'<div class="diamond-shapes-block"[^>]*>.*?</div>\s*\n\s*<p class="shape-pricing-legend',
    shapes_src,
    re.S,
)
if inline:
    legend = '    <p class="shape-pricing-legend reveal reveal-d3">圓形明亮式為牌價基準 · 非圓形切工加價依款式試算</p>\n'
    block = inline.group(0).split("<p class=\"shape-pricing-legend")[0].rstrip() + "\n" + legend
    block = block.replace("diamond-shapes-block", "price-block price-block--shapes")
    block = block.replace("diamond-shapes-head", "price-block-head")
    block = re.sub(r"<h1 ", "<h2 ", block, count=1)
    block = re.sub(r"</h1>", "</h2>", block, count=1)
    (ROOT / "app/views/partials/diamond-shapes-inline.html").write_text(block, encoding="utf-8")
    print("wrote diamond-shapes-inline.html")
