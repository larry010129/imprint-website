import { useEffect, useState } from "react";

import {
  fetchReleaseNotes,
  parseReleaseNoteSections,
  type PublishedRelease,
} from "@/components/admin/releaseNotesApi";
import { cn } from "@/lib/utils";

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

export type ReleaseNotesHistoryProps = {
  className?: string;
};

/** 版本更新紀錄 — published + history, separate sidebar tab. */
export default function ReleaseNotesHistory({ className }: ReleaseNotesHistoryProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [published, setPublished] = useState<PublishedRelease | null>(null);
  const [history, setHistory] = useState<PublishedRelease[]>([]);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const data = await fetchReleaseNotes();
        if (cancelled) return;
        setPublished(data.published ?? null);
        setHistory(data.history ?? []);
        setError("");
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "載入失敗");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className={cn("w-full space-y-5", className)}>
      <div className="space-y-1">
        <h2 className="text-xl font-semibold tracking-tight text-foreground">
          版本更新紀錄
        </h2>
        <p className="text-sm text-muted-foreground">
          已發布版本與過往推送紀錄。
        </p>
      </div>

      <div className="space-y-4 rounded-lg border border-border bg-background/60 p-5">
        {loading ? (
          <p className="text-sm text-muted-foreground">載入中…</p>
        ) : error ? (
          <p className="text-sm text-destructive">{error}</p>
        ) : (
          <>
            {published ? (
              <div className="space-y-3 rounded-md border border-border/70 bg-background p-4">
                <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                  <span className="text-sm font-semibold text-foreground">
                    {published.version || "未命名版本"}
                  </span>
                  <span className="text-sm text-foreground">{published.title}</span>
                  <span className="text-xs text-muted-foreground">
                    發布於 {formatPublishedAt(published.publishedAt)}
                  </span>
                </div>
                {parseReleaseNoteSections(published.notes).map((section, sectionIndex) => (
                  <section key={sectionIndex} className="space-y-1.5">
                    {section.title ? (
                      <h4 className="text-sm font-medium text-foreground">{section.title}</h4>
                    ) : null}
                    {section.items.length > 0 ? (
                      <ul className="list-disc space-y-1 pl-5 text-sm text-foreground">
                        {section.items.map((item, itemIndex) => (
                          <li key={itemIndex}>{item}</li>
                        ))}
                      </ul>
                    ) : null}
                  </section>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">目前尚無已發布版本。</p>
            )}

            {history.length > 0 ? (
              <div className="space-y-3">
                <h4 className="text-sm font-medium text-foreground">過往版本</h4>
                <div className="max-h-[70vh] space-y-3 overflow-y-auto pr-1">
                  {history.map((release) => (
                    <details
                      key={release.releaseId}
                      className="rounded-md border border-border/60 bg-background/80 px-4 py-3"
                    >
                      <summary className="cursor-pointer list-none space-y-1 text-sm">
                        <span className="font-medium text-foreground">
                          {release.version || "未命名版本"} · {release.title}
                        </span>
                        <span className="block text-xs text-muted-foreground">
                          發布於 {formatPublishedAt(release.publishedAt)}
                        </span>
                      </summary>
                      <div className="mt-3 space-y-3 border-t border-border/60 pt-3">
                        {parseReleaseNoteSections(release.notes).map((section, sectionIndex) => (
                          <section key={sectionIndex} className="space-y-1.5">
                            {section.title ? (
                              <h5 className="text-sm font-medium text-foreground">
                                {section.title}
                              </h5>
                            ) : null}
                            {section.items.length > 0 ? (
                              <ul className="list-disc space-y-1 pl-5 text-sm text-foreground">
                                {section.items.map((item, itemIndex) => (
                                  <li key={itemIndex}>{item}</li>
                                ))}
                              </ul>
                            ) : null}
                          </section>
                        ))}
                      </div>
                    </details>
                  ))}
                </div>
              </div>
            ) : null}
          </>
        )}
      </div>
    </div>
  );
}
