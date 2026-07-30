import CmsSection from "./CmsSection";
import type { SectionRenderContext } from "./types";
import type { CmsPagePayload } from "@/lib/cms";

type Props = {
  payload: CmsPagePayload;
  preview?: boolean;
  inline?: boolean;
};

export default function CmsPageView({ payload, preview, inline }: Props) {
  const sections = payload.sections || payload.page.sections || [];
  const ctx: SectionRenderContext = {
    page: payload.page,
    faq: payload.faq || {},
    testimonials: payload.testimonials || [],
    preview,
    inline,
    lcpSectionId: preview || inline ? null : payload.meta?.lcp_section_id,
  };
  const showBanner = Boolean(preview || inline);

  return (
    <>
      {showBanner ? (
        <div className="cms-preview-banner" role="status">
          預覽：{payload.page.title} · /p/{payload.page.slug}
          {payload.page.status !== "published" ? "（草稿）" : ""}
        </div>
      ) : null}
      <article
        className="cms-page"
        data-cms-page={payload.page.slug}
        {...(inline ? { "data-cms-inline": "1" } : {})}
      >
        {sections.length ? (
          sections.map((section) => (
            <CmsSection key={section.id} section={section} ctx={ctx} />
          ))
        ) : (
          <section className="cms-section cms-section--empty">
            <div className="container">
              <p>此頁尚無區塊內容。請從左側新增區塊。</p>
            </div>
          </section>
        )}
      </article>
    </>
  );
}
