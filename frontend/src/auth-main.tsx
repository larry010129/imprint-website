import { createRoot } from "react-dom/client"
import { Auth } from "@/components/ui/auth-form-1"
import "./index.css"

document.querySelectorAll("[data-auth-login-root]").forEach((el) => {
  const googleClientId = el.getAttribute("data-google-client-id") || undefined
  createRoot(el).render(<Auth googleClientId={googleClientId} />)
})
