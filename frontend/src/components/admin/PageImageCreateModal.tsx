import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button-1";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { PageImageEditRow } from "@/components/admin/PageImageEditModal";

export type PageImageCreateOption = {
  page_key: string;
  page_label: string;
  slot_key: string;
  slot_label: string;
  target_w: number;
  target_h: number;
};

export type PageImageCreateModalProps = {
  options: PageImageCreateOption[];
  defaultPageKey?: string;
  onClose: () => void;
  onCreated: (row: PageImageEditRow) => void;
  createPageImage: (
    pageKey: string,
    slotKey: string,
  ) => Promise<{ pageImage?: PageImageEditRow; error?: string | { message?: string } }>;
};

function resolveError(error: string | { message?: string } | undefined) {
  if (!error) return "建立失敗";
  if (typeof error === "string") return error;
  return error.message || "建立失敗";
}

const EMPTY = "__none__";

export default function PageImageCreateModal({
  options,
  defaultPageKey = "",
  onClose,
  onCreated,
  createPageImage,
}: PageImageCreateModalProps) {
  const pages = useMemo(() => {
    const seen = new Map<string, string>();
    for (const option of options) {
      if (!seen.has(option.page_key)) {
        seen.set(option.page_key, option.page_label || option.page_key);
      }
    }
    return [...seen.entries()].map(([value, label]) => ({ value, label }));
  }, [options]);

  const initialPage =
    defaultPageKey && pages.some((page) => page.value === defaultPageKey)
      ? defaultPageKey
      : pages[0]?.value || "";

  const [pageKey, setPageKey] = useState(initialPage);
  const [slotKey, setSlotKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const slotsForPage = useMemo(
    () => options.filter((option) => option.page_key === pageKey),
    [options, pageKey],
  );

  const selectedSlot =
    slotsForPage.find((slot) => slot.slot_key === slotKey) ||
    slotsForPage[0] ||
    null;

  const slotValue = selectedSlot?.slot_key || EMPTY;

  async function handleCreate() {
    if (!selectedSlot) return;
    setSaving(true);
    setError("");
    const res = await createPageImage(selectedSlot.page_key, selectedSlot.slot_key);
    setSaving(false);
    if (res.error || !res.pageImage) {
      setError(resolveError(res.error));
      return;
    }
    onCreated(res.pageImage);
  }

  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <DialogContent
        className="border-[#ede7e0] bg-white text-[#2b2320] sm:max-w-md"
        data-admin-root=""
      >
        <DialogHeader>
          <DialogTitle>新增頁面圖片</DialogTitle>
          <p className="text-sm text-[#8a817b]">
            選擇尚未建立的內容圖片區塊，建立後即可上傳圖片。
          </p>
        </DialogHeader>

        {options.length === 0 ? (
          <p className="text-sm leading-relaxed text-[#8a817b]">
            所有頁面圖片區塊皆已建立。請在表格中選擇區塊上傳或更換圖片。
          </p>
        ) : (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>頁面</Label>
              <Select
                value={pageKey || EMPTY}
                onValueChange={(next) => {
                  const resolved = next === EMPTY ? "" : next;
                  setPageKey(resolved);
                  setSlotKey("");
                }}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="— 選擇頁面 —" />
                </SelectTrigger>
                <SelectContent>
                  {pages.map((page) => (
                    <SelectItem key={page.value} value={page.value}>
                      {page.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>圖片區塊</Label>
              <Select
                value={slotValue}
                onValueChange={(next) => setSlotKey(next === EMPTY ? "" : next)}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="— 選擇區塊 —" />
                </SelectTrigger>
                <SelectContent>
                  {slotsForPage.map((slot) => (
                    <SelectItem key={slot.slot_key} value={slot.slot_key}>
                      {slot.slot_label}（{slot.target_w}×{slot.target_h}）
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {error ? <p className="text-xs text-[#c0392b]">{error}</p> : null}
          </div>
        )}

        <DialogFooter className="gap-2 sm:gap-3">
          <Button type="button" variant="outline" size="sm" onClick={onClose}>
            取消
          </Button>
          {options.length > 0 ? (
            <Button
              type="button"
              size="sm"
              disabled={saving || !selectedSlot}
              onClick={() => void handleCreate()}
            >
              {saving ? "建立中…" : "建立並上傳"}
            </Button>
          ) : null}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
