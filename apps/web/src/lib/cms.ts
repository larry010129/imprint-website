import { cookies, headers } from "next/headers";

import { apiBase } from "@/lib/api";

export type CmsFreeformBlock = {
  id: string;
  kind: "heading" | "text" | "button" | "image";
  x: number;
  y: number;
  w: number;
  h: number;
  z: number;
  text?: string;
  href?: string;
  image_url?: string;
  image_alt?: string;
};

export type CmsSection = {
  id: string;
  page_id?: string;
  sort_order?: number;
  type: string;
  props: Record<string, unknown>;
  is_visible?: boolean;
};

export type CmsPage = {
  id: string;
  slug: string;
  title: string;
  meta_description?: string;
  status: "draft" | "published";
  sections?: CmsSection[];
};

export type CmsPagePayload = {
  page: CmsPage;
  sections: CmsSection[];
  faq: {
    categories?: { id: string; title?: string; items?: FaqItem[] }[];
    teaser?: FaqItem[];
    items?: FaqItem[];
  };
  testimonials: Testimonial[];
  meta: {
    lcp_section_id?: string | null;
    lcp_image?: string | null;
    lcp_image_type?: string | null;
    preview?: boolean;
  };
};

export type FaqItem = {
  id?: string;
  question?: string;
  answer?: string;
  category_id?: string;
};

export type Testimonial = {
  id?: string;
  name?: string;
  role?: string;
  text?: string;
  image_url?: string;
};

export async function fetchCmsPage(
  slug: string,
  opts?: { preview?: boolean },
): Promise<CmsPagePayload | null> {
  const preview = Boolean(opts?.preview);
  const qs = preview ? "?preview=1" : "";
  const url = `${apiBase()}/api/cms/pages/${encodeURIComponent(slug)}${qs}`;
  const hdrs: Record<string, string> = { Accept: "application/json" };
  if (preview) {
    const jar = await cookies();
    const cookieHeader = jar
      .getAll()
      .map((c) => `${c.name}=${c.value}`)
      .join("; ");
    if (cookieHeader) hdrs.Cookie = cookieHeader;
    const h = await headers();
    const auth = h.get("authorization");
    if (auth) hdrs.Authorization = auth;
  }
  try {
    const res = await fetch(url, {
      headers: hdrs,
      cache: preview ? "no-store" : undefined,
      next: preview ? undefined : { revalidate: 30 },
    });
    if (!res.ok) return null;
    return (await res.json()) as CmsPagePayload;
  } catch {
    return null;
  }
}

export function faqItemsForSection(
  props: Record<string, unknown>,
  faq: CmsPagePayload["faq"],
): FaqItem[] {
  const limit = Math.max(1, Math.min(24, Number(props.limit) || 6));
  const categoryId = String(props.category_id || "");
  let items: FaqItem[] = [];
  if (categoryId) {
    const cat = (faq.categories || []).find((c) => String(c.id) === categoryId);
    items = cat?.items || [];
  } else if (props.mode === "all") {
    items = faq.items || [];
  } else {
    items = faq.teaser || [];
    if (!items.length) {
      items = (faq.categories || []).flatMap((c) => c.items || []);
    }
  }
  return items.slice(0, limit);
}
