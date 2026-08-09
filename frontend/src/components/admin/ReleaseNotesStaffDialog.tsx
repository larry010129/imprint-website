import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button-1";
import type { PublishedRelease } from "@/components/admin/releaseNotesApi";

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  release: PublishedRelease | null;
  onDismiss: (releaseId: string) => void;
};

function formatPublishedAt(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  try {
    return new Intl.DateTimeFormat("zh-TW", {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(d);
  } catch {
    return iso;
  }
}

export default function ReleaseNotesStaffDialog({
  open,
  onOpenChange,
  release,
  onDismiss,
}: Props) {
  function handleOpenChange(next: boolean) {
    if (!next && release?.releaseId) {
      onDismiss(release.releaseId);
    }
    onOpenChange(next);
  }

  const notes = release?.notes?.filter((n) => String(n).trim()) ?? [];

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{release?.title || "更新公告"}</DialogTitle>
          <DialogDescription asChild>
            <div className="space-y-1 text-sm text-muted-foreground">
              {release?.version ? (
                <p>
                  版本 <span className="font-medium text-foreground">{release.version}</span>
                </p>
              ) : null}
              {release?.publishedAt ? (
                <p>發布於 {formatPublishedAt(release.publishedAt)}</p>
              ) : null}
              {!release ? <p>目前尚無已發布的更新內容。</p> : null}
            </div>
          </DialogDescription>
        </DialogHeader>

        {notes.length > 0 ? (
          <ul className="max-h-[50vh] list-disc space-y-2 overflow-y-auto pl-5 text-sm text-foreground">
            {notes.map((note, i) => (
              <li key={`${i}-${note.slice(0, 24)}`}>{note}</li>
            ))}
          </ul>
        ) : release ? (
          <p className="text-sm text-muted-foreground">此版本尚無詳細說明。</p>
        ) : null}

        <DialogFooter>
          <Button type="button" onClick={() => handleOpenChange(false)}>
            知道了
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
