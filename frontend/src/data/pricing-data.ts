/** Official pricing from pricing-config.js DEFAULTS (★官方資料). */
export const CARAT_RANGES: Record<string, string> = {
  "0.10": "0.10–0.15ct",
  "0.20": "0.20–0.25ct",
  "0.30": "0.30–0.35ct",
  "0.50": "0.50–0.55ct",
  "0.60": "0.60–0.65ct",
  "0.70": "0.70–0.75ct",
  "0.80": "0.80–0.85ct",
  "0.90": "0.90–0.95ct",
  "1.00": "1.00–1.25ct",
  "1.50": "1.50–1.75ct",
  "2.00": "2.00–2.50ct",
  "3.00": "3.00–3.50ct",
};

export const SNAPSHOT_CARATS = ["0.10", "0.50", "1.00", "3.00"] as const;

export const SNAPSHOT_LABELS: Record<string, string> = {
  "0.10": "低調的日常陪伴",
  "0.50": "最受歡迎・可送鑑定",
  "1.00": "傳家的份量",
  "3.00": "頂級珍藏",
};

export const WHITE_DIAMOND_PRICES: Record<string, number> = {
  "0.10": 24000,
  "0.20": 48000,
  "0.30": 79000,
  "0.50": 98000,
  "0.60": 113000,
  "0.70": 133000,
  "0.80": 159000,
  "0.90": 200000,
  "1.00": 250000,
  "1.50": 380000,
  "2.00": 700000,
  "3.00": 990000,
};

export const FANCY_DIAMOND_PRICES: Record<string, number | null> = {
  "0.30": 102000,
  "0.50": 127000,
  "0.60": 147000,
  "0.70": 172000,
  "0.80": 206000,
  "0.90": 260000,
  "1.00": 325000,
  "1.50": 494000,
  "2.00": 910000,
  "3.00": 1287000,
};

export const WHITE_MULTI_PRICES: Record<string, Record<string, number>> = {
  "0.10": { "2": 45600, "3": 61200, "4": 81000 },
  "0.20": { "2": 86400, "3": 122400, "4": 162000 },
  "0.30": { "2": 142200, "3": 189600, "4": 250000 },
};

export const FANCY_MULTI_PRICES: Record<string, Record<string, number>> = {
  "0.30": { "2": 173400, "3": 244800, "4": 322300 },
};

export const SHAPE_SURCHARGE_PCT = 10;

export const MOUNTING_LABELS: Record<string, string> = {
  loose: "裸鑽",
  necklace: "項鍊",
  ring: "戒指",
  earring: "耳環",
  bracelet: "手鍊",
};

export const METAL_LABELS: Record<string, string> = {
  "9k": "9K",
  "14k": "14K",
  "18k": "18K",
  pt950: "PT950",
  silver: "純銀",
};

/** Mounting fees (未稅, 估算值 except 9K necklace). */
export const MOUNTING_PRICES: Record<
  string,
  Record<string, number>
> = {
  loose: { "18k": 0, "14k": 0, "9k": 0, pt950: 0, silver: 0 },
  necklace: { "18k": 15000, "14k": 12500, "9k": 10000, pt950: 18000, silver: 7000 },
  ring: { "18k": 18000, "14k": 15000, "9k": 12000, pt950: 21500, silver: 8000 },
  earring: { "18k": 21000, "14k": 17500, "9k": 14000, pt950: 25000, silver: 9500 },
  bracelet: { "18k": 24000, "14k": 20000, "9k": 16000, pt950: 29000, silver: 11000 },
};

export function fmtPrice(n: number | null | undefined): string {
  if (n == null) return "—";
  return `NT$ ${n.toLocaleString("zh-TW")}`;
}

export function sortedCaratKeys(table: Record<string, unknown>): string[] {
  return Object.keys(table).sort((a, b) => parseFloat(a) - parseFloat(b));
}
