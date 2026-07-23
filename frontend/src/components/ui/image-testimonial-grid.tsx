import * as React from "react";
import { motion } from "motion/react";
import { cn } from "@/lib/utils";

interface MasonryGridProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Number of columns. @default 3 */
  columns?: number;
  /** Gap on Tailwind spacing scale. @default 4 */
  gap?: number;
}

/**
 * True masonry: round-robin into flex columns so row gaps do not line up
 * across columns (unlike CSS column-count balance).
 */
const MasonryGrid = React.forwardRef<HTMLDivElement, MasonryGridProps>(
  ({ className, columns = 3, gap = 4, children, ...props }, ref) => {
    const childArray = React.Children.toArray(children);
    const cols = Math.max(1, columns);
    const buckets: React.ReactNode[][] = Array.from({ length: cols }, () => []);
    childArray.forEach((child, i) => {
      buckets[i % cols].push(child);
    });

    const gapRem = `${gap * 0.25}rem`;

    const cardVariants = {
      hidden: { opacity: 0, y: 20 },
      visible: {
        opacity: 1,
        y: 0,
        transition: {
          duration: 0.5,
          ease: "easeOut" as const,
        },
      },
    };

    return (
      <div
        ref={ref}
        className={cn("flex w-full items-start", className)}
        style={{ gap: gapRem }}
        {...props}
      >
        {buckets.map((bucket, colIndex) => (
          <div
            key={colIndex}
            className="flex min-w-0 flex-1 flex-col"
            style={{ gap: gapRem }}
          >
            {bucket.map((child, rowIndex) => (
              <motion.div
                key={rowIndex}
                variants={cardVariants}
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true, amount: 0.15 }}
              >
                {child}
              </motion.div>
            ))}
          </div>
        ))}
      </div>
    );
  },
);

MasonryGrid.displayName = "MasonryGrid";

/** Cycle aspect ratios so adjacent columns break at different heights. */
const ASPECT_CYCLE = [
  "aspect-[4/5]",
  "aspect-[3/4]",
  "aspect-square",
  "aspect-[2/3]",
  "aspect-[5/6]",
  "aspect-[3/5]",
] as const;

export type ImageTestimonialCardProps = {
  name: string;
  feedback: string;
  mainImage?: string;
  role?: string;
  /** Index used to pick a staggered aspect ratio */
  index?: number;
  className?: string;
};

/** Image-led testimonial tile — product photo dominant, name + quote overlay. */
function ImageTestimonialCard({
  name,
  feedback,
  mainImage,
  role,
  index = 0,
  className,
}: ImageTestimonialCardProps) {
  const safeName = String(name || "客戶").trim() || "客戶";
  const safeFeedback = String(feedback || "").trim();
  const aspect = ASPECT_CYCLE[index % ASPECT_CYCLE.length];

  return (
    <div
      className={cn(
        "group relative overflow-hidden rounded-2xl bg-[#2a2438] transition-transform duration-300 ease-in-out hover:scale-[1.02]",
        className,
      )}
    >
      {mainImage ? (
        <img
          src={mainImage}
          alt={safeFeedback || safeName}
          className={cn("h-full w-full object-cover", aspect)}
          loading="lazy"
          decoding="async"
          onError={(e) => {
            e.currentTarget.src =
              "https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?auto=format&fit=crop&w=800&q=80";
          }}
        />
      ) : (
        <div
          className={cn(
            "w-full bg-gradient-to-br from-[#8eedf0]/40 to-[#2a1845]",
            aspect,
          )}
        />
      )}
      <div className="absolute inset-0 bg-gradient-to-b from-black/65 via-black/25 to-transparent" />
      <div className="absolute top-0 left-0 p-4 text-white">
        <div className="mb-2 min-w-0">
          <span className="block truncate text-sm font-semibold drop-shadow-md">
            {safeName}
          </span>
          {role ? (
            <span className="block truncate text-[11px] text-white/75 drop-shadow-md">
              {role}
            </span>
          ) : null}
        </div>
        {safeFeedback ? (
          <p className="line-clamp-4 text-[12px] leading-snug font-medium drop-shadow-md">
            「{safeFeedback.replace(/^「|」$/g, "")}」
          </p>
        ) : null}
      </div>
    </div>
  );
}

export { MasonryGrid, ImageTestimonialCard };
