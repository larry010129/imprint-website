import { faqItemsForSection } from "@/lib/cms";

import { str, type SectionProps } from "./types";

export default function FaqEmbedSection({ section, ctx }: SectionProps) {
  const props = section.props || {};
  const items = faqItemsForSection(props, ctx.faq);
  return (
    <section
      className="cms-section cms-embed"
      data-cms-reveal
      data-cms-section-id={section.id}
      data-cms-section-type="faq_embed"
      id={str(props, "anchor") !== "end" ? str(props, "anchor") : undefined}
    >
      <div className="container">
        <h2>常見問題</h2>
        <div className="cms-embed__list">
          {items.length ? (
            items.map((item, i) => (
              <details key={item.id || i} className="cms-embed__item">
                <summary>
                  <span>{item.question}</span>
                </summary>
                <div className="cms-embed__answer">
                  <p>{item.answer}</p>
                </div>
              </details>
            ))
          ) : (
            <p className="cms-body">目前尚無 FAQ。請至後台「內容」管理新增。</p>
          )}
        </div>
        <div className="cms-actions">
          <a className="cms-btn" href="/faq.html">
            查看全部 FAQ
          </a>
        </div>
      </div>
    </section>
  );
}
