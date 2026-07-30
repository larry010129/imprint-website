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
  defaultTemplateForType,
  SECTION_PALETTE,
  sectionLabel,
  type CmsPage,
  type CmsSection,
  type CmsSectionTemplate,
} from "@/components/admin/cmsSectionMeta";
import CmsAddSectionGallery, {
  type CmsInsertTarget,
} from "@/components/admin/CmsAddSectionGallery";
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
  focusedProp?: string | null;
  galleryOpen: boolean;
  insertTarget: CmsInsertTarget | null;
  onOpenGallery: () => void;
  onCloseGallery: () => void;
  onChooseTemplate: (template: CmsSectionTemplate) => void | Promise<void>;
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
                focusProp={props.focusedProp}
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
          <p className="cms-hint">點擊立即加入目前位置，或拖曳到預覽中的插入線。</p>
          <button
            type="button"
            className="btn-sm btn-primary cms-open-gallery"
            disabled={props.disabled}
            onClick={props.onOpenGallery}
          >
            瀏覽區塊範本
          </button>
          <div className="cms-palette-grid">
            {SECTION_PALETTE.map((item) => {
              const template = defaultTemplateForType(item.type);
              return (
              <CmsPaletteButton
                key={item.type}
                type={item.type}
                template={template}
                disabled={props.disabled}
                onAdd={() => void props.onChooseTemplate(template)}
              />
              );
            })}
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
      <CmsAddSectionGallery
        open={props.galleryOpen}
        disabled={props.disabled}
        target={props.insertTarget}
        onClose={props.onCloseGallery}
        onChoose={props.onChooseTemplate}
      />
    </aside>
  );
}
