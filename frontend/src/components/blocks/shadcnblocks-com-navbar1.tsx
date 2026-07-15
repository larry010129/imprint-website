import { Menu } from "lucide-react"
import type { ReactNode } from "react"

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import { Button } from "@/components/ui/button"
import {
  NavigationMenu,
  NavigationMenuContent,
  NavigationMenuItem,
  NavigationMenuLink,
  NavigationMenuList,
  NavigationMenuTrigger,
  navigationMenuTriggerStyle,
} from "@/components/ui/navigation-menu"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet"
import { cn } from "@/lib/utils"

export interface MenuItem {
  title: string
  url: string
  description?: string
  icon?: ReactNode
  items?: MenuItem[]
}

export interface Navbar1Props {
  logo?: {
    url: string
    src: string
    alt: string
    title: string
  }
  logoNode?: ReactNode
  menu?: MenuItem[]
  mobileExtraLinks?: {
    name: string
    url: string
  }[]
  auth?: {
    login: {
      text: string
      url: string
    }
    signup: {
      text: string
      url: string
    }
  }
  extraActions?: ReactNode
}

const Navbar1 = ({
  logo = {
    url: "https://www.shadcnblocks.com",
    src: "https://www.shadcnblocks.com/images/block/block-1.svg",
    alt: "logo",
    title: "Shadcnblocks.com",
  },
  logoNode,
  menu = [],
  mobileExtraLinks = [],
  auth = {
    login: { text: "Log in", url: "#" },
    signup: { text: "Sign up", url: "#" },
  },
  extraActions,
}: Navbar1Props) => {
  const logoMark = logoNode ?? (
    <img src={logo.src} className="w-8" alt={logo.alt} />
  )

  return (
    <div className="container nav-inner">
      <nav className="site-nav-bar-desktop">
        <div className="flex min-w-0 flex-1 items-center gap-6">
          <a href={logo.url} className="brand flex shrink-0 items-center gap-2">
            {logoMark}
            <span className="brand-name">
              <span className="zh">{logo.title}</span>
              {logo.alt ? <span className="en">{logo.alt}</span> : null}
            </span>
          </a>
          <div className="flex min-w-0 flex-1 items-center justify-center">
            <NavigationMenu className="site-nav-menu">
              <NavigationMenuList>
                {menu.map((item) => renderMenuItem(item))}
              </NavigationMenuList>
            </NavigationMenu>
          </div>
        </div>
        <div className="nav-cta flex shrink-0 items-center gap-2">
          {extraActions}
          <Button asChild variant="outline" size="sm" className="btn-line">
            <a href={auth.login.url}>{auth.login.text}</a>
          </Button>
          <Button asChild size="sm" className="btn-mint">
            <a href={auth.signup.url}>{auth.signup.text}</a>
          </Button>
        </div>
      </nav>

      <div className="site-nav-bar-mobile">
        <div className="flex items-center justify-between gap-3">
          <a href={logo.url} className="brand flex items-center gap-2">
            {logoMark}
            <span className="brand-name">
              <span className="zh">{logo.title}</span>
              {logo.alt ? <span className="en">{logo.alt}</span> : null}
            </span>
          </a>
          <Sheet>
            <SheetTrigger asChild>
              <Button variant="outline" size="icon" aria-label="開啟選單">
                <Menu className="size-4" />
              </Button>
            </SheetTrigger>
            <SheetContent className="overflow-y-auto">
              <SheetHeader>
                <SheetTitle>
                  <a href={logo.url} className="brand flex items-center gap-2">
                    {logoMark}
                    <span className="brand-name">
                      <span className="zh">{logo.title}</span>
                      {logo.alt ? <span className="en">{logo.alt}</span> : null}
                    </span>
                  </a>
                </SheetTitle>
              </SheetHeader>
              <div className="my-6 flex flex-col gap-6">
                <Accordion
                  type="single"
                  collapsible
                  className="flex w-full flex-col gap-4"
                >
                  {menu.map((item) => renderMobileMenuItem(item))}
                </Accordion>
                {mobileExtraLinks.length ? (
                  <div className="border-t border-border py-4">
                    <div className="grid grid-cols-2 justify-start">
                      {mobileExtraLinks.map((link) => (
                        <a
                          key={link.url}
                          className="inline-flex h-10 items-center gap-2 whitespace-nowrap rounded-md px-4 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-accent-foreground"
                          href={link.url}
                        >
                          {link.name}
                        </a>
                      ))}
                    </div>
                  </div>
                ) : null}
                <div className="flex flex-col gap-3">
                  <Button asChild variant="outline">
                    <a href={auth.login.url}>{auth.login.text}</a>
                  </Button>
                  <Button asChild className="btn-mint">
                    <a href={auth.signup.url}>{auth.signup.text}</a>
                  </Button>
                </div>
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </div>
  )
}

function renderMenuItem(item: MenuItem) {
  if (item.items?.length) {
    return (
      <NavigationMenuItem key={item.title}>
        <NavigationMenuTrigger className="site-nav-trigger">
          {item.title}
        </NavigationMenuTrigger>
        <NavigationMenuContent>
          <ul className="w-80 p-3">
            {item.items.map((subItem) => (
              <li key={subItem.title}>
                <NavigationMenuLink asChild>
                  <a
                    className="flex select-none gap-4 rounded-md p-3 leading-none no-underline outline-none transition-colors hover:bg-muted hover:text-accent-foreground"
                    href={subItem.url}
                  >
                    {subItem.icon}
                    <div>
                      <div className="text-sm font-semibold">
                        {subItem.title}
                      </div>
                      {subItem.description ? (
                        <p className="text-sm leading-snug text-muted-foreground">
                          {subItem.description}
                        </p>
                      ) : null}
                    </div>
                  </a>
                </NavigationMenuLink>
              </li>
            ))}
          </ul>
        </NavigationMenuContent>
      </NavigationMenuItem>
    )
  }

  return (
    <NavigationMenuItem key={item.title}>
      <NavigationMenuLink asChild>
        <a
          className={cn(
            navigationMenuTriggerStyle(),
            "site-nav-link nav-plain-link",
          )}
          href={item.url}
        >
          {item.title}
        </a>
      </NavigationMenuLink>
    </NavigationMenuItem>
  )
}

function renderMobileMenuItem(item: MenuItem) {
  if (item.items?.length) {
    return (
      <AccordionItem
        key={item.title}
        value={item.title}
        className="border-b-0"
      >
        <AccordionTrigger className="py-0 font-semibold hover:no-underline">
          {item.title}
        </AccordionTrigger>
        <AccordionContent className="mt-2">
          {item.items.map((subItem) => (
            <a
              key={subItem.title}
              className="flex select-none gap-4 rounded-md p-3 leading-none outline-none transition-colors hover:bg-muted hover:text-accent-foreground"
              href={subItem.url}
            >
              {subItem.icon}
              <div>
                <div className="text-sm font-semibold">{subItem.title}</div>
                {subItem.description ? (
                  <p className="text-sm leading-snug text-muted-foreground">
                    {subItem.description}
                  </p>
                ) : null}
              </div>
            </a>
          ))}
        </AccordionContent>
      </AccordionItem>
    )
  }

  return (
    <a key={item.title} href={item.url} className="font-semibold">
      {item.title}
    </a>
  )
}

export { Navbar1 }
