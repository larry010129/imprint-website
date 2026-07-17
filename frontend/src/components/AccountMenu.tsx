import * as React from "react"

import { ClipboardList, LayoutDashboard, LogOut, ShoppingCart, User } from "lucide-react"

import {
  displayName,
  initials,
  logoutSession,
  truncateNavLabel,
  type Session,
} from "@/lib/session"

function resolveHref(href: string, siteRoot: string): string {
  if (/^(https?:|tel:|mailto:)/.test(href)) return href
  if (!siteRoot) return href
  let path = href.startsWith("/") ? href.slice(1) : href
  if (path === "") path = "index.html"
  else if (path.endsWith("/")) path += "index.html"
  return siteRoot + path
}

type AccountMenuProps = {
  siteRoot: string
  session: Session | null
  variant?: "default" | "drawer"
  onNavigate?: () => void
}

function AccountLinks({
  siteRoot,
  session,
  onNavigate,
  onLogout,
}: {
  siteRoot: string
  session: Session
  onNavigate?: () => void
  onLogout: () => void
}) {
  return (
    <>
      <a
        role="menuitem"
        className="account-menu-item"
        href={resolveHref("/account.html", siteRoot)}
        onClick={onNavigate}
      >
        <User size={16} aria-hidden="true" />
        我的帳戶
      </a>
      <a
        role="menuitem"
        className="account-menu-item"
        href={resolveHref("/history.html", siteRoot)}
        onClick={onNavigate}
      >
        <ClipboardList size={16} aria-hidden="true" />
        訂購紀錄
      </a>
      <a
        role="menuitem"
        className="account-menu-item"
        href={resolveHref("/cart.html", siteRoot)}
        onClick={onNavigate}
      >
        <ShoppingCart size={16} aria-hidden="true" />
        購物車
      </a>
      {session.isAdmin ? (
        <a
          role="menuitem"
          className="account-menu-item account-menu-admin"
          href={resolveHref("/admin.html", siteRoot)}
          onClick={onNavigate}
        >
          <LayoutDashboard size={16} aria-hidden="true" />
          管理後台
        </a>
      ) : null}
      <button
        type="button"
        role="menuitem"
        className="account-menu-item account-menu-logout"
        onClick={onLogout}
      >
        <LogOut size={16} aria-hidden="true" />
        登出
      </button>
    </>
  )
}

export function AccountMenu({
  siteRoot,
  session,
  variant = "default",
  onNavigate,
}: AccountMenuProps) {
  const [open, setOpen] = React.useState(false)
  const rootRef = React.useRef<HTMLDivElement>(null)
  const loginHref = resolveHref("/login.html", siteRoot)
  const isDrawer = variant === "drawer"

  React.useEffect(() => {
    if (!open || isDrawer) return
    const onDoc = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false)
    }
    document.addEventListener("mousedown", onDoc)
    document.addEventListener("keydown", onKey)
    return () => {
      document.removeEventListener("mousedown", onDoc)
      document.removeEventListener("keydown", onKey)
    }
  }, [open, isDrawer])

  const onLogout = async () => {
    setOpen(false)
    onNavigate?.()
    await logoutSession()
    window.location.href = resolveHref("/", siteRoot)
  }

  if (!session) {
    if (isDrawer) {
      return (
        <a
          href={loginHref}
          className="mobile-animated-nav__link"
          onClick={onNavigate}
        >
          會員登入
        </a>
      )
    }

    return (
      <div className="account-menu">
        <a
          href={loginHref}
          className="account-menu-trigger account-menu-trigger--guest"
          aria-label="會員登入"
        >
          <span className="account-menu-text">
            <span className="account-menu-name">會員登入</span>
          </span>
          <span className="account-menu-avatar account-menu-avatar--guest" aria-hidden="true">
            <User size={16} strokeWidth={2.25} />
          </span>
        </a>
      </div>
    )
  }

  const name = displayName(session)
  const email = session.user.email
  const nameLabel = truncateNavLabel(name, 10)

  if (isDrawer) {
    return (
      <>
        <p className="mobile-animated-nav__account-label">{name}</p>
        <ul className="mobile-animated-nav__sublist mobile-animated-nav__sublist--account">
          <li>
            <a
              href={resolveHref("/account.html", siteRoot)}
              className="mobile-animated-nav__sublink"
              onClick={onNavigate}
            >
              我的帳戶
            </a>
          </li>
          <li>
            <a
              href={resolveHref("/history.html", siteRoot)}
              className="mobile-animated-nav__sublink"
              onClick={onNavigate}
            >
              訂購紀錄
            </a>
          </li>
          <li>
            <a
              href={resolveHref("/cart.html", siteRoot)}
              className="mobile-animated-nav__sublink"
              onClick={onNavigate}
            >
              購物車
            </a>
          </li>
          {session.isAdmin ? (
            <li>
              <a
                href={resolveHref("/admin.html", siteRoot)}
                className="mobile-animated-nav__sublink"
                onClick={onNavigate}
              >
                管理後台
              </a>
            </li>
          ) : null}
          <li>
            <button
              type="button"
              className="mobile-animated-nav__sublink mobile-animated-nav__sublink--button"
              onClick={onLogout}
            >
              登出
            </button>
          </li>
        </ul>
      </>
    )
  }

  return (
    <div className="account-menu" ref={rootRef}>
      <button
        type="button"
        className="account-menu-trigger"
        aria-expanded={open}
        aria-haspopup="menu"
        aria-label={nameLabel}
        title={`${name}\n${email}`}
        onClick={() => setOpen((v) => !v)}
      >
        <span className="account-menu-text">
          <span className="account-menu-name">{nameLabel}</span>
        </span>
        <span className="account-menu-avatar" aria-hidden="true">
          {initials(session)}
        </span>
      </button>

      {open ? (
        <div className="account-menu-panel" role="menu">
          <AccountLinks
            siteRoot={siteRoot}
            session={session}
            onLogout={onLogout}
          />
        </div>
      ) : null}
    </div>
  )
}
