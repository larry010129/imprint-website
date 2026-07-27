import { createRoot } from "react-dom/client"
import AccountPage from "@/components/AccountPage"
import "./index.css"

document.querySelectorAll("[data-account-root]").forEach((el) => {
  createRoot(el).render(<AccountPage />)
})
