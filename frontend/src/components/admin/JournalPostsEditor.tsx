import { useEffect, useState } from "react";

import { useToast } from "@/components/ui/toast-1";
import { ImageUploadField } from "@/components/ui/image-upload";

export type JournalPost = {
  id: string;
  title: string;
  body: string;
  posted_at: string;
  image_url?: string | null;
  is_archived: boolean;
  is_published: boolean;
};

export type JournalPostsApi = {
  getJournalPosts: (options?: Record<string, unknown>) => Promise<{
    posts?: JournalPost[];
    error?: string;
  }>;
  createJournalPost: (fields: Record<string, unknown>) => Promise<{
    post?: JournalPost;
    error?: string;
  }>;
  updateJournalPost: (fields: Record<string, unknown>) => Promise<{
    post?: JournalPost;
    error?: string;
  }>;
  journalPostAction: (id: string, action: "publish" | "unpublish" | "delete") => Promise<{
    ok?: boolean;
    error?: string;
  }>;
  uploadPageImage: (file: File, pageKey?: string) => Promise<{
    url?: string;
    error?: string | { message?: string };
  }>;
};

type Draft = Omit<JournalPost, "id"> & { id?: string };

const emptyDraft = (): Draft => ({
  title: "",
  body: "",
  posted_at: new Date().toISOString().slice(0, 10),
  image_url: "",
  is_archived: false,
  is_published: true,
});

function draftFromPost(post: JournalPost): Draft {
  return {
    id: post.id,
    title: post.title || "",
    body: post.body || "",
    posted_at: String(post.posted_at || "").slice(0, 10),
    image_url: post.image_url || "",
    is_archived: Boolean(post.is_archived),
    is_published: Boolean(post.is_published),
  };
}

export default function JournalPostsEditor({ api }: { api: JournalPostsApi }) {
  const { showToast } = useToast();
  const [posts, setPosts] = useState<JournalPost[]>([]);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [imagePending, setImagePending] = useState(false);
  const [imageFieldKey, setImageFieldKey] = useState(0);

  const load = async () => {
    setLoading(true);
    const result = await api.getJournalPosts({ page: 1, pageSize: 100 });
    if (result.error) setError(String(result.error));
    else {
      setError(null);
      setPosts(result.posts || []);
    }
    setLoading(false);
  };

  useEffect(() => {
    void load();
  }, [api]);

  const setField = <K extends keyof Draft>(field: K, value: Draft[K]) => {
    setDraft((current) => ({ ...(current || emptyDraft()), [field]: value }));
  };

  const save = async () => {
    if (!draft?.title.trim() || !draft.posted_at) {
      setError("請填寫標題與日期");
      return;
    }
    // Soft: pending crop/file never wrote image_url — keep prior/empty and remount picker.
    if (imagePending) {
      showToast(
        draft.image_url ? "尚未確認裁切，將使用原圖" : "尚未確認裁切，將使用空白圖片",
        "warning",
        "top-right",
      );
      setImagePending(false);
      setImageFieldKey((key) => key + 1);
    }
    setSaving(true);
    const payload = {
      id: draft.id,
      title: draft.title.trim(),
      body: draft.body.trim(),
      posted_at: draft.posted_at,
      image_url: String(draft.image_url || "").trim() || null,
      is_archived: draft.is_archived,
      is_published: draft.is_published,
    };
    const result = draft.id
      ? await api.updateJournalPost(payload)
      : await api.createJournalPost(payload);
    setSaving(false);
    if (result.error || !result.post) {
      setError(String(result.error || "文章儲存失敗"));
      return;
    }
    setPosts((current) => {
      const exists = current.some((post) => post.id === result.post!.id);
      return exists
        ? current.map((post) => post.id === result.post!.id ? result.post! : post)
        : [result.post!, ...current];
    });
    setDraft(null);
    setError(null);
    showToast("日誌文章已儲存", "success", "top-right");
  };

  const action = async (post: JournalPost, next: "publish" | "unpublish" | "delete") => {
    if (next === "delete" && !window.confirm("確定要刪除此文章嗎？")) return;
    const result = await api.journalPostAction(post.id, next);
    if (result.error) {
      showToast(String(result.error), "error", "top-right");
      return;
    }
    if (next === "delete") setPosts((current) => current.filter((item) => item.id !== post.id));
    else setPosts((current) => current.map((item) => item.id === post.id ? { ...item, is_published: next === "publish" } : item));
  };

  return (
    <div className="cms-copy-group cms-journal-editor">
      <div className="cms-copy-card__header">
        <div>
          <h3 className="cms-copy-group__title">日誌文章</h3>
          <p className="cms-hint">新增或編輯會直接更新 /journal 的文章列表。</p>
        </div>
        <button type="button" className="btn-sm btn-primary" onClick={() => {
          setDraft(emptyDraft());
          setError(null);
          setImagePending(false);
          setImageFieldKey((key) => key + 1);
        }}>
          新增文章
        </button>
      </div>
      {error ? <p className="cms-msg cms-msg--error">{error}</p> : null}
      {draft ? (
        <article className="cms-copy-card">
          <h4>{draft.id ? "編輯日誌文章" : "新增日誌文章"}</h4>
          <label className="cms-field"><span>標題</span><input value={draft.title} maxLength={200} onChange={(event) => setField("title", event.target.value)} /></label>
          <label className="cms-field"><span>日期</span><input type="date" value={draft.posted_at} onChange={(event) => setField("posted_at", event.target.value)} /></label>
          <label className="cms-field"><span>內文</span><textarea rows={8} value={draft.body} onChange={(event) => setField("body", event.target.value)} /></label>
          <ImageUploadField
            key={imageFieldKey}
            label="文章圖片（選填）"
            value={String(draft.image_url || "")}
            targetW={1200}
            targetH={800}
            onChange={(url) => setField("image_url", url)}
            onUpload={(file) => api.uploadPageImage(file, "/journal")}
            onPendingChange={setImagePending}
            onValidationError={(message) => {
              setError(message);
              showToast(message, "error", "top-right");
            }}
          />
          <label className="cms-field cms-field--check"><span><input type="checkbox" checked={draft.is_published} onChange={(event) => setField("is_published", event.target.checked)} /> 發布</span></label>
          <label className="cms-field cms-field--check"><span><input type="checkbox" checked={draft.is_archived} onChange={(event) => setField("is_archived", event.target.checked)} /> 已結束</span></label>
          <div className="cms-copy-card__actions">
            <button type="button" className="btn-sm" onClick={() => setDraft(null)}>取消</button>
            <button type="button" className="btn-sm btn-primary" disabled={saving} onClick={() => void save()}>{saving ? "儲存中…" : "儲存文章"}</button>
          </div>
        </article>
      ) : null}
      {loading ? <p className="cms-hint">載入文章中…</p> : null}
      {!loading && !posts.length ? <p className="cms-hint">目前沒有日誌文章。</p> : null}
      <div className="cms-journal-list">
        {posts.map((post) => (
          <article className="cms-copy-card" key={post.id}>
            <div className="cms-copy-card__header"><h4>{post.title}</h4><span className="cms-hint">{post.posted_at}</span></div>
            <p>{post.body || "（沒有內文）"}</p>
            <div className="cms-copy-card__actions">
              <span className="cms-hint">{post.is_published ? "已發布" : "草稿"}</span>
              <button type="button" className="btn-sm" onClick={() => {
                setDraft(draftFromPost(post));
                setError(null);
                setImagePending(false);
                setImageFieldKey((key) => key + 1);
              }}>編輯</button>
              <button type="button" className="btn-sm" onClick={() => void action(post, post.is_published ? "unpublish" : "publish")}>{post.is_published ? "取消發布" : "發布"}</button>
              <button type="button" className="btn-sm adx-action--danger" onClick={() => void action(post, "delete")}>刪除</button>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
