import { useCallback, useEffect, useState } from "react";

import { PlayerContainer } from "@/components/ui/player-layout";
import { Button } from "@/components/ui/button-1";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ToastProvider, useToast } from "@/components/ui/toast-1";
import { cn } from "@/lib/utils";

const MAX_ROWS = 6;
const YT_ID_RE = /^[A-Za-z0-9_-]{11}$/;

export type FeaturedVideoRow = {
  url: string;
  title: string;
  label: string;
};

export type FeaturedVideoPayload = {
  enabled: boolean;
  videos?: Array<{
    youtubeId?: string;
    youtube_id?: string;
    url?: string;
    title?: string;
    label?: string;
    publishedAt?: string;
  }>;
  error?: string;
};

export type AdminFeaturedVideoEditorProps = {
  api: {
    getFeaturedVideo: () => Promise<FeaturedVideoPayload>;
    saveFeaturedVideo: (body: {
      enabled: boolean;
      videos: Array<{ url: string; title: string; label: string }>;
    }) => Promise<FeaturedVideoPayload & { ok?: boolean }>;
    syncFeaturedVideo?: () => Promise<
      FeaturedVideoPayload & { ok?: boolean; channel_url?: string }
    >;
  };
  onRendered?: () => void;
};

function emptyRow(index: number): FeaturedVideoRow {
  return { url: "", title: "", label: `品牌影片 ${index + 1}` };
}

function padRows(
  videos: FeaturedVideoPayload["videos"] | undefined,
): FeaturedVideoRow[] {
  const rows: FeaturedVideoRow[] = [];
  const list = Array.isArray(videos) ? videos : [];
  for (let i = 0; i < MAX_ROWS; i++) {
    const v = list[i];
    if (!v) {
      rows.push(emptyRow(i));
      continue;
    }
    const id = String(v.youtubeId || v.youtube_id || "").trim();
    const url = String(v.url || (id ? `https://www.youtube.com/watch?v=${id}` : "")).trim();
    rows.push({
      url,
      title: String(v.title || "").trim(),
      label: String(v.label || `品牌影片 ${i + 1}`).trim() || `品牌影片 ${i + 1}`,
    });
  }
  return rows;
}

function extractYoutubeId(value: string): string | null {
  const raw = value.trim();
  if (!raw) return null;
  if (YT_ID_RE.test(raw)) return raw;
  try {
    const withProto =
      raw.includes("://") || raw.startsWith("www.") || raw.startsWith("youtu")
        ? raw.includes("://")
          ? raw
          : `https://${raw}`
        : "";
    if (!withProto) return null;
    const u = new URL(withProto);
    const host = u.hostname.replace(/^www\./, "");
    if (host === "youtu.be" || host === "m.youtu.be") {
      const id = u.pathname.split("/").filter(Boolean)[0] || "";
      return YT_ID_RE.test(id) ? id : null;
    }
    if (host.endsWith("youtube.com") || host.endsWith("youtube-nocookie.com")) {
      const v = u.searchParams.get("v");
      if (v && YT_ID_RE.test(v)) return v;
      const parts = u.pathname.split("/").filter(Boolean);
      if (
        parts.length >= 2 &&
        ["embed", "shorts", "live", "v"].includes(parts[0]) &&
        YT_ID_RE.test(parts[1])
      ) {
        return parts[1];
      }
    }
  } catch {
    return null;
  }
  return null;
}

function posterUrl(id: string): string {
  return `https://i.ytimg.com/vi/${id}/hqdefault.jpg`;
}

function ThumbPreview({ url }: { url: string }) {
  const id = extractYoutubeId(url);
  return (
    <PlayerContainer
      className="aspect-video w-28 shrink-0 rounded-md border border-border bg-muted [--aspect-ratio:16/9]"
      style={{ aspectRatio: "16 / 9" }}
    >
      {id ? (
        <img
          src={posterUrl(id)}
          alt=""
          className="absolute inset-0 size-full object-cover"
          loading="lazy"
        />
      ) : (
        <div className="absolute inset-0 flex items-center justify-center text-[11px] text-muted-foreground">
          無預覽
        </div>
      )}
    </PlayerContainer>
  );
}

function AdminFeaturedVideoEditorInner({
  api,
  onRendered,
}: AdminFeaturedVideoEditorProps) {
  const { showToast } = useToast();
  const [enabled, setEnabled] = useState(true);
  const [rows, setRows] = useState<FeaturedVideoRow[]>(() =>
    Array.from({ length: MAX_ROWS }, (_, i) => emptyRow(i)),
  );
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [syncing, setSyncing] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.getFeaturedVideo();
      if (res.error) {
        showToast(String(res.error), "error", "top-right");
        return;
      }
      setEnabled(Boolean(res.enabled));
      setRows(padRows(res.videos));
    } finally {
      setLoading(false);
    }
  }, [api, showToast]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    onRendered?.();
  }, [onRendered, loading]);

  function updateRow(index: number, patch: Partial<FeaturedVideoRow>) {
    setRows((prev) =>
      prev.map((row, i) => (i === index ? { ...row, ...patch } : row)),
    );
  }

  function moveRow(index: number, direction: -1 | 1) {
    const next = index + direction;
    if (next < 0 || next >= MAX_ROWS) return;
    setRows((prev) => {
      const copy = [...prev];
      const tmp = copy[index];
      copy[index] = copy[next];
      copy[next] = tmp;
      return copy;
    });
  }

  function clearRow(index: number) {
    updateRow(index, emptyRow(index));
  }


  async function handleSync() {
    if (!api.syncFeaturedVideo) {
      showToast("同步功能尚未就緒", "error", "top-right");
      return;
    }
    setSyncing(true);
    try {
      const res = await api.syncFeaturedVideo();
      if (res.error || res.ok === false) {
        showToast(String(res.error || "同步失敗"), "error", "top-right");
        return;
      }
      setEnabled(Boolean(res.enabled));
      setRows(padRows(res.videos));
      showToast("已同步最新 6 支影片（先進先出）", "success", "top-right");
    } finally {
      setSyncing(false);
    }
  }

  async function handleSave() {
    const videos: Array<{ url: string; title: string; label: string }> = [];
    for (let i = 0; i < rows.length; i++) {
      const row = rows[i];
      const raw = row.url.trim();
      if (!raw) continue;
      const id = extractYoutubeId(raw);
      if (!id) {
        showToast(`第 ${i + 1} 列 YouTube 網址無效`, "error", "top-right");
        return;
      }
      videos.push({
        url: raw,
        title: row.title.trim() || `品牌影片 ${i + 1}`,
        label: row.label.trim() || row.title.trim() || `品牌影片 ${i + 1}`,
      });
    }
    if (enabled && videos.length === 0) {
      showToast("啟用時至少需要一支影片", "error", "top-right");
      return;
    }
    setSaving(true);
    try {
      const res = await api.saveFeaturedVideo({ enabled, videos });
      if (res.error || res.ok === false) {
        showToast(String(res.error || "儲存失敗"), "error", "top-right");
        return;
      }
      setEnabled(Boolean(res.enabled));
      setRows(padRows(res.videos));
      showToast("已儲存首頁品牌影片", "success", "top-right");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-3 p-1" aria-busy="true">
        <p className="text-sm text-muted-foreground">載入中…</p>
      </div>
    );
  }

  return (
    <div className="featured-video-editor space-y-5 p-1">
      <p className="adx-panel-note text-sm text-muted-foreground">
        管理首頁詩文區塊下方的品牌影片牆（最多 6 支）。貼上 YouTube 網址或 11 碼
        ID；縮圖自動取自 YouTube。儲存後請強制重新整理首頁確認。
      </p>

      <label className="flex items-center gap-2 text-sm font-medium">
        <input
          type="checkbox"
          className="size-4 accent-primary"
          checked={enabled}
          onChange={(e) => setEnabled(e.target.checked)}
        />
        啟用首頁品牌影片牆
      </label>

      <div className="space-y-4">
        {rows.map((row, index) => (
          <div
            key={index}
            className={cn(
              "grid gap-3 rounded-lg border border-border bg-background/60 p-3",
              "md:grid-cols-[auto_1fr_auto] md:items-start",
            )}
          >
            <div className="flex items-start gap-3">
              <span className="inline-flex size-7 shrink-0 items-center justify-center rounded-md bg-muted text-xs font-semibold text-muted-foreground">
                {index + 1}
              </span>
              <ThumbPreview url={row.url} />
            </div>
            <div className="grid gap-2 sm:grid-cols-3">
              <div className="space-y-1 sm:col-span-3">
                <Label htmlFor={`fv-url-${index}`}>YouTube 網址 / ID</Label>
                <Input
                  id={`fv-url-${index}`}
                  value={row.url}
                  placeholder="https://www.youtube.com/watch?v=… 或 11 碼 ID"
                  onChange={(e) => updateRow(index, { url: e.target.value })}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor={`fv-title-${index}`}>標題</Label>
                <Input
                  id={`fv-title-${index}`}
                  value={row.title}
                  placeholder="主播放器標題"
                  onChange={(e) => updateRow(index, { title: e.target.value })}
                />
              </div>
              <div className="space-y-1 sm:col-span-2">
                <Label htmlFor={`fv-label-${index}`}>縮圖標籤</Label>
                <Input
                  id={`fv-label-${index}`}
                  value={row.label}
                  placeholder={`品牌影片 ${index + 1}`}
                  onChange={(e) => updateRow(index, { label: e.target.value })}
                />
              </div>
            </div>
            <div className="flex flex-wrap gap-1.5 md:flex-col">
              <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={index === 0}
                onClick={() => moveRow(index, -1)}
              >
                上移
              </Button>
              <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={index === MAX_ROWS - 1}
                onClick={() => moveRow(index, 1)}
              >
                下移
              </Button>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={() => clearRow(index)}
              >
                清空
              </Button>
            </div>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-2 border-t border-border pt-4">
        <Button
          type="button"
          variant="primary"
          disabled={saving || syncing}
          onClick={() => void handleSave()}
        >
          {saving ? "儲存中…" : "儲存品牌影片"}
        </Button>
        <Button
          type="button"
          variant="outline"
          disabled={saving || syncing || loading || !api.syncFeaturedVideo}
          onClick={() => void handleSync()}
        >
          {syncing ? "同步中…" : "同步最新 6 支"}
        </Button>
        <Button
          type="button"
          variant="outline"
          disabled={saving || syncing || loading}
          onClick={() => void load()}
        >
          重新載入
        </Button>
      </div>
    </div>
  );
}

export default function AdminFeaturedVideoEditor(
  props: AdminFeaturedVideoEditorProps,
) {
  return (
    <ToastProvider>
      <AdminFeaturedVideoEditorInner {...props} />
    </ToastProvider>
  );
}
