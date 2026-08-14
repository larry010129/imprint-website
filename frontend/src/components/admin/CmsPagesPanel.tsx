import { useCallback, useEffect, useState } from "react";

import ExistingSitePageEditor, {
  type ExistingSitePageEditorProps,
  type PageImageKey,
  type SitePage,
} from "@/components/admin/ExistingSitePageEditor";
import { ToastProvider, useToast } from "@/components/ui/toast-1";

export type CmsPagesPanelProps = {
  /** Prefer bootstrap/site_pages constants — never unpaged listCmsPages walk. */
  initialSitePages?: SitePage[];
  pageImageKeys?: PageImageKey[];
  api: ExistingSitePageEditorProps["api"] & {
    listPages: () => Promise<{
      site_pages?: SitePage[];
      error?: string;
    }>;
  };
};

function CmsPagesPanelInner({ api, initialSitePages, pageImageKeys }: CmsPagesPanelProps) {
  const { showToast } = useToast();
  const [sitePages, setSitePages] = useState<SitePage[]>(() => initialSitePages || []);
  const [editingSiteRoute, setEditingSiteRoute] = useState<string | null>(null);

  const reload = useCallback(async () => {
    if (initialSitePages && initialSitePages.length) {
      setSitePages(initialSitePages);
      return;
    }
    const res = await api.listPages();
    if (res.error) {
      showToast(String(res.error), "error", "top-right");
      return;
    }
    setSitePages(res.site_pages || []);
  }, [api, initialSitePages, showToast]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const editingSitePage = sitePages.find((page) => page.route === editingSiteRoute);
  if (editingSitePage) {
    return (
      <ExistingSitePageEditor
        page={editingSitePage}
        pageImageKeys={pageImageKeys}
        api={api}
        onBack={() => setEditingSiteRoute(null)}
      />
    );
  }

  return (
    <div className="cms-pages-panel">
      <p className="adx-panel-note">
        選擇現有官網頁面，修改文字與圖片。不可新建頁面。試算、上架、價格表、購物車、登入不在此編輯。
      </p>
      <h3 className="cms-page-section-title">
        現有官網頁面
        <span className="adx-risk-tag" title="測試功能，開發中，使用請自負風險">
          Beta · 開發中 · 使用風險
        </span>
      </h3>
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
        {!sitePages.length ? (
          <p className="cms-hint">尚無可編輯的官網頁面。</p>
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
