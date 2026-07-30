import { str, type SectionProps } from "./types";

export default function HeroSection({ section, ctx }: SectionProps) {
  const props = section.props || {};
  const isLcp = ctx.lcpSectionId === section.id && !ctx.preview && !ctx.inline;
  const imageUrl = str(props, "image_url");
  const edit = Boolean(ctx.inline);

  return (
    <section
      className="cms-section cms-hero"
      data-cms-reveal
      data-cms-section-id={section.id}
      data-cms-section-type="hero"
      id={str(props, "anchor") !== "end" ? str(props, "anchor") : undefined}
    >
      {imageUrl ? (
        <div className="cms-hero__media">
          <img
            src={imageUrl}
            srcSet={`${imageUrl} 1600w`}
            sizes="100vw"
            width={1600}
            height={900}
            alt={str(props, "image_alt")}
            loading={isLcp ? "eager" : "lazy"}
            fetchPriority={isLcp ? "high" : "low"}
            decoding="async"
            data-cms-editable="image_url"
            data-cms-prop="image_url"
          />
          <div className="cms-hero__shade" />
        </div>
      ) : edit ? (
        <div className="cms-hero__media cms-hero__media--empty">
          <button
            type="button"
            className="cms-image-upload-placeholder cms-image-upload-placeholder--hero"
            data-cms-editable="image_url"
            data-cms-prop="image_url"
          >
            <span>上傳 Hero 圖片</span>
            <small>點擊選擇背景圖</small>
          </button>
        </div>
      ) : null}
      <div className="cms-hero__copy">
        {(str(props, "eyebrow") || edit) && (
          <p className="cms-eyebrow" data-cms-editable="text" data-cms-prop="eyebrow">
            {str(props, "eyebrow") || "眉題"}
          </p>
        )}
        <h1 data-cms-editable="text" data-cms-prop="title">
          {str(props, "title") || ctx.page.title}
        </h1>
        {(str(props, "lead") || edit) && (
          <p className="cms-lead" data-cms-editable="text" data-cms-prop="lead">
            {str(props, "lead") || "在此編輯引言。"}
          </p>
        )}
        {(str(props, "cta_label") || str(props, "cta_secondary_label") || edit) && (
          <div className="cms-actions">
            {(str(props, "cta_label") || edit) && (
              <a
                className="cms-btn cms-btn--solid"
                href={str(props, "cta_href") || "#"}
                data-cms-editable="button"
                data-cms-prop="cta_label"
                data-cms-href-prop="cta_href"
              >
                {str(props, "cta_label") || "主要行動"}
              </a>
            )}
            {(str(props, "cta_secondary_label") || edit) && (
              <a
                className="cms-btn cms-btn--ghost"
                href={str(props, "cta_secondary_href") || "#"}
                data-cms-editable="button"
                data-cms-prop="cta_secondary_label"
                data-cms-href-prop="cta_secondary_href"
              >
                {str(props, "cta_secondary_label") || "次要行動"}
              </a>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
