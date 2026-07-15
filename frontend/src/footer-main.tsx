import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import HoverFooter from "@/components/HoverFooter";
import "./footer.css";

document.querySelectorAll<HTMLElement>("[data-hover-footer-root]").forEach((el) => {
  createRoot(el).render(
    <StrictMode>
      <HoverFooter />
    </StrictMode>,
  );
});
