import { useEffect, useState } from "react";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";

import {
  CmsPaletteButton,
  CmsSortableRow,
  CmsTrashDropTarget,
} from "@/components/admin/CmsEditorDnd";
import CmsSectionPropsForm, {
  CmsPageMetaForm,
} from "@/components/admin/CmsSectionPropsForm";
import {
  SECTION_PALETTE,
  sectionLabel,
  type CmsPage,
  type CmsSection,
} from "@/components/admin/cmsSectionMeta";
import { Switch } from "@/components/ui/switch";
import type { ImageUploadResult } from "@/components/ui/image-upload";

type Props = {
  page: CmsPage | null;
  sections: CmsSection[];
  selected: CmsSection | null;
  selectedId: string | null;
  media: { id: string; url: string; alt?: string }[];
  faqCategories: { id: string; title: string }[];
  disabled: boolean;
  onAdd: () => void;
  onSelect: (id: string) => void;
  onChangeProps: (props: Record<string, unknown>) => void;
  onPickMedia: (prop: string) => void;
  onToggleVisibility: () => void;
  onDelete: (section?: CmsSection) => void;
  onSaveMeta: (meta: Partial<CmsPage>) => void;
  uploadImage?: (file: File) => Promise<ImageUploadResult>;
  onImageUploaded?: (url: string, alt: string) => void | Promise<void>;
};

export default function CmsEditorTools(props: Props) {
  const [tab, setTab] = useState<"content" | "add">("add");

  useEffect(() => {
    if (props.selectedId) setTab("content");
  }, [props.selectedId]);

  return (
    <aside className="cms-editor__props">
      <h3>區塊設定</h3>
      <Switch
        name="cms-tools-tab"
        size="small"
        className="cms-tools-tabs"
        value={tab}
        onValueChange={(value) => setTab(value === "add" ? "add" : "content")}
      >
        <Switch.Control label="內容設定" value="content" />
        <Switch.Control label="新增元素" value="add" />
      </Switch>

      {tab === "content" ? (
        <>
          {props.selected ? (
            <>
              <p className="cms-hint">{sectionLabel(props.selected.type)}</p>
              <CmsSectionPropsForm
                section={props.selected}
                media={props.media}
                faqCategories={props.faqCategories}
                disabled={props.disabled}
                onChange={props.onChangeProps}
                onPickMedia={props.onPickMedia}
                uploadImage={props.uploadImage}
                onImageUploaded={props.onImageUploaded}
              />
              <div className="cms-props-actions">
                <button
                  type="button"
                  className="btn-sm"
                  disabled={props.disabled}
                  onClick={props.onToggleVisibility}
                >
                  {props.selected.is_visible ? "隱藏" : "顯示"}
                </button>
                <button
                  type="button"
                  className="btn-sm"
                  disabled={props.disabled}
                  onClick={() => {
                    if (confirm("刪除此區塊？")) props.onDelete(props.selected || undefined);
                  }}
                >
                  刪除區塊
                </button>
              </div>
            </>
          ) : (
            <p className="cms-hint">點選圖層或預覽中的區塊以編輯。</p>
          )}
          <CmsPageMetaForm page={props.page} onSave={props.onSaveMeta} />
        </>
      ) : (
        <div className="cms-tools-add">
          <p className="cms-hint">拖曳到預覽中的藍色插入線放置（點擊僅提示）。</p>
          <div className="cms-palette-grid">
            {SECTION_PALETTE.map((item) => (
              <CmsPaletteButton
                key={item.type}
                type={item.type}
                disabled={props.disabled}
                onAdd={props.onAdd}
              />
            ))}
          </div>
          <details className="cms-ordering" open>
            <summary>區塊排序（{props.sections.length}）</summary>
            <p className="cms-hint">拖曳區塊排序，或拖到下方垃圾桶刪除。</p>
            <SortableContext
              items={props.sections.map((section) => section.id)}
              strategy={verticalListSortingStrategy}
            >
              <div className="cms-layers">
                {props.sections.map((section) => (
                  <CmsSortableRow
                    key={section.id}
                    section={section}
                    selected={section.id === props.selectedId}
                    onSelect={() => props.onSelect(section.id)}
                    onDelete={() => {
                      props.onSelect(section.id);
                      props.onDelete(section);
                    }}
                  />
                ))}
              </div>
            </SortableContext>
          </details>
        </div>
      )}
      <CmsTrashDropTarget />
    </aside>
  );
}
