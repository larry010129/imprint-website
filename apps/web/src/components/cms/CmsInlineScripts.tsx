"use client";

import { useEffect } from "react";

/** Load legacy preview-edit scripts against Next-rendered DOM (same data-* hooks). */
export default function CmsInlineScripts({ enabled }: { enabled: boolean }) {
  useEffect(() => {
    if (!enabled) return;
    const scripts = [
      "/js/cms-inline-edit.js?v=12",
      "/js/cms-canvas-controls.js?v=2",
      "/js/cms-freeform-edit.js?v=2",
    ];
    const nodes: HTMLScriptElement[] = [];
    for (const src of scripts) {
      const el = document.createElement("script");
      el.src = src;
      el.async = false;
      document.body.appendChild(el);
      nodes.push(el);
    }
    return () => {
      nodes.forEach((n) => n.remove());
    };
  }, [enabled]);
  return null;
}
