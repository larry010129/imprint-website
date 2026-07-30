import { useEffect, useMemo, useRef, useState } from "react";

import {
  SECTION_TEMPLATE_CATEGORIES,
  SECTION_TEMPLATES,
  type CmsSectionTemplate,
  type CmsSectionTemplateCategory,
} from "@/components/admin/cmsSectionMeta";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export type CmsInsertTarget = {
  anchor: string;
  index: number;
  beforeId?: string | null;
};

type Props = {
  open: boolean;
  disabled?: boolean;
  target: CmsInsertTarget | null;
  onClose: () => void;
  onChoose: (template: CmsSectionTemplate) => void | Promise<void>;
};

export default function CmsAddSectionGallery({
  open,
  disabled = false,
  target,
  onClose,
  onChoose,
}: Props) {
  const [category, setCategory] =
    useState<CmsSectionTemplateCategory>("blank");
  const [message, setMessage] = useState("");
  const firstTabRef = useRef<HTMLButtonElement>(null);
  const restoreFocusRef = useRef<HTMLElement | null>(null);
  const templates = useMemo(
    () => SECTION_TEMPLATES.filter((item) => item.category === category),
    [category],
  );

  useEffect(() => {
    if (!open) return;
    restoreFocusRef.current = document.activeElement as HTMLElement | null;
    setMessage("");
    requestAnimationFrame(() => firstTabRef.current?.focus());
  }, [open]);

  function close() {
    onClose();
    requestAnimationFrame(() => restoreFocusRef.current?.focus());
  }

  return (
    <Dialog open={open} onOpenChange={(next) => !next && close()}>
      <DialogContent
        className="cms-add-gallery"
        overlayClassName="cms-add-gallery__overlay"
        aria-describedby="cms-add-gallery-description"
      >
        <DialogHeader>
          <DialogTitle>新增區塊</DialogTitle>
          <DialogDescription id="cms-add-gallery-description">
            選擇版型後，會插入到
            {target ? `「${target.anchor}」第 ${target.index + 1} 個位置` : "頁面尾端"}。
          </DialogDescription>
        </DialogHeader>

        <div className="cms-add-gallery__tabs" role="tablist" aria-label="區塊分類">
          {SECTION_TEMPLATE_CATEGORIES.map((item, index) => (
            <button
              key={item.id}
              ref={index === 0 ? firstTabRef : undefined}
              type="button"
              role="tab"
              aria-selected={category === item.id}
              className={category === item.id ? "is-active" : ""}
              onClick={() => setCategory(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>

        <div className="cms-add-gallery__grid" role="tabpanel">
          {templates.map((template) => (
            <button
              key={template.id}
              type="button"
              className="cms-template-tile"
              disabled={disabled}
              onClick={async () => {
                setMessage(`正在新增「${template.label}」…`);
                await onChoose(template);
              }}
            >
              <span
                className={`cms-template-preview cms-template-preview--${template.previewKind}`}
                aria-hidden="true"
              >
                <i />
                <i />
                <i />
              </span>
              <strong>{template.label}</strong>
              <span>{template.description}</span>
            </button>
          ))}
        </div>
        <p className="cms-add-gallery__live" aria-live="polite">
          {message}
        </p>
      </DialogContent>
    </Dialog>
  );
}
