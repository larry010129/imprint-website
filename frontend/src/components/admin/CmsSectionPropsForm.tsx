import type { ReactNode } from "react";

import PageLinkSelect from "@/components/admin/PageLinkSelect";
import type { CmsPage, CmsSection } from "@/components/admin/cmsSectionMeta";

type Props = {
  section: CmsSection;
  media: { id: string; url: string; alt?: string }[];
  faqCategories: { id: string; title: string }[];
  onChange: (props: Record<string, unknown>) => void;
  onPickMedia: (prop: string) => void;
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
  onChange,
  onPickMedia,
}: Props) {
  const p = section.props || {};
  const set = (key: string, value: unknown) => onChange({ ...p, [key]: value });

  if (section.type === "spacer") {
    return (
      <Field label="高度">
        <select
          value={String(p.size || "md")}
          onChange={(e) => set("size", e.target.value)}
        >
          <option value="sm">小</option>
          <option value="md">中</option>
          <option value="lg">大</option>
        </select>
      </Field>
    );
  }

  if (section.type === "faq_embed") {
    return (
      <>
        <Field label="顯示筆數">
          <input
            type="number"
            min={1}
            max={24}
            value={Number(p.limit || 6)}
            onChange={(e) => set("limit", Number(e.target.value) || 6)}
          />
        </Field>
        <Field label="內容範圍">
          <select
            value={String(p.mode || "teaser")}
            onChange={(e) => set("mode", e.target.value)}
          >
            <option value="teaser">精選 FAQ</option>
            <option value="all">全部 FAQ</option>
          </select>
        </Field>
        <Field label="指定分類">
          <select
            value={String(p.category_id || "")}
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
      </>
    );
  }

  if (section.type === "testimonials_embed") {
    return (
      <>
        <Field label="顯示筆數">
          <input
            type="number"
            min={1}
            max={24}
            value={Number(p.limit || 6)}
            onChange={(e) => set("limit", Number(e.target.value) || 6)}
          />
        </Field>
        <p className="cms-hint">見證內容來自後台「內容 → 見證」。</p>
      </>
    );
  }

  if (section.type === "button_row") {
    const buttons = Array.isArray(p.buttons) ? (p.buttons as { label: string; href: string }[]) : [];
    return (
      <div className="cms-btn-list">
        {buttons.map((btn, index) => (
          <div key={index} className="cms-btn-row">
            <Field label={`按鈕 ${index + 1} 文字`}>
              <input
                value={btn.label || ""}
                onChange={(e) => {
                  const next = buttons.map((b, i) =>
                    i === index ? { ...b, label: e.target.value } : b
                  );
                  set("buttons", next);
                }}
              />
            </Field>
            <div className="cms-field">
              <PageLinkSelect
                name={`btn-${index}`}
                label="連結"
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
          onClick={() => set("buttons", [...buttons, { label: "新連結", href: "/" }])}
        >
          新增按鈕
        </button>
      </div>
    );
  }

  return (
    <>
      {"eyebrow" in p || section.type === "hero" ? (
        <Field label="眉標">
          <input value={String(p.eyebrow || "")} onChange={(e) => set("eyebrow", e.target.value)} />
        </Field>
      ) : null}
      <Field label="標題">
        <input value={String(p.title || "")} onChange={(e) => set("title", e.target.value)} />
      </Field>
      {"lead" in p || section.type === "hero" || section.type === "cta_band" ? (
        <Field label="引言">
          <textarea
            rows={3}
            value={String(p.lead || "")}
            onChange={(e) => set("lead", e.target.value)}
          />
        </Field>
      ) : null}
      {"body" in p || section.type === "rich_text" || section.type === "image_text" ? (
        <Field label="內文">
          <textarea
            rows={5}
            value={String(p.body || "")}
            onChange={(e) => set("body", e.target.value)}
          />
        </Field>
      ) : null}
      {section.type === "rich_text" ? (
        <Field label="欄數">
          <select
            value={String(p.columns || 1)}
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
            value={String(p.layout || "left")}
            onChange={(e) => set("layout", e.target.value)}
          >
            <option value="left">圖左文右</option>
            <option value="right">圖右文左</option>
          </select>
        </Field>
      ) : null}
      {section.type === "hero" || section.type === "image_text" ? (
        <>
          <Field label="圖片 URL">
            <div className="cms-media-row">
              <input
                value={String(p.image_url || "")}
                onChange={(e) => set("image_url", e.target.value)}
              />
              <button type="button" className="btn-sm" onClick={() => onPickMedia("image_url")}>
                媒體庫
              </button>
            </div>
          </Field>
          <Field label="圖片替代文字">
            <input
              value={String(p.image_alt || "")}
              onChange={(e) => set("image_alt", e.target.value)}
            />
          </Field>
        </>
      ) : null}
      {section.type === "hero" || section.type === "cta_band" || section.type === "image_text" ? (
        <>
          <Field label="主按鈕文字">
            <input
              value={String(p.cta_label || "")}
              onChange={(e) => set("cta_label", e.target.value)}
            />
          </Field>
          <div className="cms-field">
            <PageLinkSelect
              name="cta_href"
              label="主按鈕連結"
              value={String(p.cta_href || "")}
              onChange={(href) => set("cta_href", href)}
            />
          </div>
        </>
      ) : null}
      {section.type === "hero" || section.type === "cta_band" ? (
        <>
          <Field label="次按鈕文字">
            <input
              value={String(p.cta_secondary_label || "")}
              onChange={(e) => set("cta_secondary_label", e.target.value)}
            />
          </Field>
          <div className="cms-field">
            <PageLinkSelect
              name="cta_secondary_href"
              label="次按鈕連結"
              value={String(p.cta_secondary_href || "")}
              onChange={(href) => set("cta_secondary_href", href)}
            />
          </div>
        </>
      ) : null}
    </>
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
      <p className="cms-hint">公開網址：/p/{page.slug}</p>
    </div>
  );
}
