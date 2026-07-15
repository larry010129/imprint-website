import { useState, type ReactNode } from "react";
import { motion } from "motion/react";
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
} from "@/components/ui/animated-table";
import {
  CARAT_RANGES,
  FANCY_DIAMOND_PRICES,
  FANCY_MULTI_PRICES,
  fmtPrice,
  MOUNTING_LABELS,
  MOUNTING_PRICES,
  METAL_LABELS,
  SHAPE_SURCHARGE_PCT,
  SNAPSHOT_CARATS,
  SNAPSHOT_LABELS,
  sortedCaratKeys,
  WHITE_DIAMOND_PRICES,
  WHITE_MULTI_PRICES,
} from "@/data/pricing-data";
import { cn } from "@/lib/utils";

type ColorTab = "white" | "fancy";

function AnimatedRow({
  index,
  children,
  className,
}: {
  index: number;
  children: ReactNode;
  className?: string;
}) {
  return (
    <motion.tr
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4, delay: index * 0.08 }}
      className={cn(
        "border-b transition-colors hover:bg-muted/50",
        className
      )}
    >
      {children}
    </motion.tr>
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
    <div className="flex gap-2 mb-4">
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
            "px-4 py-2 rounded-lg text-sm font-medium transition-colors",
            value === id
              ? "bg-primary text-white"
              : "bg-muted text-muted-foreground hover:bg-muted/80"
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
    <div className="mb-8 text-center max-w-2xl mx-auto">
      <p className="text-xs tracking-[0.2em] text-primary uppercase mb-2">
        {eyebrow}
      </p>
      <h2 className="text-xl sm:text-2xl md:text-3xl font-bold tracking-tight">
        {title}
      </h2>
      {lead && (
        <p className="mt-3 text-muted-foreground leading-relaxed">{lead}</p>
      )}
    </div>
  );
}

export default function PriceTable() {
  const [singleTab, setSingleTab] = useState<ColorTab>("white");
  const [multiTab, setMultiTab] = useState<ColorTab>("white");

  const singleTable =
    singleTab === "white" ? WHITE_DIAMOND_PRICES : FANCY_DIAMOND_PRICES;
  const singleKeys = sortedCaratKeys(singleTable);
  const multiTable =
    multiTab === "white" ? WHITE_MULTI_PRICES : FANCY_MULTI_PRICES;
  const multiKeys = sortedCaratKeys(multiTable);

  const mountingStyles = Object.keys(MOUNTING_PRICES).filter((k) => k !== "loose");
  const metals = ["9k", "14k", "18k", "pt950", "silver"] as const;

  return (
    <section
      className="price-reference bg-background py-12 md:py-16"
      id="price-reference"
      aria-label="DNA 鑽石價格參考"
    >
      <div className="container mx-auto px-4 max-w-5xl">
        <SectionHeading
          eyebrow="PRICE REFERENCE"
          title="DNA 鑽石價格參考"
          lead="圓形明亮式切工／白鑽基準價。實際規格請與顧問確認，或至各系列頁線上試算。"
        />

        {/* Snapshot */}
        <div className="mb-12">
          <h3 className="text-lg font-semibold mb-4">熱門克拉參考</h3>
          <Table>
            <TableCaption>
              圓形明亮式切工／白鑽基準價，0.10 克拉 NT$24,000 起
            </TableCaption>
            <TableHeader>
              <tr className="border-b">
                <TableHead>克拉</TableHead>
                <TableHead>說明</TableHead>
                <TableHead className="text-right">價格</TableHead>
              </tr>
            </TableHeader>
            <TableBody>
              {SNAPSHOT_CARATS.map((c, i) => (
                <AnimatedRow
                  key={c}
                  index={i}
                  className={c === "0.50" ? "bg-primary/5" : undefined}
                >
                  <TableCell className="font-medium">{c} 克拉</TableCell>
                  <TableCell className="text-muted-foreground">
                    {SNAPSHOT_LABELS[c]}
                  </TableCell>
                  <TableCell className="text-right font-medium">
                    {fmtPrice(WHITE_DIAMOND_PRICES[c])}
                  </TableCell>
                </AnimatedRow>
              ))}
            </TableBody>
          </Table>
        </div>

        {/* Single diamond */}
        <div className="mb-12">
          <h3 className="text-lg font-semibold mb-2">單顆鑽石・完整克拉價格表</h3>
          <ColorTabs value={singleTab} onChange={setSingleTab} />
          <Table>
            <TableCaption>
              {singleTab === "fancy"
                ? "彩鑽最低 0.30 克拉；3.00 克拉以上請洽官方 LINE 專屬報價"
                : "3.00 克拉以上請洽官方 LINE 專屬報價"}
            </TableCaption>
            <TableHeader>
              <tr className="border-b">
                <TableHead>克拉</TableHead>
                <TableHead>實際區間</TableHead>
                <TableHead className="text-right">價格</TableHead>
              </tr>
            </TableHeader>
            <TableBody>
              {singleKeys.map((c, i) => {
                const val = singleTable[c as keyof typeof singleTable];
                return (
                  <AnimatedRow key={c} index={i}>
                    <TableCell className="font-medium">{c} 克拉</TableCell>
                    <TableCell className="text-muted-foreground">
                      {CARAT_RANGES[c] ?? "—"}
                    </TableCell>
                    <TableCell className="text-right font-medium">
                      {val != null ? (
                        fmtPrice(val as number)
                      ) : (
                        <span className="text-muted-foreground">無法製作</span>
                      )}
                    </TableCell>
                  </AnimatedRow>
                );
              })}
            </TableBody>
          </Table>
        </div>

        {/* Multi stone */}
        <div className="mb-12">
          <h3 className="text-lg font-semibold mb-2">多顆珍藏方案</h3>
          <p className="text-sm text-muted-foreground mb-4">
            同一份樣本可培育 2～4 顆鑽石，適合結髮或全家福系列。顆數越多，平均單顆越划算。
          </p>
          <ColorTabs value={multiTab} onChange={setMultiTab} />
          <Table>
            <TableCaption>
              0.30 克拉以上：沿用 0.30 整組價・2 顆 85 折、3 顆 8 折、4 顆 75 折
            </TableCaption>
            <TableHeader>
              <tr className="border-b">
                <TableHead>克拉</TableHead>
                <TableHead className="text-right">2 顆</TableHead>
                <TableHead className="text-right">3 顆</TableHead>
                <TableHead className="text-right">4 顆</TableHead>
              </tr>
            </TableHeader>
            <TableBody>
              {multiKeys.map((c, i) => {
                const row = multiTable[c] ?? {};
                return (
                  <AnimatedRow key={c} index={i}>
                    <TableCell className="font-medium">
                      {c} 克拉
                      <span className="block text-xs text-muted-foreground mt-0.5">
                        {CARAT_RANGES[c]}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      {fmtPrice(row["2"])}
                    </TableCell>
                    <TableCell className="text-right">
                      {fmtPrice(row["3"])}
                    </TableCell>
                    <TableCell className="text-right">
                      {fmtPrice(row["4"])}
                    </TableCell>
                  </AnimatedRow>
                );
              })}
              <AnimatedRow index={multiKeys.length} className="text-muted-foreground">
                <TableCell>0.30 克拉以上</TableCell>
                <TableCell className="text-right">沿用 0.30 整組價・85 折</TableCell>
                <TableCell className="text-right">8 折</TableCell>
                <TableCell className="text-right">75 折</TableCell>
              </AnimatedRow>
            </TableBody>
          </Table>
        </div>

        {/* Mounting */}
        <div className="mb-12">
          <h3 className="text-lg font-semibold mb-2">飾品戒台費用參考</h3>
          <p className="text-sm text-muted-foreground mb-4">
            鑽石價格不含飾品戒台；以下為未稅估算，9K 經典款項鍊 NT$10,000 起為官方公開價格。
          </p>
          <Table>
            <TableCaption>戒台依款式與材質另計，正式報價請洽顧問</TableCaption>
            <TableHeader>
              <tr className="border-b">
                <TableHead>款式</TableHead>
                {metals.map((m) => (
                  <TableHead key={m} className="text-right">
                    {METAL_LABELS[m]}
                  </TableHead>
                ))}
              </tr>
            </TableHeader>
            <TableBody>
              {mountingStyles.map((style, i) => (
                <AnimatedRow key={style} index={i}>
                  <TableCell className="font-medium">
                    {MOUNTING_LABELS[style]}
                  </TableCell>
                  {metals.map((m) => (
                    <TableCell key={m} className="text-right">
                      {MOUNTING_PRICES[style][m] === 0
                        ? "—"
                        : fmtPrice(MOUNTING_PRICES[style][m])}
                    </TableCell>
                  ))}
                </AnimatedRow>
              ))}
            </TableBody>
            <TableFooter>
              <tr>
                <TableCell colSpan={6} className="text-muted-foreground text-sm">
                  戒台費用為未稅金額，顯示時另加 5% 稅金
                </TableCell>
              </tr>
            </TableFooter>
          </Table>
        </div>

        {/* Rules */}
        <div className="mb-10 rounded-xl border border-border bg-muted/30 p-6">
          <h3 className="text-lg font-semibold mb-4">切工與報價規則</h3>
          <ul className="space-y-3 text-sm leading-relaxed text-muted-foreground list-disc pl-5">
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
