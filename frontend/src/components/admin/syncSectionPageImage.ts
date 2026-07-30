import {
  sectionPageImageLabel,
  type CmsSectionType,
} from "@/components/admin/cmsSectionMeta";

export type SyncSectionPageImageFields = {
  sectionId: string;
  sectionType?: string;
  imageUrl: string;
  imageAlt?: string;
  label?: string;
  /** Optional; backend derives page_key from section when omitted. */
  pageKey?: string;
};

export type SyncSectionPageImageApi = {
  syncSectionPageImage?: (
    fields: SyncSectionPageImageFields
  ) => Promise<{ ok?: boolean; pageImage?: unknown; error?: string }>;
  removeSectionPageImage?: (fields: {
    sectionId: string;
    pageKey?: string;
  }) => Promise<{ ok?: boolean; error?: string }>;
};

export function sectionPageImageSlotKey(sectionId: string): string {
  return `cms-section-${sectionId}`;
}

export async function syncSectionPageImage(
  api: SyncSectionPageImageApi,
  fields: {
    sectionId: string;
    sectionType: CmsSectionType | string;
    imageUrl: string;
    imageAlt?: string;
    pageKey?: string;
  }
): Promise<{ ok: boolean; error?: string }> {
  const sectionId = String(fields.sectionId || "").trim();
  if (!sectionId) {
    return { ok: false, error: "缺少 sectionId" };
  }
  if (!api.syncSectionPageImage) {
    return { ok: false, error: "頁面圖片同步 API 尚未就緒" };
  }
  const res = await api.syncSectionPageImage({
    pageKey: fields.pageKey,
    sectionId,
    sectionType: fields.sectionType,
    imageUrl: fields.imageUrl,
    imageAlt: fields.imageAlt || "",
    label: sectionPageImageLabel(fields.sectionType),
  });
  if (res.error) return { ok: false, error: String(res.error) };
  return { ok: true };
}

export async function removeSectionPageImage(
  api: SyncSectionPageImageApi,
  fields: { sectionId: string; pageKey?: string }
): Promise<{ ok: boolean; error?: string }> {
  const sectionId = String(fields.sectionId || "").trim();
  if (!sectionId) {
    return { ok: false, error: "缺少 sectionId" };
  }
  if (!api.removeSectionPageImage) {
    return { ok: false, error: "頁面圖片同步 API 尚未就緒" };
  }
  const res = await api.removeSectionPageImage({
    pageKey: fields.pageKey,
    sectionId,
  });
  if (res.error) return { ok: false, error: String(res.error) };
  return { ok: true };
}
