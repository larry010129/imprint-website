import { useEffect, useState } from "react";
import { useDraggable, useDroppable } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { Trash2 } from "lucide-react";

import {
  CmsPaletteButton,
  CmsSortableRow,
  CMS_TRASH_DROP_ID,
} from "@/components/admin/CmsEditorDnd";
import CmsSectionPropsForm from "@/components/admin/CmsSectionPropsForm";
import {
  SECTION_PALETTE,
  sectionLabel,
  type CmsSection,
} from "@/components/admin/cmsSectionMeta";
import { Switch } from "@/components/ui/switch";
import type { CopySlot } from "@/components/admin/ExistingSitePageEditor";
import type { ImageUploadResult } from "@/components/ui/image-upload";

export function SiteSlotRow({
  slot,
  selected,
  onSelect,
  disabled = false,
}: {
  slot: CopySlot;
  selected: boolean;
  onSelect: () => void;
  disabled?: boolean;
}) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `slot:${slot.slot_key}`,
    data: { source: "slot", slot, label: slot.label },
    disabled,
  });
  return (
    <button
      type="button"
      ref={setNodeRef}
      style={{ opacity: isDragging ? 0.35 : 1 }}
      className={`cms-layer${selected ? " is-active" : ""}${slot.is_published ? "" : " is-hidden"}`}
      onClick={onSelect}
      disabled={disabled}
      {...attributes}
      {...listeners}
    >
      <span className="cms-layer__handle" aria-hidden="true">
        ⋮⋮
      </span>
      <span>{slot.label}</span>
    </button>
  );
}

function SiteTrashDropTarget() {
  const { isOver, setNodeRef } = useDroppable({ id: CMS_TRASH_DROP_ID });
  return (
    <div
      ref={setNodeRef}
      className={`cms-trash-target${isOver ? " is-over" : ""}`}
      aria-label="拖曳到此刪除區塊或還原欄位"
    >
      <Trash2 size={18} aria-hidden="true" />
      <span>{isOver ? "放開以刪除／還原" : "拖曳區塊刪除，或欄位還原預設"}</span>
    </div>
  );
}

type Props = {
  selectedSlot: CopySlot | null;
  selectedSection: CmsSection | null;
  slots: CopySlot[];
  sections: CmsSection[];
  selectedSlotKey: string | null;
  selectedSectionId: string | null;
  faqCategories: { id: string; title: string }[];
  disabled: boolean;
  saving: boolean;
  onSelectSlot: (key: string) => void;
  onSelectSection: (id: string) => void;
  onChangeSelectedSlot: (next: CopySlot) => void;
  onSaveSelectedSlot: () => void;
  onResetSelectedSlot: () => void;
  onChangeSectionProps: (props: Record<string, unknown>) => void;
  onPickMedia: (prop: string) => void;
  onToggleSectionVisibility: () => void;
  onDeleteSection: (section?: CmsSection) => void;
  onPaletteAdd: () => void;
  uploadImage?: (file: File) => Promise<ImageUploadResult>;
  onImageUploaded?: (url: string, alt: string) => void | Promise<void>;
};

export default function SiteEditorTools(props: Props) {
  const [tab, setTab] = useState<"content" | "add">("add");

  useEffect(() => {
    if (props.selectedSectionId || props.selectedSlotKey) setTab("content");
  }, [props.selectedSectionId, props.selectedSlotKey]);

  return (
    <aside className="cms-editor__props">
      <h3>內容設定</h3>
      <Switch
        name="site-tools-tab"
        size="small"
        className="cms-tools-tabs"
        value={tab}
        onValueChange={(value) => setTab(value === "add" ? "add" : "content")}
      >
        <Switch.Control label="內容設定" value="content" />
        <Switch.Control label="新增元素" value="add" />
      </Switch>

      {tab === "content" ? (
        props.selectedSection ? (
          <>
            <p className="cms-hint">{sectionLabel(props.selectedSection.type)} 區塊</p>
            <CmsSectionPropsForm
              section={props.selectedSection}
              media={[]}
              faqCategories={props.faqCategories}
              disabled={props.disabled}
              onChange={props.onChangeSectionProps}
              onPickMedia={props.onPickMedia}
              uploadImage={props.uploadImage}
              onImageUploaded={props.onImageUploaded}
            />
            <div className="cms-props-actions">
              <button
                type="button"
                className="btn-sm"
                disabled={props.disabled}
                onClick={props.onToggleSectionVisibility}
              >
                {props.selectedSection.is_visible ? "隱藏" : "顯示"}
              </button>
              <button
                type="button"
                className="btn-sm"
                disabled={props.disabled}
                onClick={() => {
                  if (confirm("刪除此區塊？")) {
                    props.onDeleteSection(props.selectedSection || undefined);
                  }
                }}
              >
                刪除區塊
              </button>
            </div>
          </>
        ) : props.selectedSlot ? (
          <form
            className="cms-site-slot-form"
            onSubmit={(event) => {
              event.preventDefault();
              props.onSaveSelectedSlot();
            }}
          >
            <strong>{props.selectedSlot.label}</strong>
            <p className="cms-hint">文字請直接在左側完整頁面預覽中修改。</p>
            {props.selectedSlot.kind === "button" ? (
              <label className="cms-field">
                <span>連結</span>
                <input
                  value={props.selectedSlot.href}
                  disabled={props.disabled}
                  onChange={(event) =>
                    props.onChangeSelectedSlot({
                      ...props.selectedSlot!,
                      href: event.target.value,
                    })
                  }
                />
              </label>
            ) : null}
            <label>
              <input
                type="checkbox"
                checked={props.selectedSlot.is_published}
                disabled={props.disabled}
                onChange={(event) =>
                  props.onChangeSelectedSlot({
                    ...props.selectedSlot!,
                    is_published: event.target.checked,
                  })
                }
              />{" "}
              啟用自訂值
            </label>
            <div className="cms-props-actions">
              <button
                type="submit"
                className="btn-sm btn-primary"
                disabled={props.saving || props.disabled}
              >
                儲存設定
              </button>
              <button
                type="button"
                className="btn-sm"
                disabled={props.disabled}
                onClick={() => {
                  if (confirm("還原此欄位為預設內容？")) props.onResetSelectedSlot();
                }}
              >
                還原預設
              </button>
            </div>
          </form>
        ) : (
          <p className="cms-hint">
            點擊預覽中的虛線文字編輯固定文案，或點選附加區塊後在此上傳圖片。
          </p>
        )
      ) : (
        <div className="cms-tools-add">
          <p className="cms-hint">拖曳到預覽中的藍色插入線放置（點擊僅提示）。</p>
          <div className="cms-palette-grid">
            {SECTION_PALETTE.map((item) => (
              <CmsPaletteButton
                key={item.type}
                type={item.type}
                label={item.label}
                description={item.description}
                disabled={props.disabled}
                onAdd={props.onPaletteAdd}
              />
            ))}
          </div>
          <details className="cms-ordering" open>
            <summary>附加區塊（{props.sections.length}）</summary>
            <SortableContext
              items={props.sections.map((section) => section.id)}
              strategy={verticalListSortingStrategy}
            >
              <div className="cms-layers">
                {props.sections.map((section) => (
                  <CmsSortableRow
                    key={section.id}
                    section={section}
                    selected={section.id === props.selectedSectionId}
                    onSelect={() => props.onSelectSection(section.id)}
                    onDelete={() => {
                      props.onSelectSection(section.id);
                      props.onDeleteSection(section);
                    }}
                  />
                ))}
              </div>
            </SortableContext>
          </details>
          <details className="cms-ordering">
            <summary>固定欄位（{props.slots.length}）</summary>
            <p className="cms-hint">拖曳欄位到下方垃圾桶可還原預設內容。</p>
            <div className="cms-layers">
              {props.slots.map((slot) => (
                <SiteSlotRow
                  key={slot.slot_key}
                  slot={slot}
                  selected={slot.slot_key === props.selectedSlotKey}
                  onSelect={() => props.onSelectSlot(slot.slot_key)}
                  disabled={props.disabled}
                />
              ))}
            </div>
          </details>
        </div>
      )}
      <SiteTrashDropTarget />
    </aside>
  );
}
