import { useCallback, useState } from "react";

import { ImageCropEditor } from "@/components/ui/image-crop-editor";
import { Button } from "@/components/ui/button-1";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  cropImageToFile,
  defaultCropPercent,
  isFullCrop,
  type CropPercent,
} from "@/lib/crop-image";

/** Optional square guide for shop thumbs; off by default to preserve original. */
const SQUARE_ASPECT = 1;

export type ProductImageCropResult = {
  file: File;
  skippedCrop: boolean;
};

export type ProductImageCropModalProps = {
  previewUrl: string;
  file: File;
  fileLabel?: string;
  onComplete: (result: ProductImageCropResult) => void;
  onCancel: () => void;
};

/**
 * Product upload crop (same ImageCropEditor / cropImageToFile as 頁面圖片).
 * Default: freeform full-frame — no forced aspect; skip re-encode when untouched.
 */
export default function ProductImageCropModal({
  previewUrl,
  file,
  fileLabel,
  onComplete,
  onCancel,
}: ProductImageCropModalProps) {
  const [lockSquare, setLockSquare] = useState(false);
  const aspect = lockSquare ? SQUARE_ASPECT : undefined;
  const [crop, setCrop] = useState<CropPercent>(() => defaultCropPercent(undefined));
  const [cropTouched, setCropTouched] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const handleCropChange = useCallback((next: CropPercent) => {
    setCrop(next);
    setCropTouched(true);
  }, []);

  const handleCropInit = useCallback((next: CropPercent) => {
    setCrop(next);
  }, []);

  const handleLockSquare = useCallback((checked: boolean) => {
    setLockSquare(checked);
    setCropTouched(false);
    setCrop(defaultCropPercent(checked ? SQUARE_ASPECT : undefined));
  }, []);

  const finishOriginal = useCallback(() => {
    onComplete({ file, skippedCrop: true });
  }, [file, onComplete]);

  const finishWithCrop = useCallback(async () => {
    if (!previewUrl) {
      setError("請選擇圖片");
      return;
    }
    // Freeform + untouched/full frame = keep original bytes (no forced crop).
    // 1:1 lock means user opted into aspect crop even before dragging.
    const keepOriginal =
      !lockSquare && (!cropTouched || isFullCrop(crop));
    if (keepOriginal) {
      finishOriginal();
      return;
    }
    setBusy(true);
    setError("");
    try {
      const cropped = await cropImageToFile(previewUrl, crop, file, {
        maxWidth: 2000,
        maxBytes: 1024 * 1024,
        mimeType: "image/webp",
        quality: 0.88,
      });
      if (!cropped.size) {
        setError("裁切結果是空的，請重試");
        return;
      }
      onComplete({ file: cropped, skippedCrop: false });
    } catch (e) {
      setError(e instanceof Error ? e.message : "裁切失敗");
    } finally {
      setBusy(false);
    }
  }, [
    crop,
    cropTouched,
    file,
    finishOriginal,
    lockSquare,
    onComplete,
    previewUrl,
  ]);

  const nameHint = fileLabel || file.name || "圖片";

  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open) onCancel();
      }}
    >
      <DialogContent
        className="z-[221] border-[#ede7e0] bg-white text-[#2b2320] sm:max-w-lg"
        overlayClassName="z-[220]"
        data-admin-root=""
      >
        <DialogHeader>
          <DialogTitle>裁切商品圖片</DialogTitle>
          <p className="text-sm text-[#8a817b]">
            {nameHint}
            <br />
            預設保留原圖比例；可選裁切，或略過直接上傳。
          </p>
        </DialogHeader>

        <div className="space-y-3">
          <label className="flex cursor-pointer items-center gap-2 text-sm text-[#2b2320]">
            <input
              type="checkbox"
              className="size-4 accent-[#2b2320]"
              checked={lockSquare}
              disabled={busy}
              onChange={(e) => handleLockSquare(e.target.checked)}
            />
            <span>鎖定正方形 1:1（選用，適合縮圖）</span>
          </label>

          <ImageCropEditor
            key={lockSquare ? "square" : "free"}
            src={previewUrl}
            aspectRatio={aspect}
            crop={crop}
            onCropChange={handleCropChange}
            onCropInit={handleCropInit}
            disabled={busy}
          />

          <p className="text-xs text-[#8a817b]">
            未調整裁切框時會直接上傳原檔，不會強制裁切。
          </p>
          {error ? <p className="text-xs text-[#c0392b]">{error}</p> : null}
        </div>

        <DialogFooter className="gap-2 sm:gap-3">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onCancel}
            disabled={busy}
          >
            取消
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={finishOriginal}
            disabled={busy || !previewUrl}
          >
            略過裁切，直接上傳
          </Button>
          <Button
            type="button"
            size="sm"
            disabled={busy || !previewUrl}
            onClick={() => void finishWithCrop()}
          >
            {busy ? "處理中…" : "確認裁切並上傳"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
