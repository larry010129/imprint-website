import type { PageImage } from "@/lib/static-image";

type Variant = "split" | "step" | "usp";

const variantClass: Record<Variant, string> = {
  split: "dna-info-figure dna-info-figure--split",
  step: "dna-info-figure dna-info-figure--step",
  usp: "dna-info-figure dna-info-figure--usp",
};

export default function DnaInfoFigure({
  image,
  variant = "split",
}: {
  image: PageImage;
  variant?: Variant;
}) {
  const base = variantClass[variant];

  if (image.kind === "placeholder") {
    return (
      <div
        className={`${base} dna-info-figure--placeholder`}
        role="img"
        aria-label={image.alt}
      >
        <span>{image.label}</span>
      </div>
    );
  }

  return (
    <figure className={base}>
      <picture>
        {image.webp && <source srcSet={image.webp} type="image/webp" />}
        <img src={image.src} alt={image.alt} loading="lazy" decoding="async" />
      </picture>
    </figure>
  );
}
