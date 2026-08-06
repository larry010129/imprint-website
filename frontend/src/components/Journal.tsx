import { Timeline } from "@/components/ui/timeline";

type JournalEntry = {
  date: string;
  title: string;
  body?: string;
  archived?: boolean;
};

const ENTRIES: JournalEntry[] = [
  {
    date: "2026-03-18",
    title: "如果有一種方式，能把「牠」永遠留在你身邊，你會選擇嗎？",
  },
  {
    date: "2023-12-01",
    title: "寵物展活動記錄",
  },
  {
    date: "2023-11-01",
    title: "銘印鑽石將在台北寵物用品博覽會暨台北貓展與您見面",
    body: "展出地點：台北南港展覽館二館｜11568 台北市南港區經貿二路 2 號　攤位號碼：P1024\n展出日期：2023/11/24（五）至 2023/11/27（一）　展出時間：10:00–18:00",
    archived: true,
  },
  {
    date: "2023-08-02",
    title: "甚麼是實驗室生長鑽石（又稱未來鑽石、人造鑽石、培育鑽石）？與天然鑽石有何不同？",
    body: "人們自數百年前就嘗試合成鑽石，經過無數次的失敗，在上個世紀終於在實驗室合成出鑽石。目前合成寶石級鑽石的方法有兩種：一是高溫高壓法（HPHT），另一則是化學氣相沉積法（CVD）。",
  },
];

export default function Journal() {
  const data = ENTRIES.map((entry) => ({
    title: entry.date,
    content: (
      <div>
        <h4 className="text-lg md:text-xl font-semibold text-neutral-800 mb-3">
          {entry.title}
        </h4>
        {entry.archived && (
          <p className="text-xs uppercase tracking-wide text-neutral-400 mb-3">
            活動已結束，僅供紀錄
          </p>
        )}
        {entry.body && (
          <p className="text-neutral-600 text-sm md:text-base whitespace-pre-line">
            {entry.body}
          </p>
        )}
      </div>
    ),
  }));

  return (
    <Timeline
      data={data}
      eyebrow="JOURNAL"
      heading="品牌日誌"
      description="培育鑽石知識分享、品牌動態與展會紀錄。"
    />
  );
}
