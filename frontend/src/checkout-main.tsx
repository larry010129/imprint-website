import { createRoot } from "react-dom/client";
import CheckoutPage from "@/components/CheckoutPage";
import "./index.css";

document.querySelectorAll("[data-checkout-root]").forEach((el) => {
  createRoot(el).render(<CheckoutPage />);
});
