/**
 * Cache-busting for admin image thumbs.
 *
 * The token comes from the row's `updated_at`, so it is identical between
 * renders and the browser keeps caching the thumb until the row really changes.
 * Rows from tables without an `updated_at` column (e.g. `product_images`) get no
 * token until a caller reports a save — busting those on every page load would
 * make every thumb a cache miss.
 */

let saveEpoch = 0;

/** Invalidate thumbs for rows that carry no `updated_at`. */
export function bumpImageCacheEpoch(): number {
  saveEpoch = Date.now();
  return saveEpoch;
}

export function imageVersionToken(updatedAt?: string | number | null): string {
  const raw = updatedAt == null ? "" : String(updatedAt).trim();
  if (!raw) return saveEpoch ? String(saveEpoch) : "";
  const ms = Date.parse(raw);
  return Number.isNaN(ms) ? encodeURIComponent(raw) : String(ms);
}

export function bustImageUrl(
  url?: string | null,
  updatedAt?: string | number | null,
): string {
  const src = String(url || "").trim();
  if (!src) return "";
  if (/^(data|blob):/i.test(src)) return src;
  if (/[?&]v=/.test(src)) return src;
  const token = imageVersionToken(updatedAt);
  if (!token) return src;
  return `${src}${src.includes("?") ? "&" : "?"}v=${token}`;
}
