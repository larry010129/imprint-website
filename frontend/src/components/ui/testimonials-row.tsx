import React, { type CSSProperties } from "react";
import { type Testimonial } from "@/components/ui/testimonials-columns-1";

/** Two horizontal marquee rows (L/R). DNA palette glass cards, 4:3 box @0.5x. */
export const TestimonialsRow = (props: {
  className?: string;
  testimonials: Testimonial[];
  duration?: number;
  reverse?: boolean;
}) => {
  const trackClass = [
    "home-testimonial-marquee__track flex w-max gap-3 pr-3",
    props.reverse ? "home-testimonial-marquee__track--reverse" : "",
  ].join(" ");

  return (
    <div
      aria-label="客戶見證跑馬燈，移入指標或聚焦可暫停"
      className={`${props.className || ""} home-testimonial-marquee`}
      tabIndex={0}
    >
      <div
        className={trackClass}
        style={{ "--marquee-duration": `${props.duration || 30}s` } as CSSProperties}
      >
        {[
          ...new Array(2).fill(0).map((_, index) => (
            <React.Fragment key={index}>
              {props.testimonials.map(({ text, image, name, role }, i) => (
                <div
                  className="flex aspect-square w-[13rem] shrink-0 flex-col overflow-hidden rounded-xl border border-white/75 bg-gradient-to-br from-white/72 to-[#d6eefa]/55 p-3 text-[#2a2438] shadow-[0_7px_18px_rgba(20,58,96,0.1)] backdrop-blur-[14px]"
                  key={`${index}-${i}-${name}`}
                >
                  <p className="line-clamp-3 text-[10px] leading-[1.7] tracking-[0.02em]">
                    {text}
                  </p>
                  <div className="mt-1.5 flex items-center gap-1.5">
                    <div
                      aria-hidden
                      className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-[#8eedf0] to-[#58cfd4] text-[9px] font-semibold text-[#2a1845]"
                      style={{ fontFamily: "var(--serif, 'Noto Serif TC', serif)" }}
                    >
                      {name.charAt(0)}
                    </div>
                    <div className="flex min-w-0 flex-col leading-tight">
                      <div className="truncate text-[10px] font-semibold tracking-tight text-[#2a2438]">
                        {name}
                      </div>
                      <div className="truncate text-[9px] tracking-tight text-[#6b6578]">
                        {role}
                      </div>
                    </div>
                  </div>
                  {image ? (
                    <div className="mt-1.5 min-h-0 flex-1 overflow-hidden rounded-lg bg-[#8eedf0]/20">
                      <img
                        src={image}
                        alt=""
                        className="h-full w-full object-cover"
                        loading="lazy"
                        decoding="async"
                      />
                    </div>
                  ) : null}
                </div>
              ))}
            </React.Fragment>
          )),
        ]}
      </div>
    </div>
  );
};
