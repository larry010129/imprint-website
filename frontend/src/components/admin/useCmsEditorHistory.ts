import { useCallback, useRef, useState } from "react";

export type CmsHistoryCommand = {
  label: string;
  undo: () => Promise<void>;
  redo: () => Promise<void>;
  coalesceKey?: string;
};

type HistoryEntry = CmsHistoryCommand & { recordedAt: number };

export default function useCmsEditorHistory(
  onError: (message: string) => void,
  limit = 30
) {
  const undoStack = useRef<HistoryEntry[]>([]);
  const redoStack = useRef<HistoryEntry[]>([]);
  const applying = useRef(false);
  const busyRef = useRef(false);
  const [, render] = useState(0);
  const [busy, setBusy] = useState(false);

  const update = useCallback(() => render((value) => value + 1), []);

  const record = useCallback(
    (command: CmsHistoryCommand) => {
      if (applying.current) return;
      const entry = { ...command, recordedAt: Date.now() };
      const previous = undoStack.current.at(-1);
      if (
        command.coalesceKey &&
        previous?.coalesceKey === command.coalesceKey &&
        entry.recordedAt - previous.recordedAt < 800
      ) {
        undoStack.current[undoStack.current.length - 1] = {
          ...entry,
          undo: previous.undo,
        };
      } else {
        undoStack.current.push(entry);
        if (undoStack.current.length > limit) undoStack.current.shift();
      }
      redoStack.current = [];
      update();
    },
    [limit, update]
  );

  const apply = useCallback(
    async (direction: "undo" | "redo") => {
      if (busyRef.current) return;
      const source = direction === "undo" ? undoStack.current : redoStack.current;
      const target = direction === "undo" ? redoStack.current : undoStack.current;
      const entry = source.at(-1);
      if (!entry) return;
      busyRef.current = true;
      applying.current = true;
      setBusy(true);
      try {
        await entry[direction]();
        source.pop();
        target.push(entry);
        update();
      } catch (error) {
        onError(`${direction === "undo" ? "復原" : "重做"}失敗：${String(error)}`);
      } finally {
        applying.current = false;
        busyRef.current = false;
        setBusy(false);
      }
    },
    [onError, update]
  );

  const clear = useCallback(() => {
    if (busyRef.current) return;
    undoStack.current = [];
    redoStack.current = [];
    update();
  }, [update]);

  return {
    busy,
    canUndo: undoStack.current.length > 0,
    canRedo: redoStack.current.length > 0,
    record,
    undo: () => apply("undo"),
    redo: () => apply("redo"),
    clear,
  };
}
