import * as React from "react"
import { Check, Clock, Copy, UserRound } from "lucide-react"

import { cn } from "@/lib/utils"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"

export type MemberAccountCardProps = {
  member: {
    name: string
    email: string
    phone: string
    avatarUrl?: string
    initials: string
    memberId: string
    loginType: string
    shippingCity: string
    shippingPostal: string
    shippingAddress: string
    statusLabel: string
    statusHint: string
  }
  qrCodeUrl?: string
  onUpdateProfile: () => void
  onLogout?: () => void
  className?: string
}

function InfoField({
  label,
  value,
  children,
  className,
}: {
  label: string
  value: string
  children?: React.ReactNode
  className?: string
}) {
  return (
    <div className={cn("flex min-w-0 flex-col", className)}>
      <span className="text-[12px] leading-none text-[#6B7280]">{label}</span>
      <span className="mt-1.5 flex items-center gap-2 text-[14px] font-semibold leading-snug break-all text-[#111827]">
        {value}
        {children}
      </span>
    </div>
  )
}

function CopyButton({ text, label }: { text: string; label: string }) {
  const [copied, setCopied] = React.useState(false)

  return (
    <button
      type="button"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text)
          setCopied(true)
          window.setTimeout(() => setCopied(false), 1500)
        } catch {
          // ignore
        }
      }}
      aria-label={label}
      title={copied ? "已複製" : "複製"}
      className="shrink-0 cursor-pointer text-[#9CA3AF] transition-colors hover:text-[#111827]"
    >
      {copied ? <Check className="h-3.5 w-3.5 text-[#111827]" /> : <Copy className="h-3.5 w-3.5" />}
    </button>
  )
}

export function MemberAccountCard({
  member,
  qrCodeUrl,
  onUpdateProfile,
  onLogout,
  className,
}: MemberAccountCardProps) {
  const cityLine = [member.shippingPostal, member.shippingCity].filter(Boolean).join(" ")
  const addressLine = member.shippingAddress || ""

  return (
    <div
      className={cn(
        "w-full max-w-[420px] rounded-[20px] border border-[#E5E7EB] bg-white p-7 text-[#111827]",
        "shadow-[0_18px_50px_-20px_rgba(15,23,42,0.28),0_8px_20px_-12px_rgba(15,23,42,0.12)]",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3.5">
          <Avatar className="h-[56px] w-[56px] border border-[#E5E7EB] shadow-sm">
            {member.avatarUrl ? <AvatarImage src={member.avatarUrl} alt={member.name} /> : null}
            <AvatarFallback className="bg-[#F3F4F6] text-[15px] font-semibold text-[#111827]">
              {member.initials || <UserRound className="h-5 w-5" />}
            </AvatarFallback>
          </Avatar>
          <div className="min-w-0">
            <div className="flex items-center gap-1.5 text-[13px] text-[#6B7280]">
              <Clock className="h-3.5 w-3.5 shrink-0" strokeWidth={1.75} />
              <span>帳戶狀態</span>
            </div>
            <p className="mt-1 text-[16px] font-semibold leading-tight text-[#111827]">
              {member.statusLabel}
            </p>
            <p className="mt-0.5 text-[12px] leading-snug text-[#6B7280]">
              ({member.statusHint})
            </p>
          </div>
        </div>
        {qrCodeUrl ? (
          <img
            src={qrCodeUrl}
            alt="會員識別 QR"
            className="h-[68px] w-[68px] shrink-0 rounded-[6px] bg-white object-contain"
          />
        ) : (
          <div className="flex h-[68px] w-[68px] shrink-0 items-center justify-center rounded-[6px] border border-[#E5E7EB] bg-[#F9FAFB] text-[9px] font-semibold tracking-[0.16em] text-[#9CA3AF]">
            QR
          </div>
        )}
      </div>

      <div className="my-6 grid grid-cols-2 gap-x-6 gap-y-5 border-y border-[#E5E7EB] py-6">
        <InfoField label="姓名" value={member.name || "—"} />
        <InfoField label="聯絡電話" value={member.phone || "尚未填寫"} />
        <InfoField label="寄送縣市" value={cityLine || "尚未填寫"} />
        <InfoField label="Email" value={member.email || "—"} />
        <InfoField label="會員編號" value={member.memberId}>
          <CopyButton text={member.memberId} label="複製會員編號" />
        </InfoField>
        <InfoField label="登入方式" value={member.loginType} />
        <InfoField label="寄送地址" value={addressLine || "尚未填寫"} className="col-span-1" />
      </div>

      <button
        type="button"
        onClick={onUpdateProfile}
        className="flex h-12 w-full items-center justify-center rounded-[10px] bg-[#111111] text-[15px] font-semibold text-white transition-colors hover:bg-black focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#111111]"
      >
        更新帳戶資料
      </button>

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
  )
}
