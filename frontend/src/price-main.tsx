import { createRoot } from "react-dom/client";
import PriceTable from "@/components/PriceTable";
import "./index.css";

document.querySelectorAll("[data-price-root]").forEach((el) => {
  createRoot(el).render(<PriceTable />);
});
