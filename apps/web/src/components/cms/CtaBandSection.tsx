import { str, type SectionProps } from "./types";

export default function CtaBandSection({ section, ctx }: SectionProps) {
  const props = section.props || {};
  const imageUrl = str(props, "image_url");
  const edit = Boolean(ctx.inline);
  return (
    <section
      className={`cms-section cms-cta${imageUrl ? " cms-cta--has-media" : ""}`}
      data-cms-reveal
      data-cms-section-id={section.id}
      data-cms-section-type="cta_band"
      id={str(props, "anchor") !== "end" ? str(props, "anchor") : undefined}
    >
      {imageUrl ? (
        <div className="cms-cta__media">
          <img
            src={imageUrl}
            srcSet={`${imageUrl} 1600w`}
            sizes="100vw"
            width={1600}
            height={600}
            alt={str(props, "image_alt")}
            loading="lazy"
            fetchPriority="low"
            decoding="async"
            data-cms-editable="image_url"
            data-cms-prop="image_url"
          />
        </div>
      ) : edit ? (
        <div className="cms-cta__media cms-cta__media--empty">
          <button
            type="button"
            className="cms-image-upload-placeholder"
            data-cms-editable="image_url"
            data-cms-prop="image_url"
          >
            <span>選用 CTA 圖片（選填）</span>
            <small>點擊上傳</small>
          </button>
        </div>
      ) : null}
      <div className="container cms-cta__copy">
        <h2 data-cms-editable="text" data-cms-prop="title">
          {str(props, "title") || "輸入標題"}
        </h2>
        {(str(props, "lead") || edit) && (
          <p className="cms-lead" data-cms-editable="text" data-cms-prop="lead">
            {str(props, "lead") || "在此編輯說明。"}
          </p>
        )}
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
      </div>
    </section>
  );
}
