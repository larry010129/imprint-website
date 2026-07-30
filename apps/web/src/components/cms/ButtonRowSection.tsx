import { str, type SectionProps } from "./types";

type Btn = { label?: string; href?: string };

export default function ButtonRowSection({ section, ctx }: SectionProps) {
  const props = section.props || {};
  const edit = Boolean(ctx.inline);
  let buttons = Array.isArray(props.buttons) ? (props.buttons as Btn[]) : [];
  if (!buttons.length && edit) {
    buttons = [
      { label: "新連結", href: "/" },
      { label: "第二個連結", href: "/contact.html" },
    ];
  }
  return (
    <section
      className="cms-section cms-buttons"
      data-cms-reveal
      data-cms-section-id={section.id}
      data-cms-section-type="button_row"
      id={str(props, "anchor") !== "end" ? str(props, "anchor") : undefined}
    >
      <div className="container">
        <div className="cms-actions">
          {buttons.map((btn, index) => (
            <a
              key={`${btn.label}-${index}`}
              className="cms-btn"
              href={btn.href || "#"}
              data-cms-editable="button"
              data-cms-prop="buttons"
              data-cms-button-index={index}
            >
              {btn.label || "按鈕"}
            </a>
          ))}
        </div>
      </div>
    </section>
  );
}
