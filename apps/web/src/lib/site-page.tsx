import type { Metadata } from "next";
import Script from "next/script";

import { PageScripts } from "@/components/site/AssetTags";
import BodyAttrs from "@/components/site/BodyAttrs";
import JsonLd from "@/components/site/JsonLd";
import {
  AuthChrome,
  BareChrome,
  SiteChrome,
  SiteHeadAssets,
} from "@/components/site/SiteChrome";
import {
  fetchPageContext,
  readLocalBody,
  type PageContext,
} from "@/lib/page-context";
import { getPage, siteOrigin, type PageRegistryEntry } from "@/lib/page-registry";

function stripPhoneFromLd(block: string): string {
  try {
    const payload = JSON.parse(block) as unknown;
    const clean = (value: unknown): unknown => {
      if (Array.isArray(value)) return value.map(clean);
      if (value && typeof value === "object") {
        const out: Record<string, unknown> = {};
        for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
          if (k === "telephone") continue;
          out[k] = clean(v);
        }
        return out;
      }
      if (typeof value === "string") {
        return value.replace("電話：02-2977-0268；", "");
      }
      return value;
    };
    return JSON.stringify(clean(payload));
  } catch {
    return block;
  }
}

export function metadataFor(entry: PageRegistryEntry, ctx?: PageContext | null): Metadata {
  const title = ctx?.title || entry.title;
  const description = ctx?.description || entry.description;
  const ogTitle = ctx?.og_title || entry.og_title || title;
  const ogDescription = ctx?.og_description || entry.og_description || description;
  const ogImagePath =
    ctx?.og_image || entry.og_image || "images/hero/imprint-diamond-family-memorial.jpg";
  const canonical = `${siteOrigin()}/${ctx?.canonical_path ?? entry.canonical_path}`;
  const robots = ctx?.robots || entry.robots;

  return {
    title: { absolute: title },
    description: description || undefined,
    alternates: { canonical },
    robots: robots
      ? robots.includes("noindex")
        ? { index: false, follow: !robots.includes("nofollow") }
        : { index: true, follow: true }
      : { index: true, follow: true },
    openGraph: {
      type: "website",
      siteName: "銘印鑽石 IMPRINT DIAMOND",
      locale: "zh_TW",
      url: canonical,
      title: ogTitle,
      description: ogDescription || undefined,
      images: [{ url: `${siteOrigin()}/${ogImagePath}` }],
    },
    twitter: {
      card: "summary_large_image",
      images: [`${siteOrigin()}/${ogImagePath}`],
    },
  };
}

function BreadcrumbLd({
  breadcrumbs,
}: {
  breadcrumbs: [string, string | null][];
}) {
  if (!breadcrumbs?.length) return null;
  const itemListElement = breadcrumbs.map(([name, url], i) => {
    const item: Record<string, unknown> = {
      "@type": "ListItem",
      position: i + 1,
      name,
    };
    if (url) item.item = `${siteOrigin()}${url}`;
    return item;
  });
  const block = JSON.stringify({
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement,
  });
  return <JsonLd blocks={[block]} />;
}

export async function renderSiteRoute(
  route: string,
  searchParams?: { cms_edit?: string },
) {
  const entry = getPage(route);
  if (!entry) {
    return { notFound: true as const };
  }

  const cmsEdit =
    searchParams?.cms_edit === "1" ||
    searchParams?.cms_edit === "true" ||
    searchParams?.cms_edit === "yes";

  const ctx = await fetchPageContext(route, {
    cmsEdit,
    includeBody: true,
  });

  let bodyHtml = ctx?.body_html;
  if (!bodyHtml) {
    bodyHtml = await readLocalBody(entry.body_key);
  }

  const layout = ctx?.layout || entry.layout;
  const extraCss = ctx?.extra_css?.length ? ctx.extra_css : entry.extra_css;
  const extraScripts = ctx?.extra_scripts?.length
    ? ctx.extra_scripts
    : entry.extra_scripts;
  const mainClass = ctx?.main_class || entry.main_class;
  const mvcPage = ctx?.mvc_page ?? entry.mvc_page;
  const extraBodyClass = ctx?.extra_body_class ?? entry.extra_body_class;
  const headBlocks = (ctx?.extra_head_blocks || entry.extra_head_blocks || []).map(
    stripPhoneFromLd,
  );
  const breadcrumbs = (ctx?.breadcrumbs || entry.breadcrumbs || []) as [
    string,
    string | null,
  ][];
  const siteCmsEdit = Boolean(ctx?.site_cms_edit);
  const googleId = ctx?.google_client_id || "";

  const bodyClass = [
    layout === "auth" ? "auth-layout" : layout === "bare" ? "" : "site-layout",
    extraBodyClass,
  ]
    .filter(Boolean)
    .join(" ");

  const content = (
    <div dangerouslySetInnerHTML={{ __html: bodyHtml }} />
  );

  const headBits = (
    <>
      {layout === "site" ? (
        <SiteHeadAssets
          extraCss={extraCss}
          lcpImage={ctx?.lcp_image}
          lcpImageType={ctx?.lcp_image_type}
        />
      ) : (
        <>
          <link rel="stylesheet" href="/static/css/social-fab.css?v=8" />
          {extraCss.map((href) => (
            <link key={href} rel="stylesheet" href={href} />
          ))}
        </>
      )}
      {entry.head_extras?.map((extra, i) =>
        extra.tag === "link" && extra.href ? (
          <link
            key={i}
            rel={extra.rel}
            as={extra.as}
            href={extra.href}
            type={extra.type}
            {...(extra.fetchpriority
              ? { fetchPriority: extra.fetchpriority as "high" | "low" | "auto" }
              : {})}
          />
        ) : null,
      )}
      <JsonLd blocks={headBlocks} />
      <BreadcrumbLd breadcrumbs={breadcrumbs} />
      {googleId ? (
        <>
          <Script
            src="https://accounts.google.com/gsi/client"
            strategy="afterInteractive"
          />
          <script
            dangerouslySetInnerHTML={{
              __html: `window.IMPRINT_GOOGLE_CLIENT_ID = ${JSON.stringify(googleId)};`,
            }}
          />
        </>
      ) : null}
    </>
  );

  let shell: React.ReactNode;
  if (layout === "auth") {
    shell = (
      <AuthChrome mvcPage={mvcPage} extraBodyClass={extraBodyClass}>
        {content}
      </AuthChrome>
    );
  } else if (layout === "bare") {
    shell = <BareChrome>{content}</BareChrome>;
  } else {
    shell = (
      <SiteChrome
        mainClass={mainClass}
        mvcPage={mvcPage}
        extraBodyClass={extraBodyClass}
        siteCmsEdit={siteCmsEdit}
        cmsPageKey={route}
      >
        {content}
      </SiteChrome>
    );
  }

  return {
    notFound: false as const,
    metadata: metadataFor(entry, ctx),
    node: (
      <>
        {headBits}
        <BodyAttrs
          className={bodyClass}
          mvcPage={mvcPage}
          siteCmsEdit={siteCmsEdit}
          cmsPageKey={route}
          siteRoot={layout === "auth"}
        />
        {shell}
        <PageScripts scripts={extraScripts} />
      </>
    ),
  };
}

export function createPage(route: string) {
  return {
    async generateMetadata({
      searchParams,
    }: {
      searchParams?: Promise<{ cms_edit?: string }>;
    }): Promise<Metadata> {
      const entry = getPage(route);
      if (!entry) return { title: "銘印鑽石" };
      const sp = searchParams ? await searchParams : undefined;
      const cmsEdit =
        sp?.cms_edit === "1" || sp?.cms_edit === "true" || sp?.cms_edit === "yes";
      const ctx = await fetchPageContext(route, {
        cmsEdit,
        includeBody: false,
      });
      return metadataFor(entry, ctx);
    },
    async Page({
      searchParams,
    }: {
      searchParams?: Promise<{ cms_edit?: string }>;
    }) {
      const sp = searchParams ? await searchParams : undefined;
      const result = await renderSiteRoute(route, sp);
      if (result.notFound) {
        const { notFound } = await import("next/navigation");
        notFound();
      }
      return result.node;
    },
  };
}
