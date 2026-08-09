import { IMAGE_ACCEPT, validateImageFile } from "@/lib/image-file";

export type CmsMediaItem = { id: string; url: string; alt?: string };

export default function CmsMediaModal({
  media,
  total,
  page = 1,
  pageSize = 20,
  onPageChange,
  onClose,
  onDelete,
  onSelect,
  onUpload,
  onInvalid,
}: {
  media: CmsMediaItem[];
  total?: number;
  page?: number;
  pageSize?: number;
  onPageChange?: (page: number) => void;
  onClose: () => void;
  onDelete: (item: CmsMediaItem) => void;
  onSelect: (item: CmsMediaItem) => void;
  onUpload: (file: File) => void;
  onInvalid?: (message: string) => void;
}) {
  const recordCount = total ?? media.length;
  const pageCount = Math.max(1, Math.ceil(recordCount / Math.max(pageSize, 1)));
  const showPager = typeof onPageChange === "function" && recordCount > pageSize;

  return (
    <div
      className="cms-media-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="cms-media-title"
    >
      <div className="cms-media-modal__card">
        <header>
          <h3 id="cms-media-title">媒體庫</h3>
          <button type="button" className="btn-sm" onClick={onClose}>
            關閉
          </button>
        </header>
        <label className="btn-sm cms-upload">
          上傳圖片
          <input
            type="file"
            accept={IMAGE_ACCEPT}
            hidden
            onChange={(event) => {
              const input = event.target;
              const file = input.files?.[0];
              input.value = "";
              if (!file) return;
              const err = validateImageFile(file);
              if (err) {
                onInvalid?.(err);
                return;
              }
              onUpload(file);
            }}
          />
        </label>
        <p className="cms-hint">
          JPG / PNG / WEBP，來源 ≤1MB；上傳後轉 WebP 並壓縮至 ≤500KB
          {recordCount ? ` · 共 ${recordCount} 張` : ""}
        </p>
        <div className="cms-media-grid">
          {media.map((item) => (
            <div key={item.id} className="cms-media-item">
              <button
                type="button"
                className="cms-media-item__select"
                onClick={() => onSelect(item)}
              >
                <img src={item.url} alt={item.alt || ""} loading="lazy" decoding="async" />
              </button>
              <button
                type="button"
                className="cms-media-item__delete"
                onClick={() => onDelete(item)}
              >
                刪除
              </button>
            </div>
          ))}
        </div>
        {showPager ? (
          <div className="cms-media-pager" style={{ display: "flex", gap: 8, marginTop: 12, alignItems: "center" }}>
            <button
              type="button"
              className="btn-sm"
              disabled={page <= 1}
              onClick={() => onPageChange?.(page - 1)}
            >
              上一頁
            </button>
            <span className="cms-hint">
              第 {page} / {pageCount} 頁
            </span>
            <button
              type="button"
              className="btn-sm"
              disabled={page >= pageCount}
              onClick={() => onPageChange?.(page + 1)}
            >
              下一頁
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
