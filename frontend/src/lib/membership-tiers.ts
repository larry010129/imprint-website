import type { Session } from "@/lib/session";

export type MembershipTrack = "member" | "partner";

export type MemberTierId = "ice" | "platinum" | "rose" | "star" | "imprint";
export type PartnerTierId =
  | "partner_entry"
  | "partner_platinum"
  | "partner_rose"
  | "partner_star"
  | "partner_imprint";

/** Internal IDs only — never show L1–L5 in UI. */
export type MembershipTierId = MemberTierId | PartnerTierId;

export type MembershipAccent = {
  from: string;
  to: string;
  text: string;
  muted: string;
  line: string;
  chip: string;
};

export type MembershipPlan = {
  id: MembershipTierId;
  name: string;
  price: string;
  cadence: string;
  track: MembershipTrack;
  minOrders: number;
  minSpend: number;
  minInvites: number;
  minOrdersPerMonth: number;
  minOrdersPerYear: number;
  inviteOnly: boolean;
  accent: MembershipAccent;
};

export type CellValue = boolean | string;

export type MembershipFeature = {
  label: string;
  values: [CellValue, CellValue, CellValue, CellValue, CellValue];
};

export type MembershipFeatureGroup = {
  section: string;
  features: MembershipFeature[];
};

export type MembershipConfig = {
  /** Master switch — false hides ladder UI on account/profile. */
  enabled?: boolean;
  member: {
    tiers: Array<{
      id: MemberTierId;
      name: string;
      minOrders: number;
      minSpendTwd: number;
      minInvites: number;
      inviteOnly: boolean;
    }>;
    benefitGroups: MembershipFeatureGroup[];
  };
  partner: {
    tiers: Array<{
      id: PartnerTierId;
      name: string;
      minOrdersPerMonth: number;
      minOrdersPerYear: number;
      inviteOnly: boolean;
    }>;
    benefitGroups: MembershipFeatureGroup[];
  };
};

export type OrderLike = {
  status?: unknown;
  total_price?: unknown;
  created_at?: unknown;
};

export const MEMBERSHIP_ELIGIBLE_ORDER_STATUSES = ["shipped", "completed"] as const;

const MEMBER_ACCENTS: Record<MemberTierId, MembershipAccent> = {
  ice: {
    from: "#f4fbfb",
    to: "#9CEFEF",
    text: "#2b2320",
    muted: "#3a7a7a",
    line: "#dcf2f2",
    chip: "#5ecfcf",
  },
  platinum: {
    from: "#f7f8fa",
    to: "#d4dae6",
    text: "#2b2320",
    muted: "#5c6578",
    line: "#c5ccd8",
    chip: "#8b95a8",
  },
  rose: {
    from: "#faf0ec",
    to: "#e8b4a2",
    text: "#2b2320",
    muted: "#8a5a4a",
    line: "#e0c4b8",
    chip: "#c4785a",
  },
  star: {
    from: "#1c2430",
    to: "#2a3340",
    text: "#faf8f6",
    muted: "#b8c4d4",
    line: "#3a4555",
    chip: "#9cb4d4",
  },
  imprint: {
    from: "#141210",
    to: "#2b2320",
    text: "#f5efe6",
    muted: "#d4c4a8",
    line: "#b8956c",
    chip: "#b8956c",
  },
};

const PARTNER_ACCENTS: Record<PartnerTierId, MembershipAccent> = {
  partner_entry: {
    from: "#f7f5f2",
    to: "#e8e0d4",
    text: "#2b2320",
    muted: "#6b5e52",
    line: "#d8cfc3",
    chip: "#a89078",
  },
  partner_platinum: {
    from: "#f4f6f8",
    to: "#c8d0dc",
    text: "#2b2320",
    muted: "#4a5568",
    line: "#b0bac8",
    chip: "#718096",
  },
  partner_rose: {
    from: "#f8ece8",
    to: "#d9a090",
    text: "#2b2320",
    muted: "#7a4a3c",
    line: "#d0b0a4",
    chip: "#b06850",
  },
  partner_star: {
    from: "#161c28",
    to: "#243040",
    text: "#faf8f6",
    muted: "#a8b8cc",
    line: "#3a4860",
    chip: "#7a9cc0",
  },
  partner_imprint: {
    from: "#120f0c",
    to: "#2a2018",
    text: "#f5efe6",
    muted: "#d0b890",
    line: "#a07848",
    chip: "#c4a06a",
  },
};

export const DEFAULT_MEMBERSHIP_CONFIG: MembershipConfig = {
  enabled: true,
  member: {
    tiers: [
      { id: "ice", name: "冰藍卡", minOrders: 0, minSpendTwd: 0, minInvites: 0, inviteOnly: false },
      { id: "platinum", name: "白金卡", minOrders: 1, minSpendTwd: 50000, minInvites: 3, inviteOnly: false },
      { id: "rose", name: "玫瑰金", minOrders: 2, minSpendTwd: 120000, minInvites: 5, inviteOnly: false },
      { id: "star", name: "星鑽卡", minOrders: 3, minSpendTwd: 280000, minInvites: 10, inviteOnly: false },
      { id: "imprint", name: "銘鑽卡", minOrders: 0, minSpendTwd: 0, minInvites: 0, inviteOnly: true },
    ],
    benefitGroups: [
      {
        section: "訂製服務",
        features: [
          { label: "線上客製試算", values: [true, true, true, true, true] },
          { label: "訂單進度查詢", values: [true, true, true, true, true] },
          { label: "購物車儲存配置", values: [true, true, true, true, true] },
          { label: "腰圍刻字選項", values: [true, true, true, true, true] },
          {
            label: "完整設計客製",
            values: ["線上試算", "線上試算", "半客製化", "優先設計諮詢", "專屬全案設計"],
          },
        ],
      },
      {
        section: "會員禮遇",
        features: [
          { label: "會員活動通知", values: [true, true, true, true, true] },
          { label: "生日驚喜禮", values: [false, false, "即將推出", "即將推出", "即將推出"] },
          { label: "專屬顧問服務", values: [false, false, false, true, true] },
          { label: "培育鑽石優惠劵", values: [false, false, "即將推出", "即將推出", "即將推出"] },
        ],
      },
      {
        section: "服務保障",
        features: [
          { label: "鑑定協助", values: ["基本", "基本", "優先", "優先", "專人"] },
          { label: "售後保固諮詢", values: [true, true, true, true, true] },
          { label: "VIP 預約通道", values: [false, false, false, false, "即將推出"] },
        ],
      },
    ],
  },
  partner: {
    tiers: [
      {
        id: "partner_entry",
        name: "合作入門",
        minOrdersPerMonth: 0,
        minOrdersPerYear: 0,
        inviteOnly: false,
      },
      {
        id: "partner_platinum",
        name: "合作白金",
        minOrdersPerMonth: 10,
        minOrdersPerYear: 120,
        inviteOnly: false,
      },
      {
        id: "partner_rose",
        name: "合作玫瑰金",
        minOrdersPerMonth: 30,
        minOrdersPerYear: 360,
        inviteOnly: false,
      },
      {
        id: "partner_star",
        name: "合作星鑽",
        minOrdersPerMonth: 50,
        minOrdersPerYear: 600,
        inviteOnly: false,
      },
      {
        id: "partner_imprint",
        name: "合作銘鑽",
        minOrdersPerMonth: 0,
        minOrdersPerYear: 0,
        inviteOnly: true,
      },
    ],
    benefitGroups: [
      {
        section: "合作服務",
        features: [
          { label: "合作廠商身份", values: [true, true, true, true, true] },
          { label: "批量下單協助", values: [false, true, true, true, true] },
          { label: "優先產能協調", values: [false, false, true, true, true] },
          { label: "專屬業務窗口", values: [false, false, false, true, true] },
          { label: "品牌聯合露出", values: [false, false, false, false, "邀請制"] },
        ],
      },
    ],
  },
};

let liveConfig: MembershipConfig = DEFAULT_MEMBERSHIP_CONFIG;

export function getMembershipConfig(): MembershipConfig {
  return liveConfig;
}

export function setMembershipConfig(config: MembershipConfig | null | undefined): void {
  liveConfig = config ? mergeConfig(config) : DEFAULT_MEMBERSHIP_CONFIG;
}

function traditionalZh(name: string): string {
  // Simplified 蓝 (U+84DD) → Traditional 藍 (U+85CD)
  return name.replace(/\u84dd/g, "\u85cd");
}

export function isMembershipProgramEnabled(config = liveConfig): boolean {
  return config.enabled !== false;
}

function mergeConfig(raw: MembershipConfig): MembershipConfig {
  const base = DEFAULT_MEMBERSHIP_CONFIG;
  return {
    enabled: raw.enabled === undefined ? base.enabled !== false : !!raw.enabled,
    member: {
      tiers: base.member.tiers.map((t) => {
        const hit = raw.member?.tiers?.find((x) => x.id === t.id);
        return hit
          ? {
              ...t,
              name: traditionalZh(String(hit.name || t.name)),
              minOrders: Number(hit.minOrders) || 0,
              minSpendTwd: Number(hit.minSpendTwd) || 0,
              minInvites: Number(hit.minInvites) || 0,
              inviteOnly: !!hit.inviteOnly,
            }
          : t;
      }),
      benefitGroups:
        Array.isArray(raw.member?.benefitGroups) && raw.member.benefitGroups.length
          ? raw.member.benefitGroups
          : base.member.benefitGroups,
    },
    partner: {
      tiers: base.partner.tiers.map((t) => {
        const hit = raw.partner?.tiers?.find((x) => x.id === t.id);
        return hit
          ? {
              ...t,
              name: traditionalZh(String(hit.name || t.name)),
              minOrdersPerMonth: Number(hit.minOrdersPerMonth) || 0,
              minOrdersPerYear: Number(hit.minOrdersPerYear) || 0,
              inviteOnly: !!hit.inviteOnly,
            }
          : t;
      }),
      benefitGroups:
        Array.isArray(raw.partner?.benefitGroups) && raw.partner.benefitGroups.length
          ? raw.partner.benefitGroups
          : base.partner.benefitGroups,
    },
  };
}

function apiBase(): string {
  const base = (window as Window & { IMPRINT_API_BASE?: string }).IMPRINT_API_BASE;
  return typeof base === "string" ? base : "";
}

export async function fetchMembershipConfig(): Promise<MembershipConfig> {
  try {
    const res = await fetch(`${apiBase()}/api/membership-config`, { credentials: "include" });
    if (!res.ok) throw new Error("bad status");
    const data = (await res.json()) as { config?: MembershipConfig };
    setMembershipConfig(data.config);
    return liveConfig;
  } catch {
    setMembershipConfig(null);
    return liveConfig;
  }
}

export function isMembershipEligibleOrderStatus(status: unknown): boolean {
  if (typeof status !== "string") return false;
  return MEMBERSHIP_ELIGIBLE_ORDER_STATUSES.includes(
    status.trim().toLowerCase() as (typeof MEMBERSHIP_ELIGIBLE_ORDER_STATUSES)[number],
  );
}

function parseOrderDate(value: unknown): Date | null {
  if (value instanceof Date && !Number.isNaN(value.getTime())) return value;
  if (typeof value !== "string" && typeof value !== "number") return null;
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? null : d;
}

function taipeiYmd(d: Date): { y: number; m: number; day: number } {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Taipei",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(d);
  const get = (type: string) => Number(parts.find((p) => p.type === type)?.value || 0);
  return { y: get("year"), m: get("month"), day: get("day") };
}

export function rollingTwoYearCutoff(now = new Date()): Date {
  return new Date(now.getTime() - 730 * 24 * 60 * 60 * 1000);
}

export function filterEligibleOrders(orders: unknown): OrderLike[] {
  if (!Array.isArray(orders)) return [];
  return orders.filter((order): order is OrderLike => {
    if (!order || typeof order !== "object") return false;
    return isMembershipEligibleOrderStatus((order as OrderLike).status);
  });
}

export function memberWindowStats(orders: unknown, now = new Date()) {
  const cutoff = rollingTwoYearCutoff(now);
  const eligible = filterEligibleOrders(orders).filter((o) => {
    const d = parseOrderDate(o.created_at);
    return d ? d >= cutoff : false;
  });
  const orderCount = eligible.length;
  const spend = eligible.reduce((sum, o) => {
    const n = Number(o.total_price);
    if (!Number.isFinite(n) || n <= 0) return sum;
    return sum + Math.round(n);
  }, 0);
  return { orderCount, spend, cutoff };
}

export function partnerWindowStats(orders: unknown, now = new Date()) {
  const nowTp = taipeiYmd(now);
  const eligible = filterEligibleOrders(orders);
  let monthCount = 0;
  let yearCount = 0;
  for (const o of eligible) {
    const d = parseOrderDate(o.created_at);
    if (!d) continue;
    const tp = taipeiYmd(d);
    if (tp.y === nowTp.y) {
      yearCount += 1;
      if (tp.m === nowTp.m) monthCount += 1;
    }
  }
  return { monthCount, yearCount };
}

/** @deprecated use memberWindowStats — kept for call sites during migrate */
export function eligibleMembershipOrderCount(orders: unknown): number {
  return memberWindowStats(orders).orderCount;
}

/** @deprecated use memberWindowStats */
export function eligibleMembershipSpend(orders: unknown): number {
  return memberWindowStats(orders).spend;
}

function formatSpend(n: number): string {
  return `NT$${n.toLocaleString("zh-TW")}`;
}

function memberPriceLine(tier: MembershipConfig["member"]["tiers"][number]): string {
  if (tier.inviteOnly) return "僅限邀請";
  if (tier.id === "ice") return "免費";
  const bits: string[] = [];
  if (tier.minOrders > 0) bits.push(`${tier.minOrders} 筆`);
  if (tier.minSpendTwd > 0) bits.push(formatSpend(tier.minSpendTwd));
  return bits.join(" or ") || "—";
}

/** 續卡條件：金額 or 筆數 or 邀請（顯示實際門檻數字） */
function memberCadenceLine(tier: MembershipConfig["member"]["tiers"][number]): string {
  if (tier.inviteOnly) return "僅限邀請";
  if (tier.id === "ice") return "永久";
  const bits: string[] = [];
  if (tier.minSpendTwd > 0) bits.push(formatSpend(tier.minSpendTwd));
  if (tier.minOrders > 0) bits.push(`${tier.minOrders} 筆`);
  if (tier.minInvites > 0) bits.push(`${tier.minInvites} 邀請`);
  return bits.join(" or ") || "—";
}

function partnerPriceLine(tier: MembershipConfig["partner"]["tiers"][number]): string {
  if (tier.inviteOnly) return "僅限邀請";
  if (tier.id === "partner_entry") return "合作身份";
  return `每月 ${tier.minOrdersPerMonth} or 每年 ${tier.minOrdersPerYear}`;
}

export function membershipTrackForSession(session: Session): MembershipTrack {
  if (session.isAdmin && !session.profile?.is_partner) return "member";
  if (session.profile?.is_partner) return "partner";
  return "member";
}

export function plansForTrack(track: MembershipTrack, config = liveConfig): MembershipPlan[] {
  if (track === "partner") {
    return config.partner.tiers.map((t) => ({
      id: t.id,
      name: t.name,
      price: partnerPriceLine(t),
      cadence: t.inviteOnly ? "僅限邀請" : t.id === "partner_entry" ? "永久（合作身份）" : "每月 or 每年重計",
      track: "partner" as const,
      minOrders: t.minOrdersPerMonth,
      minSpend: 0,
      minInvites: 0,
      minOrdersPerMonth: t.minOrdersPerMonth,
      minOrdersPerYear: t.minOrdersPerYear,
      inviteOnly: !!t.inviteOnly,
      accent: PARTNER_ACCENTS[t.id],
    }));
  }
  return config.member.tiers.map((t) => ({
    id: t.id,
    name: t.name,
    price: memberPriceLine(t),
    cadence: memberCadenceLine(t),
    track: "member" as const,
    minOrders: t.minOrders,
    minSpend: t.minSpendTwd,
    minInvites: t.minInvites,
    minOrdersPerMonth: 0,
    minOrdersPerYear: 0,
    inviteOnly: !!t.inviteOnly,
    accent: MEMBER_ACCENTS[t.id],
  }));
}

/** Member-track plans from live config (comparison default). */
export const MEMBERSHIP_PLANS: MembershipPlan[] = plansForTrack("member");

export function refreshMembershipPlansExport(): MembershipPlan[] {
  MEMBERSHIP_PLANS.length = 0;
  MEMBERSHIP_PLANS.push(...plansForTrack("member"));
  return MEMBERSHIP_PLANS;
}

export function featureGroupsForTrack(
  track: MembershipTrack,
  config = liveConfig,
): MembershipFeatureGroup[] {
  return track === "partner" ? config.partner.benefitGroups : config.member.benefitGroups;
}

export const MEMBERSHIP_FEATURE_GROUPS: MembershipFeatureGroup[] =
  DEFAULT_MEMBERSHIP_CONFIG.member.benefitGroups;

export const MEMBERSHIP_PLAN_CTAS: Record<string, { label: string; href: string }> = {
  ice: { label: "開始試算", href: "/shop/calculator.html" },
  platinum: { label: "開始試算", href: "/shop/calculator.html" },
  rose: { label: "查看訂單", href: "/history.html" },
  star: { label: "查看訂單", href: "/history.html" },
  imprint: { label: "聯絡顧問", href: "/contact.html" },
  partner_entry: { label: "開始試算", href: "/shop/calculator.html" },
  partner_platinum: { label: "開始試算", href: "/shop/calculator.html" },
  partner_rose: { label: "查看訂單", href: "/history.html" },
  partner_star: { label: "查看訂單", href: "/history.html" },
  partner_imprint: { label: "聯絡顧問", href: "/contact.html" },
};

function memberQualifies(
  tier: MembershipConfig["member"]["tiers"][number],
  orderCount: number,
  spend: number,
  invites: number,
): boolean {
  if (tier.inviteOnly) return false;
  if (tier.id === "ice") return true;
  return (
    orderCount >= tier.minOrders ||
    spend >= tier.minSpendTwd ||
    (tier.minInvites > 0 && invites >= tier.minInvites)
  );
}

function partnerQualifies(
  tier: MembershipConfig["partner"]["tiers"][number],
  monthCount: number,
  yearCount: number,
): boolean {
  if (tier.inviteOnly) return false;
  if (tier.id === "partner_entry") return true;
  return monthCount >= tier.minOrdersPerMonth || yearCount >= tier.minOrdersPerYear;
}

export type ResolveMembershipInput = {
  session: Session;
  orders?: unknown;
  inviteCount2y?: number;
  config?: MembershipConfig;
  now?: Date;
};

export function resolveMembershipTier(
  session: Session,
  orderCountOrOpts?: number | ResolveMembershipInput,
  spend = 0,
): MembershipTierId {
  // Legacy signature: (session, orderCount, spend)
  if (typeof orderCountOrOpts === "number" || orderCountOrOpts == null) {
    const track = membershipTrackForSession(session);
    if (track === "partner") {
      return resolveMembershipFromContext({
        session,
        orders: [],
        inviteCount2y: session.inviteCount2y || 0,
      });
    }
    const orderCount = typeof orderCountOrOpts === "number" ? orderCountOrOpts : 0;
    const config = liveConfig;
    if (session.isAdmin) return "imprint";
    if (session.imprintInvited || session.profile?.imprint_invited) return "imprint";
    let best: MemberTierId = "ice";
    for (const tier of config.member.tiers) {
      if (memberQualifies(tier, orderCount, spend, session.inviteCount2y || 0)) {
        best = tier.id;
      }
    }
    return best;
  }
  return resolveMembershipFromContext(orderCountOrOpts);
}

export function resolveMembershipFromContext(input: ResolveMembershipInput): MembershipTierId {
  const session = input.session;
  const config = input.config || liveConfig;
  const track = membershipTrackForSession(session);
  const now = input.now || new Date();

  if (track === "partner") {
    if (session.isAdmin || session.partnerImprintInvited || session.profile?.partner_imprint_invited) {
      return "partner_imprint";
    }
    const { monthCount, yearCount } = partnerWindowStats(input.orders, now);
    let best: PartnerTierId = "partner_entry";
    for (const tier of config.partner.tiers) {
      if (partnerQualifies(tier, monthCount, yearCount)) best = tier.id;
    }
    return best;
  }

  if (session.isAdmin || session.imprintInvited || session.profile?.imprint_invited) {
    return "imprint";
  }
  const { orderCount, spend } = memberWindowStats(input.orders, now);
  const invites = input.inviteCount2y ?? session.inviteCount2y ?? 0;
  let best: MemberTierId = "ice";
  for (const tier of config.member.tiers) {
    if (memberQualifies(tier, orderCount, spend, invites)) best = tier.id;
  }
  return best;
}

export function membershipPlanById(
  id: MembershipTierId,
  config = liveConfig,
): MembershipPlan {
  const track = String(id).startsWith("partner_") ? "partner" : "member";
  return plansForTrack(track, config).find((p) => p.id === id) ?? plansForTrack(track, config)[0];
}

export function membershipDisplayLabel(session: Session, tierId: MembershipTierId): string {
  if (session.isAdmin && !session.profile?.is_partner) return "管理員";
  return membershipPlanById(tierId).name;
}

export function membershipUpgradeHint(
  tierId: MembershipTierId,
  orderCountOrMonth: number,
  spendOrYear = 0,
  invites = 0,
): string | null {
  const plan = membershipPlanById(tierId);
  const plans = plansForTrack(plan.track);
  const idx = plans.findIndex((p) => p.id === tierId);
  const next = plans[idx + 1];
  if (!next) return null;
  if (next.inviteOnly) return `「${next.name}」僅限品牌邀請`;

  if (plan.track === "partner") {
    const monthLeft = Math.max(0, next.minOrdersPerMonth - orderCountOrMonth);
    const yearLeft = Math.max(0, next.minOrdersPerYear - spendOrYear);
    if (monthLeft <= 0 || yearLeft <= 0) return null;
    return `本月再完成 ${monthLeft} 筆 or 本年再完成 ${yearLeft} 筆，可升級「${next.name}」`;
  }

  const ordersLeft = Math.max(0, next.minOrders - orderCountOrMonth);
  const spendLeft = Math.max(0, next.minSpend - spendOrYear);
  const inviteLeft = Math.max(0, next.minInvites - invites);
  if (ordersLeft <= 0 || spendLeft <= 0 || (next.minInvites > 0 && inviteLeft <= 0)) return null;
  const inviteBit =
    next.minInvites > 0 ? ` or 邀請滿 ${next.minInvites} 位好友（目前 ${invites}）` : "";
  return `再完成 ${ordersLeft} 筆 or 累計消費滿 ${formatSpend(next.minSpend)}${inviteBit}，即可升級「${next.name}」`;
}

export function formatMembershipSpendLine(spend: number, orderCount: number): string {
  return `消費 ${formatSpend(spend)} · 完成訂單 ${orderCount} 筆`;
}

export type MembershipProgress = {
  percent: number;
  label: string;
  detail: string;
  /** Compact current/target for card UI, e.g. `3/5` or `NT$12,000/NT$50,000`. */
  ratioLabel: string;
  isMax: boolean;
  nextName: string | null;
};

export type ProgressContext = {
  tierId: MembershipTierId;
  orderCount?: number;
  spend?: number;
  invites?: number;
  monthCount?: number;
  yearCount?: number;
};

type RatioCandidate = {
  cur: number;
  max: number;
  format?: (n: number) => string;
};

/** Pick the strongest OR-path and format as `current/target`. */
function bestRatioLabel(candidates: RatioCandidate[]): string {
  let best: RatioCandidate | null = null;
  let bestPct = -1;
  for (const c of candidates) {
    if (c.max <= 0) continue;
    const pct = c.cur / c.max;
    if (pct > bestPct) {
      bestPct = pct;
      best = c;
    }
  }
  if (!best) return "—";
  const fmt = best.format ?? ((n: number) => String(Math.max(0, Math.floor(n))));
  return `${fmt(best.cur)}/${fmt(best.max)}`;
}

function formatRatioNumber(n: number): string {
  return Math.max(0, Math.floor(n)).toLocaleString("zh-TW");
}

function memberRatioCandidates(
  oc: number,
  sp: number,
  inv: number,
  minOrders: number,
  minSpend: number,
  minInvites: number,
): RatioCandidate[] {
  const out: RatioCandidate[] = [];
  if (minSpend > 0) out.push({ cur: sp, max: minSpend, format: formatRatioNumber });
  if (minOrders > 0) out.push({ cur: oc, max: minOrders, format: formatRatioNumber });
  if (minInvites > 0) out.push({ cur: inv, max: minInvites, format: formatRatioNumber });
  return out;
}

function partnerRatioCandidates(
  month: number,
  year: number,
  minMonth: number,
  minYear: number,
): RatioCandidate[] {
  const out: RatioCandidate[] = [];
  if (minMonth > 0) out.push({ cur: month, max: minMonth });
  if (minYear > 0) out.push({ cur: year, max: minYear });
  return out;
}

export function membershipProgressTowardNext(
  tierIdOrCtx: MembershipTierId | ProgressContext,
  orderCount = 0,
  spend = 0,
): MembershipProgress {
  const ctx: ProgressContext =
    typeof tierIdOrCtx === "string"
      ? { tierId: tierIdOrCtx, orderCount, spend }
      : tierIdOrCtx;

  const plan = membershipPlanById(ctx.tierId);
  const plans = plansForTrack(plan.track);
  const idx = plans.findIndex((p) => p.id === ctx.tierId);
  const next = plans[idx + 1];

  if (!next) {
    const detail =
      plan.track === "partner"
        ? `本月 ${ctx.monthCount ?? 0} 筆 · 本年 ${ctx.yearCount ?? 0} 筆`
        : formatMembershipSpendLine(ctx.spend ?? 0, ctx.orderCount ?? 0);
    return {
      percent: 100,
      label: plan.inviteOnly || ctx.tierId.includes("imprint") ? "邀請制最高等級" : "已達最高等級",
      detail,
      ratioLabel: plan.inviteOnly || ctx.tierId.includes("imprint") ? "邀請制" : "滿級",
      isMax: true,
      nextName: null,
    };
  }

  if (next.inviteOnly) {
    return {
      percent: 100,
      label: `「${next.name}」僅限邀請`,
      detail:
        plan.track === "partner"
          ? `本月 ${ctx.monthCount ?? 0} 筆 · 本年 ${ctx.yearCount ?? 0} 筆`
          : formatMembershipSpendLine(ctx.spend ?? 0, ctx.orderCount ?? 0),
      ratioLabel: "邀請制",
      isMax: false,
      nextName: next.name,
    };
  }

  if (plan.track === "partner") {
    const month = ctx.monthCount ?? 0;
    const year = ctx.yearCount ?? 0;
    const monthPct = next.minOrdersPerMonth > 0 ? Math.min(1, month / next.minOrdersPerMonth) : 1;
    const yearPct = next.minOrdersPerYear > 0 ? Math.min(1, year / next.minOrdersPerYear) : 1;
    const percent = Math.round(Math.max(monthPct, yearPct) * 100);
    const ratioLabel = bestRatioLabel(
      partnerRatioCandidates(month, year, next.minOrdersPerMonth, next.minOrdersPerYear),
    );
    return {
      percent,
      label: `升級「${next.name}」`,
      detail: `本月 ${month}/${next.minOrdersPerMonth} · 本年 ${year}/${next.minOrdersPerYear}`,
      ratioLabel,
      isMax: false,
      nextName: next.name,
    };
  }

  const oc = ctx.orderCount ?? 0;
  const sp = ctx.spend ?? 0;
  const inv = ctx.invites ?? 0;
  const orderPct = next.minOrders > 0 ? Math.min(1, oc / next.minOrders) : 1;
  const spendPct = next.minSpend > 0 ? Math.min(1, sp / next.minSpend) : 1;
  const invitePct = next.minInvites > 0 ? Math.min(1, inv / next.minInvites) : 0;
  const percent = Math.round(Math.max(orderPct, spendPct, invitePct) * 100);
  const ratioLabel = bestRatioLabel(
    memberRatioCandidates(oc, sp, inv, next.minOrders, next.minSpend, next.minInvites),
  );
  return {
    percent,
    label: `升級「${next.name}」`,
    detail: formatMembershipSpendLine(sp, oc),
    ratioLabel,
    isMax: false,
    nextName: next.name,
  };
}

/** Progress toward keeping the current tier (續卡), not upgrading. */
export function membershipKeepProgress(
  tierIdOrCtx: MembershipTierId | ProgressContext,
  orderCount = 0,
  spend = 0,
): MembershipProgress {
  const ctx: ProgressContext =
    typeof tierIdOrCtx === "string"
      ? { tierId: tierIdOrCtx, orderCount, spend }
      : tierIdOrCtx;

  const plan = membershipPlanById(ctx.tierId);

  if (plan.inviteOnly || String(ctx.tierId).includes("imprint")) {
    return {
      percent: 100,
      label: "續卡進度",
      detail: "邀請制",
      ratioLabel: "邀請制",
      isMax: true,
      nextName: null,
    };
  }

  if (plan.track === "partner") {
    if (plan.id === "partner_entry" || (plan.minOrdersPerMonth <= 0 && plan.minOrdersPerYear <= 0)) {
      return {
        percent: 100,
        label: "續卡進度",
        detail: "永久（合作身份）",
        ratioLabel: "永久",
        isMax: true,
        nextName: null,
      };
    }
    const month = ctx.monthCount ?? 0;
    const year = ctx.yearCount ?? 0;
    const monthPct =
      plan.minOrdersPerMonth > 0 ? Math.min(1, month / plan.minOrdersPerMonth) : 1;
    const yearPct = plan.minOrdersPerYear > 0 ? Math.min(1, year / plan.minOrdersPerYear) : 1;
    const percent = Math.round(Math.max(monthPct, yearPct) * 100);
    const ratioLabel = bestRatioLabel(
      partnerRatioCandidates(month, year, plan.minOrdersPerMonth, plan.minOrdersPerYear),
    );
    return {
      percent,
      label: "續卡進度",
      detail: `本月 ${month}/${plan.minOrdersPerMonth} · 本年 ${year}/${plan.minOrdersPerYear}`,
      ratioLabel,
      isMax: percent >= 100,
      nextName: null,
    };
  }

  if (plan.id === "ice" || (plan.minOrders <= 0 && plan.minSpend <= 0 && plan.minInvites <= 0)) {
    return {
      percent: 100,
      label: "續卡進度",
      detail: "永久",
      ratioLabel: "永久",
      isMax: true,
      nextName: null,
    };
  }

  const oc = ctx.orderCount ?? 0;
  const sp = ctx.spend ?? 0;
  const inv = ctx.invites ?? 0;
  const orderPct = plan.minOrders > 0 ? Math.min(1, oc / plan.minOrders) : 0;
  const spendPct = plan.minSpend > 0 ? Math.min(1, sp / plan.minSpend) : 0;
  const invitePct = plan.minInvites > 0 ? Math.min(1, inv / plan.minInvites) : 0;
  const percent = Math.round(Math.max(orderPct, spendPct, invitePct) * 100);
  const ratioLabel = bestRatioLabel(
    memberRatioCandidates(oc, sp, inv, plan.minOrders, plan.minSpend, plan.minInvites),
  );
  const bits: string[] = [];
  if (plan.minSpend > 0) bits.push(`${formatSpend(sp)}/${formatSpend(plan.minSpend)}`);
  if (plan.minOrders > 0) bits.push(`${oc}/${plan.minOrders} 筆`);
  if (plan.minInvites > 0) bits.push(`${inv}/${plan.minInvites} 邀請`);
  return {
    percent,
    label: "續卡進度",
    detail: bits.join(" · ") || formatMembershipSpendLine(sp, oc),
    ratioLabel,
    isMax: percent >= 100,
    nextName: null,
  };
}

export function applyFetchedMembershipConfig(config: MembershipConfig): void {
  setMembershipConfig(config);
  refreshMembershipPlansExport();
}

/** Stable 12-digit numeric display id from internal user id (UUID). */
export function deriveMemberDisplayNumber(memberId: string): string {
  const compact = memberId.replace(/[\s-]/g, "").trim().toLowerCase();
  if (!compact || !/^[0-9a-f]+$/.test(compact)) return "";
  try {
    const value = BigInt(`0x${compact}`) % 1_000_000_000_000n;
    return value.toString().padStart(12, "0");
  } catch {
    return "";
  }
}

export function formatMemberDisplayGroups(memberId: string): string {
  const number = deriveMemberDisplayNumber(memberId);
  if (!number) return "———— ————";
  return number.replace(/(.{4})/g, "$1 ").trim();
}
