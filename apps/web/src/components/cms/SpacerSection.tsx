import { str, type SectionProps } from "./types";

export default function SpacerSection({ section }: SectionProps) {
  const props = section.props || {};
  const size = str(props, "size", "md") || "md";
  return (
    <section
      className={`cms-section cms-section--spacer-${size}`}
      data-cms-section-id={section.id}
      data-cms-section-type="spacer"
      aria-hidden="true"
      id={str(props, "anchor") !== "end" ? str(props, "anchor") : undefined}
    />
  );
}
