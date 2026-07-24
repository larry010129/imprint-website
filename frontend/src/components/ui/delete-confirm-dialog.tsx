import { CircleAlert } from "lucide-react";

import { Button } from "@/components/ui/button-1";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export type DeleteConfirmDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
  title?: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
};

export function DeleteConfirmDialog({
  open,
  onOpenChange,
  onConfirm,
  title = "確定要刪除嗎？",
  description = "此操作無法復原，刪除後資料將永久移除。",
  confirmLabel = "刪除",
  cancelLabel = "取消",
}: DeleteConfirmDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="border-[#ede7e0] bg-white text-[#2b2320] sm:max-w-md">
        <DialogHeader>
          <div className="flex flex-col gap-3">
            <div className="flex size-10 items-center justify-center rounded-full bg-[#fafaf8]">
              <CircleAlert className="size-5 text-[#c0392b]" aria-hidden />
            </div>
            <div className="flex flex-col gap-2">
              <DialogTitle className="text-[#2b2320]">{title}</DialogTitle>
              <DialogDescription className="text-[#8a817b]">{description}</DialogDescription>
            </div>
          </div>
        </DialogHeader>
        <DialogFooter className="gap-2 sm:gap-3">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => onOpenChange(false)}
          >
            {cancelLabel}
          </Button>
          <Button
            type="button"
            variant="destructive"
            size="sm"
            className="bg-[#c0392b] text-white hover:bg-[#c0392b]/90"
            onClick={() => {
              onConfirm();
              onOpenChange(false);
            }}
          >
            {confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
