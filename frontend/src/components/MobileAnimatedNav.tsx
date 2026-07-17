import * as React from "react"
import {
  motion,
  type Variants,
} from "motion/react"

import { NAV_ITEMS, resolveHref } from "@/lib/nav-items"

const panelVariants: Variants = {
  open: {
    opacity: 1,
    transition: { duration: 0.22, ease: "easeOut" },
  },
  closed: {
    opacity: 0,
    transition: { duration: 0.18 },
  },
}

const navVariants: Variants = {
  open: { transition: { staggerChildren: 0.06, delayChildren: 0.18 } },
  closed: { transition: { staggerChildren: 0.04, staggerDirection: -1 } },
}

const itemVariants: Variants = {
  open: {
    y: 0,
    opacity: 1,
    transition: { y: { stiffness: 1000, velocity: -100 } },
  },
  closed: {
    y: 40,
    opacity: 0,
    transition: { y: { stiffness: 1000 } },
  },
}

type MobileAnimatedNavProps = {
  isOpen: boolean
  siteRoot: string
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
        <motion.path
          fill="transparent"
          strokeWidth="3"
          stroke="currentColor"
          strokeLinecap="round"
          animate={
            isOpen
              ? { d: "M 3 16.5 L 17 2.5" }
              : { d: "M 2 2.5 L 20 2.5" }
          }
        />
        <motion.path
          fill="transparent"
          strokeWidth="3"
          stroke="currentColor"
          strokeLinecap="round"
          d="M 2 9.423 L 20 9.423"
          animate={{ opacity: isOpen ? 0 : 1 }}
          transition={{ duration: 0.1 }}
        />
        <motion.path
          fill="transparent"
          strokeWidth="3"
          stroke="currentColor"
          strokeLinecap="round"
          animate={
            isOpen
              ? { d: "M 3 2.5 L 17 16.346" }
              : { d: "M 2 16.346 L 20 16.346" }
          }
        />
      </svg>
    </button>
  )
}

export default function MobileAnimatedNav({
  isOpen,
  siteRoot,
  onNavigate,
  accountSlot,
}: MobileAnimatedNavProps) {
  const [expandedId, setExpandedId] = React.useState<string | null>(null)

  React.useEffect(() => {
    if (!isOpen) setExpandedId(null)
  }, [isOpen])

  return (
    <motion.nav
      className="mobile-animated-nav"
      initial={false}
      animate={isOpen ? "open" : "closed"}
      aria-hidden={!isOpen}
      style={{ pointerEvents: isOpen ? "auto" : "none" }}
    >
      <motion.div
        className="mobile-animated-nav__panel"
        variants={panelVariants}
      />
      <motion.ul
        className="mobile-animated-nav__list"
        variants={navVariants}
        role="list"
      >
        {NAV_ITEMS.map((item) => {
          const hasChildren = !!item.children?.length
          const expanded = expandedId === item.id

          return (
            <motion.li
              key={item.id}
              className="mobile-animated-nav__item"
              variants={itemVariants}
            >
              <div className="mobile-animated-nav__row">
                <a
                  href={resolveHref(item.href, siteRoot)}
                  className="mobile-animated-nav__link"
                  onClick={onNavigate}
                >
                  {item.label}
                </a>
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
            </motion.li>
          )
        })}
        {accountSlot ? (
          <motion.li
            className="mobile-animated-nav__item mobile-animated-nav__item--account"
            variants={itemVariants}
          >
            {accountSlot}
          </motion.li>
        ) : null}
      </motion.ul>
    </motion.nav>
  )
}
