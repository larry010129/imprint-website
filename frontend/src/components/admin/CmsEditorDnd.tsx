import type { ReactNode } from "react";
import { useDroppable } from "@dnd-kit/core";

import {
  SECTION_FALLBACK_ICON,
  sectionDescription,
  sectionMeta,
} from "@/components/admin/cmsSectionMeta";

export const CMS_CANVAS_DROP_ID = "cms-canvas-drop";
export const CMS_TRASH_DROP_ID = "cms-trash-drop";

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
