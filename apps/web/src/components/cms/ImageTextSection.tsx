import { str, type SectionProps } from "./types";

export default function ImageTextSection({ section, ctx }: SectionProps) {
  const props = section.props || {};
  const layout = str(props, "layout", "stack") || "stack";
  const imageUrl = str(props, "image_url");
  const edit = Boolean(ctx.inline);
  return (
    <section
      className={`cms-section cms-image-text cms-image-text--${layout}`}
      data-cms-reveal
      data-cms-section-id={section.id}
      data-cms-section-type="image_text"
      id={str(props, "anchor") !== "end" ? str(props, "anchor") : undefined}
    >
      <div className="container cms-image-text__grid">
        <figure className="cms-image-text__media">
          {imageUrl ? (
            <img
              src={imageUrl}
              srcSet={`${imageUrl} 1200w`}
              sizes="(max-width: 800px) 100vw, 50vw"
              width={1200}
              height={900}
              alt={str(props, "image_alt")}
              loading="lazy"
              fetchPriority="low"
              decoding="async"
              data-cms-editable="image_url"
              data-cms-prop="image_url"
            />
          ) : edit ? (
            <button
              type="button"
              className="cms-image-upload-placeholder"
              data-cms-editable="image_url"
              data-cms-prop="image_url"
            >
              <span>上傳圖片</span>
              <small>點擊選擇或拖曳檔案</small>
            </button>
          ) : null}
        </figure>
        <div className="cms-image-text__copy">
          {(str(props, "title") || edit) && (
            <h2 data-cms-editable="text" data-cms-prop="title">
              {str(props, "title") || "圖文標題"}
            </h2>
          )}
          {(str(props, "body") || edit) && (
            <div className="cms-body" data-cms-editable="text" data-cms-prop="body">
              {str(props, "body") || "在此編輯說明文字。"}
            </div>
          )}
          {(str(props, "cta_label") || edit) && (
            <div className="cms-actions">
              <a
                className="cms-btn"
                href={str(props, "cta_href") || "#"}
                data-cms-editable="button"
                data-cms-prop="cta_label"
                data-cms-href-prop="cta_href"
              >
                {str(props, "cta_label") || "行動按鈕"}
              </a>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
