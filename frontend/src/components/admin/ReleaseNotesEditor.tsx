import { useEffect, useState } from "react";

import ReleaseNotesStaffDialog from "@/components/admin/ReleaseNotesStaffDialog";
import {
  fetchReleaseNotesDraft,
  notesToTextarea,
  publishReleaseNotes,
  ReleaseNotesApiError,
  saveReleaseNotesDraft,
  setSeenReleaseId,
  textareaToNotes,
  type PublishedRelease,
} from "@/components/admin/releaseNotesApi";
import { Button } from "@/components/ui/button-1";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

function isUnlockMissing(err: unknown): boolean {
  return err instanceof ReleaseNotesApiError && (err.status === 401 || err.status === 403);
}

function redirectToAdmin(): void {
  window.location.replace("/admin");
}

export type ReleaseNotesEditorProps = {
  className?: string;
};

export default function ReleaseNotesEditor({ className }: ReleaseNotesEditorProps) {
  const [version, setVersion] = useState("");
  const [title, setTitle] = useState("");
  const [notesText, setNotesText] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [statusMsg, setStatusMsg] = useState("");
  const [statusTone, setStatusTone] = useState<"neutral" | "ok" | "err">("neutral");
  const [previewOpen, setPreviewOpen] = useState(false);
  const [published, setPublished] = useState<PublishedRelease | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const draft = await fetchReleaseNotesDraft();
        if (cancelled) return;
        setVersion(draft.version);
        setTitle(draft.title);
        setNotesText(notesToTextarea(draft.notes));
        setStatusMsg("");
        setStatusTone("neutral");
      } catch (err) {
        if (cancelled) return;
        if (isUnlockMissing(err)) {
          redirectToAdmin();
          return;
        }
        setStatusTone("err");
        setStatusMsg(err instanceof Error ? err.message : "載入失敗");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleSaveDraft() {
    setSaving(true);
    setStatusMsg("");
    setStatusTone("neutral");
    try {
      const saved = await saveReleaseNotesDraft({
        version: version.trim(),
        title: title.trim(),
        notes: textareaToNotes(notesText),
      });
      setVersion(saved.version);
      setTitle(saved.title);
      setNotesText(notesToTextarea(saved.notes));
      setStatusTone("ok");
      setStatusMsg("草稿已儲存");
    } catch (err) {
      if (isUnlockMissing(err)) {
        redirectToAdmin();
        return;
      }
      setStatusTone("err");
      setStatusMsg(err instanceof Error ? err.message : "儲存草稿失敗");
    } finally {
      setSaving(false);
    }
  }

  async function handlePublish() {
    setPublishing(true);
    setStatusMsg("");
    setStatusTone("neutral");
    try {
      await saveReleaseNotesDraft({
        version: version.trim(),
        title: title.trim(),
        notes: textareaToNotes(notesText),
      });
      const result = await publishReleaseNotes();
      setPublished(result);
      if (result.releaseId) setSeenReleaseId(result.releaseId);
      setPreviewOpen(true);
      setStatusTone("ok");
      setStatusMsg("已推送");
    } catch (err) {
      if (isUnlockMissing(err)) {
        redirectToAdmin();
        return;
      }
      setStatusTone("err");
      setStatusMsg(err instanceof Error ? err.message : "推送發布失敗");
    } finally {
      setPublishing(false);
    }
  }

  const busy = loading || saving || publishing;

  return (
    <div className={cn("w-full space-y-5", className)}>
      <div className="space-y-1">
        <h2 className="text-xl font-semibold tracking-tight text-foreground">
          版本更新筆記
        </h2>
        <p className="text-sm text-muted-foreground">
          編輯草稿後可儲存或推送發布。推送後其他管理員進入後台會看到更新內容。
        </p>
      </div>

      <div className="grid w-full gap-5 lg:grid-cols-[minmax(0,320px)_minmax(0,1fr)]">
        <div className="space-y-4 rounded-lg border border-border bg-background/60 p-5">
          <div className="space-y-2">
            <Label htmlFor="rn-version">版本</Label>
            <Input
              id="rn-version"
              value={version}
              onChange={(e) => setVersion(e.target.value)}
              placeholder="例如 1.2.0"
              disabled={busy}
              autoComplete="off"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="rn-title">標題</Label>
            <Input
              id="rn-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="本次更新標題"
              disabled={busy}
              autoComplete="off"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2 pt-1">
            <Button
              type="button"
              variant="outline"
              disabled={busy}
              onClick={() => void handleSaveDraft()}
            >
              {saving ? "儲存中…" : "儲存草稿"}
            </Button>
            <Button
              type="button"
              variant="primary"
              disabled={busy}
              onClick={() => void handlePublish()}
            >
              {publishing ? "推送中…" : "推送發布"}
            </Button>
            <a
              href="/admin"
              className="text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
            >
              返回後台
            </a>
          </div>

          <p
            className={cn(
              "min-h-[1.25rem] text-sm",
              statusTone === "ok" && "text-emerald-700 dark:text-emerald-400",
              statusTone === "err" && "text-destructive",
              statusTone === "neutral" && "text-muted-foreground",
            )}
            role="status"
            aria-live="polite"
          >
            {loading ? "載入中…" : statusMsg}
          </p>
        </div>

        <div className="space-y-2 rounded-lg border border-border bg-background/60 p-5">
          <Label htmlFor="rn-notes">更新內容</Label>
          <Textarea
            id="rn-notes"
            value={notesText}
            onChange={(e) => setNotesText(e.target.value)}
            placeholder={
              "## 商店 / 訂單\n- 修正項鍊長度驗證\n- 結帳頁載入錯誤已修\n\n## 後台管理\n- 內容編輯頁載入加速"
            }
            disabled={busy}
            rows={22}
            className="min-h-[26rem] w-full font-sans"
          />
          <p className="text-xs text-muted-foreground">
            用 <code className="rounded bg-muted px-1">## 分類標題</code> 分段；
            項目行前加 <code className="rounded bg-muted px-1">-</code>；
            分類之間空一行。
          </p>
        </div>
      </div>

      <ReleaseNotesStaffDialog
        open={previewOpen}
        onOpenChange={setPreviewOpen}
        release={published}
        onDismiss={setSeenReleaseId}
      />
    </div>
  );
}
