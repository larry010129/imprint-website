import { useEffect, useRef, type ReactNode } from "react";

import CmsSectionImageField from "@/components/admin/CmsSectionImageField";
import PageLinkSelect from "@/components/admin/PageLinkSelect";
import {
  sectionImagePropKey,
  type CmsPage,
  type CmsSection,
} from "@/components/admin/cmsSectionMeta";
import type { ImageUploadResult } from "@/components/ui/image-upload";

type Props = {
  section: CmsSection;
  media: { id: string; url: string; alt?: string }[];
  faqCategories: { id: string; title: string }[];
  disabled?: boolean;
  onChange: (props: Record<string, unknown>) => void;
  onPickMedia: (prop: string) => void;
  uploadImage?: (file: File) => Promise<ImageUploadResult>;
  onImageUploaded?: (url: string, alt: string) => void | Promise<void>;
  onUploadImage?: (file: File) => Promise<ImageUploadResult>;
  focusProp?: string | null;
};

function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <label className="cms-field">
      <span>{label}</span>
      {children}
    </label>
  );
}

export default function CmsSectionPropsForm({
  section,
  faqCategories,
  disabled = false,
  onChange,
  onPickMedia,
  uploadImage,
  onImageUploaded,
  onUploadImage,
  focusProp,
}: Props) {
  const formRef = useRef<HTMLDivElement>(null);
  const p = section.props || {};
  const set = (key: string, value: unknown) => onChange({ ...p, [key]: value });
  const imageProp = sectionImagePropKey(section.type, p);
  const uploader = uploadImage || onUploadImage;
  useEffect(() => {
    if (!focusProp) return;
    const control = Array.from(
      formRef.current?.querySelectorAll<HTMLElement>("[data-cms-prop]") || [],
    ).find((element) => element.dataset.cmsProp === focusProp);
    if (!control) return;
    control.scrollIntoView({ block: "nearest", behavior: "smooth" });
    requestAnimationFrame(() => control.focus());
  }, [focusProp, section.id]);

  if (section.type === "spacer") {
    return (
      <div ref={formRef} className="cms-section-props-form">
      <Field label="高度">
        <select
          data-cms-prop="size"
          value={String(p.size || "md")}
          disabled={disabled}
          onChange={(e) => set("size", e.target.value)}
        >
          <option value="sm">小</option>
          <option value="md">中</option>
          <option value="lg">大</option>
        </select>
      </Field>
      </div>
    );
  }

  if (section.type === "faq_embed") {
    return (
      <div ref={formRef} className="cms-section-props-form">
        <Field label="顯示筆數">
          <input
            data-cms-prop="limit"
            type="number"
            min={1}
            max={24}
            disabled={disabled}
            value={Number(p.limit || 6)}
            onChange={(e) => set("limit", Number(e.target.value) || 6)}
          />
        </Field>
        <Field label="內容範圍">
          <select
            data-cms-prop="mode"
            value={String(p.mode || "teaser")}
            disabled={disabled}
            onChange={(e) => set("mode", e.target.value)}
          >
            <option value="teaser">精選 FAQ</option>
            <option value="all">全部 FAQ</option>
          </select>
        </Field>
        <Field label="指定分類">
          <select
            data-cms-prop="category_id"
            value={String(p.category_id || "")}
            disabled={disabled}
            onChange={(e) => set("category_id", e.target.value)}
          >
            <option value="">不指定分類</option>
            {faqCategories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.title}
              </option>
            ))}
          </select>
        </Field>
        <p className="cms-hint">FAQ 內容來自後台「內容 → FAQ」，此處僅嵌入。</p>
      </div>
    );
  }

  if (section.type === "testimonials_embed") {
    return (
      <div ref={formRef} className="cms-section-props-form">
        <Field label="顯示筆數">
          <input
            data-cms-prop="limit"
            type="number"
            min={1}
            max={24}
            disabled={disabled}
            value={Number(p.limit || 6)}
            onChange={(e) => set("limit", Number(e.target.value) || 6)}
          />
        </Field>
        <p className="cms-hint">見證內容來自後台「內容 → 見證」。</p>
      </div>
    );
  }

  if (section.type === "button_row") {
    const buttons = Array.isArray(p.buttons)
      ? (p.buttons as { label: string; href: string }[])
      : [];
    return (
      <div ref={formRef} className="cms-btn-list cms-section-props-form">
        {buttons.map((btn, index) => (
          <div key={index} className="cms-btn-row">
            <div className="cms-field">
              <label>
                <span>按鈕 {index + 1} 文字</span>
                <input
                  data-cms-prop="buttons"
                  value={btn.label || ""}
                  disabled={disabled}
                  onChange={(event) => {
                    const next = buttons.map((item, itemIndex) =>
                      itemIndex === index
                        ? { ...item, label: event.target.value }
                        : item,
                    );
                    set("buttons", next);
                  }}
                />
              </label>
              <PageLinkSelect
                name={`btn-${index}`}
                label={`按鈕 ${index + 1} 連結`}
                value={btn.href || ""}
                onChange={(href) => {
                  const next = buttons.map((b, i) => (i === index ? { ...b, href } : b));
                  set("buttons", next);
                }}
              />
            </div>
          </div>
        ))}
        <button
          type="button"
          className="btn-sm"
          disabled={disabled}
          onClick={() => set("buttons", [...buttons, { label: "新連結", href: "/" }])}
        >
          新增按鈕
        </button>
      </div>
    );
  }

  return (
    <div ref={formRef} className="cms-section-props-form">
      <p className="cms-hint">可直接在預覽編輯，也可在此精確調整內容。</p>
      {(
        {
          hero: ["eyebrow", "title", "lead", "cta_label", "cta_secondary_label"],
          rich_text: ["title", "body"],
          image_text: ["title", "body", "cta_label"],
          cta_band: ["title", "lead", "cta_label", "cta_secondary_label"],
        } as Record<string, string[]>
      )[section.type]?.map((key) => (
        <Field
          key={key}
          label={
            {
              eyebrow: "眉題",
              title: "標題",
              lead: "說明",
              body: "內文",
              cta_label: "主按鈕文字",
              cta_secondary_label: "次按鈕文字",
            }[key] || key
          }
        >
          {key === "body" || key === "lead" ? (
            <textarea
              data-cms-prop={key}
              rows={key === "body" ? 6 : 3}
              value={String(p[key] || "")}
              disabled={disabled}
              onChange={(event) => set(key, event.target.value)}
            />
          ) : (
            <input
              data-cms-prop={key}
              value={String(p[key] || "")}
              disabled={disabled}
              onChange={(event) => set(key, event.target.value)}
            />
          )}
        </Field>
      ))}
      {section.type === "rich_text" ? (
        <Field label="欄數">
          <select
            data-cms-prop="columns"
            value={String(p.columns || 1)}
            disabled={disabled}
            onChange={(e) => set("columns", Number(e.target.value))}
          >
            <option value={1}>1 欄</option>
            <option value={2}>2 欄</option>
            <option value={3}>3 欄</option>
          </select>
        </Field>
      ) : null}
      {section.type === "image_text" ? (
        <Field label="圖片位置">
          <select
            data-cms-prop="layout"
            value={String(p.layout || "stack")}
            disabled={disabled}
            onChange={(e) => set("layout", e.target.value)}
          >
            <option value="stack">上圖下文（預設）</option>
            <option value="left">圖左文右</option>
            <option value="right">圖右文左</option>
          </select>
        </Field>
      ) : null}
      {imageProp && uploader ? (
        <div data-cms-prop="image_url" tabIndex={-1}>
        <CmsSectionImageField
          label={section.type === "cta_band" ? "CTA 圖片（選填）" : "區塊圖片"}
          imageUrl={String(p.image_url || "")}
          imageAlt={String(p.image_alt || "")}
          disabled={disabled}
          targetW={section.type === "hero" ? 1600 : 1200}
          targetH={section.type === "cta_band" ? 600 : 900}
          uploadImage={uploader}
          onAltChange={(alt) => set("image_alt", alt)}
          onUploaded={async (url) => {
            const alt = String(p.image_alt || "");
            if (onImageUploaded) {
              await onImageUploaded(url, alt);
              return;
            }
            set(imageProp, url);
          }}
        />
        </div>
      ) : imageProp ? (
        <>
          <Field label="圖片 URL">
            <div className="cms-media-row">
              <input
                data-cms-prop="image_url"
                value={String(p.image_url || "")}
                disabled={disabled}
                onChange={(e) => set("image_url", e.target.value)}
              />
              <button
                type="button"
                className="btn-sm"
                disabled={disabled}
                onClick={() => onPickMedia(imageProp)}
              >
                媒體庫
              </button>
            </div>
          </Field>
          <Field label="圖片替代文字">
            <input
              data-cms-prop="image_alt"
              value={String(p.image_alt || "")}
              disabled={disabled}
              onChange={(e) => set("image_alt", e.target.value)}
            />
          </Field>
        </>
      ) : null}
      {imageProp && uploader ? (
        <div className="cms-media-row" style={{ marginTop: 8 }}>
          <button
            type="button"
            className="btn-sm"
            disabled={disabled}
            onClick={() => onPickMedia(imageProp)}
          >
            媒體庫
          </button>
        </div>
      ) : null}
      {section.type === "hero" || section.type === "cta_band" || section.type === "image_text" ? (
        <div className="cms-field">
          <PageLinkSelect
            name="cta_href"
            label="主按鈕連結"
            value={String(p.cta_href || "")}
            onChange={(href) => set("cta_href", href)}
          />
        </div>
      ) : null}
      {section.type === "hero" || section.type === "cta_band" ? (
        <div className="cms-field">
          <PageLinkSelect
            name="cta_secondary_href"
            label="次按鈕連結"
            value={String(p.cta_secondary_href || "")}
            onChange={(href) => set("cta_secondary_href", href)}
          />
        </div>
      ) : null}
    </div>
  );
}

export function CmsPageMetaForm({
  page,
  onSave,
}: {
  page: CmsPage | null;
  onSave: (meta: Partial<CmsPage>) => void;
}) {
  if (!page) return null;
  return (
    <div className="cms-meta">
      <h3>頁面 SEO</h3>
      <label className="cms-field">
        <span>Meta 描述</span>
        <textarea
          rows={3}
          defaultValue={page.meta_description || ""}
          onBlur={(e) => onSave({ meta_description: e.target.value })}
        />
      </label>
      <p className="cms-hint">
        {page.site_route
          ? `固定頁面：${page.site_route}`
          : `公開網址：/p/${page.slug}`}
      </p>
    </div>
  );
}
