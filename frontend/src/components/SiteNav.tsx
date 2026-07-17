import * as React from "react"



import { AccountMenu } from "@/components/AccountMenu"

import MobileAnimatedNav, {

  MobileMenuToggle,

} from "@/components/MobileAnimatedNav"

import { MovingBorderButton } from "@/components/ui/moving-border"

import { NAV_ITEMS, resolveHref } from "@/lib/nav-items"

import { fetchSession, type Session } from "@/lib/session"



const BRAND_PATH =

  "M12299 14276l-1463 -1021c-1,-1 -3,-2 -4,-3 -28,-19 -35,-58 -15,-85 135,-193 384,-30 400,-19 1,0 1,1 2,1l1123 784 715 -442 0 -1169 -715 -442 -1658 1153 0 0c-86,60 2,-1 -86,60 -217,152 -769,540 -850,596 -49,33 -83,57 -118,82l-3 2c-143,100 -304,213 -463,306 -163,95 -325,170 -466,192 -25,4 -49,7 -71,9 -24,2 -48,3 -70,3 -101,0 -199,-17 -292,-51 -92,-34 -177,-83 -253,-149 -87,-75 -157,-166 -204,-265 -48,-100 -74,-208 -74,-315 0,-118 33,-236 93,-346 49,-90 116,-174 198,-249 -82,-75 -149,-160 -198,-250 -60,-111 -93,-229 -93,-346 0,-107 26,-215 74,-315 48,-99 117,-190 204,-265 94,-81 203,-138 319,-170 116,-32 241,-39 367,-19 142,22 304,97 467,193 159,93 320,206 464,307l14 10c31,21 60,42 104,72 52,36 297,208 523,366l90 63c26,18 35,52 19,80 -7,12 -54,89 -157,103 -50,7 -114,-2 -192,-42 -3,-2 -6,-3 -9,-5 -174,-122 -247,-173 -283,-199 -74,-52 -134,-94 -164,-114l0 0 0 0c-11,-8 -31,-21 -55,-38 -1,-1 -3,-2 -4,-3 -68,-48 9,6 -62,-43 -126,-89 -276,-194 -422,-281 -141,-84 -277,-151 -380,-167 -83,-13 -163,-9 -238,12 -74,20 -143,56 -203,107 -54,46 -97,102 -127,162 -29,59 -45,122 -45,184 0,80 30,164 82,244 54,81 131,156 225,214 2,1 4,2 6,4l50 35c17,11 29,30 29,52l0 96 0 0c0,19 -9,38 -26,50l-52 36 0 0c-1,1 -2,1 -3,2 -95,58 -174,134 -228,215 -52,79 -82,164 -82,244 0,62 16,126 45,185 29,60 73,116 127,162 60,51 128,87 202,107 74,20 152,24 233,12 2,0 3,-1 5,-1 208,-32 547,-269 797,-443 1,-1 2,-2 3,-2l1 0 0 0 0 0c53,-37 36,-25 63,-44 15,-10 34,-24 60,-42 104,-71 2653,-1849 2722,-1898 20,-15 47,-17 69,-3l963 596c20,10 34,31 34,55l0 1442 0 0c0,20 -10,40 -29,52l-968 599 0 0c-20,12 -47,12 -67,-2z"



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

  const [mobileOpen, setMobileOpen] = React.useState(false)



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

    return () => window.removeEventListener("scroll", onNavScroll)

  }, [])



  React.useEffect(() => {

    document.body.style.overflow = mobileOpen ? "hidden" : ""

    return () => {

      document.body.style.overflow = ""

    }

  }, [mobileOpen])



  React.useEffect(() => {

    const mq = window.matchMedia("(min-width: 861px)")

    const onChange = () => {

      if (mq.matches) setMobileOpen(false)

    }

    mq.addEventListener("change", onChange)

    return () => mq.removeEventListener("change", onChange)

  }, [])



  return (

    <header

      className={`nav${mobileOpen ? " is-mobile-menu-open" : ""}`}

      ref={headerRef}

    >

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



        <div className="nav-cta nav-cta-col">

          <MovingBorderButton

            as="a"

            href={resolveHref("/shop/calculator/", siteRoot)}

            borderRadius="0.45rem"

            containerClassName="nav-calc-moving shrink-0"

            className="nav-calc-moving-inner whitespace-nowrap"

          >

            開始訂製

          </MovingBorderButton>

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

          <AccountMenu siteRoot={siteRoot} session={session} />

          <MobileMenuToggle

            isOpen={mobileOpen}

            onToggle={() => setMobileOpen((open) => !open)}

          />

        </div>

      </div>



      <MobileAnimatedNav

        isOpen={mobileOpen}

        siteRoot={siteRoot}

        onNavigate={() => setMobileOpen(false)}

        accountSlot={

          <AccountMenu

            siteRoot={siteRoot}

            session={session}

            variant="drawer"

            onNavigate={() => setMobileOpen(false)}

          />

        }

      />

    </header>

  )

}


