import type { ReactNode } from "react"
import { FAQ_CATEGORIES, type FaqEntry } from "@/data/faq-content"

export type FaqItem = {
  id: string
  question: string
  answer: ReactNode
}

export type FaqCategory = {
  id: string
  title: string
  items: FaqItem[]
}

function answerWithLinks(entry: FaqEntry): ReactNode {
  if (entry.id === "item-6") {
    return (
      <>
        價格依克拉數計算：0.10 克拉 NT$24,000 起、0.50 克拉 NT$98,000、1.00 克拉
        NT$250,000（圓形明亮式切工／白鑽）。非圓形切工（公主方、橢圓、梨形等）加價
        10%，且需 0.30 克拉以上才能製作；彩鑽最低製作規格為 0.30 克拉，報價依顏色稀有度而定；3.00
        克拉以上請洽官方 LINE 專屬報價。完整價目請見
        <a href="/price.html"> 價格試算・價格總覽</a>。
      </>
    )
  }

  if (entry.id === "item-10") {
    return (
      <>
        您可以選擇以下任一方式開始訂製：
        <br />
        <br />
        <strong>線上客製試算</strong> — 前往
        <a href="/shop/calculator/"> 客製試算頁</a>
        ，依步驟選擇品項、款式、金屬與鑽石規格，系統即時試算價格；確認後可加入購物車並送出訂單，我們會與您聯繫確認樣本與細節。
        <br />
        <br />
        <strong>預約顧問</strong> — 也可透過官方 LINE 預約，由專屬顧問一對一討論需求、確認樣本份量與報價，再進行採樣與培育。官方
        LINE：
        <a href="https://lin.ee/ktVBtmx" target="_blank" rel="noopener">
          {" "}
          點此加入
        </a>
        ；電話：02-2977-0268；門市：新北市三重區福德南路 43 號 1 樓（預約制）。
      </>
    )
  }

  return entry.answer
}

function toFaqItem(entry: FaqEntry): FaqItem {
  return {
    id: entry.id,
    question: entry.question,
    answer: answerWithLinks(entry),
  }
}

export const FAQ_CATEGORY_LIST: FaqCategory[] = FAQ_CATEGORIES.map((cat) => ({
  id: cat.id,
  title: cat.title,
  items: cat.items.map(toFaqItem),
}))

export const FAQ_ITEMS_FULL: FaqItem[] = FAQ_CATEGORY_LIST.flatMap(
  (cat) => cat.items,
)

const TEASER_IDS = ["item-1", "item-6", "item-9", "item-10"] as const

export const FAQ_ITEMS_TEASER: FaqItem[] = TEASER_IDS.map(
  (id) => FAQ_ITEMS_FULL.find((item) => item.id === id)!,
)
