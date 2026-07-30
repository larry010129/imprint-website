import CmsSectionPropsForm from "@/components/admin/CmsSectionPropsForm";
import { sectionLabel, type CmsSection, type CmsSectionTemplate } from "@/components/admin/cmsSectionMeta";
import CmsAddSectionGallery, {
  type CmsInsertTarget,
} from "@/components/admin/CmsAddSectionGallery";
import type { CopySlot } from "@/components/admin/ExistingSitePageEditor";
import type { ImageUploadResult } from "@/components/ui/image-upload";

type Props = {
  selectedSlot: CopySlot | null;
  selectedSection: CmsSection | null;
  faqCategories: { id: string; title: string }[];
  disabled: boolean;
  saving: boolean;
  onChangeSelectedSlot: (next: CopySlot) => void;
  onSaveSelectedSlot: () => void;
  onResetSelectedSlot: () => void;
  onChangeSectionProps: (props: Record<string, unknown>) => void;
  onPickMedia: (prop: string) => void;
  onToggleSectionVisibility: () => void;
  onDeleteSection: (section?: CmsSection) => void;
  focusedProp?: string | null;
  galleryOpen: boolean;
  insertTarget: CmsInsertTarget | null;
  onCloseGallery: () => void;
  onChooseTemplate: (template: CmsSectionTemplate) => void | Promise<void>;
  uploadImage?: (file: File) => Promise<ImageUploadResult>;
  onImageUploaded?: (url: string, alt: string) => void | Promise<void>;
};

export default function SiteEditorTools(props: Props) {
  return (
    <aside className="cms-editor__props">
      <h3>內容設定</h3>

      {props.selectedSection ? (
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
            focusProp={props.focusedProp}
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
          點擊預覽文字編輯固定文案；點選附加區塊後，可在此編輯標題、內文與圖片。
        </p>
      )}
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
