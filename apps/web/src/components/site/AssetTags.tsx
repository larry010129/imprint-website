import Script from "next/script";

import type { ScriptAsset } from "@/lib/page-registry";

export function StylesheetLinks({ hrefs }: { hrefs: string[] }) {
  return (
    <>
      {hrefs.map((href) => (
        <link key={href} rel="stylesheet" href={href} />
      ))}
    </>
  );
}

export function PageScripts({ scripts }: { scripts: ScriptAsset[] }) {
  return (
    <>
      {scripts.map((scr, i) => {
        if (scr.inline) {
          return (
            <script
              key={`inline-${i}`}
              type={scr.type || undefined}
              dangerouslySetInnerHTML={{ __html: scr.inline }}
            />
          );
        }
        if (!scr.src) return null;
        return (
          <Script
            key={scr.src + i}
            src={scr.src}
            strategy="afterInteractive"
            type={scr.type === "module" ? "module" : undefined}
          />
        );
      })}
    </>
  );
}
