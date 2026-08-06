import { useScroll, useTransform, motion } from "motion/react";
import React, { useEffect, useRef, useState } from "react";

interface TimelineEntry {
  year: string;
  month: string;
  content: React.ReactNode;
}

interface TimelineProps {
  data: TimelineEntry[];
  eyebrow?: string;
  heading?: string;
  description?: string;
}

function shouldShowYear(data: TimelineEntry[], index: number): boolean {
  if (index === 0) return true;
  return data[index].year !== data[index - 1].year;
}

export const Timeline = ({ data, eyebrow, heading, description }: TimelineProps) => {
  const ref = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [height, setHeight] = useState(0);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const measure = () => {
      setHeight(el.getBoundingClientRect().height);
    };

    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, [data]);

  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start 10%", "end 50%"],
  });

  const heightTransform = useTransform(scrollYProgress, [0, 1], [0, height]);
  const opacityTransform = useTransform(scrollYProgress, [0, 0.1], [0, 1]);

  return (
    <div className="w-full bg-white font-sans md:px-10" ref={containerRef}>
      {(eyebrow || heading || description) && (
        <div className="max-w-7xl mx-auto py-20 px-4 md:px-8 lg:px-10">
          {eyebrow && (
            <p className="text-sm tracking-widest text-neutral-500 mb-2">{eyebrow}</p>
          )}
          {heading && (
            <h2 className="text-lg md:text-4xl mb-4 text-black max-w-4xl">{heading}</h2>
          )}
          {description && (
            <p className="text-neutral-700 text-sm md:text-base max-w-sm">{description}</p>
          )}
        </div>
      )}

      <div ref={ref} className="relative max-w-7xl mx-auto pb-20">
        {data.map((item, index) => {
          const showYear = shouldShowYear(data, index);
          return (
            <div key={index} className="flex justify-start pt-10 md:pt-40 md:gap-10">
              <div className="sticky flex flex-col md:flex-row z-40 items-center top-40 self-start max-w-xs lg:max-w-sm md:w-full">
                <div className="h-10 absolute left-3 md:left-3 w-10 rounded-full bg-white flex items-center justify-center">
                  <div className="h-4 w-4 rounded-full bg-neutral-200 border border-neutral-300 p-2" />
                </div>
                <span className="hidden md:block absolute left-14 text-sm md:text-base font-medium tabular-nums text-neutral-400">
                  {item.month}
                </span>
                {showYear && (
                  <h3 className="hidden md:block text-xl md:pl-24 md:text-5xl font-bold text-neutral-500">
                    {item.year}
                  </h3>
                )}
              </div>

              <div className="relative pl-20 pr-4 md:pl-4 w-full">
                <div className="md:hidden mb-4 text-left">
                  {showYear && (
                    <h3 className="text-2xl font-bold text-neutral-500">{item.year}</h3>
                  )}
                  <p className="text-sm font-medium tabular-nums text-neutral-400">{item.month}</p>
                </div>
                {item.content}
              </div>
            </div>
          );
        })}
        <div
          style={{ height: height + "px" }}
          className="absolute md:left-8 left-8 top-0 overflow-hidden w-[2px] bg-[linear-gradient(to_bottom,var(--tw-gradient-stops))] from-transparent from-[0%] via-neutral-200 to-transparent to-[99%] [mask-image:linear-gradient(to_bottom,transparent_0%,black_10%,black_90%,transparent_100%)]"
        >
          <motion.div
            style={{ height: heightTransform, opacity: opacityTransform }}
            className="absolute inset-x-0 top-0 w-[2px] bg-gradient-to-t from-purple-500 via-blue-500 to-transparent from-[0%] via-[10%] rounded-full"
          />
        </div>
      </div>
    </div>
  );
};
