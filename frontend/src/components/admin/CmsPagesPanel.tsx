import { useCallback, useEffect, useState } from "react";

import CmsPageEditor, { type CmsPageEditorProps } from "@/components/admin/CmsPageEditor";
import ExistingSitePageEditor, {
  type CopySlot,
  type ExistingSitePageEditorProps,
  type SitePage,
} from "@/components/admin/ExistingSitePageEditor";
import type { CmsPage } from "@/components/admin/cmsSectionMeta";
import { ToastProvider, useToast } from "@/components/ui/toast-1";

export type CmsPagesPanelProps = {
  api: CmsPageEditorProps["api"] &
    ExistingSitePageEditorProps["api"] & {
      listPages: () => Promise<{
        pages?: CmsPage[];
        site_pages?: SitePage[];
        error?: string;
      }>;
      createPage: (fields: {
        slug: string;
        title: string;
      }) => Promise<{ page?: CmsPage; error?: string }>;
      getCopySlots: () => Promise<{
        slots?: CopySlot[];
        pages?: SitePage[];
        error?: string;
      }>;
      updateCopySlot: (fields: Record<string, unknown>) => Promise<{
        slot?: CopySlot;
        error?: string;
      }>;
    };
};

type CmsPageRow = CmsPage & { site_route?: string; cms_path?: string };

function CmsPagesPanelInner({ api }: CmsPagesPanelProps) {
  const { showToast } = useToast();
  const [pages, setPages] = useState<CmsPageRow[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [sitePages, setSitePages] = useState<SitePage[]>([]);
  const [editingSiteRoute, setEditingSiteRoute] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [slug, setSlug] = useState("");
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async () => {
    const res = await api.listPages();
    if (res.error) {
      showToast(String(res.error), "error", "top-right");
      return;
    }
    const rows = (res.pages || []) as CmsPageRow[];
    rows.sort((a, b) => {
      const ra = a.site_route || a.slug;
      const rb = b.site_route || b.slug;
      return ra.localeCompare(rb, "zh-Hant") || a.title.localeCompare(b.title, "zh-Hant");
    });
    setPages(rows);
    setSitePages(res.site_pages || []);
  }, [api, showToast]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const editingSitePage = sitePages.find((page) => page.route === editingSiteRoute);
  if (editingSitePage) {
    return (
      <ExistingSitePageEditor
        page={editingSitePage}
        api={api}
        onBack={() => setEditingSiteRoute(null)}
      />
    );
  }

  if (editingId) {
    return (
      <CmsPageEditor
        pageId={editingId}
        api={api}
        onBack={() => {
          setEditingId(null);
          void reload();
        }}
        onDeleted={() => {
          setEditingId(null);
          void reload();
        }}
      />
    );
  }

  return (
    <div className="cms-pages-panel">
      <p className="adx-panel-note">
        「現有官網頁面」會載入真正網址與原本版面，並可在頁尾新增模組區塊。下方「新建活動頁」使用
        /p/slug 區塊編輯器。試算、上架、價格表、購物車、登入不在此編輯。
      </p>
      <h3 className="cms-page-section-title">現有官網頁面</h3>
      <div className="cms-page-list">
        {sitePages.map((page) => (
          <button
            key={page.route}
            type="button"
            className="cms-page-row"
            onClick={() => setEditingSiteRoute(page.route)}
          >
            <span className="cms-page-row__title">{page.title}</span>
            <span className="cms-page-row__slug">{page.route}</span>
            <span className="cms-page-row__status">
              {page.content_tab === "page"
                ? "編輯頁面"
                : page.content_tab === "faq"
                  ? "由 FAQ 管理"
                  : "由見證管理"}
            </span>
          </button>
        ))}
      </div>

      <h3 className="cms-page-section-title">新建活動頁</h3>
      <form
        className="cms-create-form"
        onSubmit={(e) => {
          e.preventDefault();
          if (busy) return;
          setBusy(true);
          void api.createPage({ title, slug }).then((res) => {
            setBusy(false);
            if (res.error || !res.page) {
              showToast(String(res.error || "建立失敗"), "error", "top-right");
              return;
            }
            showToast(`已建立「${res.page.title}」`, "success", "top-right");
            setTitle("");
            setSlug("");
            setEditingId(res.page.id);
          });
        }}
      >
        <input
          placeholder="頁面標題"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />
        <input
          placeholder="slug（例：spring-campaign）"
          value={slug}
          onChange={(e) => setSlug(e.target.value)}
          required
        />
        <button type="submit" className="btn-sm btn-primary" disabled={busy}>
          建立新頁
        </button>
      </form>
      <div className="cms-page-list">
        {pages.map((page) => (
          <button
            key={page.id}
            type="button"
            className="cms-page-row"
            onClick={() => setEditingId(page.id)}
          >
            <span className="cms-page-row__title">{page.title}</span>
            <span className="cms-page-row__slug">/p/{page.slug}</span>
            <span className="cms-page-row__status">
              {page.status === "published" ? "已發布" : "草稿"}
            </span>
          </button>
        ))}
        {!pages.length ? (
          <p className="cms-hint">尚無自訂活動頁。需要時可由上方建立。</p>
        ) : null}
      </div>
    </div>
  );
}

export default function CmsPagesPanel(props: CmsPagesPanelProps) {
  return (
    <ToastProvider>
      <CmsPagesPanelInner {...props} />
    </ToastProvider>
  );
}
