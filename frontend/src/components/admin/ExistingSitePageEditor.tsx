import { useEffect, useMemo, useState } from "react";

import PageLinkSelect from "@/components/admin/PageLinkSelect";
import JournalPostsEditor, {
  type JournalPostsApi,
} from "@/components/admin/JournalPostsEditor";
import {
  type CmsPage,
  type CmsSection,
  type CmsSectionType,
} from "@/components/admin/cmsSectionMeta";
import { useToast } from "@/components/ui/toast-1";

export type SitePage = {
  route: string;
  title: string;
  content_tab: "page" | "faq" | "testimonials";
};

export type CopySlot = {
  page_key: string;
  slot_key: string;
  kind: "text" | "button";
  label: string;
  text_value: string;
  href: string;
  default_text: string;
  default_href: string;
  is_published: boolean;
};

export type ExistingSitePageEditorProps = {
  page: SitePage;
  api: {
    getCopySlots: (pageKey?: string) => Promise<{
      slots?: CopySlot[];
      pages?: SitePage[];
      error?: string;
    }>;
    updateCopySlot: (fields: Record<string, unknown>) => Promise<{
      slot?: CopySlot;
      error?: string;
    }>;
    getCmsSitePage: (route: string) => Promise<{
      page?: CmsPage;
      sections?: CmsSection[];
      error?: string;
    }>;
    updateSection: (fields: Record<string, unknown>) => Promise<{
      section?: CmsSection;
      error?: string;
    }>;
  } & JournalPostsApi;
  onBack: () => void;
};

type SaveState = "idle" | "saving" | "saved" | "error";
type SectionDrafts = Record<string, CmsSection>;
type SlotDrafts = Record<string, CopySlot>;

const TEXT_FIELDS: Partial<Record<CmsSectionType, string[]>> = {
  hero: ["eyebrow", "title", "lead"],
  rich_text: ["title", "body"],
  image_text: ["title", "body"],
  cta_band: ["title", "lead"],
};

const SECTION_LABELS: Partial<Record<CmsSectionType, string>> = {
  hero: "主視覺文字",
  rich_text: "文字內容",
  image_text: "圖文內容",
  cta_band: "行動呼籲",
  button_row: "按鈕列",
  faq_embed: "FAQ 區塊",
  testimonials_embed: "見證區塊",
  spacer: "間距區塊",
  freeform: "自由排版區塊",
};

const FIELD_LABELS: Record<string, string> = {
  eyebrow: "眉標",
  title: "標題",
  lead: "說明文字",
  body: "內文",
  button_name: "按鈕名稱",
  content: "內容",
};

const MAX_BUTTONS = 8;

function cloneSection(section: CmsSection): CmsSection {
  return {
    ...section,
    props: JSON.parse(JSON.stringify(section.props || {})) as Record<string, unknown>,
  };
}

function cloneSlot(slot: CopySlot): CopySlot {
  return { ...slot };
}

function routeMatches(left: string, right: string): boolean {
  const normalize = (value: string) => {
    const clean = String(value || "").trim().replace(/\/$/, "");
    return clean.endsWith(".html") ? clean.slice(0, -5) : clean;
  };
  return normalize(left) === normalize(right);
}

function sectionLabel(section: CmsSection, index: number): string {
  return `${SECTION_LABELS[section.type] || section.type} ${index + 1}`;
}

function sectionHasFields(section: CmsSection): boolean {
  return Boolean(TEXT_FIELDS[section.type]?.length || section.type === "button_row" ||
    section.type === "hero" || section.type === "image_text" || section.type === "cta_band");
}

function TextField({
  name,
  value,
  multiline,
  onChange,
}: {
  name: string;
  value: string;
  multiline?: boolean;
  onChange: (value: string) => void;
}) {
  return (
    <label className="cms-field">
      <span>{FIELD_LABELS[name] || name}</span>
      {multiline ? (
        <textarea rows={name === "body" ? 6 : 3} value={value} onChange={(event) => onChange(event.target.value)} />
      ) : (
        <input type="text" value={value} onChange={(event) => onChange(event.target.value)} />
      )}
    </label>
  );
}

function ButtonFields({
  name,
  label,
  href,
  onChange,
  onRemove,
}: {
  name: string;
  label: string;
  href: string;
  onChange: (field: "label" | "href", value: string) => void;
  onRemove?: () => void;
}) {
  return (
    <div className="cms-button-editor">
      <div className="cms-button-editor__header">
        <strong>{name}</strong>
        {onRemove ? (
          <button type="button" className="btn-sm" onClick={onRemove}>
            移除按鈕
          </button>
        ) : null}
      </div>
      <TextField name="button_name" value={label} onChange={(value) => onChange("label", value)} />
      <PageLinkSelect
        name={`button-link-${name}`}
        label="按鈕連結"
        value={href}
        onChange={(value) => onChange("href", value)}
      />
    </div>
  );
}

function SectionForm({
  section,
  index,
  onChange,
}: {
  section: CmsSection;
  index: number;
  onChange: (props: Record<string, unknown>) => void;
}) {
  const props = section.props || {};
  const textFields = TEXT_FIELDS[section.type] || [];
  const buttons = Array.isArray(props.buttons)
    ? (props.buttons as { label?: string; href?: string }[])
    : [];

  const updateButton = (buttonIndex: number, field: "label" | "href", value: string) => {
    onChange({
      ...props,
      buttons: buttons.map((button, index) =>
        index === buttonIndex ? { ...button, [field]: value } : button,
      ),
    });
  };

  const updateCta = (field: string, value: string) => onChange({ ...props, [field]: value });

  return (
    <section className="cms-copy-card" data-cms-fixed-section={section.type}>
      <div className="cms-copy-card__header">
        <h3>{sectionLabel(section, index)}</h3>
        <span className="cms-hint">固定版型</span>
      </div>

      {textFields.map((field) => (
        <TextField
          key={field}
          name={field}
          value={String(props[field] || "")}
          multiline={field === "body" || field === "lead"}
          onChange={(value) => onChange({ ...props, [field]: value })}
        />
      ))}

      {section.type === "hero" || section.type === "cta_band" || section.type === "image_text" ? (
        <div className="cms-button-list">
          <ButtonFields
            name="主要按鈕"
            label={String(props.cta_label || "")}
            href={String(props.cta_href || "")}
            onChange={updateCtaField(updateCta, "cta")}
          />
          {section.type !== "image_text" ? (
            <ButtonFields
              name="次要按鈕（可選）"
              label={String(props.cta_secondary_label || "")}
              href={String(props.cta_secondary_href || "")}
              onChange={updateCtaField(updateCta, "secondary")}
            />
          ) : null}
        </div>
      ) : null}

      {section.type === "button_row" ? (
        <div className="cms-button-list">
          {buttons.map((button, buttonIndex) => (
            <ButtonFields
              key={`${section.id}-button-${buttonIndex}`}
              name={`按鈕 ${buttonIndex + 1}`}
              label={String(button.label || "")}
              href={String(button.href || "")}
              onChange={(field, value) => updateButton(buttonIndex, field, value)}
              onRemove={() => onChange({ ...props, buttons: buttons.filter((_, i) => i !== buttonIndex) })}
            />
          ))}
          <button
            type="button"
            className="btn-sm"
            disabled={buttons.length >= MAX_BUTTONS}
            onClick={() => onChange({ ...props, buttons: [...buttons, { label: "", href: "/" }] })}
          >
            新增按鈕
          </button>
          {!buttons.length ? <p className="cms-hint">目前沒有按鈕。</p> : null}
        </div>
      ) : null}
    </section>
  );
}

function updateCtaField(
  update: (field: string, value: string) => void,
  kind: "cta" | "secondary",
) {
  return (field: "label" | "href", value: string) => {
    const prefix = kind === "secondary" ? "cta_secondary_" : "cta_";
    update(`${prefix}${field === "label" ? "label" : "href"}`, value);
  };
}

export default function ExistingSitePageEditor({
  page,
  api,
  onBack,
}: ExistingSitePageEditorProps) {
  const { showToast } = useToast();
  const [slots, setSlots] = useState<CopySlot[]>([]);
  const [sections, setSections] = useState<CmsSection[]>([]);
  const [slotDrafts, setSlotDrafts] = useState<SlotDrafts>({});
  const [sectionDrafts, setSectionDrafts] = useState<SectionDrafts>({});
  const [slotStates, setSlotStates] = useState<Record<string, SaveState>>({});
  const [sectionStates, setSectionStates] = useState<Record<string, SaveState>>({});
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const pageSlots = useMemo(
    () => slots.filter((slot) => routeMatches(slot.page_key, page.route)),
    [page.route, slots],
  );
  const editableSections = useMemo(
    () => sections.filter(sectionHasFields),
    [sections],
  );

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setLoadError(null);
    void Promise.all([api.getCopySlots(page.route), api.getCmsSitePage(page.route)])
      .then(([slotResult, pageResult]) => {
        if (cancelled) return;
        const error = slotResult.error || pageResult.error;
        if (error) {
          setLoadError(String(error));
          return;
        }
        const nextSlots = (slotResult.slots || []).filter((slot) => routeMatches(slot.page_key, page.route));
        const nextSections = pageResult.sections || pageResult.page?.sections || [];
        setSlots(nextSlots);
        setSections(nextSections);
        setSlotDrafts(Object.fromEntries(nextSlots.map((slot) => [slot.slot_key, cloneSlot(slot)])));
        setSectionDrafts(Object.fromEntries(nextSections.map((section) => [section.id, cloneSection(section)])));
        setSlotStates({});
        setSectionStates({});
      })
      .catch((error) => {
        if (!cancelled) setLoadError(String(error));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [api, page.route]);

  const updateSlotDraft = (slot: CopySlot, field: "text_value" | "href", value: string) => {
    setSlotDrafts((current) => ({
      ...current,
      [slot.slot_key]: { ...current[slot.slot_key], [field]: value, is_published: true },
    }));
    setSlotStates((current) => ({ ...current, [slot.slot_key]: "idle" }));
  };

  const saveSlot = async (slot: CopySlot) => {
    const draft = slotDrafts[slot.slot_key] || slot;
    setSlotStates((current) => ({ ...current, [slot.slot_key]: "saving" }));
    try {
      const result = await api.updateCopySlot({
        pageKey: draft.page_key,
        slotKey: draft.slot_key,
        textValue: draft.text_value,
        href: draft.kind === "button" ? draft.href : "",
        isPublished: true,
      });
      if (result.error || !result.slot) throw new Error(String(result.error || "儲存失敗"));
      setSlots((current) => current.map((item) => item.slot_key === slot.slot_key ? result.slot! : item));
      setSlotDrafts((current) => ({ ...current, [slot.slot_key]: cloneSlot(result.slot!) }));
      setSlotStates((current) => ({ ...current, [slot.slot_key]: "saved" }));
      showToast("內容已儲存", "success", "top-right");
    } catch (error) {
      setSlotStates((current) => ({ ...current, [slot.slot_key]: "error" }));
      showToast(String(error), "error", "top-right");
    }
  };

  const resetSlot = (slot: CopySlot) => {
    setSlotDrafts((current) => ({ ...current, [slot.slot_key]: cloneSlot(slot) }));
    setSlotStates((current) => ({ ...current, [slot.slot_key]: "idle" }));
  };

  const updateSectionDraft = (section: CmsSection, props: Record<string, unknown>) => {
    setSectionDrafts((current) => ({
      ...current,
      [section.id]: { ...(current[section.id] || section), props },
    }));
    setSectionStates((current) => ({ ...current, [section.id]: "idle" }));
  };

  const saveSection = async (section: CmsSection) => {
    const draft = sectionDrafts[section.id] || section;
    setSectionStates((current) => ({ ...current, [section.id]: "saving" }));
    try {
      const result = await api.updateSection({ id: draft.id, props: draft.props });
      if (result.error || !result.section) throw new Error(String(result.error || "儲存失敗"));
      setSections((current) => current.map((item) => item.id === section.id ? result.section! : item));
      setSectionDrafts((current) => ({ ...current, [section.id]: cloneSection(result.section!) }));
      setSectionStates((current) => ({ ...current, [section.id]: "saved" }));
      showToast("區塊已儲存", "success", "top-right");
    } catch (error) {
      setSectionStates((current) => ({ ...current, [section.id]: "error" }));
      showToast(String(error), "error", "top-right");
    }
  };

  const resetSection = (section: CmsSection) => {
    setSectionDrafts((current) => ({ ...current, [section.id]: cloneSection(section) }));
    setSectionStates((current) => ({ ...current, [section.id]: "idle" }));
  };

  const stateLabel = (state: SaveState | undefined) =>
    state === "saving" ? "儲存中…" : state === "saved" ? "已儲存" : state === "error" ? "儲存失敗" : "";
  const isJournal = page.route === "/journal";

  return (
    <div className="cms-editor cms-site-editor cms-fixed-content-editor">
      <div className="cms-editor__top">
        <button type="button" className="btn-sm" onClick={onBack}>返回頁面列表</button>
        <strong>{page.title}</strong>
        <span className="cms-editor__site-route">{page.route}</span>
      </div>
      <p className="cms-inline-instruction">
        這裡只編輯文字、按鈕名稱與頁面連結。頁面版型、圖片與區塊順序由系統固定。
      </p>

      {isJournal ? <JournalPostsEditor api={api} /> : <>
        {loading ? <p className="cms-hint">載入內容中…</p> : null}
        {loadError ? <p className="cms-msg cms-msg--error">{loadError}</p> : null}

        {!loading && !loadError ? (
        <div className="cms-fixed-content-list">
          {pageSlots.length ? (
            <section className="cms-copy-group">
              <h3 className="cms-copy-group__title">既有頁面文字與按鈕</h3>
              {pageSlots.map((slot) => {
                const draft = slotDrafts[slot.slot_key] || slot;
                const text = draft.text_value || (!draft.is_published ? draft.default_text : "") || draft.default_text;
                const href = draft.href || (!draft.is_published ? draft.default_href : "") || draft.default_href;
                return (
                  <article className="cms-copy-card" key={slot.slot_key}>
                    <h4>{slot.label || slot.slot_key}</h4>
                    {slot.kind === "button" ? (
                      <>
                        <TextField name="button_name" value={text} onChange={(value) => updateSlotDraft(slot, "text_value", value)} />
                        <PageLinkSelect
                          name={`legacy-link-${slot.slot_key}`}
                          label="按鈕連結"
                          value={href}
                          onChange={(value) => updateSlotDraft(slot, "href", value)}
                        />
                      </>
                    ) : (
                      <TextField name="content" value={text} multiline onChange={(value) => updateSlotDraft(slot, "text_value", value)} />
                    )}
                    <div className="cms-copy-card__actions">
                      <button type="button" className="btn-sm" onClick={() => resetSlot(slot)}>還原</button>
                      <button type="button" className="btn-sm btn-primary" onClick={() => void saveSlot(slot)} disabled={slotStates[slot.slot_key] === "saving"}>儲存</button>
                      <span className={`cms-msg cms-msg--${slotStates[slot.slot_key] || "idle"}`}>{stateLabel(slotStates[slot.slot_key])}</span>
                    </div>
                  </article>
                );
              })}
            </section>
          ) : null}

          {editableSections.length ? (
            <section className="cms-copy-group">
              <h3 className="cms-copy-group__title">固定 CMS 區塊</h3>
              {editableSections.map((section, index) => {
                const draft = sectionDrafts[section.id] || section;
                return (
                  <div key={section.id}>
                    <SectionForm section={draft} index={index} onChange={(props) => updateSectionDraft(section, props)} />
                    <div className="cms-copy-card__actions">
                      <button type="button" className="btn-sm" onClick={() => resetSection(section)}>還原</button>
                      <button type="button" className="btn-sm btn-primary" onClick={() => void saveSection(section)} disabled={sectionStates[section.id] === "saving"}>儲存</button>
                      <span className={`cms-msg cms-msg--${sectionStates[section.id] || "idle"}`}>{stateLabel(sectionStates[section.id])}</span>
                    </div>
                  </div>
                );
              })}
            </section>
          ) : null}

          {!pageSlots.length && !editableSections.length ? (
            <p className="cms-hint">此頁面目前沒有可編輯的文字或按鈕。</p>
          ) : null}
        </div>
        ) : null}
      </>}
    </div>
  );
}
