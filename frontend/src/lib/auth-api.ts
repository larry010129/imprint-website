const REMEMBER_EMAIL_COOKIE = "imprint_login_email"

function apiBase(): string {
  const api = (window as Window & { imprintAPI?: { getBase?: () => string } }).imprintAPI
  return api?.getBase?.() ?? ""
}

async function parseJson(res: Response) {
  try {
    return await res.json()
  } catch {
    return {}
  }
}

export function getRememberedEmail(): string {
  return document.cookie.split(";").reduce<string>((found, part) => {
    if (found) return found
    const chunk = part.trim()
    if (!chunk.startsWith(`${REMEMBER_EMAIL_COOKIE}=`)) return ""
    try {
      return decodeURIComponent(chunk.slice(REMEMBER_EMAIL_COOKIE.length + 1))
    } catch {
      return chunk.slice(REMEMBER_EMAIL_COOKIE.length + 1)
    }
  }, "")
}

export function storeRememberedEmail(email: string, remember: boolean) {
  if (remember && email) {
    document.cookie = `${REMEMBER_EMAIL_COOKIE}=${encodeURIComponent(email)}; path=/; max-age=${365 * 24 * 60 * 60}; SameSite=Lax`
  } else {
    document.cookie = `${REMEMBER_EMAIL_COOKIE}=; path=/; max-age=0; SameSite=Lax`
  }
}

export async function redirectAfterLogin() {
  const session = await fetchSession()
  const params = new URLSearchParams(window.location.search)
  const next = params.get("next")

  let target = "/account.html"
  if (next) {
    try {
      const url = new URL(next, window.location.origin)
      if (url.origin === window.location.origin) {
        target = `${url.pathname}${url.search}${url.hash}`
      }
    } catch {
      // ignore malformed next
    }
  }

  if (session && session.profileComplete === false) {
    const completeUrl = new URL("/account.html", window.location.origin)
    completeUrl.searchParams.set("complete", "1")
    if (next) {
      try {
        const url = new URL(next, window.location.origin)
        if (url.origin === window.location.origin) {
          completeUrl.searchParams.set("next", `${url.pathname}${url.search}${url.hash}`)
        }
      } catch {
        // ignore malformed next
      }
    }
    window.location.href = `${completeUrl.pathname}${completeUrl.search}`
    return
  }

  window.location.href = target
}

export async function enrichGoogleProfile(accessToken: string) {
  const res = await fetch(`${apiBase()}/api/auth/google-enrich`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ access_token: accessToken }),
  })
  const data = await parseJson(res)
  return { ok: res.ok, status: res.status, data }
}

export async function loginWithPassword(email: string, password: string, remember = true) {
  const res = await fetch(`${apiBase()}/api/auth/login`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, remember }),
  })
  const data = await parseJson(res)
  return { ok: res.ok, status: res.status, data }
}

export async function requestPasswordReset(email: string) {
  const res = await fetch(`${apiBase()}/api/auth/request-password-reset`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  })
  const data = await parseJson(res)
  return { ok: res.ok, status: res.status, data }
}

export async function loginWithGoogleCredential(credential: string) {
  const res = await fetch(`${apiBase()}/api/auth/google`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ credential }),
  })
  const data = await parseJson(res)
  return { ok: res.ok, status: res.status, data }
}

export async function fetchSession() {
  const res = await fetch(`${apiBase()}/api/auth/session`, { credentials: "include" })
  const data = await parseJson(res)
  return data?.user ? data : null
}
