import CmsSectionPropsForm, {
  CmsPageMetaForm,
} from "@/components/admin/CmsSectionPropsForm";
import {
  sectionLabel,
  type CmsPage,
  type CmsSection,
  type CmsSectionTemplate,
} from "@/components/admin/cmsSectionMeta";
import CmsAddSectionGallery, {
  type CmsInsertTarget,
} from "@/components/admin/CmsAddSectionGallery";
import type { ImageUploadResult } from "@/components/ui/image-upload";

type Props = {
  page: CmsPage | null;
  selected: CmsSection | null;
  media: { id: string; url: string; alt?: string }[];
  faqCategories: { id: string; title: string }[];
  disabled: boolean;
  focusedProp?: string | null;
  galleryOpen: boolean;
  insertTarget: CmsInsertTarget | null;
  onCloseGallery: () => void;
  onChooseTemplate: (template: CmsSectionTemplate) => void | Promise<void>;
  onChangeProps: (props: Record<string, unknown>) => void;
  onPickMedia: (prop: string) => void;
  onToggleVisibility: () => void;
  onDelete: (section?: CmsSection) => void;
  onSaveMeta: (meta: Partial<CmsPage>) => void;
  uploadImage?: (file: File) => Promise<ImageUploadResult>;
  onImageUploaded?: (url: string, alt: string) => void | Promise<void>;
};

export default function CmsEditorTools(props: Props) {
  return (
    <aside className="cms-editor__props">
      <h3>區塊設定</h3>

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
