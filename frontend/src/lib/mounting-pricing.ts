import { MOUNTING_PRICES } from "@/data/pricing-data";

/** Mirrors public/js/shop-pricing-local.js — labor + metal scaled by live alloy rates. */
/** Universal 金工費 (flat NT$, not taxed). Same for every style. */
const LABOR_FEE_TWD = 5000;

const PURITY_MULTIPLIER: Record<string, number> = {
  "9k": 0.5,
  "14k": 0.75,
  "18k": 0.85,
  pt950: 1.1,
  s925: 0.925,
};

const METAL_SYMBOL: Record<string, "XAU" | "XPT" | "XAG"> = {
  "9k": "XAU",
  "14k": "XAU",
  "18k": "XAU",
  pt950: "XPT",
  s925: "XAG",
};

const FALLBACK_METAL_RAW = { XAU: 4300, XPT: 1050, XAG: 30 } as const;

/** Table column key → /api/bot-gold alloyRates key */
export const MOUNTING_METAL_RATE_KEY: Record<string, string> = {
  "9k": "9k",
  "14k": "14k",
  "18k": "18k",
  pt950: "pt950",
  silver: "s925",
};

export type GoldQuotePayload = {
  quote?: { available?: boolean; fetched_at_display?: string | null; source?: string };
  alloyRates?: Record<string, number>;
};

function baselineRateForMetal(metalKey: string): number {
  const rateKey = MOUNTING_METAL_RATE_KEY[metalKey];
  const symbol = METAL_SYMBOL[rateKey];
  return FALLBACK_METAL_RAW[symbol] * PURITY_MULTIPLIER[rateKey];
}

export function perGramForMetal(
  metalKey: string,
  alloyRates: Record<string, number> | null | undefined,
): number {
  const rateKey = MOUNTING_METAL_RATE_KEY[metalKey];
  const live = alloyRates?.[rateKey];
  if (live != null && Number.isFinite(live)) return live;
  return baselineRateForMetal(metalKey);
}

/** Pre-tax mounting fee; scales metal portion with live BOT alloy rates. */
export function mountingFeePreTax(
  style: string,
  metalKey: string,
  alloyRates: Record<string, number> | null | undefined,
): number {
  const base = MOUNTING_PRICES[style]?.[metalKey] ?? 0;
  if (!base) return 0;

  const labor = LABOR_FEE_TWD;
  const metalPortion = base - labor;
  if (metalPortion <= 0) return base;

  const scale =
    perGramForMetal(metalKey, alloyRates) / baselineRateForMetal(metalKey);
  return Math.round(labor + metalPortion * scale);
}

export function buildLiveMountingTable(
  alloyRates: Record<string, number> | null | undefined,
): Record<string, Record<string, number>> {
  const out: Record<string, Record<string, number>> = {};
  for (const style of Object.keys(MOUNTING_PRICES)) {
    if (style === "loose") continue;
    out[style] = {};
    for (const metal of Object.keys(MOUNTING_PRICES[style])) {
      out[style][metal] = mountingFeePreTax(style, metal, alloyRates);
    }
  }
  return out;
}

export async function fetchGoldQuote(): Promise<GoldQuotePayload | null> {
  try {
    const res = await fetch("/api/bot-gold", { cache: "no-store" });
    if (!res.ok) return null;
    const data = (await res.json()) as GoldQuotePayload;
    if (!data?.quote?.available || !data.alloyRates) return null;
    return data;
  } catch {
    return null;
  }
}
