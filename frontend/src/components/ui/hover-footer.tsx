"use client";
import { useRef, useEffect, useState } from "react";
import { cn } from "@/lib/utils";

export const TextHoverEffect = ({
  text,
  duration,
  className,
}: {
  text: string;
  duration?: number;
  automatic?: boolean;
  className?: string;
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const gradientRef = useRef<SVGRadialGradientElement>(null);
  const pointerRef = useRef({ x: 0, y: 0 });
  const frameRef = useRef<number | null>(null);
  const [hovered, setHovered] = useState(false);

  useEffect(() => {
    return () => {
      if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
    };
  }, []);

  function trackPointer(clientX: number, clientY: number) {
    pointerRef.current = { x: clientX, y: clientY };
    if (frameRef.current !== null) return;
    frameRef.current = requestAnimationFrame(() => {
      frameRef.current = null;
      const gradient = gradientRef.current;
      const svg = svgRef.current;
      if (!gradient || !svg) return;
      const svgRect = svg.getBoundingClientRect();
      if (!svgRect.width || !svgRect.height) return;
      const cx = ((pointerRef.current.x - svgRect.left) / svgRect.width) * 100;
      const cy = ((pointerRef.current.y - svgRect.top) / svgRect.height) * 100;
      gradient.setAttribute("cx", `${cx}%`);
      gradient.setAttribute("cy", `${cy}%`);
    });
  }

  return (
    <svg
      ref={svgRef}
      width="100%"
      height="100%"
      viewBox="0 0 300 100"
      xmlns="http://www.w3.org/2000/svg"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onMouseMove={(e) => trackPointer(e.clientX, e.clientY)}
      className={cn("select-none uppercase cursor-pointer", className)}
    >
      <defs>
        <linearGradient
          id="textGradient"
          gradientUnits="userSpaceOnUse"
          cx="50%"
          cy="50%"
          r="25%"
        >
          {hovered && (
            <>
              <stop offset="0%" stopColor="#eab308" />
              <stop offset="25%" stopColor="#ef4444" />
              <stop offset="50%" stopColor="#80eeb4" />
              <stop offset="75%" stopColor="#06b6d4" />
              <stop offset="100%" stopColor="#8b5cf6" />
            </>
          )}
        </linearGradient>

        <radialGradient
          ref={gradientRef}
          id="revealMask"
          gradientUnits="userSpaceOnUse"
          r="20%"
          cx="50%"
          cy="50%"
          style={{ transition: `cx ${duration ?? 0}s ease-out, cy ${duration ?? 0}s ease-out` }}
        >
          <stop offset="0%" stopColor="white" />
          <stop offset="100%" stopColor="black" />
        </radialGradient>
        <mask id="textMask">
          <rect
            x="0"
            y="0"
            width="100%"
            height="100%"
            fill="url(#revealMask)"
          />
        </mask>
      </defs>
      <text
        x="50%"
        y="50%"
        textAnchor="middle"
        dominantBaseline="middle"
        strokeWidth="0.3"
        className="fill-transparent stroke-neutral-200 font-[helvetica] text-7xl font-bold dark:stroke-neutral-800"
        style={{ opacity: hovered ? 0.7 : 0 }}
      >
        {text}
      </text>
      <text
        x="50%"
        y="50%"
        textAnchor="middle"
        dominantBaseline="middle"
        strokeWidth="0.3"
        className="footer-hover-stroke-draw fill-transparent stroke-[#3ca2fa] font-[helvetica] text-7xl font-bold
        dark:stroke-[#3ca2fa99]"
      >
        {text}
      </text>
      <text
        x="50%"
        y="50%"
        textAnchor="middle"
        dominantBaseline="middle"
        stroke="url(#textGradient)"
        strokeWidth="0.3"
        mask="url(#textMask)"
        className="fill-transparent font-[helvetica] text-7xl font-bold"
      >
        {text}
      </text>
    </svg>
  );
};

export const FooterBackgroundGradient = () => {
  return (
    <div
      className="absolute inset-0 z-0"
      style={{
        background:
          "radial-gradient(125% 125% at 50% 10%, #0F0F1166 50%, #3ca2fa33 100%)",
      }}
    />
  );
};
