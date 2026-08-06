import { createRoot } from "react-dom/client";
import Journal from "@/components/Journal";
import "./index.css";

document.querySelectorAll("[data-journal-root]").forEach((el) => {
  createRoot(el).render(<Journal />);
});
