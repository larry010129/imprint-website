import { useEffect, useRef, useState } from "react";

import ReleaseNotesStaffDialog from "@/components/admin/ReleaseNotesStaffDialog";
import ReleaseNotesUnlock from "@/components/admin/ReleaseNotesUnlock";
import {
  LONG_PRESS_MS,
  fetchReleaseNotes,
  getSeenReleaseId,
  setSeenReleaseId,
  type PublishedRelease,
} from "@/components/admin/releaseNotesApi";

export type ReleaseNotesGateProps = {
  /** Sidebar credit button id (default: adminReleaseNotesCredit) */
  creditId?: string;
};

/**
 * Credit long-press (3s) → OTP unlock; short click / unread published → staff Dialog.
 */
export default function ReleaseNotesGate({
  creditId = "adminReleaseNotesCredit",
}: ReleaseNotesGateProps) {
  const [published, setPublished] = useState<PublishedRelease | null>(null);
  const [staffOpen, setStaffOpen] = useState(false);
  const [unlockOpen, setUnlockOpen] = useState(false);
  const longFiredRef = useRef(false);
  const timerRef = useRef<number | null>(null);
  const pointerIdRef = useRef<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const data = await fetchReleaseNotes();
        if (cancelled) return;
        const pub = data.published ?? null;
        setPublished(pub);
        if (pub?.releaseId && pub.releaseId !== getSeenReleaseId()) {
          setStaffOpen(true);
        }
      } catch {
        /* admin session / API not ready — silent */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const node = document.getElementById(creditId);
    if (!node) return;
    const credit: HTMLElement = node;

    function clearTimer() {
      if (timerRef.current != null) {
        window.clearTimeout(timerRef.current);
        timerRef.current = null;
      }
      credit.classList.remove("is-holding");
    }

    function onPointerDown(e: PointerEvent) {
      if (e.button != null && e.button !== 0) return;
      longFiredRef.current = false;
      pointerIdRef.current = e.pointerId;
      try {
        credit.setPointerCapture(e.pointerId);
      } catch {
        /* ignore */
      }
      credit.classList.add("is-holding");
      clearTimer();
      timerRef.current = window.setTimeout(() => {
        longFiredRef.current = true;
        credit.classList.remove("is-holding");
        setUnlockOpen(true);
        timerRef.current = null;
      }, LONG_PRESS_MS);
    }

    function onPointerEnd(e: PointerEvent) {
      if (
        pointerIdRef.current != null &&
        e.pointerId !== pointerIdRef.current
      ) {
        return;
      }
      clearTimer();
      pointerIdRef.current = null;
      try {
        credit.releasePointerCapture(e.pointerId);
      } catch {
        /* ignore */
      }
    }

    function onClick(e: MouseEvent) {
      if (longFiredRef.current) {
        e.preventDefault();
        e.stopPropagation();
        longFiredRef.current = false;
        return;
      }
      e.preventDefault();
      void (async () => {
        try {
          const data = await fetchReleaseNotes();
          setPublished(data.published ?? null);
        } catch {
          /* keep last known published */
        }
        setStaffOpen(true);
      })();
    }

    function onContextMenu(e: Event) {
      e.preventDefault();
    }

    credit.addEventListener("pointerdown", onPointerDown);
    credit.addEventListener("pointerup", onPointerEnd);
    credit.addEventListener("pointercancel", onPointerEnd);
    credit.addEventListener("pointerleave", onPointerEnd);
    credit.addEventListener("click", onClick);
    credit.addEventListener("contextmenu", onContextMenu);

    return () => {
      clearTimer();
      credit.removeEventListener("pointerdown", onPointerDown);
      credit.removeEventListener("pointerup", onPointerEnd);
      credit.removeEventListener("pointercancel", onPointerEnd);
      credit.removeEventListener("pointerleave", onPointerEnd);
      credit.removeEventListener("click", onClick);
      credit.removeEventListener("contextmenu", onContextMenu);
    };
  }, [creditId]);

  function handleDismiss(releaseId: string) {
    setSeenReleaseId(releaseId);
  }

  return (
    <>
      <ReleaseNotesStaffDialog
        open={staffOpen}
        onOpenChange={setStaffOpen}
        release={published}
        onDismiss={handleDismiss}
      />
      <ReleaseNotesUnlock open={unlockOpen} onOpenChange={setUnlockOpen} />
    </>
  );
}
