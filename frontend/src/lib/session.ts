export type SessionProfile = {
  full_name?: string | null
  phone?: string | null
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
  const data = await request<{
    user: SessionUser | null
    profile?: SessionProfile | null
    isAdmin?: boolean
  }>("/api/auth/session")
  if (!data?.user) return null
  return { user: data.user, profile: data.profile ?? null, isAdmin: !!data.isAdmin }
}

export async function logoutSession(): Promise<boolean> {
  const data = await request<{ ok?: boolean }>("/api/auth/logout", { method: "POST" })
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
