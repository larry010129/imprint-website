import { useCallback, useEffect, useState } from "react";

import PageImageEditModal, {
  type PageImageEditRow,
} from "@/components/admin/PageImageEditModal";
import { pageImageSaveKeys } from "@/lib/page-image-save-keys";
import { bustImageUrl } from "@/lib/image-cache-bust";
import type { ImageUploadResult } from "@/components/ui/image-upload";

export type SitePageImageEditorApi = {
  getPageImages: (opts?: {
    page_key?: string;
    pageSize?: number;
  }) => Promise<{
    pageImages?: PageImageEditRow[];
    error?: string;
  }>;
  updatePageImage: (fields: {
    pageKey: string;
    slotKey: string;
    imageUrl: string;
    imageWebp: string;
    imageAlt: string;
    isPublished: boolean;
  }) => Promise<{
    pageImage?: PageImageEditRow;
    error?: string | { message?: string };
  }>;
  uploadPageImage: (file: File, pageKey?: string) => Promise<ImageUploadResult>;
  pageImageAction?: (
    pageKey: string,
    slotKey: string,
    action: "restore" | "reset" | "publish" | "unpublish",
  ) => Promise<{
    pageImage?: PageImageEditRow;
    ok?: boolean;
    error?: string | { message?: string };
  }>;
};

export default function SitePageImageEditor({
  pageKey,
  api,
}: {
  pageKey: string;
  api: SitePageImageEditorApi;
}) {
  const [rows, setRows] = useState<PageImageEditRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<PageImageEditRow | null>(null);

  const reload = useCallback(() => {
    setLoading(true);
    setError(null);
    return api
      .getPageImages({ page_key: pageKey, pageSize: 100 })
      .then((res) => {
        if (res.error) {
          setError(String(res.error));
          setRows([]);
          return;
        }
        setRows(res.pageImages || []);
      })
      .catch((err) => {
        setError(String(err));
        setRows([]);
      })
      .finally(() => setLoading(false));
  }, [api, pageKey]);

  useEffect(() => {
    void reload();
  }, [reload]);

  return (
    <section className="cms-copy-group">
      <h3 className="cms-copy-group__title">頁面圖片</h3>
      {loading ? <p className="cms-hint">載入圖片中…</p> : null}
      {error ? <p className="cms-msg cms-msg--error">{error}</p> : null}
      {!loading && !error && !rows.length ? (
        <p className="cms-hint">此頁尚無圖片列。請先在「頁面圖片」分頁建立區塊。</p>
      ) : null}
      {rows.map((row) => {
        const keys = pageImageSaveKeys(row);
        const src = bustImageUrl(
          row.image_url || row.display_url || row.default_image_url,
        );
        return (
          <article className="cms-copy-card" key={`${row.page_key}\u001f${row.slot_key}`}>
            <div className="cms-copy-card__header">
              <h4>{row.slot_label || row.slot_key}</h4>
              <span className="cms-hint">
                {row.target_w}×{row.target_h}
              </span>
            </div>
            {src ? (
              <img
                src={src}
                alt=""
                width={row.target_w || 56}
                height={row.target_h || 36}
                style={{ maxWidth: 140, height: "auto", borderRadius: 4 }}
              />
            ) : (
              <p className="cms-hint">未設定</p>
            )}
            <div className="cms-copy-card__actions">
              <button
                type="button"
                className="btn-sm btn-primary"
                disabled={!keys}
                onClick={() => keys && setEditing({ ...row, page_key: keys.pageKey, slot_key: keys.slotKey })}
              >
                更換圖片
              </button>
            </div>
          </article>
        );
      })}
      {editing ? (
        <PageImageEditModal
          row={editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            void reload();
          }}
          uploadImage={(file) => api.uploadPageImage(file, editing.page_key)}
          updatePageImage={(fields) => {
            const keys = pageImageSaveKeys(editing);
            if (!keys) {
              return Promise.resolve({ error: "頁面圖片鍵值無效" });
            }
            return api.updatePageImage({
              pageKey: keys.pageKey,
              slotKey: keys.slotKey,
              imageUrl: fields.imageUrl,
              imageWebp: fields.imageWebp,
              imageAlt: fields.imageAlt,
              isPublished: fields.isPublished,
            });
          }}
          pageImageAction={
            api.pageImageAction
              ? (_pageKey, _slotKey, action) => {
                  const keys = pageImageSaveKeys(editing);
                  if (!keys) {
                    return Promise.resolve({ error: "頁面圖片鍵值無效" });
                  }
                  return api.pageImageAction!(keys.pageKey, keys.slotKey, action);
                }
              : undefined
          }
        />
      ) : null}
    </section>
  );
}
