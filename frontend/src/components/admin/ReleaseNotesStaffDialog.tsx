import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button-1";
import {
  parseReleaseNoteSections,
  type PublishedRelease,
} from "@/components/admin/releaseNotesApi";

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

  const sections = parseReleaseNoteSections(release?.notes ?? []);

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

        {sections.length > 0 ? (
          <div className="max-h-[50vh] space-y-5 overflow-y-auto pr-1 text-sm text-foreground">
            {sections.map((section, sectionIndex) => (
              <section
                key={`${sectionIndex}-${section.title ?? "items"}`}
                className="space-y-2"
              >
                {section.title ? (
                  <h3 className="text-sm font-semibold leading-snug text-foreground">
                    {section.title}
                  </h3>
                ) : null}
                {section.items.length > 0 ? (
                  <ul className="list-disc space-y-1.5 pl-5">
                    {section.items.map((item, itemIndex) => (
                      <li key={`${sectionIndex}-${itemIndex}-${item.slice(0, 24)}`}>
                        {item}
                      </li>
                    ))}
                  </ul>
                ) : null}
              </section>
            ))}
          </div>
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
