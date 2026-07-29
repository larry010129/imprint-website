import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";

import {
  CMS_CANVAS_DROP_ID,
  CmsCanvasDropTarget,
  CmsPaletteButton,
  CmsSortableRow,
} from "@/components/admin/CmsEditorDnd";
import CmsMediaModal from "@/components/admin/CmsMediaModal";
import CmsSectionPropsForm, {
  CmsPageMetaForm,
} from "@/components/admin/CmsSectionPropsForm";
import {
  SECTION_PALETTE,
  sectionLabel,
  type CmsPage,
  type CmsSection,
  type CmsSectionType,
} from "@/components/admin/cmsSectionMeta";
import useCmsSectionSaves from "@/components/admin/useCmsSectionSaves";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/components/ui/toast-1";

export type CmsPageEditorProps = {
  pageId: string | null;
  api: {
    getPage: (id: string) => Promise<{ page?: CmsPage; error?: string }>;
    updatePage: (fields: Record<string, unknown>) => Promise<{ page?: CmsPage; error?: string }>;
    pageAction: (id: string, action: string) => Promise<{ ok?: boolean; error?: string }>;
    createSection: (
      pageId: string,
      body: { type: string }
    ) => Promise<{ section?: CmsSection; error?: string }>;
    updateSection: (fields: Record<string, unknown>) => Promise<{ section?: CmsSection; error?: string }>;
    sectionAction: (id: string, action: string) => Promise<{ ok?: boolean; error?: string }>;
    reorderSections: (
      pageId: string,
      sectionIds: string[]
    ) => Promise<{ sections?: CmsSection[]; error?: string }>;
    getMedia: () => Promise<{ media?: { id: string; url: string; alt?: string }[]; error?: string }>;
    getFaqCategories: () => Promise<{
      categories?: { id: string; title: string }[];
      error?: string;
    }>;
    uploadMedia: (file: File) => Promise<{ media?: { id: string; url: string }; url?: string; error?: string }>;
    deleteMedia: (id: string) => Promise<{ ok?: boolean; error?: string }>;
  };
  onBack: () => void;
  onDeleted?: () => void;
};

export default function CmsPageEditor({ pageId, api, onBack, onDeleted }: CmsPageEditorProps) {
  const { showToast } = useToast();
  const [page, setPage] = useState<CmsPage | null>(null);
  const [sections, setSections] = useState<CmsSection[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [device, setDevice] = useState<"desktop" | "mobile">("desktop");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [media, setMedia] = useState<{ id: string; url: string; alt?: string }[]>([]);
  const [faqCategories, setFaqCategories] = useState<{ id: string; title: string }[]>([]);
  const [mediaOpen, setMediaOpen] = useState(false);
  const [mediaProp, setMediaProp] = useState("image_url");
  const [previewTick, setPreviewTick] = useState(0);
  const [paletteDragging, setPaletteDragging] = useState(false);
  const previewRef = useRef<HTMLIFrameElement>(null);

  const notify = useCallback(
    (message: string, type: "success" | "error" | "warning" | "info" = "info") => {
      setMsg(message);
      showToast(message, type, "top-right");
    },
    [showToast]
  );

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );
  const selected = useMemo(
    () => sections.find((s) => s.id === selectedId) || null,
    [sections, selectedId]
  );
  const refreshPreview = useCallback(() => setPreviewTick((n) => n + 1), []);
  const { mergePending, queueSave } = useCmsSectionSaves({
    updateSection: api.updateSection,
    setSections,
    setMessage: (value) => {
      const text = typeof value === "function" ? value("") : value;
      setMsg(text);
      // Autosave: toast errors only (avoid spam on every keystroke save).
      if (String(text).includes("失敗")) {
        showToast(String(text), "error", "top-right");
      }
    },
    refreshPreview,
  });

  const load = useCallback(async () => {
    if (!pageId) return;
    setBusy(true);
    const res = await api.getPage(pageId);
    setBusy(false);
    if (res.error || !res.page) {
      notify(String(res.error || "載入失敗"), "error");
      return;
    }
    setPage(res.page);
    setSections(mergePending(res.page.sections || []));
    if (!selectedId && res.page.sections?.[0]) {
      setSelectedId(res.page.sections[0].id);
    }
  }, [api, mergePending, notify, pageId, selectedId]);

  useEffect(() => {
    void load();
  }, [pageId]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    void api.getMedia().then((res) => {
      if (res.media) setMedia(res.media);
    });
    void api.getFaqCategories().then((res) => {
      if (res.categories) setFaqCategories(res.categories);
    });
  }, [api]);

  useEffect(() => {
    function onMessage(event: MessageEvent) {
      if (event.origin !== window.location.origin) return;
      if (event.source !== previewRef.current?.contentWindow) return;
      const data = event.data;
      if (!data || data.source !== "cms-inline") return;
      if (data.type === "select-section" && data.sectionId) {
        setSelectedId(String(data.sectionId));
      }
      if (data.type === "inline-edit" && data.sectionId && data.prop) {
        const section = sections.find((s) => s.id === data.sectionId);
        if (!section) return;
        const nextProps: Record<string, unknown> = { ...section.props };
        if (data.prop === "buttons" && Number.isInteger(data.buttonIndex)) {
          const buttons = Array.isArray(section.props.buttons)
            ? section.props.buttons.map((button) => ({ ...(button as Record<string, unknown>) }))
            : [];
          const button = buttons[data.buttonIndex];
          if (!button) return;
          button.label = String(data.value || "");
          if (data.href != null) button.href = String(data.href);
          nextProps.buttons = buttons;
        } else {
          nextProps[String(data.prop)] = data.value;
          if (data.hrefProp && data.href != null) {
            nextProps[String(data.hrefProp)] = data.href;
          }
        }
        queueSave(section.id, nextProps);
      }
      if (data.type === "edit-image" && data.sectionId && data.prop) {
        setSelectedId(String(data.sectionId));
        setMediaProp(String(data.prop));
        setMediaOpen(true);
      }
    }
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [queueSave, sections]);

  async function saveMeta(patch: Partial<CmsPage>) {
    if (!page) return;
    setBusy(true);
    const res = await api.updatePage({ id: page.id, ...patch });
    setBusy(false);
    if (res.error || !res.page) {
      notify(String(res.error || "儲存失敗"), "error");
      return;
    }
    setPage(res.page);
    notify("頁面資料已儲存", "success");
    setPreviewTick((n) => n + 1);
  }

  async function addSection(type: CmsSectionType, insertAt = sections.length) {
    if (!page) return;
    setBusy(true);
    const res = await api.createSection(page.id, { type });
    if (res.error || !res.section) {
      setBusy(false);
      notify(String(res.error || "新增失敗"), "error");
      return;
    }
    const next = [...sections];
    next.splice(Math.max(0, Math.min(insertAt, next.length)), 0, res.section);
    if (insertAt < sections.length) {
      const reordered = await api.reorderSections(
        page.id,
        next.map((section) => section.id)
      );
      if (reordered.error || !reordered.sections) {
        setSections([...sections, res.section]);
        setBusy(false);
        notify(String(reordered.error || "區塊已新增，但插入位置儲存失敗"), "warning");
        return;
      }
      setSections(reordered.sections);
    } else {
      setSections(next);
    }
    setBusy(false);
    setSelectedId(res.section.id);
    notify(`已新增「${sectionLabel(type)}」區塊`, "success");
    refreshPreview();
  }

  function onDragStart(event: DragStartEvent) {
    setPaletteDragging(event.active.data.current?.source === "palette");
  }

  async function onDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    setPaletteDragging(false);
    if (!over || !page) return;
    if (active.data.current?.source === "palette") {
      const type = active.data.current.type as CmsSectionType;
      const overIndex = sections.findIndex((section) => section.id === over.id);
      const insertAt = over.id === CMS_CANVAS_DROP_ID || overIndex < 0
        ? sections.length
        : overIndex;
      await addSection(type, insertAt);
      return;
    }
    if (active.id === over.id) return;
    const oldIndex = sections.findIndex((s) => s.id === active.id);
    const newIndex = sections.findIndex((s) => s.id === over.id);
    if (oldIndex < 0 || newIndex < 0) return;
    const next = arrayMove(sections, oldIndex, newIndex);
    setSections(next);
    const res = await api.reorderSections(
      page.id,
      next.map((s) => s.id)
    );
    if (res.error || !res.sections) {
      setSections(sections);
      notify(String(res.error || "排序儲存失敗"), "error");
      return;
    }
    setSections(res.sections);
    notify("區塊順序已更新", "success");
    refreshPreview();
  }

  function saveProps(props: Record<string, unknown>) {
    if (!selected) return;
    queueSave(selected.id, props);
  }

  if (!pageId) {
    return <p className="note">請選擇頁面。</p>;
  }

  const previewUrl = page
    ? `/p/${encodeURIComponent(page.slug)}?preview=1&inline=1&t=${previewTick}`
    : "";
  const openPreviewUrl = page
    ? `/p/${encodeURIComponent(page.slug)}?preview=1`
    : "";

  return (
    <div className="cms-editor">
      <div className="cms-editor__top">
        <button type="button" className="btn-sm" onClick={onBack}>
          ← 返回列表
        </button>
        <input
          className="cms-editor__title"
          value={page?.title || ""}
          onChange={(e) => setPage((p) => (p ? { ...p, title: e.target.value } : p))}
          onBlur={() => page && void saveMeta({ title: page.title })}
        />
        <input
          className="cms-editor__slug"
          value={page?.slug || ""}
          onChange={(e) => setPage((p) => (p ? { ...p, slug: e.target.value } : p))}
          onBlur={() => page && void saveMeta({ slug: page.slug })}
          title="slug"
        />
        <span className="cms-status">{page?.status === "published" ? "已發布" : "草稿"}</span>
        <button
          type="button"
          className="btn-sm"
          disabled={busy || !page}
          onClick={() =>
            page &&
            void api.pageAction(page.id, page.status === "published" ? "unpublish" : "publish").then(
              (res) => {
                if (res.error) {
                  notify(String(res.error), "error");
                  return;
                }
                notify(
                  page.status === "published" ? "已取消發布（改為草稿）" : "頁面已發布",
                  "success"
                );
                void load();
              }
            )
          }
        >
          {page?.status === "published" ? "取消發布" : "發布"}
        </button>
        <a className="btn-sm" href={openPreviewUrl || "#"} target="_blank" rel="noreferrer">
          開新分頁預覽
        </a>
        <button
          type="button"
          className="btn-sm"
          onClick={() => {
            if (!page || !confirm("確定刪除此頁？")) return;
            void api.pageAction(page.id, "delete").then((res) => {
              if (res.error) {
                notify(String(res.error), "error");
                return;
              }
              showToast("頁面已刪除", "success", "top-right");
              onDeleted?.();
            });
          }}
        >
          刪除
        </button>
        {msg ? <span className="cms-msg">{msg}</span> : null}
      </div>

      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={onDragStart}
        onDragCancel={() => setPaletteDragging(false)}
        onDragEnd={(event) => void onDragEnd(event)}
      >
      <div className="cms-editor__body">
        <aside className="cms-editor__palette">
          <h3>新增區塊</h3>
          <div className="cms-palette-grid">
            {SECTION_PALETTE.map((item) => (
              <CmsPaletteButton
                key={item.type}
                type={item.type}
                label={item.label}
                onAdd={() => void addSection(item.type)}
              />
            ))}
          </div>
          <h3>圖層</h3>
          <SortableContext items={sections.map((s) => s.id)} strategy={verticalListSortingStrategy}>
            <div className="cms-layers">
              {sections.map((section) => (
                <CmsSortableRow
                  key={section.id}
                  section={section}
                  selected={section.id === selectedId}
                  onSelect={() => setSelectedId(section.id)}
                />
              ))}
            </div>
          </SortableContext>
        </aside>

        <CmsCanvasDropTarget
          className={`cms-editor__canvas cms-editor__canvas--${device}`}
          active={paletteDragging}
        >
          <div className="cms-device-toggle">
            <Switch
              name="cms-preview-device"
              size="small"
              value={device}
              onValueChange={(next) => {
                if (next === "mobile" || next === "desktop") setDevice(next);
              }}
            >
              <Switch.Control label="手機" value="mobile" />
              <Switch.Control label="電腦" value="desktop" defaultChecked />
            </Switch>
          </div>
          {previewUrl ? (
            <iframe
              ref={previewRef}
              key={previewUrl}
              title="CMS preview"
              className="cms-preview-frame"
              src={previewUrl}
            />
          ) : null}
        </CmsCanvasDropTarget>

        <aside className="cms-editor__props">
          <h3>區塊設定</h3>
          {selected ? (
            <>
              <p className="cms-hint">{sectionLabel(selected.type)}</p>
              <CmsSectionPropsForm
                section={selected}
                media={media}
                faqCategories={faqCategories}
                onChange={(props) => void saveProps(props)}
                onPickMedia={(prop) => {
                  setMediaProp(prop);
                  setMediaOpen(true);
                }}
              />
              <div className="cms-props-actions">
                <button
                  type="button"
                  className="btn-sm"
                  onClick={() =>
                    void api
                      .sectionAction(selected.id, selected.is_visible ? "hide" : "show")
                      .then((res) => {
                        if (res.error) {
                          notify(String(res.error), "error");
                          return;
                        }
                        notify(selected.is_visible ? "區塊已隱藏" : "區塊已顯示", "success");
                        void load();
                      })
                  }
                >
                  {selected.is_visible ? "隱藏" : "顯示"}
                </button>
                <button
                  type="button"
                  className="btn-sm"
                  onClick={() => {
                    if (!confirm("刪除此區塊？")) return;
                    void api.sectionAction(selected.id, "delete").then((res) => {
                      if (res.error) {
                        notify(String(res.error), "error");
                        return;
                      }
                      notify("區塊已刪除", "success");
                      setSelectedId(null);
                      void load();
                    });
                  }}
                >
                  刪除區塊
                </button>
              </div>
            </>
          ) : (
            <p className="cms-hint">點選圖層或預覽中的區塊以編輯。</p>
          )}
          <CmsPageMetaForm
            page={page}
            onSave={(meta) => void saveMeta(meta)}
          />
        </aside>
      </div>
      </DndContext>

      {mediaOpen ? (
        <CmsMediaModal
          media={media}
          onClose={() => setMediaOpen(false)}
          onUpload={(file) => {
            void api.uploadMedia(file).then((res) => {
              if (res.media) {
                setMedia((prev) => [res.media!, ...prev]);
                notify("媒體已上傳", "success");
              } else if (res.error) {
                notify(String(res.error), "error");
              }
            });
          }}
          onSelect={(item) => {
            if (selected) saveProps({ ...selected.props, [mediaProp]: item.url });
            notify("已套用圖片", "success");
            setMediaOpen(false);
          }}
          onDelete={(item) => {
            if (!confirm("刪除此媒體紀錄？")) return;
            void api.deleteMedia(item.id).then((res) => {
              if (res.error) notify(String(res.error), "error");
              else {
                setMedia((prev) => prev.filter((mediaItem) => mediaItem.id !== item.id));
                notify("媒體已刪除", "success");
              }
            });
          }}
        />
      ) : null}
    </div>
  );
}
