import { useEffect, useRef, type ReactNode } from "react";
import { useDraggable, useDroppable } from "@dnd-kit/core";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Trash2 } from "lucide-react";

import {
  SECTION_FALLBACK_ICON,
  sectionDescription,
  sectionLabel,
  sectionMeta,
  type CmsSection,
  type CmsSectionType,
} from "@/components/admin/cmsSectionMeta";

export const CMS_CANVAS_DROP_ID = "cms-canvas-drop";
export const CMS_TRASH_DROP_ID = "cms-trash-drop";

export function CmsSortableRow({
  section,
  selected,
  onSelect,
  onDelete,
}: {
  section: CmsSection;
  selected: boolean;
  onSelect: () => void;
  onDelete?: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: section.id,
    data: { source: "section", section, label: sectionLabel(section.type) },
  });
  return (
    <button
      type="button"
      ref={setNodeRef}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.35 : 1,
      }}
      className={`cms-layer${selected ? " is-active" : ""}${section.is_visible ? "" : " is-hidden"}`}
      onClick={onSelect}
      onContextMenu={(event) => {
        if (!onDelete) return;
        event.preventDefault();
        onSelect();
        if (confirm("刪除此區塊？")) onDelete();
      }}
      title={onDelete ? "右鍵可刪除" : undefined}
      {...attributes}
      {...listeners}
    >
      <span className="cms-layer__handle" aria-hidden="true">⋮⋮</span>
      <span>{sectionLabel(section.type)}</span>
    </button>
  );
}

export function CmsPaletteButton({
  type,
  label,
  description,
  onAdd,
  disabled = false,
}: {
  type: CmsSectionType;
  label?: string;
  description?: string;
  /** Click hint only — sections are created on canvas drop. */
  onAdd: () => void;
  disabled?: boolean;
}) {
  const meta = sectionMeta(type);
  const title = label || meta?.label || type;
  const hint = description || meta?.description || "";
  const Icon = meta?.icon || SECTION_FALLBACK_ICON;
  const skipClickRef = useRef(false);
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `palette:${type}`,
    data: { source: "palette", type, label: title },
    disabled,
  });
  useEffect(() => {
    if (isDragging) skipClickRef.current = true;
  }, [isDragging]);
  return (
    <button
      ref={setNodeRef}
      type="button"
      className={`cms-palette-card${isDragging ? " is-dragging" : ""}`}
      disabled={disabled}
      style={{ opacity: isDragging ? 0.35 : 1 }}
      onClick={() => {
        if (skipClickRef.current) {
          skipClickRef.current = false;
          return;
        }
        onAdd();
      }}
      title={hint || title}
      {...attributes}
      {...listeners}
    >
      <span className="cms-palette-card__icon" aria-hidden="true">
        <Icon size={18} strokeWidth={1.75} />
      </span>
      <span className="cms-palette-card__body">
        <span className="cms-palette-card__title">{title}</span>
        {hint ? <span className="cms-palette-card__hint">{hint}</span> : null}
      </span>
    </button>
  );
}

export function CmsDragOverlayCard({
  label,
  type,
}: {
  label: string;
  type?: string;
}) {
  const meta = type ? sectionMeta(type) : undefined;
  const Icon = meta?.icon || SECTION_FALLBACK_ICON;
  const hint = type ? sectionDescription(type) : "";
  return (
    <div className="cms-drag-overlay cms-drag-overlay--card">
      <span className="cms-palette-card__icon" aria-hidden="true">
        <Icon size={18} strokeWidth={1.75} />
      </span>
      <span className="cms-palette-card__body">
        <span className="cms-palette-card__title">{label}</span>
        {hint ? <span className="cms-palette-card__hint">{hint}</span> : null}
      </span>
    </div>
  );
}

export function CmsCanvasDropTarget({
  className,
  active,
  children,
}: {
  className: string;
  active: boolean;
  children: ReactNode;
}) {
  const { isOver, setNodeRef } = useDroppable({ id: CMS_CANVAS_DROP_ID });
  return (
    <div
      ref={setNodeRef}
      className={`${className}${active ? " is-drop-enabled" : ""}${isOver ? " is-drop-over" : ""}`}
    >
      {children}
    </div>
  );
}

export function CmsTrashDropTarget() {
  const { isOver, setNodeRef } = useDroppable({ id: CMS_TRASH_DROP_ID });
  return (
    <div
      ref={setNodeRef}
      className={`cms-trash-target${isOver ? " is-over" : ""}`}
      aria-label="拖曳區塊到此刪除"
    >
      <Trash2 size={18} aria-hidden="true" />
      <span>{isOver ? "放開以刪除" : "拖曳區塊到此刪除"}</span>
    </div>
  );
}
