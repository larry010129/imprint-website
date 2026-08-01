import * as React from "react";
import { Check, Copy } from "lucide-react";

import {
  deriveMemberDisplayNumber,
  formatMemberDisplayGroups,
  membershipKeepProgress,
  membershipPlanById,
  membershipProgressTowardNext,
  type MembershipProgress,
  type MembershipTierId,
} from "@/lib/membership-tiers";
import { cn } from "@/lib/utils";

export type MembershipCardProps = {
  tierId: MembershipTierId;
  memberName: string;
  memberId: string;
  /** Role override e.g. 管理員 / 合作夥伴 — still shows card metal of tierId */
  roleLabel?: string;
  spend?: number;
  orderCount?: number;
  invites?: number;
  monthCount?: number;
  yearCount?: number;
  progressOverride?: MembershipProgress;
  keepProgressOverride?: MembershipProgress;
  partnerChip?: boolean;
  /** Hide upgrade progress (e.g. membership program master switch off). */
  hideProgress?: boolean;
  /** Override card title (tier name). */
  titleOverride?: string;
  qrCodeUrl?: string;
  onUpdateProfile?: () => void;
  onLogout?: () => void;
  className?: string;
};


function CopyButton({
  text,
  className,
}: {
  text: string;
  className?: string;
}) {
  const [copied, setCopied] = React.useState(false);
  return (
    <button
      type="button"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setCopied(true);
          window.setTimeout(() => setCopied(false), 1500);
        } catch {
          // ignore
        }
      }}
      aria-label="複製會員編號"
      className={cn("shrink-0 opacity-70 transition-opacity hover:opacity-100", className)}
    >
      {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
    </button>
  );
}

function CardProgressBar({
  progress,
  isDark,
  accent,
}: {
  progress: MembershipProgress;
  isDark: boolean;
  accent: { muted: string; chip: string; to: string };
}) {
  return (
    <div className="w-full" title={progress.detail}>
      <div className="mb-0.5 flex items-center justify-between gap-2 text-[9px] sm:text-[10px]">
        <span className="truncate font-medium" style={{ color: accent.muted }}>
          {progress.label}
        </span>
        <span className="shrink-0 tabular-nums opacity-80" style={{ color: accent.muted }}>
          {progress.ratioLabel}
        </span>
      </div>
      <div
        className="h-1.5 w-full overflow-hidden rounded-full"
        style={{
          background: isDark ? "rgba(255,255,255,0.16)" : "rgba(43,35,32,0.12)",
        }}
        role="progressbar"
        aria-valuenow={progress.percent}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${progress.label}，${progress.detail}`}
      >
        <div
          className="h-full rounded-full transition-[width] duration-500 ease-out"
          style={{
            width: `${progress.percent}%`,
            background: isDark
              ? "linear-gradient(90deg, rgba(255,255,255,0.55), rgba(255,255,255,0.95))"
              : `linear-gradient(90deg, ${accent.chip}, ${accent.to})`,
            boxShadow: isDark ? "none" : `0 0 8px ${accent.chip}66`,
          }}
        />
      </div>
    </div>
  );
}

export const MembershipCard = React.memo(function MembershipCard({
  tierId,
  memberName,
  memberId,
  roleLabel,
  spend = 0,
  orderCount = 0,
  invites = 0,
  monthCount = 0,
  yearCount = 0,
  progressOverride,
  keepProgressOverride,
  partnerChip = false,
  hideProgress = false,
  titleOverride,
  qrCodeUrl,
  onUpdateProfile,
  onLogout,
  className,
}: MembershipCardProps) {
  const plan = membershipPlanById(tierId);
  const { accent } = plan;
  const isDark =
    tierId === "star" ||
    tierId === "imprint" ||
    tierId === "partner_star" ||
    tierId === "partner_imprint";
  const idDisplay = formatMemberDisplayGroups(memberId);
  const idCopy = deriveMemberDisplayNumber(memberId);
  const progressCtx = {
    tierId,
    orderCount,
    spend,
    invites,
    monthCount,
    yearCount,
  };
  const progress = progressOverride || membershipProgressTowardNext(progressCtx);
  const keepProgress = keepProgressOverride || membershipKeepProgress(progressCtx);

  return (
    <div className={cn("w-full max-w-[420px]", className)}>
      <div
        className="group relative aspect-[1.586/1] w-full overflow-hidden rounded-[14px] shadow-[0_20px_48px_-18px_rgba(15,23,42,0.38),0_8px_18px_-10px_rgba(15,23,42,0.18)] transition-[transform,box-shadow] duration-300 hover:-translate-y-0.5 hover:shadow-[0_26px_56px_-16px_rgba(15,23,42,0.42)] sm:rounded-[16px]"
        style={{
          background: `linear-gradient(135deg, ${accent.from} 0%, ${accent.to} 55%, ${accent.chip} 160%)`,
          color: accent.text,
          border: `1px solid ${accent.line}`,
        }}
      >
        {/* Metallic sheen */}
        <div
          className="pointer-events-none absolute inset-0 opacity-80 transition-opacity duration-500 group-hover:opacity-100"
          style={{
            background:
              "linear-gradient(115deg, transparent 0%, rgba(255,255,255,0.28) 28%, transparent 42%, transparent 58%, rgba(255,255,255,0.12) 72%, transparent 100%)",
          }}
          aria-hidden="true"
        />
        <div
          className="pointer-events-none absolute -top-1/3 -right-1/4 h-[90%] w-[70%] rounded-full opacity-30"
          style={{
            background: `radial-gradient(circle, ${isDark ? "rgba(255,255,255,0.18)" : "rgba(255,255,255,0.55)"} 0%, transparent 68%)`,
          }}
          aria-hidden="true"
        />

        <div className="relative flex h-full flex-col justify-between px-4 py-3 sm:px-5 sm:py-3.5">
          {/* Top row: brand + badge */}
          <div className="flex items-start justify-between gap-2">
            <div className="flex min-w-0 items-center gap-2.5">
              <img
                src="/favicon.svg"
                alt=""
                aria-hidden="true"
                className={cn(
                  "h-7 w-7 shrink-0 rounded-[5px] object-contain sm:h-8 sm:w-8",
                  isDark && "brightness-0 invert",
                )}
              />
              <div className="min-w-0">
                <p className="text-[10px] font-semibold tracking-[0.14em] uppercase opacity-70 sm:text-[11px]">
                  IMPRINT
                </p>
                <h2 className="truncate text-[17px] font-bold tracking-tight sm:text-[20px]">
                  {titleOverride || plan.name}
                </h2>
              </div>
            </div>
            <div className="flex shrink-0 flex-col items-end gap-1">
              {partnerChip ? (
                <span
                  className="rounded-full px-2 py-0.5 text-[10px] font-semibold tracking-wide"
                  style={{
                    background: isDark ? "rgba(255,255,255,0.2)" : "rgba(43,35,32,0.14)",
                    color: accent.text,
                  }}
                >
                  合作
                </span>
              ) : null}
              <span
                className="rounded-full px-2 py-0.5 text-[10px] font-semibold tracking-wide sm:px-2.5 sm:text-[11px]"
                style={{
                  background: isDark ? "rgba(255,255,255,0.14)" : "rgba(43,35,32,0.1)",
                  color: accent.text,
                }}
              >
                {roleLabel || "目前等級"}
              </span>
            </div>
          </div>

          {/* Mid: member number + progress bars */}
          <div className="mt-0.5 flex flex-1 flex-col justify-center gap-2 sm:gap-2.5">
            <div className="flex items-center gap-2">
              <p
                className="font-mono text-[15px] font-semibold tracking-[0.18em] sm:text-[18px] sm:tracking-[0.22em]"
                style={{
                  textShadow: isDark
                    ? "0 1px 0 rgba(0,0,0,0.35)"
                    : "0 1px 0 rgba(255,255,255,0.35)",
                }}
              >
                {idDisplay || "———— ————"}
              </p>
              <CopyButton text={idCopy} className="mt-0.5" />
            </div>

            {!hideProgress ? (
              <div className="flex w-full max-w-[92%] flex-col gap-1.5">
                <CardProgressBar progress={progress} isDark={isDark} accent={accent} />
                <CardProgressBar progress={keepProgress} isDark={isDark} accent={accent} />
              </div>
            ) : null}
          </div>

          {/* Bottom: holder + QR */}
          <div className="flex items-end justify-between gap-3">
            <div className="min-w-0">
              <p className="text-[9px] font-semibold tracking-[0.16em] uppercase opacity-65 sm:text-[10px]">
                CARDHOLDER
              </p>
              <p className="mt-0.5 truncate text-[13px] font-semibold tracking-wide uppercase sm:text-[15px]">
                {memberName || "—"}
              </p>
            </div>
            {qrCodeUrl ? (
              <img
                src={qrCodeUrl}
                alt=""
                aria-hidden="true"
                className="h-11 w-11 shrink-0 rounded-[6px] bg-white object-contain p-0.5 shadow-sm sm:h-12 sm:w-12"
              />
            ) : (
              <div
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[6px] text-[8px] font-semibold tracking-[0.14em] opacity-50 sm:h-12 sm:w-12"
                style={{
                  border: `1px solid ${accent.line}`,
                  background: isDark ? "rgba(255,255,255,0.06)" : "rgba(255,255,255,0.55)",
                }}
              >
                QR
              </div>
            )}
          </div>
        </div>
      </div>

      {onUpdateProfile ? (
        <button
          type="button"
          onClick={onUpdateProfile}
          className="mt-3 flex h-12 w-full items-center justify-center rounded-[10px] bg-[#111111] text-[15px] font-semibold text-white transition-colors hover:bg-black focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#111111]"
        >
          更新帳戶資料
        </button>
      ) : null}

      {onLogout ? (
        <button
          type="button"
          onClick={onLogout}
          className="mt-3 w-full text-center text-[13px] text-[#6B7280] underline-offset-2 transition-colors hover:text-[#111827] hover:underline"
        >
          登出
        </button>
      ) : null}
    </div>
  );
});
