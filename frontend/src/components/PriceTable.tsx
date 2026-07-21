import { type ReactNode, useEffect, useMemo, useState } from "react";
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  CARAT_RANGES,
  FANCY_DIAMOND_PRICES,
  FANCY_MULTI_PRICES,
  fmtPrice,
  MOUNTING_LABELS,
  METAL_LABELS,
  SHAPE_SURCHARGE_PCT,
  SNAPSHOT_CARATS,
  SNAPSHOT_LABELS,
  sortedCaratKeys,
  WHITE_DIAMOND_PRICES,
  WHITE_MULTI_PRICES,
} from "@/data/pricing-data";
import {
  buildLiveMountingTable,
  fetchGoldQuote,
  type GoldQuotePayload,
} from "@/lib/mounting-pricing";
import { cn } from "@/lib/utils";

type ColorTab = "white" | "fancy";

const headClass = "h-8 px-1.5 py-1.5";
const cellClass = "px-1.5 py-1.5";
const numHeadClass = cn(headClass, "w-0 whitespace-nowrap text-right");
const numCellClass = cn(cellClass, "w-0 whitespace-nowrap text-right");

function DenseTable({
  caption,
  children,
}: {
  caption?: string;
  children: ReactNode;
}) {
  return (
    <div className="overflow-hidden rounded-lg border border-border bg-background">
      <Table className="[&_th]:px-1.5 [&_td]:px-1.5 [&_th]:py-1.5 [&_td]:py-1.5">
        {caption ? <TableCaption>{caption}</TableCaption> : null}
        {children}
      </Table>
    </div>
  );
}

function ColorTabs({
  value,
  onChange,
}: {
  value: ColorTab;
  onChange: (v: ColorTab) => void;
}) {
  return (
    <div className="mb-4 flex gap-2">
      {(
        [
          ["white", "白鑽"],
          ["fancy", "彩鑽"],
        ] as const
      ).map(([id, label]) => (
        <button
          key={id}
          type="button"
          onClick={() => onChange(id)}
          className={cn(
            "rounded-lg px-4 py-2 text-sm font-medium transition-colors",
            value === id
              ? "bg-primary text-primary-foreground"
              : "bg-muted text-muted-foreground hover:bg-muted/80",
          )}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

function SectionHeading({
  eyebrow,
  title,
  lead,
}: {
  eyebrow: string;
  title: string;
  lead?: string;
}) {
  return (
    <div className="mx-auto mb-8 max-w-2xl text-center">
      <p className="mb-2 text-xs uppercase tracking-[0.2em] text-primary">{eyebrow}</p>
      <h2 className="text-xl font-bold tracking-tight sm:text-2xl md:text-3xl">{title}</h2>
      {lead ? <p className="mt-3 leading-relaxed text-muted-foreground">{lead}</p> : null}
    </div>
  );
}

function SingleDiamondPrice({
  value,
}: {
  value: number | null | undefined;
}) {
  if (value != null) {
    return <span className="font-medium">{fmtPrice(value)}</span>;
  }
  return <span className="text-muted-foreground">無法製作</span>;
}

export default function PriceTable() {
  const [multiTab, setMultiTab] = useState<ColorTab>("white");
  const [goldQuote, setGoldQuote] = useState<GoldQuotePayload | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchGoldQuote().then((data) => {
      if (!cancelled && data) setGoldQuote(data);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const singleCaratKeys = useMemo(
    () =>
      sortedCaratKeys({
        ...WHITE_DIAMOND_PRICES,
        ...FANCY_DIAMOND_PRICES,
      }),
    [],
  );
  const multiTable =
    multiTab === "white" ? WHITE_MULTI_PRICES : FANCY_MULTI_PRICES;
  const multiKeys = sortedCaratKeys(multiTable);

  const liveMounting = useMemo(
    () => buildLiveMountingTable(goldQuote?.alloyRates),
    [goldQuote],
  );
  const mountingStyles = Object.keys(liveMounting);
  const metals = ["9k", "14k", "18k", "pt950", "silver"] as const;
  const goldAsOf = goldQuote?.quote?.fetched_at_display;
  const necklace9k = liveMounting.necklace?.["9k"];

  return (
    <section
      className="price-reference bg-background py-12 md:py-16"
      id="price-reference"
      aria-label="DNA 鑽石價格參考"
    >
      <div className="mx-auto max-w-5xl px-4">
        <SectionHeading
          eyebrow="PRICE REFERENCE"
          title="DNA 鑽石價格參考"
          lead="圓形明亮式切工／白鑽基準價。實際規格請與顧問確認，或使用線上 Calculator／聯絡我們。"
        />

        <div className="mb-12">
          <h3 className="mb-4 text-lg font-semibold">熱門克拉參考</h3>
          <DenseTable caption="圓形明亮式切工／白鑽基準價，0.10 克拉 NT$24,000 起">
            <TableHeader>
              <TableRow className="bg-muted/50">
                <TableHead className={headClass}>克拉</TableHead>
                <TableHead className={headClass}>說明</TableHead>
                <TableHead className={numHeadClass}>價格</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {SNAPSHOT_CARATS.map((c) => (
                <TableRow key={c} className={c === "0.50" ? "bg-primary/5" : undefined}>
                  <TableCell className={cn(cellClass, "font-medium")}>{c} 克拉</TableCell>
                  <TableCell className={cn(cellClass, "text-muted-foreground")}>
                    {SNAPSHOT_LABELS[c]}
                  </TableCell>
                  <TableCell className={cn(numCellClass, "font-medium")}>
                    {fmtPrice(WHITE_DIAMOND_PRICES[c])}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </DenseTable>
        </div>

        <div className="mb-12">
          <h3 className="mb-2 text-lg font-semibold">單顆鑽石・完整克拉價格表</h3>
          <p className="mb-4 text-sm text-muted-foreground">
            白鑽與彩鑽牌價並列對照；彩鑽最低 0.30 克拉。
          </p>
          <DenseTable caption="3.00 克拉以上請洽官方 LINE 專屬報價">
            <TableHeader>
              <TableRow className="bg-muted/50">
                <TableHead className={headClass}>克拉</TableHead>
                <TableHead className={headClass}>實際區間</TableHead>
                <TableHead className={numHeadClass}>白鑽價格</TableHead>
                <TableHead className={numHeadClass}>彩鑽價格</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {singleCaratKeys.map((c) => (
                <TableRow key={c}>
                  <TableCell className={cn(cellClass, "font-medium")}>{c} 克拉</TableCell>
                  <TableCell className={cn(cellClass, "text-muted-foreground")}>
                    {CARAT_RANGES[c] ?? "—"}
                  </TableCell>
                  <TableCell className={numCellClass}>
                    <SingleDiamondPrice value={WHITE_DIAMOND_PRICES[c]} />
                  </TableCell>
                  <TableCell className={numCellClass}>
                    <SingleDiamondPrice value={FANCY_DIAMOND_PRICES[c]} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </DenseTable>
        </div>

        <div className="mb-12">
          <h3 className="mb-2 text-lg font-semibold">多顆珍藏方案</h3>
          <p className="mb-4 text-sm text-muted-foreground">
            同一份樣本可培育 2～4 顆鑽石，適合結髮或全家福系列。顆數越多，平均單顆越划算。
          </p>
          <ColorTabs value={multiTab} onChange={setMultiTab} />
          <DenseTable caption="0.30 克拉以上：沿用 0.30 整組價・2 顆 85 折、3 顆 8 折、4 顆 75 折">
            <TableHeader>
              <TableRow className="bg-muted/50">
                <TableHead className={headClass}>克拉</TableHead>
                <TableHead className={numHeadClass}>2 顆</TableHead>
                <TableHead className={numHeadClass}>3 顆</TableHead>
                <TableHead className={numHeadClass}>4 顆</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {multiKeys.map((c) => {
                const row = multiTable[c] ?? {};
                return (
                  <TableRow key={c}>
                    <TableCell className={cn(cellClass, "font-medium")}>
                      {c} 克拉
                      <span className="mt-0.5 block text-xs text-muted-foreground">
                        {CARAT_RANGES[c]}
                      </span>
                    </TableCell>
                    <TableCell className={numCellClass}>
                      {fmtPrice(row["2"])}
                    </TableCell>
                    <TableCell className={numCellClass}>
                      {fmtPrice(row["3"])}
                    </TableCell>
                    <TableCell className={numCellClass}>
                      {fmtPrice(row["4"])}
                    </TableCell>
                  </TableRow>
                );
              })}
              <TableRow className="text-muted-foreground">
                <TableCell className={cellClass}>0.30 克拉以上</TableCell>
                <TableCell className={numCellClass}>
                  沿用 0.30 整組價・85 折
                </TableCell>
                <TableCell className={numCellClass}>8 折</TableCell>
                <TableCell className={numCellClass}>75 折</TableCell>
              </TableRow>
            </TableBody>
          </DenseTable>
        </div>

        <div className="mb-12">
          <h3 className="mb-2 text-lg font-semibold">飾品戒台費用參考</h3>
          <p className="mb-4 text-sm text-muted-foreground">
            鑽石價格不含飾品戒台；以下為未稅估算，依台銀黃金條塊牌價浮動調整金屬成本
            {necklace9k != null ? (
              <>
                （9K 經典款項鍊 {fmtPrice(necklace9k)} 起）
              </>
            ) : null}
            。
            {goldAsOf ? (
              <span className="mt-1 block text-xs">牌價更新：{goldAsOf}</span>
            ) : null}
          </p>
          <DenseTable caption="戒台依款式與材質另計，正式報價請洽顧問">
            <TableHeader>
              <TableRow className="bg-muted/50">
                <TableHead className={headClass}>款式</TableHead>
                {metals.map((m) => (
                  <TableHead key={m} className={numHeadClass}>
                    {METAL_LABELS[m]}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {mountingStyles.map((style) => (
                <TableRow key={style}>
                  <TableCell className={cn(cellClass, "font-medium")}>
                    {MOUNTING_LABELS[style]}
                  </TableCell>
                  {metals.map((m) => {
                    const price = liveMounting[style]?.[m];
                    return (
                      <TableCell key={m} className={numCellClass}>
                        {price == null || price === 0 ? "—" : fmtPrice(price)}
                      </TableCell>
                    );
                  })}
                </TableRow>
              ))}
            </TableBody>
            <TableFooter>
              <TableRow>
                <TableCell colSpan={6} className={cn(cellClass, "text-sm text-muted-foreground")}>
                  金工價格已含 5% 營業稅；鑽石牌價已含稅
                </TableCell>
              </TableRow>
            </TableFooter>
          </DenseTable>
        </div>

        <div className="mb-10 rounded-xl border border-border bg-muted/30 p-6">
          <h3 className="mb-4 text-lg font-semibold">切工與報價規則</h3>
          <ul className="list-disc space-y-3 pl-5 text-sm leading-relaxed text-muted-foreground">
            <li>
              圓形明亮式切工／白鑽為基準價；其餘切工加價{" "}
              <strong className="text-foreground">{SHAPE_SURCHARGE_PCT}%</strong>
              ，且需 <strong className="text-foreground">0.30 克拉以上</strong>
              才能製作。
            </li>
            <li>
              DNA 鑽石價格<strong className="text-foreground">不含飾品戒台</strong>
              ；戒台依款式與材質另計（9K 經典項鍊 NT$10,000 起，不含鑽）。
            </li>
            <li>因鑽石價格浮動，以上僅供參考，銘印鑽石保有更改之權利。</li>
          </ul>
          <p className="mt-4 text-sm">
            <a
              href="/faq.html"
              className="text-primary underline underline-offset-2 hover:opacity-80"
            >
              更多常見問題 →
            </a>
          </p>
        </div>

        <div className="text-center">
          <a
            className="inline-flex items-center justify-center rounded-lg bg-foreground px-6 py-3 text-sm font-medium text-background transition-opacity hover:opacity-90"
            href="https://lin.ee/ktVBtmx"
            target="_blank"
            rel="noopener noreferrer"
          >
            索取專屬報價
          </a>
        </div>
      </div>
    </section>
  );
}
