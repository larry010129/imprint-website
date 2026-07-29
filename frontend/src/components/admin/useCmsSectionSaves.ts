import { useCallback, useEffect, useRef } from "react";
import type { Dispatch, SetStateAction } from "react";

import type { CmsSection } from "@/components/admin/cmsSectionMeta";

type SaveState = {
  props: Record<string, unknown>;
  revision: number;
  timer: number | null;
  inFlight: boolean;
};

type Options = {
  updateSection: (fields: Record<string, unknown>) => Promise<{
    section?: CmsSection;
    error?: string;
  }>;
  setSections: Dispatch<SetStateAction<CmsSection[]>>;
  setMessage: Dispatch<SetStateAction<string>>;
  refreshPreview: () => void;
};

export default function useCmsSectionSaves({
  updateSection,
  setSections,
  setMessage,
  refreshPreview,
}: Options) {
  const states = useRef(new Map<string, SaveState>());
  const mounted = useRef(true);

  const flush = useCallback(
    async (sectionId: string) => {
      const state = states.current.get(sectionId);
      if (!state || state.inFlight) return;
      state.timer = null;
      state.inFlight = true;
      const sentRevision = state.revision;
      const sentProps = state.props;
      const res = await updateSection({ id: sectionId, props: sentProps });
      state.inFlight = false;
      if (!mounted.current) return;

      if (res.error || !res.section) {
        setMessage(`儲存失敗（內容仍保留）：${String(res.error || "未知錯誤")}`);
        if (state.revision !== sentRevision) {
          state.timer = window.setTimeout(() => void flush(sectionId), 0);
        }
        return;
      }
      if (state.revision !== sentRevision) {
        state.timer = window.setTimeout(() => void flush(sectionId), 0);
        return;
      }
      states.current.delete(sectionId);
      setMessage("已儲存");
      refreshPreview();
    },
    [refreshPreview, setMessage, updateSection]
  );

  const queueSave = useCallback(
    (sectionId: string, props: Record<string, unknown>) => {
      const current = states.current.get(sectionId);
      const state: SaveState = current || {
        props,
        revision: 0,
        timer: null,
        inFlight: false,
      };
      state.props = props;
      state.revision += 1;
      if (state.timer !== null) window.clearTimeout(state.timer);
      state.timer = window.setTimeout(() => void flush(sectionId), 300);
      states.current.set(sectionId, state);
      setSections((prev) =>
        prev.map((section) => (section.id === sectionId ? { ...section, props } : section))
      );
    },
    [flush, setSections]
  );

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
        if (!state.inFlight) {
          void updateSection({ id: sectionId, props: state.props });
        }
      });
    };
  }, [updateSection]);

  return { mergePending, queueSave };
}
