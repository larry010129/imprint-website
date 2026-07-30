import { Redo2, Undo2 } from "lucide-react";

import type { CmsPage } from "@/components/admin/cmsSectionMeta";

type Props = {
  page: CmsPage | null;
  busy: boolean;
  message: string;
  canUndo: boolean;
  canRedo: boolean;
  previewUrl: string;
  onBack: () => void;
  onUndo: () => void;
  onRedo: () => void;
  onChangePage: (page: CmsPage) => void;
  onSaveMeta: (patch: Partial<CmsPage>) => void;
  onTogglePublish: () => void;
  onDeletePage: () => void;
};

export default function CmsEditorTopbar(props: Props) {
  return (
    <div className="cms-editor__top">
      <button type="button" className="btn-sm" onClick={props.onBack}>
        ← 返回列表
      </button>
      <div className="cms-history-actions">
        <button
          type="button"
          className="btn-sm cms-icon-button"
          disabled={!props.canUndo || props.busy}
          onClick={props.onUndo}
          title="復原（Ctrl/Cmd+Z）"
          aria-label="復原"
        >
          <Undo2 size={16} aria-hidden="true" />
        </button>
        <button
          type="button"
          className="btn-sm cms-icon-button"
          disabled={!props.canRedo || props.busy}
          onClick={props.onRedo}
          title="重做（Ctrl/Cmd+Shift+Z 或 Ctrl/Cmd+Y）"
          aria-label="重做"
        >
          <Redo2 size={16} aria-hidden="true" />
        </button>
      </div>
      <input
        className="cms-editor__title"
        value={props.page?.title || ""}
        onChange={(event) =>
          props.page &&
          props.onChangePage({ ...props.page, title: event.target.value })
        }
        onBlur={() =>
          props.page && props.onSaveMeta({ title: props.page.title })
        }
      />
      <input
        className="cms-editor__slug"
        value={props.page?.slug || ""}
        onChange={(event) =>
          props.page &&
          props.onChangePage({ ...props.page, slug: event.target.value })
        }
        onBlur={() => props.page && props.onSaveMeta({ slug: props.page.slug })}
        title="slug"
      />
      <span className="cms-status">
        {props.page?.status === "published" ? "已發布" : "草稿"}
      </span>
      <button
        type="button"
        className="btn-sm"
        disabled={props.busy || !props.page}
        onClick={props.onTogglePublish}
      >
        {props.page?.status === "published" ? "取消發布" : "發布"}
      </button>
      <a
        className="btn-sm"
        href={props.previewUrl || "#"}
        target="_blank"
        rel="noreferrer"
      >
        開新分頁預覽
      </a>
      <button type="button" className="btn-sm" onClick={props.onDeletePage}>
        刪除
      </button>
      {props.message ? <span className="cms-msg">{props.message}</span> : null}
    </div>
  );
}
