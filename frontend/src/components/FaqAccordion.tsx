import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  FAQ_CATEGORY_LIST,
  FAQ_ITEMS_FULL,
  FAQ_ITEMS_TEASER,
  type FaqItem,
} from "@/data/faq-items"

const LINE_URL = "https://lin.ee/ktVBtmx"

const TAB_TRIGGER_CLASS =
  "relative after:absolute after:inset-x-0 after:bottom-0 after:-mb-1 after:h-0.5 hover:bg-accent hover:text-foreground data-[state=active]:bg-transparent data-[state=active]:shadow-none data-[state=active]:after:bg-primary data-[state=active]:hover:bg-accent"

type FaqAccordionProps = {
  variant?: "full" | "teaser"
  items?: FaqItem[]
  className?: string
}

function FaqAccordionPanel({ list }: { list: FaqItem[] }) {
  return (
    <Accordion
      type="single"
      collapsible
      className="bg-card ring-muted w-full rounded-2xl border px-8 py-3 shadow-sm ring-4 dark:ring-0"
    >
      {list.map((item) => (
        <AccordionItem
          key={item.id}
          value={item.id}
          className="border-dashed"
        >
          <AccordionTrigger className="cursor-pointer text-base hover:no-underline">
            {item.question}
          </AccordionTrigger>
          <AccordionContent>
            <div className="text-base text-muted-foreground">{item.answer}</div>
          </AccordionContent>
        </AccordionItem>
      ))}
    </Accordion>
  )
}

export function FaqAccordion({
  variant = "full",
  items,
  className = "",
}: FaqAccordionProps) {
  const list = items ?? (variant === "teaser" ? FAQ_ITEMS_TEASER : FAQ_ITEMS_FULL)

  if (variant === "teaser") {
    return (
      <div className="mx-auto w-full max-w-xl">
        <FaqAccordionPanel list={list} />
      </div>
    )
  }

  const defaultTab = FAQ_CATEGORY_LIST[0]?.id ?? "about"

  return (
    <section className={`py-16 md:py-24 ${className}`.trim()}>
      <div className="mx-auto max-w-5xl px-4 md:px-6">
        <div className="mx-auto max-w-xl">
          <Tabs defaultValue={defaultTab}>
            <TabsList className="h-auto w-full flex-wrap justify-start gap-2 rounded-none border-b border-border bg-transparent px-0 py-1 text-foreground">
              {FAQ_CATEGORY_LIST.map((cat) => (
                <TabsTrigger
                  key={cat.id}
                  value={cat.id}
                  className={TAB_TRIGGER_CLASS}
                >
                  {cat.title}
                </TabsTrigger>
              ))}
            </TabsList>

            {FAQ_CATEGORY_LIST.map((cat) => (
              <TabsContent key={cat.id} value={cat.id} className="mt-6">
                <FaqAccordionPanel list={cat.items} />
              </TabsContent>
            ))}
          </Tabs>

          <p className="text-muted-foreground mt-6 px-8">
            還有想了解的？歡迎透過官方 LINE 與{" "}
            <a
              href={LINE_URL}
              target="_blank"
              rel="noopener"
              className="text-primary font-medium hover:underline"
            >
              專屬顧問聯繫
            </a>
          </p>
        </div>
      </div>
    </section>
  )
}

export default FaqAccordion
