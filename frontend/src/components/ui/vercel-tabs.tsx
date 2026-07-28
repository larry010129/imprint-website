import * as React from "react";
import { useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";

export type VercelTab = {
  id: string;
  label: string;
};

export type VercelTabsProps = React.HTMLAttributes<HTMLDivElement> & {
  tabs: VercelTab[];
  activeTab?: string;
  onTabChange?: (tabId: string) => void;
};

const VercelTabs = React.forwardRef<HTMLDivElement, VercelTabsProps>(
  ({ className, tabs, activeTab, onTabChange, ...props }, ref) => {
    const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
    const [activeIndex, setActiveIndex] = useState(0);
    const [hoverStyle, setHoverStyle] = useState<React.CSSProperties>({});
    const [activeStyle, setActiveStyle] = useState<React.CSSProperties>({
      left: "0px",
      width: "0px",
    });
    const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);

    useEffect(() => {
      if (!activeTab) return;
      const idx = tabs.findIndex((tab) => tab.id === activeTab);
      if (idx >= 0) setActiveIndex(idx);
    }, [activeTab, tabs]);

    useEffect(() => {
      if (hoveredIndex === null) return;
      const hoveredElement = tabRefs.current[hoveredIndex];
      if (!hoveredElement) return;
      setHoverStyle({
        left: `${hoveredElement.offsetLeft}px`,
        width: `${hoveredElement.offsetWidth}px`,
      });
    }, [hoveredIndex]);

    useEffect(() => {
      const activeElement = tabRefs.current[activeIndex];
      if (!activeElement) return;
      setActiveStyle({
        left: `${activeElement.offsetLeft}px`,
        width: `${activeElement.offsetWidth}px`,
      });
    }, [activeIndex, tabs]);

    useEffect(() => {
      const frame = requestAnimationFrame(() => {
        const firstElement = tabRefs.current[activeIndex] || tabRefs.current[0];
        if (!firstElement) return;
        setActiveStyle({
          left: `${firstElement.offsetLeft}px`,
          width: `${firstElement.offsetWidth}px`,
        });
      });
      return () => cancelAnimationFrame(frame);
    }, [activeIndex, tabs]);

    return (
      <div ref={ref} className={cn("relative", className)} {...props}>
        <div className="relative overflow-x-auto pb-1.5">
          <div
            className="pointer-events-none absolute h-[30px] rounded-[6px] bg-[#2b232014] transition-all duration-300 ease-out"
            style={{
              ...hoverStyle,
              opacity: hoveredIndex !== null ? 1 : 0,
            }}
          />
          <div
            className="pointer-events-none absolute bottom-[-6px] h-[2px] bg-[#2b2320] transition-all duration-300 ease-out"
            style={activeStyle}
          />
          <div className="relative flex items-center space-x-[6px]" role="tablist">
            {tabs.map((tab, index) => (
              <button
                key={tab.id}
                type="button"
                role="tab"
                aria-selected={index === activeIndex}
                ref={(el) => {
                  tabRefs.current[index] = el;
                }}
                className={cn(
                  "h-[30px] cursor-pointer px-3 py-2 transition-colors duration-300",
                  index === activeIndex ? "text-[#2b2320]" : "text-[#2b232099]",
                )}
                onMouseEnter={() => setHoveredIndex(index)}
                onMouseLeave={() => setHoveredIndex(null)}
                onClick={() => {
                  setActiveIndex(index);
                  onTabChange?.(tab.id);
                }}
              >
                <span className="flex h-full items-center justify-center whitespace-nowrap text-sm font-medium leading-5">
                  {tab.label}
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  },
);
VercelTabs.displayName = "VercelTabs";

export { VercelTabs };
