import { useEffect, useState } from "react";
import { Timeline } from "@/components/ui/timeline";
import {
  fetchJournalPostsApi,
  type ApiJournalPost,
} from "@/lib/content-api";

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

  useEffect(() => {
    let cancelled = false;
    fetchJournalPostsApi().then((posts) => {
      if (!cancelled) setEntries(posts.map(mapPost));
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const data = sortNewestFirst(entries).map((entry) => {
    const { year, month } = yearMonthFromDate(entry.date);
    return {
      year,
      month,
      content: <EntryCard entry={entry} />,
    };
  });

  return (
    <Timeline
      data={data}
      eyebrow="JOURNAL"
      heading="品牌日誌"
      description="培育鑽石知識分享、品牌動態與展會紀錄。"
    />
  );
}
