import { cookies, headers } from "next/headers";

import { apiBase } from "@/lib/api";

export type PageContext = {
  route: string;
  google_client_id: string;
  body_html?: string;
  page_images: unknown[];
  page_copy_slots: unknown[];
  lcp_image: string | null;
  lcp_image_type: string | null;
  site_cms_edit: boolean;
  featured_video: Record<string, unknown> | null;
  youtube_latest_video: Record<string, unknown> | null;
  layout: "site" | "auth" | "bare";
  extra_css: string[];
  extra_scripts: Array<{
    src?: string;
    inline?: string;
    type?: string;
    defer?: boolean;
    async?: boolean;
  }>;
  main_class: string;
  mvc_page: string | null;
  extra_body_class: string | null;
  title: string;
  description: string;
  canonical_path: string;
  og_title: string | null;
  og_description: string | null;
  og_image: string | null;
  breadcrumbs: [string, string | null][];
  extra_head_blocks: string[];
  head_extras: Array<Record<string, string | undefined>>;
  robots?: string;
  site_cms_sections?: unknown[];
};

export async function fetchPageContext(
  route: string,
  opts?: { cmsEdit?: boolean; includeBody?: boolean },
): Promise<PageContext | null> {
  const includeBody = opts?.includeBody !== false;
  const qs = new URLSearchParams({
    route,
    include_body: includeBody ? "1" : "0",
  });
  if (opts?.cmsEdit) qs.set("cms_edit", "1");

  const cookieStore = await cookies();
  const cookieHeader = cookieStore
    .getAll()
    .map((c) => `${c.name}=${c.value}`)
    .join("; ");

  const hdrs = await headers();
  const url = `${apiBase()}/api/v1/page-context?${qs.toString()}`;
  try {
    const res = await fetch(url, {
      headers: {
        Accept: "application/json",
        ...(cookieHeader ? { Cookie: cookieHeader } : {}),
        ...(hdrs.get("user-agent")
          ? { "User-Agent": hdrs.get("user-agent")! }
          : {}),
      },
      cache: opts?.cmsEdit ? "no-store" : "default",
      next: opts?.cmsEdit ? undefined : { revalidate: 30 },
    });
    if (!res.ok) return null;
    return (await res.json()) as PageContext;
  } catch {
    return null;
  }
}

/** Strip export leftovers that BeautifulSoup sometimes unwraps into visible text. */
function stripLeakedComponentMarkers(html: string): string {
  return html.replace(/(?:<!--\s*)?@component\s+[^\n<>]+(?:-->)?\s*\n?/gi, "");
}

/** Fallback when API down: local body without slot apply. */
export async function readLocalBody(bodyKey: string): Promise<string> {
  const { readFile } = await import("fs/promises");
  const { join } = await import("path");
  const path = join(
    process.cwd(),
    "..",
    "..",
    "content",
    "site",
    "bodies",
    `${bodyKey}.html`,
  );
  try {
    return stripLeakedComponentMarkers(await readFile(path, "utf8"));
  } catch {
    return `<p>Missing body: ${bodyKey}</p>`;
  }
}
