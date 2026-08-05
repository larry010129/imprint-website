import { useState } from "react";

import {
  ImageUploadField,
  type ImageUploadResult,
} from "@/components/ui/image-upload";

type Props = {
  label?: string;
  imageUrl: string;
  imageAlt: string;
  disabled?: boolean;
  onAltChange: (alt: string) => void;
  onUploaded: (url: string) => void | Promise<void>;
  uploadImage: (file: File) => Promise<ImageUploadResult>;
  targetW?: number;
  targetH?: number;
};

export default function CmsSectionImageField({
  label = "區塊圖片",
  imageUrl,
  imageAlt,
  disabled = false,
  onAltChange,
  onUploaded,
  uploadImage,
  targetW = 1600,
  targetH = 900,
}: Props) {
  const [error, setError] = useState("");

  return (
    <div className={`cms-section-image-field${disabled ? " is-disabled" : ""}`}>
      <ImageUploadField
        label={label}
        value={imageUrl}
        hint="支援 JPG / PNG / WEBP · 來源 ≤1MB · 上傳後轉 WebP 並壓縮至 ≤500KB（與頁面圖片相同流程）"
        targetW={targetW}
        targetH={targetH}
        onValidationError={setError}
        onUpload={async (file) => {
          if (disabled) return { error: "忙碌中，請稍候" };
          setError("");
          return uploadImage(file);
        }}
        onChange={(url) => {
          void onUploaded(url);
        }}
      />
      <label className="cms-field">
        <span>圖片替代文字</span>
        <input
          value={imageAlt}
          disabled={disabled}
          onChange={(event) => onAltChange(event.target.value)}
        />
      </label>
      {error ? <p className="cms-msg cms-msg--error">{error}</p> : null}
    </div>
  );
}
