import { createRoot } from "react-dom/client";
import DnaDiamondPage from "@/components/DnaDiamondPage";
import "./index.css";

document.querySelectorAll("[data-dna-diamond-root]").forEach((el) => {
  createRoot(el).render(<DnaDiamondPage />);
});
