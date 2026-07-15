import * as React from "react"

import { ClipboardList, LayoutDashboard, LogOut, ShoppingCart, User } from "lucide-react"



import {

  displayName,

  initials,

  logoutSession,

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

}



export function AccountMenu({ siteRoot, session }: AccountMenuProps) {

  const [open, setOpen] = React.useState(false)

  const rootRef = React.useRef<HTMLDivElement>(null)

  const loginHref = resolveHref("/login.html", siteRoot)



  React.useEffect(() => {

    if (!open) return

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

  }, [open])



  if (!session) {

    return (

      <div className="account-menu">

        <a

          href={loginHref}

          className="account-menu-trigger account-menu-trigger--guest"

        >

          <span className="account-menu-text">

            <span className="account-menu-name">會員登入</span>

            <span className="account-menu-email">Sign in</span>

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



  const onLogout = async () => {

    setOpen(false)

    await logoutSession()

    window.location.href = resolveHref("/", siteRoot)

  }



  return (

    <div className="account-menu" ref={rootRef}>

      <button

        type="button"

        className="account-menu-trigger"

        aria-expanded={open}

        aria-haspopup="menu"

        onClick={() => setOpen((v) => !v)}

      >

        <span className="account-menu-text">

          <span className="account-menu-name">{name}</span>

          <span className="account-menu-email">{email}</span>

        </span>

        <span className="account-menu-avatar" aria-hidden="true">

          {initials(session)}

        </span>

      </button>



      {open ? (

        <div className="account-menu-panel" role="menu">

          <a

            role="menuitem"

            className="account-menu-item"

            href={resolveHref("/account.html", siteRoot)}

          >

            <User size={16} aria-hidden="true" />

            我的帳戶

          </a>

          <a

            role="menuitem"

            className="account-menu-item"

            href={resolveHref("/history.html", siteRoot)}

          >

            <ClipboardList size={16} aria-hidden="true" />

            訂購紀錄

          </a>

          <a

            role="menuitem"

            className="account-menu-item"

            href={resolveHref("/cart.html", siteRoot)}

          >

            <ShoppingCart size={16} aria-hidden="true" />

            購物車

          </a>

          {session.isAdmin ? (
            <a
              role="menuitem"
              className="account-menu-item account-menu-admin"
              href={resolveHref("/admin.html", siteRoot)}
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

        </div>

      ) : null}

    </div>

  )

}


