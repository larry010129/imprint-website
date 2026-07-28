export type CropPercent = {
  x: number;
  y: number;
  width: number;
  height: number;
};

export type CropPixels = {
  x: number;
  y: number;
  width: number;
  height: number;
};

export function resolveAspectRatio(
  aspectRatio?: number,
  targetW?: number,
  targetH?: number,
): number | undefined {
  if (aspectRatio && aspectRatio > 0) return aspectRatio;
  if (targetW && targetH && targetW > 0 && targetH > 0) return targetW / targetH;
  return undefined;
}

export function defaultCropPercent(aspect?: number): CropPercent {
  if (!aspect || aspect <= 0) {
    return { x: 0, y: 0, width: 100, height: 100 };
  }
  const imageAspect = 1;
  let width = 100;
  let height = 100;
  if (aspect > imageAspect) {
    height = (100 / aspect) * imageAspect;
  } else {
    width = 100 * aspect;
  }
  return {
    x: (100 - width) / 2,
    y: (100 - height) / 2,
    width,
    height,
  };
}

export function fitCropPercent(imageAspect: number, aspect?: number): CropPercent {
  if (!aspect || aspect <= 0) {
    return { x: 0, y: 0, width: 100, height: 100 };
  }
  let width = 100;
  let height = (width / aspect) * imageAspect;
  if (height > 100) {
    height = 100;
    width = (height * aspect) / imageAspect;
  }
  return {
    x: (100 - width) / 2,
    y: (100 - height) / 2,
    width,
    height,
  };
}

export function percentToPixels(
  crop: CropPercent,
  naturalWidth: number,
  naturalHeight: number,
): CropPixels {
  return {
    x: Math.round((crop.x / 100) * naturalWidth),
    y: Math.round((crop.y / 100) * naturalHeight),
    width: Math.round((crop.width / 100) * naturalWidth),
    height: Math.round((crop.height / 100) * naturalHeight),
  };
}

export function isFullCrop(crop: CropPercent) {
  return (
    crop.x <= 0.5 &&
    crop.y <= 0.5 &&
    crop.width >= 99.5 &&
    crop.height >= 99.5
  );
}

function needsCrossOrigin(src: string): boolean {
  if (src.startsWith("blob:") || src.startsWith("data:")) return false;
  if (src.startsWith("/")) return false;
  try {
    const url = new URL(src, window.location.origin);
    return url.origin !== window.location.origin;
  } catch {
    return false;
  }
}

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const useCrossOrigin = needsCrossOrigin(src);

    const finish = () => resolve(img);
    const fail = () => {
      if (useCrossOrigin) {
        img.removeAttribute("crossorigin");
        img.onload = finish;
        img.onerror = () => reject(new Error("無法載入圖片"));
        img.src = src;
        return;
      }
      reject(new Error("無法載入圖片"));
    };

    if (useCrossOrigin) {
      img.crossOrigin = "anonymous";
    }
    img.onload = finish;
    img.onerror = fail;
    img.src = src;
  });
}

export type CropToFileOptions = {
  maxWidth?: number;
  mimeType?: string;
  quality?: number;
};

export async function cropImageToBlob(
  src: string,
  crop: CropPercent,
  mimeType: string,
  quality = 0.92,
  maxWidth?: number,
): Promise<Blob> {
  const img = await loadImage(src);
  if (!img.naturalWidth || !img.naturalHeight) {
    throw new Error("無法載入圖片");
  }
  const pixels = percentToPixels(crop, img.naturalWidth, img.naturalHeight);
  if (pixels.width < 1 || pixels.height < 1) {
    throw new Error("裁切範圍無效");
  }
  let outW = Math.max(1, pixels.width);
  let outH = Math.max(1, pixels.height);
  if (maxWidth && outW > maxWidth) {
    const scale = maxWidth / outW;
    outW = maxWidth;
    outH = Math.max(1, Math.round(outH * scale));
  }
  const canvas = document.createElement("canvas");
  canvas.width = outW;
  canvas.height = outH;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("無法建立裁切畫布");
  ctx.drawImage(
    img,
    pixels.x,
    pixels.y,
    pixels.width,
    pixels.height,
    0,
    0,
    outW,
    outH,
  );
  const type = mimeType || "image/jpeg";
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (!blob || blob.size < 1) {
          reject(new Error("裁切失敗"));
          return;
        }
        resolve(blob);
      },
      type,
      quality,
    );
  });
}

export async function cropImageToFile(
  src: string,
  crop: CropPercent,
  sourceFile?: File | null,
  options?: CropToFileOptions,
): Promise<File> {
  if (!src) throw new Error("請選擇圖片");
  const mime = options?.mimeType || sourceFile?.type || "image/jpeg";
  const ext =
    mime === "image/png" ? "png" : mime === "image/webp" ? "webp" : "jpg";
  const baseName = sourceFile?.name?.replace(/\.[^.]+$/, "") || "cropped";
  const blob = await cropImageToBlob(
    src,
    crop,
    mime,
    options?.quality ?? 0.9,
    options?.maxWidth,
  );
  return new File([blob], `${baseName}-cropped.${ext}`, { type: mime });
}
