import { createRoot } from "react-dom/client"
import SiteNav from "@/components/SiteNav"
import "./index.css"

document.querySelectorAll("[data-site-nav-root]").forEach((el) => {
  createRoot(el).render(<SiteNav />)
})
