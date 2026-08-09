import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  pointerWithin,
  useSensor,
  useSensors,
  type CollisionDetection,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import {
  sortableKeyboardCoordinates,
} from "@dnd-kit/sortable";

import {
  CMS_CANVAS_DROP_ID,
  CMS_TRASH_DROP_ID,
  CmsCanvasDropTarget,
  CmsDragOverlayCard,
} from "@/components/admin/CmsEditorDnd";
import CmsEditorTopbar from "@/components/admin/CmsEditorTopbar";
import CmsEditorTools from "@/components/admin/CmsEditorTools";
import type { CmsInsertTarget } from "@/components/admin/CmsAddSectionGallery";
import CmsMediaModal from "@/components/admin/CmsMediaModal";
import {
  sectionImagePropKey,
  sectionLabel,
  sectionPrimaryProp,
  type CmsPage,
  type CmsSection,
  type CmsSectionTemplate,
  type CmsSectionType,
} from "@/components/admin/cmsSectionMeta";
import {
  syncSectionPageImage,
  type SyncSectionPageImageApi,
} from "@/components/admin/syncSectionPageImage";
import { createCmsPreviewBridge, softOrHard } from "@/components/admin/cmsPreviewBridge";
import useCmsEditorCommands, {
  copyCmsProps,
  type SectionRef,
} from "@/components/admin/useCmsEditorCommands";
import useCmsEditorHistory from "@/components/admin/useCmsEditorHistory";
import useCmsSectionSaves from "@/components/admin/useCmsSectionSaves";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/components/ui/toast-1";
import type { ImageUploadResult } from "@/components/ui/image-upload";

export type CmsPageEditorProps = {
  pageId: string | null;
  api: {
    getPage: (id: string) => Promise<{ page?: CmsPage; error?: string }>;
    updatePage: (fields: Record<string, unknown>) => Promise<{ page?: CmsPage; error?: string }>;
    pageAction: (id: string, action: string) => Promise<{ ok?: boolean; error?: string }>;
    createSection: (
      pageId: string,
      body: { type: string; props?: Record<string, unknown> }
    ) => Promise<{ section?: CmsSection; error?: string }>;
    updateSection: (fields: Record<string, unknown>) => Promise<{ section?: CmsSection; error?: string }>;
    getSectionHtml?: (id: string) => Promise<{ html?: string; error?: string }>;
    sectionAction: (id: string, action: string) => Promise<{ ok?: boolean; error?: string }>;
    reorderSections: (
      pageId: string,
      sectionIds: string[]
    ) => Promise<{ sections?: CmsSection[]; error?: string }>;
    getMedia: (opts?: {
      page?: number;
      pageSize?: number;
    }) => Promise<{
      media?: { id: string; url: string; alt?: string }[];
      total?: number;
      page?: number;
      page_size?: number;
      error?: string;
    }>;
    getFaqCategories: () => Promise<{
      categories?: { id: string; title: string }[];
      error?: string;
    }>;
    uploadMedia: (file: File) => Promise<{ media?: { id: string; url: string }; url?: string; error?: string }>;
    deleteMedia: (id: string) => Promise<{ ok?: boolean; error?: string }>;
    uploadPageImage?: (
      file: File,
      pageKey?: string
    ) => Promise<ImageUploadResult>;
  } & SyncSectionPageImageApi;
  onBack: () => void;
  onDeleted?: () => void;
};

function changedPropKey(
  before: Record<string, unknown>,
  after: Record<string, unknown>
) {
  const keys = new Set([...Object.keys(before), ...Object.keys(after)]);
  const changed = [...keys].filter(
    (key) => JSON.stringify(before[key]) !== JSON.stringify(after[key])
  );
  return changed.length === 1 ? changed[0] : "all";
}

function isEditableTarget(target: EventTarget | null) {
  const element = target as HTMLElement | null;
  return Boolean(
    element?.closest("input, textarea, select, [contenteditable='true']")
  );
}

const cmsCollisionDetection: CollisionDetection = (args) => {
  const pointerHits = pointerWithin(args);
  const trashHit = pointerHits.find((collision) => collision.id === CMS_TRASH_DROP_ID);
  if (trashHit) return [trashHit];
  const canvasHit = pointerHits.find((collision) => collision.id === CMS_CANVAS_DROP_ID);
  if (canvasHit && args.active.data.current?.source === "palette") {
    return [canvasHit];
  }
  return closestCenter(args).filter((collision) => collision.id !== CMS_TRASH_DROP_ID);
};

export default function CmsPageEditor({ pageId, api, onBack, onDeleted }: CmsPageEditorProps) {
  const { showToast } = useToast();
  const [page, setPage] = useState<CmsPage | null>(null);
  const [sections, setSections] = useState<CmsSection[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [device, setDevice] = useState<"desktop" | "mobile">("desktop");
  const [actionBusy, setActionBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [media, setMedia] = useState<{ id: string; url: string; alt?: string }[]>([]);
  const [mediaTotal, setMediaTotal] = useState(0);
  const [mediaPage, setMediaPage] = useState(1);
  const mediaPageSize = 20;
  const [faqCategories, setFaqCategories] = useState<{ id: string; title: string }[]>([]);
  const [mediaOpen, setMediaOpen] = useState(false);
  const [mediaProp, setMediaProp] = useState("image_url");
  const [mediaBlockId, setMediaBlockId] = useState<string | null>(null);
  const [previewNonce, setPreviewNonce] = useState(0);
  const [dragging, setDragging] = useState(false);
  const [dragLabel, setDragLabel] = useState<string | null>(null);
  const [dragType, setDragType] = useState<string | undefined>(undefined);
  const [insertTarget, setInsertTarget] = useState<CmsInsertTarget | null>(null);
  const [galleryOpen, setGalleryOpen] = useState(false);
  const [focusedProp, setFocusedProp] = useState<string | null>(null);
  const previewRef = useRef<HTMLIFrameElement>(null);
  const dropTargetRef = useRef<{ anchor: string; index: number } | null>(null);
  const sectionRefs = useRef(new Map<string, SectionRef>());
  const deleteSectionRef = useRef<(section: CmsSection) => Promise<void>>(async () => undefined);
  const duplicateSectionRef = useRef<(section: CmsSection) => Promise<unknown>>(
    async () => undefined
  );
  const moveSectionRef = useRef<
    (section: CmsSection, direction: "up" | "down") => Promise<void>
  >(async () => undefined);
  const toggleSectionRef = useRef<(section: CmsSection) => Promise<void>>(
    async () => undefined
  );

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
  const history = useCmsEditorHistory((message) => notify(message, "error"));
  const busy = actionBusy || history.busy;
  const selected = useMemo(
    () => sections.find((s) => s.id === selectedId) || null,
    [sections, selectedId]
  );
  const hardRefreshPreview = useCallback(() => {
    const frame = previewRef.current;
    try {
      if (frame?.contentWindow) {
        frame.contentWindow.location.reload();
        return;
      }
    } catch {
      /* cross-origin or unloaded */
    }
    setPreviewNonce((n) => n + 1);
  }, []);
  const fetchSectionHtml = api.getSectionHtml;
  const preview = useMemo(
    () =>
      createCmsPreviewBridge({
        iframeRef: previewRef,
        hardRefresh: hardRefreshPreview,
        fetchSectionHtml: async (sectionId) => {
          if (!fetchSectionHtml) return { error: "缺少區塊預覽 API" };
          return fetchSectionHtml(sectionId);
        },
      }),
    [fetchSectionHtml, hardRefreshPreview]
  );
  const { discardPending, flushPending, mergePending, pendingIds, queueSave } = useCmsSectionSaves({
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
    onSectionSaved: (sectionId) => preview.syncSection(sectionId),
    hardRefreshPreview,
  });
  const getSectionRef = useCallback((id: string) => {
    const existing = sectionRefs.current.get(id);
    if (existing) return existing;
    const reference = { key: id, currentId: id };
    sectionRefs.current.set(id, reference);
    return reference;
  }, []);

  const load = useCallback(async () => {
    if (!pageId) return;
    setActionBusy(true);
    const res = await api.getPage(pageId);
    setActionBusy(false);
    if (res.error || !res.page) {
      notify(String(res.error || "載入失敗"), "error");
      return;
    }
    setPage(res.page);
    const incoming = mergePending(res.page.sections || []);
    incoming.forEach((section) => getSectionRef(section.id));
    setSections(incoming);
    setSelectedId((current) =>
      incoming.some((section) => section.id === current)
        ? current
        : incoming[0]?.id || null
    );
  }, [api, getSectionRef, mergePending, notify, pageId]);

  useEffect(() => {
    history.clear();
    void load();
  }, [pageId]); // eslint-disable-line react-hooks/exhaustive-deps

  const loadMediaPage = useCallback(
    async (page: number) => {
      const res = await api.getMedia({ page, pageSize: mediaPageSize });
      if (res.media) {
        setMedia(res.media);
        setMediaTotal(Number(res.total || res.media.length));
        setMediaPage(Number(res.page || page));
      }
    },
    [api]
  );

  useEffect(() => {
    void loadMediaPage(1);
    void api.getFaqCategories().then((res) => {
      if (res.categories) setFaqCategories(res.categories);
    });
  }, [api, loadMediaPage]);

  const prepareSection = useCallback(
    async (id: string) => {
      const saved = await flushPending(id);
      if (!saved) throw new Error("尚有內容未能儲存，已取消這次操作");
      discardPending(id);
    },
    [discardPending, flushPending]
  );

  const applyProps = useCallback(
    async (reference: SectionRef, props: Record<string, unknown>) => {
      await prepareSection(reference.currentId);
      const res = await api.updateSection({
        id: reference.currentId,
        props: copyCmsProps(props),
      });
      if (res.error || !res.section) throw new Error(String(res.error || "內容儲存失敗"));
      setSections((current) =>
        current.map((section) =>
          section.id === reference.currentId ? res.section! : section
        )
      );
      await softOrHard(
        () => preview.syncSection(reference.currentId),
        hardRefreshPreview
      );
    },
    [api, hardRefreshPreview, prepareSection, preview]
  );

  const saveSectionProps = useCallback(
    (
      section: CmsSection,
      props: Record<string, unknown>,
      options?: { skipPreview?: boolean }
    ) => {
      if (busy) return;
      const before = copyCmsProps(section.props);
      const after = copyCmsProps(props);
      if (JSON.stringify(before) === JSON.stringify(after)) return;
      const reference = getSectionRef(section.id);
      history.record({
        label: "編輯區塊",
        coalesceKey: `props:${reference.key}:${changedPropKey(before, after)}`,
        undo: () => applyProps(reference, before),
        redo: () => applyProps(reference, after),
      });
      queueSave(section.id, after, options);
    },
    [applyProps, busy, getSectionRef, history, queueSave]
  );

  useEffect(() => {
    function onMessage(event: MessageEvent) {
      if (event.origin !== window.location.origin) return;
      if (event.source !== previewRef.current?.contentWindow) return;
      const data = event.data;
      if (!data || data.source !== "cms-inline") return;
      if (data.type === "preview-ack") {
        preview.handleAck(data);
        return;
      }
      if (data.type === "open-add") {
        const index =
          typeof data.index === "number" && Number.isFinite(data.index)
            ? Math.max(0, Math.floor(data.index))
            : Infinity;
        setInsertTarget({
          anchor: typeof data.anchor === "string" && data.anchor ? data.anchor : "end",
          index,
          beforeId: typeof data.beforeId === "string" ? data.beforeId : undefined,
        });
        setGalleryOpen(true);
        return;
      }
      if (data.type === "select-section" && data.sectionId) {
        const nextId = String(data.sectionId);
        if (selectedId !== nextId) setFocusedProp(null);
        setSelectedId(nextId);
      }
      if (data.type === "focus-prop" && data.sectionId) {
        setSelectedId(String(data.sectionId));
        setFocusedProp(typeof data.prop === "string" ? data.prop : "title");
      }
      if (data.type === "duplicate-section" && data.sectionId) {
        const section = sections.find((item) => item.id === data.sectionId);
        if (section && !busy) void duplicateSectionRef.current(section);
      }
      if (data.type === "move-section" && data.sectionId) {
        const section = sections.find((item) => item.id === data.sectionId);
        const direction =
          data.direction === -1 || data.direction === "up"
            ? "up"
            : data.direction === 1 || data.direction === "down"
              ? "down"
              : null;
        if (section && direction && !busy) {
          void moveSectionRef.current(section, direction);
        }
      }
      if (data.type === "toggle-section" && data.sectionId) {
        const section = sections.find((item) => item.id === data.sectionId);
        if (section && !busy) void toggleSectionRef.current(section);
      }
      if (data.type === "delete-section" && data.sectionId) {
        if (busy) return;
        const section = sections.find((s) => s.id === data.sectionId);
        if (!section) return;
        if (!confirm("刪除此區塊？")) return;
        void deleteSectionRef.current(section);
      }
      if (data.type === "block-layout" && data.sectionId && Array.isArray(data.blocks)) {
        if (busy) return;
        const section = sections.find((s) => s.id === data.sectionId);
        if (!section || section.type !== "freeform") return;
        const device = data.device === "mobile" ? "mobile" : "desktop";
        const key = device === "mobile" ? "blocks_mobile" : "blocks";
        saveSectionProps(
          section,
          { ...section.props, [key]: data.blocks },
          { skipPreview: true }
        );
      }
      if (data.type === "block-edit" && data.sectionId && data.blockId && data.field) {
        if (busy) return;
        const section = sections.find((s) => s.id === data.sectionId);
        if (!section || section.type !== "freeform") return;
        const blocks = Array.isArray(section.props.blocks)
          ? section.props.blocks.map((block) => ({ ...(block as Record<string, unknown>) }))
          : [];
        const target = blocks.find((block) => block.id === data.blockId);
        if (!target) return;
        target[String(data.field)] = String(data.value || "");
        if (data.href != null) target.href = String(data.href);
        saveSectionProps(section, { ...section.props, blocks }, { skipPreview: true });
      }
      if (data.type === "inline-edit" && data.sectionId && data.prop) {
        if (busy) return;
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
        saveSectionProps(section, nextProps, { skipPreview: true });
      }
      if (data.type === "edit-image" && data.sectionId) {
        setSelectedId(String(data.sectionId));
        if (data.prop) setMediaProp(String(data.prop));
        setMediaBlockId(typeof data.blockId === "string" ? data.blockId : null);
        setMediaOpen(true);
      }
      if (data.type === "drop-index") {
        const indexOk =
          typeof data.index === "number" && Number.isFinite(data.index);
        const anchorRaw =
          typeof data.anchor === "string" ? data.anchor.trim().toLowerCase() : "";
        const anchor = anchorRaw || "end";
        dropTargetRef.current = indexOk
          ? { anchor, index: Math.max(0, Math.floor(data.index)) }
          : null;
      }
    }
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [busy, preview, saveSectionProps, sections, selectedId]);

  async function saveMeta(patch: Partial<CmsPage>) {
    if (!page) return;
    setActionBusy(true);
    const res = await api.updatePage({ id: page.id, ...patch });
    setActionBusy(false);
    if (res.error || !res.page) {
      notify(String(res.error || "儲存失敗"), "error");
      return;
    }
    setPage(res.page);
    notify("頁面資料已儲存", "success");
    hardRefreshPreview();
  }

  const pageKey = page?.site_route || (page ? `/p/${page.slug}` : "");

  const {
    addSection,
    deleteSection,
    duplicateSection,
    moveSection,
    reorder,
    toggleVisibility,
  } =
    useCmsEditorCommands({
      page,
      pageKey,
      sections,
      selected,
      api,
      setSections,
      setSelectedId,
      setBusy: setActionBusy,
      getSectionRef,
      registerSectionRef: (id, reference) => sectionRefs.current.set(id, reference),
      prepareSection,
      pendingSectionIds: pendingIds,
      record: history.record,
      notify,
      preview,
    });
  deleteSectionRef.current = deleteSection;
  duplicateSectionRef.current = duplicateSection;
  moveSectionRef.current = moveSection;
  toggleSectionRef.current = (section) => toggleVisibility(section);

  const uploadSectionImage = useCallback(
    async (file: File): Promise<ImageUploadResult> => {
      if (api.uploadPageImage) return api.uploadPageImage(file, pageKey);
      const res = await api.uploadMedia(file);
      if (res.error) return { error: res.error };
      return { url: res.url || res.media?.url };
    },
    [api, pageKey]
  );

  const handleSectionImageUploaded = useCallback(
    async (section: CmsSection, url: string, alt: string) => {
      const imageProp = sectionImagePropKey(section.type, section.props);
      if (!imageProp) return;
      const nextProps = { ...section.props, [imageProp]: url, image_alt: alt };
      saveSectionProps(section, nextProps);
      if (!pageKey) return;
      const sync = await syncSectionPageImage(api, {
        pageKey,
        sectionId: section.id,
        sectionType: section.type,
        imageUrl: url,
        imageAlt: alt,
      });
      if (!sync.ok) {
        notify(sync.error || "已更新區塊圖片，但尚未同步到頁面圖片", "warning");
        return;
      }
      notify("圖片已更新，並同步到頁面圖片", "success");
    },
    [api, notify, pageKey, saveSectionProps]
  );

  function endPaletteDropUi() {
    preview.hideDropGaps();
    dropTargetRef.current = null;
    setDragging(false);
    setDragLabel(null);
    setDragType(undefined);
  }

  function onDragStart(event: DragStartEvent) {
    if (busy) return;
    setDragging(true);
    const data = event.active.data.current;
    if (typeof data?.label === "string") {
      setDragLabel(data.label);
    } else if (data?.source === "palette" && data.type) {
      setDragLabel(sectionLabel(String(data.type)));
    } else {
      setDragLabel("拖曳中");
    }
    setDragType(typeof data?.type === "string" ? data.type : undefined);
    if (data?.source === "palette") {
      dropTargetRef.current = { anchor: "end", index: sections.length };
      preview.showDropGaps();
    }
  }

  async function onDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    const source = active.data.current?.source;
    const gapTarget = dropTargetRef.current;
    endPaletteDropUi();
    if (busy || !over || !page) return;
    if (over.id === CMS_TRASH_DROP_ID) {
      if (source === "section") {
        const section = sections.find((item) => item.id === active.id);
        if (section) await deleteSection(section);
      }
      return;
    }
    if (source === "palette") {
      const type = active.data.current?.type as CmsSectionType;
      if (!type) return;
      const initialProps =
        active.data.current?.initialProps &&
        typeof active.data.current.initialProps === "object"
          ? (active.data.current.initialProps as Record<string, unknown>)
          : undefined;
      const overIndex = sections.findIndex((section) => section.id === over.id);
      if (overIndex >= 0) {
        await addSection(type, overIndex, initialProps);
        return;
      }
      if (over.id === CMS_CANVAS_DROP_ID) {
        await addSection(type, {
          anchor: gapTarget?.anchor || "end",
          index: gapTarget?.index ?? sections.length,
        }, initialProps);
        return;
      }
      await addSection(type, sections.length, initialProps);
      return;
    }
    if (active.id === over.id) return;
    const oldIndex = sections.findIndex((item) => item.id === active.id);
    const newIndex = sections.findIndex((item) => item.id === over.id);
    if (oldIndex >= 0 && newIndex >= 0) await reorder(oldIndex, newIndex);
  }

  useEffect(() => {
    if (!dragging || dragType == null) return;
    function onPointerMove(event: PointerEvent) {
      const frame = previewRef.current;
      if (!frame) return;
      const rect = frame.getBoundingClientRect();
      if (
        event.clientX < rect.left ||
        event.clientX > rect.right ||
        event.clientY < rect.top ||
        event.clientY > rect.bottom
      ) {
        return;
      }
      preview.hoverDrop(event.clientY - rect.top);
    }
    window.addEventListener("pointermove", onPointerMove);
    return () => window.removeEventListener("pointermove", onPointerMove);
  }, [dragType, dragging, preview]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (busy || isEditableTarget(event.target)) return;
      if (event.key === "Delete" && selected) {
        event.preventDefault();
        if (confirm("刪除此區塊？")) void deleteSection(selected);
        return;
      }
      if (!(event.ctrlKey || event.metaKey)) return;
      const key = event.key.toLowerCase();
      const wantsUndo = key === "z" && !event.shiftKey;
      const wantsRedo = (key === "z" && event.shiftKey) || key === "y";
      if (!wantsUndo && !wantsRedo) return;
      event.preventDefault();
      void (wantsUndo ? history.undo() : history.redo());
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [busy, deleteSection, history, selected]);

  useEffect(() => {
    preview.selectSection(selectedId);
  }, [preview, selectedId]);

  useEffect(() => {
    preview.post({ type: "set-device", device });
  }, [device, preview]);

  if (!pageId) {
    return <p className="note">請選擇頁面。</p>;
  }

  const previewUrl = page
    ? `/p/${encodeURIComponent(page.slug)}?preview=1&inline=1${previewNonce ? `&t=${previewNonce}` : ""}`
    : "";
  const openPreviewUrl = page
    ? `/p/${encodeURIComponent(page.slug)}?preview=1`
    : "";

  async function chooseTemplate(template: CmsSectionTemplate) {
    const created = await addSection(
      template.type,
      insertTarget || sections.length,
      template.props
    );
    if (!created) return;
    setGalleryOpen(false);
    setInsertTarget(null);
    setFocusedProp(sectionPrimaryProp(template.type));
  }

  function closeGallery() {
    setGalleryOpen(false);
    if (insertTarget) {
      preview.focusAddTarget(
        insertTarget.anchor,
        Number.isFinite(insertTarget.index) ? insertTarget.index : sections.length
      );
    }
    setInsertTarget(null);
  }

  return (
    <div className={`cms-editor${dragging ? " is-dragging" : ""}`}>
      <CmsEditorTopbar
        page={page}
        busy={busy}
        message={msg}
        canUndo={history.canUndo}
        canRedo={history.canRedo}
        previewUrl={openPreviewUrl}
        onBack={onBack}
        onUndo={() => void history.undo()}
        onRedo={() => void history.redo()}
        onChangePage={setPage}
        onSaveMeta={(patch) => void saveMeta(patch)}
        onTogglePublish={() => {
          if (!page) return;
          void api
            .pageAction(page.id, page.status === "published" ? "unpublish" : "publish")
            .then((res) => {
              if (res.error) return notify(String(res.error), "error");
              notify(page.status === "published" ? "已取消發布（改為草稿）" : "頁面已發布", "success");
              void load();
            });
        }}
        onDeletePage={() => {
          if (!page || !confirm("確定刪除此頁？")) return;
          void api.pageAction(page.id, "delete").then((res) => {
            if (res.error) return notify(String(res.error), "error");
            showToast("頁面已刪除", "success", "top-right");
            onDeleted?.();
          });
        }}
      />

      <DndContext
        sensors={sensors}
        collisionDetection={cmsCollisionDetection}
        onDragStart={onDragStart}
        onDragCancel={() => endPaletteDropUi()}
        onDragEnd={(event) => void onDragEnd(event)}
      >
      <div className="cms-editor__body">
        <CmsCanvasDropTarget
          className={`cms-editor__canvas cms-editor__canvas--${device}${busy ? " is-busy" : ""}`}
          active={dragging}
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
              title="CMS preview"
              className="cms-preview-frame"
              src={previewUrl}
            />
          ) : null}
        </CmsCanvasDropTarget>

        <CmsEditorTools
          page={page}
          selected={selected}
          media={media}
          faqCategories={faqCategories}
          disabled={busy}
          focusedProp={focusedProp}
          galleryOpen={galleryOpen}
          insertTarget={insertTarget}
          onCloseGallery={closeGallery}
          onChooseTemplate={chooseTemplate}
          onChangeProps={(props) => selected && saveSectionProps(selected, props)}
          onPickMedia={(prop) => {
            if (prop.startsWith("freeform-block:")) {
              const parts = prop.split(":");
              setMediaBlockId(parts[1] || null);
              setMediaProp(parts[2] || "blocks");
            } else {
              setMediaProp(prop);
              setMediaBlockId(null);
            }
            setMediaOpen(true);
          }}
          onToggleVisibility={() => void toggleVisibility()}
          onDelete={(section) => {
            const target = section || selected;
            if (target) void deleteSection(target);
          }}
          onSaveMeta={(meta) => void saveMeta(meta)}
          uploadImage={uploadSectionImage}
          onImageUploaded={(url, alt) =>
            selected ? handleSectionImageUploaded(selected, url, alt) : undefined
          }
        />
      </div>
      <DragOverlay dropAnimation={null}>
        {dragLabel ? <CmsDragOverlayCard label={dragLabel} type={dragType} /> : null}
      </DragOverlay>
      </DndContext>

      {mediaOpen ? (
        <CmsMediaModal
          media={media}
          total={mediaTotal}
          page={mediaPage}
          pageSize={mediaPageSize}
          onPageChange={(nextPage) => {
            void loadMediaPage(nextPage);
          }}
          onClose={() => setMediaOpen(false)}
          onInvalid={(message) => notify(message, "error")}
          onUpload={(file) => {
            void api.uploadMedia(file).then((res) => {
              if (res.media) {
                notify("媒體已上傳", "success");
                void loadMediaPage(1);
              } else if (res.error) {
                notify(String(res.error), "error");
              }
            });
          }}
          onSelect={(item) => {
            if (selected) {
              if (selected.type === "freeform" && mediaBlockId) {
                const listKey =
                  mediaProp === "blocks_mobile" ? "blocks_mobile" : "blocks";
                const blocks = Array.isArray(selected.props[listKey])
                  ? (selected.props[listKey] as Record<string, unknown>[]).map(
                      (block) => ({ ...block })
                    )
                  : [];
                const target = blocks.find((block) => block.id === mediaBlockId);
                if (target) {
                  target.image_url = item.url;
                  target.image_alt = String(item.alt || target.image_alt || "");
                  saveSectionProps(selected, {
                    ...selected.props,
                    [listKey]: blocks,
                  });
                  notify("已套用圖片", "success");
                }
              } else {
                const next = { ...selected.props, [mediaProp]: item.url };
                if (mediaProp === "image_url" || sectionImagePropKey(selected.type, next)) {
                  void handleSectionImageUploaded(
                    selected,
                    item.url,
                    String(next.image_alt || item.alt || "")
                  );
                } else {
                  saveSectionProps(selected, next);
                  notify("已套用圖片", "success");
                }
              }
            }
            setMediaBlockId(null);
            setMediaOpen(false);
          }}
          onDelete={(item) => {
            if (!confirm("刪除此媒體紀錄？")) return;
            void api.deleteMedia(item.id).then((res) => {
              if (res.error) notify(String(res.error), "error");
              else {
                notify("媒體已刪除", "success");
                void loadMediaPage(mediaPage);
              }
            });
          }}
        />
      ) : null}
    </div>
  );
}
