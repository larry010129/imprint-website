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

export type CmsSectionTemplateCategory =
  | "blank"
  | "wireframe"
  | "designed"
  | "content";

export type CmsSectionTemplate = {
  id: string;
  category: CmsSectionTemplateCategory;
  type: CmsSectionType;
  label: string;
  description: string;
  props: Record<string, unknown>;
  previewKind: "hero" | "text" | "split" | "banner" | "list" | "buttons" | "space";
};

export const SECTION_TEMPLATE_CATEGORIES: {
  id: CmsSectionTemplateCategory;
  label: string;
}[] = [
  { id: "blank", label: "空白" },
  { id: "wireframe", label: "線框" },
  { id: "designed", label: "設計" },
  { id: "content", label: "內容" },
];

export const SECTION_TEMPLATES: CmsSectionTemplate[] = [
  {
    id: "blank-text",
    category: "blank",
    type: "rich_text",
    label: "空白文字",
    description: "從標題與內文開始",
    props: { title: "", body: "", columns: 1 },
    previewKind: "text",
  },
  {
    id: "blank-image-text",
    category: "blank",
    type: "image_text",
    label: "空白圖文",
    description: "圖片與內容的自由起點",
    props: { title: "", body: "", image_url: "", image_alt: "", layout: "stack" },
    previewKind: "split",
  },
  {
    id: "wireframe-hero",
    category: "wireframe",
    type: "hero",
    label: "主視覺線框",
    description: "標題、說明與雙按鈕",
    props: {
      eyebrow: "EYEBROW",
      title: "輸入主標題",
      lead: "輸入一段簡短說明。",
      image_url: "",
      image_alt: "",
      cta_label: "主要行動",
      cta_href: "/contact.html",
      cta_secondary_label: "次要行動",
      cta_secondary_href: "/",
    },
    previewKind: "hero",
  },
  {
    id: "wireframe-split",
    category: "wireframe",
    type: "image_text",
    label: "左右圖文",
    description: "桌面雙欄、手機自動堆疊",
    props: {
      title: "段落標題",
      body: "在此輸入內容。",
      image_url: "",
      image_alt: "",
      layout: "left",
      cta_label: "",
      cta_href: "",
    },
    previewKind: "split",
  },
  {
    id: "wireframe-buttons",
    category: "wireframe",
    type: "button_row",
    label: "雙按鈕",
    description: "並列的快速行動入口",
    props: {
      buttons: [
        { label: "第一個連結", href: "/" },
        { label: "第二個連結", href: "/contact.html" },
      ],
    },
    previewKind: "buttons",
  },
  {
    id: "designed-story",
    category: "designed",
    type: "rich_text",
    label: "品牌故事",
    description: "雙欄敘事版面",
    props: {
      title: "一段值得被好好說出的故事",
      body: "在這裡寫下品牌、服務或重要理念，讓讀者自然走進內容。",
      columns: 2,
    },
    previewKind: "text",
  },
  {
    id: "designed-cta",
    category: "designed",
    type: "cta_band",
    label: "深色行動橫幅",
    description: "適合頁尾轉換與聯絡入口",
    props: {
      title: "準備好開始了嗎？",
      lead: "我們會依照您的步調，陪您了解下一步。",
      image_url: "",
      image_alt: "",
      cta_label: "聯絡我們",
      cta_href: "/contact.html",
      cta_secondary_label: "了解更多",
      cta_secondary_href: "/about.html",
    },
    previewKind: "banner",
  },
  {
    id: "content-faq",
    category: "content",
    type: "faq_embed",
    label: "常見問題",
    description: "嵌入後台精選 FAQ",
    props: { mode: "teaser", category_id: "", limit: 6 },
    previewKind: "list",
  },
  {
    id: "content-testimonials",
    category: "content",
    type: "testimonials_embed",
    label: "客戶見證",
    description: "嵌入已發布見證",
    props: { limit: 6 },
    previewKind: "list",
  },
  {
    id: "content-spacer",
    category: "content",
    type: "spacer",
    label: "段落留白",
    description: "建立舒適的內容節奏",
    props: { size: "md" },
    previewKind: "space",
  },
];

export function defaultTemplateForType(type: CmsSectionType): CmsSectionTemplate {
  return (
    SECTION_TEMPLATES.find((template) => template.type === type) || {
      id: `blank-${type}`,
      category: "blank",
      type,
      label: sectionLabel(type),
      description: sectionDescription(type),
      props: {},
      previewKind: "text",
    }
  );
}

export function sectionPrimaryProp(type: CmsSectionType): string {
  if (type === "button_row") return "buttons";
  if (type === "spacer") return "size";
  if (type === "faq_embed" || type === "testimonials_embed") return "limit";
  return "title";
}

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
