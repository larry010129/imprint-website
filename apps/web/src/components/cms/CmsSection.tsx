import type { ComponentType } from "react";

import ButtonRowSection from "./ButtonRowSection";
import CtaBandSection from "./CtaBandSection";
import FaqEmbedSection from "./FaqEmbedSection";
import FreeformSection from "./FreeformSection";
import HeroSection from "./HeroSection";
import ImageTextSection from "./ImageTextSection";
import RichTextSection from "./RichTextSection";
import SpacerSection from "./SpacerSection";
import TestimonialsEmbedSection from "./TestimonialsEmbedSection";
import type { SectionProps } from "./types";

const MAP: Record<string, ComponentType<SectionProps>> = {
  hero: HeroSection,
  rich_text: RichTextSection,
  image_text: ImageTextSection,
  cta_band: CtaBandSection,
  faq_embed: FaqEmbedSection,
  testimonials_embed: TestimonialsEmbedSection,
  button_row: ButtonRowSection,
  spacer: SpacerSection,
  freeform: FreeformSection,
};

export default function CmsSection(props: SectionProps) {
  const Comp = MAP[props.section.type];
  if (!Comp) return null;
  return <Comp {...props} />;
}
