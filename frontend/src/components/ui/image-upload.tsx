import { useCallback, useEffect, useRef, useState } from "react";
import { ImagePlus, Trash2, Upload } from "lucide-react";

import { useImageUpload } from "@/components/hooks/use-image-upload";
import { ImageCropEditor } from "@/components/ui/image-crop-editor";
import { Button } from "@/components/ui/button-1";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  cropImageToFile,
  defaultCropPercent,
  resolveAspectRatio,
  type CropPercent,
} from "@/lib/crop-image";
import { cn } from "@/lib/utils";

export type ImageUploadResult = {
  url?: string;
  error?: string | { message?: string };
};

export type ImageUploadFieldProps = {
  label?: string;
  hint?: string;
  value?: string;
  onChange?: (url: string) => void;
  onUpload?: (file: File) => Promise<ImageUploadResult>;
  uploadOnSelect?: boolean;
  className?: string;
  onValidationError?: (message: string) => void;
  /** Fired when a newly picked file is waiting for 「確認裁切並上傳」. */
  onPendingChange?: (pending: boolean) => void;
  aspectRatio?: number;
  targetW?: number;
  targetH?: number;
  cropEnabled?: boolean;
};

function resolveError(error: ImageUploadResult["error"]) {
  if (!error) return "上傳失敗";
  if (typeof error === "string") return error;
  return error.message || "上傳失敗";
}

async function resolveUploadFile(
  previewUrl: string,
  crop: CropPercent,
  sourceFile: File | null,
  maxWidth?: number,
) {
  return cropImageToFile(previewUrl, crop, sourceFile, {
    maxWidth,
    maxBytes: 1024 * 1024,
    mimeType: "image/webp",
    quality: 0.82,
  });
}

export function ImageUploadField({
  label,
  hint = "支援 JPG / PNG / WEBP · 來源 ≤1MB · 上傳後轉 WebP 並壓縮至 ≤500KB",
  value = "",
  onChange,
  onUpload,
  uploadOnSelect = true,
  className,
  onValidationError,
  onPendingChange,
  aspectRatio,
  targetW,
  targetH,
  cropEnabled = true,
}: ImageUploadFieldProps) {
  const rootRef = useRef<HTMLDivElement>(null);
  const [uploading, setUploading] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [crop, setCrop] = useState<CropPercent>(() =>
    defaultCropPercent(resolveAspectRatio(aspectRatio, targetW, targetH)),
  );
  const resolvedAspect = resolveAspectRatio(aspectRatio, targetW, targetH) ?? 3 / 2;

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
    setRemotePreview,
    hasPreview,
  } = useImageUpload({
    initialPreviewUrl: value,
    onValidationError,
  });

  // Sync from controlled `value` only when that prop changes.
  // Do not re-run when `file` clears after upload — setRemotePreview already
  // applied the new URL; re-syncing from a stale mount-time value would revert it.
  useEffect(() => {
    if (!file) setRemotePreview(value);
  }, [value, setRemotePreview]); // eslint-disable-line react-hooks/exhaustive-deps -- omit file on purpose

  const handleCropChange = useCallback((next: CropPercent) => {
    setCrop(next);
  }, []);

  const runUpload = useCallback(async (): Promise<string | null> => {
    if (!onUpload || !previewUrl) return null;
    setUploading(true);
    setLocalError(null);
    try {
      const uploadFile = await resolveUploadFile(
        previewUrl,
        crop,
        file,
        targetW,
      );
      const res = await onUpload(uploadFile);
      if (res.error || !res.url) {
        const resolved = resolveError(res.error);
        setLocalError(resolved);
        onValidationError?.(resolved);
        // Keep crop preview so the error stays visible next to the control.
        return null;
      }
      onChange?.(res.url);
      setRemotePreview(res.url);
      setLocalError(null);
      return res.url;
    } catch (error) {
      const msg = error instanceof Error ? error.message : "裁切失敗";
      setLocalError(msg);
      onValidationError?.(msg);
      return null;
    } finally {
      setUploading(false);
    }
  }, [
    crop,
    file,
    onChange,
    onUpload,
    onValidationError,
    previewUrl,
    setRemotePreview,
    targetW,
  ]);

  const isPendingLocal = Boolean(file);

  useEffect(() => {
    onPendingChange?.(isPendingLocal);
  }, [isPendingLocal, onPendingChange]);

  // A pending local crop must never be silently dropped: the parent's hidden
  // image_url still holds the OLD URL, so saving would look like a no-op replace.
  // Cancel the submit (capture, before the form's own handler), upload, then
  // re-submit so the parent reads the fresh URL. On failure nothing is saved and
  // the error stays next to the control.
  const committingRef = useRef(false);
  useEffect(() => {
    if (!uploadOnSelect || !onUpload) return;
    const onSubmitCapture = (event: Event) => {
      const form = event.target;
      const root = rootRef.current;
      if (!(form instanceof HTMLFormElement) || !root) return;
      if (!form.contains(root)) return;
      if (root.getAttribute("data-pending-upload") !== "1") return;
      event.preventDefault();
      event.stopPropagation();
      if (committingRef.current) return;
      committingRef.current = true;
      void runUpload()
        .then((url) => {
          // Another pending field in the same form re-intercepts this submit.
          if (url && form.isConnected) form.requestSubmit();
        })
        .finally(() => {
          committingRef.current = false;
        });
    };
    document.addEventListener("submit", onSubmitCapture, true);
    return () => document.removeEventListener("submit", onSubmitCapture, true);
  }, [onUpload, runUpload, uploadOnSelect]);

  const showDropZone = !hasPreview || uploading;
  // Crop only for a newly picked local file — never force re-crop of committed URLs.
  const showCrop = cropEnabled && isPendingLocal && !uploading;
  const showCommittedPreview = hasPreview && !isPendingLocal && !uploading;
  const pendingUpload =
    Boolean(onUpload) && uploadOnSelect && isPendingLocal;

  return (
    <div
      ref={rootRef}
      className={cn("space-y-2", className)}
      data-admin-root=""
      data-image-upload-root=""
      data-pending-upload={isPendingLocal ? "1" : "0"}
    >
      {label ? <Label>{label}</Label> : null}
      <div className="relative">
        <Input
          ref={inputRef}
          type="file"
          accept={accept}
          className="hidden"
          tabIndex={-1}
          onChange={handleInputChange}
        />

        {showDropZone ? (
          <button
            type="button"
            disabled={uploading}
            onClick={openFilePicker}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={cn(
              "flex w-full flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-4 py-8 text-center transition-colors",
              "border-[#ede7e0] bg-[#fafaf8] text-[#8a817b] hover:border-[#2b2320]/30 hover:bg-[#f7f3ee]",
              isDragging && "border-[#5ecfcf] bg-[#f0fbfb]",
              uploading && "pointer-events-none opacity-70",
            )}
          >
            <div className="flex size-10 items-center justify-center rounded-full bg-white shadow-sm">
              <ImagePlus className="size-5 text-[#2b2320]" aria-hidden />
            </div>
            <div className="space-y-1">
              <p className="text-sm font-medium text-[#2b2320]">點擊選擇圖片</p>
              <p className="text-xs">或拖曳檔案到此</p>
            </div>
            <p className="text-[11px] text-[#8a817b]">{hint}</p>
            {uploading ? <p className="text-xs text-[#2b2320]">上傳中…</p> : null}
          </button>
        ) : null}

        {showCommittedPreview ? (
          <div className="space-y-3">
            <div className="overflow-hidden rounded-lg border border-[#ede7e0] bg-[#fafaf8]">
              <img
                src={previewUrl}
                alt=""
                className="block h-auto max-h-64 w-full object-contain"
              />
            </div>
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
                  onChange?.("");
                  setLocalError(null);
                }}
              >
                <Trash2 className="size-3.5" aria-hidden />
                移除
              </Button>
            </div>
          </div>
        ) : null}

        {showCrop ? (
          <div className="space-y-3">
            <ImageCropEditor
              src={previewUrl}
              aspectRatio={resolvedAspect}
              crop={crop}
              onCropChange={handleCropChange}
              onCropInit={handleCropChange}
              disabled={uploading}
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
                  resetPreview(value || "");
                  if (!value) onChange?.("");
                  setLocalError(null);
                }}
              >
                <Trash2 className="size-3.5" aria-hidden />
                取消選圖
              </Button>
              {pendingUpload ? (
                <Button
                  type="button"
                  size="sm"
                  disabled={uploading}
                  onClick={() => void runUpload()}
                >
                  {uploading ? "上傳中…" : "確認裁切並上傳"}
                </Button>
              ) : null}
            </div>
          </div>
        ) : null}
      </div>
      {!uploadOnSelect && file ? (
        <p className="text-xs text-[#8a817b]">已選擇新圖片，儲存後才會上傳。</p>
      ) : null}
      {file && uploadOnSelect ? (
        <p className="text-xs text-[#8a817b]">
          調整裁切後按「確認裁切並上傳」；直接儲存表單也會先自動上傳這張新圖。
        </p>
      ) : null}
      {localError ? (
        <p className="text-xs text-[#c0392b]" role="alert">
          {localError}
        </p>
      ) : null}
    </div>
  );
}
