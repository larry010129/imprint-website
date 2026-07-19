/** Spec + price display for checkout — ported from public/js/shop-quote-render.js */

export type ShopConfig = {
  category?: string;
  type?: string;
  summaryZh?: string;
  gold?: string;
  color?: string;
  carat?: string;
  ringSize?: number | string;
  lengthCm?: number | string;
  chainLength?: number | string;
  includeChain?: boolean;
  chainGold?: string;
  chainColor?: string;
  diamondKind?: string;
  fancyColor?: string;
  diamondShape?: string;
  stoneCount?: number;
  engravingBand?: string;
  engravingGirdle?: string;
  series?: string;
};

export type PriceBreakdown = {
  diamondPrice?: number | null;
  taijinPrice?: number | null;
  laborPrice?: number | null;
  metalworkPrice?: number | null;
  chainPrice?: number | null;
  total?: number | null;
  manualOverride?: boolean;
};

export type SpecRow = { label: string; value: string };

const CAT_ZH: Record<string, string> = {
  pendant: "項墜",
  ring: "戒指",
  earring: "耳飾",
  bracelet: "手鍊",
  chain: "鍊條",
};

const GOLD_ZH: Record<string, string> = {
  "9k": "9K",
  "14k": "14K",
  "18k": "18K",
  pt950: "PT950",
  s925: "925銀",
};

const COLOR_ZH: Record<string, string> = {
  white: "白金",
  yellow: "黃金",
  rose: "玫瑰金",
};

const FANCY_COLOR_ZH: Record<string, string> = {
  yellow: "黃",
  pink: "粉",
  blue: "藍",
};

const SHAPE_ZH: Record<string, string> = {
  round: "圓形",
};

export function formatTwdAmount(n?: number | null): string {
  if (n == null || Number.isNaN(Number(n))) return "—";
  return "NT$" + Math.round(Number(n)).toLocaleString("zh-Hant-TW");
}

function materialLabel(gold?: string, color?: string): string {
  if (!gold) return "—";
  const g = GOLD_ZH[gold] || gold;
  if (gold === "pt950" || gold === "s925") return g;
  const c = COLOR_ZH[color || ""] || COLOR_ZH.white;
  return g + c;
}

function caratLabel(carat?: string): string {
  if (!carat) return "—";
  if (carat === "3fen") return "3分";
  if (carat === "4fen") return "4分";
  return carat + "ct";
}

function diamondLabel(config: ShopConfig): string {
  if (config.diamondKind === "fancy") {
    const color = config.fancyColor ? FANCY_COLOR_ZH[config.fancyColor] || config.fancyColor : "";
    return color ? `彩鑽（${color}）` : "彩鑽";
  }
  return "白鑽";
}

function parseConfig(raw: unknown): ShopConfig {
  if (!raw || typeof raw !== "object") return {};
  return raw as ShopConfig;
}

export function itemImageUrl(
  _config: ShopConfig,
  _styleType?: string | null,
  apiImageUrl?: string | null
): string {
  return apiImageUrl || "";
}

export function specRows(configInput: ShopConfig | unknown, summaryZh?: string | null): SpecRow[] {
  const config = parseConfig(configInput);
  const rows: SpecRow[] = [
    { label: "品項", value: CAT_ZH[config.category || ""] || config.category || "—" },
    { label: "款式", value: config.summaryZh || summaryZh || "訂製品項" },
    { label: "金屬材質", value: materialLabel(config.gold, config.color) },
    { label: "克拉", value: caratLabel(config.carat) },
    { label: "鑽石", value: diamondLabel(config) },
  ];

  if (config.diamondShape && config.diamondShape !== "round") {
    rows.push({ label: "形狀", value: SHAPE_ZH[config.diamondShape] || config.diamondShape });
  }
  if (config.stoneCount && config.stoneCount > 1) {
    rows.push({ label: "鑽石顆數", value: String(config.stoneCount) });
  }
  if (config.ringSize) rows.push({ label: "戒圍", value: String(config.ringSize) });
  if (config.lengthCm) rows.push({ label: "長度", value: `${config.lengthCm} cm` });
  if (config.chainLength && config.category !== "chain") {
    rows.push({ label: "鍊長", value: `${config.chainLength} cm` });
  }
  if (config.includeChain) {
    const chainMat =
      config.chainGold || config.chainColor
        ? materialLabel(config.chainGold, config.chainColor)
        : "是";
    rows.push({ label: "搭配鍊條", value: chainMat });
  }
  if (config.engravingBand) rows.push({ label: "戒圈刻字", value: config.engravingBand });
  if (config.engravingGirdle) rows.push({ label: "腰圍刻字", value: config.engravingGirdle });
  if (config.series) rows.push({ label: "系列", value: config.series });

  return rows;
}

export function breakdownRows(breakdown: PriceBreakdown): SpecRow[] {
  if (!breakdown || breakdown.manualOverride) return [];

  const rows: SpecRow[] = [];
  if (breakdown.diamondPrice != null && breakdown.diamondPrice > 0) {
    rows.push({ label: "鑽石價格", value: formatTwdAmount(breakdown.diamondPrice) });
  }

  const metalwork =
    breakdown.metalworkPrice != null
      ? breakdown.metalworkPrice
      : breakdown.taijinPrice != null && breakdown.laborPrice != null
        ? breakdown.taijinPrice + breakdown.laborPrice
        : null;
  if (metalwork != null && metalwork > 0) {
    rows.push({ label: "金工價格", value: formatTwdAmount(metalwork) });
  }
  if (breakdown.chainPrice != null && breakdown.chainPrice > 0) {
    rows.push({ label: "搭配鏈條", value: formatTwdAmount(breakdown.chainPrice) });
  }
  if (breakdown.total != null) {
    rows.push({ label: "小計", value: formatTwdAmount(breakdown.total) });
  }
  return rows;
}

/** Compact line for sidebar (e.g. "14K白金 · 0.3ct") */
export function itemMetaLine(configInput: ShopConfig | unknown, summaryZh?: string | null): string {
  const config = parseConfig(configInput);
  const parts = [
    materialLabel(config.gold, config.color),
    caratLabel(config.carat),
    CAT_ZH[config.category || ""] || config.category,
  ].filter((p) => p && p !== "—");
  if (!parts.length && summaryZh) return summaryZh;
  return parts.slice(0, 3).join(" · ");
}
