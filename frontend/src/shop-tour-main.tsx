import { createRoot } from "react-dom/client";
import ShopTour from "@/components/ShopTour";
import "./index.css";
import "../../public/css/shop-tour.css";

document.querySelectorAll("[data-shop-tour-root]").forEach((el) => {
  createRoot(el).render(<ShopTour />);
});
