export type NavChild = {
  label: string
  href: string
}

export type NavItem = {
  id: string
  label: string
  href: string
  children?: NavChild[]
}

export const NAV_ITEMS: NavItem[] = [
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
    ],
  },
  { id: "track-order", label: "查詢訂製進度", href: "/track-order.html" },
]

export function resolveHref(href: string, siteRoot: string): string {
  if (/^(https?:|tel:|mailto:)/.test(href)) return href
  if (!siteRoot) return href
  let path = href.startsWith("/") ? href.slice(1) : href
  if (path === "") path = "index.html"
  else if (path.endsWith("/")) path += "index.html"
  return siteRoot + path
}
