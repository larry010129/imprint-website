import type { RefObject } from "react";

export type CmsPreviewBridge = {
  hardRefresh: () => void;
  post: (payload: Record<string, unknown>) => boolean;
  syncSection: (
    sectionId: string,
    beforeId?: string | null,
    anchor?: string | null
  ) => Promise<boolean>;
  removeSection: (sectionId: string) => Promise<boolean>;
  reorderSections: (sectionIds: string[]) => Promise<boolean>;
  setVisible: (sectionId: string, visible: boolean) => Promise<boolean>;
  selectSection: (sectionId: string | null) => void;
  focusSection: (sectionId: string) => void;
  focusAddTarget: (anchor: string, index: number) => void;
  handleAck: (payload: Record<string, unknown>) => boolean;
  showDropGaps: () => boolean;
  hideDropGaps: () => boolean;
  hoverDrop: (relativeY: number) => boolean;
  applyCopySlot: (slotKey: string, text: string, href?: string) => boolean;
  applyImageSlot: (slotKey: string, url: string, alt?: string) => boolean;
};

type FetchSectionHtml = (
  sectionId: string
) => Promise<{ html?: string; error?: string }>;

export function createCmsPreviewBridge(options: {
  iframeRef: RefObject<HTMLIFrameElement | null>;
  hardRefresh: () => void;
  fetchSectionHtml: FetchSectionHtml;
}): CmsPreviewBridge {
  const { iframeRef, hardRefresh, fetchSectionHtml } = options;
  let requestSequence = 0;
  const pending = new Map<
    string,
    { action: string; resolve: (ok: boolean) => void; timer: number }
  >();

  function post(payload: Record<string, unknown>) {
    const win = iframeRef.current?.contentWindow;
    if (!win) return false;
    win.postMessage({ source: "cms-editor", ...payload }, window.location.origin);
    return true;
  }

  function postWithAck(
    action: string,
    payload: Record<string, unknown>,
    timeoutMs = 500,
  ): Promise<boolean> {
    const requestId = `cms-${Date.now()}-${++requestSequence}`;
    return new Promise((resolve) => {
      const timer = window.setTimeout(() => {
        pending.delete(requestId);
        resolve(false);
      }, timeoutMs);
      pending.set(requestId, { action, resolve, timer });
      if (!post({ ...payload, requestId })) {
        window.clearTimeout(timer);
        pending.delete(requestId);
        resolve(false);
      }
    });
  }

  function handleAck(payload: Record<string, unknown>) {
    if (payload.type !== "preview-ack") return false;
    const requestId = String(payload.replyTo || payload.requestId || "");
    const item = pending.get(requestId);
    if (!item || (payload.action && payload.action !== item.action)) return false;
    window.clearTimeout(item.timer);
    pending.delete(requestId);
    item.resolve(payload.ok !== false);
    return true;
  }

  return {
    hardRefresh,
    post,
    async syncSection(sectionId, beforeId = null, anchor = null) {
      try {
        const res = await fetchSectionHtml(sectionId);
        if (res.error || !res.html) return false;
        return postWithAck("apply-section", {
          type: "apply-section",
          sectionId,
          html: res.html,
          beforeId: beforeId || null,
          anchor: anchor || null,
        });
      } catch {
        return false;
      }
    },
    removeSection(sectionId) {
      return postWithAck("remove-section", { type: "remove-section", sectionId });
    },
    reorderSections(sectionIds) {
      return postWithAck("reorder-sections", {
        type: "reorder-sections",
        sectionIds,
      });
    },
    setVisible(sectionId, visible) {
      return postWithAck("set-visible", {
        type: "set-visible",
        sectionId,
        visible,
      });
    },
    selectSection(sectionId) {
      post({ type: "select-section", sectionId });
    },
    focusSection(sectionId) {
      post({ type: "focus-section", sectionId });
    },
    focusAddTarget(anchor, index) {
      post({ type: "focus-add-target", anchor, index });
    },
    handleAck,
    showDropGaps() {
      return post({ type: "show-drop-gaps" });
    },
    hideDropGaps() {
      return post({ type: "hide-drop-gaps" });
    },
    hoverDrop(relativeY) {
      return post({ type: "hover-drop", relativeY });
    },
    applyCopySlot(slotKey, text, href = "") {
      return post({ type: "apply-copy-slot", slotKey, text, href });
    },
    applyImageSlot(slotKey, url, alt = "") {
      return post({ type: "apply-image-slot", slotKey, url, alt });
    },
  };
}

export async function softOrHard(
  soft: () => boolean | Promise<boolean>,
  hard: () => void,
  retries = 2
) {
  for (let attempt = 0; attempt < retries; attempt += 1) {
    try {
      if (await soft()) return;
    } catch {
      /* retry */
    }
  }
  hard();
}
