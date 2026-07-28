import { useCallback, useEffect, useState } from "react";
import { ImagePlus, Trash2, Upload } from "lucide-react";

import BannerCropModal, { type BannerCropResult } from "@/components/admin/BannerCropModal";
import { useImageUpload } from "@/components/hooks/use-image-upload";
import type { ImageUploadResult } from "@/components/ui/image-upload";
import { cn } from "@/lib/utils";

export type BannerImageUploadCardsProps = {
  initialDesktopUrl?: string;
  initialMobileUrl?: string;
  onDesktopUrlChange: (url: string) => void;
  onMobileUrlChange: (url: string) => void;
  uploadImage: (file: File) => Promise<ImageUploadResult>;
};

type SlotProps = {
  label: string;
  previewUrl: string;
  wrapperClass: string;
  innerClass: string;
  isDragging: boolean;
  disabled?: boolean;
  onPick: () => void;
  onDragOver: (e: React.DragEvent) => void;
  onDragLeave: (e: React.DragEvent) => void;
  onDrop: (e: React.DragEvent) => void;
  onReplace: () => void;
  onRemove: () => void;
};

function UploadSlot({
  label,
  previewUrl,
  wrapperClass,
  innerClass,
  isDragging,
  disabled,
  onPick,
  onDragOver,
  onDragLeave,
  onDrop,
  onReplace,
  onRemove,
}: SlotProps) {
  const hasImg = Boolean(previewUrl);
  return (
    <div className={cn("flex min-h-0 flex-col gap-1.5", wrapperClass)}>
      <p className="shrink-0 text-[10px] font-semibold uppercase tracking-wider text-[#5c5450]">
        {label}
      </p>
      {hasImg ? (
        <div className={cn("group relative min-h-0 flex-1 overflow-hidden rounded-lg", innerClass)}>
          <img src={previewUrl} alt="" className="h-full w-full object-cover" />
          <div className="absolute inset-0 flex items-center justify-center gap-1.5 bg-black/40 opacity-0 transition-opacity group-hover:opacity-100">
            <button
              type="button"
              onClick={onReplace}
              disabled={disabled}
              className="flex items-center gap-1 rounded-md bg-white px-2 py-1 text-[11px] font-medium text-[#2b2320] hover:bg-[#f7f3ee]"
            >
              <Upload className="size-3" aria-hidden />
              更換
            </button>
            <button
              type="button"
              onClick={onRemove}
              disabled={disabled}
              className="flex items-center gap-1 rounded-md bg-white px-2 py-1 text-[11px] font-medium text-[#c0392b] hover:bg-[#fef5f4]"
            >
              <Trash2 className="size-3" aria-hidden />
              移除
            </button>
          </div>
        </div>
      ) : (
        <button
          type="button"
          onClick={onPick}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
          disabled={disabled}
          className={cn(
            "flex w-full min-h-0 flex-1 flex-col items-center justify-center gap-1.5 rounded-lg border-2 border-dashed text-center transition-colors",
            innerClass,
            "border-[#ede7e0] bg-[#fafaf8] hover:border-[#2b2320]/30 hover:bg-[#f7f3ee]",
            isDragging && "border-[#5ecfcf] bg-[#f0fbfb]",
          )}
        >
          <div className="flex size-8 items-center justify-center rounded-full bg-white shadow-sm">
            <ImagePlus className="size-4 text-[#2b2320]" aria-hidden />
          </div>
          <p className="text-[11px] font-medium text-[#2b2320]">點擊選擇</p>
          <p className="text-[10px] text-[#8a817b]">或拖曳至此</p>
        </button>
      )}
    </div>
  );
}

export default function BannerImageUploadCards({
  initialDesktopUrl = "",
  initialMobileUrl = "",
  onDesktopUrlChange,
  onMobileUrlChange,
  uploadImage,
}: BannerImageUploadCardsProps) {
  const [desktopUrl, setDesktopUrl] = useState(initialDesktopUrl);
  const [mobileUrl, setMobileUrl] = useState(initialMobileUrl);
  const [cropOpen, setCropOpen] = useState(false);
  const [pickError, setPickError] = useState("");

  // Same file→dataURL pipeline as 頁面圖片 (useImageUpload).
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
  } = useImageUpload({
    onValidationError: setPickError,
  });

  const startCropFromPick = useCallback(() => {
    setPickError("");
    openFilePicker();
  }, [openFilePicker]);

  // When a new file+dataURL is ready, open crop modal (same pipeline as 頁面圖片).
  useEffect(() => {
    if (file && previewUrl) {
      setCropOpen(true);
      setPickError("");
    }
  }, [file, previewUrl]);

  const handleCropComplete = useCallback(
    (result: BannerCropResult) => {
      setCropOpen(false);
      clearPendingFile();
      setDesktopUrl(result.desktopUrl);
      setMobileUrl(result.mobileUrl);
      onDesktopUrlChange(result.desktopUrl);
      onMobileUrlChange(result.mobileUrl);
    },
    [clearPendingFile, onDesktopUrlChange, onMobileUrlChange],
  );

  const handleCropCancel = useCallback(() => {
    setCropOpen(false);
    clearPendingFile();
  }, [clearPendingFile]);

  const onDesktopDrop = useCallback(
    (e: React.DragEvent) => {
      handleDrop(e);
    },
    [handleDrop],
  );

  const onMobileDrop = useCallback(
    (e: React.DragEvent) => {
      handleDrop(e);
    },
    [handleDrop],
  );

  const clearDesktop = useCallback(() => {
    setDesktopUrl("");
    onDesktopUrlChange("");
  }, [onDesktopUrlChange]);

  const clearMobile = useCallback(() => {
    setMobileUrl("");
    onMobileUrlChange("");
  }, [onMobileUrlChange]);

  return (
    <div className="space-y-2" data-admin-root="">
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={handleInputChange}
      />
      {/* Same-height row; width split 5:5 (PC : phone) */}
      <div className="grid grid-cols-2 items-stretch gap-3">
        <UploadSlot
          label="① 電腦版（16:9）"
          previewUrl={desktopUrl}
          wrapperClass="min-w-0"
          innerClass="aspect-video w-full"
          isDragging={isDragging}
          onPick={startCropFromPick}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={onDesktopDrop}
          onReplace={startCropFromPick}
          onRemove={clearDesktop}
        />
        <UploadSlot
          label="② 手機版（9:16）"
          previewUrl={mobileUrl}
          wrapperClass="min-w-0 h-full"
          innerClass="mx-auto h-full min-h-[7.5rem] w-auto max-w-full aspect-[9/16]"
          isDragging={isDragging}
          onPick={startCropFromPick}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={onMobileDrop}
          onReplace={startCropFromPick}
          onRemove={clearMobile}
        />
      </div>
      <p className="text-[11px] text-[#8a817b]">
        點擊或拖曳圖片至任一欄，依序裁切①電腦版（16:9）與②手機版（9:16）後自動上傳（與頁面圖片相同流程）。
      </p>
      {pickError ? <p className="text-xs text-[#c0392b]">{pickError}</p> : null}
      {cropOpen && file && previewUrl ? (
        <BannerCropModal
          file={file}
          previewUrl={previewUrl}
          uploadImage={uploadImage}
          onComplete={handleCropComplete}
          onCancel={handleCropCancel}
        />
      ) : null}
    </div>
  );
}
