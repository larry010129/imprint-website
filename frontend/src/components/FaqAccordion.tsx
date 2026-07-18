import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import {
  FAQ_ITEMS_FULL,
  FAQ_ITEMS_TEASER,
  type FaqItem,
} from "@/data/faq-items"

const LINE_URL = "https://lin.ee/ktVBtmx"

type FaqAccordionProps = {
  variant?: "full" | "teaser"
  items?: FaqItem[]
  className?: string
}

export function FaqAccordion({
  variant = "full",
  items,
  className = "",
}: FaqAccordionProps) {
  const list = items ?? (variant === "teaser" ? FAQ_ITEMS_TEASER : FAQ_ITEMS_FULL)

  const accordion = (
    <Accordion
      type="single"
      collapsible
      className="bg-card ring-muted mx-auto w-full max-w-xl rounded-2xl border px-8 py-3 shadow-sm ring-4 dark:ring-0"
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

  if (variant === "teaser") {
    return accordion
  }

  return (
    <section className={`py-16 md:py-24 ${className}`.trim()}>
      <div className="mx-auto max-w-5xl px-4 md:px-6">
        <div className="mx-auto max-w-xl">
          {accordion}

          {variant === "full" && (
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
          )}
        </div>
      </div>
    </section>
  )
}

export default FaqAccordion
