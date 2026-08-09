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
  maxBytes?: number;
  mimeType?: string;
  quality?: number;
};

function canvasToBlob(
  canvas: HTMLCanvasElement,
  mimeType: string,
  quality: number,
): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (!blob || blob.size < 1) {
          reject(new Error("圖片處理失敗"));
          return;
        }
        resolve(blob);
      },
      mimeType,
      quality,
    );
  });
}

export async function cropImageToBlob(
  src: string,
  crop: CropPercent,
  mimeType: string,
  quality = 0.92,
  maxWidth?: number,
  maxBytes?: number,
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
  let canvas = document.createElement("canvas");
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
  const type = mimeType || "image/webp";
  let encodeQuality = quality;
  let blob = await canvasToBlob(canvas, type, encodeQuality);
  while (maxBytes && blob.size > maxBytes && encodeQuality > 0.48) {
    encodeQuality = Math.max(0.48, encodeQuality - 0.08);
    blob = await canvasToBlob(canvas, type, encodeQuality);
  }
  while (maxBytes && blob.size > maxBytes && canvas.width > 640) {
    const smaller = document.createElement("canvas");
    smaller.width = Math.max(640, Math.round(canvas.width * 0.84));
    smaller.height = Math.max(1, Math.round(canvas.height * (smaller.width / canvas.width)));
    const smallerContext = smaller.getContext("2d");
    if (!smallerContext) throw new Error("無法建立圖片處理畫布");
    smallerContext.drawImage(canvas, 0, 0, smaller.width, smaller.height);
    canvas = smaller;
    blob = await canvasToBlob(canvas, type, encodeQuality);
  }
  if (maxBytes && blob.size > maxBytes) {
    throw new Error("圖片最佳化後仍超過 1MB，請選擇較小的來源圖片");
  }
  return blob;
}

export async function cropImageToFile(
  src: string,
  crop: CropPercent,
  sourceFile?: File | null,
  options?: CropToFileOptions,
): Promise<File> {
  if (!src) throw new Error("請選擇圖片");
  const mime = options?.mimeType || "image/webp";
  const ext =
    mime === "image/png" ? "png" : mime === "image/webp" ? "webp" : "jpg";
  // Keep original upload basename (stem); only normalize extension to output mime.
  const sourceName = sourceFile?.name || "";
  const baseName = sourceName.replace(/\.[^.]+$/, "") || "image";
  const blob = await cropImageToBlob(
    src,
    crop,
    mime,
    options?.quality ?? 0.9,
    options?.maxWidth,
    options?.maxBytes,
  );
  return new File([blob], `${baseName}.${ext}`, { type: mime });
}
