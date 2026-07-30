import type { LucideIcon } from "lucide-react";
import {
  AlignVerticalSpaceAround,
  Columns2,
  HelpCircle,
  ImageIcon,
  LayoutTemplate,
  Megaphone,
  MousePointerClick,
  Quote,
  Type,
} from "lucide-react";

export type CmsSectionType =
  | "hero"
  | "rich_text"
  | "image_text"
  | "cta_band"
  | "faq_embed"
  | "testimonials_embed"
  | "button_row"
  | "spacer";

export type CmsSection = {
  id: string;
  page_id: string;
  sort_order: number;
  type: CmsSectionType;
  props: Record<string, unknown>;
  is_visible: boolean;
};

export type CmsPage = {
  id: string;
  slug: string;
  title: string;
  meta_description: string;
  status: "draft" | "published";
  site_route?: string | null;
  sections?: CmsSection[];
};

export type CmsPaletteItem = {
  type: CmsSectionType;
  label: string;
  description: string;
  icon: LucideIcon;
};

export const SECTION_PALETTE: CmsPaletteItem[] = [
  {
    type: "hero",
    label: "Hero",
    description: "大圖標題與行動按鈕",
    icon: LayoutTemplate,
  },
  {
    type: "rich_text",
    label: "文字",
    description: "純文字段落區塊",
    icon: Type,
  },
  {
    type: "image_text",
    label: "圖文",
    description: "圖片搭配說明文字",
    icon: ImageIcon,
  },
  {
    type: "cta_band",
    label: "CTA",
    description: "強調行動號召橫幅",
    icon: Megaphone,
  },
  {
    type: "faq_embed",
    label: "FAQ",
    description: "嵌入常見問題列表",
    icon: HelpCircle,
  },
  {
    type: "testimonials_embed",
    label: "見證",
    description: "嵌入客戶見證",
    icon: Quote,
  },
  {
    type: "button_row",
    label: "按鈕列",
    description: "一列快速連結按鈕",
    icon: MousePointerClick,
  },
  {
    type: "spacer",
    label: "間距",
    description: "調整區塊上下空白",
    icon: AlignVerticalSpaceAround,
  },
];

/** Fallback icon when type unknown. */
export const SECTION_FALLBACK_ICON = Columns2;

export function sectionMeta(type: string): CmsPaletteItem | undefined {
  return SECTION_PALETTE.find((item) => item.type === type);
}

export function sectionLabel(type: string): string {
  return sectionMeta(type)?.label || type;
}

export function sectionDescription(type: string): string {
  return sectionMeta(type)?.description || "";
}

/** Types / props that enter the shared section image pipeline. */
export function sectionImagePropKey(
  type: string,
  props: Record<string, unknown> = {}
): "image_url" | null {
  if (type === "hero" || type === "image_text" || type === "cta_band") return "image_url";
  if (Object.prototype.hasOwnProperty.call(props, "image_url")) return "image_url";
  return null;
}

export function sectionPageImageLabel(type: string): string {
  const label = sectionLabel(type);
  return `${label} 區塊`;
}

/** page_images key for a CMS host or modular page. */
export function pageKeyForCmsPage(
  page: CmsPage | null | undefined,
  fallbackRoute = ""
): string {
  const route = String(page?.site_route || "").trim();
  if (route) return route;
  const slug = String(page?.slug || "").trim();
  if (slug) return `/p/${slug}`;
  return String(fallbackRoute || "").trim();
}

/** Homepage (and default site) CMS host order. Unknown anchors sort before `end`. */
export const CMS_ANCHOR_ORDER = [
  "before-series",
  "series-top",
  "series-mid",
  "after-series",
  "end",
] as const;

export function sectionAnchor(section: CmsSection): string {
  const a = String(section.props?.anchor || "end").trim().toLowerCase() || "end";
  return a;
}

/** Insert `newSection` into an anchor group at localIndex; flatten by CMS_ANCHOR_ORDER. */
export function buildOrderWithAnchor(
  sections: CmsSection[],
  newSection: CmsSection,
  anchor: string,
  localIndex: number
): CmsSection[] {
  const target = String(anchor || "end").trim().toLowerCase() || "end";
  const groups = new Map<string, CmsSection[]>();
  for (const section of sections) {
    const key = sectionAnchor(section);
    const list = groups.get(key);
    if (list) list.push(section);
    else groups.set(key, [section]);
  }
  const group = [...(groups.get(target) || [])];
  const idx = Number.isFinite(localIndex)
    ? Math.max(0, Math.min(Math.floor(localIndex), group.length))
    : group.length;
  group.splice(idx, 0, newSection);
  groups.set(target, group);

  const known = new Set<string>(CMS_ANCHOR_ORDER);
  const result: CmsSection[] = [];
  for (const key of CMS_ANCHOR_ORDER) {
    if (key === "end") continue;
    const items = groups.get(key);
    if (items?.length) result.push(...items);
  }
  const leftovers = [...groups.keys()]
    .filter((key) => !known.has(key) && key !== "end")
    .sort();
  for (const key of leftovers) {
    const items = groups.get(key);
    if (items?.length) result.push(...items);
  }
  const endItems = groups.get("end");
  if (endItems?.length) result.push(...endItems);
  return result;
}
