import type { ReactNode } from "react";
import { useDraggable, useDroppable } from "@dnd-kit/core";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

import { sectionLabel, type CmsSection, type CmsSectionType } from "@/components/admin/cmsSectionMeta";

export const CMS_CANVAS_DROP_ID = "cms-canvas-drop";

export function CmsSortableRow({
  section,
  selected,
  onSelect,
}: {
  section: CmsSection;
  selected: boolean;
  onSelect: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: section.id,
  });
  return (
    <button
      type="button"
      ref={setNodeRef}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.7 : 1,
      }}
      className={`cms-layer${selected ? " is-active" : ""}${section.is_visible ? "" : " is-hidden"}`}
      onClick={onSelect}
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
  onAdd,
}: {
  type: CmsSectionType;
  label: string;
  onAdd: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: `palette:${type}`,
    data: { source: "palette", type },
  });
  return (
    <button
      ref={setNodeRef}
      type="button"
      className="btn-sm cms-palette-item"
      style={{
        transform: CSS.Translate.toString(transform),
        opacity: isDragging ? 0.65 : 1,
      }}
      onClick={onAdd}
      {...attributes}
      {...listeners}
    >
      {label}
    </button>
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
