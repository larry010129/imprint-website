export type PublishedRelease = {
  releaseId: string;
  version: string;
  title: string;
  notes: string[];
  publishedAt: string;
};

export type ReleaseNotesResponse = {
  published: PublishedRelease | null;
  history: PublishedRelease[];
};

export const SEEN_STORAGE_KEY = "adminReleaseSeenId";
export const LONG_PRESS_MS = 3000;
export const CODE_LEN = 6;
export const CODE_CHAR_RE = /^[0-9A-Za-z]$/;

export function getSeenReleaseId(): string | null {
  try {
    return localStorage.getItem(SEEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setSeenReleaseId(releaseId: string): void {
  try {
    localStorage.setItem(SEEN_STORAGE_KEY, releaseId);
  } catch {
    /* ignore quota / private mode */
  }
}

export async function fetchReleaseNotes(): Promise<ReleaseNotesResponse> {
  const res = await fetch("/api/admin/release-notes", {
    credentials: "include",
  });
  if (!res.ok) {
    throw new Error("failed to load release notes");
  }
  return (await res.json()) as ReleaseNotesResponse;
}

export async function unlockReleaseNotes(
  code: string,
): Promise<{ ok: true } | { ok: false; error: string }> {
  const res = await fetch("/api/admin/release-notes/unlock", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code }),
  });
  if (res.ok) return { ok: true };
  let error = "通行碼錯誤";
  try {
    const data = (await res.json()) as { error?: string; message?: string };
    error = data.error || data.message || error;
  } catch {
    /* keep default */
  }
  return { ok: false, error };
}

export type ReleaseNotesDraft = {
  version: string;
  title: string;
  notes: string[];
};

export class ReleaseNotesApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ReleaseNotesApiError";
    this.status = status;
  }
}

async function parseJson(res: Response): Promise<Record<string, unknown>> {
  try {
    return (await res.json()) as Record<string, unknown>;
  } catch {
    return {};
  }
}

function errorMessage(body: Record<string, unknown>, fallback: string): string {
  const detail = body.detail ?? body.error ?? body.message;
  if (typeof detail === "string" && detail.trim()) return detail.trim();
  return fallback;
}

function normalizeDraft(raw: Partial<ReleaseNotesDraft> | undefined, fallback?: ReleaseNotesDraft): ReleaseNotesDraft {
  return {
    version: String(raw?.version ?? fallback?.version ?? ""),
    title: String(raw?.title ?? fallback?.title ?? ""),
    notes: Array.isArray(raw?.notes)
      ? raw.notes.map((n) => String(n ?? ""))
      : (fallback?.notes ?? []),
  };
}

function normalizePublished(raw: Partial<PublishedRelease> | undefined): PublishedRelease {
  return {
    releaseId: String(raw?.releaseId ?? ""),
    version: String(raw?.version ?? ""),
    title: String(raw?.title ?? ""),
    notes: Array.isArray(raw?.notes) ? raw.notes.map((n) => String(n ?? "")) : [],
    publishedAt: String(raw?.publishedAt ?? ""),
  };
}

export async function fetchReleaseNotesDraft(): Promise<ReleaseNotesDraft> {
  const res = await fetch("/api/admin/release-notes/draft", {
    credentials: "include",
  });
  const body = await parseJson(res);
  if (!res.ok) {
    throw new ReleaseNotesApiError(res.status, errorMessage(body, "無法載入草稿"));
  }
  return normalizeDraft((body.draft ?? body) as Partial<ReleaseNotesDraft>);
}

export async function saveReleaseNotesDraft(
  draft: ReleaseNotesDraft,
): Promise<ReleaseNotesDraft> {
  const res = await fetch("/api/admin/release-notes/draft", {
    method: "PUT",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      version: draft.version,
      title: draft.title,
      notes: draft.notes,
    }),
  });
  const body = await parseJson(res);
  if (!res.ok) {
    throw new ReleaseNotesApiError(res.status, errorMessage(body, "儲存草稿失敗"));
  }
  return normalizeDraft((body.draft ?? body) as Partial<ReleaseNotesDraft>, draft);
}

export async function publishReleaseNotes(): Promise<PublishedRelease> {
  const res = await fetch("/api/admin/release-notes/publish", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  const body = await parseJson(res);
  if (!res.ok) {
    throw new ReleaseNotesApiError(res.status, errorMessage(body, "推送發布失敗"));
  }
  return normalizePublished((body.published ?? body) as Partial<PublishedRelease>);
}

export function notesToTextarea(notes: string[]): string {
  return notes.join("\n");
}

export function textareaToNotes(value: string): string[] {
  return value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}
