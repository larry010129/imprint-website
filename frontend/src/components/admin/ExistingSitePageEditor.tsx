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
import { sortableKeyboardCoordinates } from "@dnd-kit/sortable";
import { Redo2, Undo2 } from "lucide-react";

import {
  CMS_CANVAS_DROP_ID,
  CMS_TRASH_DROP_ID,
  CmsCanvasDropTarget,
  CmsDragOverlayCard,
} from "@/components/admin/CmsEditorDnd";
import PageImageEditModal, {
  type PageImageEditRow,
} from "@/components/admin/PageImageEditModal";
import SiteEditorTools from "@/components/admin/SiteEditorTools";
import {
  sectionAnchor,
  sectionImagePropKey,
  sectionLabel,
  type CmsPage,
  type CmsSection,
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
    getCopySlots: () => Promise<{
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
    createSection: (
      pageId: string,
      body: { type: string; props?: Record<string, unknown> }
    ) => Promise<{ section?: CmsSection; error?: string }>;
    updateSection: (
      fields: Record<string, unknown>
    ) => Promise<{ section?: CmsSection; error?: string }>;
    getSectionHtml?: (id: string) => Promise<{ html?: string; error?: string }>;
    sectionAction: (
      id: string,
      action: string
    ) => Promise<{ ok?: boolean; error?: string }>;
    reorderSections: (
      pageId: string,
      sectionIds: string[]
    ) => Promise<{ sections?: CmsSection[]; error?: string }>;
    getFaqCategories?: () => Promise<{
      categories?: { id: string; title: string }[];
      error?: string;
    }>;
    getPageImages?: () => Promise<{
      pageImages?: PageImageEditRow[];
      error?: string;
    }>;
    uploadPageImage?: (file: File) => Promise<ImageUploadResult>;
    updatePageImage?: (fields: {
      pageKey: string;
      slotKey: string;
      imageUrl: string;
      imageWebp: string;
      imageAlt: string;
      isPublished: boolean;
    }) => Promise<{ error?: string | { message?: string } }>;
    uploadMedia?: (file: File) => Promise<ImageUploadResult>;
  } & SyncSectionPageImageApi;
  onBack: () => void;
};

type SaveStatus = "idle" | "saving" | "saved" | "error";

function copySlot(slot: CopySlot): CopySlot {
  return { ...slot };
}

function isEditableTarget(target: EventTarget | null) {
  const element = target as HTMLElement | null;
  return Boolean(
    element?.closest("input, textarea, select, [contenteditable='true']")
  );
}

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

const siteCollisionDetection: CollisionDetection = (args) => {
  const pointerHits = pointerWithin(args);
  const trashHit = pointerHits.find((collision) => collision.id === CMS_TRASH_DROP_ID);
  if (trashHit) return [trashHit];
  const canvasHit = pointerHits.find((collision) => collision.id === CMS_CANVAS_DROP_ID);
  if (canvasHit && args.active.data.current?.source === "palette") {
    return [canvasHit];
  }
  return closestCenter(args).filter(
    (collision) =>
      collision.id !== CMS_TRASH_DROP_ID &&
      (args.active.data.current?.source === "palette" ||
        collision.id !== CMS_CANVAS_DROP_ID)
  );
};

export default function ExistingSitePageEditor({
  page,
  api,
  onBack,
}: ExistingSitePageEditorProps) {
  const { showToast } = useToast();
  const [slots, setSlots] = useState<CopySlot[]>([]);
  const [hostPage, setHostPage] = useState<CmsPage | null>(null);
  const [sections, setSections] = useState<CmsSection[]>([]);
  const [selectedSlotKey, setSelectedSlotKey] = useState<string | null>(null);
  const [selectedSectionId, setSelectedSectionId] = useState<string | null>(null);
  const [device, setDevice] = useState<"desktop" | "mobile">("desktop");
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const [actionBusy, setActionBusy] = useState(false);
  const [previewNonce, setPreviewNonce] = useState(0);
  const [dragging, setDragging] = useState(false);
  const [dragLabel, setDragLabel] = useState<string | null>(null);
  const [dragType, setDragType] = useState<string | undefined>(undefined);
  const [faqCategories, setFaqCategories] = useState<{ id: string; title: string }[]>([]);
  const [pageImageEdit, setPageImageEdit] = useState<PageImageEditRow | null>(null);
  const previewRef = useRef<HTMLIFrameElement>(null);
  const dropTargetRef = useRef<{ anchor: string; index: number } | null>(null);
  const slotsRef = useRef<CopySlot[]>([]);
  const lastSavedRef = useRef(new Map<string, CopySlot>());
  const saveRevision = useRef(0);
  const slotSaveRevisions = useRef(new Map<string, number>());
  const slotSaveChains = useRef(new Map<string, Promise<void>>());
  const sectionRefs = useRef(new Map<string, SectionRef>());
  const deleteSectionRef = useRef<(section: CmsSection) => Promise<void>>(async () => undefined);

  const history = useCmsEditorHistory((message) =>
    showToast(message, "error", "top-right")
  );
  const busy = history.busy || saveStatus === "saving" || actionBusy;
  const hardRefreshPreview = useCallback(() => {
    const frame = previewRef.current;
    try {
      if (frame?.contentWindow) {
        frame.contentWindow.location.reload();
        return;
      }
    } catch {
      /* unloaded */
    }
    setPreviewNonce((tick) => tick + 1);
  }, []);
  const notify = useCallback(
    (message: string, type: "success" | "error" | "warning" | "info" = "info") => {
      showToast(message, type, "top-right");
    },
    [showToast]
  );
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
      if (String(text).includes("失敗")) notify(String(text), "error");
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

  useEffect(() => {
    slotsRef.current = slots;
  }, [slots]);

  const rememberSaved = useCallback((slot: CopySlot) => {
    lastSavedRef.current.set(slot.slot_key, copySlot(slot));
  }, []);

  const loadSlots = useCallback(async () => {
    const result = await api.getCopySlots();
    if (result.error) {
      notify(String(result.error), "error");
      return;
    }
    const pageSlots = (result.slots || []).filter((slot) => slot.page_key === page.route);
    lastSavedRef.current = new Map(pageSlots.map((slot) => [slot.slot_key, copySlot(slot)]));
    setSlots(pageSlots);
    setSelectedSlotKey((current) =>
      current && pageSlots.some((slot) => slot.slot_key === current) ? current : null
    );
  }, [api, notify, page.route]);

  const loadHost = useCallback(async () => {
    setActionBusy(true);
    const result = await api.getCmsSitePage(page.route);
    setActionBusy(false);
    if (result.error || !result.page) {
      notify(String(result.error || "載入固定頁區塊失敗"), "error");
      setHostPage(null);
      setSections([]);
      return;
    }
    setHostPage(result.page);
    const incoming = mergePending(result.sections || result.page.sections || []);
    incoming.forEach((section) => getSectionRef(section.id));
    setSections(incoming);
    setSelectedSectionId((current) =>
      current && incoming.some((section) => section.id === current)
        ? current
        : null
    );
  }, [api, getSectionRef, mergePending, notify, page.route]);

  useEffect(() => {
    history.clear();
    sectionRefs.current.clear();
    void loadSlots();
    void loadHost();
  }, [page.route]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    void api.getFaqCategories?.().then((res) => {
      if (res.categories) setFaqCategories(res.categories);
    });
  }, [api]);

  const softApplySlot = useCallback(
    (slot: CopySlot) => {
      const ok = preview.applyCopySlot(
        slot.slot_key,
        slot.text_value,
        slot.kind === "button" ? slot.href : ""
      );
      if (!ok) hardRefreshPreview();
    },
    [hardRefreshPreview, preview]
  );

  const persistSlot = useCallback(
    (slot: CopySlot, syncPreview = false): Promise<void> => {
      const revision = ++saveRevision.current;
      const slotRevision = (slotSaveRevisions.current.get(slot.slot_key) || 0) + 1;
      slotSaveRevisions.current.set(slot.slot_key, slotRevision);
      setSaveStatus("saving");

      const previous = slotSaveChains.current.get(slot.slot_key) || Promise.resolve();
      const task = previous.catch(() => undefined).then(async () => {
        const result = await api.updateCopySlot({
          pageKey: slot.page_key,
          slotKey: slot.slot_key,
          textValue: slot.text_value,
          href: slot.kind === "button" ? slot.href : "",
          isPublished: slot.is_published,
        });
        if (result.error || !result.slot) {
          if (revision === saveRevision.current) setSaveStatus("error");
          throw new Error(String(result.error || "儲存失敗"));
        }
        if (slotSaveRevisions.current.get(slot.slot_key) === slotRevision) {
          rememberSaved(result.slot);
          slotsRef.current = slotsRef.current.map((item) =>
            item.slot_key === result.slot!.slot_key ? result.slot! : item
          );
          setSlots(slotsRef.current);
          if (syncPreview) softApplySlot(result.slot);
        }
        if (revision === saveRevision.current) setSaveStatus("saved");
      });
      slotSaveChains.current.set(slot.slot_key, task);
      void task.finally(() => {
        if (slotSaveChains.current.get(slot.slot_key) === task) {
          slotSaveChains.current.delete(slot.slot_key);
        }
      });
      return task;
    },
    [api, rememberSaved, softApplySlot]
  );

  const applySlot = useCallback(
    async (next: CopySlot, syncPreview = true) => {
      slotsRef.current = slotsRef.current.map((item) =>
        item.slot_key === next.slot_key ? next : item
      );
      setSlots(slotsRef.current);
      setSelectedSlotKey(next.slot_key);
      setSelectedSectionId(null);
      try {
        await persistSlot(next, syncPreview);
      } catch (error) {
        notify(String(error), "error");
        throw error;
      }
    },
    [notify, persistSlot]
  );

  const commitSlot = useCallback(
    (before: CopySlot, after: CopySlot, coalesceKey?: string, syncPreview = false) => {
      if (
        before.text_value === after.text_value &&
        before.href === after.href &&
        before.is_published === after.is_published
      ) {
        return;
      }
      history.record({
        label: "編輯內容",
        coalesceKey,
        undo: () => applySlot(copySlot(before), true),
        redo: () => applySlot(copySlot(after), true),
      });
      slotsRef.current = slotsRef.current.map((item) =>
        item.slot_key === after.slot_key ? after : item
      );
      setSlots(slotsRef.current);
      setSelectedSlotKey(after.slot_key);
      setSelectedSectionId(null);
      void persistSlot(after, syncPreview).catch((error) => {
        notify(String(error), "error");
      });
    },
    [applySlot, history, notify, persistSlot]
  );

  const resetSlot = useCallback(
    async (slot: CopySlot) => {
      if (busy) return;
      const before = copySlot(slot);
      const after: CopySlot = {
        ...slot,
        text_value: slot.default_text,
        href: slot.default_href,
        is_published: false,
      };
      try {
        await applySlot(after, true);
        history.record({
          label: "還原預設",
          undo: () => applySlot(before, true),
          redo: () => applySlot(after, true),
        });
        notify("已還原預設內容", "success");
      } catch {
        /* toast already shown */
      }
    },
    [applySlot, busy, history, notify]
  );

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

  const pageKey = page.route;
  const { addSection, deleteSection, reorder, toggleVisibility } = useCmsEditorCommands({
    page: hostPage,
    pageKey,
    sections,
    selected: sections.find((section) => section.id === selectedSectionId) || null,
    api,
    setSections,
    setSelectedId: setSelectedSectionId,
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

  const uploadSectionImage = useCallback(
    async (file: File): Promise<ImageUploadResult> => {
      if (api.uploadPageImage) return api.uploadPageImage(file);
      if (api.uploadMedia) return api.uploadMedia(file);
      return { error: "圖片上傳 API 尚未就緒" };
    },
    [api]
  );

  const handleSectionImageUploaded = useCallback(
    async (section: CmsSection, url: string, alt: string) => {
      const imageProp = sectionImagePropKey(section.type, section.props);
      if (!imageProp) return;
      const nextProps = { ...section.props, [imageProp]: url, image_alt: alt };
      saveSectionProps(section, nextProps);
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

  const openFixedPageImage = useCallback(
    async (slotKey: string) => {
      if (!api.getPageImages || !api.uploadPageImage || !api.updatePageImage) {
        notify("頁面圖片編輯 API 尚未就緒", "warning");
        return;
      }
      const res = await api.getPageImages();
      if (res.error) {
        notify(String(res.error), "error");
        return;
      }
      const row = (res.pageImages || []).find(
        (item) => item.page_key === page.route && item.slot_key === slotKey
      );
      if (!row) {
        notify("找不到此圖片槽位，請到「頁面圖片」分頁確認", "warning");
        return;
      }
      setPageImageEdit(row);
    },
    [api, notify, page.route]
  );

  useEffect(() => {
    function onMessage(event: MessageEvent) {
      if (event.origin !== window.location.origin) return;
      if (event.source !== previewRef.current?.contentWindow) return;
      const data = event.data;
      if (!data) return;

      if (data.source === "cms-inline") {
        if (data.type === "select-section" && data.sectionId) {
          setSelectedSectionId(String(data.sectionId));
          setSelectedSlotKey(null);
        }
        if (data.type === "delete-section" && data.sectionId) {
          if (busy) return;
          const section = sections.find((item) => item.id === data.sectionId);
          if (!section) return;
          if (!confirm("刪除此區塊？")) return;
          void deleteSectionRef.current(section);
        }
        if (data.type === "inline-edit" && data.sectionId && data.prop) {
          if (busy) return;
          const section = sections.find((item) => item.id === data.sectionId);
          if (!section) return;
          const nextProps: Record<string, unknown> = { ...section.props };
          if (data.prop === "buttons" && Number.isInteger(data.buttonIndex)) {
            const buttons = Array.isArray(section.props.buttons)
              ? section.props.buttons.map((button) => ({
                  ...(button as Record<string, unknown>),
                }))
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
          setSelectedSectionId(String(data.sectionId));
          setSelectedSlotKey(null);
        }
        if (data.type === "drop-index") {
          const indexOk =
            typeof data.index === "number" && Number.isFinite(data.index);
          const anchor =
            typeof data.anchor === "string" ? data.anchor.trim().toLowerCase() : "";
          dropTargetRef.current =
            indexOk && anchor
              ? { anchor, index: Math.max(0, Math.floor(data.index)) }
              : null;
        }
        return;
      }

      if (data.source !== "cms-site-inline" || data.pageKey !== page.route) return;
      if (busy) return;
      const slotKey = typeof data.slotKey === "string" ? data.slotKey : "";
      const slot = slotsRef.current.find((item) => item.slot_key === slotKey);
      if (data.type === "select-slot" && slot) {
        setSelectedSlotKey(slot.slot_key);
        setSelectedSectionId(null);
      }
      if (data.type === "inline-edit" && slot && typeof data.value === "string") {
        const before = copySlot(slot);
        const after: CopySlot = {
          ...slot,
          text_value: data.value.slice(0, 12000),
          href: slot.href,
          is_published: true,
        };
        commitSlot(before, after, `text:${slot.slot_key}`);
      }
      if (data.type === "select-image" && slotKey) {
        void openFixedPageImage(slotKey);
      }
    }
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [busy, commitSlot, openFixedPageImage, page.route, saveSectionProps, sections]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (busy || isEditableTarget(event.target)) return;
      const selectedSection =
        sections.find((section) => section.id === selectedSectionId) || null;
      if (event.key === "Delete" && selectedSection) {
        event.preventDefault();
        if (confirm("刪除此區塊？")) void deleteSection(selectedSection);
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
  }, [busy, deleteSection, history, sections, selectedSectionId]);

  useEffect(() => {
    preview.selectSection(selectedSectionId);
  }, [preview, selectedSectionId]);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
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
    if (typeof data?.label === "string") setDragLabel(data.label);
    else if (data?.source === "palette" && data.type) setDragLabel(sectionLabel(String(data.type)));
    else setDragLabel("拖曳中");
    setDragType(typeof data?.type === "string" ? data.type : undefined);
    if (data?.source === "palette") {
      dropTargetRef.current = { anchor: "end", index: sections.filter((s) => sectionAnchor(s) === "end").length };
      preview.showDropGaps();
    }
  }

  async function onDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    const source = active.data.current?.source;
    const gapTarget = dropTargetRef.current;
    endPaletteDropUi();
    if (busy || !over) return;
    if (over.id === CMS_TRASH_DROP_ID) {
      if (source === "slot") {
        const slot = active.data.current?.slot as CopySlot | undefined;
        if (slot) await resetSlot(slot);
      } else if (source === "section") {
        const section = sections.find((item) => item.id === active.id);
        if (section) await deleteSection(section);
      }
      return;
    }
    if (source === "palette") {
      const type = active.data.current?.type as CmsSectionType | undefined;
      if (!type) return;
      if (!hostPage) {
        notify("固定頁主機尚未就緒，請稍後再試", "warning");
        return;
      }
      const overIndex = sections.findIndex((section) => section.id === over.id);
      if (overIndex >= 0) {
        const neighbor = sections[overIndex];
        const anchor = sectionAnchor(neighbor);
        const localIndex = sections
          .filter((section) => sectionAnchor(section) === anchor)
          .findIndex((section) => section.id === neighbor.id);
        await addSection(type, {
          anchor,
          index: localIndex >= 0 ? localIndex : Infinity,
        });
        return;
      }
      if (over.id === CMS_CANVAS_DROP_ID) {
        await addSection(type, {
          anchor: gapTarget?.anchor || "end",
          index: gapTarget?.index ?? Infinity,
        });
        return;
      }
      await addSection(type, { anchor: "end", index: Infinity });
      return;
    }
    if (source === "section" && active.id !== over.id) {
      const oldIndex = sections.findIndex((item) => item.id === active.id);
      const newIndex = sections.findIndex((item) => item.id === over.id);
      if (oldIndex >= 0 && newIndex >= 0) await reorder(oldIndex, newIndex);
    }
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

  const selectedSlot = useMemo(
    () => slots.find((slot) => slot.slot_key === selectedSlotKey) || null,
    [selectedSlotKey, slots]
  );
  const selectedSection = useMemo(
    () => sections.find((section) => section.id === selectedSectionId) || null,
    [sections, selectedSectionId]
  );

  const previewUrl = `${page.route}${page.route.includes("?") ? "&" : "?"}cms_edit=1${
    previewNonce ? `&t=${previewNonce}` : ""
  }`;
  const saveLabel = {
    idle: "",
    saving: "儲存中…",
    saved: "已儲存",
    error: "儲存失敗",
  }[saveStatus];

  function onPaletteAdd() {
    notify("拖曳到預覽中的插入線放置", "info");
  }

  return (
    <div className={`cms-editor cms-site-editor${dragging ? " is-dragging" : ""}`}>
      <div className="cms-editor__top">
        <button type="button" className="btn-sm" onClick={onBack}>
          ← 返回頁面列表
        </button>
        <div className="cms-history-actions">
          <button
            type="button"
            className="btn-sm cms-icon-button"
            disabled={!history.canUndo || busy}
            onClick={() => void history.undo()}
            title="復原（Ctrl/Cmd+Z）"
            aria-label="復原"
          >
            <Undo2 size={16} aria-hidden="true" />
          </button>
          <button
            type="button"
            className="btn-sm cms-icon-button"
            disabled={!history.canRedo || busy}
            onClick={() => void history.redo()}
            title="重做（Ctrl/Cmd+Shift+Z 或 Ctrl/Cmd+Y）"
            aria-label="重做"
          >
            <Redo2 size={16} aria-hidden="true" />
          </button>
        </div>
        <strong>{page.title}</strong>
        <span className="cms-editor__site-route">{page.route}</span>
        <span className={`cms-msg cms-msg--${saveStatus}`}>{saveLabel}</span>
        <a className="btn-sm" href={page.route} target="_blank" rel="noreferrer">
          開啟實際頁面
        </a>
      </div>

      <p className="cms-inline-instruction">
        直接點預覽中的文字編輯。從右側拖曳區塊到預覽插入線放置；圖片可在預覽或右側上傳更換。
      </p>

      <DndContext
        sensors={sensors}
        collisionDetection={siteCollisionDetection}
        onDragStart={onDragStart}
        onDragCancel={() => endPaletteDropUi()}
        onDragEnd={(event) => void onDragEnd(event)}
      >
        <div className="cms-editor__body cms-site-editor__body">
          <CmsCanvasDropTarget
            className={`cms-editor__canvas cms-editor__canvas--${device}${busy ? " is-busy" : ""}`}
            active={dragging}
          >
            <div className="cms-device-toggle">
              <Switch
                name="site-preview-device"
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
            <iframe
              ref={previewRef}
              title={`${page.title} preview`}
              className="cms-preview-frame"
              src={previewUrl}
            />
          </CmsCanvasDropTarget>

          <SiteEditorTools
            selectedSlot={selectedSlot}
            selectedSection={selectedSection}
            slots={slots}
            sections={sections}
            selectedSlotKey={selectedSlotKey}
            selectedSectionId={selectedSectionId}
            faqCategories={faqCategories}
            disabled={busy || !hostPage}
            saving={saveStatus === "saving"}
            onSelectSlot={(key) => {
              setSelectedSlotKey(key);
              setSelectedSectionId(null);
            }}
            onSelectSection={(id) => {
              setSelectedSectionId(id);
              setSelectedSlotKey(null);
            }}
            onChangeSelectedSlot={(next) => {
              slotsRef.current = slotsRef.current.map((slot) =>
                slot.slot_key === next.slot_key ? next : slot
              );
              setSlots(slotsRef.current);
            }}
            onSaveSelectedSlot={() => {
              if (!selectedSlot) return;
              const after =
                slotsRef.current.find((slot) => slot.slot_key === selectedSlot.slot_key) ||
                selectedSlot;
              const before =
                lastSavedRef.current.get(after.slot_key) || copySlot(after);
              commitSlot(before, after, `form:${after.slot_key}`, true);
            }}
            onResetSelectedSlot={() => selectedSlot && void resetSlot(selectedSlot)}
            onChangeSectionProps={(props) =>
              selectedSection && saveSectionProps(selectedSection, props)
            }
            onPickMedia={() => {
              /* ImageUploadField is primary; media library optional later */
            }}
            onToggleSectionVisibility={() => void toggleVisibility()}
            onDeleteSection={(section) => {
              const target = section || selectedSection;
              if (target) void deleteSection(target);
            }}
            onPaletteAdd={onPaletteAdd}
            uploadImage={uploadSectionImage}
            onImageUploaded={(url, alt) =>
              selectedSection
                ? handleSectionImageUploaded(selectedSection, url, alt)
                : undefined
            }
          />
        </div>
        <DragOverlay dropAnimation={null}>
          {dragLabel ? <CmsDragOverlayCard label={dragLabel} type={dragType} /> : null}
        </DragOverlay>
      </DndContext>

      {pageImageEdit && api.uploadPageImage && api.updatePageImage ? (
        <PageImageEditModal
          row={pageImageEdit}
          onClose={() => setPageImageEdit(null)}
          onSaved={(result) => {
            setPageImageEdit(null);
            notify("頁面圖片已更新", "success");
            if (result?.slotKey && result.imageUrl) {
              const ok = preview.applyImageSlot(
                result.slotKey,
                result.imageUrl,
                result.imageAlt
              );
              if (!ok) hardRefreshPreview();
            } else {
              hardRefreshPreview();
            }
          }}
          uploadImage={api.uploadPageImage}
          updatePageImage={api.updatePageImage}
        />
      ) : null}
    </div>
  );
}
