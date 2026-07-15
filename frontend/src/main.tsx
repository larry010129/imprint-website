import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { FaqAccordion } from "@/components/FaqAccordion"
import "./faq.css"

document.querySelectorAll<HTMLElement>("[data-faq-root]").forEach((el) => {
  const variant = el.dataset.variant === "teaser" ? "teaser" : "full"
  createRoot(el).render(
    <StrictMode>
      <FaqAccordion variant={variant} />
    </StrictMode>,
  )
})
