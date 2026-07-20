from pathlib import Path
import re

text = Path("app/views/partials/price-page-body.html").read_text(encoding="utf-8")
parts = re.findall(
    r'<th class="price-col-head"><span class="price-col-label">(.+?)</span></th>',
    text,
    re.S,
)
root = Path("app/views/partials")
root.joinpath("price-col-label-white.html").write_text(parts[0].strip(), encoding="utf-8")
root.joinpath("price-col-label-fancy.html").write_text(parts[1].strip(), encoding="utf-8")
print("ok", len(parts))
