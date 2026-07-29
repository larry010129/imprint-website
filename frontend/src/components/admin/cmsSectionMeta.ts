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
  sections?: CmsSection[];
};

export const SECTION_PALETTE: { type: CmsSectionType; label: string }[] = [
  { type: "hero", label: "Hero" },
  { type: "rich_text", label: "文字" },
  { type: "image_text", label: "圖文" },
  { type: "cta_band", label: "CTA" },
  { type: "faq_embed", label: "FAQ" },
  { type: "testimonials_embed", label: "見證" },
  { type: "button_row", label: "按鈕列" },
  { type: "spacer", label: "間距" },
];

export function sectionLabel(type: string): string {
  return SECTION_PALETTE.find((s) => s.type === type)?.label || type;
}
