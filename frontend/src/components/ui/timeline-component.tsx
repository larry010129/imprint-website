import { cn } from "@/lib/utils";

export type TimelineItem = {
  step: string;
  title: string;
  description: string;
};

export type ProcessTimelineProps = {
  items: TimelineItem[];
  className?: string;
};

/**
 * Vertical process timeline — glass cards on mint gradient line.
 * Brand-tuned for Imprint (cream / mint); accepts step data via props.
 */
export function ProcessTimeline({ items, className }: ProcessTimelineProps) {
  return (
    <div className={cn("relative mx-auto max-w-3xl py-2", className)}>
      <div
        className="absolute left-[18px] top-0 h-full w-[2px] bg-gradient-to-b from-[#dcf2f2] via-[#5ecfcf]/70 to-[#dcf2f2]"
        aria-hidden
      />

      <ol className="space-y-8">
        {items.map((item, idx) => (
          <li
            key={`${item.step}-${idx}`}
            className="relative flex animate-fade-in items-start gap-5"
            style={{ animationDelay: `${idx * 80}ms` }}
          >
            <div className="relative z-10 mt-1.5 shrink-0">
              <div
                className={cn(
                  "flex size-9 items-center justify-center rounded-full border-2 border-white",
                  "bg-gradient-to-br from-[#9cefef] to-[#5ecfcf]",
                  "text-[11px] font-semibold tracking-wider text-[#2b2320]",
                  "shadow-[0_0_14px_rgba(94,207,207,0.45)]"
                )}
                style={{ fontFamily: "var(--serif, 'Noto Serif TC', serif)" }}
              >
                {item.step}
              </div>
            </div>

            <div
              className={cn(
                "min-w-0 flex-1 rounded-lg border border-[#dcf2f2]/80 p-4 backdrop-blur-md md:p-5",
                "bg-white/75 shadow-[0_8px_28px_rgba(43,35,32,0.06)]",
                "transition-shadow duration-300 hover:shadow-[0_10px_32px_rgba(94,207,207,0.12)]"
              )}
            >
              <h3
                className="text-base font-semibold tracking-[0.06em] text-[#2b2320] md:text-[17px]"
                style={{ fontFamily: "var(--serif, 'Noto Serif TC', serif)" }}
              >
                {item.title}
              </h3>
              <p className="mt-2 text-[13px] leading-[1.85] text-[#5c534e]">{item.description}</p>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}

/** Demo default export (21st / shadcn scaffold) */
export function Component() {
  const events: TimelineItem[] = [
    { step: "01", title: "Founded yourThing", description: "The project started with a small passionate team." },
    { step: "02", title: "Launch v1.0", description: "Released our first public version with core features." },
    { step: "03", title: "Global Expansion", description: "Scaled to thousands of users in over 40 countries." },
    { step: "04", title: "New Horizons", description: "Introduced AI-powered features and deeper integrations." },
  ];
  return <ProcessTimeline items={events} />;
}
