import * as React from "react"

import { navParentIsLink, resolveHref, type NavItem } from "@/lib/nav-items"

type MobileAnimatedNavProps = {
  isOpen: boolean
  siteRoot: string
  items: NavItem[]
  onNavigate: () => void
  accountSlot?: React.ReactNode
}

export function MobileMenuToggle({
  isOpen,
  onToggle,
}: {
  isOpen: boolean
  onToggle: () => void
}) {
  return (
    <button
      type="button"
      className="nav-burger mobile-menu-toggle"
      aria-label={isOpen ? "關閉選單" : "開啟選單"}
      aria-expanded={isOpen}
      onClick={onToggle}
    >
      <svg width="23" height="23" viewBox="0 0 23 23" aria-hidden="true">
        <path
          fill="transparent"
          strokeWidth="3"
          stroke="currentColor"
          strokeLinecap="round"
          d={isOpen ? "M 3 16.5 L 17 2.5" : "M 2 2.5 L 20 2.5"}
        />
        <path
          className="mobile-menu-toggle__middle"
          fill="transparent"
          strokeWidth="3"
          stroke="currentColor"
          strokeLinecap="round"
          d="M 2 9.423 L 20 9.423"
          opacity={isOpen ? 0 : 1}
        />
        <path
          fill="transparent"
          strokeWidth="3"
          stroke="currentColor"
          strokeLinecap="round"
          d={isOpen ? "M 3 2.5 L 17 16.346" : "M 2 16.346 L 20 16.346"}
        />
      </svg>
    </button>
  )
}

export default function MobileAnimatedNav({
  isOpen,
  siteRoot,
  items,
  onNavigate,
  accountSlot,
}: MobileAnimatedNavProps) {
  const [expandedId, setExpandedId] = React.useState<string | null>(null)

  React.useEffect(() => {
    if (!isOpen) setExpandedId(null)
  }, [isOpen])

  return (
    <nav
      className={`mobile-animated-nav${isOpen ? " is-open" : ""}`}
      aria-hidden={!isOpen}
    >
      <div className="mobile-animated-nav__panel" />
      <ul className="mobile-animated-nav__list" role="list">
        {items.map((item) => {
          const hasChildren = !!item.children?.length
          const expanded = expandedId === item.id

          return (
            <li key={item.id} className="mobile-animated-nav__item">
              <div className="mobile-animated-nav__row">
                {navParentIsLink(item) ? (
                  <a
                    href={resolveHref(item.href, siteRoot)}
                    className="mobile-animated-nav__link"
                    onClick={onNavigate}
                  >
                    {item.label}
                  </a>
                ) : (
                  <button
                    type="button"
                    className="mobile-animated-nav__link mobile-animated-nav__link--label"
                    onClick={() =>
                      setExpandedId(expanded ? null : item.id)
                    }
                  >
                    {item.label}
                  </button>
                )}
                {hasChildren ? (
                  <button
                    type="button"
                    className="mobile-animated-nav__expand"
                    aria-expanded={expanded}
                    aria-label={`展開 ${item.label}`}
                    onClick={() =>
                      setExpandedId(expanded ? null : item.id)
                    }
                  >
                    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
                      <path
                        d="M6 9l6 6 6-6"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        style={{
                          transform: expanded ? "rotate(180deg)" : undefined,
                          transformOrigin: "center",
                        }}
                      />
                    </svg>
                  </button>
                ) : null}
              </div>
              {hasChildren && expanded ? (
                <ul className="mobile-animated-nav__sublist">
                  {item.children!.map((child) => (
                    <li key={child.href}>
                      <a
                        href={resolveHref(child.href, siteRoot)}
                        className="mobile-animated-nav__sublink"
                        onClick={onNavigate}
                      >
                        {child.label}
                      </a>
                    </li>
                  ))}
                </ul>
              ) : null}
            </li>
          )
        })}
        {accountSlot ? (
          <li className="mobile-animated-nav__item mobile-animated-nav__item--account">
            {accountSlot}
          </li>
        ) : null}
      </ul>
    </nav>
  )
}
