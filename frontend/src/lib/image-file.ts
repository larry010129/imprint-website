/** Shared image-picker rules — match admin upload APIs (PNG/JPG/WEBP). */

export const IMAGE_ACCEPT = "image/png,image/jpeg,image/webp";

export const IMAGE_MAX_UPLOAD_BYTES = 1 * 1024 * 1024;

const ALLOWED_MIME = new Set(["image/png", "image/jpeg", "image/webp"]);
const ALLOWED_EXT = new Set([".png", ".jpg", ".jpeg", ".webp"]);

function fileExtension(name: string): string {
  const i = name.lastIndexOf(".");
  return i >= 0 ? name.slice(i).toLowerCase() : "";
}

/** True when MIME (if present) and extension are PNG/JPG/JPEG/WEBP. */
export function isAllowedImageFile(file: File): boolean {
  const ext = fileExtension(file.name || "");
  if (!ALLOWED_EXT.has(ext)) return false;
  if (file.type && !ALLOWED_MIME.has(file.type)) return false;
  return true;
}

/** Error message, or null if file may proceed. */
export function validateImageFile(
  file: File,
  maxBytes = IMAGE_MAX_UPLOAD_BYTES,
): string | null {
  if (!isAllowedImageFile(file)) return "僅支援 PNG / JPG / WEBP";
  if (file.size > maxBytes) {
    if (maxBytes >= IMAGE_MAX_UPLOAD_BYTES * 2) {
      return `來源圖片需小於 ${Math.round(maxBytes / (1024 * 1024))}MB`;
    }
    return "圖片需小於 1MB";
  }
  return null;
}
