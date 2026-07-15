import * as React from "react"

import { AccountMenu } from "@/components/AccountMenu"
import { fetchSession, type Session } from "@/lib/session"

type NavChild = {
  label: string
  href: string
}

type NavItem = {
  id: string
  label: string
  href: string
  children?: NavChild[]
}

const NAV_ITEMS: NavItem[] = [
  {
    id: "shop",
    label: "珠寶試算",
    href: "/shop/calculator/",
    children: [
      { label: "戒台試算", href: "/shop/calculator/" },
      { label: "DNA 鑽石價格", href: "/price.html" },
      { label: "台銀金價", href: "/gold-price.html" },
    ],
  },
  { id: "diamonds", label: "DNA 鑽石", href: "/diamonds.html" },
  {
    id: "jewelry",
    label: "時尚珠寶",
    href: "/jewelry/",
    children: [
      { label: "戒指", href: "/jewelry/rings/" },
      { label: "項鍊", href: "/jewelry/necklaces/" },
      { label: "耳環", href: "/jewelry/earrings/" },
      { label: "手鍊", href: "/jewelry/bracelets/" },
    ],
  },
  {
    id: "knowledge",
    label: "鑽石知識",
    href: "/what-is-dna-diamond.html",
    children: [
      { label: "DNA 鑽石的誕生", href: "/what-is-dna-diamond.html" },
      { label: "常見問題", href: "/faq.html" },
    ],
  },
  {
    id: "about",
    label: "關於我們",
    href: "/about.html",
    children: [
      { label: "品牌故事", href: "/about.html" },
      { label: "客戶見證", href: "/stories.html" },
      { label: "聯絡我們", href: "/contact.html" },
    ],
  },
  { id: "track-order", label: "查詢訂製進度", href: "/track-order.html" },
]

const BRAND_PATH =
  "M12299 14276l-1463 -1021c-1,-1 -3,-2 -4,-3 -28,-19 -35,-58 -15,-85 135,-193 384,-30 400,-19 1,0 1,1 2,1l1123 784 715 -442 0 -1169 -715 -442 -1658 1153 0 0c-86,60 2,-1 -86,60 -217,152 -769,540 -850,596 -49,33 -83,57 -118,82l-3 2c-143,100 -304,213 -463,306 -163,95 -325,170 -466,192 -25,4 -49,7 -71,9 -24,2 -48,3 -70,3 -101,0 -199,-17 -292,-51 -92,-34 -177,-83 -253,-149 -87,-75 -157,-166 -204,-265 -48,-100 -74,-208 -74,-315 0,-118 33,-236 93,-346 49,-90 116,-174 198,-249 -82,-75 -149,-160 -198,-250 -60,-111 -93,-229 -93,-346 0,-107 26,-215 74,-315 48,-99 117,-190 204,-265 94,-81 203,-138 319,-170 116,-32 241,-39 367,-19 142,22 304,97 467,193 159,93 320,206 464,307l14 10c31,21 60,42 104,72 52,36 297,208 523,366l90 63c26,18 35,52 19,80 -7,12 -54,89 -157,103 -50,7 -114,-2 -192,-42 -3,-2 -6,-3 -9,-5 -174,-122 -247,-173 -283,-199 -74,-52 -134,-94 -164,-114l0 0 0 0c-11,-8 -31,-21 -55,-38 -1,-1 -3,-2 -4,-3 -68,-48 9,6 -62,-43 -126,-89 -276,-194 -422,-281 -141,-84 -277,-151 -380,-167 -83,-13 -163,-9 -238,12 -74,20 -143,56 -203,107 -54,46 -97,102 -127,162 -29,59 -45,122 -45,184 0,80 30,164 82,244 54,81 131,156 225,214 2,1 4,2 6,4l50 35c17,11 29,30 29,52l0 96 0 0c0,19 -9,38 -26,50l-52 36 0 0c-1,1 -2,1 -3,2 -95,58 -174,134 -228,215 -52,79 -82,164 -82,244 0,62 16,126 45,185 29,60 73,116 127,162 60,51 128,87 202,107 74,20 152,24 233,12 2,0 3,-1 5,-1 208,-32 547,-269 797,-443 1,-1 2,-2 3,-2l1 0 0 0 0 0c53,-37 36,-25 63,-44 15,-10 34,-24 60,-42 104,-71 2653,-1849 2722,-1898 20,-15 47,-17 69,-3l963 596c20,10 34,31 34,55l0 1442 0 0c0,20 -10,40 -29,52l-968 599 0 0c-20,12 -47,12 -67,-2z"

function resolveHref(href: string, siteRoot: string): string {
  if (/^(https?:|tel:|mailto:)/.test(href)) return href
  if (!siteRoot) return href
  let path = href.startsWith("/") ? href.slice(1) : href
  if (path === "") path = "index.html"
  else if (path.endsWith("/")) path += "index.html"
  return siteRoot + path
}

function useSiteRoot(): string {
  return document.body.dataset.siteRoot ?? ""
}

function ChevronIcon() {
  return (
    <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
      <path
        d="M6 9l6 6 6-6"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function NavList({ siteRoot }: { siteRoot: string }) {
  return (
    <ul className="nav-menu" data-safe-triangle-menu>
      {NAV_ITEMS.map((item) => (
        <li key={item.id} className="nav-item" data-nav-id={item.id}>
          <a href={resolveHref(item.href, siteRoot)}>{item.label}</a>
          {item.children?.length ? (
            <>
              <button
                type="button"
                className="dd-toggle"
                aria-label={`展開 ${item.label} 子選單`}
                aria-expanded="false"
              >
                <ChevronIcon />
              </button>
              <div className="dropdown">
                {item.children.map((child) => (
                  <a key={child.href} href={resolveHref(child.href, siteRoot)}>
                    {child.label}
                  </a>
                ))}
              </div>
            </>
          ) : null}
        </li>
      ))}
    </ul>
  )
}

export default function SiteNav() {
  const siteRoot = useSiteRoot()
  const homeHref = resolveHref("/", siteRoot)
  const headerRef = React.useRef<HTMLElement>(null)
  const [session, setSession] = React.useState<Session | null>(null)

  React.useEffect(() => {
    let active = true
    fetchSession().then((data) => {
      if (active) setSession(data)
    })
    return () => {
      active = false
    }
  }, [])

  React.useEffect(() => {
    const header = headerRef.current
    if (!header) return
    const root = header.parentElement

    const onNavScroll = () => {
      const scrolled = window.scrollY > 10
      header.classList.toggle("is-scrolled", scrolled)
      if (root?.matches("[data-site-nav-root]")) {
        root.classList.toggle(
          "is-nav-hero",
          document.body.classList.contains("page-home") && !scrolled,
        )
      }
    }
    window.addEventListener("scroll", onNavScroll, { passive: true })
    onNavScroll()

    const burger = header.querySelector<HTMLButtonElement>(".nav-burger")
    const menu = header.querySelector<HTMLElement>(".site-nav-mobile .nav-menu")
    if (!burger || !menu) return

    const onBurgerClick = () => {
      burger.classList.toggle("is-open")
      menu.classList.toggle("is-open")
      document.body.style.overflow = menu.classList.contains("is-open")
        ? "hidden"
        : ""
    }

    const toggles = menu.querySelectorAll<HTMLButtonElement>(
      ":scope > .nav-item > .dd-toggle",
    )
    const toggleHandlers = Array.from(toggles).map((toggle) => {
      const item = toggle.closest(".nav-item")
      if (!item) return () => {}

      const onToggleClick = () => {
        const willOpen = !item.classList.contains("is-open")
        item.classList.toggle("is-open", willOpen)
        toggle.setAttribute("aria-expanded", willOpen ? "true" : "false")
      }
      toggle.addEventListener("click", onToggleClick)
      return () => toggle.removeEventListener("click", onToggleClick)
    })

    const dropdownLinks = menu.querySelectorAll<HTMLAnchorElement>(
      ".dropdown a",
    )
    const linkHandlers = Array.from(dropdownLinks).map((link) => {
      const onLinkClick = () => {
        if (
          window.innerWidth <= 860 &&
          link.getAttribute("href") &&
          link.getAttribute("href") !== "#"
        ) {
          burger.classList.remove("is-open")
          menu.classList.remove("is-open")
          document.body.style.overflow = ""
        }
      }
      link.addEventListener("click", onLinkClick)
      return () => link.removeEventListener("click", onLinkClick)
    })

    burger.addEventListener("click", onBurgerClick)
    return () => {
      window.removeEventListener("scroll", onNavScroll)
      burger.removeEventListener("click", onBurgerClick)
      toggleHandlers.forEach((off) => off())
      linkHandlers.forEach((off) => off())
    }
  }, [])

  return (
    <header className="nav" ref={headerRef}>
      <div className="container nav-inner">
        <a className="brand nav-brand" href={homeHref} aria-label="銘印鑽石首頁">
          <svg
            className="brand-mark"
            viewBox="7684 11471 5729 2870"
            aria-hidden="true"
          >
            <path d={BRAND_PATH} fill="currentColor" />
          </svg>
          <span className="brand-name">
            <span className="zh">銘印鑽石</span>
            <span className="en">IMPRINT DIAMOND</span>
          </span>
        </a>

        <nav className="site-nav-desktop nav-menu-col" aria-label="主選單">
          <NavList siteRoot={siteRoot} />
        </nav>

        <nav className="site-nav-mobile" aria-label="主選單">
          <NavList siteRoot={siteRoot} />
        </nav>

        <div className="nav-cta nav-cta-col">
          <AccountMenu siteRoot={siteRoot} session={session} />
          <a
            className="btn btn-mint btn-calc"
            href={resolveHref("/shop/calculator/", siteRoot)}
          >
            開始訂製
          </a>
          <a
            className="btn btn-line btn-contact"
            href={resolveHref("/contact.html", siteRoot)}
          >
            聯絡我們
          </a>
          <a className="btn btn-line" href="tel:0229770268">
            02-2977-0268
          </a>
          <a
            className="btn btn-dark"
            href="https://lin.ee/ktVBtmx"
            target="_blank"
            rel="noopener"
          >
            預約諮詢
          </a>
          <button className="nav-burger" aria-label="開啟選單" type="button">
            <span />
            <span />
            <span />
          </button>
        </div>
      </div>
    </header>
  )
}
