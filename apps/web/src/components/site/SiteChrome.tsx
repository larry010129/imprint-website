import { readFileSync } from "fs";
import { join } from "path";

import Script from "next/script";

import FooterIsland from "@/components/site/FooterIsland";
import SocialFabIsland from "@/components/site/SocialFabIsland";

const ORG_LD = `{"@context":"https://schema.org","@type":"Organization","@id":"https://www.imprint-diamond.com/#organization","name":"銘印鑽石 IMPRINT DIAMOND","legalName":"心之銘印鑽石有限公司","url":"https://www.imprint-diamond.com/","telephone":"+886-2-2977-0268","address":{"@type":"PostalAddress","streetAddress":"福德南路43號1樓","addressLocality":"三重區","addressRegion":"新北市","addressCountry":"TW"},"contactPoint":[{"@type":"ContactPoint","telephone":"+886-2-2977-0268","contactType":"customer service","areaServed":"TW","availableLanguage":["zh-Hant"]}],"sameAs":["https://www.facebook.com/Imprintdiamond/","https://lin.ee/ktVBtmx"]}`;

const IMG_FALLBACK = `window.imgFallback=function(img){var s=img.dataset.fbStep?parseInt(img.dataset.fbStep,10):0;var e=["jpg","png","jpeg"];var pic=img.parentElement&&img.parentElement.tagName==="PICTURE"?img.parentElement:null;if(s<e.length-1){s++;img.dataset.fbStep=String(s);if(pic){var srcs=pic.querySelectorAll("source");for(var i=0;i<srcs.length;i++){srcs[i].remove();}}img.src=img.src.replace(/\\.(jpg|jpeg|png)(\\?.*)?$/i,"."+e[s]+"$2");}else{(pic||img).remove();}};`;

const BOTPRESS = `
(() => {
  "use strict";
  let loadPromise;
  const appendScript = (src) => new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = src;
    script.async = true;
    script.onload = resolve;
    script.onerror = () => reject(new Error("Unable to load " + src));
    document.head.append(script);
  });
  window.loadImprintChat = () => {
    if (loadPromise) return loadPromise;
    if (window.botpress) return Promise.resolve(window.botpress);
    loadPromise = appendScript("https://cdn.botpress.cloud/webchat/v3.6/inject.js")
      .then(() => appendScript("https://files.bpcontent.cloud/2026/03/15/22/20260315220508-1BHDZ8TO.js"))
      .then(() => appendScript("/static/js/botpress-theme.js?v=4"))
      .then(() => window.botpress)
      .catch((error) => { loadPromise = undefined; throw error; });
    return loadPromise;
  };
  const prepareChat = () => { void window.loadImprintChat().catch(() => {}); };
  const contactFab = document.querySelector("[data-social-fab]");
  const contactToggle = document.querySelector("[data-social-fab] [aria-controls]");
  contactFab?.addEventListener("pointerenter", prepareChat, { once: true });
  contactFab?.addEventListener("focusin", prepareChat, { once: true });
  contactToggle?.addEventListener("pointerdown", prepareChat, { once: true });
})();
`;

export function SiteHeadAssets({
  extraCss = [],
  lcpImage,
  lcpImageType,
}: {
  extraCss?: string[];
  lcpImage?: string | null;
  lcpImageType?: string | null;
}) {
  return (
    <>
      <script dangerouslySetInnerHTML={{ __html: IMG_FALLBACK }} />
      {lcpImage ? (
        <link
          rel="preload"
          as="image"
          href={lcpImage}
          type={lcpImageType || undefined}
          fetchPriority="high"
        />
      ) : null}
      <link rel="stylesheet" href="/static/css/base.css?v=4.2" />
      <link rel="stylesheet" href="/static/css/nav.css?v=4.3" />
      <link rel="stylesheet" href="/static/css/home.css?v=5.4" />
      <link rel="stylesheet" href="/static/css/pages.css?v=5.21" />
      <link rel="stylesheet" href="/static/css/skeleton.css?v=2" />
      <link rel="stylesheet" href="/static/css/responsive.css?v=3.15" />
      <link rel="stylesheet" href="/static/css/social-fab.css?v=8" />
      <link rel="stylesheet" href="/static/react/src.css?v=18" />
      <link rel="stylesheet" href="/static/react/footer.css?v=11" />
      {extraCss.map((href) => (
        <link key={href} rel="stylesheet" href={href} />
      ))}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: ORG_LD }}
      />
    </>
  );
}

export function SiteChrome({
  children,
  mainClass,
  mvcPage,
  extraBodyClass,
  siteCmsEdit,
  cmsPageKey,
}: {
  children: React.ReactNode;
  mainClass?: string;
  mvcPage?: string | null;
  extraBodyClass?: string | null;
  siteCmsEdit?: boolean;
  cmsPageKey?: string;
}) {
  const bodyClass = ["site-layout", extraBodyClass].filter(Boolean).join(" ");
  return (
    <div
      className={bodyClass}
      data-mvc={mvcPage || undefined}
      data-cms-site-edit={siteCmsEdit ? "1" : undefined}
      data-cms-inline={siteCmsEdit ? "1" : undefined}
      data-cms-page-key={siteCmsEdit ? cmsPageKey : undefined}
    >
      <div className="site-chrome">
        <div className="topbar">
          全台唯一在地 DNA 鑽石培育實驗室｜門市採預約制｜
          <a href="tel:0229770268" style={{ color: "inherit", textDecoration: "none" }}>
            02-29770268
          </a>
        </div>
        <div data-site-nav-root="" />
      </div>
      <Script type="module" src="/static/react/nav.js?v=31" strategy="afterInteractive" />
      <main className={mainClass || undefined}>{children}</main>
      <FooterIsland />
      <Script src="/static/js/nav-dropdown.js?v=1" strategy="afterInteractive" />
      <Script src="/static/js/skeleton-ui.js?v=1" strategy="afterInteractive" />
      <Script src="/static/js/site-layout.js?v=2" strategy="afterInteractive" />
      <Script src="/static/js/main.js?v=2.4" strategy="afterInteractive" />
      <SocialFabIsland html={socialFabMarkup()} />
      <script dangerouslySetInnerHTML={{ __html: BOTPRESS }} />
      {siteCmsEdit ? (
        <>
          <script
            dangerouslySetInnerHTML={{
              __html: `window.__CMS_SITE_PAGE_KEY__=${JSON.stringify(cmsPageKey || "")};`,
            }}
          />
          <Script src="/js/site-inline-edit.js?v=6" strategy="afterInteractive" />
          <Script src="/js/cms-inline-edit.js?v=12" strategy="afterInteractive" />
          <Script src="/js/cms-canvas-controls.js?v=2" strategy="afterInteractive" />
          <Script src="/js/cms-freeform-edit.js?v=1" strategy="afterInteractive" />
        </>
      ) : null}
    </div>
  );
}

let _socialFabHtml: string | null = null;

function socialFabMarkup(): string {
  if (_socialFabHtml) return _socialFabHtml;
  try {
    // Partial ships a <script defer> for Jinja; strip it here — Next loads via SocialFabIsland post-hydrate.
    _socialFabHtml = readFileSync(
      join(process.cwd(), "..", "..", "content", "site", "partials", "social-fab.html"),
      "utf8",
    )
      .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, "")
      .replace(/<script\b[^>]*\/>/gi, "")
      .trim();
  } catch {
    _socialFabHtml =
      '<div class="imprint-contact-fab" id="imprintContactFab" data-social-fab></div>';
  }
  return _socialFabHtml;
}

export function AuthChrome({
  children,
  mvcPage,
  extraBodyClass,
}: {
  children: React.ReactNode;
  mvcPage?: string | null;
  extraBodyClass?: string | null;
}) {
  const bodyClass = ["auth-layout", extraBodyClass].filter(Boolean).join(" ");
  return (
    <div className={bodyClass} data-site-root="" data-mvc={mvcPage || undefined}>
      <main className="auth-main">{children}</main>
      <SocialFabIsland html={socialFabMarkup()} />
      <script dangerouslySetInnerHTML={{ __html: BOTPRESS }} />
    </div>
  );
}

export function BareChrome({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
