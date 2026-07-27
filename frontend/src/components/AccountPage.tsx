import * as React from "react"
import { AnimatePresence, motion } from "motion/react"
import { ArrowLeft, Loader2 } from "lucide-react"

import { MembershipCard } from "@/components/ui/membership-card"
import { MembershipComparison } from "@/components/ui/membership-comparison"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { cn } from "@/lib/utils"
import {
  applyFetchedMembershipConfig,
  fetchMembershipConfig,
  isMembershipProgramEnabled,
  memberWindowStats,
  membershipDisplayLabel,
  membershipTrackForSession,
  membershipUpgradeHint,
  partnerWindowStats,
  resolveMembershipFromContext,
} from "@/lib/membership-tiers"
import {
  displayName,
  fetchSession,
  logoutSession,
  refreshSession,
  type Session,
} from "@/lib/session"

type EnrichResult = {
  ok?: boolean
  error?: string
  message?: string
  imported?: { phone?: boolean; address?: boolean }
  profile?: Session["profile"]
}

type OrderRow = { status?: string | null; total_price?: number | null; created_at?: string | null }

function apiBase(): string {
  const base = (window as Window & { IMPRINT_API_BASE?: string }).IMPRINT_API_BASE
  return typeof base === "string" ? base : ""
}

async function apiFetchOrders(): Promise<OrderRow[]> {
  try {
    const res = await fetch(`${apiBase()}/api/orders`, { credentials: "include" })
    if (!res.ok) return []
    const data = (await res.json()) as { orders?: OrderRow[] }
    return Array.isArray(data.orders) ? data.orders : []
  } catch {
    return []
  }
}

async function patchProfile(body: Record<string, string>) {
  const res = await fetch(`${apiBase()}/api/auth/profile`, {
    method: "PATCH",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  const data = await res.json().catch(() => ({}))
  return { ok: res.ok, status: res.status, data }
}

function shortMemberId(id: string): string {
  const compact = id.replace(/-/g, "").toUpperCase()
  return compact.slice(0, 10) || id.slice(0, 8)
}

function wantsCompleteBanner(session: Session): boolean {
  const params = new URLSearchParams(window.location.search)
  return params.get("complete") === "1" || session.profileComplete === false
}

const swapIn = {
  initial: { opacity: 0, rotateY: 78, scale: 0.96 },
  animate: { opacity: 1, rotateY: 0, scale: 1 },
  exit: { opacity: 0, rotateY: -78, scale: 0.96 },
}

const swapTransition = {
  duration: 0.38,
  ease: [0.22, 1, 0.36, 1] as const,
}

declare global {
  interface Window {
    IMPRINT_GOOGLE_CLIENT_ID?: string
    imprintGoogleProfileImport?: {
      requestImport: (cb: (res: EnrichResult & { _httpStatus?: number }) => void) => void
    }
  }
}

export default function AccountPage() {
  const [loading, setLoading] = React.useState(true)
  const [session, setSession] = React.useState<Session | null>(null)
  const [orders, setOrders] = React.useState<OrderRow[]>([])
  const [configReady, setConfigReady] = React.useState(false)
  const [editing, setEditing] = React.useState(false)
  const [saving, setSaving] = React.useState(false)
  const [importing, setImporting] = React.useState(false)
  const [msg, setMsg] = React.useState<{ text: string; type: "ok" | "err" | "info" } | null>(null)

  const [editName, setEditName] = React.useState("")
  const [editPhone, setEditPhone] = React.useState("")
  const [editPostal, setEditPostal] = React.useState("")
  const [editCity, setEditCity] = React.useState("")
  const [editAddress, setEditAddress] = React.useState("")

  const syncForm = React.useCallback((data: Session) => {
    setEditName(data.profile?.full_name?.trim() || "")
    setEditPhone(data.profile?.phone?.trim() || "")
    setEditPostal(data.profile?.shipping_postal?.trim() || "")
    setEditCity(data.profile?.shipping_city?.trim() || "")
    setEditAddress(data.profile?.shipping_address?.trim() || "")
  }, [])

  React.useEffect(() => {
    let cancelled = false
    ;(async () => {
      const [data, orderRows, config] = await Promise.all([
        fetchSession(),
        apiFetchOrders(),
        fetchMembershipConfig(),
      ])
      if (cancelled) return
      if (!data) {
        window.location.href =
          "/login.html?next=" + encodeURIComponent(window.location.pathname + window.location.search)
        return
      }
      applyFetchedMembershipConfig(config)
      setSession(data)
      syncForm(data)
      setOrders(orderRows)
      setConfigReady(true)
      setLoading(false)
    })()
    return () => {
      cancelled = true
    }
  }, [syncForm])

  const membership = React.useMemo(() => {
    if (!session || !configReady) return null
    const programOn = isMembershipProgramEnabled()
    const track = membershipTrackForSession(session)
    const tierId = resolveMembershipFromContext({
      session,
      orders,
      inviteCount2y: session.inviteCount2y || 0,
    })
    const memberStats = memberWindowStats(orders)
    const partnerStats = partnerWindowStats(orders)
    const upgradeHint = !programOn
      ? null
      : track === "partner"
        ? membershipUpgradeHint(tierId, partnerStats.monthCount, partnerStats.yearCount)
        : membershipUpgradeHint(
            tierId,
            memberStats.orderCount,
            memberStats.spend,
            session.inviteCount2y || 0,
          )
    return {
      programOn,
      tierId,
      track,
      orderCount: memberStats.orderCount,
      spend: memberStats.spend,
      invites: session.inviteCount2y || 0,
      monthCount: partnerStats.monthCount,
      yearCount: partnerStats.yearCount,
      label: programOn
        ? membershipDisplayLabel(session, tierId)
        : session.isAdmin
          ? "管理員"
          : session.profile?.is_partner
            ? "合作廠商"
            : "會員",
      upgradeHint,
      referralCode: session.referralCode || session.profile?.referral_code || "",
    }
  }, [orders, session, configReady])

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    setMsg(null)
    const name = editName.trim()
    const phone = editPhone.trim()
    if (!name) {
      setMsg({ text: "請填寫姓名", type: "err" })
      return
    }
    if (!phone) {
      setMsg({ text: "請填寫聯絡電話", type: "err" })
      return
    }

    setSaving(true)
    const result = await patchProfile({
      fullName: name,
      phone,
      shippingPostal: editPostal.trim(),
      shippingCity: editCity.trim(),
      shippingAddress: editAddress.trim(),
    })
    setSaving(false)

    if (result.status === 401) {
      window.location.href = "/login.html?next=" + encodeURIComponent("/account.html")
      return
    }
    if (!result.ok || result.data.error) {
      setMsg({ text: result.data.error || "儲存失敗，請稍後再試", type: "err" })
      return
    }

    const next = await refreshSession()
    if (next) {
      setSession(next)
      syncForm(next)
    }
    setMsg({ text: "已儲存帳戶資料", type: "ok" })
    setEditing(false)
  }

  function handleGoogleImport() {
    if (!window.imprintGoogleProfileImport) {
      setMsg({ text: "Google 匯入尚未就緒，請重新整理頁面。", type: "err" })
      return
    }
    setMsg(null)
    setImporting(true)
    window.imprintGoogleProfileImport.requestImport(async (res) => {
      setImporting(false)
      if (res?._httpStatus === 401) {
        window.location.href =
          "/login.html?next=" + encodeURIComponent("/account.html?complete=1")
        return
      }
      if (!res || res.error || !res.ok) {
        setMsg({ text: res?.error || "匯入失敗，請稍後再試", type: "err" })
        return
      }
      const parts: string[] = []
      if (res.imported?.phone) parts.push("電話")
      if (res.imported?.address) parts.push("地址")
      setMsg({
        text:
          res.message ||
          (parts.length
            ? `已從 Google 匯入：${parts.join("、")}。`
            : "Google 帳戶中沒有可匯入的資料，請手動填寫。"),
        type: parts.length ? "ok" : "info",
      })
      const next = await refreshSession()
      if (next) {
        setSession(next)
        syncForm(next)
      }
    })
  }

  async function handleLogout() {
    await logoutSession()
    window.location.href = "/"
  }

  if (loading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center text-sm text-[#6B7280]" aria-busy="true">
        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        載入帳戶中…
      </div>
    )
  }

  if (!session || !membership) return null

  const name = displayName(session)
  const showComplete = wantsCompleteBanner(session)
  const canImport = !!(
    session.hasGoogleLinked &&
    window.IMPRINT_GOOGLE_CLIENT_ID &&
    window.imprintGoogleProfileImport
  )
  const qrCodeUrl = session.user.id
    ? `https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=${encodeURIComponent(`imprint-member:${session.user.id}`)}`
    : undefined
  const roleOverride =
    session.isAdmin || session.profile?.is_partner ? membership.label : undefined
  const programOn = membership.programOn

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col items-center gap-8 px-1 py-2">
      {showComplete && !session.profileComplete && !editing ? (
        <div className="w-full max-w-[420px] rounded-[16px] border border-[#E5E7EB] bg-white p-4 shadow-sm">
          <p className="text-sm leading-relaxed text-[#4B5563]">
            歡迎加入！請補齊聯絡電話；寄送地址可稍後填寫。
          </p>
          {canImport ? (
            <button
              type="button"
              className="mt-3 flex h-11 w-full items-center justify-center rounded-[10px] border border-[#E5E7EB] bg-white text-[14px] font-medium text-[#111827] transition-colors hover:bg-[#F9FAFB] disabled:opacity-60"
              disabled={importing}
              onClick={handleGoogleImport}
            >
              {importing ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  匯入中…
                </>
              ) : (
                "從 Google 帳戶匯入電話與地址"
              )}
            </button>
          ) : null}
        </div>
      ) : null}

      <div className="relative w-full max-w-[420px]" style={{ perspective: 1400 }}>
        <AnimatePresence mode="wait" initial={false}>
          {!editing ? (
            <motion.div
              key={programOn ? "member-card" : "account-panel"}
              initial={swapIn.initial}
              animate={swapIn.animate}
              exit={swapIn.exit}
              transition={swapTransition}
              style={{ transformOrigin: "center center", backfaceVisibility: "hidden" }}
              className="w-full"
            >
              {programOn ? (
                <MembershipCard
                  tierId={membership.tierId}
                  memberName={name}
                  memberId={shortMemberId(session.user.id)}
                  roleLabel={roleOverride || membership.label}
                  spend={membership.spend}
                  orderCount={membership.orderCount}
                  invites={membership.invites}
                  monthCount={membership.monthCount}
                  yearCount={membership.yearCount}
                  partnerChip={membership.track === "partner"}
                  qrCodeUrl={qrCodeUrl}
                  onUpdateProfile={() => {
                    setMsg(null)
                    setEditing(true)
                  }}
                  onLogout={handleLogout}
                />
              ) : (
                <div className="w-full rounded-[20px] border border-[#E5E7EB] bg-white p-7 text-[#111827] shadow-[0_18px_50px_-20px_rgba(15,23,42,0.28),0_8px_20px_-12px_rgba(15,23,42,0.12)]">
                  <div className="flex items-center gap-3">
                    <img
                      src="/favicon.svg"
                      alt=""
                      aria-hidden="true"
                      className="h-10 w-10 rounded-[8px] object-contain"
                    />
                    <div className="min-w-0">
                      <p className="text-[11px] font-semibold tracking-[0.14em] text-[#9CA3AF] uppercase">
                        IMPRINT
                      </p>
                      <h2 className="truncate text-[20px] font-semibold tracking-tight">我的帳戶</h2>
                    </div>
                  </div>
                  <div className="mt-6 space-y-3">
                    <div>
                      <p className="text-[12px] text-[#6B7280]">姓名</p>
                      <p className="mt-0.5 text-[16px] font-medium">{name || "—"}</p>
                    </div>
                    <div>
                      <p className="text-[12px] text-[#6B7280]">Email</p>
                      <p className="mt-0.5 break-all text-[15px] text-[#374151]">
                        {session.user.email || "—"}
                      </p>
                    </div>
                    {session.profile?.phone?.trim() ? (
                      <div>
                        <p className="text-[12px] text-[#6B7280]">聯絡電話</p>
                        <p className="mt-0.5 text-[15px] text-[#374151]">
                          {session.profile.phone.trim()}
                        </p>
                      </div>
                    ) : null}
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setMsg(null)
                      setEditing(true)
                    }}
                    className="mt-7 flex h-12 w-full items-center justify-center rounded-[10px] bg-[#111111] text-[15px] font-semibold text-white transition-colors hover:bg-black"
                  >
                    更新帳戶資料
                  </button>
                  <button
                    type="button"
                    onClick={handleLogout}
                    className="mt-3 w-full text-center text-[13px] text-[#6B7280] underline-offset-2 transition-colors hover:text-[#111827] hover:underline"
                  >
                    登出
                  </button>
                </div>
              )}
            </motion.div>
          ) : (
            <motion.form
              key="edit"
              initial={swapIn.initial}
              animate={swapIn.animate}
              exit={swapIn.exit}
              transition={swapTransition}
              style={{ transformOrigin: "center center", backfaceVisibility: "hidden" }}
              onSubmit={handleSave}
              className="w-full space-y-4 rounded-[20px] border border-[#E5E7EB] bg-white p-7 text-[#111827] shadow-[0_18px_50px_-20px_rgba(15,23,42,0.28),0_8px_20px_-12px_rgba(15,23,42,0.12)]"
            >
              <div className="relative mb-1 text-center">
                <button
                  type="button"
                  disabled={saving}
                  onClick={() => {
                    syncForm(session)
                    setEditing(false)
                    setMsg(null)
                  }}
                  className="absolute top-0 left-0 inline-flex h-9 w-9 items-center justify-center rounded-full text-[#6B7280] transition-colors hover:bg-[#F3F4F6] hover:text-[#111827]"
                  aria-label={programOn ? "返回會員卡" : "返回帳戶"}
                >
                  <ArrowLeft className="h-4 w-4" />
                </button>
                <h2 className="text-[18px] font-semibold">更新帳戶資料</h2>
                <p className="mt-1 text-[12px] text-[#6B7280]">Email 由登入帳號決定，無法在此修改。</p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="acc-name" className="text-[12px] text-[#6B7280]">姓名</Label>
                <Input
                  id="acc-name"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  autoComplete="name"
                  required
                  placeholder="請輸入姓名"
                  className="h-11 border-[#E5E7EB] bg-white"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="acc-phone" className="text-[12px] text-[#6B7280]">聯絡電話</Label>
                <Input
                  id="acc-phone"
                  type="tel"
                  value={editPhone}
                  onChange={(e) => setEditPhone(e.target.value)}
                  autoComplete="tel"
                  required
                  placeholder="請輸入電話"
                  className="h-11 border-[#E5E7EB] bg-white"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="acc-email" className="text-[12px] text-[#6B7280]">Email</Label>
                <Input
                  id="acc-email"
                  value={session.user.email}
                  disabled
                  readOnly
                  className="h-11 border-[#E5E7EB] bg-[#F9FAFB]"
                />
              </div>

              <div className="border-t border-[#E5E7EB] pt-4">
                <p className="text-[14px] font-semibold">寄送地址</p>
                <p className="mt-1 text-[12px] text-[#6B7280]">結帳選宅配時會自動帶入；可留空。</p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="acc-postal" className="text-[12px] text-[#6B7280]">郵遞區號</Label>
                <Input
                  id="acc-postal"
                  value={editPostal}
                  onChange={(e) => setEditPostal(e.target.value)}
                  autoComplete="postal-code"
                  inputMode="numeric"
                  placeholder="例：106"
                  className="h-11 border-[#E5E7EB] bg-white"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="acc-city" className="text-[12px] text-[#6B7280]">縣市／區</Label>
                <Input
                  id="acc-city"
                  value={editCity}
                  onChange={(e) => setEditCity(e.target.value)}
                  autoComplete="address-level1"
                  placeholder="例：台北市大安區"
                  className="h-11 border-[#E5E7EB] bg-white"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="acc-address" className="text-[12px] text-[#6B7280]">詳細地址</Label>
                <Input
                  id="acc-address"
                  value={editAddress}
                  onChange={(e) => setEditAddress(e.target.value)}
                  autoComplete="street-address"
                  placeholder="路名、巷弄、樓層"
                  className="h-11 border-[#E5E7EB] bg-white"
                />
              </div>

              {msg ? (
                <p
                  className={cn(
                    "text-sm",
                    msg.type === "ok" && "text-emerald-700",
                    msg.type === "err" && "text-red-600",
                    msg.type === "info" && "text-[#6B7280]",
                  )}
                  role="status"
                >
                  {msg.text}
                </p>
              ) : null}

              <div className="flex flex-col gap-2 pt-1">
                <button
                  type="submit"
                  disabled={saving}
                  className="flex h-12 w-full items-center justify-center rounded-[10px] bg-[#111111] text-[15px] font-semibold text-white transition-colors hover:bg-black disabled:opacity-60"
                >
                  {saving ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      儲存中…
                    </>
                  ) : (
                    "儲存帳戶資料"
                  )}
                </button>
                <button
                  type="button"
                  disabled={saving}
                  onClick={() => {
                    syncForm(session)
                    setEditing(false)
                    setMsg(null)
                  }}
                  className="h-11 w-full rounded-[10px] border border-[#E5E7EB] bg-white text-[14px] font-medium text-[#374151] transition-colors hover:bg-[#F9FAFB]"
                >
                  取消
                </button>
              </div>
            </motion.form>
          )}
        </AnimatePresence>
      </div>

      {!editing && msg ? (
        <p
          className={cn(
            "text-center text-sm",
            msg.type === "ok" && "text-emerald-700",
            msg.type === "err" && "text-red-600",
            msg.type === "info" && "text-[#6B7280]",
          )}
        >
          {msg.text}
        </p>
      ) : null}

      {!editing && membership.programOn && membership.referralCode ? (
        <p className="max-w-[420px] text-center text-[13px] text-[#6B7280]">
          好友邀請碼：
          <span className="font-mono font-semibold tracking-wide text-[#111827]">
            {membership.referralCode}
          </span>
          <span className="mt-1 block text-[12px]">好友註冊時填入，可協助維持會員等級</span>
        </p>
      ) : null}

      {!editing && membership.programOn ? (
        <div className="w-full">
          <MembershipComparison
            currentTierId={membership.tierId}
            upgradeHint={membership.upgradeHint}
            track={membership.track}
          />
        </div>
      ) : null}
    </div>
  )
}
