import type { Session } from "@/lib/session";

export type MembershipTierId = "standard" | "companion" | "legacy";

export type MembershipPlan = {
  id: MembershipTierId;
  name: string;
  price: string;
  cadence: string;
};

export type CellValue = boolean | string;

export type MembershipFeature = {
  label: string;
  values: [CellValue, CellValue, CellValue];
};

export type MembershipFeatureGroup = {
  section: string;
  features: MembershipFeature[];
};

export const MEMBERSHIP_ELIGIBLE_ORDER_STATUSES = ["shipped", "completed"] as const;

export function isMembershipEligibleOrderStatus(status: unknown): boolean {
  if (typeof status !== "string") return false;
  return MEMBERSHIP_ELIGIBLE_ORDER_STATUSES.includes(
    status.trim().toLowerCase() as (typeof MEMBERSHIP_ELIGIBLE_ORDER_STATUSES)[number],
  );
}

export function eligibleMembershipOrderCount(orders: unknown): number {
  if (!Array.isArray(orders)) return 0;
  return orders.reduce((count, order) => {
    if (!order || typeof order !== "object") return count;
    const status = (order as { status?: unknown }).status;
    return count + (isMembershipEligibleOrderStatus(status) ? 1 : 0);
  }, 0);
}

export const MEMBERSHIP_PLANS: MembershipPlan[] = [
  { id: "standard", name: "銘印會員", price: "免費", cadence: "註冊即享" },
  { id: "companion", name: "銘印摯友", price: "1 筆訂單", cadence: "完成訂單自動升級" },
  { id: "legacy", name: "銘印典藏", price: "3 筆訂單", cadence: "專屬典藏禮遇" },
];

export const MEMBERSHIP_FEATURE_GROUPS: MembershipFeatureGroup[] = [
  {
    section: "訂製服務",
    features: [
      { label: "線上客製試算", values: [true, true, true] },
      { label: "訂單進度查詢", values: [true, true, true] },
      { label: "購物車儲存配置", values: [true, true, true] },
      { label: "腰圍刻字選項", values: [true, true, true] },
    ],
  },
  {
    section: "會員禮遇",
    features: [
      { label: "會員活動通知", values: [true, true, true] },
      { label: "優先諮詢回覆", values: [false, "即將推出", "即將推出"] },
      { label: "生日驚喜禮", values: [false, "即將推出", "即將推出"] },
      { label: "專屬顧問服務", values: [false, false, true] },
    ],
  },
  {
    section: "服務保障",
    features: [
      { label: "鑑定協助", values: ["基本", "優先", "專人"] },
      { label: "售後保固諮詢", values: [true, true, true] },
      { label: "線下鑑賞邀請", values: [false, false, "即將推出"] },
      { label: "VIP 預約通道", values: [false, false, "即將推出"] },
    ],
  },
];

export function resolveMembershipTier(session: Session, orderTotal: number): MembershipTierId {
  if (session.isAdmin) return "legacy";
  if (orderTotal >= 3) return "legacy";
  if (session.profile?.is_partner) return "companion";
  if (orderTotal >= 1) return "companion";
  return "standard";
}

export function membershipPlanById(id: MembershipTierId): MembershipPlan {
  return MEMBERSHIP_PLANS.find((p) => p.id === id) ?? MEMBERSHIP_PLANS[0];
}

export function membershipDisplayLabel(session: Session, tierId: MembershipTierId): string {
  if (session.isAdmin) return "管理員";
  if (session.profile?.is_partner) return "合作夥伴";
  return membershipPlanById(tierId).name;
}

export function membershipUpgradeHint(tierId: MembershipTierId, orderTotal: number): string | null {
  if (tierId === "legacy") return null;
  if (tierId === "companion") {
    const remaining = Math.max(0, 3 - orderTotal);
    return remaining > 0
      ? `再完成 ${remaining} 筆訂單即可升級「銘印典藏」`
      : null;
  }
  const remaining = Math.max(0, 1 - orderTotal);
  return remaining > 0
    ? `完成首筆訂單即可升級「銘印摯友」`
    : null;
}
