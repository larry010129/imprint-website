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
  type CropPercent,
} from "@/lib/crop-image";
import type { ImageUploadResult } from "@/components/ui/image-upload";

/** Desktop hero: viewport is ~16:9 at full width (92vh, max 900px) */
const DESKTOP_ASPECT = 16 / 9;
/** Mobile hero: viewport is portrait 9:16 at ≤860px (78vh, phone ~390×844) */
const MOBILE_ASPECT = 9 / 16;

export type BannerCropResult = {
  desktopUrl: string;
  mobileUrl: string;
};

export type BannerCropModalProps = {
  previewUrl: string;
  file: File;
  onComplete: (result: BannerCropResult) => void;
  onCancel: () => void;
  uploadImage: (file: File) => Promise<ImageUploadResult>;
};

function resolveError(error: ImageUploadResult["error"]): string {
  if (!error) return "上傳失敗";
  if (typeof error === "string") return error;
  return error.message || "上傳失敗";
}

/** Same idea as 頁面圖片: always build a File from the data-URL preview + crop. */
async function resolveUploadFile(
  previewUrl: string,
  crop: CropPercent,
  sourceFile: File | null,
  maxWidth: number,
): Promise<File> {
  if (!previewUrl) throw new Error("請選擇圖片");
  return cropImageToFile(previewUrl, crop, sourceFile, {
    maxWidth,
    mimeType: "image/jpeg",
    quality: 0.88,
  });
}

export default function BannerCropModal({
  previewUrl,
  file,
  onComplete,
  onCancel,
  uploadImage,
}: BannerCropModalProps) {
  const [step, setStep] = useState<1 | 2>(1);
  const [desktopCrop, setDesktopCrop] = useState<CropPercent>(() =>
    defaultCropPercent(DESKTOP_ASPECT),
  );
  const [mobileCrop, setMobileCrop] = useState<CropPercent>(() =>
    defaultCropPercent(MOBILE_ASPECT),
  );
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  const handleDesktopCropChange = useCallback((c: CropPercent) => {
    setDesktopCrop(c);
  }, []);

  const handleMobileCropChange = useCallback((c: CropPercent) => {
    setMobileCrop(c);
  }, []);

  const handleNext = useCallback(() => {
    setStep(2);
    setError("");
  }, []);

  const handleBack = useCallback(() => {
    setStep(1);
    setError("");
  }, []);

  const handleConfirm = useCallback(async () => {
    if (!previewUrl) {
      setError("請選擇圖片");
      return;
    }
    setUploading(true);
    setError("");
    try {
      // Match 頁面圖片: crop from data-URL preview, then upload File with bytes.
      const desktopFile = await resolveUploadFile(
        previewUrl,
        desktopCrop,
        file,
        2400,
      );
      if (!desktopFile.size) {
        setError("電腦版裁切結果是空的，請重試");
        return;
      }
      const desktopRes = await uploadImage(desktopFile);
      if (desktopRes.error || !desktopRes.url) {
        setError(resolveError(desktopRes.error));
        return;
      }

      const mobileFile = await resolveUploadFile(
        previewUrl,
        mobileCrop,
        file,
        1080,
      );
      if (!mobileFile.size) {
        setError("手機版裁切結果是空的，請重試");
        return;
      }
      const mobileRes = await uploadImage(mobileFile);
      if (mobileRes.error || !mobileRes.url) {
        setError(resolveError(mobileRes.error));
        return;
      }

      onComplete({ desktopUrl: desktopRes.url, mobileUrl: mobileRes.url });
    } catch (e) {
      setError(e instanceof Error ? e.message : "裁切失敗");
    } finally {
      setUploading(false);
    }
  }, [desktopCrop, file, mobileCrop, onComplete, previewUrl, uploadImage]);

  const stepLabel = step === 1 ? "電腦版裁切" : "手機版裁切";
  const stepHint =
    step === 1
      ? "比例 16:9｜電腦、大螢幕（橫式）"
      : "比例 9:16｜手機直式，置中裁切";

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
          <DialogTitle>
            裁切圖片 · {step}/2 {stepLabel}
          </DialogTitle>
          <p className="text-sm text-[#8a817b]">{stepHint}</p>
        </DialogHeader>

        <div className="space-y-3">
          <div className="flex items-center gap-2 text-xs">
            <span
              className={
                step === 1 ? "font-semibold text-[#2b2320]" : "text-[#8a817b]"
              }
            >
              ① 電腦版裁切
            </span>
            <span className="text-[#c9c0b8]" aria-hidden>
              →
            </span>
            <span
              className={
                step === 2 ? "font-semibold text-[#2b2320]" : "text-[#8a817b]"
              }
            >
              ② 手機版裁切
            </span>
          </div>

          {step === 1 && (
            <ImageCropEditor
              src={previewUrl}
              aspectRatio={DESKTOP_ASPECT}
              crop={desktopCrop}
              onCropChange={handleDesktopCropChange}
              onCropInit={setDesktopCrop}
              disabled={uploading}
            />
          )}

          {step === 2 && (
            <ImageCropEditor
              src={previewUrl}
              aspectRatio={MOBILE_ASPECT}
              crop={mobileCrop}
              onCropChange={handleMobileCropChange}
              onCropInit={setMobileCrop}
              disabled={uploading}
            />
          )}

          {error ? <p className="text-xs text-[#c0392b]">{error}</p> : null}
        </div>

        <DialogFooter className="gap-2 sm:gap-3">
          {step === 1 ? (
            <>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={onCancel}
                disabled={uploading}
              >
                取消
              </Button>
              <Button
                type="button"
                size="sm"
                onClick={handleNext}
                disabled={uploading || !previewUrl}
              >
                下一步：手機版裁切 →
              </Button>
            </>
          ) : (
            <>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleBack}
                disabled={uploading}
              >
                ← 上一步
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={onCancel}
                disabled={uploading}
              >
                取消
              </Button>
              <Button
                type="button"
                size="sm"
                disabled={uploading || !previewUrl}
                onClick={() => void handleConfirm()}
              >
                {uploading ? "上傳中…" : "確認儲存"}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
