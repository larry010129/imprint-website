"use client";

import { useEffect, useRef } from "react";

/** Mount legacy footer island only after hydration — avoids SSR/client DOM mismatch. */
export default function FooterIsland() {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const root = ref.current;
    if (!root) return;

    let requested = false;
    let observer: IntersectionObserver | undefined;

    const load = () => {
      if (requested || root.dataset.footerRequested === "1") return;
      requested = true;
      root.dataset.footerRequested = "1";
      const script = document.createElement("script");
      script.type = "module";
      script.src = "/static/react/footer.js?v=11";
      document.body.appendChild(script);
    };

    const nearViewport =
      root.getBoundingClientRect().top <= window.innerHeight + 800;
    if (nearViewport || !("IntersectionObserver" in window)) {
      load();
    } else {
      observer = new IntersectionObserver(
        (entries) => {
          if (!entries.some((entry) => entry.isIntersecting)) return;
          observer?.disconnect();
          load();
        },
        { rootMargin: "800px 0px" },
      );
      observer.observe(root);
    }

    return () => observer?.disconnect();
  }, []);

  return <div ref={ref} data-hover-footer-root="" />;
}
