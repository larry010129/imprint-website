import { useCallback, useEffect, useRef } from "react";
import type { Dispatch, SetStateAction } from "react";

import { softOrHard } from "@/components/admin/cmsPreviewBridge";
import type { CmsSection } from "@/components/admin/cmsSectionMeta";

type SaveState = {
  props: Record<string, unknown>;
  revision: number;
  timer: number | null;
  inFlight: Promise<boolean> | null;
  /** True when iframe contenteditable already shows the new text. */
  skipPreview: boolean;
};

type Options = {
  updateSection: (fields: Record<string, unknown>) => Promise<{
    section?: CmsSection;
    error?: string;
  }>;
  setSections: Dispatch<SetStateAction<CmsSection[]>>;
  setMessage: Dispatch<SetStateAction<string>>;
  /** Soft-patch preview for this section; return false to signal hard refresh needed. */
  onSectionSaved?: (sectionId: string) => boolean | Promise<boolean>;
  hardRefreshPreview?: () => void;
};

export default function useCmsSectionSaves({
  updateSection,
  setSections,
  setMessage,
  onSectionSaved,
  hardRefreshPreview,
}: Options) {
  const states = useRef(new Map<string, SaveState>());
  const mounted = useRef(true);
  const onSavedRef = useRef(onSectionSaved);
  const hardRef = useRef(hardRefreshPreview);
  onSavedRef.current = onSectionSaved;
  hardRef.current = hardRefreshPreview;

  const flush = useCallback(
    async (sectionId: string): Promise<boolean> => {
      const state = states.current.get(sectionId);
      if (!state) return true;
      if (state.inFlight) return state.inFlight;
      state.timer = null;
      const sentRevision = state.revision;
      const sentProps = state.props;
      const request = (async () => {
        try {
          const res = await updateSection({ id: sectionId, props: sentProps });
          if (!mounted.current) return false;
          if (res.error || !res.section) {
            setMessage(`儲存失敗（內容仍保留）：${String(res.error || "未知錯誤")}`);
            if (state.revision !== sentRevision) {
              state.timer = window.setTimeout(() => void flush(sectionId), 0);
            }
            return false;
          }
          if (state.revision !== sentRevision) {
            state.timer = window.setTimeout(() => void flush(sectionId), 0);
            return true;
          }
          const skipPreview = state.skipPreview;
          states.current.delete(sectionId);
          setMessage("已儲存");
          if (!skipPreview) {
            if (onSavedRef.current) {
              await softOrHard(
                () => onSavedRef.current!(sectionId),
                () => hardRef.current?.()
              );
            } else {
              hardRef.current?.();
            }
          }
          return true;
        } catch (error) {
          if (mounted.current) {
            setMessage(`儲存失敗（內容仍保留）：${String(error)}`);
          }
          return false;
        }
      })();
      state.inFlight = request;
      try {
        return await request;
      } finally {
        state.inFlight = null;
      }
    },
    [setMessage, updateSection]
  );

  const queueSave = useCallback(
    (
      sectionId: string,
      props: Record<string, unknown>,
      options?: { skipPreview?: boolean }
    ) => {
      const current = states.current.get(sectionId);
      const state: SaveState = current || {
        props,
        revision: 0,
        timer: null,
        inFlight: null,
        skipPreview: false,
      };
      state.props = props;
      state.revision += 1;
      // Once a form edit needs a patch, keep patching even if a later inline save arrives.
      if (options?.skipPreview) {
        if (!current) state.skipPreview = true;
      } else {
        state.skipPreview = false;
      }
      if (state.timer !== null) window.clearTimeout(state.timer);
      state.timer = window.setTimeout(() => void flush(sectionId), 300);
      states.current.set(sectionId, state);
      setSections((prev) =>
        prev.map((section) => (section.id === sectionId ? { ...section, props } : section))
      );
    },
    [flush, setSections]
  );

  const flushPending = useCallback(
    async (sectionId: string): Promise<boolean> => {
      let state = states.current.get(sectionId);
      if (!state) return true;
      const activeRequest = state.inFlight;
      const activeRevision = state.revision;
      if (state.timer !== null) {
        window.clearTimeout(state.timer);
        state.timer = null;
      }
      const activeSucceeded = activeRequest ? await activeRequest : true;
      state = states.current.get(sectionId);
      if (!state) return activeSucceeded;
      if (activeRequest && state.revision === activeRevision) return activeSucceeded;
      if (state.timer !== null) window.clearTimeout(state.timer);
      state.timer = null;
      return flush(sectionId);
    },
    [flush]
  );

  const discardPending = useCallback((sectionId: string) => {
    const state = states.current.get(sectionId);
    if (state?.timer !== null && state?.timer !== undefined) {
      window.clearTimeout(state.timer);
    }
    states.current.delete(sectionId);
  }, []);

  const hasPending = useCallback((sectionId: string) => states.current.has(sectionId), []);

  const pendingIds = useCallback(() => [...states.current.keys()], []);

  const mergePending = useCallback((incoming: CmsSection[]) => {
    return incoming.map((section) => {
      const state = states.current.get(section.id);
      return state ? { ...section, props: state.props } : section;
    });
  }, []);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      states.current.forEach((state, sectionId) => {
        if (state.timer !== null) window.clearTimeout(state.timer);
        if (state.inFlight === null) {
          void updateSection({ id: sectionId, props: state.props });
        }
      });
    };
  }, [updateSection]);

  return { discardPending, flushPending, hasPending, mergePending, pendingIds, queueSave };
}
