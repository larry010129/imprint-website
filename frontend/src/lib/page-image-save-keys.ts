/** Save/replace must send route + kebab slot, never 銘印鑽石 / 真我鑽石 / 主視覺. */

const SLOT_RE = /^[a-z0-9][a-z0-9-]{0,63}$/;

export type PageImageSaveKeys = {
  pageKey: string;
  slotKey: string;
};

export function pageImageSaveKeys(row: {
  page_key?: string;
  slot_key?: string;
}): PageImageSaveKeys | null {
  const pageKey = String(row.page_key || "").trim();
  const slotKey = String(row.slot_key || "").trim();
  if (!pageKey.startsWith("/") || pageKey.includes("?")) return null;
  if (!SLOT_RE.test(slotKey)) return null;
  return { pageKey, slotKey };
}

export function routeMatches(left: string, right: string): boolean {
  const normalize = (value: string) => {
    const clean = String(value || "").trim().replace(/\/$/, "");
    return clean.endsWith(".html") ? clean.slice(0, -5) : clean;
  };
  return normalize(left) === normalize(right);
}

export function pageHasImageSlots(
  route: string,
  keys: { page_key: string }[],
): boolean {
  return keys.some((key) => routeMatches(key.page_key, route));
}
