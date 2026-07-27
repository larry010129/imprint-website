import * as React from "react"
import { AnimatePresence, motion } from "motion/react"
import { ArrowLeft, Loader2 } from "lucide-react"

import { MemberAccountCard } from "@/components/ui/member-account-card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { cn } from "@/lib/utils"
import {
  displayName,
  fetchSession,
  initials,
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

function apiBase(): string {
  const base = (window as Window & { IMPRINT_API_BASE?: string }).IMPRINT_API_BASE
  return typeof base === "string" ? base : ""
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
    fetchSession().then((data) => {
      if (cancelled) return
      if (!data) {
        window.location.href =
          "/login.html?next=" + encodeURIComponent(window.location.pathname + window.location.search)
        return
      }
      setSession(data)
      syncForm(data)
      setLoading(false)
    })
    return () => {
      cancelled = true
    }
  }, [syncForm])

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

  if (!session) return null

  const name = displayName(session)
  const phone = session.profile?.phone?.trim() || ""
  const showComplete = wantsCompleteBanner(session)
  const canImport = !!(
    session.hasGoogleLinked &&
    window.IMPRINT_GOOGLE_CLIENT_ID &&
    window.imprintGoogleProfileImport
  )
  const qrCodeUrl = session.user.id
    ? `https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=${encodeURIComponent(`imprint-member:${session.user.id}`)}`
    : undefined

  return (
    <div className="mx-auto flex w-full max-w-[420px] flex-col items-center gap-5 px-1 py-2">
      {showComplete && !session.profileComplete && !editing ? (
        <div className="w-full rounded-[16px] border border-[#E5E7EB] bg-white p-4 shadow-sm">
          <p className="text-sm leading-relaxed text-[#4B5563]">
            歡迎加入！請補齊聯絡電話；寄送地址可稍後填寫。
          </p>
          {canImport ? (
            <Button
              type="button"
              variant="outline"
              className="mt-3 w-full border-[#E5E7EB] bg-white text-[#111827]"
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
            </Button>
          ) : null}
        </div>
      ) : null}

      <div
        className="relative w-full"
        style={{ perspective: 1400 }}
      >
        <AnimatePresence mode="wait" initial={false}>
          {!editing ? (
            <motion.div
              key="card"
              initial={swapIn.initial}
              animate={swapIn.animate}
              exit={swapIn.exit}
              transition={swapTransition}
              style={{ transformOrigin: "center center", backfaceVisibility: "hidden" }}
              className="w-full"
            >
              <MemberAccountCard
                member={{
                  name,
                  email: session.user.email,
                  phone,
                  initials: initials(session),
                  memberId: shortMemberId(session.user.id),
                  loginType: session.hasGoogleLinked ? "Google 帳號" : "Email 密碼",
                  shippingCity: session.profile?.shipping_city?.trim() || "",
                  shippingPostal: session.profile?.shipping_postal?.trim() || "",
                  shippingAddress: session.profile?.shipping_address?.trim() || "",
                  statusLabel: session.profileComplete ? "資料完整" : "待補齊資料",
                  statusHint: session.profileComplete ? "可正常使用會員服務" : "請補齊聯絡電話",
                }}
                qrCodeUrl={qrCodeUrl}
                onUpdateProfile={() => {
                  setMsg(null)
                  setEditing(true)
                }}
                onLogout={handleLogout}
              />
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
                  className="absolute left-0 top-0 inline-flex h-9 w-9 items-center justify-center rounded-full text-[#6B7280] transition-colors hover:bg-[#F3F4F6] hover:text-[#111827]"
                  aria-label="返回帳戶卡片"
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
    </div>
  )
}
