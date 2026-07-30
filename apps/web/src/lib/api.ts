/**
 * FastAPI JSON client for Next Server Components.
 * Pricing/cart/catalog SoT stays in Python — never reimplement calculator math here.
 */

const DEFAULT_API = "http://127.0.0.1:8080";

export function apiBase(): string {
  const raw = (process.env.API_INTERNAL_BASE || DEFAULT_API).replace(/\/$/, "");
  if (raw.startsWith("http://") || raw.startsWith("https://")) return raw;
  return `https://${raw}`;
}

export async function fetchJson<T>(
  path: string,
  init?: RequestInit & { revalidate?: number },
): Promise<T | null> {
  const { revalidate = 60, ...rest } = init || {};
  const url = `${apiBase()}${path.startsWith("/") ? path : `/${path}`}`;
  try {
    const res = await fetch(url, {
      ...rest,
      next: { revalidate },
      headers: {
        Accept: "application/json",
        ...(rest.headers || {}),
      },
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}
