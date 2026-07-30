import { str, type SectionProps } from "./types";

export default function RichTextSection({ section, ctx }: SectionProps) {
  const props = section.props || {};
  const cols = Number(props.columns) || 1;
  const edit = Boolean(ctx.inline);
  return (
    <section
      className={`cms-section cms-rich cms-rich--cols-${cols}`}
      data-cms-reveal
      data-cms-section-id={section.id}
      data-cms-section-type="rich_text"
      id={str(props, "anchor") !== "end" ? str(props, "anchor") : undefined}
    >
      <div className="container">
        {(str(props, "title") || edit) && (
          <h2 data-cms-editable="text" data-cms-prop="title">
            {str(props, "title") || "輸入標題"}
          </h2>
        )}
        {(str(props, "body") || edit) && (
          <div className="cms-body" data-cms-editable="text" data-cms-prop="body">
            {str(props, "body") || "在此編輯內文。"}
          </div>
        )}
      </div>
    </section>
  );
}
