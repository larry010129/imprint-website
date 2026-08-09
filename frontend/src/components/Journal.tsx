import { useEffect, useState } from "react";
import { Timeline } from "@/components/ui/timeline";
import {
  fetchJournalPostsApi,
  type ApiJournalPost,
} from "@/lib/content-api";

const JOURNAL_PAGE_SIZE = 20;

type JournalEntry = {
  date: string;
  title: string;
  body?: string;
  archived?: boolean;
  imageUrl?: string | null;
};

function yearMonthFromDate(date: string): { year: string; month: string } {
  const [year = "", month = ""] = date.split("-");
  return { year, month };
}

function sortNewestFirst(entries: JournalEntry[]): JournalEntry[] {
  return [...entries].sort((a, b) => b.date.localeCompare(a.date));
}

function mapPost(post: ApiJournalPost): JournalEntry {
  return {
    date: post.posted_at,
    title: post.title,
    body: post.body || undefined,
    archived: post.is_archived,
    imageUrl: post.image_url,
  };
}

function EntryCard({ entry }: { entry: JournalEntry }) {
  return (
    <div>
      <h4 className="text-lg md:text-xl font-semibold text-neutral-800 mb-3">
        {entry.title}
      </h4>
      {entry.archived && (
        <p className="text-xs uppercase tracking-wide text-neutral-400 mb-3">
          活動已結束，僅供紀錄
        </p>
      )}
      {entry.imageUrl && (
        <img
          src={entry.imageUrl}
          alt=""
          loading="lazy"
          decoding="async"
          className="w-full max-w-xl mb-4 rounded-sm object-cover"
        />
      )}
      {entry.body && (
        <p className="text-neutral-600 text-sm md:text-base whitespace-pre-line">
          {entry.body}
        </p>
      )}
    </div>
  );
}

export default function Journal() {
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loadingMore, setLoadingMore] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchJournalPostsApi({ page: 1, pageSize: JOURNAL_PAGE_SIZE }).then(
      (result) => {
        if (cancelled) return;
        setEntries(result.posts.map(mapPost));
        setPage(result.page);
        setTotal(result.total);
      },
    );
    return () => {
      cancelled = true;
    };
  }, []);

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

  const data = sortNewestFirst(entries).map((entry) => {
    const { year, month } = yearMonthFromDate(entry.date);
    return {
      year,
      month,
      content: <EntryCard entry={entry} />,
    };
  });

  return (
    <div>
      <Timeline
        data={data}
        eyebrow="JOURNAL"
        heading="品牌日誌"
        description="培育鑽石知識分享、品牌動態與展會紀錄。"
      />
      {hasMore && (
        <div className="flex justify-center pb-16">
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
    </div>
  );
}
