import { useEffect, useRef, useState } from "react";
import { Calendar, Package, Sparkles, Zap, ArrowUpRight } from "lucide-react";
import {
  fetchJournalPostsApi,
  type ApiJournalPost,
} from "@/lib/content-api";

const JOURNAL_PAGE_SIZE = 20;

type JournalEntry = {
  id: string;
  date: string;
  title: string;
  body?: string;
  archived?: boolean;
  imageUrl?: string | null;
};

const JOURNAL_ICONS = [Calendar, Sparkles, Package, Zap];

function sortNewestFirst(entries: JournalEntry[]): JournalEntry[] {
  return [...entries].sort((a, b) => b.date.localeCompare(a.date));
}

function journalDateLabel(date: string): string {
  const [year = "", month = "", day = ""] = date.split("-");
  return `${year} · ${month}.${day}`;
}

function mapPost(post: ApiJournalPost): JournalEntry {
  return {
    id: post.id,
    date: post.posted_at,
    title: post.title,
    body: post.body || undefined,
    archived: post.is_archived,
    imageUrl: post.image_url,
  };
}

function EntryCard({ entry, active }: { entry: JournalEntry; active: boolean }) {
  const detailHref = `/journal/${encodeURIComponent(entry.id)}`;

  return (
    <article
      className={
        "flex flex-col rounded-2xl border p-3 transition-all duration-300 " +
        (active
          ? "border-[#d8f4f4] bg-[#f7ffff] shadow-lg"
          : "border-[#ede7e0] bg-white")
      }
    >
      {entry.imageUrl && (
        <img
          src={entry.imageUrl}
          alt=""
          loading="lazy"
          decoding="async"
          className="mb-4 aspect-[3/2] w-full rounded-lg object-cover object-top"
        />
      )}
      <div className="space-y-4 p-1 md:p-2">
        <div className="space-y-2">
          <h2
            className={
              "[overflow-wrap:anywhere] text-lg font-medium leading-tight tracking-tight transition-colors duration-200 md:text-xl " +
              (active ? "text-neutral-900" : "text-neutral-700")
            }
          >
            <a
              href={detailHref}
              className="inline hover:text-neutral-500"
            >
              {entry.title}
              <ArrowUpRight className="ml-1 inline-block h-4 w-4 align-[-0.125em]" aria-hidden="true" />
            </a>
          </h2>
          <p
            className={
              "text-sm leading-relaxed transition-all duration-300 " +
              (active ? "text-neutral-600" : "line-clamp-2 text-neutral-500")
            }
          >
            {entry.body || ""}
          </p>
        </div>
        <div
          aria-hidden={!active}
          className={
            "grid transition-all duration-500 ease-out " +
            (active ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0")
          }
        >
          <div className="overflow-hidden">
            <div className="space-y-3 pt-1">
              {entry.archived && (
                <p className="text-xs uppercase tracking-wide text-neutral-400">
                  活動已結束，僅供紀錄
                </p>
              )}
              <a
                href={detailHref}
                className="text-sm text-neutral-600 underline decoration-neutral-300 underline-offset-4 hover:text-neutral-900"
              >
                閱讀完整文章
              </a>
            </div>
          </div>
        </div>
      </div>
    </article>
  );
}

export default function Journal() {
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loadingMore, setLoadingMore] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const sortedEntries = sortNewestFirst(entries);
  const sentinelRefs = useRef<(HTMLDivElement | null)[]>([]);

  useEffect(() => {
    let cancelled = false;
    fetchJournalPostsApi({ page: 1, pageSize: JOURNAL_PAGE_SIZE }).then(
      (result) => {
        if (cancelled) return;
        setEntries(result.posts.map(mapPost));
        setPage(result.page);
        setTotal(result.total);
        if (result.ok) {
          document.querySelector("[data-journal-ssr]")?.setAttribute("hidden", "");
        }
      },
    );
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!sentinelRefs.current.length) return;

    const updateActive = () => {
      const centerY = window.innerHeight / 3;
      let bestIndex = 0;
      let bestDistance = Number.POSITIVE_INFINITY;
      sentinelRefs.current.forEach((node, index) => {
        if (!node) return;
        const rect = node.getBoundingClientRect();
        const distance = Math.abs(rect.top + rect.height / 2 - centerY);
        if (distance < bestDistance) {
          bestDistance = distance;
          bestIndex = index;
        }
      });
      setActiveIndex((current) => (current === bestIndex ? current : bestIndex));
    };

    const observer = new IntersectionObserver(updateActive, {
      rootMargin: "-15% 0px -55% 0px",
      threshold: [0, 0.5, 1],
    });
    sentinelRefs.current.forEach((node) => node && observer.observe(node));
    updateActive();
    return () => observer.disconnect();
  }, [sortedEntries.length]);

  const hasMore = entries.length < total;

  async function loadMore() {
    if (loadingMore || !hasMore) return;
    setLoadingMore(true);
    try {
      const nextPage = page + 1;
      const result = await fetchJournalPostsApi({
        page: nextPage,
        pageSize: JOURNAL_PAGE_SIZE,
      });
      setEntries((prev) => [...prev, ...result.posts.map(mapPost)]);
      setPage(result.page);
      setTotal(result.total);
    } finally {
      setLoadingMore(false);
    }
  }

  return (
    <section className="py-20 md:py-32">
      <div className="container">
        <div className="mx-auto max-w-3xl">
          <p className="mb-2 text-sm tracking-widest text-neutral-500">JOURNAL</p>
          <h1 className="mb-4 text-3xl font-bold tracking-tight text-neutral-900 md:text-5xl">
            品牌日誌
          </h1>
          <p className="mb-6 text-base text-neutral-600 md:text-lg">
            培育鑽石知識分享、品牌動態與展會紀錄。
          </p>
        </div>

        <div className="mx-auto mt-16 max-w-5xl space-y-16 md:mt-24 md:space-y-24">
          {sortedEntries.map((entry, index) => {
            const Icon = JOURNAL_ICONS[index % JOURNAL_ICONS.length];
            const active = index === activeIndex;
            return (
              <div
                key={entry.id}
                aria-current={active ? "true" : "false"}
                className="relative flex flex-col gap-4 md:flex-row md:gap-16"
              >
                <div
                  ref={(element) => {
                    sentinelRefs.current[index] = element;
                  }}
                  aria-hidden="true"
                  className="absolute -top-24 left-0 h-12 w-12 opacity-0"
                />
                <div className="top-8 flex h-min w-full shrink-0 items-center gap-4 md:sticky md:w-64">
                  <div
                    className={
                      "rounded-lg p-2 " +
                      (active
                        ? "bg-[#9cefef] text-[#2b2320]"
                        : "bg-[#f3f0ec] text-[#8a817b]")
                    }
                  >
                    <Icon className="h-4 w-4" aria-hidden="true" />
                  </div>
                  <div className="flex min-w-0 flex-col">
                    <a
                      href={`/journal/${encodeURIComponent(entry.id)}`}
                      className="truncate text-sm font-medium text-neutral-800 hover:text-neutral-500"
                    >
                      {entry.title}
                    </a>
                    <span className="text-xs tabular-nums text-neutral-500">
                      {journalDateLabel(entry.date)}
                    </span>
                  </div>
                </div>
                <div className="relative w-full min-w-0">
                  <EntryCard entry={entry} active={active} />
                </div>
              </div>
            );
          })}
        </div>
      </div>
      {hasMore && (
        <div className="flex justify-center pb-16 pt-16">
          <button
            type="button"
            onClick={loadMore}
            disabled={loadingMore}
            className="text-sm tracking-wide text-neutral-700 underline underline-offset-4 disabled:opacity-50"
          >
            {loadingMore ? "載入中…" : "載入更多"}
          </button>
        </div>
      )}
    </section>
  );
}
