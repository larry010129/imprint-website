import type { RefObject } from "react";

export type CmsPreviewBridge = {
  hardRefresh: () => void;
  post: (payload: Record<string, unknown>) => boolean;
  syncSection: (
    sectionId: string,
    beforeId?: string | null,
    anchor?: string | null
  ) => Promise<boolean>;
  removeSection: (sectionId: string) => boolean;
  reorderSections: (sectionIds: string[]) => boolean;
  setVisible: (sectionId: string, visible: boolean) => boolean;
  selectSection: (sectionId: string | null) => void;
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

  function post(payload: Record<string, unknown>) {
    const win = iframeRef.current?.contentWindow;
    if (!win) return false;
    win.postMessage({ source: "cms-editor", ...payload }, window.location.origin);
    return true;
  }

  return {
    hardRefresh,
    post,
    async syncSection(sectionId, beforeId = null, anchor = null) {
      try {
        const res = await fetchSectionHtml(sectionId);
        if (res.error || !res.html) return false;
        const sent = post({
          type: "apply-section",
          sectionId,
          html: res.html,
          beforeId: beforeId || null,
          anchor: anchor || null,
        });
        if (!sent) return false;
        return true;
      } catch {
        return false;
      }
    },
    removeSection(sectionId) {
      return post({ type: "remove-section", sectionId });
    },
    reorderSections(sectionIds) {
      return post({ type: "reorder-sections", sectionIds });
    },
    setVisible(sectionId, visible) {
      return post({ type: "set-visible", sectionId, visible });
    },
    selectSection(sectionId) {
      post({ type: "select-section", sectionId });
    },
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
