import type { LucideIcon } from "lucide-react";
import {
  AlignVerticalSpaceAround,
  Columns2,
  HelpCircle,
  ImageIcon,
  LayoutTemplate,
  Megaphone,
  MousePointerClick,
  Move,
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
  | "spacer"
  | "freeform";

export type CmsFreeformBlockKind = "heading" | "text" | "button" | "image";

export type CmsFreeformBlock = {
  id: string;
  kind: CmsFreeformBlockKind;
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

export function newFreeformBlockId(): string {
  return `b-${Math.random().toString(36).slice(2, 10)}`;
}

export function defaultFreeformBlock(
  kind: CmsFreeformBlockKind,
  index = 0
): CmsFreeformBlock {
  const base = {
    id: newFreeformBlockId(),
    kind,
    x: 10 + (index % 3) * 6,
    y: 12 + (index % 4) * 10,
    w: kind === "button" ? 22 : kind === "image" ? 36 : 40,
    h: kind === "heading" ? 14 : kind === "image" ? 28 : 12,
    z: index + 1,
  };
  if (kind === "heading") return { ...base, text: "新標題" };
  if (kind === "text") return { ...base, text: "在此編輯文字。" };
  if (kind === "button") {
    return { ...base, text: "了解更多", href: "/contact.html" };
  }
  return { ...base, image_url: "", image_alt: "" };
}

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
  previewKind: "hero" | "text" | "split" | "banner" | "list" | "buttons" | "space" | "freeform";
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
    id: "blank-freeform",
    category: "blank",
    type: "freeform",
    label: "自由版面",
    description: "像 PowerPoint／Squarespace 一樣自由拖曳元素",
    props: {
      height: 480,
      blocks: [
        {
          id: "b-title",
          kind: "heading",
          x: 8,
          y: 16,
          w: 56,
          h: 16,
          z: 2,
          text: "自由版面標題",
        },
        {
          id: "b-body",
          kind: "text",
          x: 8,
          y: 38,
          w: 44,
          h: 18,
          z: 1,
          text: "在預覽中拖曳把手移動，拖曳右下角縮放。",
        },
        {
          id: "b-cta",
          kind: "button",
          x: 8,
          y: 66,
          w: 24,
          h: 12,
          z: 3,
          text: "了解更多",
          href: "/contact.html",
        },
      ],
      blocks_mobile: [],
    },
    previewKind: "freeform",
  },
  {
    id: "designed-freeform-hero",
    category: "designed",
    type: "freeform",
    label: "自由 Hero",
    description: "大標題＋說明＋按鈕的自由版面起點",
    props: {
      height: 560,
      blocks: [
        {
          id: "fh-eyebrow",
          kind: "text",
          x: 8,
          y: 18,
          w: 40,
          h: 8,
          z: 1,
          text: "IMPRINT DIAMOND",
        },
        {
          id: "fh-title",
          kind: "heading",
          x: 8,
          y: 28,
          w: 70,
          h: 18,
          z: 3,
          text: "把思念，留成永恆",
        },
        {
          id: "fh-lead",
          kind: "text",
          x: 8,
          y: 50,
          w: 48,
          h: 14,
          z: 2,
          text: "台灣在地 DNA 紀念鑽石，依您的步調客製。",
        },
        {
          id: "fh-cta",
          kind: "button",
          x: 8,
          y: 72,
          w: 22,
          h: 12,
          z: 4,
          text: "開始諮詢",
          href: "/contact.html",
        },
      ],
      blocks_mobile: [
        {
          id: "fh-title-m",
          kind: "heading",
          x: 6,
          y: 22,
          w: 88,
          h: 20,
          z: 2,
          text: "把思念，留成永恆",
        },
        {
          id: "fh-cta-m",
          kind: "button",
          x: 6,
          y: 70,
          w: 50,
          h: 12,
          z: 3,
          text: "開始諮詢",
          href: "/contact.html",
        },
      ],
    },
    previewKind: "freeform",
  },
  {
    id: "designed-hero-full",
    category: "designed",
    type: "hero",
    label: "全幅 Hero",
    description: "大圖背景＋雙 CTA 的完整主視覺",
    props: {
      eyebrow: "銘印鑽石",
      title: "全台唯一在地 DNA 紀念鑽石",
      lead: "從樣本到鑲嵌，於台灣實驗室完成。",
      image_url: "",
      image_alt: "",
      cta_label: "客製試算",
      cta_href: "/shop/calculator/",
      cta_secondary_label: "了解製程",
      cta_secondary_href: "/what-is-dna-diamond.html",
    },
    previewKind: "hero",
  },
  {
    id: "blank-text",
    category: "blank",
    type: "rich_text",
    label: "空白文字",
    description: "從標題與內文開始",
    props: { title: "輸入標題", body: "在此編輯內文。", columns: 1 },
    previewKind: "text",
  },
  {
    id: "blank-image-text",
    category: "blank",
    type: "image_text",
    label: "空白圖文",
    description: "圖片與內容的自由起點",
    props: {
      title: "圖文標題",
      body: "在此編輯說明文字。",
      image_url: "",
      image_alt: "",
      layout: "stack",
      cta_label: "了解更多",
      cta_href: "/contact.html",
    },
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

/** Sensible starter props when palette/drag omits template props. */
export function defaultPropsForType(type: CmsSectionType): Record<string, unknown> {
  return copyProps(defaultTemplateForType(type).props);
}

function copyProps(props: Record<string, unknown>): Record<string, unknown> {
  return JSON.parse(JSON.stringify(props)) as Record<string, unknown>;
}

export function defaultTemplateForType(type: CmsSectionType): CmsSectionTemplate {
  const found = SECTION_TEMPLATES.find((template) => template.type === type);
  if (found) return found;
  const fallbackProps: Record<CmsSectionType, Record<string, unknown>> = {
    hero: {
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
    rich_text: { title: "輸入標題", body: "在此編輯內文。", columns: 1 },
    image_text: {
      title: "圖文標題",
      body: "在此編輯說明文字。",
      image_url: "",
      image_alt: "",
      layout: "stack",
      cta_label: "了解更多",
      cta_href: "/contact.html",
    },
    cta_band: {
      title: "準備好開始了嗎？",
      lead: "我們會依照您的步調，陪您了解下一步。",
      image_url: "",
      image_alt: "",
      cta_label: "聯絡我們",
      cta_href: "/contact.html",
      cta_secondary_label: "了解更多",
      cta_secondary_href: "/about.html",
    },
    faq_embed: { mode: "teaser", category_id: "", limit: 6 },
    testimonials_embed: { limit: 6 },
    button_row: {
      buttons: [
        { label: "第一個連結", href: "/" },
        { label: "第二個連結", href: "/contact.html" },
      ],
    },
    spacer: { size: "md" },
    freeform: {
      height: 480,
      blocks: [
        {
          id: "b-title",
          kind: "heading",
          x: 8,
          y: 16,
          w: 56,
          h: 16,
          z: 2,
          text: "自由版面標題",
        },
        {
          id: "b-body",
          kind: "text",
          x: 8,
          y: 38,
          w: 44,
          h: 18,
          z: 1,
          text: "在預覽中拖曳把手移動，拖曳右下角縮放。",
        },
        {
          id: "b-cta",
          kind: "button",
          x: 8,
          y: 66,
          w: 24,
          h: 12,
          z: 3,
          text: "了解更多",
          href: "/contact.html",
        },
      ],
      blocks_mobile: [],
    },
  };
  return {
    id: `blank-${type}`,
    category: "blank",
    type,
    label: sectionLabel(type),
    description: sectionDescription(type),
    props: fallbackProps[type] || {},
    previewKind: type === "freeform" ? "freeform" : "text",
  };
}

export function sectionPrimaryProp(type: CmsSectionType): string {
  if (type === "button_row") return "buttons";
  if (type === "spacer") return "size";
  if (type === "faq_embed" || type === "testimonials_embed") return "limit";
  if (type === "freeform") return "height";
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
  {
    type: "freeform",
    label: "自由版面",
    description: "區塊內自由拖曳／縮放元素",
    icon: Move,
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
