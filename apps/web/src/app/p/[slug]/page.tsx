import type { Metadata } from "next";
import { notFound } from "next/navigation";

import CmsInlineScripts from "@/components/cms/CmsInlineScripts";
import CmsPageView from "@/components/cms/CmsPageView";
import { fetchCmsPage } from "@/lib/cms";
import "@/styles/cms-sections.css";

type PageProps = {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ preview?: string; inline?: string; t?: string }>;
};

function flag(v: string | undefined) {
  return v === "1" || v === "true" || v === "yes";
}

export async function generateMetadata({
  params,
  searchParams,
}: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const sp = await searchParams;
  const preview = flag(sp.preview) || flag(sp.inline);
  const payload = await fetchCmsPage(slug, { preview });
  if (!payload) return { title: "頁面不存在" };
  return {
    title: payload.page.title,
    description: payload.page.meta_description || undefined,
  };
}

export default async function CmsPublicPage({ params, searchParams }: PageProps) {
  const { slug } = await params;
  const sp = await searchParams;
  const preview = flag(sp.preview);
  const inline = flag(sp.inline);
  const wantPreview = preview || inline;

  const payload = await fetchCmsPage(slug, { preview: wantPreview });
  if (!payload) notFound();

  return (
    <>
      <style>{`
        .cms-preview-banner {
          position: sticky; top: 0; z-index: 80;
          background: #1a1a1a; color: #fff;
          text-align: center; padding: 0.5rem 1rem;
          font-size: 0.85rem; letter-spacing: 0.04em;
        }
        .cms-page[data-cms-inline] a[href] { cursor: default; }
      `}</style>
      <main className="cms-modular">
        <CmsPageView payload={payload} preview={preview} inline={inline} />
      </main>
      <CmsInlineScripts enabled={inline} />
    </>
  );
}
