import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ChangeEvent,
  type DragEvent,
} from "react";

const DEFAULT_ACCEPT = "image/png,image/jpeg,image/webp";
// Selected sources are resized and compressed before upload.
const DEFAULT_MAX_BYTES = 20 * 1024 * 1024;

function isAcceptedType(file: File, accept: string) {
  const tokens = accept.split(",").map((t) => t.trim()).filter(Boolean);
  if (tokens.length === 0) return true;
  return tokens.some((token) => {
    if (token.endsWith("/*")) {
      return file.type.startsWith(token.slice(0, -1));
    }
    return file.type === token;
  });
}

export type UseImageUploadOptions = {
  accept?: string;
  maxSizeBytes?: number;
  initialPreviewUrl?: string;
  onValidationError?: (message: string) => void;
};

export function useImageUpload({
  accept = DEFAULT_ACCEPT,
  maxSizeBytes = DEFAULT_MAX_BYTES,
  initialPreviewUrl = "",
  onValidationError,
}: UseImageUploadOptions = {}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const objectUrlRef = useRef<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState(initialPreviewUrl);
  const [isDragging, setIsDragging] = useState(false);

  const cleanupObjectUrl = useCallback(() => {
    if (objectUrlRef.current) {
      URL.revokeObjectURL(objectUrlRef.current);
      objectUrlRef.current = null;
    }
  }, []);

  useEffect(() => {
    setPreviewUrl(initialPreviewUrl);
  }, [initialPreviewUrl]);

  useEffect(() => () => cleanupObjectUrl(), [cleanupObjectUrl]);

  const reportError = useCallback(
    (message: string) => {
      onValidationError?.(message);
    },
    [onValidationError],
  );

  const assignFile = useCallback(
    (next: File | null) => {
      cleanupObjectUrl();
      if (!next) {
        setFile(null);
        setPreviewUrl(initialPreviewUrl);
        return;
      }
      if (!isAcceptedType(next, accept)) {
        reportError("僅支援 PNG / JPG / WEBP");
        return;
      }
      if (next.size > maxSizeBytes) {
        reportError("來源圖片需小於 20MB");
        return;
      }
      const objectUrl = URL.createObjectURL(next);
      objectUrlRef.current = objectUrl;
      setFile(next);
      setPreviewUrl(objectUrl);
    },
    [accept, cleanupObjectUrl, initialPreviewUrl, maxSizeBytes, reportError],
  );

  const openFilePicker = useCallback(() => {
    inputRef.current?.click();
  }, []);

  const handleInputChange = useCallback(
    (event: ChangeEvent<HTMLInputElement>) => {
      const picked = event.target.files?.[0];
      if (picked) assignFile(picked);
      event.target.value = "";
    },
    [assignFile],
  );

  const handleDragOver = useCallback((event: DragEvent) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((event: DragEvent) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (event: DragEvent) => {
      event.preventDefault();
      event.stopPropagation();
      setIsDragging(false);
      const dropped = event.dataTransfer.files?.[0];
      if (dropped) assignFile(dropped);
    },
    [assignFile],
  );

  const clearPendingFile = useCallback(() => {
    assignFile(null);
  }, [assignFile]);

  const setRemotePreview = useCallback(
    (url: string) => {
      cleanupObjectUrl();
      setFile(null);
      setPreviewUrl(url);
    },
    [cleanupObjectUrl],
  );

  const resetPreview = useCallback(
    (url = "") => {
      cleanupObjectUrl();
      setFile(null);
      setPreviewUrl(url);
    },
    [cleanupObjectUrl],
  );

  return {
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
    setRemotePreview,
    resetPreview,
    hasPreview: Boolean(previewUrl),
  };
}
