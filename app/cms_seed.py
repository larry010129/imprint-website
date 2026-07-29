"""Remove obsolete demo mirrors now that real site routes are editable."""

from __future__ import annotations

LEGACY_SEEDED_SLUGS = frozenset(
    {
        "home",
        "about",
        "brand-story",
        "contact",
        "faq",
        "stories",
        "series",
        "series-intro",
        "what-is-dna-diamond",
        "price-overview",
        "privacy",
        "terms",
        "return-policy",
        "series-first-love",
        "series-pet",
        "series-love",
        "series-family",
        "series-heirloom",
    }
)


def remove_legacy_seeded_pages(cur) -> int:
    """Delete former /p/* mirrors; their real routes are edited directly."""
    cur.execute(
        "delete from cms_pages where slug = any(%s) returning id",
        (list(LEGACY_SEEDED_SLUGS),),
    )
    return len(cur.fetchall())
