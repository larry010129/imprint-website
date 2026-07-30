"use client";

import { useEffect } from "react";

/** SSR fab markup; load mutator script only after hydration. */
export default function SocialFabIsland({ html }: { html: string }) {
  useEffect(() => {
    if (document.querySelector("script[data-imprint-social-fab]")) return;
    const script = document.createElement("script");
    script.src = "/static/js/social-fab.js?v=6";
    script.dataset.imprintSocialFab = "1";
    document.body.appendChild(script);
  }, []);

  return <div dangerouslySetInnerHTML={{ __html: html }} />;
}
