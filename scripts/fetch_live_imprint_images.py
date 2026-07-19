"""Download brand images from imprint-diamond.com CDN into public/images/legacy-live/."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

CDN = "https://cdn.soeasy.tw/storages/100098"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "public" / "images" / "legacy-live"

# category, cdn_filename, local_name, live_section, dna_page_section (optional)
ASSETS: list[tuple[str, str, str, str, str | None]] = [
    # styles — section backgrounds
    ("styles", "8043fee85b29bf151aaa4f9e321f6223e54e.jpg", "what-is-dna-diamond-bg.jpg", "什麼是DNA鑽石", "intro"),
    ("styles", "58181251452d850c8d7a929b22a2174461ea.jpg", "eternal-memorial.jpg", "一段思念，如何成為永恆", "process"),
    ("styles", "5208ece088d276c28f8e9737be5ca676e598.jpg", "taiwan-local-lab.jpg", "無需漂洋過海", "local"),
    ("styles", "4043bb1b5f1b7ed3618a810bfda96eb9d8bf.jpg", "jewelry-making.jpg", "製作成飾品", "promise-jewelry"),
    # features — five series + signature
    ("features", "533597552e504a3bdc105142d3a8dc1a0974.jpg", "first-love.jpg", "First Love｜滿月紀念", None),
    ("features", "758711f910377d881d497eb7d5f9f4a1c15a.jpg", "pet-companion.jpg", "Companion｜毛孩陪伴", None),
    ("features", "44746e03559d44a19702d0982876b1731aa9.jpg", "love-couple.jpg", "Love｜愛情紀念", None),
    ("features", "742514b811a75a04ffd84865eb4430ad7e71.jpg", "family.jpg", "Family｜家族傳承", None),
    ("features", "2917d0e5a7fa4de1b83d46f181cb964e7c95.jpg", "heirloom-life.jpg", "Heirloom｜生命鑽石", "process-step-6"),
    ("features", "6450d833777790eaad794b63fcda6bf94cec.jpg", "signature-custom.jpg", "Signature｜專屬訂製", None),
    # sliders — homepage carousel
    ("sliders", "16515db4292568cbc53c432de0a70b4970d7.jpg", "slider-01.jpg", "carousel", None),
    ("sliders", "57128463f4a4628cf00931f0bf0de30fe092.jpg", "slider-02.jpg", "carousel", None),
    ("sliders", "857511f910377d881d497eb7d5f9f4a1c15a.jpg", "slider-03.jpg", "carousel (OG)", None),
    ("sliders", "8272e74372bd70ca4e6c9c08b41849820b18.jpg", "slider-04.jpg", "carousel", None),
    ("sliders", "536421234b2cd7d6c429f7c76e1bea613be4.jpg", "slider-05.jpg", "carousel", None),
    ("sliders", "1071d0e5a7fa4de1b83d46f181cb964e7c95.jpg", "slider-06.jpg", "carousel", None),
    ("sliders", "458626eaf005419c8d2c3501230d38aca3f1.jpg", "slider-07.jpg", "carousel", None),
    ("sliders", "5681d13aed5c6c5f42dbb7fb63e3f6f4b77c.jpg", "slider-08.jpg", "carousel", None),
    ("sliders", "4191a0a52f8f24e09bd04261efdca7224dc9.jpg", "slider-09.jpg", "carousel", None),
    ("sliders", "3261980281fff6a37d355f07267a5e9b41c0.jpg", "slider-10.jpg", "carousel", None),
    ("sliders", "7395181009704214fd77af3e77c95d7eb37c.jpg", "slider-11.jpg", "carousel", None),
    ("sliders", "3911bfd0f013e24f4633d94a6eaca0f31006.jpg", "slider-12.jpg", "carousel", None),
    # testimons — customer portraits
    ("testimons", "7582fe5df232cafa4c4e0f1a0294418e5660.jpg", "testimonial-01.jpg", "客戶見證", None),
    ("testimons", "38698cda81fc7ad906927144235dda5fdf15.jpg", "testimonial-02.jpg", "客戶見證", None),
    ("testimons", "391818e2999891374a475d0687ca9f989d83.jpg", "testimonial-03.jpg", "客戶見證", None),
    ("testimons", "4681f3ccdd27d2000e3f9255a7e3e2c48800.jpg", "testimonial-04.jpg", "客戶見證", None),
    ("testimons", "4822d0096ec6c83575373e3a21d129ff8fef.jpg", "testimonial-05.jpg", "客戶見證", None),
    ("testimons", "5535156005c5baf40ff51a327f1c34f2975b.jpg", "testimonial-06.jpg", "客戶見證", None),
    ("testimons", "1815032b2cc936860b03048302d991c3498f.jpg", "testimonial-07.jpg", "客戶見證", None),
    ("testimons", "7940799bad5a3b514f096e69bbc4a7896cd9.jpg", "testimonial-08.jpg", "客戶見證", None),
]


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "imprint-website-asset-sync/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        dest.write_bytes(resp.read())


def main() -> int:
    manifest: dict[str, dict] = {}
    ok, fail = 0, 0

    for category, cdn_name, local_name, live_section, dna_section in ASSETS:
        url = f"{CDN}/{category}/{cdn_name}"
        rel = f"legacy-live/{category}/{local_name}"
        dest = OUT / category / local_name
        entry = {
            "cdnUrl": url,
            "local": rel,
            "staticPath": f"/static/images/{rel}",
            "liveSection": live_section,
        }
        if dna_section:
            entry["dnaPageSection"] = dna_section

        try:
            download(url, dest)
            entry["bytes"] = dest.stat().st_size
            entry["status"] = "ok"
            ok += 1
            print(f"OK  {rel} ({entry['bytes']:,} bytes)")
        except (urllib.error.URLError, OSError) as exc:
            entry["status"] = "failed"
            entry["error"] = str(exc)
            fail += 1
            print(f"FAIL {rel}: {exc}")

        manifest[f"{category}/{cdn_name}"] = entry

    manifest_path = OUT / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "source": "https://www.imprint-diamond.com/",
                "cdnBase": CDN,
                "downloaded": ok,
                "failed": fail,
                "assets": manifest,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nManifest: {manifest_path}")
    print(f"Done: {ok} ok, {fail} failed")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
