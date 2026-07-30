import type { Dispatch, SetStateAction } from "react";
import { arrayMove } from "@dnd-kit/sortable";

import type {
  CmsPage,
  CmsSection,
  CmsSectionType,
} from "@/components/admin/cmsSectionMeta";
import {
  buildOrderWithAnchor,
  sectionAnchor,
  sectionLabel,
} from "@/components/admin/cmsSectionMeta";
import type { CmsPreviewBridge } from "@/components/admin/cmsPreviewBridge";
import { softOrHard } from "@/components/admin/cmsPreviewBridge";
import type { CmsHistoryCommand } from "@/components/admin/useCmsEditorHistory";
import {
  removeSectionPageImage,
  type SyncSectionPageImageApi,
} from "@/components/admin/syncSectionPageImage";

export type SectionRef = { key: string; currentId: string };

export type AddSectionTarget =
  | number
  | {
      anchor?: string;
      /** Local index within the anchor host (append when omitted / Infinity). */
      index?: number;
    };

type Api = {
  createSection: (
    pageId: string,
    body: { type: string; props?: Record<string, unknown> }
  ) => Promise<{ section?: CmsSection; error?: string }>;
  updateSection: (
    fields: Record<string, unknown>
  ) => Promise<{ section?: CmsSection; error?: string }>;
  sectionAction: (
    id: string,
    action: string
  ) => Promise<{ ok?: boolean; error?: string }>;
  reorderSections: (
    pageId: string,
    ids: string[]
  ) => Promise<{ sections?: CmsSection[]; error?: string }>;
} & SyncSectionPageImageApi;

type Options = {
  page: CmsPage | null;
  /** Host page route for page_images sync (site route or /p/slug). */
  pageKey?: string;
  sections: CmsSection[];
  selected: CmsSection | null;
  api: Api;
  setSections: Dispatch<SetStateAction<CmsSection[]>>;
  setSelectedId: Dispatch<SetStateAction<string | null>>;
  setBusy: Dispatch<SetStateAction<boolean>>;
  getSectionRef: (id: string) => SectionRef;
  registerSectionRef: (id: string, reference: SectionRef) => void;
  prepareSection: (id: string) => Promise<void>;
  /** When set, mid-insert only flushes sections that still have pending props. */
  pendingSectionIds?: () => string[];
  record: (command: CmsHistoryCommand) => void;
  notify: (
    message: string,
    type?: "success" | "error" | "warning" | "info"
  ) => void;
  preview: CmsPreviewBridge;
};

export function copyCmsProps(props: Record<string, unknown>) {
  return JSON.parse(JSON.stringify(props)) as Record<string, unknown>;
}

function resolveAddTarget(
  sections: CmsSection[],
  target: AddSectionTarget
): { anchor: string; localIndex: number } {
  if (typeof target === "number") {
    const insertAt = Math.max(0, Math.min(Math.floor(target), sections.length));
    if (insertAt >= sections.length) {
      const last = sections[sections.length - 1];
      return {
        anchor: last ? sectionAnchor(last) : "end",
        localIndex: Number.POSITIVE_INFINITY,
      };
    }
    const neighbor = sections[insertAt];
    const anchor = sectionAnchor(neighbor);
    const group = sections.filter((section) => sectionAnchor(section) === anchor);
    const at = group.findIndex((section) => section.id === neighbor.id);
    return { anchor, localIndex: at >= 0 ? at : group.length };
  }
  const anchor = String(target.anchor || "end").trim().toLowerCase() || "end";
  const raw = target.index;
  const localIndex =
    raw == null || !Number.isFinite(raw)
      ? Number.POSITIVE_INFINITY
      : Math.max(0, Math.floor(raw));
  return { anchor, localIndex };
}

export default function useCmsEditorCommands(options: Options) {
  const {
    page,
    pageKey = "",
    sections,
    selected,
    api,
    setSections,
    setSelectedId,
    setBusy,
    getSectionRef,
    registerSectionRef,
    prepareSection,
    pendingSectionIds,
    record,
    notify,
    preview,
  } = options;

  async function flushPendingOnly(ids: string[]) {
    const targets = pendingSectionIds
      ? ids.filter((id) => pendingSectionIds().includes(id))
      : ids;
    await Promise.all(targets.map((id) => prepareSection(id)));
  }

  async function applyOrder(order: SectionRef[]) {
    if (!page) throw new Error("頁面尚未載入");
    await flushPendingOnly(order.map((reference) => reference.currentId));
    const ids = order.map((reference) => reference.currentId);
    const res = await api.reorderSections(page.id, ids);
    if (res.error || !res.sections) throw new Error(String(res.error || "排序儲存失敗"));
    setSections(res.sections);
    await softOrHard(() => preview.reorderSections(ids), preview.hardRefresh);
  }

  async function cleanupPageImage(sectionId: string) {
    if (!api.removeSectionPageImage) return;
    await removeSectionPageImage(api, { pageKey: pageKey || undefined, sectionId });
  }

  async function deletePersisted(reference: SectionRef) {
    await prepareSection(reference.currentId);
    const res = await api.sectionAction(reference.currentId, "delete");
    if (res.error) throw new Error(String(res.error));
    void cleanupPageImage(reference.currentId);
    setSections((current) =>
      current.filter((section) => section.id !== reference.currentId)
    );
    setSelectedId((current) => (current === reference.currentId ? null : current));
    await softOrHard(
      () => preview.removeSection(reference.currentId),
      preview.hardRefresh
    );
  }

  async function recreate(
    snapshot: CmsSection,
    reference: SectionRef,
    order: SectionRef[]
  ) {
    if (!page) throw new Error("頁面尚未載入");
    const created = await api.createSection(page.id, {
      type: snapshot.type,
      props: copyCmsProps(snapshot.props),
    });
    if (created.error || !created.section) {
      throw new Error(String(created.error || "區塊重建失敗"));
    }
    const newId = created.section.id;
    try {
      const updated = await api.updateSection({
        id: newId,
        props: copyCmsProps(snapshot.props),
        isVisible: snapshot.is_visible,
      });
      if (updated.error || !updated.section) {
        throw new Error(String(updated.error || "區塊內容還原失敗"));
      }
      await flushPendingOnly(
        order.filter((item) => item !== reference).map((item) => item.currentId)
      );
      const ids = order.map((item) => (item === reference ? newId : item.currentId));
      const reordered = await api.reorderSections(page.id, ids);
      if (reordered.error || !reordered.sections) {
        throw new Error(String(reordered.error || "區塊位置還原失敗"));
      }
      reference.currentId = newId;
      registerSectionRef(newId, reference);
      setSections(reordered.sections);
      setSelectedId(newId);
      const index = ids.indexOf(newId);
      const beforeId = index >= 0 && index < ids.length - 1 ? ids[index + 1] : null;
      const anchor = sectionAnchor(updated.section);
      await softOrHard(async () => {
        const synced = await preview.syncSection(newId, beforeId, anchor);
        if (synced) preview.reorderSections(ids);
        return synced;
      }, preview.hardRefresh);
    } catch (error) {
      await api.sectionAction(newId, "delete");
      throw error;
    }
  }

  async function addSection(
    type: CmsSectionType,
    target: AddSectionTarget = sections.length
  ) {
    if (!page) return;
    setBusy(true);
    try {
      const { anchor, localIndex } = resolveAddTarget(sections, target);
      const res = await api.createSection(page.id, {
        type,
        props: { anchor },
      });
      if (res.error || !res.section) throw new Error(String(res.error || "新增失敗"));

      const created: CmsSection = {
        ...res.section,
        props: { ...res.section.props, anchor },
      };
      const next = buildOrderWithAnchor(sections, created, anchor, localIndex);
      const nextIds = next.map((item) => item.id);
      const appendOnly =
        nextIds.length === sections.length + 1 &&
        nextIds[nextIds.length - 1] === created.id &&
        nextIds.slice(0, -1).every((id, i) => id === sections[i]?.id);
      let persisted = next;
      if (!appendOnly) {
        try {
          await flushPendingOnly(sections.map((item) => item.id));
          const reordered = await api.reorderSections(page.id, nextIds);
          if (reordered.error || !reordered.sections) {
            throw new Error(String(reordered.error || "插入位置儲存失敗"));
          }
          persisted = reordered.sections;
        } catch (error) {
          await api.sectionAction(res.section.id, "delete");
          throw error;
        }
      }
      const snapshot = persisted.find((item) => item.id === res.section!.id) || created;
      const reference = getSectionRef(res.section.id);
      const order = persisted.map((item) => getSectionRef(item.id));
      setSections(persisted);
      setSelectedId(res.section.id);
      record({
        label: "新增區塊",
        undo: () => deletePersisted(reference),
        redo: () => recreate(snapshot, reference, order),
      });
      notify(`已新增「${sectionLabel(type)}」區塊`, "success");
      const persistedIndex = persisted.findIndex((item) => item.id === res.section!.id);
      const beforeId =
        persistedIndex >= 0 && persistedIndex < persisted.length - 1
          ? persisted[persistedIndex + 1]?.id || null
          : null;
      // Prefer next sibling in same anchor host for soft insert position.
      const sameAnchorBefore =
        persisted
          .slice(persistedIndex + 1)
          .find((item) => sectionAnchor(item) === anchor)?.id || null;
      const sectionId = res.section.id;
      await softOrHard(async () => {
        const synced = await preview.syncSection(
          sectionId,
          sameAnchorBefore || beforeId,
          anchor
        );
        if (synced && !appendOnly) {
          preview.reorderSections(persisted.map((item) => item.id));
        }
        return synced;
      }, preview.hardRefresh);
      preview.selectSection(sectionId);
    } catch (error) {
      notify(String(error), "error");
    } finally {
      setBusy(false);
    }
  }

  async function deleteSection(section: CmsSection) {
    const snapshot = { ...section, props: copyCmsProps(section.props) };
    const reference = getSectionRef(section.id);
    const order = sections.map((item) => getSectionRef(item.id));
    setBusy(true);
    try {
      await deletePersisted(reference);
      record({
        label: "刪除區塊",
        undo: () => recreate(snapshot, reference, order),
        redo: () => deletePersisted(reference),
      });
      notify("區塊已刪除", "success");
    } catch (error) {
      notify(String(error), "error");
    } finally {
      setBusy(false);
    }
  }

  async function reorder(oldIndex: number, newIndex: number) {
    const before = sections.map((item) => getSectionRef(item.id));
    const after = arrayMove(before, oldIndex, newIndex);
    setBusy(true);
    try {
      await applyOrder(after);
      record({
        label: "排序區塊",
        undo: () => applyOrder(before),
        redo: () => applyOrder(after),
      });
      notify("區塊順序已更新", "success");
    } catch (error) {
      notify(String(error), "error");
    } finally {
      setBusy(false);
    }
  }

  async function toggleVisibility() {
    if (!selected) return;
    const reference = getSectionRef(selected.id);
    const before = selected.is_visible;
    const apply = async (isVisible: boolean) => {
      await prepareSection(reference.currentId);
      const res = await api.updateSection({ id: reference.currentId, isVisible });
      if (res.error || !res.section) throw new Error(String(res.error || "顯示設定失敗"));
      setSections((current) =>
        current.map((item) => (item.id === reference.currentId ? res.section! : item))
      );
      await softOrHard(
        () => preview.setVisible(reference.currentId, isVisible),
        preview.hardRefresh
      );
    };
    setBusy(true);
    try {
      await apply(!before);
      record({
        label: "切換區塊顯示",
        undo: () => apply(before),
        redo: () => apply(!before),
      });
      notify(before ? "區塊已隱藏" : "區塊已顯示", "success");
    } catch (error) {
      notify(String(error), "error");
    } finally {
      setBusy(false);
    }
  }

  return { addSection, deleteSection, reorder, toggleVisibility };
}
