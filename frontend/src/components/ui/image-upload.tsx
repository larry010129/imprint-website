import { useCallback, useEffect, useState } from "react";
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
  cropTouched: boolean,
  sourceFile: File | null,
) {
  if (sourceFile && !cropTouched) return sourceFile;
  return cropImageToFile(previewUrl, crop, sourceFile);
}

export function ImageUploadField({
  label,
  hint = "支援 PNG / JPG / WEBP · 1MB 內",
  value = "",
  onChange,
  onUpload,
  uploadOnSelect = true,
  className,
  onValidationError,
  aspectRatio,
  targetW,
  targetH,
  cropEnabled = true,
}: ImageUploadFieldProps) {
  const [uploading, setUploading] = useState(false);
  const [crop, setCrop] = useState<CropPercent>(() =>
    defaultCropPercent(resolveAspectRatio(aspectRatio, targetW, targetH)),
  );
  const [cropTouched, setCropTouched] = useState(false);
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
    clearPendingFile,
    resetPreview,
    setRemotePreview,
    hasPreview,
  } = useImageUpload({
    initialPreviewUrl: value,
    onValidationError,
  });

  useEffect(() => {
    if (!file) setRemotePreview(value);
  }, [file, setRemotePreview, value]);

  useEffect(() => {
    setCropTouched(false);
  }, [file, previewUrl]);

  const handleCropChange = useCallback((next: CropPercent) => {
    setCrop(next);
    setCropTouched(true);
  }, []);

  const handleCropInit = useCallback((next: CropPercent) => {
    setCrop(next);
  }, []);

  const runUpload = useCallback(async () => {
    if (!onUpload || !previewUrl) return;
    setUploading(true);
    try {
      const uploadFile = await resolveUploadFile(
        previewUrl,
        crop,
        cropTouched,
        file,
      );
      const res = await onUpload(uploadFile);
      if (res.error || !res.url) {
        onValidationError?.(resolveError(res.error));
        if (file) clearPendingFile();
        return;
      }
      onChange?.(res.url);
      setRemotePreview(res.url);
      setCropTouched(false);
    } catch (error) {
      onValidationError?.(error instanceof Error ? error.message : "裁切失敗");
    } finally {
      setUploading(false);
    }
  }, [
    clearPendingFile,
    crop,
    cropTouched,
    file,
    onChange,
    onUpload,
    onValidationError,
    previewUrl,
    setRemotePreview,
  ]);

  const showDropZone = !hasPreview || uploading;
  const showCrop = cropEnabled && hasPreview && !uploading;
  const pendingUpload =
    Boolean(onUpload) &&
    uploadOnSelect &&
    (Boolean(file) || (cropTouched && hasPreview));

  return (
    <div className={cn("space-y-2", className)} data-admin-root="">
      {label ? <Label>{label}</Label> : null}
      <div className="relative">
        <Input
          ref={inputRef}
          type="file"
          accept={accept}
          className="hidden"
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

        {showCrop ? (
          <div className="space-y-3">
            <ImageCropEditor
              src={previewUrl}
              aspectRatio={resolvedAspect}
              crop={crop}
              onCropChange={handleCropChange}
              onCropInit={handleCropInit}
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
                  resetPreview("");
                  onChange?.("");
                  setCropTouched(false);
                }}
              >
                <Trash2 className="size-3.5" aria-hidden />
                移除
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
        <p className="text-xs text-[#8a817b]">調整裁切範圍後，請按「確認裁切並上傳」。</p>
      ) : null}
    </div>
  );
}
