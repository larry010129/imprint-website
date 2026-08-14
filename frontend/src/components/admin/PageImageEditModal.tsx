import { useCallback, useEffect, useState } from "react";
import { ImagePlus, RotateCcw, Trash2, Upload } from "lucide-react";

import { useImageUpload } from "@/components/hooks/use-image-upload";
import { ImageCropEditor } from "@/components/ui/image-crop-editor";
import { Button } from "@/components/ui/button-1";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { ImageUploadResult } from "@/components/ui/image-upload";
import {
  cropImageToFile,
  defaultCropPercent,
  isFullCrop,
  resolveAspectRatio,
  type CropPercent,
} from "@/lib/crop-image";
import { pageImageSaveKeys } from "@/lib/page-image-save-keys";
import { cn } from "@/lib/utils";

export type PageImageEditRow = {
  page_key: string;
  slot_key: string;
  slot_label?: string;
  label?: string;
  target_w: number;
  target_h: number;
  is_published: boolean;
  image_url?: string;
  image_webp?: string;
  image_alt?: string;
  display_url?: string;
  default_image_url?: string;
  previous_image_url?: string | null;
  previous_image_webp?: string | null;
  previousImageUrl?: string | null;
  previousImageWebp?: string | null;
};

export type PageImageEditModalProps = {
  row: PageImageEditRow;
  onClose: () => void;
  onSaved: (result?: { slotKey: string; imageUrl: string; imageAlt: string }) => void;
  uploadImage: (file: File) => Promise<ImageUploadResult>;
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

function resolveError(error: string | { message?: string } | undefined) {
  if (!error) return "儲存失敗";
  if (typeof error === "string") return error;
  return error.message || "儲存失敗";
}

function previousUrlOf(row: PageImageEditRow): string {
  return (
    row.previous_image_url ||
    row.previousImageUrl ||
    row.previous_image_webp ||
    row.previousImageWebp ||
    ""
  ).trim();
}

async function resolveUploadFile(
  previewUrl: string,
  crop: CropPercent,
  cropTouched: boolean,
  sourceFile: File | null,
  maxWidth: number,
) {
  if (!sourceFile && !cropTouched && isFullCrop(crop)) return null;
  return cropImageToFile(previewUrl, crop, sourceFile, {
    maxWidth,
    maxBytes: 1024 * 1024,
    mimeType: "image/webp",
    quality: 0.82,
  });
}

export default function PageImageEditModal({
  row,
  onClose,
  onSaved,
  uploadImage,
  updatePageImage,
  pageImageAction,
}: PageImageEditModalProps) {
  const initialPreview =
    row.display_url || row.image_url || row.default_image_url || "";
  const aspect = resolveAspectRatio(undefined, row.target_w, row.target_h) ?? 3 / 2;

  const [imageUrl, setImageUrl] = useState(row.image_url || "");
  const [imageWebp, setImageWebp] = useState(row.image_webp || "");
  const [previousUrl, setPreviousUrl] = useState(() => previousUrlOf(row));
  const [saving, setSaving] = useState(false);
  const [validationError, setValidationError] = useState("");
  const [crop, setCrop] = useState<CropPercent>(() => defaultCropPercent(aspect));
  const [cropTouched, setCropTouched] = useState(false);

  const {
    file,
    previewUrl,
    isDragging,
    inputRef,
    accept,
    openFilePicker,
    handleInputChange,
    handleDragOver,
    handleDragLeave,
    handleDrop,
    resetPreview,
    hasPreview,
  } = useImageUpload({
    initialPreviewUrl: initialPreview,
    onValidationError: setValidationError,
  });

  useEffect(() => {
    setCropTouched(false);
    setValidationError("");
  }, [file, previewUrl]);

  const handleCropChange = useCallback((next: CropPercent) => {
    setCrop(next);
    setCropTouched(true);
  }, []);

  const handleCropInit = useCallback((next: CropPercent) => {
    setCrop(next);
  }, []);

  const applySavedRow = useCallback(
    (saved: PageImageEditRow | undefined, fallbackUrl: string) => {
      const nextUrl = saved?.image_url || fallbackUrl;
      const nextWebp = saved?.image_webp || "";
      const nextPrev = saved ? previousUrlOf(saved) : "";
      setImageUrl(nextUrl);
      setImageWebp(nextWebp);
      setPreviousUrl(nextPrev);
      if (nextUrl) resetPreview(nextUrl);
      onSaved({
        slotKey: row.slot_key,
        imageUrl: nextUrl,
        imageAlt: row.image_alt || "",
      });
    },
    [onSaved, resetPreview, row.image_alt, row.slot_key],
  );

  const handleSave = useCallback(async () => {
    setSaving(true);
    setValidationError("");
    let nextUrl = imageUrl;
    let nextWebp = imageWebp;

    try {
      const needsUpload =
        Boolean(file) || (cropTouched && !isFullCrop(crop) && hasPreview);
      if (needsUpload) {
        const uploadFile = await resolveUploadFile(
          previewUrl,
          crop,
          cropTouched,
          file,
          row.target_w,
        );
        if (!uploadFile) {
          setValidationError("請選擇圖片");
          return;
        }
        const uploadRes = await uploadImage(uploadFile);
        if (uploadRes.error || !uploadRes.url) {
          setValidationError(resolveError(uploadRes.error));
          return;
        }
        nextUrl = uploadRes.url;
        nextWebp = /\.webp$/i.test(nextUrl) ? nextUrl : "";
        setImageUrl(nextUrl);
        setImageWebp(nextWebp);
      }

      const keys = pageImageSaveKeys(row);
      if (!keys) {
        setValidationError("頁面圖片鍵值無效");
        return;
      }
      const updateRes = await updatePageImage({
        pageKey: keys.pageKey,
        slotKey: keys.slotKey,
        imageUrl: nextUrl,
        imageWebp: nextWebp,
        imageAlt: row.image_alt || "",
        isPublished: !!row.is_published,
      });

      if (updateRes.error) {
        setValidationError(resolveError(updateRes.error));
        return;
      }

      applySavedRow(updateRes.pageImage, nextUrl);
    } catch (error) {
      setValidationError(error instanceof Error ? error.message : "裁切失敗");
    } finally {
      setSaving(false);
    }
  }, [
    applySavedRow,
    crop,
    cropTouched,
    file,
    hasPreview,
    imageUrl,
    imageWebp,
    previewUrl,
    row.image_alt,
    row.is_published,
    row.page_key,
    row.slot_key,
    row.target_w,
    updatePageImage,
    uploadImage,
  ]);

  const handleRestore = useCallback(async () => {
    if (!pageImageAction || !previousUrl) return;
    setSaving(true);
    setValidationError("");
    try {
      const keys = pageImageSaveKeys(row);
      if (!keys) {
        setValidationError("頁面圖片鍵值無效");
        return;
      }
      const res = await pageImageAction(keys.pageKey, keys.slotKey, "restore");
      if (res.error) {
        setValidationError(resolveError(res.error));
        return;
      }
      applySavedRow(res.pageImage, previousUrl);
    } catch (error) {
      setValidationError(error instanceof Error ? error.message : "還原失敗");
    } finally {
      setSaving(false);
    }
  }, [applySavedRow, pageImageAction, previousUrl, row.page_key, row.slot_key]);

  const title = row.slot_label || row.label || "圖片";

  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <DialogContent
        className="border-[#ede7e0] bg-white text-[#2b2320] sm:max-w-md"
        data-admin-root=""
      >
        <DialogHeader>
          <DialogTitle>更換圖片 · {title}</DialogTitle>
          {row.label ? (
            <p className="text-sm text-[#8a817b]">
              {row.label}
              {"　"}
              建議尺寸{" "}
              <strong className="font-semibold text-[#2b2320]">
                {row.target_w}×{row.target_h}
              </strong>{" "}
              px
            </p>
          ) : null}
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label>上傳新圖（JPG / PNG / WEBP，來源 ≤1MB；存檔 ≤500KB WebP）</Label>
            <Input
              ref={inputRef}
              type="file"
              accept={accept}
              className="hidden"
              onChange={handleInputChange}
            />

            {!hasPreview ? (
              <button
                type="button"
                disabled={saving}
                onClick={openFilePicker}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={cn(
                  "flex w-full flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-4 py-8 text-center transition-colors",
                  "border-[#ede7e0] bg-[#fafaf8] text-[#8a817b] hover:border-[#2b2320]/30 hover:bg-[#f7f3ee]",
                  isDragging && "border-[#5ecfcf] bg-[#f0fbfb]",
                )}
              >
                <div className="flex size-10 items-center justify-center rounded-full bg-white shadow-sm">
                  <ImagePlus className="size-5 text-[#2b2320]" aria-hidden />
                </div>
                <div className="space-y-1">
                  <p className="text-sm font-medium text-[#2b2320]">點擊選擇圖片</p>
                  <p className="text-xs">或拖曳檔案到此</p>
                </div>
                <p className="text-[11px] text-[#8a817b]">
                  支援 JPG / PNG / WEBP · 來源 ≤1MB · 上傳後轉 WebP 並壓縮至 ≤500KB
                </p>
              </button>
            ) : (
              <div className="space-y-3">
                <ImageCropEditor
                  src={previewUrl}
                  aspectRatio={aspect}
                  crop={crop}
                  onCropChange={handleCropChange}
                  onCropInit={handleCropInit}
                  disabled={saving}
                />
                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    className="border-[#ede7e0] bg-white text-[#2b2320] shadow-none hover:bg-[#f7f3ee]"
                    onClick={openFilePicker}
                  >
                    <Upload className="size-3.5" aria-hidden />
                    更換
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    className="border-[#ede7e0] bg-white text-[#c0392b] shadow-none hover:bg-[#fef5f4]"
                    onClick={() => {
                      resetPreview("");
                      setImageUrl("");
                      setImageWebp("");
                      setCropTouched(false);
                    }}
                  >
                    <Trash2 className="size-3.5" aria-hidden />
                    移除
                  </Button>
                </div>
              </div>
            )}

            {previousUrl && pageImageAction ? (
              <Button
                type="button"
                size="sm"
                variant="outline"
                className="border-[#ede7e0] bg-white text-[#2b2320] shadow-none hover:bg-[#f7f3ee]"
                disabled={saving}
                onClick={() => void handleRestore()}
              >
                <RotateCcw className="size-3.5" aria-hidden />
                還原上一張
              </Button>
            ) : null}

            {file ? (
              <p className="text-xs text-[#8a817b]">已選擇新圖片，儲存後才會上傳。</p>
            ) : hasPreview ? (
              <p className="text-xs text-[#8a817b]">拖曳選取裁切範圍，儲存時會套用裁切。</p>
            ) : null}
            {validationError ? (
              <p className="text-xs text-[#c0392b]">{validationError}</p>
            ) : null}
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-3">
          <Button type="button" variant="outline" size="sm" onClick={onClose}>
            取消
          </Button>
          <Button
            type="button"
            size="sm"
            disabled={saving}
            onClick={() => void handleSave()}
          >
            {saving ? "儲存中…" : "儲存"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
