export type SessionProfile = {
  full_name?: string | null
  phone?: string | null
  store_name?: string | null
  is_partner?: boolean | null
  shipping_postal?: string | null
  shipping_city?: string | null
  shipping_address?: string | null
}

export type SessionUser = {
  id: string
  email: string
}

export type Session = {
  user: SessionUser
  profile?: SessionProfile | null
  isAdmin?: boolean
}

type SharedSessionWindow = Window & {
  __imprintSessionPromise?: Promise<Session | null>
}

function sharedSessionWindow(): SharedSessionWindow {
  return window as SharedSessionWindow
}

function clearSharedSession(): void {
  delete sharedSessionWindow().__imprintSessionPromise
}

function apiBase(): string {
  const base = (window as Window & { IMPRINT_API_BASE?: string }).IMPRINT_API_BASE
  return typeof base === "string" ? base : ""
}

async function request<T>(path: string, init?: RequestInit): Promise<T | null> {
  try {
    const res = await fetch(apiBase() + path, {
      credentials: "include",
      ...init,
      headers: {
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
        ...init?.headers,
      },
    })
    if (!res.ok) return null
    return (await res.json()) as T
  } catch {
    return null
  }
}

export async function fetchSession(): Promise<Session | null> {
  const shared = sharedSessionWindow()
  const existing = shared.__imprintSessionPromise
  if (existing) return existing

  const pending = request<{
    user: SessionUser | null
    profile?: SessionProfile | null
    isAdmin?: boolean
  }>("/api/auth/session").then((data) =>
    data?.user
      ? { user: data.user, profile: data.profile ?? null, isAdmin: !!data.isAdmin }
      : null,
  )
  shared.__imprintSessionPromise = pending
  const session = await pending
  if (!session && shared.__imprintSessionPromise === pending) clearSharedSession()
  return session
}

export async function logoutSession(): Promise<boolean> {
  clearSharedSession()
  const data = await request<{ ok?: boolean }>("/api/auth/logout", { method: "POST" })
  clearSharedSession()
  return !!data?.ok
}

export function truncateNavLabel(text: string, maxLen = 12): string {
  const t = text.trim()
  if (t.length <= maxLen) return t
  return `${t.slice(0, maxLen)}...`
}

export function displayName(session: Session): string {
  const name = session.profile?.full_name?.trim()
  if (name) return name
  const email = session.user.email || ""
  const local = email.split("@")[0]
  return local || "會員"
}

export function initials(session: Session): string {
  const name = displayName(session)
  const parts = name.trim().split(/\s+/)
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
  return name.slice(0, 2).toUpperCase()
}
