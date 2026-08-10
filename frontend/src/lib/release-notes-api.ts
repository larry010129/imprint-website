/** Editor-facing release-notes API helpers. */

export type ReleaseNotesDraft = {
  version: string;
  title: string;
  notes: string[];
};

export type ReleaseNotesPublished = {
  releaseId: string;
  version: string;
  title: string;
  notes: string[];
  publishedAt: string;
};

export class ReleaseNotesApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ReleaseNotesApiError";
    this.status = status;
  }
}

async function parseError(res: Response, fallback: string): Promise<string> {
  try {
    const data = (await res.json()) as { error?: string; message?: string; detail?: string };
    return data.error || data.message || data.detail || fallback;
  } catch {
    return fallback;
  }
}

export {
  notesHaveSections,
  notesToTextarea,
  parseReleaseNoteSections,
  textareaToNotes,
  type ReleaseNoteSection,
} from "@/components/admin/releaseNotesFormat";

export async function fetchReleaseNotesDraft(): Promise<ReleaseNotesDraft> {
  const res = await fetch("/api/admin/release-notes/draft", {
    credentials: "include",
  });
  if (!res.ok) {
    throw new ReleaseNotesApiError(await parseError(res, "載入草稿失敗"), res.status);
  }
  const data = (await res.json()) as { draft?: ReleaseNotesDraft };
  const draft = data.draft;
  if (!draft || typeof draft !== "object") {
    throw new ReleaseNotesApiError("草稿格式錯誤", 500);
  }
  return {
    version: String(draft.version || ""),
    title: String(draft.title || ""),
    notes: Array.isArray(draft.notes) ? draft.notes.map(String) : [],
  };
}

export async function saveReleaseNotesDraft(
  draft: ReleaseNotesDraft,
): Promise<ReleaseNotesDraft> {
  const res = await fetch("/api/admin/release-notes/draft", {
    method: "PUT",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(draft),
  });
  if (!res.ok) {
    throw new ReleaseNotesApiError(await parseError(res, "儲存草稿失敗"), res.status);
  }
  const data = (await res.json()) as { draft?: ReleaseNotesDraft };
  const saved = data.draft;
  if (!saved) {
    throw new ReleaseNotesApiError("儲存回應格式錯誤", 500);
  }
  return {
    version: String(saved.version || ""),
    title: String(saved.title || ""),
    notes: Array.isArray(saved.notes) ? saved.notes.map(String) : [],
  };
}

export async function publishReleaseNotes(): Promise<ReleaseNotesPublished> {
  const res = await fetch("/api/admin/release-notes/publish", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  if (!res.ok) {
    throw new ReleaseNotesApiError(await parseError(res, "推送發布失敗"), res.status);
  }
  const data = (await res.json()) as { published?: ReleaseNotesPublished };
  const published = data.published;
  if (!published?.releaseId) {
    throw new ReleaseNotesApiError("推送回應格式錯誤", 500);
  }
  return {
    releaseId: String(published.releaseId),
    version: String(published.version || ""),
    title: String(published.title || ""),
    notes: Array.isArray(published.notes) ? published.notes.map(String) : [],
    publishedAt: String(published.publishedAt || ""),
  };
}
