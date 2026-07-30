import type { CmsPagePayload, CmsSection, FaqItem, Testimonial } from "@/lib/cms";

export type SectionRenderContext = {
  page: CmsPagePayload["page"];
  faq: CmsPagePayload["faq"];
  testimonials: Testimonial[];
  preview?: boolean;
  inline?: boolean;
  lcpSectionId?: string | null;
};

export type SectionProps = {
  section: CmsSection;
  ctx: SectionRenderContext;
};

export function str(props: Record<string, unknown>, key: string, fallback = ""): string {
  const v = props[key];
  return typeof v === "string" ? v : fallback;
}

export function asFaq(items: FaqItem[]): FaqItem[] {
  return Array.isArray(items) ? items : [];
}
