import { str, type SectionProps } from "./types";

export default function TestimonialsEmbedSection({ section, ctx }: SectionProps) {
  const props = section.props || {};
  const limit = Math.max(1, Math.min(24, Number(props.limit) || 6));
  const items = (ctx.testimonials || []).slice(0, limit);
  return (
    <section
      className="cms-section cms-embed"
      data-cms-reveal
      data-cms-section-id={section.id}
      data-cms-section-type="testimonials_embed"
      id={str(props, "anchor") !== "end" ? str(props, "anchor") : undefined}
    >
      <div className="container">
        <h2>客戶見證</h2>
        <div className="cms-testimonials">
          {items.length ? (
            items.map((t, i) => (
              <article key={t.id || i} className="cms-testimonial">
                {t.image_url ? (
                  <img
                    src={t.image_url}
                    width={640}
                    height={640}
                    alt={t.name || ""}
                    loading="lazy"
                    fetchPriority="low"
                    decoding="async"
                  />
                ) : null}
                <p className="cms-testimonial__name">{t.name}</p>
                <p className="cms-testimonial__role">{t.role}</p>
                <p>{t.text}</p>
              </article>
            ))
          ) : (
            <p className="cms-body">目前尚無見證。</p>
          )}
        </div>
        <div className="cms-actions">
          <a className="cms-btn" href="/stories.html">
            閱讀更多見證
          </a>
        </div>
      </div>
    </section>
  );
}
