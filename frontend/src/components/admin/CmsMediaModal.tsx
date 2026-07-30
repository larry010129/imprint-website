import { IMAGE_ACCEPT, validateImageFile } from "@/lib/image-file";

export type CmsMediaItem = { id: string; url: string; alt?: string };

export default function CmsMediaModal({
  media,
  onClose,
  onDelete,
  onSelect,
  onUpload,
  onInvalid,
}: {
  media: CmsMediaItem[];
  onClose: () => void;
  onDelete: (item: CmsMediaItem) => void;
  onSelect: (item: CmsMediaItem) => void;
  onUpload: (file: File) => void;
  onInvalid?: (message: string) => void;
}) {
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
        <div className="cms-media-grid">
          {media.map((item) => (
            <div key={item.id} className="cms-media-item">
              <button
                type="button"
                className="cms-media-item__select"
                onClick={() => onSelect(item)}
              >
                <img src={item.url} alt={item.alt || ""} />
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
      </div>
    </div>
  );
}
